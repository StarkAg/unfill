# Unfill

Turn a filled-in form back into a blank one.

Feed it a scan of a form somebody has written on, and it erases the handwriting —
names, numbers, dates, signatures — while leaving the printed form itself
untouched: the table rules, the labels, the logo, the QR code. The result is a
clean template you can print and fill in again.

```
python cli.py scan.jpg -o blank.png
```

Or open the web app and drag the scan in:

```
python app.py     # http://localhost:8000
```

## How it works

Three steps, and the interesting part is the first one.

**1. Find the ink.** The naive approach — "keep pixels that are more blue than
red" — does not work. A scan gives printed black text a faint blue cast, and
JPEG leaves coloured fringes along every letter edge, so a blue-vs-red test
flags the *form* as well as the handwriting and you erase the thing you were
trying to keep.

What separates them is **saturation**. Printed black text and QR codes are
desaturated — they're gray, even when tinted. Pen ink is a genuinely saturated
blue. So detection runs in HSV: blue-ish hue, *and* saturated, *and* not paper.

That still catches the thin fringes, so two filters follow. A morphological
opening erodes away 1–2px speckle, and a connected-component filter drops any
blob too small to be handwriting. Real strokes are thick and connected; fringes
aren't. The page header (logo, QR, photo) is masked out entirely, since nobody
writes there.

Finally the mask is dilated. Ink has faint tails and edges beyond its core, and
if you don't cover them the eraser leaves visible ghosts.

**2. Erase it.** The mask goes to [LaMa](https://github.com/Sanster/IOPaint), a
large-mask inpainting model. This matters more than it sounds: handwriting
crosses the printed table lines, and a plain white fill would leave gaps in
them. LaMa reconstructs the ruling underneath the ink.

**3. Whiten the paper.** A scan carries a colour cast and uneven lighting, which
looks obviously photocopied when printed. Converting to neutral grayscale kills
the cast; dividing the page by a blurred estimate of its own background flattens
the shadows; a levels stretch snaps the paper to pure white and the ink to
black. The photo and logo are excluded from the hard clipping, or they'd blow
out to white. A despeckle pass removes the leftover scan dust.

Output is 300 DPI, so it prints at true size.

## Install

```bash
pip install -r requirements.txt
```

First run downloads the LaMa weights (~196MB) and caches them. CPU is fine — a
full page takes a few seconds. Pass `--device cuda` if you have a GPU.

## CLI

```bash
# one file
python cli.py scan.jpg -o blank.png

# a whole folder
python cli.py ./scans -o ./blanks --save-masks

# faint ink still showing? erase harder
python cli.py scan.jpg -o blank.png --grow 3

# keep the original paper tone
python cli.py scan.jpg -o blank.png --no-whiten
```

## Library

```python
from PIL import Image
from unfill import unfill

result = unfill(Image.open("scan.jpg"))
result.image.save("blank.png", dpi=(300, 300))
print(f"erased {result.ink_coverage:.1f}% of the page")
```

`MaskOptions` and `WhitenOptions` expose the thresholds if you need to retune
for a different pen colour or a different form.

## Tuning

Defaults target blue ballpoint on a black-printed form.

| Symptom | Fix |
| --- | --- |
| Faint ghosts where ink was | raise `--grow`, or lower `min_saturation` |
| Printed text being eaten | raise `min_saturation`, raise `min_blob_area` |
| Ink is black, not blue | widen `hue_lo`/`hue_hi`; saturation alone won't separate black ink from black print |
| Photo blown out to white | add its box to `WhitenOptions.gentle_boxes` |

The `gentle_boxes` and `header_frac` defaults are positioned for one specific
form layout. Different form, different boxes.

## A note on the data

Forms are full of personal information. The web app processes uploads in memory
and never writes them to disk, and the repo's `.gitignore` excludes every image
format so scans can't be committed by accident. Keep it that way.

## Licence

MIT
