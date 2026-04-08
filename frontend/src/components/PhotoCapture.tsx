import { useRef, useState } from 'react'
import { photoFit } from '../api/client'
import type { Avatar } from '../types'

interface Props {
  gender: 'male' | 'female'
  onComplete: (avatar: Avatar) => void
}

export default function PhotoCapture({ gender, onComplete }: Props) {
  const [frontFile, setFrontFile] = useState<File | null>(null)
  const [sideFile,  setSideFile]  = useState<File | null>(null)
  const [heightCm,  setHeightCm]  = useState(175)
  const [fitting,   setFitting]   = useState(false)
  const [error,     setError]     = useState('')

  const frontRef = useRef<HTMLInputElement>(null)
  const sideRef  = useRef<HTMLInputElement>(null)

  const handleSubmit = async () => {
    if (!frontFile || !sideFile) {
      setError('Les deux photos (face et profil) sont obligatoires.')
      return
    }
    if (heightCm < 140 || heightCm > 220) {
      setError('La taille doit etre entre 140 et 220 cm.')
      return
    }

    setFitting(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('front', frontFile)
      fd.append('side', sideFile)
      fd.append('height_m', String(heightCm / 100))
      fd.append('gender', gender)
      const updated = await photoFit(fd)
      onComplete(updated)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erreur lors de l\'analyse photo.')
    } finally {
      setFitting(false)
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-600">
        Chargez une photo de face et une photo de profil (fond uni, corps entier visible).
        L'analyse prend 10-30 secondes.
      </p>

      {/* Front photo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Photo de face <span className="text-red-500">*</span>
        </label>
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-brand-400 transition-colors"
          onClick={() => frontRef.current?.click()}
        >
          {frontFile ? (
            <span className="text-sm text-brand-600">{frontFile.name}</span>
          ) : (
            <span className="text-sm text-gray-400">Cliquer pour choisir une photo</span>
          )}
        </div>
        <input
          ref={frontRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => setFrontFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {/* Side photo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Photo de profil <span className="text-red-500">*</span>
        </label>
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-brand-400 transition-colors"
          onClick={() => sideRef.current?.click()}
        >
          {sideFile ? (
            <span className="text-sm text-brand-600">{sideFile.name}</span>
          ) : (
            <span className="text-sm text-gray-400">Cliquer pour choisir une photo</span>
          )}
        </div>
        <input
          ref={sideRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => setSideFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {/* Height */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Taille (cm)
        </label>
        <input
          type="number"
          min={140}
          max={220}
          value={heightCm}
          onChange={(e) => setHeightCm(parseInt(e.target.value, 10))}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
        />
      </div>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={fitting || !frontFile || !sideFile}
        className="w-full py-3 bg-brand-500 text-white rounded-lg font-medium text-sm
                   hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {fitting ? 'Analyse en cours...' : 'Analyser les photos'}
      </button>

      {fitting && (
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-gray-400 mt-2">Cela peut prendre 10-30 secondes...</p>
        </div>
      )}
    </div>
  )
}
