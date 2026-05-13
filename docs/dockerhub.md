<p>
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/">
    <img src="https://github.com/Hangry-Labs/OmniVoiceTTS/raw/master/logo.jpg" alt="Hangry Labs OmniVoiceTTS logo">
  </a>
</p>

# Hangry Labs OmniVoiceTTS

Easy-to-run OmniVoice text-to-speech Docker images with a browser UI and HTTP API included.

This Hangry Labs fork is built for people who want massively multilingual text to speech without a long setup. Install Docker, run one command, open the local UI, or call the API from your own application.

## Listen First

Before pulling the image, hear what OmniVoiceTTS can do:

**[Open the OmniVoiceTTS language examples page](https://hangry-labs.github.io/OmniVoiceTTS/examples/)**

The examples page includes native-language samples, voice-variety demos, translated intros, and cross-language clone demos across 20 languages.

## Responsible Use

OmniVoice supports voice cloning. Do not use this image for unauthorized voice cloning, impersonation, fraud, harassment, scams, or any illegal or unethical activity. Only clone voices when you have the rights and consent to do so.

## Project Links

- GitHub repository: https://github.com/Hangry-Labs/OmniVoiceTTS
- Project page: https://hangry-labs.github.io/OmniVoiceTTS/examples/
- Upstream OmniVoice project: https://github.com/k2-fsa/OmniVoice
- Upstream model: https://huggingface.co/k2-fsa/OmniVoice
- Hangry Labs: https://nuggies.website/

## Quick Start

Run with NVIDIA GPU support:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 hangrylabs/omnivoicetts:latest
```

Run on CPU:

```bash
docker run -p 7861:7861 -e OMNIVOICE_DEVICE=cpu hangrylabs/omnivoicetts:latest
```

Run on a different GPU by changing both GPU numbers. For example, GPU `1`:

```bash
docker run -p 7861:7861 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/omnivoicetts:latest
```

Then open:

http://localhost:7861

The `latest` image is the full baked image with OmniVoice model assets, the Higgs audio tokenizer, and Whisper ASR assets included for offline-friendly use after the image is pulled. The release image is based on Python 3.13 and is intended to run without live Hugging Face downloads after pull. Version tags such as `v0.1.0` are also available for reproducible deployments.

Tiny tags use the `vX.Y.Z_tiny` pattern. They keep runtime dependencies but skip baked Hugging Face model assets, and are intended for persistent-volume workflows where the cache is warmed on first online use:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_hf_cache:/app/.cache/huggingface hangrylabs/omnivoicetts:latest_tiny
```

## What You Get

- Browser UI for auto voice, voice design, and voice cloning
- HTTP API for applications and automation
- 600+ language support inherited from OmniVoice
- WAV, MP3, FLAC, and OGG output support
- GPU support when Docker/NVIDIA support is available
- Offline-friendly usage with the standard full image once it is available locally
- Kokoro-shaped compatibility fields and routes such as `voice`, `use_gpu`, `response_format`, `/tts/voices`, `/tts/speakers`, `/tts/stream-formats`, `/tts/convert`, and `/tts/stream`

## API Example

Default API behavior returns WAV:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs OmniVoiceTTS","language":"English"}' \
  -o hello.wav
```

Request MP3 when you want compact output:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs OmniVoiceTTS","language":"English","output_format":"mp3"}' \
  -o hello.mp3
```

Voice design:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a custom designed voice.","language":"English","instruct":"female, low pitch, british accent","output_format":"mp3"}' \
  -o designed.mp3
```

Voice design is for speaker attributes only. Do not combine `instruct` with bracket expression tags such as `[laughter]` or `[sigh]`; use no voice prompt or voice cloning for expressive bracket tags.

Voice cloning can be called with a reference audio path that is visible inside the container:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"This voice follows the reference sample.","language":"English","ref_audio":"/data/ref.wav","ref_text":"Transcript of the reference audio.","output_format":"mp3"}' \
  -o cloned.mp3
```

Compatibility output-format fields:

```bash
curl -X POST "http://localhost:7861/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"Kokoro-shaped request using response_format.","voice":"default","response_format":"mp3"}' \
  -o converted.mp3
```

Health check:

```bash
curl http://localhost:7861/tts/ping
```

API docs are available at:

http://localhost:7861/tts/docs

## Image Tags

- Recommended tag for most users: `latest`
- Versioned release tags use the pattern `vX.Y.Z`, for example `v0.1.0`
- Tiny tags use `latest_tiny` or versioned tags such as `v0.1.0_tiny`

## Release Validation

Before the initial release, the Python 3.13 baked image was built and tested without a host model-cache volume mounted. API validation covered `/tts/ping`, `/tts/status`, discovery routes, OpenAPI docs, metrics, real generation in WAV/MP3/FLAC/OGG, voice design, `/tts/stream`, `/tts/convert`, `/tts/purge`, and generation after purge/reload from baked cache.

## Attribution

This is an independently maintained Hangry Labs packaging and serving fork of the original OmniVoice project by k2-fsa and contributors:

https://github.com/k2-fsa/OmniVoice

License and attribution are preserved in the repository. Original OmniVoice copyright remains with the upstream authors; Hangry Labs maintains the Docker packaging, Web UI/API integration, documentation, release tooling, and related modifications in this fork.
