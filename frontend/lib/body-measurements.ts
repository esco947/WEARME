// Browser-only — do NOT import in Server Components
import type { PoseLandmarkerResult, NormalizedLandmark, Landmark } from './pose';
import { getMaskWidthAtY, maskCoverageInZone } from './silhouette-analysis';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------
export interface BodyMeasurements {
  taille: number;
  poids: number;
  epaules: number;
  poitrine: number;
  tour_taille: number;
  hanches: number;
  longueur_jambes: number;
  forme_jambes: number;   // -3..+3
  longueur_bras: number;
  forme_bras: number;     // -3..+3
  cou: number;            // -3..+3
  posture: number;        // -3..+3
}

export interface MeasurementConfidence {
  epaules: number;
  poitrine: number;
  tour_taille: number;
  hanches: number;
  longueur_jambes: number;
  longueur_bras: number;
  forme_jambes: number;
  forme_bras: number;
  cou: number;
  posture: number;
}

export interface ExtractionResult {
  measurements: BodyMeasurements;
  confidence: MeasurementConfidence;
  /** Incohérences anatomiques détectées (informatives, n'empêchent pas l'utilisation) */
  anatomicalWarnings: string[];
}

// ---------------------------------------------------------------------------
// Math helpers
// ---------------------------------------------------------------------------
function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function avg(...vals: number[]): number {
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function dist3D(a: Landmark, b: Landmark): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2);
}

/** Ramanujan ellipse circumference. a = half-width, b = half-depth (cm). */
function ellipseCircumference(a: number, b: number): number {
  if (a <= 0 || b <= 0) return 0;
  const h = ((a - b) / (a + b)) ** 2;
  return Math.PI * (a + b) * (1 + (3 * h) / (10 + Math.sqrt(4 - 3 * h)));
}

// ---------------------------------------------------------------------------
// Mask helpers
// ---------------------------------------------------------------------------
interface MaskLike {
  width: number;
  height: number;
  getAsFloat32Array(): Float32Array;
}

// getMaskWidthAtY and maskCoverageInZone are imported from silhouette-analysis.ts
// They replace the old getConstrainedWidth / maskCoverage implementations.
// Key improvements:
//   - getMaskWidthAtY sums ALL body pixels (not just longest contiguous run)
//   - Médiane sur 5 lignes adjacentes → robuste aux artefacts locaux (ombres, coutures)

// ---------------------------------------------------------------------------
// Calibration
// ---------------------------------------------------------------------------
/**
 * Returns two scale factors:
 *   pxY: cm per mask-pixel in the vertical direction (from body height)
 *   pxX: cm per mask-pixel in the horizontal direction (calibrated from
 *        the known shoulder width and the landmark horizontal span)
 */
function computeScales(
  lm: NormalizedLandmark[],
  fWLm: Landmark[],
  maskW: number,
  maskH: number,
  heightCm: number,
  worldScale: number,
): { pxY: number; pxX: number } {
  const headTopY = lm[0].y - 0.08;
  const ankleY   = avg(lm[27].y, lm[28].y);
  const bodyHNorm = ankleY - headTopY;

  const pxY = bodyHNorm > 0.05 ? heightCm / (bodyHNorm * maskH) : 1;

  // Horizontal calibration: use world-landmark shoulder width anchored in image x
  const shoulderCm   = dist3D(fWLm[11], fWLm[12]) * 100 * worldScale;
  const shoulderNormX = Math.abs(lm[12].x - lm[11].x);
  const shoulderMaskPx = shoulderNormX * maskW;
  const pxX = shoulderMaskPx > 5 && shoulderCm > 5
    ? shoulderCm / shoulderMaskPx
    : pxY; // fallback: assume square pixels

  return { pxY, pxX };
}

// ---------------------------------------------------------------------------
// Main extraction
// ---------------------------------------------------------------------------
export function extractAllMeasurements(
  frontResult: PoseLandmarkerResult,
  profileResult: PoseLandmarkerResult,
  heightCm: number,
  weightKg: number,
  gender: string,
): ExtractionResult {
  const fLm  = frontResult.landmarks[0];
  const fWLm = frontResult.worldLandmarks[0];
  const pLm  = profileResult.landmarks[0];
  const pWLm = profileResult.worldLandmarks[0];

  const def = defaultResult(heightCm, weightKg, gender);
  if (!fLm || fLm.length < 29 || !fWLm) return def;

  // ── World scale calibration ─────────────────────────────────────────────
  const wHeadY  = fWLm[0].y + 0.10;
  const wAnkleY = avg(fWLm[27].y, fWLm[28].y);
  const wBodyH  = wHeadY - wAnkleY;
  const worldScale = wBodyH > 0.3 ? heightCm / (wBodyH * 100) : 1;

  // ── Shoulder width from world landmarks (biacromial) ────────────────────
  const shoulderWidthCm = dist3D(fWLm[11], fWLm[12]) * 100 * worldScale;
  const confEpaules = Math.min(
    fLm[11].visibility ?? 0,
    fLm[12].visibility ?? 0,
  );

  // ── Limb lengths from world landmarks ───────────────────────────────────
  const leftArmCm  = (dist3D(fWLm[11], fWLm[13]) + dist3D(fWLm[13], fWLm[15])) * 100 * worldScale;
  const rightArmCm = (dist3D(fWLm[12], fWLm[14]) + dist3D(fWLm[14], fWLm[16])) * 100 * worldScale;
  const armLengthCm = avg(leftArmCm, rightArmCm);
  const confArm = Math.min(
    fLm[11].visibility ?? 0, fLm[15].visibility ?? 0,
    fLm[12].visibility ?? 0, fLm[16].visibility ?? 0,
  );

  const leftLegCm  = (dist3D(fWLm[23], fWLm[25]) + dist3D(fWLm[25], fWLm[27])) * 100 * worldScale;
  const rightLegCm = (dist3D(fWLm[24], fWLm[26]) + dist3D(fWLm[26], fWLm[28])) * 100 * worldScale;
  const legLengthCm = avg(leftLegCm, rightLegCm);
  const confLeg = Math.min(
    fLm[23].visibility ?? 0, fLm[27].visibility ?? 0,
    fLm[24].visibility ?? 0, fLm[28].visibility ?? 0,
  );

  // ── Y positions (normalised image coords) ────────────────────────────────
  const headTopY = fLm[0].y - 0.08;
  const shY   = avg(fLm[11].y, fLm[12].y);
  const hipY  = avg(fLm[23].y, fLm[24].y);
  const knY   = avg(fLm[25].y, fLm[26].y);
  const elY   = avg(fLm[13].y, fLm[14].y);
  const ankY  = avg(fLm[27].y, fLm[28].y);

  const chestY  = shY  + (hipY - shY) * 0.22;
  const waistY  = shY  + (hipY - shY) * 0.58;
  const hipMeasY = hipY + (hipY - shY) * 0.04;
  const thighY  = hipY + (knY  - hipY) * 0.38;
  const uArmY   = shY  + (elY  - shY) * 0.40;
  const neckY   = shY  - (hipY - shY) * 0.14;

  // ── X boundaries for constrained scans ──────────────────────────────────
  // Key idea: scan ONLY between the relevant landmarks so arms / opposite leg
  // are never included in the measurement.
  const lShX = Math.min(fLm[11].x, fLm[12].x); // left-most shoulder
  const rShX = Math.max(fLm[11].x, fLm[12].x); // right-most shoulder
  const lHiX = Math.min(fLm[23].x, fLm[24].x);
  const rHiX = Math.max(fLm[23].x, fLm[24].x);

  const PAD_TORSO = 0.025; // ~2.5% of image width (flesh beyond joint)
  const PAD_HIP   = 0.040; // hips can extend beyond the landmark
  const PAD_LIMB  = 0.055; // radius around each limb landmark

  // ── Front segmentation mask ──────────────────────────────────────────────
  const fMaskRaw = frontResult.segmentationMasks?.[0] as MaskLike | undefined;
  let frontMaskQ = 0;

  // Sensible fallback: use anthropometric proportions of shoulder width
  let chestWCm  = shoulderWidthCm * 0.88;
  let waistWCm  = shoulderWidthCm * 0.70;
  let hipWCm    = shoulderWidthCm * 0.93;
  let thighWCm  = shoulderWidthCm * 0.23;
  let uArmWCm   = shoulderWidthCm * 0.13;
  let neckWCm   = shoulderWidthCm * 0.11;

  if (fMaskRaw) {
    try {
      const fData  = fMaskRaw.getAsFloat32Array();
      const fMaskW = fMaskRaw.width;
      const fMaskH = fMaskRaw.height;
      const { pxX } = computeScales(fLm, fWLm, fMaskW, fMaskH, heightCm, worldScale);

      // Torso: constrained between shoulders (chest/waist) or hips
      // getMaskWidthAtY prend yNorm directement (pas yPixel) et utilise la médiane sur 5 lignes
      const cWPx = getMaskWidthAtY(fData, fMaskW, fMaskH, chestY,   lShX - PAD_TORSO, rShX + PAD_TORSO);
      const wWPx = getMaskWidthAtY(fData, fMaskW, fMaskH, waistY,   lShX - PAD_TORSO, rShX + PAD_TORSO);
      const hWPx = getMaskWidthAtY(fData, fMaskW, fMaskH, hipMeasY, lHiX - PAD_HIP,   rHiX + PAD_HIP);
      // Neck: narrow band around neck centre
      const neckCX = avg(fLm[11].x, fLm[12].x); // midpoint between shoulders
      const nWPx = getMaskWidthAtY(fData, fMaskW, fMaskH, neckY, neckCX - PAD_LIMB * 0.8, neckCX + PAD_LIMB * 0.8);

      // Each thigh individually, centred on the knee landmark x
      const lThCX = fLm[25].x;
      const rThCX = fLm[26].x;
      const lThPx = getMaskWidthAtY(fData, fMaskW, fMaskH, thighY, lThCX - PAD_LIMB, lThCX + PAD_LIMB);
      const rThPx = getMaskWidthAtY(fData, fMaskW, fMaskH, thighY, rThCX - PAD_LIMB, rThCX + PAD_LIMB);

      // Each upper-arm individually, centred on the elbow landmark x
      const lElCX = fLm[13].x;
      const rElCX = fLm[14].x;
      const lArmPx = getMaskWidthAtY(fData, fMaskW, fMaskH, uArmY, lElCX - PAD_LIMB * 0.6, lElCX + PAD_LIMB * 0.6);
      const rArmPx = getMaskWidthAtY(fData, fMaskW, fMaskH, uArmY, rElCX - PAD_LIMB * 0.6, rElCX + PAD_LIMB * 0.6);

      // Accept mask values only when plausible (> a few pixels each)
      const torsoOk = cWPx > 6 && wWPx > 4 && hWPx > 4;
      const limbsOk = (lThPx + rThPx) > 4 && (lArmPx + rArmPx) > 2;

      if (torsoOk) {
        chestWCm = cWPx * pxX;
        waistWCm = wWPx * pxX;
        hipWCm   = hWPx * pxX;
        if (nWPx > 2) neckWCm = nWPx * pxX;
      }
      if (limbsOk) {
        thighWCm = avg(lThPx, rThPx) * pxX;
        uArmWCm  = avg(lArmPx, rArmPx) * pxX;
      }

      frontMaskQ = maskCoverageInZone(fData, fMaskW, fMaskH, 0, 1, headTopY + 0.05, ankY - 0.03);
    } catch {
      // Silently keep landmark-based fallbacks
    }
  }

  // ── Profile segmentation mask (depths) ───────────────────────────────────
  const pMaskRaw = profileResult.segmentationMasks?.[0] as MaskLike | undefined;
  let profileMaskQ = 0;

  // Depth fallback ratios (anatomically plausible)
  let chestDCm = chestWCm * 0.52;
  let waistDCm = waistWCm * 0.88;
  let hipDCm   = hipWCm   * 0.63;

  if (pLm && pLm.length >= 29 && pMaskRaw) {
    try {
      const pData  = pMaskRaw.getAsFloat32Array();
      const pMaskW = pMaskRaw.width;
      const pMaskH = pMaskRaw.height;

      const pHeadTopY = pLm[0].y - 0.08;
      const pAnkleY   = avg(pLm[27].y, pLm[28].y);
      const pBodyHN   = pAnkleY - pHeadTopY;

      if (pBodyHN > 0.15) {
        // Scale vertical (cm par pixel masque en Y)
        const pScaleY = heightCm / (pBodyHN * pMaskH);
        // Scale horizontal (cm par pixel masque en X) — correction aspect ratio
        // BUG CORRIGÉ : l'ancienne implémentation utilisait pScaleY pour les mesures
        // horizontales, ce qui était incorrect si l'image n'était pas carrée.
        // pMaskH/pMaskW corrige l'anisotropie du masque.
        const pScaleX = pScaleY * (pMaskH / pMaskW);

        const pShY  = avg(pLm[11].y, pLm[12].y);
        const pHipY = avg(pLm[23].y, pLm[24].y);
        const pChY  = pShY + (pHipY - pShY) * 0.22;
        const pWaY  = pShY + (pHipY - pShY) * 0.58;
        const pHiY  = pHipY + (pHipY - pShY) * 0.04;

        // In profile, use a centred window to avoid forward-arm contamination.
        const midX  = avg(pLm[11].x, pLm[12].x, pLm[23].x, pLm[24].x);
        const depthWindow = 0.25; // ±25% around body centre in x
        const cDPx = getMaskWidthAtY(pData, pMaskW, pMaskH, pChY, midX - depthWindow, midX + depthWindow);
        const wDPx = getMaskWidthAtY(pData, pMaskW, pMaskH, pWaY, midX - depthWindow, midX + depthWindow);
        const hDPx = getMaskWidthAtY(pData, pMaskW, pMaskH, pHiY, midX - depthWindow, midX + depthWindow);

        // Physiological sanity caps: depth ≤ 75% of corresponding front width
        const saneCap = (depthCm: number, frontWidthCm: number) =>
          Math.min(depthCm, frontWidthCm * 0.75);

        if (cDPx > 3 && wDPx > 3 && hDPx > 3) {
          chestDCm = saneCap(cDPx * pScaleX, chestWCm);
          waistDCm = saneCap(wDPx * pScaleX, waistWCm);
          hipDCm   = saneCap(hDPx * pScaleX, hipWCm);

          profileMaskQ = maskCoverageInZone(pData, pMaskW, pMaskH, 0, 1, pHeadTopY + 0.05, pAnkleY - 0.03);
        }
      }
    } catch {
      // Keep ratio-based depths
    }
  }

  // ── Circumferences (Ramanujan ellipse) ────────────────────────────────────
  const bmi      = weightKg / (heightCm / 100) ** 2;

  // Apply a small BMI-based correction to depth estimates (heavier → rounder section)
  const bmiRound = 1 + clamp((bmi - 22) / 60, -0.1, 0.2); // ±10-20% adjustment
  const poitrineRaw   = ellipseCircumference(chestWCm / 2, chestDCm * bmiRound / 2);
  const tour_tailleRaw = ellipseCircumference(waistWCm / 2, waistDCm * bmiRound / 2);
  const hancheRaw     = ellipseCircumference(hipWCm   / 2, hipDCm   * bmiRound / 2);

  const poitrine   = clamp(poitrineRaw,    60, 145);
  const tour_taille = clamp(tour_tailleRaw, 55, 140);
  const hanches    = clamp(hancheRaw,       70, 145);

  // ── Form parameters ───────────────────────────────────────────────────────
  // BMI signal: neutral at BMI 22, ±1 std ≈ ±5 BMI points → scale ≈ 0.4 per unit
  const bmiDelta   = bmi - 22;
  const bmiFormJam = clamp(bmiDelta * 0.30, -2.5, 2.5);
  const bmiFormBras = clamp(bmiDelta * 0.25, -2.5, 2.5);
  const bmiCou     = clamp(bmiDelta * 0.22, -2.0, 2.0);

  // Mask-based ratios (less reliable, blended only when mask quality is good)
  const maskWeight = clamp(frontMaskQ * 1.5, 0, 0.65); // cap at 65% mask influence
  const bmiWeight  = 1 - maskWeight;

  // Thigh: ratio of thigh width to body height (ref ~0.135 for neutral/BMI 22)
  const thighRatio    = thighWCm / heightCm;
  const maskFormJam   = clamp((thighRatio - 0.135) / 0.025, -3, 3);
  const forme_jambes  = clamp(maskWeight * maskFormJam + bmiWeight * bmiFormJam, -3, 3);

  // Upper arm: ratio (ref ~0.065 for neutral/BMI 22)
  const armRatio    = uArmWCm / heightCm;
  const maskFormBras = clamp((armRatio - 0.065) / 0.012, -3, 3);
  const forme_bras   = clamp(maskWeight * maskFormBras + bmiWeight * bmiFormBras, -3, 3);

  // Neck: ratio (ref ~0.042 for neutral/BMI 22)
  const neckRatio = neckWCm / heightCm;
  const maskCouRaw = clamp((neckRatio - 0.042) / 0.009, -3, 3);
  const cou = clamp(maskWeight * maskCouRaw + bmiWeight * bmiCou, -3, 3);

  // ── Posture from profile world landmarks ─────────────────────────────────
  let posture = 0;
  let confPosture = 0.10;
  if (pWLm && pWLm.length >= 29) {
    const pShZ  = avg(pWLm[11].z, pWLm[12].z);
    const pHipZ = avg(pWLm[23].z, pWLm[24].z);
    posture     = clamp((pHipZ - pShZ) * 8, -3, 3);
    confPosture = profileMaskQ * 0.7;
  }

  // ── Confidence scores ─────────────────────────────────────────────────────
  const cirqConf = Math.sqrt(frontMaskQ * profileMaskQ); // geometric mean is fairer
  const confidence: MeasurementConfidence = {
    epaules:         clamp(confEpaules, 0, 1),
    poitrine:        clamp(cirqConf, 0, 1),
    tour_taille:     clamp(cirqConf * 0.90, 0, 1),
    hanches:         clamp(cirqConf, 0, 1),
    longueur_jambes: clamp(confLeg, 0, 1),
    longueur_bras:   clamp(confArm, 0, 1),
    forme_jambes:    clamp(frontMaskQ * 0.75, 0, 1),
    forme_bras:      clamp(frontMaskQ * 0.60, 0, 1),
    cou:             clamp(frontMaskQ * 0.50, 0, 1),
    posture:         clamp(confPosture, 0, 1),
  };

  // ── Gender-specific shoulder fallback ────────────────────────────────────
  const epaulesRef = gender === 'female' ? 37 : gender === 'male' ? 44 : 40.5;
  const epaules = clamp(shoulderWidthCm > 20 ? shoulderWidthCm : epaulesRef, 28, 62);

  const measurements: BodyMeasurements = {
    taille:           heightCm,
    poids:            weightKg,
    epaules,
    poitrine,
    tour_taille,
    hanches,
    longueur_jambes:  clamp(legLengthCm > 30 ? legLengthCm : heightCm * 0.47, 60, 100),
    forme_jambes,
    longueur_bras:    clamp(armLengthCm > 20 ? armLengthCm : heightCm * 0.37, 45, 90),
    forme_bras,
    cou,
    posture,
  };

  const anatomicalWarnings = validateAndClamp(measurements);
  return { measurements, confidence, anatomicalWarnings };
}

// ---------------------------------------------------------------------------
// Anatomical validation + final clamp
// ---------------------------------------------------------------------------
/**
 * Vérifie la cohérence anatomique des mesures et applique des fallbacks si
 * des incohérences sont détectées. Retourne la liste des avertissements.
 *
 * Mutation in-place : les valeurs suspects sont corrigées avec un fallback
 * proportionnel avant utilisation.
 */
function validateAndClamp(m: BodyMeasurements): string[] {
  const warnings: string[] = [];

  // Taille > hanches (rare mais possible avec un mauvais masque profil)
  if (m.tour_taille > m.hanches) {
    warnings.push(`taille (${m.tour_taille.toFixed(0)}cm) > hanches (${m.hanches.toFixed(0)}cm) — probable erreur masque profil`);
    m.tour_taille = m.hanches * 0.88;
  }

  // Longueur bras > 56% de la taille
  if (m.longueur_bras > m.taille * 0.56) {
    warnings.push(`longueur bras suspecte (${m.longueur_bras.toFixed(0)}cm pour taille ${m.taille}cm)`);
    m.longueur_bras = m.taille * 0.44;
  }

  // Longueur jambes > 62% de la taille
  if (m.longueur_jambes > m.taille * 0.62) {
    warnings.push(`longueur jambes suspecte (${m.longueur_jambes.toFixed(0)}cm pour taille ${m.taille}cm)`);
    m.longueur_jambes = m.taille * 0.47;
  }

  // Épaules hors plage physiologique
  if (m.epaules < 28 || m.epaules > 65) {
    warnings.push(`largeur épaules hors plage physiologique (${m.epaules.toFixed(1)}cm)`);
    m.epaules = clamp(m.epaules, 28, 65);
  }

  // Clamp physiologique final (garde-fou ultime)
  m.poitrine    = clamp(m.poitrine,    55, 160);
  m.tour_taille = clamp(m.tour_taille, 50, 155);
  m.hanches     = clamp(m.hanches,     60, 165);

  return warnings;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------
const GENDER_DEFAULTS: Record<string, Omit<BodyMeasurements, 'taille' | 'poids'>> = {
  male: {
    epaules: 44, poitrine: 100, tour_taille: 90, hanches: 102,
    longueur_jambes: 82, forme_jambes: 0, longueur_bras: 62, forme_bras: 0, cou: 0, posture: 0,
  },
  female: {
    epaules: 37, poitrine: 93, tour_taille: 76, hanches: 100,
    longueur_jambes: 76, forme_jambes: 0, longueur_bras: 57, forme_bras: 0, cou: 0, posture: 0,
  },
  neutral: {
    epaules: 40.5, poitrine: 96, tour_taille: 82, hanches: 101,
    longueur_jambes: 79, forme_jambes: 0, longueur_bras: 59, forme_bras: 0, cou: 0, posture: 0,
  },
};

function defaultResult(
  heightCm: number,
  weightKg: number,
  gender: string,
): ExtractionResult {
  const g = GENDER_DEFAULTS[gender] ?? GENDER_DEFAULTS.neutral;
  return {
    measurements: { taille: heightCm, poids: weightKg, ...g },
    confidence: {
      epaules: 0, poitrine: 0, tour_taille: 0, hanches: 0,
      longueur_jambes: 0, longueur_bras: 0,
      forme_jambes: 0, forme_bras: 0, cou: 0, posture: 0,
    },
    anatomicalWarnings: [],
  };
}
