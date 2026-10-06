# OmniVoiceTTS Inference Speed Benchmarks

Append one row per official end-to-end HTTP generation benchmark. Lower times are better.

The fixed workload uses the first two random samples from each language in `examples/assets/manifest.json`, repeated deterministically to 100 measured calls per category. Each category is warmed immediately before it is measured. The three measured paths are random/no-prompt generation, a predefined cached clone voice, and direct reference-audio cloning. Prewarm averages remain visible because cold model or prompt preparation regressions matter even though they are excluded from measured category totals.

Use the same image, GPU, decode steps, output format, workload size, and otherwise idle host when comparing rows. Historical rows without hardware metadata predate runtime diagnostics. Full request data is stored in `runs.json`; stage-level histories remain under `categories/`.

| Run | GPU | Calls/category | Steps | Random avg | Cached clone avg | Direct reference avg | Random prewarm avg | Cached prewarm avg | Direct prewarm avg | Measured total | Comment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 14.05.2026 22:22:11 - 0.2.1-snapshot | Unknown (legacy run) | 100 | 24 | 1.094 | 1.446 | n/a | 1.727 | n/a | n/a | 254.056 | Historical migrated run |
| 14.05.2026 22:44:20 - 0.2.1-snapshot | Unknown (legacy run) | 100 | 24 | 1.138 | 1.408 | 1.474 | 1.732 | n/a | n/a | 402.023 | Historical migrated run |
| 14.05.2026 23:04:48 - 0.2.1-snapshot | Unknown (legacy run) | 100 | 24 | 1.125 | 1.581 | 1.536 | 1.332 | 1.411 | 1.57 | 424.154 | Historical migrated run |
| 14.05.2026 23:24:54 - 0.2.1-snapshot | Unknown (legacy run) | 100 | 24 | 1.104 | 1.036 | 1.498 | 1.653 | 1.078 | 1.553 | 363.790 | Historical migrated run |
| 02.07.2026 22:06:25 - 0.2.1-snapshot | NVIDIA GeForce RTX 5070 Ti | 100 | 24 | 1.111 | 1.186 | 1.683 | 2.353 | 1.394 | 1.349 | 398.007 | Historical migrated run |
| 02.07.2026 22:29:04 - 0.2.1-snapshot | NVIDIA GeForce RTX 5070 Ti | 100 | 24 | 1.18 | 1.111 | 1.384 | 1.16 | 1.339 | 1.371 | 367.533 | Historical migrated run |
| 06.10.2026 17:50:22 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 100 | 24 | 1.047 | 1.013 | 1.317 | 1.012 | 1.81 | 1.321 | 337.704 | v1.0-snapshot RTX 5070 Ti baseline; Qwen3-ASR stopped; Windows desktop consumers present |
