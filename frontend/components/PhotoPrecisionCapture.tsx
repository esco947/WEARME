'use client';

import { useRef, useState } from 'react';
import { SKELETON_CONNECTIONS } from '@/lib/pose';
import type { NormalizedLandmark, PoseLandmarkerResult } from '@/lib/pose';
import { validateFrontPhoto, validateProfilePhoto } from '@/lib/photo-quality';
import { extractAllMeasurements } from '@/lib/body-measurements';
import type { BodyMeasurements, MeasurementConfidence } from '@/lib/body-measurements';
import { computeObjectFitContainTransform, landmarkToCanvas, drawDebugBounds } from '@/lib/overlay-mapping';
import { analyzePosePhotos } from '@/lib/api';
import type { BackendPoseResult } from '@/lib/api';
import MeasurementConfidencePanel from './MeasurementConfidencePanel';

const DEBUG = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('debug');

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type Step = 'guide' | 'upload' | 'analyzing' | 'result' | 'error';

interface PhotoState {
  file: File | null;
  previewUrl: string;
}

/** Adaptateur : masque de segmentation backend → interface MaskLike de body-measurements.ts */
class BackendMask {
  readonly width: number;
  readonly height: number;
  private _data: Float32Array;

  constructor(b64: string, width: number, height: number) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    this._data = new Float32Array(bytes.buffer);
    this.width = width;
    this.height = height;
  }

  getAsFloat32Array(): Float32Array { return this._data; }
  close(): void { /* noop */ }
}

/** Construit un PoseLandmarkerResult compatible à partir de la réponse backend */
function buildPoseResult(data: BackendPoseResult): PoseLandmarkerResult {
  const lm = data.landmarks.map(p => ({ x: p.x, y: p.y, z: p.z, visibility: p.visibility }));
  const wlm = data.world_landmarks.map(p => ({ x: p.x, y: p.y, z: p.z, visibility: p.visibility }));
  const masks = data.segmentation_mask_b64
    ? [new BackendMask(data.segmentation_mask_b64, data.mask_width, data.mask_height)]
    : [];
  return { landmarks: [lm], worldLandmarks: [wlm], segmentationMasks: masks };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Dessine le squelette des landmarks sur le canvas overlay.
 *
 * FIX CRITIQUE : utilise computeObjectFitContainTransform pour calculer
 * les offsets du letterbox (object-fit: contain) et projette correctement
 * les coordonnées normalisées MediaPipe vers les pixels canvas.
 *
 * Avant ce fix, les points étaient dessinés à `lm.x * W` / `lm.y * H`
 * (taille du conteneur), sans tenir compte du letterbox → décalage visuel.
 */
function drawSkeleton(
  canvas: HTMLCanvasElement,
  containerW: number,
  containerH: number,
  naturalW: number,
  naturalH: number,
  landmarks: NormalizedLandmark[],
) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = containerW * dpr;
  canvas.height = containerH * dpr;
  canvas.style.width  = `${containerW}px`;
  canvas.style.height = `${containerH}px`;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.scale(dpr, dpr);

  // Calcul des offsets letterbox (object-fit: contain)
  const t = computeObjectFitContainTransform(naturalW, naturalH, containerW, containerH);

  if (DEBUG) {
    drawDebugBounds(ctx, t);
  }

  // Connections (squelette)
  ctx.strokeStyle = 'rgba(99, 102, 241, 0.85)';
  ctx.lineWidth = 2;
  for (const [a, b] of SKELETON_CONNECTIONS) {
    const lmA = landmarks[a];
    const lmB = landmarks[b];
    if (!lmA || !lmB) continue;
    if ((lmA.visibility ?? 0) < 0.25 || (lmB.visibility ?? 0) < 0.25) continue;
    const { x: ax, y: ay } = landmarkToCanvas(lmA.x, lmA.y, t);
    const { x: bx, y: by } = landmarkToCanvas(lmB.x, lmB.y, t);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.stroke();
  }

  // Points (articulations)
  for (const lm of landmarks) {
    if ((lm.visibility ?? 0) < 0.25) continue;
    const { x, y } = landmarkToCanvas(lm.x, lm.y, t);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
    ctx.fill();
  }
}

// ---------------------------------------------------------------------------
// Photo upload zone
// ---------------------------------------------------------------------------
function UploadZone({
  label, photo, onFile,
}: {
  label: string;
  photo: PhotoState;
  onFile: (f: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const imgRef   = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  function handleFile(f: File) {
    if (!f.type.startsWith('image/')) return;
    if (f.size > 10 * 1024 * 1024) { alert('Image trop lourde (max 10 Mo).'); return; }
    onFile(f);
  }

  return (
    <div className="flex-1">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      {photo.previewUrl ? (
        <div className="relative rounded-xl overflow-hidden border border-indigo-200 bg-gray-50">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={imgRef}
            src={photo.previewUrl}
            alt={label}
            className="w-full object-contain max-h-56"
          />
          <canvas
            ref={canvasRef}
            className="absolute inset-0 pointer-events-none"
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="absolute bottom-2 right-2 bg-white/80 text-xs text-gray-600 px-2 py-1 rounded-lg border border-gray-200 hover:bg-white"
          >
            Changer
          </button>
        </div>
      ) : (
        <button
          onClick={() => inputRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
          className="w-full h-40 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:border-indigo-400 hover:text-indigo-500 transition-colors cursor-pointer"
        >
          <span className="text-3xl">📷</span>
          <span className="text-sm">Cliquer ou déposer une photo</span>
          <span className="text-xs">JPG, PNG, WEBP — max 10 Mo</span>
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ''; }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Guide step
// ---------------------------------------------------------------------------
const NORMS = [
  { icon: '📐', text: 'Corps entier visible, de la tête aux pieds' },
  { icon: '👁️', text: 'Face à la caméra, debout droit — 1ère photo' },
  { icon: '↩️', text: 'Profil à 90° de l\'appareil — 2ème photo' },
  { icon: '🙌', text: 'Bras légèrement écartés du corps (~30°, pose en A)' },
  { icon: '👕', text: 'Vêtements ajustés (éviter les vêtements amples)' },
  { icon: '💡', text: 'Éclairage uniforme, pas de contre-jour, fond uni' },
  { icon: '📏', text: 'Appareil à hauteur de taille (~1 m du sol)' },
];

function GuideStep({ onNext }: { onNext: () => void }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Normes pour la prise de photos</h3>
      <div className="space-y-2 mb-5">
        {NORMS.map(({ icon, text }, i) => (
          <div key={i} className="flex items-start gap-2 text-sm text-gray-700">
            <span className="mt-0.5 text-base">{icon}</span>
            <span>{text}</span>
          </div>
        ))}
      </div>
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 mb-5 text-xs text-indigo-700">
        <strong>2 photos requises</strong> : une de face + une de profil.<br />
        La photo de profil permet de mesurer les profondeurs du corps (poitrine, taille, hanches) via une approximation elliptique — beaucoup plus précis qu'une seule vue.
      </div>
      <button
        onClick={onNext}
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-xl text-sm font-medium"
      >
        J'ai compris — uploader les photos
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function PhotoPrecisionCapture({
  gender,
  onMeasurementsReady,
}: {
  gender: string;
  onMeasurementsReady: (m: BodyMeasurements, c: MeasurementConfidence) => void;
}) {
  const [step, setStep]               = useState<Step>('guide');
  const [frontPhoto, setFrontPhoto]   = useState<PhotoState>({ file: null, previewUrl: '' });
  const [profilePhoto, setProfilePhoto] = useState<PhotoState>({ file: null, previewUrl: '' });
  const [heightCm, setHeightCm]       = useState('');
  const [weightKg, setWeightKg]       = useState('');
  const [analysisStatus, setStatus]   = useState('');
  const [warnings, setWarnings]       = useState<string[]>([]);
  const [errorMsg, setErrorMsg]       = useState('');
  const [resultMeas, setResultMeas]   = useState<BodyMeasurements | null>(null);
  const [resultConf, setResultConf]   = useState<MeasurementConfidence | null>(null);
  const [frontLm, setFrontLm]         = useState<NormalizedLandmark[]>([]);
  const [profileLm, setProfileLm]     = useState<NormalizedLandmark[]>([]);

  const frontImgRef   = useRef<HTMLImageElement>(null);
  const profileImgRef = useRef<HTMLImageElement>(null);
  const frontCanvasRef   = useRef<HTMLCanvasElement>(null);
  const profileCanvasRef = useRef<HTMLCanvasElement>(null);

  function setFrontFile(f: File) {
    setFrontPhoto({ file: f, previewUrl: URL.createObjectURL(f) });
  }
  function setProfileFile(f: File) {
    setProfilePhoto({ file: f, previewUrl: URL.createObjectURL(f) });
  }

  const canAnalyze =
    frontPhoto.file !== null &&
    profilePhoto.file !== null &&
    Number(heightCm) >= 100 && Number(heightCm) <= 250 &&
    Number(weightKg) >= 20  && Number(weightKg) <= 300;

  async function handleAnalyze() {
    if (!frontPhoto.file || !profilePhoto.file) return;
    const h = Number(heightCm);
    const w = Number(weightKg);

    setStep('analyzing');
    setWarnings([]);
    setErrorMsg('');

    try {
      setStatus('Envoi des photos au serveur (première analyse ~30s le temps de télécharger le modèle)...');
      const { front: frontData, profile: profileData } = await analyzePosePhotos(
        frontPhoto.file,
        profilePhoto.file,
      );

      if (!frontData.landmarks.length || !profileData.landmarks.length) {
        setErrorMsg('Aucune personne détectée. Vérifiez que le corps entier est visible sur les deux photos.');
        setStep('error');
        return;
      }

      const frontResult = buildPoseResult(frontData);
      const profileResult = buildPoseResult(profileData);

      const frontVal = validateFrontPhoto(frontResult);
      if (!frontVal.ok) {
        setErrorMsg('Photo de face : ' + frontVal.errors.join(' '));
        setStep('error');
        return;
      }

      const profileVal = validateProfilePhoto(profileResult);
      if (!profileVal.ok) {
        setErrorMsg('Photo de profil : ' + profileVal.errors.join(' '));
        setStep('error');
        return;
      }

      setStatus('Calcul des mesures...');
      const { measurements, confidence, anatomicalWarnings } = extractAllMeasurements(
        frontResult, profileResult, h, w, gender,
      );

      setFrontLm(frontResult.landmarks[0] ?? []);
      setProfileLm(profileResult.landmarks[0] ?? []);
      setResultMeas(measurements);
      setResultConf(confidence);
      setWarnings([...frontVal.warnings, ...profileVal.warnings, ...anatomicalWarnings]);
      setStep('result');

    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Erreur d\'analyse inattendue.');
      setStep('error');
    }
  }

  // Dessine le squelette quand l'image est chargée dans l'étape résultat.
  // Lit les dimensions du conteneur parent et les dimensions naturelles stockées.
  function drawOverlay(
    imgEl: HTMLImageElement,
    canvasEl: HTMLCanvasElement,
    lm: NormalizedLandmark[],
  ) {
    if (lm.length === 0 || !imgEl.naturalWidth) return;
    const container = canvasEl.parentElement;
    if (!container) return;
    drawSkeleton(
      canvasEl,
      container.clientWidth,
      container.clientHeight,
      imgEl.naturalWidth,
      imgEl.naturalHeight,
      lm,
    );
  }

  // ---- Render ------------------------------------------------------------
  return (
    <div>
      {/* GUIDE */}
      {step === 'guide' && <GuideStep onNext={() => setStep('upload')} />}

      {/* UPLOAD */}
      {step === 'upload' && (
        <div className="space-y-4">
          {/* Photo zones */}
          <div className="flex gap-3">
            <UploadZone label="Vue de face" photo={frontPhoto} onFile={setFrontFile} />
            <UploadZone label="Vue de profil (90°)" photo={profilePhoto} onFile={setProfileFile} />
          </div>

          {/* Height + weight inputs */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-600 mb-1">
                Taille (cm) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min={100} max={250}
                value={heightCm}
                onChange={e => setHeightCm(e.target.value)}
                placeholder="ex: 175"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-400"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-600 mb-1">
                Poids (kg) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min={20} max={300}
                value={weightKg}
                onChange={e => setWeightKg(e.target.value)}
                placeholder="ex: 70"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-400"
              />
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setStep('guide')}
              className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50"
            >
              Voir les normes
            </button>
            <button
              onClick={handleAnalyze}
              disabled={!canAnalyze}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white py-2 rounded-xl text-sm font-medium transition-colors"
            >
              Analyser les photos
            </button>
          </div>
        </div>
      )}

      {/* ANALYZING */}
      {step === 'analyzing' && (
        <div className="flex flex-col items-center justify-center py-10 gap-4 text-gray-500">
          <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          <p className="text-sm text-center">{analysisStatus}</p>
        </div>
      )}

      {/* RESULT */}
      {step === 'result' && resultMeas && resultConf && (
        <div className="space-y-4">
          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 space-y-0.5">
              {warnings.map((w, i) => (
                <p key={i} className="text-xs text-amber-700">⚠️ {w}</p>
              ))}
            </div>
          )}

          {/* Photo previews with skeleton overlay */}
          <div className="flex gap-2">
            <div className="flex-1">
              <p className="text-xs text-gray-400 mb-1">Face</p>
              <div className="relative rounded-xl overflow-hidden border border-gray-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  ref={frontImgRef}
                  src={frontPhoto.previewUrl}
                  alt="Face"
                  className="w-full object-contain max-h-48"
                  onLoad={e => { const c = frontCanvasRef.current; if (c) drawOverlay(e.currentTarget, c, frontLm); }}
                />
                <canvas ref={frontCanvasRef} className="absolute inset-0 pointer-events-none" />
              </div>
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-400 mb-1">Profil</p>
              <div className="relative rounded-xl overflow-hidden border border-gray-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  ref={profileImgRef}
                  src={profilePhoto.previewUrl}
                  alt="Profil"
                  className="w-full object-contain max-h-48"
                  onLoad={e => { const c = profileCanvasRef.current; if (c) drawOverlay(e.currentTarget, c, profileLm); }}
                />
                <canvas ref={profileCanvasRef} className="absolute inset-0 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Measurements with confidence */}
          <MeasurementConfidencePanel measurements={resultMeas} confidence={resultConf} />

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => { setStep('upload'); setResultMeas(null); setResultConf(null); }}
              className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50"
            >
              Reprendre
            </button>
            <button
              onClick={() => onMeasurementsReady(resultMeas, resultConf)}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-xl text-sm font-medium"
            >
              Utiliser ces mesures →
            </button>
          </div>
        </div>
      )}

      {/* ERROR */}
      {step === 'error' && (
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <p className="text-sm font-medium text-red-700 mb-1">Photo non exploitable</p>
            <p className="text-sm text-red-600">{errorMsg}</p>
          </div>
          <button
            onClick={() => setStep('upload')}
            className="w-full py-2 text-sm text-indigo-600 border border-indigo-200 rounded-xl hover:bg-indigo-50"
          >
            Reprendre une photo
          </button>
        </div>
      )}
    </div>
  );
}
