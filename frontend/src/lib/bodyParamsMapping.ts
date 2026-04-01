/**
 * Bidirectional mapping between semantic body parameters (user-facing sliders)
 * and SMPL beta coefficients (PCA components stored in the backend).
 *
 * SMPL beta empirical effects (neutral model):
 *   b[1]  corpulence  — INVERTED: + = mince, - = gros
 *   b[2]  limb length ratio (+ = longer)
 *   b[3]  shoulder width + chest/thorax breadth (+ = wider)
 *   b[4]  hip / pelvis width — INVERTED: - = wider
 *   b[5]  global body volume — INVERTED: - = fuller
 *   b[6]  belly protrusion (+ = rounder stomach)
 *   b[7]  leg thickness + fesses — INVERTED: - = thicker / rounder
 *   b[8]  arm length (secondary)
 *   b[9]  hip width subtle (+ = wider)
 */

import type { BodyParams } from '../types'

const clamp = (v: number, lo = -1, hi = 1) => Math.max(lo, Math.min(hi, v))
const clampBeta = (v: number) => clamp(v, -3.5, 3.5)

/** BMI at reference body (70 kg / 1.75 m²) */
const BMI_REF = 70 / (1.75 * 1.75)  // ≈ 22.86

export function bodyParamsToSmplBetas(p: BodyParams): number[] {
  const b = new Array(10).fill(0)

  // Fatness combines BMI deviation + explicit corpulence slider.
  const bmi     = p.weight_kg / (p.height_m * p.height_m)
  const bmiDev  = (bmi - BMI_REF) / 10   // ~0 for 70 kg/1.75 m, ~+1 for obese
  const fatness = clamp(bmiDev * 1.5 + p.corpulence * 0.8, -2, 2)

  // b[0]: not used for height — backend scales mesh to avatar.height_m
  b[0] = 0

  // b[1]: corpulence (INVERTED: positive = thinner)
  b[1] = -fatness * 3.5
       + p.musculature * 1.2

  // b[2]: limb lengths
  b[2] = p.arm_length * 1.8 + p.leg_length * 1.5

  // b[3]: shoulder breadth + chest/thorax width + musculature
  b[3] = p.shoulder_width * 2.5
       + p.chest * 1.5
       + p.musculature * 1.0

  // b[4]: pelvis width (INVERTED: negative = wider hips/fesses)
  b[4] = -p.hips * 2.0
       - p.fesses * 1.5

  // b[5]: overall body volume (INVERTED: negative = fuller)
  b[5] = -fatness * 1.5
       - p.chest * 0.8

  // b[6]: belly protrusion
  b[6] = p.belly * 3.5
       + fatness * 1.0

  // b[7]: leg thickness + fesses (INVERTED: negative = thicker/rounder)
  b[7] = -p.fesses * 2.5
       - p.leg_shape * 2.0

  // b[8]: arm length secondary
  b[8] = p.arm_length * 1.0

  // b[9]: hip width subtle
  b[9] = p.hips * 1.0 + p.fesses * 0.5

  return b.map(clampBeta)
}

export function smplBetasToBodyParams(
  b: number[],
  height_m: number,
  weight_kg: number,
): BodyParams {
  const safe = (i: number) => b[i] ?? 0
  return {
    height_m,
    weight_kg,
    corpulence:     clamp(-safe(1) * 0.20 - safe(5) * 0.15),
    musculature:    clamp( safe(1) * 0.15 + safe(3) * 0.10),
    shoulder_width: clamp( safe(3) * 0.25),
    chest:          clamp( safe(3) * 0.20 - safe(5) * 0.15),
    belly:          clamp( safe(6) * 0.20),
    hips:           clamp(-safe(4) * 0.25 + safe(9) * 0.30),
    fesses:         clamp(-safe(7) * 0.25 - safe(4) * 0.15),
    arm_length:     clamp( safe(2) * 0.30 + safe(8) * 0.40),
    leg_length:     clamp( safe(2) * 0.35),
    leg_shape:      clamp(-safe(7) * 0.20),
  }
}

/**
 * Map the 12 semantic sliders to a subset of the 55 anatomical params.
 * This bridges the legacy BodyParams UI to the Phase-2 backend body_data system.
 *
 * Reference body: 1.75 m / 70 kg / neutral SMPL defaults.
 */
const clampParam = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

export function bodyParamsToAnatomical(p: BodyParams): Record<string, number> {
  const h = p.height_m
  const w = p.weight_kg
  const hRatio = h / 1.75   // scale length params proportionally with height

  // BMI-driven fatness
  const bmi    = w / (h * h)
  const bmiDev = (bmi - 22.86) / 10
  const fat    = Math.max(-2, Math.min(2, bmiDev * 1.5 + p.corpulence * 0.8))

  return {
    height_m:         h,
    weight_kg:        w,
    chest_circ_m:     clampParam(0.945 * hRatio + fat * 0.04 + p.chest * 0.05,          0.70, 1.50),
    underbust_circ_m: clampParam(0.858 * hRatio + fat * 0.03,                            0.60, 1.30),
    waist_circ_m:     clampParam(0.785 * hRatio + fat * 0.05 + p.belly * 0.025,          0.55, 1.40),
    abdomen_circ_m:   clampParam(0.855 * hRatio + fat * 0.06 + p.belly * 0.04,          0.60, 1.50),
    hip_circ_m:       clampParam(0.980 * hRatio + fat * 0.03 + p.hips * 0.05,           0.75, 1.50),
    mid_hip_circ_m:   clampParam(0.925 * hRatio + fat * 0.025 + p.hips * 0.03,          0.70, 1.40),
    shoulder_width_m: clampParam(0.393          + p.shoulder_width * 0.05,              0.30, 0.60),
    arm_length_m:     clampParam(0.595 * hRatio + p.arm_length * 0.05,                  0.50, 0.90),
    inseam_m:         clampParam(0.778 * hRatio + p.leg_length * 0.05,                  0.60, 1.00),
    thigh_circ_m:     clampParam(0.573          + fat * 0.02 + p.leg_shape * 0.03
                                              + p.fesses * 0.02,                        0.40, 0.85),
    upper_arm_circ_m: clampParam(0.320          + fat * 0.01 + p.musculature * 0.015,   0.20, 0.55),
    shoulder_height_m:clampParam(1.390 * hRatio,                                        1.10, 1.85),
    waist_height_m:   clampParam(1.038 * hRatio,                                        0.85, 1.45),
  }
}

export const DEFAULT_BODY_PARAMS: BodyParams = {
  height_m:       1.75,
  weight_kg:      70,
  corpulence:     0,
  musculature:    0,
  shoulder_width: 0,
  chest:          0,
  belly:          0,
  hips:           0,
  fesses:         0,
  arm_length:     0,
  leg_length:     0,
  leg_shape:      0,
}
