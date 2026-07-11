"""Detect handwritten pen ink on a scanned form and build an inpainting mask."""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


@dataclass
class MaskOptions:
    """Tunables for ink detection.

    The defaults target blue ballpoint on a black-printed form. `strength`
    scales how aggressively faint ink and its edges are picked up.
    """

    hue_lo: int = 125          # PIL hue units (0-255 == 0-360deg)
    hue_hi: int = 200
    min_saturation: int = 45   # the key discriminator - see module notes
    min_value: int = 40
    min_blue_over_red: int = 15
    min_blob_area: int = 30    # px; smaller blobs are JPEG speckle, not ink
    grow: int = 2              # dilation passes; more = covers fainter tails
    header_frac: float = 0.20  # top band protected from masking


# Why saturation is the discriminator:
#   Printed black text and QR codes are *desaturated* (gray), even when a scan
#   gives them a slight blue cast. Pen ink is a genuinely *saturated* blue. A
#   naive "blue > red" test flags the JPEG colour fringes on printed text and
#   would erase the form itself; saturation separates them cleanly.
#
# Why the blob-area filter:
#   Those fringes survive as thin 1-2px speckles. Real strokes are thick and
#   connected, so an opening + minimum-area filter drops the speckle and keeps
#   the handwriting.


def build_mask(rgb: np.ndarray, opts: MaskOptions | None = None) -> np.ndarray:
    """Return a uint8 mask (0 or 255) marking pen ink to erase."""
    opts = opts or MaskOptions()

    img = Image.fromarray(rgb)
    arr = rgb.astype(np.int16)
    r, b = arr[..., 0], arr[..., 2]

    hsv = np.asarray(img.convert("HSV")).astype(np.int16)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    ink = (
        (H > opts.hue_lo)
        & (H < opts.hue_hi)
        & (S > opts.min_saturation)
        & (V > opts.min_value)
        & (b - r > opts.min_blue_over_red)
        & ~((arr[..., 0] > 208) & (arr[..., 1] > 208) & (b > 208))  # white paper
    )

    mask = np.where(ink, 255, 0).astype(np.uint8)

    # The header (logo / QR / photo / printed info boxes) never holds
    # handwriting, so never let it be masked.
    mask[: int(mask.shape[0] * opts.header_frac), :] = 0

    m = Image.fromarray(mask, mode="L")

    # Opening: erode away printed-edge speckle, then restore stroke bodies.
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))

    # Drop connected blobs too small to be handwriting.
    a = np.asarray(m)
    labels, n = ndimage.label(a > 0)
    if n:
        sizes = np.bincount(labels.ravel())
        too_small = np.flatnonzero(sizes < opts.min_blob_area)
        a = np.where(np.isin(labels, too_small), 0, a).astype(np.uint8)
    m = Image.fromarray(a, mode="L")

    # Grow to cover ink cores *and* their faint edges, or LaMa leaves ghosts.
    for _ in range(opts.grow):
        m = m.filter(ImageFilter.MaxFilter(9))
    m = m.filter(ImageFilter.MaxFilter(5))
    m = m.filter(ImageFilter.GaussianBlur(1)).point(lambda p: 255 if p > 40 else 0)

    return np.asarray(m).astype(np.uint8)


def overlay(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Paint the mask red over the source image, for eyeballing coverage."""
    out = rgb.copy()
    out[mask > 0] = (255, 0, 0)
    return out
