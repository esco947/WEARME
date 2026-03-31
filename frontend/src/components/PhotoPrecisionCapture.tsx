/**
 * PhotoPrecisionCapture — 3-step photo-based avatar creation.
 *
 * Step 1: Upload front + side photos, enter height/weight
 * Step 2: MediaPipe pose detection (loading / processing)
 * Step 3: Results with single-canvas overlay (image + skeleton drawn together)
 *
 * KEY: We draw everything on a single <canvas> to avoid the CSS object-contain
 * letterboxing misalignment that occurs when overlaying an <canvas> on an <img>.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { BodyParams } from '../types'
import type { PoseResult } from '../lib/pose'
import { detectPoseFromImage, prewarmPoseLandmarker, POSE_CONNECTIONS, LM } from '../lib/pose'
import { validatePhotoQuality } from '../lib/photo-quality'
import { estimateBodyParams, type BodyParamsEstimate } from '../lib/body-measurements'
import MeasurementConfidencePanel from './MeasurementConfidencePanel'

// ── Types ──────────────────────────────────────────────────────────────────

interface Props {
  initialHeight?: number   // cm
  initialWeight?: number   // kg
  onComplete: (params: BodyParams, confidence: number) => void
  onCancel: () => void
}

type Step = 'upload' | 'processing' | 'results'

// ── Image loader ───────────────────────────────────────────────────────────

function loadImageElement(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload  = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Image load failed')) }
    img.src = url
  })
}

// ── Canvas rendering (image + skeleton on a single canvas) ─────────────────

const MAX_CANVAS_HEIGHT = 300   // px — max display height of the result canvas

/**
 * Draws the photo + pose skeleton on a single canvas element.
 * Using one canvas removes any CSS letterboxing / alignment issues.
 */
function drawCanvasOverlay(
  canvas: HTMLCanvasElement,
  imgEl: HTMLImageElement,
  pose: PoseResult,
) {
  const ratio = imgEl.naturalWidth / imgEl.naturalHeight
  canvas.height = MAX_CANVAS_HEIGHT
  canvas.width  = Math.round(MAX_CANVAS_HEIGHT * ratio)

  const cw = canvas.width
  const ch = canvas.height
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // 1. Draw the photo
  ctx.drawImage(imgEl, 0, 0, cw, ch)

  const lm = pose.landmarks

  // Helper: normalised coords → canvas pixels
  const px = (normX: number) => normX * cw
  const py = (normY: number) => normY * ch

  // 2. Skeleton connections
  ctx.strokeStyle = 'rgba(99,102,241,0.85)'
  ctx.lineWidth   = 2
  for (const [i, j] of POSE_CONNECTIONS) {
    const a = lm[i]
    const b = lm[j]
    if (!a || !b || a.visibility < 0.3 || b.visibility < 0.3) continue
    ctx.beginPath()
    ctx.moveTo(px(a.x), py(a.y))
    ctx.lineTo(px(b.x), py(b.y))
    ctx.stroke()
  }

  // 3. Landmark dots
  ctx.fillStyle = 'rgba(99,102,241,0.9)'
  for (const point of lm) {
    if (point.visibility < 0.3) continue
    ctx.beginPath()
    ctx.arc(px(point.x), py(point.y), 3, 0, Math.PI * 2)
    ctx.fill()
  }

  // 4. Measurement lines
  const drawMeasureLine = (
    iA: number, iB: number,
    color: string,
  ) => {
    const a = lm[iA]
    const b = lm[iB]
    if (!a || !b || a.visibility < 0.4 || b.visibility < 0.4) return
    ctx.strokeStyle = color
    ctx.lineWidth   = 2
    ctx.setLineDash([5, 4])
    ctx.beginPath()
    ctx.moveTo(px(a.x), py(a.y))
    ctx.lineTo(px(b.x), py(b.y))
    ctx.stroke()
    ctx.setLineDash([])
  }

  drawMeasureLine(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER, '#22c55e')   // shoulders
  drawMeasureLine(LM.LEFT_HIP,      LM.RIGHT_HIP,      '#f59e0b')   // hips
}

// ── Drop-zone sub-component ────────────────────────────────────────────────

interface DropZoneProps {
  label: string
  required?: boolean
  file: File | null
  onChange: (f: File | null) => void
  hint?: string
}

function DropZone({ label, required, file, onChange, hint }: DropZoneProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <label className={`flex items-center justify-center gap-3 border-2 border-dashed rounded-xl p-4 cursor-pointer transition-colors ${
        file ? 'border-brand-400 bg-brand-50' : 'border-gray-300 hover:border-brand-300'
      }`}>
        <input
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
        <span className="text-2xl">{file ? '✅' : '📷'}</span>
        <div className="text-sm text-left">
          <p className={file ? 'text-brand-700 font-medium' : 'text-gray-600'}>
            {file ? file.name : `Choisir ${label.toLowerCase()}`}
          </p>
          {hint && !file && <p className="text-xs text-gray-400">{hint}</p>}
        </div>
      </label>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function PhotoPrecisionCapture({
  initialHeight = 175,
  initialWeight = 70,
  onComplete,
  onCancel,
}: Props) {
  // ── State ────────────────────────────────────────────────────────────

  const [step, setStep]           = useState<Step>('upload')
  const [frontFile, setFrontFile] = useState<File | null>(null)
  const [sideFile, setSideFile]   = useState<File | null>(null)
  const [height, setHeight]       = useState(initialHeight)
  const [weight, setWeight]       = useState(initialWeight)
  const [statusMsg, setStatusMsg] = useState('')
  const [errors, setErrors]       = useState<string[]>([])
  const [warnings, setWarnings]   = useState<string[]>([])
  const [estimate, setEstimate]   = useState<BodyParamsEstimate | null>(null)

  // Refs: the canvas for the result overlay, and the loaded image element
  const canvasRef   = useRef<HTMLCanvasElement>(null)
  const frontImgRef = useRef<HTMLImageElement | null>(null)
  const frontPoseRef = useRef<PoseResult | null>(null)

  // Prewarm on mount
  useEffect(() => { prewarmPoseLandmarker() }, [])

  // Redraw canvas whenever pose is updated
  useEffect(() => {
    const canvas   = canvasRef.current
    const img      = frontImgRef.current
    const pose     = frontPoseRef.current
    if (!canvas || !img || !pose) return
    drawCanvasOverlay(canvas, img, pose)
  })   // runs after every render that changes refs

  // ── Analyse ──────────────────────────────────────────────────────────

  const handleAnalyse = useCallback(async () => {
    if (!frontFile) return
    setStep('processing')
    setErrors([])
    setWarnings([])
    setEstimate(null)
    frontImgRef.current  = null
    frontPoseRef.current = null
    setStatusMsg('Chargement du modèle MediaPipe…')

    try {
      const frontImg = await loadImageElement(frontFile)
      const sideImg  = sideFile ? await loadImageElement(sideFile) : null

      setStatusMsg('Détection de la pose…')
      const [frontResult, sideResult] = await Promise.all([
        detectPoseFromImage(frontImg),
        sideImg ? detectPoseFromImage(sideImg) : Promise.resolve(null),
      ])

      // Quality validation
      const fq = validatePhotoQuality(frontResult, 'front')
      const sq = sideResult ? validatePhotoQuality(sideResult, 'side') : { errors: [], warnings: [] }
      const allErrors   = [...fq.errors,   ...sq.errors.map(e => `(Profil) ${e}`)]
      const allWarnings = [...fq.warnings, ...sq.warnings.map(w => `(Profil) ${w}`)]

      if (allErrors.length > 0) {
        setErrors(allErrors)
        setWarnings(allWarnings)
        setStep('results')
        return
      }

      setStatusMsg('Calcul des mesures…')
      const est = estimateBodyParams(frontResult!, sideResult, height / 100, weight)

      // Store for canvas drawing
      frontImgRef.current  = frontImg
      frontPoseRef.current = frontResult

      setWarnings(allWarnings)
      setEstimate(est)
      setStep('results')

    } catch (err) {
      console.error('Photo analysis error:', err)
      setErrors(["Une erreur est survenue lors de l'analyse. Réessayez avec une autre photo."])
      setStep('results')
    }
  }, [frontFile, sideFile, height, weight])

  const handleRetry = () => {
    setStep('upload')
    setEstimate(null)
    setErrors([])
    setWarnings([])
    frontImgRef.current  = null
    frontPoseRef.current = null
  }

  // ── Step 1 — Upload ──────────────────────────────────────────────────

  if (step === 'upload') {
    return (
      <div className="space-y-5">
        <div className="text-sm text-gray-600 space-y-1">
          <p>Prenez deux photos debout, corps entier visible, sur fond uni.</p>
          <ul className="list-disc list-inside text-xs text-gray-500 space-y-0.5 mt-1">
            <li>Bras légèrement écartés du corps</li>
            <li>Lumière uniforme — vêtements ajustés (pas de manteau)</li>
            <li>Corps doit remplir au moins 60 % de la hauteur de la photo</li>
          </ul>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Taille (cm) <span className="text-red-400">*</span>
            </label>
            <input
              type="number" min={140} max={220}
              value={height}
              onChange={(e) => setHeight(parseInt(e.target.value) || 175)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Poids (kg) <span className="text-red-400">*</span>
            </label>
            <input
              type="number" min={40} max={200}
              value={weight}
              onChange={(e) => setWeight(parseInt(e.target.value) || 70)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
        </div>

        <DropZone
          label="Photo de face"
          required
          file={frontFile}
          onChange={setFrontFile}
          hint="Face à l'appareil, bras légèrement écartés"
        />
        <DropZone
          label="Photo de profil"
          file={sideFile}
          onChange={setSideFile}
          hint="Recommandée pour les circonférences (poitrine, taille)"
        />

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 border border-gray-300 text-gray-600 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-50 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleAnalyse}
            disabled={!frontFile}
            className="flex-1 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-xl text-sm transition-colors"
          >
            Analyser les photos
          </button>
        </div>
      </div>
    )
  }

  // ── Step 2 — Processing ──────────────────────────────────────────────

  if (step === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12">
        <div className="w-10 h-10 border-2 border-gray-200 border-t-brand-500 rounded-full animate-spin" />
        <p className="text-sm text-gray-600">{statusMsg || 'Analyse en cours…'}</p>
        <p className="text-xs text-gray-400 max-w-xs text-center">
          Le modèle MediaPipe se charge depuis internet la première fois (~25 Mo).
        </p>
      </div>
    )
  }

  // ── Step 3 — Results ─────────────────────────────────────────────────

  const hasErrors      = errors.length > 0
  const confidence     = estimate?.overallConfidence ?? 0
  const confidenceHigh = confidence >= 0.7
  const confidenceLow  = confidence < 0.4

  return (
    <div className="space-y-4">
      {/* Blocking errors */}
      {hasErrors && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-1.5">
          <p className="text-sm font-semibold text-red-700">Photo non utilisable</p>
          {errors.map((e, i) => (
            <p key={i} className="text-sm text-red-600">• {e}</p>
          ))}
        </div>
      )}

      {/* Warnings */}
      {!hasErrors && warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-1">
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-700">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Quality banner */}
      {!hasErrors && estimate && (
        <div className={`rounded-xl px-4 py-3 text-sm font-medium ${
          confidenceHigh ? 'bg-green-50 text-green-700'
          : confidenceLow ? 'bg-red-50 text-red-700'
          : 'bg-amber-50 text-amber-700'
        }`}>
          {confidenceHigh
            ? `Bonne précision (${Math.round(confidence * 100)} %) — vous pouvez appliquer ces mesures.`
            : confidenceLow
            ? `Précision faible (${Math.round(confidence * 100)} %) — nous recommandons de reprendre la photo.`
            : `Précision correcte (${Math.round(confidence * 100)} %) — résultat utilisable.`
          }
        </div>
      )}

      {/* Single canvas: photo + skeleton overlay */}
      {!hasErrors && frontImgRef.current && frontPoseRef.current && (
        <canvas
          ref={canvasRef}
          className="w-full rounded-xl"
        />
      )}

      {/* Measurement confidence panel */}
      {estimate && !hasErrors && (
        <MeasurementConfidencePanel estimate={estimate} />
      )}

      {/* Action buttons */}
      <div className="flex gap-3 pt-1">
        <button
          onClick={handleRetry}
          className="flex-1 border border-gray-300 text-gray-600 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-50 transition-colors"
        >
          Reprendre
        </button>
        {estimate && !hasErrors && (
          <button
            onClick={() => onComplete(estimate.params, estimate.overallConfidence)}
            className="flex-1 bg-brand-500 hover:bg-brand-600 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors"
          >
            Appliquer au mannequin
          </button>
        )}
      </div>
    </div>
  )
}
