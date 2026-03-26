'use client';

import { Suspense, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';

// Barème de taille : 0 à 200 cm
function HeightRuler() {
  const X = 0.78;

  const ticks = Array.from({ length: 21 }, (_, i) => ({
    cm: i * 10,
    y: i * 0.1,
    major: i % 5 === 0,
  }));

  return (
    <group position={[X, 0, 0]}>
      {/* Barre verticale */}
      <mesh position={[0, 1.0, 0]}>
        <boxGeometry args={[0.005, 2.0, 0.005]} />
        <meshBasicMaterial color="#64748b" />
      </mesh>

      {ticks.map(({ cm, y, major }) => (
        <group key={cm} position={[0, y, 0]}>
          {/* Trait de graduation */}
          <mesh position={[major ? 0.028 : 0.016, 0, 0]}>
            <boxGeometry args={[major ? 0.056 : 0.032, major ? 0.005 : 0.003, 0.004]} />
            <meshBasicMaterial color={major ? '#e2e8f0' : '#94a3b8'} />
          </mesh>

          {/* Étiquette HTML sur les graduations majeures */}
          {major && (
            <Html
              position={[0.11, 0, 0]}
              center={false}
              style={{
                color: '#e2e8f0',
                fontSize: '11px',
                fontFamily: 'monospace',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
                userSelect: 'none',
                textShadow: '0 1px 3px rgba(0,0,0,0.8)',
              }}
            >
              {cm === 0 ? '0' : `${cm} cm`}
            </Html>
          )}
        </group>
      ))}
    </group>
  );
}

function AvatarModel({ glbUrl }: { glbUrl: string }) {
  const { scene } = useGLTF(glbUrl);
  const ref = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!ref.current) return;

    const box = new THREE.Box3().setFromObject(ref.current);

    // Centrer X/Z, pieds à y=0
    ref.current.position.x -= (box.max.x + box.min.x) / 2;
    ref.current.position.z -= (box.max.z + box.min.z) / 2;
    ref.current.position.y -= box.min.y;

    // Matériau skin
    ref.current.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = new THREE.MeshStandardMaterial({
          color: '#c8a882',
          roughness: 0.75,
          metalness: 0.0,
        });
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
  }, [scene]);

  return <primitive ref={ref} object={scene} />;
}

function ModelLoader({ glbUrl }: { glbUrl: string }) {
  useEffect(() => {
    return () => {
      useGLTF.clear(glbUrl);
    };
  }, [glbUrl]);

  return (
    <Suspense fallback={null}>
      <AvatarModel key={glbUrl} glbUrl={glbUrl} />
    </Suspense>
  );
}

export default function AvatarScene({ glbUrl, height = '500px' }: { glbUrl: string; height?: string }) {
  return (
    <div style={{ width: '100%', height }} className="rounded-xl overflow-hidden bg-slate-800">
      <Canvas
        camera={{ position: [0, 1.0, 3.2], fov: 44 }}
        gl={{
          alpha: false,
          antialias: false,
          powerPreference: 'low-power',
          failIfMajorPerformanceCaveat: false,
        }}
        onCreated={({ gl }) => gl.setClearColor('#1e293b')}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[2, 5, 3]} intensity={1.4} castShadow shadow-mapSize={[1024, 1024]} />
        <directionalLight position={[-3, 3, 2]} intensity={0.5} />
        <directionalLight position={[0, 2, -4]} intensity={0.3} color="#b0c4de" />
        <hemisphereLight args={['#e8d5b7', '#334155', 0.3]} />

        <HeightRuler />

        {glbUrl && <ModelLoader glbUrl={glbUrl} />}

        <OrbitControls
          target={[0, 0.85, 0]}
          minDistance={1.5}
          maxDistance={5}
          enablePan={false}
        />
      </Canvas>
    </div>
  );
}
