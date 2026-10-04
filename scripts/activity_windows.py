"""Explicit windowed inference using the episode model's exact feature extractor."""
from dataclasses import asdict, dataclass
import math
from activity_svm import FEATURE_SCHEMA

VERSION = 'movement-windows/1.0.0'


@dataclass(frozen=True)
class WindowConfig:
    duration_s: float = 6.0
    overlap_fraction: float = .5
    feature_schema_version: str = FEATURE_SCHEMA
    provenance: str = 'engineering_demo_window_parameters'

    def __post_init__(self):
        if (not math.isfinite(self.duration_s) or self.duration_s <= 0 or
            not math.isfinite(self.overlap_fraction) or not 0 <= self.overlap_fraction < 1 or
            self.feature_schema_version != FEATURE_SCHEMA or not self.provenance):
            raise ValueError('Invalid window duration, overlap, schema or provenance')


def window_predictions(processed, model, config=WindowConfig(), protocol=None):
    rate = processed['sampling']['rate_hz']
    count = round(config.duration_s*rate)
    step = round(count*(1-config.overlap_fraction))
    if count < 3 or step < 1:
        raise ValueError('Window and step require sufficient samples')
    predictions = []
    for start in range(0,len(processed['samples'])-count+1,step):
        rows = processed['samples'][start:start+count]
        window = {**processed,'samples':rows}
        prediction = model.predict(window,**({'protocol':protocol} if protocol is not None else {}))
        predictions.append({**prediction,'window_index':len(predictions), 'start_index':start,
                            'end_index':start+count-1,'start_s':rows[0]['timestamp_s'],
                            'end_s':rows[-1]['timestamp_s'],'sample_count':count})
    used_end = predictions[-1]['end_index']+1 if predictions else 0
    return {'status':'ready' if predictions else 'unavailable', 'version':VERSION,
            'reasons':[] if predictions else ['recording_shorter_than_configured_window'],
            'config':asdict(config),'sample_count_per_window':count,'step_samples':step,
            'windows':predictions,'trailing_samples_not_windowed':len(processed['samples'])-used_end,
            'partial_window_policy':'exclude; no padding or fabricated samples'}
