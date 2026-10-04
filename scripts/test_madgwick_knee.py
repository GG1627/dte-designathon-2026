"""Deterministic ideal IMU checks; no sensor noise, bias, or translation."""
import math

from madgwick import (
    MadgwickIMU, quaternion_conjugate, quaternion_multiply,
    quaternion_normalize, quaternion_relative, relative_flexion_y_rad,
)

RATE_HZ = 100
DURATION_S = 4.0
BETA = 0.1


def assert_unit(q):
    assert all(math.isfinite(value) for value in q), q
    assert math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10), q


def ideal_motion(t):
    """45-degree raised-cosine flexion pulse, with analytic angular velocity."""
    amplitude = math.radians(45)
    frequency = 2.0 * math.pi / DURATION_S
    angle = amplitude * (1.0 - math.cos(frequency * t)) / 2.0
    velocity = amplitude * frequency * math.sin(frequency * t) / 2.0
    return angle, velocity


def ideal_acceleration(angle):
    """Specific force = -physical gravity, expressed in sensor frame.

    Inverse +Y rotation of world (0, 0, +g): (-g*sin(angle), 0, g*cos(angle)).
    """
    g = 9.80665
    return (-g * math.sin(angle), 0.0, g * math.cos(angle))


def check_edge_cases():
    identity = (1.0, 0.0, 0.0, 0.0)
    assert quaternion_normalize((0, 0, 0, 0)) == identity
    q = (math.cos(math.pi / 8), 0.0, math.sin(math.pi / 8), 0.0)
    assert_unit(quaternion_multiply(q, quaternion_conjugate(q)))
    assert abs(relative_flexion_y_rad(quaternion_relative(q, q))) < 1e-12
    # Same parent-frame convention also works when both segments are rotated.
    parent = (math.cos(math.pi / 12), 0.0, math.sin(math.pi / 12), 0.0)
    child = quaternion_multiply(parent, q)
    assert math.isclose(relative_flexion_y_rad(quaternion_relative(parent, child)), math.pi / 4)
    assert math.isclose(relative_flexion_y_rad(quaternion_conjugate(q)), -math.pi / 4)

    gyro_only = MadgwickIMU()
    for _ in range(RATE_HZ):
        gyro_only.update(0, math.pi / 4, 0, 0, 0, 0, 1 / RATE_HZ)
        assert_unit(gyro_only.quaternion)
    assert abs(relative_flexion_y_rad(gyro_only.quaternion) - math.pi / 4) < 1e-4
    # Prove acceleration correction works independently of gyro integration,
    # and that changing accelerometer units leaves the estimate unchanged.
    tilted, scaled = MadgwickIMU(), MadgwickIMU()
    target_angle = math.radians(30)
    accel = ideal_acceleration(target_angle)
    for _ in range(300):
        tilted.update(0, 0, 0, *accel, 1 / RATE_HZ)
        scaled.update(0, 0, 0, *(value / 9.80665 for value in accel), 1 / RATE_HZ)
        assert_unit(tilted.quaternion)
        assert_unit(scaled.quaternion)
    assert abs(relative_flexion_y_rad(tilted.quaternion) - target_angle) < math.radians(0.2)
    assert all(math.isclose(a, b, abs_tol=1e-10)
               for a, b in zip(tilted.quaternion, scaled.quaternion))
    stationary = MadgwickIMU()
    for _ in range(10):
        stationary.update(0, 0, 0, 0, 0, 9.80665, 1 / RATE_HZ)
    assert stationary.quaternion == identity  # Zero gradient must not divide by zero.
    tiny_accel = MadgwickIMU()
    tiny_accel.update(0, 0, 0, 1e-20, 0, 0, 1 / RATE_HZ)
    assert tiny_accel.quaternion == identity
    for values in ((math.nan, 0, 0, 0, 0, 1, 0.01), (0, 0, 0, 0, 0, 1, 0)):
        try:
            stationary.update(*values)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid IMU input was accepted")
        assert stationary.quaternion == identity


def main():
    check_edge_cases()
    thigh, shank = MadgwickIMU(beta=BETA), MadgwickIMU(beta=BETA)
    results = []
    # Include t=0 and t=4. The t=0 update is stationary at identity.
    # Later updates use measurements at each sample endpoint with dt=0.01 s.
    for index in range(int(DURATION_S * RATE_HZ) + 1):
        t = index / RATE_HZ
        true_angle, velocity = ideal_motion(t)
        thigh.update(0, 0, 0, *ideal_acceleration(0), 1 / RATE_HZ)
        shank.update(0, velocity, 0, *ideal_acceleration(true_angle), 1 / RATE_HZ)
        relative = quaternion_relative(thigh.quaternion, shank.quaternion)
        for q in (thigh.quaternion, shank.quaternion, relative):
            assert_unit(q)
        estimated = relative_flexion_y_rad(relative)
        assert math.isfinite(estimated)
        results.append((t, math.degrees(true_angle), math.degrees(estimated)))

    errors = [estimated - true for _, true, estimated in results]
    rmse = math.sqrt(sum(error**2 for error in errors) / len(errors))
    max_error = max(abs(error) for error in errors)
    true_peak = max(row[1] for row in results)
    estimated_peak = max(row[2] for row in results)
    assert rmse < 0.5, f"RMSE too large: {rmse} deg"
    assert max_error < 1.0, f"Maximum error too large: {max_error} deg"
    assert abs(estimated_peak - true_peak) < 1.0, f"Peak mismatch: {estimated_peak} deg"

    print("Synthetic ideal IMU test — not hardware validation.")
    print("\nKintra Madgwick knee test")
    print("-------------------------")
    print(f"Samples: {len(results)}")
    print(f"Sampling rate: {RATE_HZ} Hz")
    print(f"True peak flexion: {true_peak:.2f} deg")
    print(f"Estimated peak flexion: {estimated_peak:.2f} deg")
    print(f"RMSE: {rmse:.3f} deg")
    print(f"Maximum absolute error: {max_error:.3f} deg")
    print("\ntime (s) | true flexion (deg) | estimated flexion (deg) | error (deg)")
    for index in (0, 100, 200, 300, 400):
        t, true, estimated = results[index]
        print(f"{t:8.2f} | {true:18.2f} | {estimated:23.2f} | {estimated - true:+11.3f}")
    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
