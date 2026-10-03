"""Generate deterministic, post-extraction sensor fixtures using only Python stdlib."""
import json
import math
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "mock"
RATE_HZ = 100
DURATION_S = 6
MASS_KG = 75
BW_N = MASS_KG * 9.80665
CONTACT_THRESHOLD_N = 20
SCHEMA_VERSION = "0.1.0"


def geometry(side):
    # y points toward participant's left on both feet; medial labels reverse.
    cells = []
    for row, x in enumerate((0.02, 0.12, 0.22)):
        for column, y in enumerate((-0.025, 0.025)):
            medial = (side == "left" and y < 0) or (side == "right" and y > 0)
            cells.append({
                "cell_id": f"{side}_{row}_{column}",
                "x_m": x, "y_m": y, "area_m2": 0.003,
                "region": "medial" if medial else "lateral",
            })
    return cells


def knee(t, side):
    # Smooth flexion response to three labelled bilateral landings.
    angle = math.radians(8)
    velocity = acceleration = 0.0
    for start in (1.0, 3.0, 5.0):
        delta = t - (start + 0.25)
        sigma = 0.18
        amplitude = math.radians(38 if side == "left" else 36)
        pulse = amplitude * math.exp(-0.5 * (delta / sigma) ** 2)
        angle += pulse
        velocity += -delta / sigma**2 * pulse
        acceleration += (delta**2 / sigma**4 - 1 / sigma**2) * pulse
    return {
        "flexion_rad": angle,
        "angular_velocity_rad_s": velocity,
        "angular_acceleration_rad_s2": acceleration,
        "quality": {"valid": True, "reasons": []},
    }


def insole(t, side, cells, scale, missing):
    if missing:
        return {
            "plantar_normal_force_n": None,
            "cell_pressures_pa": [None] * len(cells),
            "cop_m": None, "medial_fraction": None, "lateral_fraction": None,
            "quality": {"valid": False, "reasons": ["sensor_dropout"]},
        }
    phase = None
    for start in (1.0, 3.0, 5.0):
        if start <= t <= start + 0.6:
            phase = (t - start) / 0.6
            break
    force = 0.0 if phase is None else 1.7 * BW_N * scale * math.sin(math.pi * phase) ** 2
    # Illustrative six-cell map: load moves from heel toward forefoot.
    progression = 0 if phase is None else phase
    row_weights = (1.1 - progression, 0.7, 0.1 + progression)
    weights = [row_weights[i // 2] * (0.55 if cell["region"] == "medial" else 0.45)
               for i, cell in enumerate(cells)]
    total_weight = sum(weights)
    forces = [force * weight / total_weight for weight in weights]
    pressures = [value / cell["area_m2"] for value, cell in zip(forces, cells)]
    contact = force > CONTACT_THRESHOLD_N
    cop = ({axis: sum(value * cell[axis] for value, cell in zip(forces, cells)) / force
            for axis in ("x_m", "y_m")} if contact else None)
    medial = (sum(value for value, cell in zip(forces, cells)
                  if cell["region"] == "medial") / force if contact else None)
    return {
        "plantar_normal_force_n": force,
        "cell_pressures_pa": pressures,
        "cop_m": cop,
        "medial_fraction": medial,
        "lateral_fraction": 1 - medial if contact else None,
        "quality": {"valid": True, "reasons": [] if contact else ["below_contact_threshold"]},
    }


def session(scenario):
    cells = {side: geometry(side) for side in ("left", "right")}
    samples = []
    for sequence in range(RATE_HZ * DURATION_S):
        t = sequence / RATE_HZ
        sample = {"sequence": sequence, "timestamp_s": t}
        for side in ("left", "right"):
            scale = 1.1 if scenario == "right_load_bias" and side == "right" else 1.0
            missing = scenario == "sensor_dropout" and side == "left" and 3.1 <= t < 3.25
            sample[side] = {
                "knee": knee(t, side),
                "insole": insole(t, side, cells[side], scale, missing),
            }
        samples.append(sample)
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": f"mock_{scenario}_001",
        "synthetic": True,
        "activity": "bilateral_landing",
        "scenario": scenario,
        "participant": {"id": "synthetic_athlete", "mass_kg": MASS_KG},
        "sampling": {"rate_hz": RATE_HZ, "duration_s": DURATION_S,
                     "clock": "session_monotonic", "synchronization_uncertainty_s": 0.0},
        "processing": {
            "stage": "post_sensor_extraction",
            "knee_derivatives": "analytic derivatives of synthetic flexion",
            "filter": "none; noise-free fixture",
            "calibration": "synthetic ideal alignment and force calibration",
            "cop_min_force_n": CONTACT_THRESHOLD_N,
            "gap_policy": "preserve missing samples as null; no interpolation",
        },
        "sources": {
            side: {"knee": [f"mock_{side}_thigh_imu", f"mock_{side}_shank_imu"],
                   "insole": f"mock_{side}_insole"}
            for side in ("left", "right")
        },
        "insole_geometry": cells,
        "annotations": [
            {"event_id": f"landing_{i + 1}", "type": "synthetic_landing_window",
             "start_s": start, "end_s": start + 0.6}
            for i, start in enumerate((1.0, 3.0, 5.0))
        ],
        "samples": samples,
    }


def verify(data):
    """Check fixture integrity before saving; these are not hardware validations."""
    assert data["synthetic"]
    assert len(data["samples"]) == RATE_HZ * DURATION_S
    missing_count = 0
    for index, sample in enumerate(data["samples"]):
        assert sample["sequence"] == index
        assert sample["timestamp_s"] == index / RATE_HZ
        for side in ("left", "right"):
            motion = sample[side]["knee"]
            assert all(math.isfinite(motion[key]) for key in (
                "flexion_rad", "angular_velocity_rad_s", "angular_acceleration_rad_s2"))
            foot = sample[side]["insole"]
            cells = data["insole_geometry"][side]
            assert len(foot["cell_pressures_pa"]) == len(cells)
            if not foot["quality"]["valid"]:
                missing_count += 1
                assert foot["plantar_normal_force_n"] is None
                assert all(value is None for value in foot["cell_pressures_pa"])
                assert foot["cop_m"] is None
                continue
            force = foot["plantar_normal_force_n"]
            assert force >= 0
            cell_forces = [pressure * cell["area_m2"]
                           for pressure, cell in zip(foot["cell_pressures_pa"], cells)]
            assert math.isclose(sum(cell_forces), force, rel_tol=1e-12, abs_tol=1e-10)
            if force > CONTACT_THRESHOLD_N:
                assert math.isclose(foot["medial_fraction"] + foot["lateral_fraction"], 1)
                for axis in ("x_m", "y_m"):
                    expected = sum(value * cell[axis] for value, cell in zip(cell_forces, cells)) / force
                    assert math.isclose(foot["cop_m"][axis], expected, abs_tol=1e-12)
            else:
                assert foot["cop_m"] is None
    assert missing_count == (15 if data["scenario"] == "sensor_dropout" else 0)
    for sample in data["samples"]:
        left = sample["left"]["insole"]["plantar_normal_force_n"]
        right = sample["right"]["insole"]["plantar_normal_force_n"]
        if left is not None:
            expected = left * (1.1 if data["scenario"] == "right_load_bias" else 1.0)
            assert math.isclose(right, expected, rel_tol=1e-12, abs_tol=1e-10)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for scenario in ("balanced", "right_load_bias", "sensor_dropout"):
        data = session(scenario)
        verify(data)
        target = OUTPUT / f"{scenario}.json"
        target.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")
        print(f"Verified {target.name}: {len(data['samples'])} frames")
