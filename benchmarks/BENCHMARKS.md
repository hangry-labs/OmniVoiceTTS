# OmniVoiceTTS Benchmark Suite

Benchmarks are manual release-engineering tools, not unit tests. They append comparable history only when run without `--no-write`, and they never run through `task test`, `task validate`, `task build`, or `task release`.

See the [benchmark methodology](README.md) for canonical sample selection, warm-up policy, phase isolation, and interpretation limits.

| Area | Official task | Services and isolation | Primary signal |
|---|---|---|---|
| [Inference speed](speed/BENCHMARKS.md) | `task benchmark-speed` | TTS on `:7861`; idle GPU | Warmed and prewarm latency for random, cached-profile, and direct-reference generation |
| [CPU memory](memory/cpu/BENCHMARKS.md) | `task benchmark-memory-cpu` | Docker; no TTS/ASR service required | Lowest passing container limit and conservative RAM recommendation |
| [GPU memory](memory/gpu/BENCHMARKS.md) | `task benchmark-memory-gpu` | GPU TTS on `:7861`; all other GPU work stopped | PyTorch allocation and whole-device VRAM peaks by voice mode |
| [Speech quality](speech-quality/BENCHMARKS.md) | `task benchmark-speech-quality` | TTS on `:7861`, Qwen3-ASR on `:8000`; idle GPU | Multilingual exactness, similarity, repeat consistency, timing, and VRAM |
| [SSML-H reliability](ssml/BENCHMARKS.md) | `task benchmark-ssml` | TTS on `:7861`, Qwen3-ASR on `:8000`; idle GPU | Complete deterministic multi-speaker dialogue |

## Baseline Procedure

Use controlled phases rather than a single `benchmark-all` command. The GPU-memory suite needs Qwen3-ASR and unrelated GPU services stopped, while semantic quality suites require Qwen3-ASR to be running.

1. Record the image tag or digest, repository revision, driver, runtime settings, and any intended change in each task's comment variable.
2. Stop unrelated GPU workloads. Start only OmniVoiceTTS and run `task benchmark-memory-gpu`.
3. Keep the same TTS deployment running and run `task benchmark-speed`.
4. Start the locked Qwen3-ASR service on port `8000`, then run `task benchmark-speech-quality` and `task benchmark-ssml`.
5. Run `task benchmark-memory-cpu` separately. It creates and removes its own constrained CPU containers and can take substantially longer.
6. Review each suite's `BENCHMARKS.md`, `DETAILS.md`, and `runs.json` before committing results.

Smoke tasks validate harness wiring without changing benchmark history:

```powershell
task benchmark-speed-smoke
task benchmark-memory-gpu-smoke
task benchmark-speech-quality-smoke
task benchmark-ssml-smoke
```

Do not compare official rows collected with different hardware, model assets, decoding parameters, container limits, or concurrent GPU workloads. Qwen3-ASR is a stable comparative judge for semantic regressions; it is not ground truth or a replacement for listening tests.
