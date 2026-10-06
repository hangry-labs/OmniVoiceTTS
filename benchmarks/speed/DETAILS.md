# OmniVoiceTTS Inference Speed Benchmark Details

Each new official run appends its runtime configuration and full stage summary here. Per-request timings, response headers, language grouping, and byte counts are retained in `runs.json`.

## Categories

- `random_voice`: no reference voice or design prompt.
- `predefined_voice`: named built-in clone alias through the OpenAI-compatible API. Its clone prompt is cached during prewarm.
- `direct_reference_audio`: the reference path is supplied for every native API request and is intentionally not stored in the prompt cache.
- `prewarm_random`, `prewarm_predefined`, and `prewarm_direct_reference`: unmeasured setup calls kept separately from steady-state results.

Historical stage tables are preserved here:

- [Random measured](categories/WARM_RANDOM.md)
- [Cached clone measured](categories/WARM_PREDEFINED.md)
- [Direct reference measured](categories/WARM_DIRECT_REFERENCE.md)
- [Random prewarm](categories/PREWARM_RANDOM.md)
- [Cached clone prewarm](categories/PREWARM_PREDEFINED.md)
- [Direct reference prewarm](categories/PREWARM_DIRECT_REFERENCE.md)

The historical tables were created before this unified detail log and therefore remain the authoritative stage-level presentation for those runs. New runs append both here and to those category tables.

## 06.10.2026 17:50:22 - 1.0-snapshot

- Hardware: `NVIDIA GeForce RTX 5070 Ti`
- Workload: `100` calls per measured category across `20` languages
- Decode steps / format: `24` / `mp3`
- Comment: v1.0-snapshot RTX 5070 Ti baseline; Qwen3-ASR stopped; Windows desktop consumers present

| Stage | Calls | Total | Average | Minimum | Maximum | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| direct_reference_audio | 100 | 131.74s | 1.317s | 1.234s | 1.583s | 8623760 |
| predefined_voice | 100 | 101.301s | 1.013s | 0.942s | 1.156s | 8762960 |
| prewarm_direct_reference | 10 | 13.205s | 1.321s | 1.274s | 1.38s | 965720 |
| prewarm_predefined | 10 | 18.105s | 1.81s | 1.037s | 7.858s | 977720 |
| prewarm_random | 10 | 10.118s | 1.012s | 0.953s | 1.141s | 986840 |
| random_voice | 100 | 104.663s | 1.047s | 0.931s | 1.393s | 8811920 |
