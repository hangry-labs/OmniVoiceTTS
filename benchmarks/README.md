# OmniVoiceTTS Benchmarks

This directory contains the manual release-engineering benchmarks used to detect performance, memory, speech, and dialogue regressions. They are not unit tests and do not run as part of `task test`, `task validate`, `task build`, or `task release`.

Benchmark results are comparative. A result is meaningful only when the image or revision, model assets, hardware, driver, runtime settings, workload, and background load are recorded and held constant. Start with the [benchmark result index](BENCHMARKS.md), then use each suite's `DETAILS.md` and `runs.json` for the complete evidence.

## Benchmark Suites

| Suite | Official task | Canonical workload | Primary signal |
|---|---|---|---|
| [Inference speed](speed/BENCHMARKS.md) | `task benchmark-speed` | Three 100-call rounds across all 20 manifest languages | Warmed latency for random, cached-profile, and direct-reference generation |
| [CPU memory](memory/cpu/BENCHMARKS.md) | `task benchmark-memory-cpu` | Six voice modes in fresh memory-constrained CPU containers | Lowest passing container limit and conservative RAM recommendation |
| [GPU memory](memory/gpu/BENCHMARKS.md) | `task benchmark-memory-gpu` | Four voice modes, each warmed independently | PyTorch allocation and whole-device VRAM peaks |
| [Speech quality](speech-quality/BENCHMARKS.md) | `task benchmark-speech-quality` | Two sentences per judge-supported language, repeated five times | Comparative transcript similarity, repeat consistency, timing, and diagnostics |
| [SSML-H reliability](ssml/BENCHMARKS.md) | `task benchmark-ssml` | One fixed two-speaker dialogue across 20 deterministic seeds | Complete dialogue and final-turn retention |

## Canonical Samples

[`examples/assets/manifest.json`](../examples/assets/manifest.json) is the canonical multilingual text source. Selection is deterministic and follows manifest order; benchmark runners never choose samples randomly.

- The speed suite selects the first two `random` entries for every manifest language and repeats that ordered set until each measured category contains 100 calls.
- The speech-quality suite uses the first `clone` entry in each selected language for warm-up, then generates the first two `random` entries five times each with one fixed seed per sentence.
- Speech-quality includes only languages accepted by the locked Qwen3-ASR judge. The current canonical workload is 18 languages and 180 measured calls. This filter does not describe OmniVoiceTTS language support.
- Clone and reference scenarios use [`examples/original_clone.mp3`](../examples/original_clone.mp3) through its packaged runtime copy at `/app/omnivoice/runtime_assets/voices/openai_default_voice.mp3`.
- The fixed reference transcript is `Hello from OmniVoice. This Docker image includes a browser UI and an HTTP API.`

Memory suites use a stable, realistic two-sentence request instead of the multilingual manifest:

```text
This CPU memory benchmark uses a realistic two-sentence request to estimate the RAM needed for local text to speech with common voice modes.
```

```text
This GPU memory benchmark uses a realistic two-sentence request to measure warmed inference for the voice modes commonly used through the OmniVoiceTTS API.
```

Both texts remain fixed so memory measurements can be compared between revisions.

## Methodology

### Warm-up and determinism

Every voice path is warmed independently before its measured calls. Warm-up work is excluded from steady-state measurements and reported separately where useful. Seeds, decoding steps, output format, sample order, and reference audio are fixed by each runner unless an operator explicitly overrides them.

The speed workload uses 24 decoding steps and MP3 output. It performs 10 warm-up calls for each of its three categories before measuring 100 calls per category:

- `random_voice`: no voice prompt or design prompt.
- `predefined_voice`: the named `benchmark_original_clone` saved profile, whose prompt is cached during warm-up.
- `direct_reference_audio`: the same reference path is supplied on every request without storing its prompt in the profile cache.

### CPU memory

Each CPU scenario runs in a fresh Docker container with equal memory and swap limits. Limits start at 1536 MiB and increase through a fixed practical sequence up to 12 GiB; sub-gigabyte configurations are intentionally not tested. The six paths are random voice, designed voice, direct clone with and without a transcript, and stored voice with and without a transcript.

The reported recommendation adds 512 MiB to the first passing limit and rounds up to a whole GiB. This is operational headroom, not a claim that every host and request length will fit within that amount.

### GPU memory

Random voice, designed voice, direct clone, and cached clone are each warmed once and measured for five calls by default. Before a scenario, the runner clears unused CUDA allocator blocks and resets peak counters without unloading the model. It records both PyTorch allocated/reserved memory and `nvidia-smi` whole-device VRAM.

Qwen3-ASR and unrelated GPU workloads must be stopped for this suite. Whole-device VRAM includes the desktop and every other process, so the dedicated GPU-memory suite is authoritative for clean TTS comparisons.

### Speech quality

The quality runner generates and stages every WAV before transcription begins. Qwen3-ASR is warmed only after the TTS phase, then transcribes the staged files. TTS generation and ASR judging are never interleaved on the shared GPU.

The runner uses 32 decoding steps and fixed per-sentence seeds. Transcript comparison applies Unicode compatibility normalization, case folding, and removal of punctuation and whitespace before calculating exact matches and character similarity. It records repeat consistency, generation time, real-time factor, ASR time, memory diagnostics, and hashes. Non-exact or failed audio is retained under the git-ignored `.ai/benchmark-speech-quality` directory for listening.

Qwen3-ASR is a stable comparative judge, not ground truth. Its transcript can be wrong even when the generated audio is correct. These metrics are intended to reveal changes between equivalent runs; they do not measure objective pronunciation accuracy or replace human listening.

### SSML-H reliability

The SSML-H suite generates the fixed Bob and Elisabeth dialogue `Are we ready? Yes, all preparations are complete.` with 32 decoding steps. It uses 20 fixed seeds; `2717518076` remains first because it reproduced the original missing-final-turn failure. All WAVs are generated before Qwen3-ASR is warmed and transcription begins.

A call passes when its normalized word sequence contains the complete expected dialogue. This suite targets missing turns and truncated final speech, not subjective voice quality.

## Controlled Baseline Procedure

1. Record the image tag or digest, repository revision, driver, runtime settings, hardware, and intended change in each task's comment variable.
2. Stop unrelated GPU work. Start only OmniVoiceTTS and run `task benchmark-memory-gpu`.
3. Keep that TTS deployment running and run `task benchmark-speed`.
4. Start the locked Qwen3-ASR service on port `8000`, then run `task benchmark-speech-quality` and `task benchmark-ssml`.
5. Run `task benchmark-memory-cpu` separately. It creates and removes its own constrained CPU containers and takes substantially longer.
6. Review the generated `BENCHMARKS.md`, `DETAILS.md`, and `runs.json` changes before committing an official baseline.

Smoke tasks validate harness wiring without appending benchmark history:

```powershell
task benchmark-speed-smoke
task benchmark-memory-gpu-smoke
task benchmark-speech-quality-smoke
task benchmark-ssml-smoke
```

Use `task benchmark-memory-cpu-smoke` only when Docker is available and the additional CPU runtime is acceptable.

## Result Files

Each suite follows the same evidence layout:

- `BENCHMARKS.md` contains the concise, append-only comparison table.
- `DETAILS.md` contains methodology notes and human-readable evidence for each run.
- `runs.json` contains the structured per-run and per-call measurements.
- Local diagnostic audio and temporary artifacts live under `.ai` and are not committed.

Do not compare rows collected with different hardware, model assets, decoding parameters, container limits, judge versions, or concurrent workloads. When any of those inputs change, record a new baseline before evaluating later regressions.
