# GPU Memory Benchmarks

Append one row per official warmed GPU-memory benchmark. Each scenario is prewarmed independently, then unused allocator blocks are cleared and PyTorch peak counters are reset without unloading model weights or cached clone prompts.

`Process peak` is PyTorch's maximum allocated memory for the TTS process. `Device peak` is sampled through `nvidia-smi` and includes every process on the selected GPU. Official comparisons require the same image, settings, workload, and an otherwise idle GPU.

Scenario shortcuts: `RV` random voice, `DV` designed voice, `CR` uncached direct clone with transcript, and `CC` cached clone with transcript.

| Run | GPU | Calls | RV process peak | RV device peak | DV process peak | DV device peak | CR process peak | CR device peak | CC process peak | CC device peak | Comment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 06.10.2026 17:43:51 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 5 | 2116.9 | 4706 | 2116.9 | 4706 | 2118.9 | 4608 | 2115.2 | 4764 | v1.0-snapshot baseline; Qwen3-ASR stopped; clean OmniVoice container; Windows desktop consumers present |
