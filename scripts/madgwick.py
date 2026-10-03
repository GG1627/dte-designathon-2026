"""Minimal 6-DOF Madgwick IMU filter (stdlib only).

Right-handed frame: X forward, Y left (left/right axis), Z up.
Hamilton quaternions (w, x, y, z) rotate sensor vectors into world coordinates:
q * (0, vector_sensor) * conjugate(q). Positive test flexion rotates about +Y.
Accelerometer input is specific force: at rest it points up, opposite physical
world gravity (0, 0, -g). The correction reference is therefore world +Z.
Yaw has no absolute reference in this accelerometer/gyroscope-only filter.

Gradient-descent formulation: Madgwick's original IMU report, Appendix A:
https://x-io.co.uk/downloads/madgwick_internal_report.pdf
"""
import math

EPSILON = 1e-12
IDENTITY = (1.0, 0.0, 0.0, 0.0)


def quaternion_multiply(q1, q2):
    """Hamilton product; q1 * q2 applies q2's rotation, then q1's."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def quaternion_conjugate(q):
    w, x, y, z = q
    return (w, -x, -y, -z)


def quaternion_normalize(q):
    """Return a unit quaternion; a near-zero quaternion falls back to identity.

    Nonfinite values raise ValueError rather than silently propagating NaNs.
    """
    if len(q) != 4 or not all(math.isfinite(value) for value in q):
        raise ValueError("Quaternion must contain four finite values")
    magnitude = math.hypot(*q)
    if not math.isfinite(magnitude):
        raise ValueError("Quaternion magnitude is not finite")
    return tuple(value / magnitude for value in q) if magnitude > EPSILON else IDENTITY


def quaternion_relative(q_parent, q_child):
    """Child-to-parent rotation: conjugate(parent_world) * child_world.

    quaternion_relative(q_thigh, q_shank) maps shank vectors into the thigh
    frame, describing the shank orientation relative to the thigh.
    """
    parent = quaternion_normalize(q_parent)
    child = quaternion_normalize(q_child)
    return quaternion_normalize(quaternion_multiply(quaternion_conjugate(parent), child))


def relative_flexion_y_rad(q_relative):
    """Signed Y pitch for the simple sagittal-plane test, in [-pi/2, pi/2].

    Uses Z-Y-X Euler pitch; not a general anatomical joint-angle decomposition.
    """
    w, x, y, z = quaternion_normalize(q_relative)
    return math.asin(max(-1.0, min(1.0, 2.0 * (w*y - z*x))))


class MadgwickIMU:
    def __init__(self, beta=0.1):
        if not math.isfinite(beta) or beta < 0:
            raise ValueError("beta must be finite and nonnegative")
        self.beta = beta
        self._quaternion = IDENTITY

    @property
    def quaternion(self):
        """Unit sensor-to-world orientation as (w, x, y, z)."""
        return self._quaternion

    def update(self, gx, gy, gz, ax, ay, az, dt):
        """Integrate rad/s gyro with normalized acceleration correction.

        dt must be positive seconds. Effectively zero acceleration or correction
        gradient skips correction; invalid inputs raise before changing state.
        """
        if not all(math.isfinite(value) for value in (gx, gy, gz, ax, ay, az, dt)) or dt <= 0:
            raise ValueError("IMU inputs must be finite and dt must be positive")
        w, x, y, z = self._quaternion
        derivative = [value * 0.5 for value in
                      quaternion_multiply(self._quaternion, (0.0, gx, gy, gz))]
        magnitude = math.hypot(ax, ay, az)
        if not math.isfinite(magnitude):
            raise ValueError("Accelerometer magnitude is not finite")
        if magnitude > EPSILON:
            ax, ay, az = ax / magnitude, ay / magnitude, az / magnitude
            # Residual between predicted world +Z in sensor frame and measured accel.
            fx = 2.0 * (x*z - w*y) - ax
            fy = 2.0 * (w*x + y*z) - ay
            fz = 1.0 - 2.0 * (x*x + y*y) - az
            # Jacobian-transpose times residual: normalized descent direction.
            gradient = (
                -2.0*y*fx + 2.0*x*fy,
                2.0*z*fx + 2.0*w*fy - 4.0*x*fz,
                -2.0*w*fx + 2.0*z*fy - 4.0*y*fz,
                2.0*x*fx + 2.0*y*fy,
            )
            gradient_norm = math.hypot(*gradient)
            if gradient_norm > EPSILON:
                derivative = [rate - self.beta * step / gradient_norm
                              for rate, step in zip(derivative, gradient)]
        self._quaternion = quaternion_normalize(
            tuple(value + rate * dt for value, rate in zip(self._quaternion, derivative))
        )
        return self._quaternion
