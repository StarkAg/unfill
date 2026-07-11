"""Flatten a scan to pure-white paper with crisp ink, ready for printing."""

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage


@dataclass
class WhitenOptions:
    white_point: float = 200.0   # >= this after normalising -> pure white paper
    black_point: float = 60.0    # <= this -> full black ink
    speck_area: int = 8          # isolated dark blobs below this are scan dust
    # Boxes (x0, y0, x1, y1 as fractions of the page) holding real midtones -
    # a portrait, a gray logo. Hard clipping would blow these out, so they get
    # gentle levels instead.
    gentle_boxes: list[tuple[float, float, float, float]] = field(
        default_factory=lambda: [
            (0.690, 0.083, 0.815, 0.180),  # photo box
            (0.048, 0.020, 0.145, 0.085),  # ECI logo, top-left
        ]
    )


def _levels(x: np.ndarray, black: float, white: float) -> np.ndarray:
    return np.clip((x - black) * (255.0 / (white - black)), 0, 255)


def whiten(rgb: np.ndarray, opts: WhitenOptions | None = None) -> np.ndarray:
    """Return a grayscale page: white paper, black ink, no scan tint."""
    opts = opts or WhitenOptions()
    h, w = rgb.shape[:2]

    # Going neutral grayscale removes any blue/yellow paper cast outright.
    gray = np.asarray(
        np.dot(rgb[..., :3], [0.299, 0.587, 0.114])
    ).astype(np.float32)

    # Estimate the paper background: grey-dilate to erase thin dark strokes,
    # then blur -> a smooth illumination map. Dividing it out flattens the
    # shadows and gradients a flatbed/phone scan leaves behind.
    bg = ndimage.grey_dilation(gray, size=41)
    bg = np.maximum(ndimage.gaussian_filter(bg, sigma=25), 1.0)
    norm = np.clip(gray / bg * 255.0, 0, 255)

    hard = _levels(norm, opts.black_point, opts.white_point)
    gentle = _levels(norm, 25, 240)

    out = hard
    for x0, y0, x1, y1 in opts.gentle_boxes:
        a, b = int(y0 * h), int(y1 * h)
        c, d = int(x0 * w), int(x1 * w)
        out[a:b, c:d] = gentle[a:b, c:d]

    # Despeckle the leftover scan dust on the paper.
    labels, n = ndimage.label(out < 160)
    if n:
        sizes = np.bincount(labels.ravel())
        dust = np.isin(labels, np.flatnonzero(sizes < opts.speck_area))
        out[dust] = 255

    return out.astype(np.uint8)
