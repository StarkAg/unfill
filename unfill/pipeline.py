"""The Unfill pipeline: detect ink -> erase with LaMa -> whiten the paper."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import numpy as np
from PIL import Image

from .mask import MaskOptions, build_mask
from .whiten import WhitenOptions, whiten


@dataclass
class Result:
    image: Image.Image        # the blanked form
    mask: Image.Image         # what was erased
    ink_coverage: float       # % of the page that was ink


@lru_cache(maxsize=2)
def _load_model(device: str = "cpu"):
    """LaMa, loaded once and reused. First call downloads ~196MB.

    torch and iopaint are imported lazily so that `engine="classical"` runs on
    a host that has neither installed.
    """
    import torch
    from iopaint.model_manager import ModelManager

    return ModelManager(name="lama", device=torch.device(device))


def _inpaint_lama(rgb: np.ndarray, mask: np.ndarray, device: str) -> np.ndarray:
    """Neural inpainting. Best at rebuilding printed rules under a stroke."""
    from iopaint.schema import InpaintRequest

    out = _load_model(device)(rgb, mask, InpaintRequest())
    return np.ascontiguousarray(out.astype(np.uint8)[:, :, ::-1])  # BGR -> RGB


def _inpaint_classical(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Telea inpainting: no model, no torch, milliseconds instead of seconds.

    It propagates surrounding pixels inward, which on a form is mostly "fill
    with white paper" - and since the whiten pass flattens the page anyway, the
    two engines are near-identical except where ink crossed a printed rule.
    LaMa reconstructs those rules more convincingly.
    """
    import cv2

    out = cv2.inpaint(
        np.ascontiguousarray(rgb[:, :, ::-1]), mask, 4, cv2.INPAINT_TELEA
    )
    return np.ascontiguousarray(out[:, :, ::-1])


Engine = Literal["lama", "classical"]


def unfill(
    image: Image.Image,
    *,
    whiten_paper: bool = True,
    engine: Engine = "lama",
    device: str = "cpu",
    mask_opts: MaskOptions | None = None,
    whiten_opts: WhitenOptions | None = None,
) -> Result:
    """Turn a filled-in form scan back into a blank template.

    `engine="lama"` is the better eraser; `engine="classical"` needs no model
    and no torch, which is what you want on a small host.
    """
    rgb = np.array(image.convert("RGB"))
    mask = build_mask(rgb, mask_opts)

    if mask.any():
        if engine == "lama":
            rgb = _inpaint_lama(rgb, mask, device)
        else:
            rgb = _inpaint_classical(rgb, mask)

    if whiten_paper:
        page = Image.fromarray(whiten(rgb, whiten_opts), mode="L")
    else:
        page = Image.fromarray(rgb, mode="RGB")

    return Result(
        image=page,
        mask=Image.fromarray(mask, mode="L"),
        ink_coverage=float((mask > 0).mean() * 100),
    )
