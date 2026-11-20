#!/usr/bin/env python3
"""EPISODE1 kinematics: official DH model, FK, Jacobian and numerical IK.

Units: millimetres and radians.  The model is the official one published in
`enpeizhao/episode_robot/episodeServer.py`; it is NOT derived from the STEP
mesh.  See docs/KINEMATICS.md for the zero-pose convention.

No third-party dependency beyond numpy.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

# Official ratios and joint ranges (motor side, degrees).
MOTOR_RATIOS = (25.0, 20.0, 25.0, 10.0, 4.0, 1.0)
MOTOR_RANGES_DEG = ((0.0, 340.0), (0.0, 180.0), (0.0, 163.0),
                    (0.0, 335.0), (0.0, 220.0), (0.0, 335.0))

# Official DH table: (d_mm, a_mm, alpha_rad).  theta is the joint variable.
DH_TABLE = (
    (166.0, 55.0, math.pi / 2.0),
    (0.0, 200.0, 0.0),
    (0.0, 56.0, math.pi / 2.0),
    (192.0, 0.0, -math.pi / 2.0),
    (0.0, 0.0, math.pi / 2.0),
    (55.0, 0.0, 0.0),
)

# Official host-side DH limits (degrees).
Q_LIMITS_DEG = ((-180.0, 140.0), (0.0, 180.0), (-80.0, 83.0),
                (-30.0, 270.0), (-110.0, 110.0), (-30.0, 290.0))

# Official motor->DH zero mapping.  m is the motor-side angle in degrees.
MOTOR_TO_Q_SIGN = (1.0, -1.0, -1.0, 1.0, -1.0, 1.0)
MOTOR_TO_Q_OFFSET_DEG = (-180.0, 180.0, 83.0, -30.0, 110.0, -30.0)


def deg(x: float) -> float:
    return math.radians(x)


def wrap_deg(x: float) -> float:
    """Wrap to [-180, 180)."""
    return (x + 180.0) % 360.0 - 180.0


def dh_transform(theta: float, d: float, a: float, alpha: float) -> np.ndarray:
    """Standard DH transform Rz(theta) Tz(d) Tx(a) Rx(alpha)."""
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array([
        [ct, -st * ca,  st * sa, a * ct],
        [st,  ct * ca, -ct * sa, a * st],
        [0.0,       sa,       ca,      d],
        [0.0,      0.0,      0.0,    1.0],
    ], dtype=float)


def motor_to_q(motor_deg: Sequence[float]) -> np.ndarray:
    """Convert official motor angles (degrees) to DH joint angles (radians)."""
    m = np.asarray(motor_deg, dtype=float)
    if m.shape != (6,):
        raise ValueError("need 6 motor angles")
    q = np.array([s * x + o for s, x, o in
                  zip(MOTOR_TO_Q_SIGN, m, MOTOR_TO_Q_OFFSET_DEG)], dtype=float)
    return np.deg2rad(q)


def q_to_motor(q_rad: Sequence[float]) -> np.ndarray:
    """Convert DH joint angles (radians) to official motor angles (degrees)."""
    q = np.rad2deg(np.asarray(q_rad, dtype=float))
    if q.shape != (6,):
        raise ValueError("need 6 joint angles")
    return np.array([(x - o) / s for s, x, o in
                     zip(MOTOR_TO_Q_SIGN, q, MOTOR_TO_Q_OFFSET_DEG)], dtype=float)


def fk(q_rad: Sequence[float], tool_offset_mm: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Forward kinematics; returns 4x4 base->tool transform."""
    q = np.asarray(q_rad, dtype=float)
    if q.shape != (6,):
        raise ValueError("need 6 joint angles")
    T = np.eye(4)
    for theta, (d, a, alpha) in zip(q, DH_TABLE):
        T = T @ dh_transform(float(theta), d, a, alpha)
    off = np.asarray(tool_offset_mm, dtype=float)
    if off.shape != (3,):
        raise ValueError("tool_offset_mm must have 3 elements")
    if np.any(off):
        T = T @ np.array([[1, 0, 0, off[0]], [0, 1, 0, off[1]],
                          [0, 0, 1, off[2]], [0, 0, 0, 1]], dtype=float)
    return T


def joint_axes(q_rad: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Return joint origins (6,3) and joint axes (6,3) in the base frame."""
    q = np.asarray(q_rad, dtype=float)
    T = np.eye(4)
    origins, axes = [], []
    for theta, (d, a, alpha) in zip(q, DH_TABLE):
        origins.append(T[:3, 3].copy())
        axes.append(T[:3, 2].copy())
        T = T @ dh_transform(float(theta), d, a, alpha)
    return np.asarray(origins), np.asarray(axes)


def jacobian(q_rad: Sequence[float], tool_offset_mm: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Geometric Jacobian (6x6), linear part in mm/rad."""
    q = np.asarray(q_rad, dtype=float)
    origins, axes = joint_axes(q)
    p = fk(q, tool_offset_mm)[:3, 3]
    J = np.zeros((6, 6), dtype=float)
    for i in range(6):
        J[:3, i] = np.cross(axes[i], p - origins[i])
        J[3:, i] = axes[i]
    return J


def rotation_vector(R: np.ndarray) -> np.ndarray:
    """SO(3) -> rotation vector (axis * angle)."""
    R = np.asarray(R, dtype=float)
    c = (np.trace(R) - 1.0) / 2.0
    c = float(np.clip(c, -1.0, 1.0))
    theta = math.acos(c)
    if theta < 1e-8:
        return 0.5 * np.array([R[2, 1] - R[1, 2],
                               R[0, 2] - R[2, 0],
                               R[1, 0] - R[0, 1]])
    if abs(math.pi - theta) < 1e-5:
        # Near pi: use the symmetric part to recover the axis.
        A = (R + np.eye(3)) / 2.0
        axis = np.sqrt(np.maximum(np.diag(A), 0.0))
        # Fix signs using the largest off-diagonal entry.
        i = int(np.argmax(axis))
        if axis[i] > 0:
            axis = np.sign(A[i, :]) * axis
        n = np.linalg.norm(axis)
        if n < 1e-12:
            return np.zeros(3)
        return axis / n * theta
    return (theta / (2.0 * math.sin(theta))) * np.array(
        [R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])


@dataclass
class IKResult:
    q: np.ndarray
    position_error_mm: float
    rotation_error_deg: float
    success: bool
    iterations: int
    restarts: int = 0

    def as_dict(self) -> dict:
        return {
            "q_rad": [float(x) for x in self.q],
            "q_deg": [float(math.degrees(x)) for x in self.q],
            "motor_deg": [float(x) for x in q_to_motor(self.q)],
            "position_error_mm": self.position_error_mm,
            "rotation_error_deg": self.rotation_error_deg,
            "success": bool(self.success),
            "iterations": int(self.iterations),
            "restarts": int(self.restarts),
        }


def pose_error(target: np.ndarray, current: np.ndarray) -> np.ndarray:
    """6-vector [position_error_mm, rotation_vector_rad]."""
    ep = target[:3, 3] - current[:3, 3]
    er = rotation_vector(target[:3, :3] @ current[:3, :3].T)
    return np.concatenate([ep, er])


def ik(target: np.ndarray, q0: Sequence[float] | None = None, *,
       q_limits_deg: Sequence[Sequence[float]] = Q_LIMITS_DEG,
       tool_offset_mm: Sequence[float] = (0.0, 0.0, 0.0),
       position_tol_mm: float = 1.0, rotation_tol_deg: float = 1.0,
       max_iter: int = 300, restarts: int = 8,
       damping: float = 8.0, seed: int = 0) -> IKResult:
    """Damped least-squares IK with joint limits and deterministic restarts.

    The error is 6D (position mm + rotation vector rad).  A solution is
    accepted only when both tolerances are met.
    """
    target = np.asarray(target, dtype=float)
    if target.shape != (4, 4):
        raise ValueError("target must be 4x4")
    lo = np.deg2rad(np.asarray(q_limits_deg, dtype=float)[:, 0])
    hi = np.deg2rad(np.asarray(q_limits_deg, dtype=float)[:, 1])
    rng = np.random.default_rng(seed)

    candidates = []
    if q0 is not None:
        candidates.append(np.clip(np.asarray(q0, dtype=float), lo, hi))
    # Deterministic starts: middle, plus uniform samples inside the limits.
    candidates.append((lo + hi) / 2.0)
    for _ in range(max(0, restarts)):
        candidates.append(lo + (hi - lo) * rng.random(6))

    best: IKResult | None = None
    for restart_idx, start in enumerate(candidates):
        q = start.copy()
        it_done = 0
        for it in range(1, max_iter + 1):
            T = fk(q, tool_offset_mm)
            e = pose_error(target, T)
            pe = float(np.linalg.norm(e[:3]))
            re = float(np.linalg.norm(e[3:]))
            if pe <= position_tol_mm and math.degrees(re) <= rotation_tol_deg:
                it_done = it - 1
                break
            J = jacobian(q, tool_offset_mm)
            # Reduce rotation rows to comparable scale (mm vs rad).
            W = np.diag([1.0, 1.0, 1.0, 30.0, 30.0, 30.0])
            Jw = W @ J
            ew = W @ e
            A = Jw.T @ Jw + (damping ** 2) * np.eye(6)
            dq = np.linalg.solve(A, Jw.T @ ew)
            # Limit step size for stability.
            step = float(np.linalg.norm(dq))
            if step > 0.5:
                dq *= 0.5 / step
            q = np.clip(q + dq, lo, hi)
            it_done = it
        T = fk(q, tool_offset_mm)
        e = pose_error(target, T)
        pe = float(np.linalg.norm(e[:3]))
        re = float(math.degrees(np.linalg.norm(e[3:])))
        res = IKResult(q=q, position_error_mm=pe, rotation_error_deg=re,
                       success=(pe <= position_tol_mm and re <= rotation_tol_deg),
                       iterations=it_done, restarts=restart_idx)
        if best is None or (pe + 10.0 * re) < (best.position_error_mm + 10.0 * best.rotation_error_deg):
            best = res
        if res.success:
            return res
    assert best is not None
    return best


def _rpy_matrix(rpy_deg: Sequence[float]) -> np.ndarray:
    """URDF-style fixed-axis RPY (degrees): Rz(yaw) Ry(pitch) Rx(roll)."""
    r, p, y = (math.radians(v) for v in rpy_deg)
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def parse_vec(text: str) -> list[float]:
    return [float(x) for x in text.replace(",", " ").split()]


def _cli() -> int:
    ap = argparse.ArgumentParser(description="EPISODE1 FK/IK (mm, deg)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_fk = sub.add_parser("fk", help="forward kinematics")
    p_fk.add_argument("--q-deg", required=True, help='six DH angles, e.g. "0 90 0 0 0 0"')
    p_fk.add_argument("--tool", default="0 0 0", help="tool offset in frame 6, mm")

    p_ik = sub.add_parser("ik", help="inverse kinematics")
    p_ik.add_argument("--xyz", required=True, help="target x y z, mm")
    p_ik.add_argument("--rpy-deg", default="0 0 0", help="target RPY, deg")
    p_ik.add_argument("--q0-deg", default=None, help="seed joint angles, deg")
    p_ik.add_argument("--tool", default="0 0 0")
    p_ik.add_argument("--pos-tol", type=float, default=1.0)
    p_ik.add_argument("--rot-tol", type=float, default=1.0)

    p_map = sub.add_parser("map", help="convert official motor angles <-> DH q")
    p_map.add_argument("--motor-deg", default=None)
    p_map.add_argument("--q-deg", default=None)

    a = ap.parse_args()
    if a.cmd == "fk":
        q = np.deg2rad(parse_vec(a.q_deg))
        T = fk(q, parse_vec(a.tool))
        print(json.dumps({
            "xyz_mm": [round(float(x), 4) for x in T[:3, 3]],
            "rpy_deg": [round(float(x), 4) for x in
                        np.rad2deg([math.atan2(T[2, 1], T[2, 2]),
                                    math.asin(float(np.clip(-T[2, 0], -1, 1))),
                                    math.atan2(T[1, 0], T[0, 0])])],
            "T": [[round(float(x), 6) for x in row] for row in T],
        }, ensure_ascii=False, indent=2))
        return 0
    if a.cmd == "ik":
        xyz = parse_vec(a.xyz)
        T = np.eye(4)
        T[:3, :3] = _rpy_matrix(parse_vec(a.rpy_deg))
        T[:3, 3] = xyz
        q0 = None if a.q0_deg is None else np.deg2rad(parse_vec(a.q0_deg))
        res = ik(T, q0, tool_offset_mm=parse_vec(a.tool),
                 position_tol_mm=a.pos_tol, rotation_tol_deg=a.rot_tol)
        print(json.dumps(res.as_dict(), ensure_ascii=False, indent=2))
        return 0 if res.success else 1
    if a.cmd == "map":
        if a.motor_deg is not None:
            q = motor_to_q(parse_vec(a.motor_deg))
            print(json.dumps({"q_deg": [float(math.degrees(x)) for x in q]}, indent=2))
        elif a.q_deg is not None:
            m = q_to_motor(np.deg2rad(parse_vec(a.q_deg)))
            print(json.dumps({"motor_deg": [float(x) for x in m]}, indent=2))
        else:
            ap.error("map needs --motor-deg or --q-deg")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
