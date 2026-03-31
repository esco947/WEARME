import type { BodyParamsEstimate, RawMeasurements } from '../lib/body-measurements'
import type { BodyParams } from '../types'

interface Props {
  estimate: BodyParamsEstimate
}

interface Row {
  key: keyof BodyParams
  label: string
  getRaw: (r: RawMeasurements) => number | null
  formatRaw: (v: number) => string
}

const LANDMARK_ROWS: Row[] = [
  {
    key: 'shoulder_width',
    label: 'Largeur épaules',
    getRaw: (r) => r.shoulder_width_m,
    formatRaw: (v) => `${(v * 100).toFixed(1)} cm`,
  },
  {
    key: 'hips',
    label: 'Largeur hanches',
    getRaw: (r) => r.hip_width_m,
    formatRaw: (v) => `${(v * 100).toFixed(1)} cm`,
  },
  {
    key: 'arm_length',
    label: 'Longueur bras',
    getRaw: (r) => r.arm_length_m,
    formatRaw: (v) => `${(v * 100).toFixed(0)} cm`,
  },
  {
    key: 'leg_length',
    label: 'Longueur jambe',
    getRaw: (r) => r.leg_length_m,
    formatRaw: (v) => `${(v * 100).toFixed(0)} cm`,
  },
]

const DEPTH_ROWS: Row[] = [
  {
    key: 'chest',
    label: 'Profondeur poitrine',
    getRaw: (r) => r.chest_depth_m,
    formatRaw: (v) => `${(v * 100).toFixed(1)} cm`,
  },
  {
    key: 'belly',
    label: 'Profondeur ventre',
    getRaw: (r) => r.belly_depth_m,
    formatRaw: (v) => `${(v * 100).toFixed(1)} cm`,
  },
  {
    key: 'fesses',
    label: 'Profondeur fesses',
    getRaw: (r) => r.hip_depth_m,
    formatRaw: (v) => `${(v * 100).toFixed(1)} cm`,
  },
]

function ConfidenceBar({ value }: { value: number }) {
  const pct   = Math.round(value * 100)
  const color = value >= 0.7 ? 'bg-green-500' : value >= 0.4 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

function ConfidenceBadge({ value }: { value: number }) {
  if (value >= 0.7) return <span className="text-green-600 text-xs font-medium">Fiable</span>
  if (value >= 0.4) return <span className="text-amber-600 text-xs font-medium">Approx.</span>
  return <span className="text-red-500 text-xs font-medium">Incertain</span>
}

function MeasureRow({ row, raw, conf }: { row: Row; raw: RawMeasurements; conf: number }) {
  const rawVal = row.getRaw(raw)
  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-white">
      <div className="w-40 shrink-0">
        <p className="text-xs font-medium text-gray-700">{row.label}</p>
        {rawVal != null && (
          <p className="text-xs text-gray-400">{row.formatRaw(rawVal)}</p>
        )}
      </div>
      <div className="flex-1">
        <ConfidenceBar value={conf} />
      </div>
    </div>
  )
}

export default function MeasurementConfidencePanel({ estimate }: Props) {
  const { rawMeasurements: raw, confidences, overallConfidence, hasDepthData } = estimate

  return (
    <div className="space-y-3">
      {/* Overall confidence header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Précision globale</span>
        <ConfidenceBadge value={overallConfidence} />
      </div>
      <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            overallConfidence >= 0.7 ? 'bg-green-500'
            : overallConfidence >= 0.4 ? 'bg-amber-400'
            : 'bg-red-400'
          }`}
          style={{ width: `${Math.round(overallConfidence * 100)}%` }}
        />
      </div>

      {/* Landmark rows — always visible */}
      <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 overflow-hidden">
        {LANDMARK_ROWS.map((row) => (
          <MeasureRow key={row.key} row={row} raw={raw} conf={confidences[row.key]} />
        ))}
      </div>

      {/* Depth rows — only when side photo provided */}
      {hasDepthData ? (
        <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 overflow-hidden">
          {DEPTH_ROWS.map((row) => (
            <MeasureRow key={row.key} row={row} raw={raw} conf={confidences[row.key]} />
          ))}
        </div>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
          Ajoutez une photo de profil pour estimer les formes (ventre, fesses, tour de poitrine).
        </p>
      )}

      {/* Musculature note */}
      <p className="text-xs text-gray-400 italic">
        La musculature ne peut pas être estimée depuis une photo — ajustez manuellement si besoin.
      </p>
    </div>
  )
}
