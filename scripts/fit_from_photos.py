"""CLI script for photo-based body fitting.

Reads one or two photos (front view required, side view optional),
runs the full MediaPipe + SMPL optimisation pipeline, and outputs
the fitted body parameters to a JSON file.

Usage::

    # Front view only
    python scripts/fit_from_photos.py \\
        --front data/samples/front.jpg \\
        --height 1.75

    # Front + side, with explicit gender and output path
    python scripts/fit_from_photos.py \\
        --front data/samples/front.jpg \\
        --side  data/samples/side.jpg \\
        --height 1.75 \\
        --gender male \\
        --output data/samples/fitted_body.json \\
        --n-iter 200

Requirements::

    pip install wearme[vision]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ── Argument parsing ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fit SMPL body parameters from one or two photos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--front", required=True, type=Path,
        help="Path to front-view image (JPEG or PNG).",
    )
    p.add_argument(
        "--side", default=None, type=Path,
        help="Path to side-view image (optional).",
    )
    p.add_argument(
        "--height", required=True, type=float, metavar="METRES",
        help="Standing height in metres (e.g. 1.75).",
    )
    p.add_argument(
        "--gender", default="neutral",
        choices=["neutral", "male", "female"],
        help="SMPL model gender. Default: neutral.",
    )
    p.add_argument(
        "--output", default=None, type=Path,
        help="Output JSON file path. Defaults to stdout.",
    )
    p.add_argument(
        "--n-iter", default=200, type=int, dest="n_iter",
        help="Number of optimisation iterations. Default: 200.",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging.",
    )
    return p


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the fit_from_photos CLI."""
    args = _build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger(__name__)

    # ── Import vision deps (deferred to give a clear error if not installed) ──
    try:
        import cv2  # type: ignore[import]
        from wearme.vision.photo_fitter import PhotoFitter
    except ImportError as exc:
        log.error(
            "Vision extras are required: pip install wearme[vision]\n"
            "Missing: %s", exc,
        )
        sys.exit(1)

    # ── Load images ───────────────────────────────────────────────────────────
    front_path: Path = args.front
    if not front_path.is_file():
        log.error("Front image not found: %s", front_path)
        sys.exit(1)

    front_image = cv2.imread(str(front_path))
    if front_image is None:
        log.error("Could not read front image: %s", front_path)
        sys.exit(1)

    side_image = None
    if args.side is not None:
        side_path: Path = args.side
        if not side_path.is_file():
            log.error("Side image not found: %s", side_path)
            sys.exit(1)
        side_image = cv2.imread(str(side_path))
        if side_image is None:
            log.error("Could not read side image: %s", side_path)
            sys.exit(1)

    # ── Run fitting ───────────────────────────────────────────────────────────
    log.info(
        "Fitting body (height=%.2f m, gender=%s, n_iter=%d)...",
        args.height, args.gender, args.n_iter,
    )

    try:
        fitter = PhotoFitter(n_iter=args.n_iter)
        params = fitter.fit(
            front_image=front_image,
            known_height_m=args.height,
            gender=args.gender,
            side_image=side_image,
        )
    except ValueError as exc:
        log.error("Fitting failed: %s", exc)
        sys.exit(1)

    # ── Output ────────────────────────────────────────────────────────────────
    result = params.to_dict()

    # Print measurement summary to console
    p = params._params
    print("\n── Fitted Body Measurements ─────────────────────────────")
    print(f"  Height:    {p.get('height_m', 0)*100:.1f} cm")
    print(f"  Chest:     {p.get('chest_circ_m', 0)*100:.1f} cm")
    print(f"  Waist:     {p.get('waist_circ_m', 0)*100:.1f} cm")
    print(f"  Hips:      {p.get('hip_circ_m', 0)*100:.1f} cm")
    print(f"  Shoulders: {p.get('shoulder_width_m', 0)*100:.1f} cm")
    print(f"  Betas:     {[round(b, 3) for b in params.betas.tolist()]}")
    print("─────────────────────────────────────────────────────────\n")

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        log.info("Body parameters saved to %s", args.output)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
