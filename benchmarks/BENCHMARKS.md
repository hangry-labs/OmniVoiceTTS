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

Use controlled phases rather than a single `benchmark-all` command. The GPU-memory suite needs Qwen3-ASR and unrelated GPU services stopped on the measured GPU, while semantic quality suites require an available Qwen3-ASR judge. A judge on a separate host can remain running without using TTS GPU memory.

1. Record the image tag or digest, repository revision, driver, runtime settings, and any intended change in each task's comment variable.
2. Stop unrelated GPU workloads. Start only OmniVoiceTTS and run `task benchmark-memory-gpu`. Restart TTS first, preserving its volume, when a clean-process baseline is required after ASR or other model use; a purge/reload is not the same process state.
3. Keep the same TTS deployment running and run `task benchmark-speed`.
4. Use a fixed remote Qwen3-ASR deployment, or start the local judge on port `8000`, then run `task benchmark-speech-quality` and `task benchmark-ssml`. Set `QUALITY_BENCHMARK_ASR_URL` and `SSML_BENCHMARK_ASR_URL` to override the local defaults.
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

## 28 October 2026: Post-283 Validation

Development source: `3481d51` plus the local clone-prompt inference guard and benchmark preflight checks; `1.1-snapshot`. Existing local runtime image: `sha256:1f806c3deeec8d25383131642b28a090c9e77314cba6fed394bfe9c054e7a287`, with source bind-mounted rather than an image rebuild. Runtime: Python 3.13.16, Torch `2.10.0+cu128`, Transformers `5.17.0`, NVIDIA RTX 5070 Ti (16 GB), driver `610.88`. Model and Whisper revisions remain pinned; Windows desktop GPU consumers remained present.

Qwen3-ASR ran on a separate host, reporting `Qwen/Qwen3-ASR-0.6B-hf`. TTS generation and judging were sequential. The judge's public model ID does not establish an identical software or decoding environment to the October 6 local judge. Treat these as new-runtime baselines, not an isolated before/after measurement of PR #283 or an absolute speech-quality score.

| Track | October 6 reference | October 28 result | Interpretation |
|---|---:|---:|---|
| Warmed speed: random / cached / direct reference | 1.047 / 1.013 / 1.317 s | 1.127 / 1.107 / 1.374 s | 300 measured calls plus 30 warmups; 4.3-9.3% slower on the changed runtime/host conditions, not a general speedup claim |
| Warmed GPU process peaks: RV / DV / CR / CC | 2116.9 / 2116.9 / 2118.9 / 2115.2 MiB | 2107.6 / 2116.7 / 2120.1 / 2115.1 MiB | Essentially unchanged; this track excludes the cold long-reference peak |
| Speech: exact ASR matches | 125/180 (69.44%) | 125/180 (69.44%) in both runs | Same 18-language, two-sentence, five-repeat workload; no request errors |
| Speech: mean ASR similarity | 98.28% | 98.48% in both runs | Comparative ASR signal only |
| Speech: ASR repeat-consistent cases | 36/36; earlier canonical run 34/36 | 34/36 in both runs | Hindi 02 and French 02 had different ASR transcripts for identical audio |
| Speech: clean-process average TTS / peak allocation | 1.276 s / 2167.3 MiB | 1.301 s / 2159.8 MiB | First October 28 run retained post-ASR live allocation; use the clean restart repeat for memory comparison |
| SSML-H dialogue completion | 20/20 | 20/20 | Final replies retained for every request |
| SSML-H average TTS | 4.477 s | 4.564 s | About 1.9% slower; same fixed dialogue policy |
| CPU recommendation: stored voice without transcript | 7 GB | 6 GB | Lowest passing tested limit fell from 6144 to 5120 MiB |
| CPU recommendation: stored voice with transcript | 3 GB | 2 GB | Lowest passing tested limit fell from 2560 to 1536 MiB |
| CPU recommendation: random / design / direct without transcript / direct with transcript | 2 / 2 / 6 / 2 GB | 2 / 2 / 6 / 2 GB | Unchanged rounded recommendations |

All 180 audio hashes matched between the two October 28 speech runs, including across the service restart; all five repetitions of each sentence also matched. No October 28 hash matched the older runtime baseline, so the unchanged-runtime determinism rule must not be applied across these runtime changes. The targeted same-runtime old/guarded prompt comparison separately produced identical tokens and fixed-seed speech; its **88.3% reduction in extra cold prompt-preparation peak allocation** is documented in [GPU details](memory/gpu/DETAILS.md#clone-prompt-inference-guard-28-october-2026). It is not an 88.3% reduction in warmed service VRAM.

The first speech run's post-purge baseline still had 2724.5 MiB live allocation and peaked at 2937.9 MiB. A full container restart brought the next run's starting allocation to 1937.2 MiB and peak to 2159.8 MiB. Both runs remain in history; do not attribute that process-state difference to PR #283 or to remote ASR VRAM.

Full per-call evidence and outliers are retained in each suite's `DETAILS.md` and `runs.json`; non-exact speech WAVs remain local for listening. The speed suite's named reference profile was verified before its saved-voice stage, and the runner now rejects missing or transcript-less profiles rather than silently benchmarking voice design.

Reference identity: `examples/original_clone.mp3` and its packaged copy both have SHA-256 `6a0073247382be3966f2edf461e193617d45308729e01c85415188ce5a3ffde3`. The local `benchmark_original_clone` profile uses that sample, the documented transcript, seed `12345`, and no random seed. User-created profiles were not overwritten.

The CPU matrix used the existing runtime image with current source and the unified model cache mounted read-only at `/benchmark-cache`; profile indexes and application settings were isolated from the normal deployment. All six scenarios used the same 140-character request, ascending limits from 1536 MiB, equal memory/swap caps, and one confirmation at the next limit after the first pass. Recommendations add 512 MiB and round up to whole GB. They describe this measured workload, not every CPU, reference length, or concurrency level; previously conservative application RAM-pressure warnings were not lowered by this benchmark-only work.

Validation: `task validate` passed 179 tests (176 passed, three Windows symlink skips), lock validation, and Dockerfile checks. The final benchmark-specific tests passed 19/19. All previous JSON run records were preserved, and all disposable CPU containers were removed. No images were rebuilt and no commits or pushes were made.
