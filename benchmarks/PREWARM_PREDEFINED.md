# warm_predefined

Warmup calls for the predefined cached voice path. These calls are intended to load the model and populate the stored-voice clone prompt cache before `predefined_voice` measurements start.

Baseline hardware: NVIDIA GeForce RTX 5060 Ti.

| Run | Calls | Total seconds | Avg seconds | Min | Max | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| 14.05.2026 23:24:54 - 0.2.1-snapshot | 10 | 10.777 | 1.078 | 0.962 | 1.669 | 976760 |
| 02.07.2026 22:06:25 - 0.2.1-snapshot | 10 | 13.936 | 1.394 | 1.042 | 3.629 | 980120 |
| 02.07.2026 22:29:04 - 0.2.1-snapshot | 10 | 13.39 | 1.339 | 1.023 | 3.312 | 980120 |
