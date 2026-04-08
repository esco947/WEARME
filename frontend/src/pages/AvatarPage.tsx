import { useEffect, useState } from 'react'
import { getAvatar, setGender } from '../api/client'
import { useAvatarStore } from '../store/avatarStore'
import { useAuthStore } from '../store/authStore'
import AvatarViewer, { SkinTonePicker, loadStoredSkinTone, storeSkinTone } from '../components/AvatarViewer'
import type { SkinToneId } from '../components/AvatarViewer'
import SliderPanel from '../components/SliderPanel'
import PhotoCapture from '../components/PhotoCapture'
import type { Avatar } from '../types'

type Tab = 'manuel' | 'photo'

export default function AvatarPage() {
  const { gender, measurements, meshVersion, loading, error, setFromAvatar, setLoading, setError } = useAvatarStore()
  const token = useAuthStore((s) => s.token)

  const [avatar,     setLocalAvatar] = useState<Avatar | null>(null)
  const [skinTone,   setSkinTone]    = useState<SkinToneId>(loadStoredSkinTone)
  const [activeTab,  setActiveTab]   = useState<Tab>('manuel')
  const [genderSaving, setGenderSaving] = useState(false)

  // meshVersion is tracked via the store so AvatarViewer refreshes when avatar changes
  const refreshKey = meshVersion

  // Load avatar on mount
  useEffect(() => {
    setLoading(true)
    getAvatar()
      .then((av) => {
        setLocalAvatar(av)
        setFromAvatar(av)
      })
      .catch(() => setError("Impossible de charger l'avatar."))
      .finally(() => setLoading(false))
  }, [])

  const handleAvatarUpdate = (av: Avatar) => {
    setLocalAvatar(av)
    setFromAvatar(av)
  }

  const handleGender = async (g: 'male' | 'female') => {
    setGenderSaving(true)
    try {
      const av = await setGender(g)
      handleAvatarUpdate(av)
    } catch {
      setError('Erreur lors du changement de genre.')
    } finally {
      setGenderSaving(false)
    }
  }

  if (loading) return <div className="text-center py-16 text-gray-400">Chargement...</div>
  if (error && !avatar) return <div className="text-center py-16 text-red-400">{error}</div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Mon Avatar</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

        {/* Left: 3D Viewer + skin tone + measurements */}
        <div className="space-y-3 sticky top-4">
          <AvatarViewer token={token} refreshKey={refreshKey} height="520px" skinTone={skinTone} />

          <div className="bg-white rounded-xl shadow px-4 py-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Couleur de peau</p>
            <SkinTonePicker
              value={skinTone}
              onChange={(id) => { setSkinTone(id); storeSkinTone(id) }}
            />
          </div>

          {/* Measurements panel */}
          {Object.keys(measurements).length > 0 && (
            <div className="bg-white rounded-xl shadow px-4 py-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Mensurations</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                {[
                  ['Taille',      'height'],
                  ['Poitrine',    'chest_circumference'],
                  ['Taille',      'waist_circumference'],
                  ['Hanches',     'hip_circumference'],
                  ['Epaules',     'shoulder_width'],
                  ['Entrejambe',  'inseam'],
                ].map(([label, key]) =>
                  measurements[key] !== undefined ? (
                    <>
                      <span key={key + '-label'} className="text-gray-500">{label}</span>
                      <span key={key + '-val'} className="font-medium text-right">
                        {Math.round(measurements[key] * 100)} cm
                      </span>
                    </>
                  ) : null
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: Controls */}
        <div className="bg-white rounded-2xl shadow p-6 space-y-5">

          {/* Gender */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">Genre</p>
            <div className="flex gap-2">
              {(['male', 'female'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => handleGender(g)}
                  disabled={genderSaving}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    gender === g
                      ? 'bg-brand-500 text-white border-brand-500'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-brand-400'
                  }`}
                >
                  {{ male: 'Homme', female: 'Femme' }[g]}
                </button>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <div className="flex gap-0">
              {(['manuel', 'photo'] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setActiveTab(t)}
                  className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === t
                      ? 'border-brand-500 text-brand-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {t === 'manuel' ? 'Manuel' : 'Photo'}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Manuel */}
          {activeTab === 'manuel' && avatar && (
            <SliderPanel
              avatar={avatar}
              onUpdate={(av) => {
                handleAvatarUpdate(av)
              }}
            />
          )}

          {/* Tab Photo */}
          {activeTab === 'photo' && (
            <PhotoCapture
              gender={gender}
              onComplete={(av) => {
                handleAvatarUpdate(av)
                setActiveTab('manuel')
              }}
            />
          )}

        </div>
      </div>
    </div>
  )
}
