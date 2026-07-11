"""Unfill CLI: blank out one form, or a whole folder of them.

    python cli.py scan.jpg -o blank.png
    python cli.py ./scans -o ./blanks --save-masks
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

from unfill import MaskOptions, unfill

SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def main() -> int:
    p = argparse.ArgumentParser(prog="unfill", description=__doc__)
    p.add_argument("input", type=Path, help="image file or folder of images")
    p.add_argument("-o", "--output", type=Path, required=True, help="file or folder")
    p.add_argument("--no-whiten", action="store_true", help="keep original paper tone")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    p.add_argument("--save-masks", action="store_true", help="also write the ink masks")
    p.add_argument(
        "--grow",
        type=int,
        default=MaskOptions.grow,
        help="dilation passes; raise if faint ink ghosts remain",
    )
    args = p.parse_args()

    if args.input.is_dir():
        images = sorted(f for f in args.input.iterdir() if f.suffix.lower() in SUFFIXES)
        if not images:
            print(f"no images in {args.input}", file=sys.stderr)
            return 1
        args.output.mkdir(parents=True, exist_ok=True)
        outputs = [args.output / f"{f.stem}_blank.png" for f in images]
    else:
        images = [args.input]
        if args.output.suffix:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            outputs = [args.output]
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            outputs = [args.output / f"{args.input.stem}_blank.png"]

    opts = MaskOptions(grow=args.grow)

    for src, dst in zip(images, outputs):
        res = unfill(
            Image.open(src),
            whiten_paper=not args.no_whiten,
            device=args.device,
            mask_opts=opts,
        )
        res.image.save(dst, dpi=(300, 300))
        if args.save_masks:
            res.mask.save(dst.with_name(f"{dst.stem}_mask.png"))
        print(f"{src.name} -> {dst}  (erased {res.ink_coverage:.2f}% of the page)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
