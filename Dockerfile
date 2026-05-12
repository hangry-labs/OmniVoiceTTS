FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE VERSION requirements.txt /app/
COPY omnivoice /app/omnivoice

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --extra-index-url https://download.pytorch.org/whl/cu128 -r /app/requirements.txt \
    && python -m pip install -e . --no-deps

FROM base AS baked-builder

RUN python -u /app/omnivoice/prefetch_assets.py

FROM python:3.11-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/.cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    OMNIVOICE_DEVICE=auto \
    OMNIVOICE_MODEL=k2-fsa/OmniVoice \
    OMNIVOICE_LOAD_ASR=1 \
    PORT=7861 \
    HOST=0.0.0.0 \
    UVICORN_RELOAD=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 7861

CMD ["python", "-u", "omnivoice/app.py"]

FROM runtime-base AS tiny

ENV HF_HUB_OFFLINE=0 \
    TRANSFORMERS_OFFLINE=0

COPY --from=base /usr/local /usr/local
COPY --from=base /app /app

FROM runtime-base AS baked

COPY --from=baked-builder /usr/local /usr/local
COPY --from=baked-builder /app /app
