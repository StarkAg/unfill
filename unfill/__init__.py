"""Unfill - turn a filled-in form scan back into a clean blank template."""

from .mask import MaskOptions, build_mask, overlay
from .pipeline import Result, unfill
from .whiten import WhitenOptions, whiten

__version__ = "0.1.0"

__all__ = [
    "unfill",
    "Result",
    "build_mask",
    "MaskOptions",
    "overlay",
    "whiten",
    "WhitenOptions",
]
