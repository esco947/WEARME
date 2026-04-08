import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useAvatarStore } from '../store/avatarStore'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const resetAvatar = useAvatarStore((s) => s.reset)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    resetAvatar()
    navigate('/auth')
  }

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <span className="text-xl font-bold text-brand-600 tracking-tight">WEARME</span>

        <div className="flex items-center gap-4">
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">{user.email}</span>
              <button
                onClick={handleLogout}
                className="text-xs text-gray-500 hover:text-red-500 transition-colors"
              >
                Deconnexion
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
