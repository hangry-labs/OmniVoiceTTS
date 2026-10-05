FROM python:3.13-slim AS base

ARG HF_ENDPOINT=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/persistent/models/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE VERSION requirements.txt /app/
COPY omnivoice /app/omnivoice
COPY hangrylabs /app/hangrylabs
COPY assets /app/assets

RUN if [ -n "$HF_ENDPOINT" ]; then export HF_ENDPOINT; else unset HF_ENDPOINT; fi \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --extra-index-url https://download.pytorch.org/whl/cu128 -r /app/requirements.txt \
    && date '+%d:%m:%Y %H:%M:%S' > /app/BUILD_DATE \
    && python -m pip install -e . --no-deps

FROM base AS baked-builder

ARG HF_ENDPOINT=

RUN if [ -n "$HF_ENDPOINT" ]; then export HF_ENDPOINT; else unset HF_ENDPOINT; fi \
    && python -u /app/omnivoice/prefetch_assets.py

FROM python:3.13-slim AS runtime-base

LABEL org.opencontainers.image.source="https://github.com/Hangry-Labs/OmniVoiceTTS"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/persistent/models/huggingface \
    OMNIVOICE_SETTINGS_PATH=/app/persistent/app/settings.json \
    OMNIVOICE_OPENAI_VOICE_PROFILE_DIR=/app/persistent/voices/openai \
    OMNIVOICE_UI_UPLOAD_DIR=/tmp/omnivoicetts-ui \
    OMNIVOICE_UI_UPLOAD_LIMIT_MIB=64 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    OMNIVOICE_DEVICE=auto \
    OMNIVOICE_MODEL=k2-fsa/OmniVoice \
    OMNIVOICE_LOAD_ASR=0 \
    OMNIVOICE_ALLOW_CPU_EAGER_ASR=0 \
    OMNIVOICE_MAX_CONCURRENT_GENERATIONS=1 \
    OMNIVOICE_EMPTY_CUDA_CACHE_AFTER_REQUEST=0 \
    OMNIVOICE_RESET_CUDA_PEAK_AFTER_CACHE_CLEAR=0 \
    PORT=7861 \
    HOST=0.0.0.0 \
    UVICORN_RELOAD=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && mkdir -p /app/persistent/models/huggingface /app/persistent/app /app/persistent/voices/openai /tmp/omnivoicetts-ui \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 7861

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7861/tts/ping', timeout=4).read()"]

CMD ["python", "-u", "omnivoice/app.py"]

FROM runtime-base AS tiny

ENV HF_HUB_OFFLINE=0 \
    TRANSFORMERS_OFFLINE=0

COPY --from=base /usr/local /usr/local
COPY --from=base /app /app

FROM runtime-base AS baked

COPY --from=baked-builder /usr/local /usr/local
COPY --from=baked-builder /app /app
