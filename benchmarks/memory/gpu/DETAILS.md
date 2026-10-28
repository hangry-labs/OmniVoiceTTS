# GPU Memory Benchmark Details

The runner calls the shipped HTTP API and reads PyTorch CUDA counters from `/tts/status`. It measures warmed inference rather than cold model loading: every scenario receives its own warmup, then `/tts/cache/clear` resets peak counters while retaining model weights and voice-prompt cache entries.

Whole-device VRAM is sampled with `nvidia-smi` throughout each measured stage. Stop Qwen3-ASR, games, browsers using GPU acceleration, other model containers, and unrelated CUDA work before recording an official baseline. A non-idle GPU makes device peaks unsuitable for comparisons, though the per-process PyTorch counters remain useful.

Raw call timings and memory evidence are stored in `runs.json`. A smoke run uses one scenario and one call with `--no-write`; it validates the harness but is not a benchmark result.

## 06.10.2026 17:43:51 - 1.0-snapshot

- TTS endpoint: `http://127.0.0.1:7861`
- GPU: `NVIDIA GeForce RTX 5070 Ti`; driver `610.88`
- Calls per scenario: `5` after `1` scenario warmup call(s)
- Comment: v1.0-snapshot baseline; Qwen3-ASR stopped; clean OmniVoice container; Windows desktop consumers present

| Scenario | Average seconds | Process allocated | Process reserved | Process peak | Device peak | Samples |
|---|---:|---:|---:|---:|---:|---:|
| RV - random_voice | 1.857 | 1955.7 MiB | 2302.0 MiB | 2116.9 MiB | 4706 MiB | 55 |
| DV - design_voice | 1.775 | 1955.7 MiB | 2302.0 MiB | 2116.9 MiB | 4706 MiB | 53 |
| CR - direct_clone | 1.619 | 1955.7 MiB | 2202.0 MiB | 2118.9 MiB | 4608 MiB | 48 |
| CC - cached_clone | 1.549 | 1955.7 MiB | 2358.0 MiB | 2115.2 MiB | 4764 MiB | 46 |

## Clone-Prompt Inference Guard: 28 October 2026

Focused regression validation for [upstream PR #283](https://github.com/k2-fsa/OmniVoice/pull/283), not a new full-suite memory baseline. Saved-voice cache misses and SSML-H dynamic voices prepare prompts before entering `generate()`'s inference guard. Decorating `create_voice_clone_prompt()` itself prevents unnecessary autograd intermediates in these paths; it does not change model weights or the prompt-cache policy.

- Runtime: `1.1-snapshot`, Python 3.13, PyTorch `2.10.0+cu128`, RTX 5070 Ti (16 GB), pinned default checkpoint and embedded Higgs tokenizer.
- Input: the trusted packaged `openai_default_voice.mp3`, repeated and truncated to 15 seconds. The longer input tests encoder memory only; supplied placeholder text is not used to claim transcription or generation quality for that artificial clip.
- Method: load one model in a separate Docker process, warm the tokenizer, then compare the undecorated method (`__wrapped__`) against the guarded method with caller gradients enabled. Run before/after/after/before, collecting garbage, synchronizing CUDA, clearing unused allocator blocks, and resetting peak counters before each call.
- Both repetitions produced the same peak allocations and identical audio tokens. Resident allocation before each measured call was 1,946.32 MiB.

| Prompt preparation | Peak allocated, including resident model | Extra peak above resident allocation |
|---|---:|---:|
| Before: gradients enabled | 6,406.46 MiB | 4,460.14 MiB |
| After: inference mode | 2,466.44 MiB | 520.12 MiB |

The additional peak allocation fell **88.3%** (4.36 GiB to 0.51 GiB). This is not an 88.3% reduction in total service VRAM or a general inference-speed claim. Counters cover this test process's PyTorch allocation, not Windows, other GPU users, or the separate API process; whole-device VRAM was not used as comparative evidence.

For output equivalence, use the original unmodified short reference and its locally transcribed text. After a generation warmup, prompts prepared with the old and guarded methods produced exactly identical waveforms for the same English sentence, seed `4242`, and 24 generation steps. No-transcript prompt creation remains covered by regression tests and live API smoke validation; ASR is not removed or bypassed by this change. These bounded checks do not replace the multilingual speech-quality suite or human listening review.

Regression coverage: `tests/test_voice_clone_inference.py` verifies inference/gradient state during encoding and transcription, caller-state restoration on success and exceptions, one-time prompt encoding on cache reuse, and SSML-H dynamic-voice preparation.

## 28.10.2026 17:43:10 - 1.1-snapshot

- TTS endpoint: `http://127.0.0.1:7861`
- GPU: `NVIDIA GeForce RTX 5070 Ti`; driver `610.88`
- Calls per scenario: `5` after `1` scenario warmup call(s)
- Comment: PR283 post-fix; source-mounted 3481d51 plus local inference guard; Torch2.10-cu128 Transformers5.17; remote ASR; Windows desktop present; warmed short-reference workload, not cold15s peak test

| Scenario | Average seconds | Process allocated | Process reserved | Process peak | Device peak | Samples |
|---|---:|---:|---:|---:|---:|---:|
| RV - random_voice | 1.959 | 1946.3 MiB | 2304.0 MiB | 2107.6 MiB | 4822 MiB | 59 |
| DV - design_voice | 1.816 | 1955.4 MiB | 2304.0 MiB | 2116.7 MiB | 4831 MiB | 55 |
| CR - direct_clone | 1.729 | 1955.4 MiB | 2202.0 MiB | 2120.1 MiB | 4728 MiB | 52 |
| CC - cached_clone | 1.580 | 1955.4 MiB | 2340.0 MiB | 2115.1 MiB | 4864 MiB | 48 |
