// Browser-only — do NOT import in Server Components

/**
 * Calcule le transform exact pour un <img> rendu en `object-fit: contain`
 * à l'intérieur d'un conteneur CSS de dimensions données.
 *
 * L'image peut avoir du letterbox (bandes noires) si son rapport hauteur/largeur
 * diffère de celui du conteneur. Ce module fournit les offsets et dimensions
 * exacts de la zone image réellement visible, afin que les landmarks normalisés
 * (0-1) soient correctement reprojetés sur le canvas overlay.
 */
export interface OverlayTransform {
  /** Offset horizontal gauche en px CSS (largeur du letterbox gauche) */
  offsetX: number;
  /** Offset vertical haut en px CSS (hauteur du letterbox haut) */
  offsetY: number;
  /** Largeur de l'image rendue en px CSS (sans letterbox) */
  renderedW: number;
  /** Hauteur de l'image rendue en px CSS (sans letterbox) */
  renderedH: number;
}

/**
 * Calcule l'OverlayTransform pour object-fit: contain.
 *
 * @param naturalW  Largeur réelle du bitmap (px)
 * @param naturalH  Hauteur réelle du bitmap (px)
 * @param containerW  Largeur du conteneur CSS (px logiques)
 * @param containerH  Hauteur du conteneur CSS (px logiques)
 */
export function computeObjectFitContainTransform(
  naturalW: number,
  naturalH: number,
  containerW: number,
  containerH: number,
): OverlayTransform {
  const imgAspect = naturalW / naturalH;
  const ctnAspect = containerW / containerH;

  let renderedW: number;
  let renderedH: number;

  if (imgAspect > ctnAspect) {
    // Image plus large que le conteneur → contrainte par la largeur
    renderedW = containerW;
    renderedH = containerW / imgAspect;
  } else {
    // Image plus haute que le conteneur → contrainte par la hauteur
    renderedH = containerH;
    renderedW = containerH * imgAspect;
  }

  return {
    offsetX: (containerW - renderedW) / 2,
    offsetY: (containerH - renderedH) / 2,
    renderedW,
    renderedH,
  };
}

/**
 * Convertit un landmark normalisé (0-1) en coordonnée canvas (px CSS).
 *
 * Les coordonnées normalisées MediaPipe sont relatives au bitmap source.
 * Ce helper les projette dans l'espace canvas en tenant compte du letterbox.
 */
export function landmarkToCanvas(
  nx: number,
  ny: number,
  t: OverlayTransform,
): { x: number; y: number } {
  return {
    x: t.offsetX + nx * t.renderedW,
    y: t.offsetY + ny * t.renderedH,
  };
}

/**
 * Dessine un rectangle de debug (vert) délimitant la zone image réelle
 * dans le canvas. Utile pour vérifier que le transform est correct.
 *
 * Utilisation : activer avec ?debug=true dans l'URL.
 */
export function drawDebugBounds(
  ctx: CanvasRenderingContext2D,
  t: OverlayTransform,
): void {
  ctx.save();
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 3]);
  ctx.strokeRect(t.offsetX, t.offsetY, t.renderedW, t.renderedH);
  ctx.restore();
}
