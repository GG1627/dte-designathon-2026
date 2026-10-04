"""Explicit presence and provenance; configuration does not manufacture signals."""
from dataclasses import asdict, dataclass, field

SIDES = ('left', 'right')
MODES = ('bilateral_knees_plus_insoles', 'single_knee_plus_mock_insoles')
SOURCES = ('hardware', 'synthetic_demo', 'unavailable')


@dataclass(frozen=True)
class Sensor:
    present: bool = False
    source: str = 'unavailable'
    sensor_id: str | None = None

    def __post_init__(self):
        if type(self.present) is not bool or self.source not in SOURCES:
            raise ValueError('Explicit boolean presence and supported source required')
        if self.present:
            if self.source == 'unavailable' or not isinstance(self.sensor_id, str) or not self.sensor_id.strip():
                raise ValueError('Present sensor requires source and identity')
        elif self.source != 'unavailable' or self.sensor_id is not None:
            raise ValueError('Absent sensor must be unavailable with null identity')


@dataclass(frozen=True)
class KneeSensors:
    thigh: Sensor = field(default_factory=Sensor)
    shank: Sensor = field(default_factory=Sensor)

    @property
    def present(self):
        return self.thigh.present and self.shank.present


def combined_source(sources):
    values = set(sources)
    return next(iter(values)) if len(values) == 1 else 'mixed'


@dataclass(frozen=True)
class SensorConfiguration:
    mode: str
    knees: dict
    insoles: dict
    knee_protocols: dict = field(default_factory=lambda: {s: 'thigh_shank_6DOF_v1' for s in SIDES})

    def __post_init__(self):
        if self.mode not in MODES or set(self.knees) != set(SIDES) or set(self.insoles) != set(SIDES):
            raise ValueError('Supported mode and explicit left/right sensors required')
        if not all(isinstance(self.knees[s], KneeSensors) and isinstance(self.insoles[s], Sensor) for s in SIDES):
            raise ValueError('KneeSensors and Sensor descriptors required')
        if set(self.knee_protocols) != set(SIDES) or not all(self.knee_protocols.values()):
            raise ValueError('Explicit per-knee acquisition protocol required')
        identities = [sensor.sensor_id for pair in self.knees.values() for sensor in (pair.thigh,pair.shank) if sensor.present]
        identities.extend(sensor.sensor_id for sensor in self.insoles.values() if sensor.present)
        if len(identities) != len(set(identities)):
            raise ValueError('Present sensors require distinct identities')
        if self.mode == 'single_knee_plus_mock_insoles':
            if sum(k.present for k in self.knees.values()) != 1:
                raise ValueError('Single-knee mode requires exactly one complete pair')
            if any(k.thigh.present or k.shank.present for k in self.knees.values() if not k.present):
                raise ValueError('Single-knee mode has no opposite knee pods')
            if any(not f.present or f.source != 'synthetic_demo' for f in self.insoles.values()):
                raise ValueError('Designathon mode requires both software insole streams')

    def metadata(self):
        return {'version': 'kintra-sensors/1.0.0', **asdict(self)}

    @classmethod
    def synthetic(cls, raw, mode='bilateral_knees_plus_insoles'):
        """Fixture convenience only; real adapters must declare hardware explicitly."""
        if raw.get('synthetic') is not True:
            raise ValueError('Synthetic configuration requires explicitly synthetic input')
        knees, feet = {}, {}
        for side in SIDES:
            ids = raw.get('sources', {}).get(side, {})
            pair = ids.get('knee', [])
            knees[side] = KneeSensors(*[Sensor(True, 'synthetic_demo', identity) for identity in pair]) if len(pair) == 2 else KneeSensors()
            feet[side] = Sensor(True, 'synthetic_demo', ids['insole']) if ids.get('insole') else Sensor()
        return cls(mode, knees, feet)


def source_reasons(raw, sensor, packets, actual_id):
    """Fail closed on declared synthetic/hardware conflicts; never relabel data."""
    reasons = []
    if sensor.sensor_id != actual_id:
        reasons.append('sensor_identity_mismatch')
    if sensor.source == 'hardware' and (raw.get('synthetic') is True or
            any(p.get('synthetic') is True or p.get('source') == 'synthetic_demo' for p in packets) or
            isinstance(actual_id, str) and actual_id.startswith(('mock_', 'synthetic_'))):
        reasons.append('synthetic_measurements_cannot_be_labeled_hardware')
    if any(p.get('source') is not None and p['source'] != sensor.source for p in packets):
        reasons.append('measurement_source_mismatch')
    return sorted(set(reasons))
