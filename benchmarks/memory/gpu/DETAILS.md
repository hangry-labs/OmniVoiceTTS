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
