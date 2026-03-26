// Browser-only — do NOT import in Server Components

/**
 * Extraction robuste des largeurs corporelles depuis un masque de segmentation.
 *
 * Problème de l'ancienne implémentation :
 * - Utilisait "longest contiguous run" → un seul pixel manquant (ombre, couture)
 *   coupait le compteur → sous-estimation systématique.
 *
 * Nouvelle approche :
 * - Somme TOUS les pixels body dans la plage X (pas juste le run contigu).
 * - Médiane sur windowRows lignes adjacentes pour éliminer artefacts locaux.
 */

/**
 * Mesure la largeur du corps en pixels masque à une hauteur normalisée donnée.
 *
 * @param data       Float32Array du masque (valeurs 0-1, 1 = corps)
 * @param maskW      Largeur du masque en pixels
 * @param maskH      Hauteur du masque en pixels
 * @param yNorm      Position verticale normalisée [0,1] où mesurer
 * @param xMinNorm   Borne gauche de la zone de recherche [0,1]
 * @param xMaxNorm   Borne droite de la zone de recherche [0,1]
 * @param threshold  Seuil de binarisation (défaut 0.5)
 * @param windowRows Nombre de lignes adjacentes pour le lissage (médiane)
 * @returns Largeur en pixels masque (0 si aucun pixel trouvé)
 */
export function getMaskWidthAtY(
  data: Float32Array,
  maskW: number,
  maskH: number,
  yNorm: number,
  xMinNorm: number,
  xMaxNorm: number,
  threshold = 0.5,
  windowRows = 5,
): number {
  const yCenter = Math.round(yNorm * maskH);
  const xMin = Math.max(0, Math.floor(xMinNorm * maskW));
  const xMax = Math.min(maskW - 1, Math.ceil(xMaxNorm * maskW));

  const widths: number[] = [];
  const half = Math.floor(windowRows / 2);

  for (let dy = -half; dy <= half; dy++) {
    const row = yCenter + dy;
    if (row < 0 || row >= maskH) continue;

    // Sommer TOUS les pixels body dans la plage X (pas longest run)
    let count = 0;
    for (let x = xMin; x <= xMax; x++) {
      if (data[row * maskW + x] >= threshold) count++;
    }
    widths.push(count);
  }

  if (widths.length === 0) return 0;

  // Médiane : plus robuste que la moyenne face aux artefacts
  widths.sort((a, b) => a - b);
  return widths[Math.floor(widths.length / 2)];
}

/**
 * Calcule le ratio de couverture du masque dans une zone rectangulaire.
 * Retourne 0-1 (fraction de pixels "corps" dans la bbox).
 *
 * Utilisé pour évaluer la qualité du masque dans une zone d'intérêt.
 */
export function maskCoverageInZone(
  data: Float32Array,
  maskW: number,
  maskH: number,
  xMinNorm: number,
  xMaxNorm: number,
  yMinNorm: number,
  yMaxNorm: number,
  threshold = 0.5,
): number {
  const x0 = Math.max(0, Math.floor(xMinNorm * maskW));
  const x1 = Math.min(maskW - 1, Math.ceil(xMaxNorm * maskW));
  const y0 = Math.max(0, Math.floor(yMinNorm * maskH));
  const y1 = Math.min(maskH - 1, Math.ceil(yMaxNorm * maskH));

  let total = 0;
  let body = 0;

  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      total++;
      if (data[y * maskW + x] >= threshold) body++;
    }
  }

  return total === 0 ? 0 : body / total;
}

/**
 * Dessine les lignes de scan silhouette sur un canvas en mode debug.
 * Active avec ?debug=true dans l'URL.
 *
 * @param ctx          Contexte canvas
 * @param scanLevels   Liste de positions normalisées {yNorm, label}
 * @param offsetX      Offset X du letterbox (depuis OverlayTransform)
 * @param offsetY      Offset Y du letterbox
 * @param renderedW    Largeur rendue de l'image
 * @param renderedH    Hauteur rendue de l'image
 */
export function drawDebugScanLines(
  ctx: CanvasRenderingContext2D,
  scanLevels: Array<{ yNorm: number; label: string }>,
  offsetX: number,
  offsetY: number,
  renderedW: number,
  renderedH: number,
): void {
  ctx.save();
  ctx.strokeStyle = '#00ffff';
  ctx.fillStyle = '#00ffff';
  ctx.lineWidth = 1;
  ctx.font = '10px monospace';
  ctx.setLineDash([4, 2]);

  for (const { yNorm, label } of scanLevels) {
    const y = offsetY + yNorm * renderedH;
    ctx.beginPath();
    ctx.moveTo(offsetX, y);
    ctx.lineTo(offsetX + renderedW, y);
    ctx.stroke();
    ctx.fillText(label, offsetX + 4, y - 2);
  }

  ctx.restore();
}
