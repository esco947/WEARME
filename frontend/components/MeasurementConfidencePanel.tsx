'use client';

import type { BodyMeasurements, MeasurementConfidence } from '@/lib/body-measurements';

interface Row {
  key: keyof MeasurementConfidence;
  label: string;
  getValue: (m: BodyMeasurements) => string;
  source: 'saisie' | 'landmarks' | 'ellipse' | 'morphologie';
}

const ROWS: Row[] = [
  { key: 'epaules',         label: 'Largeur des épaules',  getValue: m => `${m.epaules.toFixed(1)} cm`,          source: 'landmarks'   },
  { key: 'poitrine',        label: 'Tour de poitrine',     getValue: m => `${m.poitrine.toFixed(0)} cm`,          source: 'ellipse'     },
  { key: 'tour_taille',     label: 'Tour de taille',       getValue: m => `${m.tour_taille.toFixed(0)} cm`,       source: 'ellipse'     },
  { key: 'hanches',         label: 'Tour de hanches',      getValue: m => `${m.hanches.toFixed(0)} cm`,           source: 'ellipse'     },
  { key: 'longueur_jambes', label: 'Longueur des jambes',  getValue: m => `${m.longueur_jambes.toFixed(1)} cm`,   source: 'landmarks'   },
  { key: 'longueur_bras',   label: 'Longueur des bras',    getValue: m => `${m.longueur_bras.toFixed(1)} cm`,     source: 'landmarks'   },
  { key: 'forme_jambes',    label: 'Forme des jambes',     getValue: m => fmtForm(m.forme_jambes),                source: 'morphologie' },
  { key: 'forme_bras',      label: 'Forme des bras',       getValue: m => fmtForm(m.forme_bras),                  source: 'morphologie' },
  { key: 'cou',             label: 'Cou',                  getValue: m => fmtForm(m.cou),                         source: 'morphologie' },
  { key: 'posture',         label: 'Posture',              getValue: m => fmtForm(m.posture),                     source: 'morphologie' },
];

function fmtForm(v: number): string {
  return v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1);
}

const SOURCE_LABEL: Record<Row['source'], string> = {
  saisie:      'saisie',
  landmarks:   'landmarks 3D',
  ellipse:     'ellipse photo',
  morphologie: 'silhouette',
};

function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? 'bg-green-500' :
    pct >= 40 ? 'bg-amber-400' :
                'bg-red-400';
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-mono w-8 text-right ${
        pct >= 70 ? 'text-green-600' : pct >= 40 ? 'text-amber-500' : 'text-red-500'
      }`}>
        {pct}%
      </span>
    </div>
  );
}

export default function MeasurementConfidencePanel({
  measurements,
  confidence,
}: {
  measurements: BodyMeasurements;
  confidence: MeasurementConfidence;
}) {
  return (
    <div className="space-y-1.5">
      {/* Saisies directes */}
      <div className="flex justify-between items-center py-1 border-b border-gray-100 mb-2">
        <div>
          <span className="text-sm font-medium text-gray-700">Taille</span>
          <span className="ml-2 text-xs text-gray-400">saisie</span>
        </div>
        <span className="text-sm font-mono text-indigo-600">{measurements.taille} cm</span>
      </div>
      <div className="flex justify-between items-center py-1 border-b border-gray-100 mb-2">
        <div>
          <span className="text-sm font-medium text-gray-700">Poids</span>
          <span className="ml-2 text-xs text-gray-400">saisie</span>
        </div>
        <span className="text-sm font-mono text-indigo-600">{measurements.poids} kg</span>
      </div>

      {/* Mesures estimées */}
      {ROWS.map(({ key, label, getValue, source }) => {
        const conf = confidence[key];
        return (
          <div key={key} className="py-1">
            <div className="flex justify-between items-center mb-0.5">
              <div className="flex items-baseline gap-1.5">
                <span className="text-sm font-medium text-gray-700">{label}</span>
                <span className="text-xs text-gray-400">{SOURCE_LABEL[source]}</span>
              </div>
              <span className="text-sm font-mono text-indigo-600">{getValue(measurements)}</span>
            </div>
            <ConfBar value={conf} />
          </div>
        );
      })}

      <p className="text-xs text-gray-400 mt-3 italic">
        Estimation basée sur photos face + profil — pas un scan 3D. Ajustez les sliders si nécessaire.
      </p>
    </div>
  );
}
