import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import AuthPage from './pages/AuthPage'
import CataloguePage from './pages/CataloguePage'
import ProductPage from './pages/ProductPage'
import AvatarPage from './pages/AvatarPage'
import FittingPage from './pages/FittingPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50">
                <Navbar />
                <main>
                  <Routes>
                    <Route path="/" element={<Navigate to="/catalogue" replace />} />
                    <Route path="/catalogue" element={<CataloguePage />} />
                    <Route path="/catalogue/:id" element={<ProductPage />} />
                    <Route path="/fitting/:id" element={<FittingPage />} />
                    <Route path="/avatar" element={<AvatarPage />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
