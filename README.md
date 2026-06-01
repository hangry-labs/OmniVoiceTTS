<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/">
    <img src="logo.jpg" alt="Hangry Labs OmniVoiceTTS logo" width="720">
  </a>
</p>

# Hangry Labs OmniVoiceTTS

Easy-to-run OmniVoice text-to-speech Docker images with a browser UI and HTTP API included.

This Hangry Labs fork is made for ease of use. The aim is that anyone should be able to run massively multilingual text to speech without fighting Python environments, missing model files, or unclear setup: a person trying it at home, a developer wiring it into an app, or a professional evaluating it for local deployment. Install Docker, run one command from Quick Start, open the local link, and start generating speech.

You get:
- A browser UI for auto voice, voice design, and voice cloning
- An HTTP API for your own applications and tools
- No manual Python, model, ASR, or audio dependency setup
- 600+ language support inherited from OmniVoice
- WAV, MP3, FLAC, and OGG output
- GPU acceleration when Docker/NVIDIA support is available
- Offline-friendly usage: download the full image once, keep it, and run it later without relying on live model downloads

Official Docker images are intended for: [hangrylabs/omnivoicetts on Docker Hub](https://hub.docker.com/r/hangrylabs/omnivoicetts/tags).

**Listen to examples first:** [hangry-labs.github.io/OmniVoiceTTS/examples](https://hangry-labs.github.io/OmniVoiceTTS/examples/).

Hangry Labs home: [nuggies.website](https://nuggies.website/).

## Browser UI

The included browser UI is built for local generation, voice design, voice cloning, progressive streaming tests, seed-based reproducibility, output-format control, and live GPU visibility.

![OmniVoiceTTS browser UI](docs/ui.jpg)

---

## Responsible Use

OmniVoice supports voice cloning. Do not use this project for unauthorized voice cloning, impersonation, fraud, harassment, scams, or any illegal or unethical activity. Only clone voices when you have the rights and consent to do so. You are responsible for complying with applicable laws, regulations, platform rules, and ethical standards.

---

## Quick Start

Run with NVIDIA GPU support:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Run on CPU:

```bash
docker run -p 7861:7861 -e OMNIVOICE_DEVICE=cpu -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Run on a specific GPU (example: GPU index `1`):

```bash
docker run -p 7861:7861 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles hangrylabs/omnivoicetts:latest
```

Then open: **[http://localhost:7861](http://localhost:7861)**

The named `omnivoicetts_openai_voice_profiles` volume stores voices created in the UI so they survive container replacement and image updates. Docker creates the volume automatically the first time you run one of these commands.

The full image is baked with the OmniVoice model, the Higgs audio tokenizer, and Whisper ASR assets. After the image is pulled, normal runtime is configured for offline use with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. The Python 3.13 baked image was validated with no host model-cache volume mounted.

---

## API Usage Example

Default API behavior returns WAV:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs OmniVoiceTTS.","language":"English"}' \
  -o output.wav
```

Request MP3 when you want compact output:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs OmniVoiceTTS.","language":"English","output_format":"mp3"}' \
  -o output.mp3
```

Voice design:

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a custom designed voice.","language":"English","instruct":"female, low pitch, british accent","output_format":"mp3"}' \
  -o designed.mp3
```

Voice design is for speaker attributes only. Do not combine `instruct` with bracket expression tags such as `[laughter]` or `[sigh]`; use no voice prompt or voice cloning for those expressive tags instead.

Voice cloning with a reference audio path mounted into the container:

```bash
docker run -p 7861:7861 --gpus "device=0" -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_openai_voice_profiles:/app/openai_voice_profiles -v "%cd%/samples:/data" hangrylabs/omnivoicetts:latest
```

```bash
curl -X POST "http://localhost:7861/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"This voice follows the reference sample.","language":"English","ref_audio":"/data/ref.wav","ref_text":"Transcript of the reference audio.","output_format":"mp3"}' \
  -o cloned.mp3
```

Kokoro-shaped compatibility fields are accepted where they can be translated cleanly. Existing callers may send `voice`, `use_gpu`, or `response_format`. The `voice` field can name a saved local voice profile or an OpenAI-style alias such as `nova`; unknown Kokoro speaker ids are accepted for compatibility but ignored because OmniVoice uses no-prompt generation, voice design, or reference-audio cloning rather than fixed speaker ids.

Output format can be sent as `output_format`, `format`, or Kokoro/OpenAI-style `response_format`.

OpenAI-compatible speech clients can call the local server through `/v1/audio/speech`:

```bash
curl -X POST "http://localhost:7861/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"nova","input":"Hello from an OpenAI-compatible local OmniVoiceTTS endpoint.","response_format":"mp3"}' \
  -o openai-speech.mp3
```

Supported compatibility model ids are `omnivoice`, `tts-1`, `tts-1-hd`, and `gpt-4o-mini-tts`. OpenAI-style voice names such as `alloy`, `echo`, `fable`, `onyx`, `nova`, and `shimmer` are accepted as local compatibility aliases.

For OpenAI-compatible TTS, standard voice aliases use a local built-in clone reference by default so sentence-by-sentence playback stays closer to the same speaker identity. Advanced clients may also pass OmniVoice extensions such as `language`, `seed`, `randomize_seed`, `voice_profile`, `ref_audio`, and `ref_text` in the request body.

The browser UI includes a **Voices** tab where you can upload a reference sample and save it as a named local voice profile. The profile stores its default language, seed, and seed-randomization behavior. In OpenWebUI, set the TTS voice to the saved profile name, for example `my-voice`.

OpenAI-compatible clients can also select or override that profile through additional request parameters:

```json
{
  "voice_profile": "my-voice",
  "language": "English",
  "seed": 12345,
  "randomize_seed": false
}
```

Voice profiles are stored inside the container at `/app/openai_voice_profiles`. The Quick Start commands mount the named Docker volume `omnivoicetts_openai_voice_profiles` there so profiles survive container replacement.

The same saved profiles and built-in aliases are available on native `/tts/generate`, `/tts/convert`, `/tts/stream`, and `/tts/stream-chunks` requests through either `voice` or `voice_profile`. Explicit `ref_audio` still takes precedence when provided.

Useful endpoints:

- `GET /v1/models`
- `GET /v1/models/{model}`
- `GET /v1/audio/models`
- `GET /v1/audio/voices`
- `POST /v1/audio/speech`
- `GET /tts/ping`
- `GET /tts/status`
- `GET /tts/defaults`
- `GET /tts/formats`
- `GET /tts/stream-formats`
- `GET /tts/languages`
- `GET /tts/speakers?language=a`
- `GET /tts/voices`
- `GET /tts/voice-design/options`
- `POST /tts/generate`
- `POST /tts/convert`
- `POST /tts/stream`
- `POST /tts/stream-chunks`
- `POST /tts/cache/clear`
- `POST /tts/metrics`
- `POST /tts/purge`

`/tts/generate` and `/tts/convert` return complete generated audio. `/tts/stream` and `/tts/stream-chunks` progressively return encoded audio after each generated long-text chunk and support the same `voice`/`voice_profile` profile resolution; WAV stream requests are returned as MP3 for live playback compatibility.

Docker images default to `OMNIVOICE_MAX_CONCURRENT_GENERATIONS=1`, so concurrent API callers queue on each resolved device instead of overlapping GPU-heavy generation. `/tts/status` reports CUDA `allocated`, `reserved`, and peak allocator counters. `POST /tts/cache/clear` releases unused PyTorch CUDA allocator blocks without unloading model weights or saved voice-prompt cache entries; `POST /tts/purge` unloads cached models and then performs the stronger CUDA allocator cleanup. `OMNIVOICE_EMPTY_CUDA_CACHE_AFTER_REQUEST=1` can force allocator cleanup after every request, but it is off by default because it may reduce throughput.

Interactive API documentation is available at **[http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)**.

### Use From Python

Install this package in a Python project and point the client at a running OmniVoiceTTS server:

```python
from omnivoice import OmniVoiceTTSClient

tts = OmniVoiceTTSClient("http://localhost:7861")

audio = tts.generate(
    text="Hello from my Python app.",
    language="English",
    instruct="female, low pitch, british accent",
    output_format="mp3",
)

audio.save("hello.mp3")
```

OpenAI-shaped speech calls can also be made through the bundled client:

```python
from omnivoice import OmniVoiceTTSClient

tts = OmniVoiceTTSClient("http://localhost:7861")
audio = tts.openai_speech(
    model="tts-1",
    voice="nova",
    input="Hello from an OpenAI-compatible local endpoint.",
    response_format="mp3",
)
audio.save("openai-speech.mp3")
```

---

## Docker Features

- Full baked image with OmniVoice model assets and Whisper ASR assets included
- Optional tiny image target for cache-volume workflows
- GPU acceleration when available
- Stored OpenAI voice profiles reuse cached clone prompts after the first request
- Serialized GPU generation by default to avoid concurrent VRAM spikes
- CUDA allocator diagnostics and cache clearing without unloading model weights
- Optional `OMNIVOICE_RESAMPLE_BACKEND=librosa` fallback if a platform has `torchaudio` issues
- HTTP API + web UI in one container
- Offline-friendly runtime flags by default
- Persistent Hugging Face cache volume support in the local Taskfile workflow
- Persistent OpenAI voice-profile volume support in the local Taskfile workflow
- Kokoro-shaped compatibility routes for easier integration with existing TTS tooling

---

## FAQ

### Why does OmniVoiceTTS not support FlashAttention?

We tested FlashAttention-2 with the official Dao-AILab wheel for Python 3.13, Torch 2.8, and CUDA 12.8. It installed and ran, but it did not improve the workloads this project is built around. For normal UI/OpenAI-compatible usage, where clients often send one sentence per request, it made generation substantially slower.

Single-request API benchmark on RTX 5060 Ti, 100 calls per category:

| Category | Standard attention avg | FlashAttention avg | Result |
|---|---:|---:|---:|
| Random/no reference | 1.104s | 1.537s | 39.2% slower |
| Predefined cached voice | 1.036s | 1.628s | 57.1% slower |
| Direct reference audio | 1.498s | 2.010s | 34.2% slower |

We also tested true batched generation. Batch size 4 was still slower with FlashAttention. Batch size 10 showed small gains for clone paths but not for random/no-reference generation:

| Batch category | Standard attention avg | FlashAttention avg | Result |
|---|---:|---:|---:|
| Random/no reference, batch 10 | 0.638s/item | 0.657s/item | 3.0% slower |
| Predefined cached voice, batch 10 | 0.995s/item | 0.955s/item | 4.0% faster |
| Direct reference audio, batch 10 | 1.419s/item | 1.372s/item | 3.3% faster |

A larger 100-message batch gave only a small random/no-reference improvement, then became impractical for clone benchmarking on the 16 GB RTX 5060 Ti:

| Batch category | Standard attention | FlashAttention | Result |
|---|---:|---:|---:|
| Random/no reference, one 100-message batch | 92.18s total | 89.63s total | 2.8% faster |
| Predefined/clone, one 100-message batch | exceeded 900s timeout | not completed | impractical |

The FlashAttention experiment also increased image complexity and size, added another GPU-specific binary dependency, consumed more VRAM in large-batch tests, and produced worse stability characteristics for the use cases we actually support. Based on those results, OmniVoiceTTS intentionally does not ship FlashAttention support. The same lesson applies to other Hangry Labs speech projects: do not assume FlashAttention helps STT/TTS workloads without project-specific benchmarks.

---

## Local Development

This repository currently targets Python `>=3.13, <3.14`. The Docker image uses `python:3.13-slim`, and `task deps` regenerates Linux/Python 3.13 requirements.

Build and run the full baked image:

```bash
task image
task imagerun
task imageweb
task imageapi
```

Build and run the tiny image:

```bash
task image-tiny
task imagerun-tiny
```

Run the example-generation benchmark against the active local API:

```bash
task benchmark-examples
```

The benchmark reuses the public example workload, prewarms the model and benchmark reference voice, then runs no-prompt, predefined cached-reference, and direct reference-audio rounds. Results are appended to per-category Markdown tables under `benchmarks/` for human tracking and `benchmarks/example-generation.json` for detailed machine-readable history. Use `BENCHMARK_ITEMS=1` or `BENCHMARK_LIMIT_LANGUAGES=1` for quick smoke checks.

By default each measured stage prewarms immediately before it runs: 10 no-prompt warmup calls before `random_voice`, 10 predefined-reference warmup calls before `predefined_voice`, and 10 direct-reference warmup calls before `direct_reference_audio`. It then runs 100 no-prompt measured calls, 100 predefined cached-reference measured calls, and 100 direct `ref_audio` measured calls. The measured set is deterministic: the first two random samples from each language in `examples/assets/manifest.json`, repeated in the same order as needed to reach 100 calls per round.

Hot-swap local service code into the container without rebuilding:

```bash
task localrun
task localrun-tiny
task logs
```

Dependency and cleanup helpers:

```bash
task deps
task imagestop
task nuke
```

`task imagerun` and `task localrun` mount named Docker volumes at `/app/.cache/huggingface` and `/app/openai_voice_profiles` so cache assets and saved OpenAI voice profiles can survive container and image rebuilds. Baked run tasks seed missing cache files from the full image before startup.

Release from a clean tree:

```bash
task release DRY_RUN=1
task release
```

The release task is intentionally allowed to create the release commit, annotated tag, and next-snapshot commit. Outside that bounded release flow, normal project changes should be reviewed and committed by the repository owner.

---

## Original OmniVoice Project

OmniVoice is a massively multilingual zero-shot text-to-speech model supporting 600+ languages. It provides:

- Voice cloning from a short reference audio clip
- Voice design from speaker attributes such as gender, age, pitch, style, English accent, and Chinese dialect
- Auto voice generation with no reference prompt
- Fine-grained controls such as non-verbal symbols and pronunciation correction

Upstream links:

- Original repository: [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice)
- Hugging Face model: [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice)
- Hugging Face Space: [k2-fsa/OmniVoice](https://huggingface.co/spaces/k2-fsa/OmniVoice)
- Paper: [arXiv:2604.00688](https://arxiv.org/abs/2604.00688)

Runtime discovery is available from the local API:

- Supported languages: `GET /tts/languages`
- Voice design options: `GET /tts/voice-design/options`
- Output formats: `GET /tts/formats`
- Interactive API reference: `GET /tts/docs`

The original Python CLI tools are still present:

```bash
omnivoice-demo --ip 0.0.0.0 --port 8001
omnivoice-infer --model k2-fsa/OmniVoice --text "Hello world." --output hello.wav
omnivoice-infer-batch --model k2-fsa/OmniVoice --test_list test.jsonl --res_dir results/
```

This fork intentionally removes upstream training, data-preparation, and benchmark-evaluation pipelines from the runtime-focused package. For model training or research reproduction, use the original [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) repository.

---

## About This Fork

This project is an independently maintained packaging and serving fork of the original [OmniVoice](https://github.com/k2-fsa/OmniVoice) project by k2-fsa and contributors.

The upstream model and research are the core contribution. This Hangry Labs fork focuses on making OmniVoice simple to run and integrate: Docker image, included UI, HTTP API, offline-friendly baked assets, practical examples, and release tooling.

License and attribution are preserved in [LICENSE](LICENSE).

---

## Support & Issues

If you encounter bugs, have feature requests, or need help using Hangry Labs OmniVoiceTTS:

- Open a new [GitHub Issue](https://github.com/Hangry-Labs/OmniVoiceTTS/issues) with as much detail as possible
- Include error messages, logs, Docker command, GPU/CPU mode, and reproduction steps
- For upstream model behavior, also check the original [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) project

---

## Version History

### v0.2.0

- Reworked the browser UI into a branded Hangry Labs experience while keeping Gradio controls stable and functional.
- Added the new top banner artwork, build/runtime badge, project links, and a cleaner right-side output/control layout.
- Added multilingual UI locale support with dynamic labels, hints, generation controls, and safety text.
- Added expanded expressive bracket-tag guidance in the UI, including supported tags and the Voice Design incompatibility warning.
- Added practical progressive chunk streaming for long-form TTS through `/tts/stream` and `/tts/stream-chunks`.
- Added a dedicated UI Stream tab with buffered chunk playback and a Stop Generation control, following the stable KokoroTTS-style two-player pattern.
- Added reproducible generation controls: Seed, Randomize Seed, API `seed` / `randomize_seed` fields, and `X-OmniVoiceTTS-Seed` response headers.
- Added balanced automatic voice-profile selection for UI No Voice Prompt mode on plain text, while keeping true no-prompt behavior for expressive bracket tags.
- Added a compact live GPU monitor to the browser UI with utilization, VRAM, temperature, power draw, and sparkline history.
- Added the browser UI screenshot to README and Docker Hub documentation.
- Updated Docker Hub docs to put the public examples page and browser UI preview front and center.
- Improved local development helpers and release scripting for the `0.2.x` release line.

### v0.1.0

- Forked OmniVoice into a Hangry Labs runtime-focused project for local TTS use.
- Added Python 3.13 support with pinned runtime dependencies, refreshed lockfiles, and Docker images based on `python:3.13-slim`.
- Added full baked Docker packaging that prefetches OmniVoice, the Higgs audio tokenizer, and Whisper ASR assets for offline-friendly runtime after image pull.
- Added a tiny Docker target for persistent Hugging Face cache-volume workflows.
- Added GitHub Actions for full and tiny Docker Hub image publishing on `master`, release tags, and manual dispatch.
- Added a unified Gradio browser UI and FastAPI HTTP API on port `7861`.
- Added auto voice, structured voice design, and reference-audio voice cloning workflows.
- Added discovery/status endpoints for ping, status, defaults, formats, languages, speakers, voices, voice-design options, metrics, and OpenAPI docs.
- Added synthesis endpoints for generate, convert, progressive chunk streaming, and purge.
- Added WAV, MP3, FLAC, and OGG output support, plus `output_format`, `format`, and Kokoro/OpenAI-style `response_format` compatibility.
- Added Kokoro-shaped compatibility fields/routes where they can be translated cleanly, including `voice`, `use_gpu`, `/tts/voices`, `/tts/speakers`, `/tts/stream-formats`, `/tts/convert`, and `/tts/stream`.
- Added advanced generation controls for guidance, denoise/preprocess/postprocess, chunking, temperature, layer penalty, pitch, tempo, volume, and loudness normalization.
- Added a dependency-free Python HTTP client.
- Added Taskfile workflows for image build, image run, local bind-mounted run, API smoke testing, logs, cleanup, release, app injection, NAS shell access, and local dev process cleanup.
- Removed upstream training, data-preparation, evaluation, fine-tuning, and benchmark workflows from this fork to keep the project focused on inference, UI, API, and Docker runtime.
- Simplified public docs to README plus Docker Hub docs, with runtime discovery delegated to API endpoints.
- Added Hangry Labs branding assets, static 404 page, Docker Hub documentation, and a GitHub Pages examples showcase.
- Added 20-language public audio examples with 280 MP3 files: 10 random voice-variety samples, 3 translated intros, and 1 cross-language clone demo per language.
- Added native-language example-page controls, embedded manifest data for fetch-free GitHub Pages/direct-file preview, custom audio cards, progress bars, shared volume/mute, random intro playback, and a highlighted clone demo.
- Added a runtime guard that blocks voice-design `instruct` together with bracket expression tags such as `[laughter]` and `[sigh]`, after testing showed that combination can produce unstable non-speech audio.
- Regenerated affected non-verbal public examples without voice-design `instruct`, avoiding whisper plus bracket tags and placing tags inside sentences with follow-up text.
- Validated a fresh Python 3.13 baked image without a host model-cache volume mounted, with offline flags enabled, GPU inference, all output formats, stream/convert routes, purge, and reload from baked cache.

---

## Citation

If you use OmniVoice in research, cite the upstream work:

```bibtex
@article{zhu2026omnivoice,
      title={OmniVoice: Towards Omnilingual Zero-Shot Text-to-Speech with Diffusion Language Models},
      author={Zhu, Han and Ye, Lingxuan and Kang, Wei and Yao, Zengwei and Guo, Liyong and Kuang, Fangjun and Han, Zhifeng and Zhuang, Weiji and Lin, Long and Povey, Daniel},
      journal={arXiv preprint arXiv:2604.00688},
      year={2026}
}
```

---

## License

This fork is licensed under the [Apache License 2.0](LICENSE).

Original work by k2-fsa and contributors in [OmniVoice](https://github.com/k2-fsa/OmniVoice). The upstream responsible-use disclaimer is preserved in spirit here: users must not use this model for unauthorized voice cloning, voice impersonation, fraud, scams, or any other illegal or unethical activities.
