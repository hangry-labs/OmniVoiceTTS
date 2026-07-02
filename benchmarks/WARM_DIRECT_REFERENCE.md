# direct_reference_audio

The caller sends direct `ref_audio` with each request instead of selecting a saved voice. This is the original ad hoc voice-cloning path and intentionally does not use the stored-voice cache.

Baseline hardware: NVIDIA GeForce RTX 5060 Ti.

| Run | Calls | Total seconds | Avg seconds | Min | Max | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| 14.05.2026 23:24:54 - 0.2.1-snapshot | 100 | 149.772 | 1.498 | 1.28 | 2.09 | 8598320 |
| 02.07.2026 22:06:25 - 0.2.1-snapshot | 100 | 168.265 | 1.683 | 1.265 | 3.057 | 8623760 |
| 02.07.2026 22:29:04 - 0.2.1-snapshot | 100 | 138.353 | 1.384 | 1.265 | 1.674 | 8623760 |
