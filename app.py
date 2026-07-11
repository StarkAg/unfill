"""Unfill web app - upload a filled form, get a blank template back.

    python app.py            # http://localhost:8000

Images are processed in memory and never written to disk, which matters because
the forms people feed this tool are full of personal data.
"""

import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from unfill import MaskOptions, __version__, unfill

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 40_000_000

app = FastAPI(title="Unfill", version=__version__)


@app.post("/api/unfill")
async def api_unfill(
    file: UploadFile = File(...),
    whiten_paper: bool = Form(True),
    grow: int = Form(MaskOptions.grow),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty upload.")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 25MB).")

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception:
        raise HTTPException(400, "That file isn't a readable image.")

    if image.width * image.height > MAX_PIXELS:
        raise HTTPException(413, "Image has too many pixels (max 40MP).")

    result = unfill(
        image,
        whiten_paper=whiten_paper,
        mask_opts=MaskOptions(grow=max(0, min(grow, 5))),
    )

    buf = io.BytesIO()
    result.image.save(buf, format="PNG", dpi=(300, 300))
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"X-Ink-Coverage": f"{result.ink_coverage:.2f}"},
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/")
def index():
    return FileResponse("web/index.html")


app.mount("/", StaticFiles(directory="web"), name="web")


if __name__ == "__main__":
    import os

    import uvicorn

    # Hosts inject the port and expect us on all interfaces.
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
