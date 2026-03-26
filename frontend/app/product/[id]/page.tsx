'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getProduct, getToken, Product } from '@/lib/api';

const TYPE_LABELS: Record<string, string> = {
  top: 'Haut',
  bottom: 'Bas',
  dress: 'Robe',
  jacket: 'Veste',
};

export default function ProductPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!getToken());

    async function load() {
      try {
        const data = await getProduct(id);
        setProduct(data);
      } catch {
        setError('Produit introuvable');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  function handleTryOn() {
    if (!isLoggedIn) {
      router.push('/auth');
    } else {
      router.push(`/avatar`);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="h-96 bg-white rounded-2xl border border-gray-200 animate-pulse" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10 text-center">
        <p className="text-red-500 mb-4">{error || 'Produit introuvable'}</p>
        <Link href="/catalogue" className="text-indigo-600 hover:underline">
          Retour au catalogue
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <Link href="/catalogue" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← Retour au catalogue
      </Link>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-2">
          {/* Image */}
          <div className="aspect-square bg-gray-100 flex items-center justify-center">
            <span className="text-8xl">👕</span>
          </div>

          {/* Infos */}
          <div className="p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>
              </div>
              <p className="text-gray-500 text-sm mb-1">{product.brand}</p>
              <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full mb-4">
                {TYPE_LABELS[product.type] ?? product.type}
              </span>

              <p className="text-3xl font-bold text-indigo-600 mb-4">
                {product.price.toFixed(2)} €
              </p>

              <p className="text-gray-600 text-sm mb-6">{product.description}</p>

              {/* Tailles */}
              <div className="mb-6">
                <p className="text-sm font-medium text-gray-700 mb-2">Tailles disponibles</p>
                <div className="flex flex-wrap gap-2">
                  {product.sizes.map((size) => (
                    <span
                      key={size}
                      className="border border-gray-300 text-gray-700 text-sm px-3 py-1 rounded-lg"
                    >
                      {size}
                    </span>
                  ))}
                </div>
              </div>

              {/* Couleur */}
              <p className="text-sm text-gray-500 mb-6">
                Couleur : <span className="text-gray-800 font-medium">{product.color}</span>
              </p>
            </div>

            {/* Bouton Essayer */}
            <button
              onClick={handleTryOn}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-semibold text-lg transition-colors"
            >
              {isLoggedIn ? '✨ Essayer en 3D' : '🔒 Connexion pour essayer'}
            </button>

            {!isLoggedIn && (
              <p className="text-xs text-gray-400 text-center mt-2">
                Créez un compte gratuit pour accéder à l&apos;essayage virtuel.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
