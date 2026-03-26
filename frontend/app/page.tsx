import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      {/* Hero */}
      <div className="text-center mb-20">
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
          Essayez vos vêtements{" "}
          <span className="text-indigo-600">en 3D</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          Créez votre avatar morphologique, parcourez notre catalogue et visualisez
          comment chaque vêtement vous ira — avant de l&apos;acheter.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/catalogue"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-medium text-lg transition-colors"
          >
            Parcourir le catalogue
          </Link>
          <Link
            href="/auth"
            className="border border-gray-300 hover:border-indigo-400 text-gray-700 hover:text-indigo-600 px-8 py-3 rounded-xl font-medium text-lg transition-colors"
          >
            Créer un compte
          </Link>
        </div>
      </div>

      {/* Comment ça marche */}
      <div>
        <h2 className="text-2xl font-bold text-center text-gray-900 mb-12">
          Comment ça marche
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              step: "1",
              title: "Créez votre avatar",
              description:
                "Ajustez quelques paramètres morphologiques pour générer un avatar 3D qui vous ressemble.",
              icon: "🧍",
            },
            {
              step: "2",
              title: "Parcourez le catalogue",
              description:
                "Explorez notre sélection de vêtements filtrés par type, marque et taille.",
              icon: "👗",
            },
            {
              step: "3",
              title: "Essayez en 3D",
              description:
                "Voyez instantanément comment chaque vêtement s'adapte à votre morphologie.",
              icon: "✨",
            },
          ].map(({ step, title, description, icon }) => (
            <div key={step} className="bg-white rounded-2xl p-8 border border-gray-200 text-center">
              <div className="text-4xl mb-4">{icon}</div>
              <div className="w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full font-bold text-sm flex items-center justify-center mx-auto mb-3">
                {step}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-500">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
