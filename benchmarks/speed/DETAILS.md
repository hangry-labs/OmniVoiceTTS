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

## 28.10.2026 17:49:57 - 1.1-snapshot

- Hardware: `NVIDIA GeForce RTX 5070 Ti`
- Workload: `100` calls per measured category across `20` languages
- Decode steps / format: `24` / `mp3`
- Comment: PR283 post-fix; 3481d51 plus local inference guard; Torch2.10-cu128 Transformers5.17; Windows desktop; remote ASR idle; same canonical 300-call workload; not isolated against older dependency baseline

| Stage | Calls | Total | Average | Minimum | Maximum | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| direct_reference_audio | 100 | 137.396s | 1.374s | 1.255s | 1.829s | 8536400 |
| predefined_voice | 100 | 110.731s | 1.107s | 0.921s | 2.339s | 8570960 |
| prewarm_direct_reference | 10 | 15.435s | 1.543s | 1.275s | 2.516s | 950360 |
| prewarm_predefined | 10 | 10.451s | 1.045s | 0.934s | 1.262s | 960440 |
| prewarm_random | 10 | 10.204s | 1.02s | 0.926s | 1.102s | 987320 |
| random_voice | 100 | 112.671s | 1.127s | 0.946s | 1.591s | 8811920 |
