"""Computer vision utilities: pose estimation and photo fitting (Phase 4).

Requires the vision extras::

    pip install wearme[vision]

Public API (available when vision extras are installed):
    PhotoFitter        — main entry point for photo-based body fitting
    LandmarkResult     — landmark detection output
    SilhouetteResult   — segmentation output
    CameraParams       — pixel scale estimation
    ContourAnalyzer    — body width measurement from silhouette contours
"""

# ContourAnalyzer and CameraParams have no external deps — always importable.
from wearme.vision.camera_estimation import CameraParams, estimate_from_landmarks
from wearme.vision.contour_analyzer import ContourAnalyzer

# MediaPipe / OpenCV-dependent modules are imported lazily.
# Individual files still raise a helpful ImportError when used without extras.
try:
    from wearme.vision.landmarks import LandmarkResult, detect_landmarks
    from wearme.vision.segmentation import SilhouetteResult, extract_silhouette
    from wearme.vision.photo_fitter import PhotoFitter
    _VISION_AVAILABLE = True
except ImportError:
    _VISION_AVAILABLE = False

__all__ = [
    "PhotoFitter",
    "LandmarkResult",
    "detect_landmarks",
    "SilhouetteResult",
    "extract_silhouette",
    "CameraParams",
    "estimate_from_landmarks",
    "ContourAnalyzer",
]
