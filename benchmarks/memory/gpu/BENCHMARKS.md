# GPU Memory Benchmarks

Append one row per official warmed GPU-memory benchmark. Each scenario is prewarmed independently, then unused allocator blocks are cleared and PyTorch peak counters are reset without unloading model weights or cached clone prompts.

`Process peak` is PyTorch's maximum allocated memory for the TTS process. `Device peak` is sampled through `nvidia-smi` and includes every process on the selected GPU. Official comparisons require the same image, settings, workload, and an otherwise idle GPU.

Scenario shortcuts: `RV` random voice, `DV` designed voice, `CR` uncached direct clone with transcript, and `CC` cached clone with transcript.

| Run | GPU | Calls | RV process peak | RV device peak | DV process peak | DV device peak | CR process peak | CR device peak | CC process peak | CC device peak | Comment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 06.10.2026 17:43:51 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 5 | 2116.9 | 4706 | 2116.9 | 4706 | 2118.9 | 4608 | 2115.2 | 4764 | v1.0-snapshot baseline; Qwen3-ASR stopped; clean OmniVoice container; Windows desktop consumers present |
| 28.10.2026 17:43:10 - 1.1-snapshot | NVIDIA GeForce RTX 5070 Ti | 5 | 2107.6 | 4822 | 2116.7 | 4831 | 2120.1 | 4728 | 2115.1 | 4864 | PR283 post-fix; source-mounted 3481d51 plus local inference guard; Torch2.10-cu128 Transformers5.17; remote ASR; Windows desktop present; warmed short-reference workload, not cold15s peak test |
