// Types compatibles avec PoseLandmarkerResult de MediaPipe (sans dépendance WASM)

export interface NormalizedLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
  presence?: number;
}

export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
  presence?: number;
}

export interface PoseLandmarkerResult {
  landmarks: NormalizedLandmark[][];
  worldLandmarks: Landmark[][];
  segmentationMasks?: Array<{
    getAsFloat32Array(): Float32Array;
    width: number;
    height: number;
    close?(): void;
  }>;
}

// Skeleton connections for overlay drawing
export const SKELETON_CONNECTIONS: [number, number][] = [
  [0, 11], [0, 12],           // head → shoulders
  [11, 12],                    // shoulder bar
  [11, 13], [13, 15],          // left arm
  [12, 14], [14, 16],          // right arm
  [11, 23], [12, 24],          // torso sides
  [23, 24],                    // hip bar
  [23, 25], [25, 27],          // left leg
  [24, 26], [26, 28],          // right leg
];
