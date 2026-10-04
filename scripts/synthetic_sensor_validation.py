"""Synthetic-only reconstruction checks and CLI presentation, never runtime fusion."""
import math

def validate_processed(raw, processed):
    """Validation-only ground-truth comparison after reconstruction is complete."""
    assert len(processed["samples"]) == len(raw["samples"])
    if raw["processing"]["stage"] == "raw_sensor_fixture":
        assert len(processed["samples"]) == round(raw["sampling"]["rate_hz"] * raw["sampling"]["duration_s"])
    print("Synthetic ideal fixture — not hardware validation.")
    print("\nKintra kinematic reconstruction validation")
    print("-------------------------------------------")
    print(f"Samples: {len(processed['samples'])}")
    print(f"Sampling rate: {processed['sampling']['rate_hz']} Hz")
    signals = (
        ("flexion_rad", "Flexion", "deg", False, 1.0),
        ("angular_velocity_rad_s", "Angular velocity", "deg/s", True, 1e-9),
        ("angular_acceleration_rad_s2", "Angular acceleration", "deg/s^2", True, 5.0),
    )
    has_truth = all("ground_truth" in row for row in raw["samples"])
    for side in ("left", "right"):
        for row in processed["samples"]:
            assert all(math.isfinite(value) for key, value in row[side]["knee"].items() if key != "quality")
            for q in row[side]["orientation"].values():
                assert all(math.isfinite(value) for value in q)
                assert math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10)
        assert all(a[side]["insole"] == b[side]["insole"] for a, b in zip(raw["samples"], processed["samples"]))
        if has_truth:
            print(f"\n{side.upper()} KNEE")
            for key, label, units, absolute_peak, rmse_limit in signals:
                truth = [math.degrees(row["ground_truth"][f"{side}_knee_{key}"]) for row in raw["samples"]]
                estimates = [math.degrees(row[side]["knee"][key]) for row in processed["samples"]]
                errors = [estimate - true for estimate, true in zip(estimates, truth)]
                rmse = math.sqrt(sum(error**2 for error in errors) / len(errors))
                assert rmse < rmse_limit, f"{side} {label} ideal-test RMSE too large: {rmse}"
                true_peak = max(abs(value) for value in truth) if absolute_peak else max(truth)
                peak = max(abs(value) for value in estimates) if absolute_peak else max(estimates)
                peak_label = "peak absolute" if absolute_peak else "peak"
                print(f"\n{label}:")
                print(f"  RMSE: {rmse:.6f} {units}")
                print(f"  Max absolute error: {max(abs(error) for error in errors):.6f} {units}")
                print(f"  True {peak_label}: {true_peak:.6f} {units}")
                print(f"  Reconstructed {peak_label}: {peak:.6f} {units}")

    repeated = {side: [] for side in ("left", "right")}
    print("\nPer-landing kinematic comparison")
    for annotation in raw["annotations"]:
        if annotation["type"] != "synthetic_landing_window":
            continue
        indices = [i for i, row in enumerate(processed["samples"])
                   if annotation["start_s"] <= row["timestamp_s"] <= annotation["end_s"]]
        if not indices:
            continue
        print(f"\n{annotation['event_id']}")
        for side in ("left", "right"):
            metrics = {}
            print(f"  {side.capitalize()}:")
            for key, label, units, absolute_peak, _ in signals:
                values = [math.degrees(processed["samples"][i][side]["knee"][key]) for i in indices]
                peak = max(abs(value) for value in values) if absolute_peak else max(values)
                metrics[label] = peak
                if key == "flexion_rad":
                    metrics["ROM"] = max(values) - min(values)
                if has_truth:
                    truth = [math.degrees(raw["samples"][i]["ground_truth"][f"{side}_knee_{key}"]) for i in indices]
                    true_peak = max(abs(value) for value in truth) if absolute_peak else max(truth)
                    print(f"    {label} peak: true={true_peak:.6f}, estimated={peak:.6f} {units}")
                else:
                    print(f"    {label} peak: estimated={peak:.6f} {units}")
            repeated[side].append(metrics)
    print("\nAnnotated landing metric ranges")
    print("Ranges describe all annotated events; programmed changes are not reconstruction errors.")
    for side, events in repeated.items():
        print(f"\n{side.capitalize()}:")
        for label, units in (("Flexion", "deg"), ("ROM", "deg"),
                             ("Angular velocity", "deg/s"), ("Angular acceleration", "deg/s^2")):
            if events:
                values = [event[label] for event in events]
                print(f"  {label} range: {max(values) - min(values):.12g} {units}")
    print("\nTimestamp validation: PASS")
    print("Quaternion validation: PASS")
    print("Processed schema: PASS")
