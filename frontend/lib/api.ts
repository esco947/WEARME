const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("fitview_token");
}

export function setToken(token: string): void {
  localStorage.setItem("fitview_token", token);
}

export function removeToken(): void {
  localStorage.removeItem("fitview_token");
}

async function fetchWithAuth(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${BASE_URL}${path}`, { ...options, headers });
}

// --- Auth ---

export async function register(email: string, password: string): Promise<{ access_token: string }> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur d'inscription");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Email ou mot de passe incorrect");
  }
  return res.json();
}

// --- Avatar ---

export interface AvatarData {
  avatar_id: number;
  glb_url: string;
  betas: number[];
  gender: string;
}

export async function createAvatar(betas: number[], gender: string): Promise<AvatarData> {
  const res = await fetchWithAuth("/avatar/create", {
    method: "POST",
    body: JSON.stringify({ betas, gender }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur de création d'avatar");
  }
  return res.json();
}

export async function getAvatar(avatarId: number): Promise<AvatarData> {
  const res = await fetchWithAuth(`/avatar/${avatarId}`);
  if (!res.ok) throw new Error("Avatar non trouvé");
  return res.json();
}

// --- Catalogue ---

export interface Product {
  id: string;
  name: string;
  brand: string;
  type: string;
  sizes: string[];
  color: string;
  price: number;
  thumbnail: string;
  description: string;
}

export async function getProducts(type?: string, brand?: string): Promise<Product[]> {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (brand) params.set("brand", brand);
  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${BASE_URL}/products${query}`);
  if (!res.ok) throw new Error("Erreur de chargement du catalogue");
  return res.json();
}

export async function getProduct(id: string): Promise<Product> {
  const res = await fetch(`${BASE_URL}/products/${id}`);
  if (!res.ok) throw new Error("Produit non trouvé");
  return res.json();
}

// --- Pose detection (server-side, no WebGL) ---

export interface PoseLandmarkPoint {
  x: number;
  y: number;
  z: number;
  visibility: number;
}

export interface BackendPoseResult {
  landmarks: PoseLandmarkPoint[];
  world_landmarks: PoseLandmarkPoint[];
  segmentation_mask_b64: string | null;
  mask_width: number;
  mask_height: number;
}

export interface BackendPoseDetection {
  front: BackendPoseResult;
  profile: BackendPoseResult;
}

export async function analyzePosePhotos(
  frontFile: File,
  profileFile: File,
): Promise<BackendPoseDetection> {
  const form = new FormData();
  form.append("front", frontFile);
  form.append("profile", profileFile);

  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}/pose/detect`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erreur analyse pose" }));
    throw new Error(err.detail || "Erreur analyse pose");
  }
  return res.json();
}
