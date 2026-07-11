FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# opencv (pulled in by iopaint) needs these at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch. The default PyPI wheel bundles ~2.5GB of CUDA we never use;
# this keeps the image small enough to actually deploy. Installing it first
# means the requirements install below sees torch as already satisfied.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the LaMa weights (~196MB) into the image. The host filesystem is
# ephemeral, so otherwise every cold start would re-download them.
RUN mkdir -p /root/.cache/torch/hub/checkpoints && \
    python -c "from torch.hub import download_url_to_file; \
download_url_to_file('https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt', \
'/root/.cache/torch/hub/checkpoints/big-lama.pt')"

COPY . .

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120"]
