"""The Unfill pipeline: detect ink -> erase with LaMa -> whiten the paper."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import torch
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
    """LaMa, loaded once and reused. First call downloads ~196MB."""
    from iopaint.model_manager import ModelManager

    return ModelManager(name="lama", device=torch.device(device))


def unfill(
    image: Image.Image,
    *,
    whiten_paper: bool = True,
    device: str = "cpu",
    mask_opts: MaskOptions | None = None,
    whiten_opts: WhitenOptions | None = None,
) -> Result:
    """Turn a filled-in form scan back into a blank template."""
    from iopaint.schema import InpaintRequest

    rgb = np.array(image.convert("RGB"))
    mask = build_mask(rgb, mask_opts)

    if mask.any():
        # LaMa reconstructs the paper *and* the printed table lines that the
        # handwriting crossed - a plain white fill would leave gaps in them.
        model = _load_model(device)
        out = model(rgb, mask, InpaintRequest())
        # iopaint hands back BGR.
        rgb = np.ascontiguousarray(out.astype(np.uint8)[:, :, ::-1])

    if whiten_paper:
        page = Image.fromarray(whiten(rgb, whiten_opts), mode="L")
    else:
        page = Image.fromarray(rgb, mode="RGB")

    return Result(
        image=page,
        mask=Image.fromarray(mask, mode="L"),
        ink_coverage=float((mask > 0).mean() * 100),
    )
