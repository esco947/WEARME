'use client';

import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { createAvatar, getToken } from '@/lib/api';
import type { BodyMeasurements, MeasurementConfidence } from '@/lib/body-measurements';

const AvatarScene = dynamic(() => import('@/components/AvatarScene'), { ssr: false });
const PhotoPrecisionCapture = dynamic(() => import('@/components/PhotoPrecisionCapture'), { ssr: false });

// ---------------------------------------------------------------------------
// Valeurs de référence SMPL par genre : [moyenne, écart-type]
// Basées sur les statistiques du dataset CAESAR utilisé pour entraîner SMPL
// ---------------------------------------------------------------------------
const REFS = {
  male: {
    poids:           [80.0, 16.0] as [number, number],
    taille:          [176.0, 7.0] as [number, number],
    epaules:         [44.0, 4.0]  as [number, number],
    poitrine:        [100.0, 10.0] as [number, number],
    tour_taille:     [90.0, 13.0] as [number, number],
    hanches:         [102.0, 11.0] as [number, number],
    longueur_jambes: [82.0, 5.0]  as [number, number],
    longueur_bras:   [62.0, 5.0]  as [number, number],
  },
  female: {
    poids:           [65.0, 14.0] as [number, number],
    taille:          [163.0, 7.0] as [number, number],
    epaules:         [37.0, 3.5]  as [number, number],
    poitrine:        [93.0, 10.0] as [number, number],
    tour_taille:     [76.0, 12.0] as [number, number],
    hanches:         [100.0, 12.0] as [number, number],
    longueur_jambes: [76.0, 5.0]  as [number, number],
    longueur_bras:   [57.0, 4.0]  as [number, number],
  },
  neutral: {
    poids:           [72.0, 15.0] as [number, number],
    taille:          [169.0, 8.0] as [number, number],
    epaules:         [40.5, 4.5]  as [number, number],
    poitrine:        [96.0, 11.0] as [number, number],
    tour_taille:     [82.0, 13.0] as [number, number],
    hanches:         [101.0, 12.0] as [number, number],
    longueur_jambes: [79.0, 6.0]  as [number, number],
    longueur_bras:   [59.0, 5.0]  as [number, number],
  },
};

interface Measurements {
  poids: number;
  taille: number;
  epaules: number;
  poitrine: number;
  tour_taille: number;
  hanches: number;
  longueur_jambes: number;
  forme_jambes: number;
  longueur_bras: number;
  forme_bras: number;
  cou: number;
  posture: number;
}

function defaultMeasurements(gender: string): Measurements {
  const r = REFS[gender as keyof typeof REFS] ?? REFS.neutral;
  return {
    poids:           r.poids[0],
    taille:          r.taille[0],
    epaules:         r.epaules[0],
    poitrine:        r.poitrine[0],
    tour_taille:     r.tour_taille[0],
    hanches:         r.hanches[0],
    longueur_jambes: r.longueur_jambes[0],
    forme_jambes:    0,
    longueur_bras:   r.longueur_bras[0],
    forme_bras:      0,
    cou:             0,
    posture:         0,
  };
}

function measurementsToBetas(m: Measurements, gender: string): number[] {
  const r = REFS[gender as keyof typeof REFS] ?? REFS.neutral;
  const clamp = (v: number) => Math.max(-3, Math.min(3, v));
  const norm = (val: number, [mean, std]: [number, number]) => clamp((val - mean) / std);
  return [
    -norm(m.taille,          r.taille),
    -norm(m.poids,           r.poids),
    norm(m.epaules,         r.epaules),
    norm(m.poitrine,        r.poitrine),
    norm(m.tour_taille,     r.tour_taille),
    norm(m.hanches,         r.hanches),
    norm(m.longueur_jambes, r.longueur_jambes),
    clamp(m.forme_jambes),
    norm(m.longueur_bras,   r.longueur_bras),
    clamp(m.forme_bras),
    clamp(m.cou),
    clamp(m.posture),
  ];
}

// ---------------------------------------------------------------------------
// Définition des sliders
// ---------------------------------------------------------------------------
type SliderDef =
  | { key: keyof Measurements; label: string; unit: 'kg' | 'cm'; min: number; max: number; step: number }
  | { key: keyof Measurements; label: string; unit: ''; min: -3; max: 3; step: 0.1; hint: string };

const SLIDERS: SliderDef[] = [
  // — Mensurations —
  { key: 'poids',           label: 'Poids',                 unit: 'kg', min: 40,  max: 150, step: 1   },
  { key: 'taille',          label: 'Taille',                unit: 'cm', min: 140, max: 215, step: 1   },
  { key: 'epaules',         label: 'Largeur des épaules',   unit: 'cm', min: 28,  max: 62,  step: 0.5 },
  { key: 'poitrine',        label: 'Tour de poitrine',      unit: 'cm', min: 60,  max: 145, step: 0.5 },
  { key: 'tour_taille',     label: 'Tour de taille',        unit: 'cm', min: 55,  max: 140, step: 0.5 },
  { key: 'hanches',         label: 'Largeur des hanches',   unit: 'cm', min: 70,  max: 145, step: 0.5 },
  { key: 'longueur_jambes', label: 'Longueur des jambes',   unit: 'cm', min: 60,  max: 100, step: 0.5 },
  { key: 'forme_jambes',    label: 'Forme des jambes',      unit: '',   min: -3,  max: 3,   step: 0.1, hint: 'mince ↔ épais' },
  { key: 'longueur_bras',   label: 'Longueur des bras',     unit: 'cm', min: 45,  max: 90,  step: 0.5 },
  { key: 'forme_bras',      label: 'Forme des bras',        unit: '',   min: -3,  max: 3,   step: 0.1, hint: 'mince ↔ épais' },
  { key: 'cou',             label: 'Cou',                   unit: '',   min: -3,  max: 3,   step: 0.1, hint: 'fin ↔ épais' },
  { key: 'posture',         label: 'Posture',               unit: '',   min: -3,  max: 3,   step: 0.1, hint: 'svelte ↔ cambré' },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function AvatarPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'manuel' | 'photo'>('manuel');
  const [photoFilled, setPhotoFilled] = useState(false);
  const [gender, setGender] = useState<'male' | 'female' | 'neutral'>('neutral');
  const [measurements, setMeasurements] = useState<Measurements>(() => defaultMeasurements('neutral'));
  const [glbUrl, setGlbUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!getToken()) router.push('/auth');
  }, [router]);

  // Réinitialise les mesures cm/kg aux moyennes du nouveau genre
  function handleGenderChange(g: 'male' | 'female' | 'neutral') {
    setGender(g);
    const def = defaultMeasurements(g);
    setMeasurements((prev) => ({
      ...def,
      // Conserver les paramètres de forme (sans unité)
      forme_jambes: prev.forme_jambes,
      forme_bras:   prev.forme_bras,
      cou:          prev.cou,
      posture:      prev.posture,
    }));
  }

  function handleSlider(key: keyof Measurements, value: number) {
    setMeasurements((prev) => ({ ...prev, [key]: value }));
  }

  function handleFromPhoto(m: BodyMeasurements, _c: MeasurementConfidence) {
    setMeasurements({
      taille:          m.taille,
      poids:           m.poids,
      epaules:         m.epaules,
      poitrine:        m.poitrine,
      tour_taille:     m.tour_taille,
      hanches:         m.hanches,
      longueur_jambes: m.longueur_jambes,
      forme_jambes:    m.forme_jambes,
      longueur_bras:   m.longueur_bras,
      forme_bras:      m.forme_bras,
      cou:             m.cou,
      posture:         m.posture,
    });
    setMode('manuel');
    setPhotoFilled(true);
  }

  async function handleGenerate() {
    setError('');
    setLoading(true);
    try {
      const betas = measurementsToBetas(measurements, gender);
      const data = await createAvatar(betas, gender);
      if (data.glb_url) {
        setGlbUrl(`${data.glb_url}?t=${Date.now()}`);
      } else {
        setError('Le serveur n\'a pas pu générer le GLB. Vérifiez les logs backend.');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur de génération');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Mon Avatar</h1>
      <p className="text-gray-500 mb-8">
        Renseignez vos mensurations pour générer un mannequin morphologique personnalisé.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Panneau de gauche : paramètres */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6">

          {/* Onglets Manuel / Photo */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-5">
            {(['manuel', 'photo'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  mode === m
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {m === 'manuel' ? '✏️ Saisie manuelle' : '📷 Photo précision'}
              </button>
            ))}
          </div>

          {/* Mode Photo */}
          {mode === 'photo' && (
            <PhotoPrecisionCapture
              gender={gender}
              onMeasurementsReady={handleFromPhoto}
            />
          )}

          {/* Bandeau mesures depuis photo */}
          {mode === 'manuel' && photoFilled && (
            <div className="mb-4 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-lg flex items-center justify-between">
              <p className="text-xs text-indigo-700">
                📷 Mesures pré-remplies depuis vos photos — ajustez si nécessaire.
              </p>
              <button
                onClick={() => setPhotoFilled(false)}
                className="text-xs text-indigo-400 hover:text-indigo-600 ml-2"
              >
                ✕
              </button>
            </div>
          )}

          {/* Sélecteur de genre */}
          <div className="mb-6">
            <p className="text-sm font-semibold text-gray-700 mb-2">Sexe</p>
            <div className="flex gap-3">
              {(['female', 'male', 'neutral'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => handleGenderChange(g)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    gender === g
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
                  }`}
                >
                  {g === 'female' ? '♀ Femme' : g === 'male' ? '♂ Homme' : '⊙ Neutre'}
                </button>
              ))}
            </div>
          </div>

          {mode === 'manuel' && (
            <>
              {/* Section Mensurations */}
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500 mb-3">
                Mensurations
              </p>
              <div className="space-y-4 mb-6">
                {SLIDERS.filter((s) => s.unit !== '').map((s) => (
                  <SliderRow
                    key={s.key}
                    def={s}
                    value={measurements[s.key]}
                    onChange={(v) => handleSlider(s.key, v)}
                  />
                ))}
              </div>

              {/* Section Morphologie */}
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500 mb-3 border-t border-gray-100 pt-4">
                Morphologie
              </p>
              <div className="space-y-4">
                {SLIDERS.filter((s) => s.unit === '').map((s) => (
                  <SliderRow
                    key={s.key}
                    def={s}
                    value={measurements[s.key]}
                    onChange={(v) => handleSlider(s.key, v)}
                  />
                ))}
              </div>
            </>
          )}

          {mode === 'manuel' && (
            <>
              {error && (
                <p className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="mt-6 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white py-3 rounded-xl font-medium transition-colors"
              >
                {loading ? 'Génération en cours...' : 'Générer mon avatar'}
              </button>
            </>
          )}
        </div>

        {/* Panneau de droite : viewer 3D */}
        <div>
          <h2 className="font-semibold text-gray-900 mb-4">Aperçu 3D</h2>
          <div className="relative">
            {glbUrl ? (
              <AvatarScene glbUrl={glbUrl} height="580px" />
            ) : (
              <div style={{ height: '580px' }} className="rounded-xl bg-slate-800 flex items-center justify-center">
                {loading ? (
                  <p className="text-white text-sm font-medium">Génération en cours...</p>
                ) : (
                  <div className="text-center text-gray-400">
                    <div className="text-5xl mb-3">🧍</div>
                    <p className="text-sm">Votre avatar apparaîtra ici</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composant slider réutilisable
// ---------------------------------------------------------------------------
function SliderRow({ def, value, onChange }: {
  def: SliderDef;
  value: number;
  onChange: (v: number) => void;
}) {
  const displayValue =
    def.unit === 'kg' ? `${Math.round(value)} kg`
    : def.unit === 'cm' ? `${value % 1 === 0 ? value : value.toFixed(1)} cm`
    : (value >= 0 ? `+${value.toFixed(1)}` : value.toFixed(1));

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-gray-700">{def.label}</span>
        <span className="text-xs text-indigo-600 font-mono min-w-[56px] text-right">
          {displayValue}
        </span>
      </div>
      {'hint' in def && def.hint && (
        <p className="text-xs text-gray-400 mb-1">{def.hint}</p>
      )}
      <input
        type="range"
        min={def.min}
        max={def.max}
        step={def.step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-indigo-600"
      />
    </div>
  );
}
