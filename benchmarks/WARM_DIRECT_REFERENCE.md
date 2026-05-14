# direct_reference_audio

The caller sends direct `ref_audio` with each request instead of selecting a saved voice. This is the original ad hoc voice-cloning path and intentionally does not use the stored-voice cache.

Baseline hardware: NVIDIA GeForce RTX 5060 Ti.

| Run | Calls | Total seconds | Avg seconds | Min | Max | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| 14.05.2026 23:24:54 - 0.2.1-snapshot | 100 | 149.772 | 1.498 | 1.28 | 2.09 | 8598320 |
