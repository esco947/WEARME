"""Canonical pose definitions for WEARME.

Defines the standard fixed poses used throughout the pipeline. All poses are
represented as SMPL pose vectors: shape ``(72,)`` of Rodrigues rotation
parameters (24 joints × 3 floats each).

SMPL joint order (24 joints):
    0: pelvis         6: l_knee        12: neck         18: l_elbow
    1: l_hip          7: r_knee        13: l_collar     19: r_elbow
    2: r_hip          8: l_ankle       14: r_collar     20: l_wrist
    3: spine1         9: r_ankle       15: head         21: r_wrist
    4: l_knee        10: l_foot        16: l_shoulder   22: l_hand
    5: r_knee        11: r_foot        17: r_shoulder   23: r_hand

Usage::

    from wearme.body.canonical_pose import T_POSE, A_POSE
"""

import numpy as np

# ── T-pose ────────────────────────────────────────────────────────────────────

#: Standard T-pose: all joints at zero rotation (identity rotation matrices).
#: Arms extended horizontally, palms facing down.
T_POSE: np.ndarray = np.zeros(72, dtype=np.float64)

# ── A-pose ────────────────────────────────────────────────────────────────────
# A-pose lowers the arms to ~45° from horizontal, making the body look more
# natural and improving cloth draping in simulation.
#
# Joint index 16 = left shoulder,  index 17 = right shoulder
# Each joint occupies pose[joint_idx*3 : joint_idx*3+3].
#
# Rodrigues vector for ~30° rotation around the Z axis (forward axis):
#   left shoulder:  rotate +30° around Z  → arms down-forward
#   right shoulder: rotate -30° around Z  → arms down-forward

_SHOULDER_ANGLE_RAD: float = np.deg2rad(30.0)

_A_POSE_ARRAY: np.ndarray = np.zeros(72, dtype=np.float64)
# Left shoulder  (joint 16): rotate around local Z+
_A_POSE_ARRAY[16 * 3 + 2] = _SHOULDER_ANGLE_RAD
# Right shoulder (joint 17): rotate around local Z- (mirror)
_A_POSE_ARRAY[17 * 3 + 2] = -_SHOULDER_ANGLE_RAD

#: A-pose: arms lowered ~30° from horizontal. Preferred for cloth simulation.
A_POSE: np.ndarray = _A_POSE_ARRAY
