// Browser-only — do NOT import in Server Components

/**
 * Normalisation EXIF des images avant analyse MediaPipe.
 *
 * Les photos prises sur mobile ont souvent une orientation EXIF ≠ 1.
 * MediaPipe lit le bitmap brut et peut analyser une image "couchée" si
 * l'orientation EXIF n'est pas appliquée au préalable.
 *
 * Ce module dessine l'image dans un OffscreenCanvas avec la rotation EXIF
 * correcte, et retourne un ImageBitmap stable que MediaPipe peut traiter.
 */

export interface NormalizedImage {
  /** Bitmap normalisé (orientation EXIF appliquée), prêt pour MediaPipe */
  bitmap: ImageBitmap;
  /** Largeur réelle du bitmap normalisé (px) */
  naturalWidth: number;
  /** Hauteur réelle du bitmap normalisé (px) */
  naturalHeight: number;
  /** URL objet pour affichage dans l'UI (à révoquer quand inutile) */
  displayUrl: string;
}

/**
 * Charge un File image, corrige l'orientation EXIF, retourne un ImageBitmap
 * normalisé. Doit être utilisé avant tout appel à detectPoseFromImage().
 */
export async function normalizeImageOrientation(file: File): Promise<NormalizedImage> {
  const orientation = await readExifOrientation(file);
  const displayUrl = URL.createObjectURL(file);
  const img = await loadHTMLImage(displayUrl);

  const { naturalWidth: nw, naturalHeight: nh } = img;

  // Les orientations 5-8 nécessitent une rotation 90°/270° → swap W/H
  const swapped = orientation >= 5 && orientation <= 8;
  const canvasW = swapped ? nh : nw;
  const canvasH = swapped ? nw : nh;

  let bitmap: ImageBitmap;

  if (orientation === 1) {
    // Cas le plus fréquent sur desktop : pas de rotation nécessaire
    bitmap = await createImageBitmap(img);
  } else {
    // Dessiner avec transform EXIF dans un OffscreenCanvas
    bitmap = await drawWithExifTransform(img, orientation, nw, nh, canvasW, canvasH);
  }

  return { bitmap, naturalWidth: canvasW, naturalHeight: canvasH, displayUrl };
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function loadHTMLImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

async function drawWithExifTransform(
  img: HTMLImageElement,
  orientation: number,
  nw: number,
  nh: number,
  canvasW: number,
  canvasH: number,
): Promise<ImageBitmap> {
  // OffscreenCanvas est disponible sur Chrome/Firefox/Edge 79+
  // Fallback sur canvas HTML classique pour Safari < 16.4
  let ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
  let source: HTMLCanvasElement | OffscreenCanvas;

  if (typeof OffscreenCanvas !== 'undefined') {
    const oc = new OffscreenCanvas(canvasW, canvasH);
    ctx = oc.getContext('2d')!;
    source = oc;
  } else {
    const c = document.createElement('canvas');
    c.width = canvasW;
    c.height = canvasH;
    ctx = c.getContext('2d')!;
    source = c;
  }

  applyExifTransform(ctx, orientation, nw, nh);
  ctx.drawImage(img, 0, 0);

  return createImageBitmap(source as ImageBitmapSource);
}

/**
 * Applique la transformation ctx correspondant à l'orientation EXIF (1-8).
 *
 * Référence : https://www.daveperrett.com/articles/2012/07/28/exif-orientation-handling-is-a-ghetto/
 *
 * Orientation 1 : normal
 * Orientation 2 : miroir horizontal
 * Orientation 3 : rotation 180°
 * Orientation 4 : miroir vertical
 * Orientation 5 : miroir horizontal + rotation 270° CW
 * Orientation 6 : rotation 90° CW
 * Orientation 7 : miroir horizontal + rotation 90° CW
 * Orientation 8 : rotation 270° CW (= 90° CCW)
 */
function applyExifTransform(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  orientation: number,
  srcW: number,
  srcH: number,
): void {
  switch (orientation) {
    case 2: ctx.transform(-1, 0, 0, 1, srcW, 0);        break;
    case 3: ctx.transform(-1, 0, 0, -1, srcW, srcH);    break;
    case 4: ctx.transform(1, 0, 0, -1, 0, srcH);        break;
    case 5: ctx.transform(0, 1, 1, 0, 0, 0);            break;
    case 6: ctx.transform(0, 1, -1, 0, srcH, 0);        break;
    case 7: ctx.transform(0, -1, -1, 0, srcH, srcW);    break;
    case 8: ctx.transform(0, -1, 1, 0, 0, srcW);        break;
    // case 1: identité, rien à faire
  }
}

/**
 * Lit l'orientation EXIF d'un fichier image (tag 0x0112).
 * Retourne 1 (normal) si le tag n'est pas trouvé ou si ce n'est pas un JPEG.
 *
 * L'orientation EXIF n'existe que dans les JPEG (marqueur 0xFFD8).
 * Pour PNG/WebP, on retourne toujours 1.
 */
async function readExifOrientation(file: File): Promise<number> {
  // Lire les 64 premiers Ko max (le segment EXIF est toujours près du début)
  const MAX_READ = 65536;
  const slice = file.slice(0, MAX_READ);
  const buffer = await slice.arrayBuffer();
  const view = new DataView(buffer);

  // Vérifier la signature JPEG (0xFFD8)
  if (view.byteLength < 2 || view.getUint16(0) !== 0xffd8) return 1;

  let offset = 2;
  while (offset + 4 <= view.byteLength) {
    const marker = view.getUint16(offset);
    offset += 2;
    const segLen = view.getUint16(offset);
    offset += 2;

    // Segment APP1 (0xFFE1) — contient EXIF
    if (marker === 0xffe1) {
      // Vérifier l'en-tête "Exif\0\0"
      if (offset + 6 <= view.byteLength &&
          view.getUint32(offset) === 0x45786966 &&  // 'Exif'
          view.getUint16(offset + 4) === 0x0000) {
        const exifOffset = offset + 6;
        return parseExifOrientation(view, exifOffset);
      }
    }

    // Sauter le segment (longueur inclut les 2 octets de longueur eux-mêmes)
    offset += segLen - 2;
    if (offset >= view.byteLength) break;
  }

  return 1;
}

function parseExifOrientation(view: DataView, start: number): number {
  if (start + 8 > view.byteLength) return 1;

  // Octet ordre : "II" (little-endian) ou "MM" (big-endian)
  const byteOrder = view.getUint16(start);
  const le = byteOrder === 0x4949; // 'II'

  const ifdOffset = view.getUint32(start + 4, le);
  const ifdStart = start + ifdOffset;
  if (ifdStart + 2 > view.byteLength) return 1;

  const entryCount = view.getUint16(ifdStart, le);
  for (let i = 0; i < entryCount; i++) {
    const entryOffset = ifdStart + 2 + i * 12;
    if (entryOffset + 12 > view.byteLength) break;

    const tag = view.getUint16(entryOffset, le);
    if (tag === 0x0112) {
      // Tag Orientation trouvé
      return view.getUint16(entryOffset + 8, le);
    }
  }

  return 1;
}
