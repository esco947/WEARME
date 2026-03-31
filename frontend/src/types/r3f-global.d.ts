// Bridges @react-three/fiber v8 global JSX augmentation to React.JSX
// (needed because "jsx": "react-jsx" resolves types from react/jsx-runtime,
//  not the global JSX namespace)
import type { ThreeElements } from '@react-three/fiber'

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
