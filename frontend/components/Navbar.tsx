'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getToken, removeToken } from '@/lib/api';

export default function Navbar() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!getToken());
  }, []);

  function handleLogout() {
    removeToken();
    setIsLoggedIn(false);
    router.push('/');
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-indigo-600 tracking-tight">
          FitView
        </Link>

        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm text-gray-600 hover:text-indigo-600 transition-colors">
            Accueil
          </Link>
          <Link href="/catalogue" className="text-sm text-gray-600 hover:text-indigo-600 transition-colors">
            Catalogue
          </Link>
          {isLoggedIn && (
            <Link href="/avatar" className="text-sm text-gray-600 hover:text-indigo-600 transition-colors">
              Mon Avatar
            </Link>
          )}

          {isLoggedIn ? (
            <button
              onClick={handleLogout}
              className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg transition-colors"
            >
              Déconnexion
            </button>
          ) : (
            <Link
              href="/auth"
              className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Connexion
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
