// Browser-only — do NOT import in Server Components
import type { PoseLandmarkerResult, NormalizedLandmark } from './pose';

// ---------------------------------------------------------------------------
// Geometric pose validation
// ---------------------------------------------------------------------------
/**
 * Vérifie que les landmarks sont anatomiquement cohérents.
 * Détecte les cas : image retournée, pose bizarre, landmarks hors limites.
 * Retourne une liste d'issues (vide = OK).
 */
function validatePoseGeometry(lm: NormalizedLandmark[]): string[] {
  const issues: string[] = [];

  const avgShoulderY = (lm[11].y + lm[12].y) / 2;
  const avgHipY      = (lm[23].y + lm[24].y) / 2;
  const avgKneeY     = (lm[25].y + lm[26].y) / 2;
  const avgAnkleY    = (lm[27].y + lm[28].y) / 2;

  // Épaules doivent être au-dessus des hanches
  if (avgShoulderY > avgHipY) {
    issues.push('landmarks inversés — image peut-être retournée');
  }

  // Genoux entre hanches et chevilles
  if (avgKneeY < avgHipY || avgKneeY > avgAnkleY) {
    issues.push('genoux hors de la plage hanche-cheville — pose incohérente');
  }

  // Forte asymétrie verticale des épaules (tilt excessif)
  if (Math.abs(lm[11].y - lm[12].y) > 0.12) {
    issues.push('forte asymétrie des épaules — possible vue en biais');
  }

  return issues;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  qualityScore: number; // 0-1
}

const KEY_FRONT   = [11, 12, 23, 24, 25, 26, 27, 28, 15, 16];
const KEY_PROFILE = [11, 12, 23, 24, 27, 28];

function vis(lm: NormalizedLandmark): number {
  return lm.visibility ?? 0;
}

function dist2D(a: NormalizedLandmark, b: NormalizedLandmark): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

// ---------------------------------------------------------------------------
// Front photo validation
// ---------------------------------------------------------------------------
export function validateFrontPhoto(result: PoseLandmarkerResult): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!result.landmarks[0] || result.landmarks[0].length < 29) {
    return {
      ok: false,
      errors: [
        'Aucun corps humain détecté. Assurez-vous d\'utiliser une vraie photo d\'une personne (pas un dessin, mannequin 3D ou illustration).',
      ],
      warnings: [],
      qualityScore: 0,
    };
  }

  const lm = result.landmarks[0];

  // --- Geometric coherence check ---
  const geoIssues = validatePoseGeometry(lm);
  for (const issue of geoIssues) {
    errors.push(issue);
  }

  // --- Visibility of key landmarks ---
  const minVis = Math.min(...KEY_FRONT.map(i => vis(lm[i])));
  // Very low global visibility = probably a render/illustration, not a real human
  if (minVis < 0.20) {
    return {
      ok: false,
      errors: ['Corps non reconnu comme humain réel. Utilisez une vraie photo de vous-même, pas une image synthétique.'],
      warnings: [],
      qualityScore: 0,
    };
  }
  if (minVis < 0.45) {
    warnings.push('Certains membres sont peu visibles — le résultat sera moins précis. Essayez avec un meilleur éclairage.');
  }

  // --- Full body check: use body SPAN (relative) not absolute Y position ---
  // Span = vertical distance from nose to mid-ankle (in normalised 0-1 coords)
  const noseY   = lm[0].y;
  const ankleY  = (lm[27].y + lm[28].y) / 2;
  const bodySpan = ankleY - noseY;

  if (bodySpan < 0.40) {
    // Body too small in frame OR feet/head cut off
    if (ankleY < 0.60) {
      errors.push('Les pieds ne sont pas visibles. Reculez-vous pour inclure tout le corps (tête jusqu\'aux pieds).');
    } else {
      errors.push('Corps entier non visible dans le cadre. Reculez-vous pour que la tête et les pieds apparaissent tous les deux.');
    }
  } else if (bodySpan < 0.55) {
    warnings.push('La personne est assez petite dans l\'image — pour de meilleures mesures, rapprochez-vous légèrement.');
  }

  if (ankleY < 0.60) {
    errors.push('Les pieds sont coupés. Reculez-vous ou cadrez plus bas pour inclure les pieds.');
  }

  // --- Facing camera: nose x close to shoulder midpoint x ---
  const midShoulderX = (lm[11].x + lm[12].x) / 2;
  const noseOffset   = Math.abs(lm[0].x - midShoulderX);
  if (noseOffset > 0.14) {
    errors.push('La personne n\'est pas de face. Regardez droit vers l\'appareil photo.');
  } else if (noseOffset > 0.08) {
    warnings.push('Légèrement de côté — pour de meilleures mesures, faites face à l\'appareil.');
  }

  // --- Arms separated from body ---
  const leftWristHipDist  = dist2D(lm[15], lm[23]);
  const rightWristHipDist = dist2D(lm[16], lm[24]);
  if (leftWristHipDist < 0.06 || rightWristHipDist < 0.06) {
    warnings.push('Bras trop proches du corps — écartez légèrement les bras (pose en A) pour de meilleures mesures.');
  }

  // --- Shoulder span: should be wide (not a profile) ---
  const shoulderSpan = dist2D(lm[11], lm[12]);
  if (shoulderSpan < 0.15) {
    errors.push('Photo ressemblant à un profil. Placez-vous face à l\'appareil pour la vue de face.');
  }

  // --- Quality score ---
  const visScore    = Math.min(1, minVis / 0.65);
  const frameScore  = bodySpan > 0.60 && ankleY > 0.70 ? 1.0 : bodySpan > 0.45 ? 0.7 : 0.3;
  const orientScore = noseOffset < 0.08 ? 1.0 : noseOffset < 0.14 ? 0.6 : 0.0;
  const qualityScore = visScore * 0.5 + frameScore * 0.3 + orientScore * 0.2;

  return { ok: errors.length === 0, errors, warnings, qualityScore };
}

// ---------------------------------------------------------------------------
// Profile photo validation
// ---------------------------------------------------------------------------
export function validateProfilePhoto(result: PoseLandmarkerResult): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!result.landmarks[0] || result.landmarks[0].length < 29) {
    return {
      ok: false,
      errors: ['Aucun corps humain détecté dans la photo de profil. Utilisez une vraie photo de vous-même.'],
      warnings: [],
      qualityScore: 0,
    };
  }

  const lm = result.landmarks[0];

  // --- Geometric coherence check ---
  const geoIssues = validatePoseGeometry(lm);
  for (const issue of geoIssues) {
    warnings.push(issue); // profil : geo issues = warnings (pas bloquant car pose latérale normale)
  }

  // --- Visibility ---
  const minVis = Math.min(...KEY_PROFILE.map(i => vis(lm[i])));
  if (minVis < 0.20) {
    return {
      ok: false,
      errors: ['Corps non reconnu. Utilisez une vraie photo (pas d\'image synthétique).'],
      warnings: [],
      qualityScore: 0,
    };
  }
  if (minVis < 0.35) {
    warnings.push('Éclairage insuffisant — le résultat sera moins précis.');
  }

  // --- Full body check (span-based) ---
  const noseY  = lm[0].y;
  const ankleY = (lm[27].y + lm[28].y) / 2;
  const bodySpan = ankleY - noseY;

  if (bodySpan < 0.40) {
    errors.push('Corps entier non visible dans le profil. Reculez-vous pour inclure la tête et les pieds.');
  }
  if (ankleY < 0.60) {
    errors.push('Les pieds sont coupés dans la photo de profil.');
  }

  // --- Profile orientation: shoulders should be nearly overlapping (small horizontal span) ---
  const shoulderSpanX = Math.abs(lm[11].x - lm[12].x);
  if (shoulderSpanX > 0.22) {
    errors.push('Cette photo n\'est pas un profil. Tournez-vous à 90° de l\'appareil photo (côté gauche ou droit face à la caméra).');
  } else if (shoulderSpanX > 0.14) {
    warnings.push('Profil pas tout à fait perpendiculaire — tournez-vous davantage pour une meilleure précision.');
  }

  // --- Body upright ---
  const shoulderY = (lm[11].y + lm[12].y) / 2;
  const hipY      = (lm[23].y + lm[24].y) / 2;
  if (shoulderY > hipY) {
    errors.push('Position incorrecte — tenez-vous debout pour la photo de profil.');
  }

  const visScore    = Math.min(1, minVis / 0.55);
  const frameScore  = bodySpan > 0.55 && ankleY > 0.70 ? 1.0 : bodySpan > 0.40 ? 0.7 : 0.3;
  const profileScore = shoulderSpanX < 0.12 ? 1.0 : shoulderSpanX < 0.20 ? 0.6 : 0.0;
  const qualityScore = visScore * 0.4 + frameScore * 0.3 + profileScore * 0.3;

  return { ok: errors.length === 0, errors, warnings, qualityScore };
}
