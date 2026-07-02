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

Maintainers can reuse the same example workload as a local performance benchmark with `task benchmark-examples`; per-category summaries are appended under `benchmarks/` and detailed results are stored in `benchmarks/example-generation.json`. The default benchmark uses 100 deterministic no-prompt calls, 100 deterministic predefined cached-reference calls, and 100 deterministic direct reference-audio calls from `examples/assets/manifest.json`.

## Browser UI

The image includes a local browser UI for no-prompt generation, voice design, voice cloning, progressive streaming tests, reproducible seeds, output-format control, live GPU visibility, and a multilingual interface with 60 UI languages.

<p>
  <img src="https://github.com/Hangry-Labs/OmniVoiceTTS/raw/master/docs/ui.jpg" alt="OmniVoiceTTS browser UI">
</p>

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
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Run on CPU:

```bash
docker run -p 7861:7861 -e OMNIVOICE_DEVICE=cpu -e OMNIVOICE_LOAD_ASR=0 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

CPU mode is a fallback path and still needs enough system memory. For a 140-character CPU benchmark request, conservative rounded Docker RAM recommendations were: 2 GB for random/no-prompt voice, voice design, and direct clone with transcript; 3 GB for a stored voice profile with transcript; 6 GB for direct clone without transcript; and 7 GB for a stored voice profile without transcript. The no-transcript paths may lazy-load ASR, which is why they need much more RAM. Use more for longer text, concurrent requests, larger outputs, or host environments with tighter memory behavior.

When running on CPU, `/tts/status` reports container/system memory diagnostics and per-scenario RAM recommendations. If a CPU request appears close to the available memory limit, the container logs a warning and still tries to continue; Docker or the OS may still kill the process if RAM is exhausted.

If a CPU container exits after `Loading weights` during a cloned-voice `/v1/audio/speech` request, it is usually an out-of-memory kill rather than a Python exception. The TTS model already needs significant RAM on CPU, and clone/profile requests without a transcript can lazy-load Whisper ASR to transcribe the reference audio. Recent snapshots reduce the default footprint by keeping eager ASR off on CPU, but no-transcript clone paths still need more memory. To lower RAM use: run the latest snapshot (`0.2.1-snapshot` or newer), keep `OMNIVOICE_LOAD_ASR=0`, do not set `OMNIVOICE_ALLOW_CPU_EAGER_ASR=1`, save voice profiles with a reference transcript, include `ref_text` when sending direct `ref_audio`, keep concurrency at the default `OMNIVOICE_MAX_CONCURRENT_GENERATIONS=1`, and prefer GPU mode when available. See `benchmarks/CPU_MEMORY.md` in the GitHub repository for measured scenario recommendations.

Run on a different GPU by changing both GPU numbers. For example, GPU `1`:

```bash
docker run -p 7861:7861 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Then open:

http://localhost:7861

The named `omnivoicetts_openai_voice_profiles` volume stores voices created in the UI so they survive container replacement and image updates. Docker creates the volume automatically the first time you run one of these commands.

The `latest` image is the full baked image with OmniVoice model assets, the Higgs audio tokenizer, and Whisper ASR assets included for offline-friendly use after the image is pulled. CPU runs should keep eager ASR disabled because saved voice profiles with transcripts do not need Whisper at request startup; ASR can still lazy-load only when a reference audio request omits `ref_text`. To force eager Whisper preload on CPU anyway, set `OMNIVOICE_ALLOW_CPU_EAGER_ASR=1`. The release image is based on Python 3.13 and is intended to run without live Hugging Face downloads after pull. Version tags such as `v0.2.0` are also available for reproducible deployments.

Tiny tags use the `vX.Y.Z_tiny` pattern. They keep runtime dependencies but skip baked Hugging Face model assets, and are intended for persistent-volume workflows where the cache is warmed on first online use:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_hf_cache:/app/.cache/huggingface -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest_tiny
```

## What You Get

- Browser UI for no-prompt auto voice, voice design, and voice cloning
- Multilingual UI language selector with English fallback for missing labels
- Dedicated Generate and Stream playback tabs for normal output and progressive long-text playback
- Seed and random-seed controls for repeatable generation
- Live GPU monitor for visible NVIDIA GPU utilization, VRAM, temperature, and power draw
- HTTP API for applications and automation
- 600+ language support inherited from OmniVoice
- WAV, MP3, FLAC, and OGG output support
- GPU support when Docker/NVIDIA support is available
- Offline-friendly usage with the standard full image once it is available locally
- OpenAI-compatible `/v1/audio/speech`, `/v1/models`, and `/v1/models/{model}` routes for tools that can target local OpenAI-style TTS servers
- Local voice profiles: upload a reference sample in the UI Add Voice tab, manage it in the Manage tab, then use that name as the TTS voice in compatible clients
- Stored voice profiles reuse cached clone prompts after the first request
- Optional `OMNIVOICE_RESAMPLE_BACKEND=librosa` fallback if a platform has `torchaudio` issues
- Kokoro-shaped compatibility fields and routes such as `voice`, `use_gpu`, `response_format`, `/tts/voices`, `/tts/speakers`, `/tts/stream-formats`, `/tts/convert`, progressive `/tts/stream`, and progressive `/tts/stream-chunks`

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

Use a fixed seed when you want to recreate the same generation:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Repeatable audio from Hangry Labs OmniVoiceTTS","language":"English","output_format":"wav","seed":12345,"randomize_seed":false}' \
  -o seeded.wav
```

Responses include the used seed in the `X-OmniVoiceTTS-Seed` header when generation succeeds.

OpenAI-compatible speech request:

```bash
curl -X POST "http://localhost:7861/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"nova","input":"Hello from an OpenAI-compatible local OmniVoiceTTS endpoint.","response_format":"mp3"}' \
  -o openai-speech.mp3
```

Model discovery through `/v1/models` reports the local `omnivoice` model. Speech requests also accept `omnivoicetts`, `tts-1`, `tts-1-hd`, and `gpt-4o-mini-tts` as compatibility aliases; all of them map to the same local OmniVoice model. Voice aliases such as `alloy`, `echo`, `fable`, `onyx`, `nova`, and `shimmer` are accepted for client compatibility and mapped to local OmniVoice clone/design behavior.

For steadier OpenAI-style playback, standard voice aliases use a local built-in clone reference by default. Advanced clients may send `language`, `seed`, `randomize_seed`, `voice_profile`, `ref_audio`, and `ref_text` as extra JSON fields when the client allows additional parameters.

The browser UI has a **Voices** tab for creating local clone profiles from uploaded reference audio. A profile stores its default language, seed, and seed-randomization behavior. After saving a profile, use its name as the TTS voice in OpenWebUI or another compatible client.

You can still select or override a profile through additional parameters:

```json
{
  "voice_profile": "my-voice",
  "language": "English",
  "seed": 12345,
  "randomize_seed": false
}
```

Profiles are saved under `/app/openai_voice_profiles`. The Quick Start commands mount the named Docker volume `omnivoicetts_openai_voice_profiles` there so profiles persist across container replacement:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Native `/tts/generate`, `/tts/convert`, `/tts/stream`, and `/tts/stream-chunks` requests use the same saved-profile and built-in-alias resolver through either `voice` or `voice_profile`. Explicit `ref_audio` remains the highest-priority voice source.

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

Long text can also be requested through `/tts/stream` or `/tts/stream-chunks`. Those routes start returning encoded audio after each generated text chunk, so playback can begin before the full request completes. They support the same `voice` and `voice_profile` fields as complete generation. For live streaming, WAV requests are returned as MP3 because independent WAV chunks do not form a valid continuous stream.

```bash
curl -X POST "http://localhost:7861/tts/stream-chunks" \
  -H "Content-Type: application/json" \
  -d '{"text":"This longer request can begin playing before the full audio is finished.","voice":"nova","language":"English","output_format":"mp3"}' \
  -o streamed.mp3
```

GPU memory controls:

- Docker images default to `OMNIVOICE_MAX_CONCURRENT_GENERATIONS=1`, so concurrent requests queue per resolved device instead of overlapping large generation allocations.
- `GET /tts/status` reports CUDA `allocated`, `reserved`, `max_allocated`, and `max_reserved` values so live tensors can be distinguished from PyTorch allocator reservation.
- `POST /tts/cache/clear` runs Python garbage collection and `torch.cuda.empty_cache()` without unloading model weights or clearing saved voice-prompt cache entries.
- `POST /tts/purge` unloads cached models, clears saved voice-prompt cache entries, and then clears unused CUDA allocator blocks.
- `OMNIVOICE_EMPTY_CUDA_CACHE_AFTER_REQUEST=1` enables post-request allocator cleanup, but it is off by default because clearing after every request can reduce throughput.

## Image Tags

- Recommended tag for most users: `latest`
- Versioned release tags use the pattern `vX.Y.Z`, for example `v0.2.0`
- Tiny tags use `latest_tiny` or versioned tags such as `v0.2.0_tiny`

## Release Validation

Before the initial release, the Python 3.13 baked image was built and tested without a host model-cache volume mounted. API validation covered `/tts/ping`, `/tts/status`, discovery routes, OpenAPI docs, metrics, real generation in WAV/MP3/FLAC/OGG, voice design, `/tts/stream`, `/tts/convert`, `/tts/purge`, and generation after purge/reload from baked cache.

The v0.2.0 release adds UI-focused validation targets: multilingual interface selection, separate Generate and Stream playback paths, seed reuse, stop-generation behavior for streaming, and the live GPU monitor.

## Attribution

This is an independently maintained Hangry Labs packaging and serving fork of the original OmniVoice project by k2-fsa and contributors:

https://github.com/k2-fsa/OmniVoice

License and attribution are preserved in the repository. Original OmniVoice copyright remains with the upstream authors; Hangry Labs maintains the Docker packaging, Web UI/API integration, documentation, release tooling, and related modifications in this fork.
