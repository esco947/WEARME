'use client';

import { useEffect, useState } from 'react';
import { getProducts, Product } from '@/lib/api';
import ProductCard from '@/components/ProductCard';

const TYPE_OPTIONS = [
  { value: '', label: 'Tous' },
  { value: 'top', label: 'Hauts' },
  { value: 'bottom', label: 'Bas' },
  { value: 'dress', label: 'Robes' },
  { value: 'jacket', label: 'Vestes' },
];

const BRAND_OPTIONS = ['Toutes', 'UrbanFit', 'ModaVerde'];

export default function CataloguePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await getProducts(
          typeFilter || undefined,
          brandFilter || undefined
        );
        setProducts(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [typeFilter, brandFilter]);

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Catalogue</h1>
      <p className="text-gray-500 mb-8">Découvrez notre sélection de vêtements.</p>

      {/* Filtres */}
      <div className="flex flex-wrap gap-4 mb-8">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Catégorie</label>
          <div className="flex gap-2 flex-wrap">
            {TYPE_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setTypeFilter(value)}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  typeFilter === value
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Marque</label>
          <div className="flex gap-2 flex-wrap">
            {BRAND_OPTIONS.map((brand) => {
              const value = brand === 'Toutes' ? '' : brand;
              return (
                <button
                  key={brand}
                  onClick={() => setBrandFilter(value)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    brandFilter === value
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
                  }`}
                >
                  {brand}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Grille produits */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 h-64 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-16 text-red-600">{error}</div>
      ) : products.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          Aucun produit trouvé pour ces filtres.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
