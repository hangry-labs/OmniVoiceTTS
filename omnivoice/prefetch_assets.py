from __future__ import annotations

import os

import torch

from omnivoice import OmniVoice


def main() -> None:
    model_id = os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")
    model_revision = os.getenv(
        "OMNIVOICE_MODEL_REVISION",
        "c5fdb5ccb189668d56333f77ba2629f4cd7535f4",
    ).strip() or None
    load_asr = os.getenv("OMNIVOICE_PREFETCH_ASR", "1").lower() in {"1", "true", "yes", "y"}
    asr_model = os.getenv("OMNIVOICE_ASR_MODEL", "openai/whisper-large-v3-turbo")
    asr_model_revision = os.getenv(
        "OMNIVOICE_ASR_MODEL_REVISION",
        "41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
    ).strip() or None

    print(f"Prefetching OmniVoice model assets from {model_id} ...", flush=True)
    model = OmniVoice.from_pretrained(
        model_id,
        device_map="cpu",
        dtype=torch.float32,
        revision=model_revision,
        load_asr=False,
        asr_model_name=asr_model,
        asr_model_revision=asr_model_revision,
    )
    print(f"Loaded OmniVoice sample_rate={model.sampling_rate}", flush=True)

    if load_asr:
        print(f"Prefetching ASR model assets from {asr_model} ...", flush=True)
        model.load_asr_model(asr_model)

    print("Prefetch complete.", flush=True)


if __name__ == "__main__":
    main()
