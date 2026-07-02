# predefined_voice

A predefined voice is selected by name through the OpenAI-compatible API. This covers built-in clone aliases and voices saved through the UI Add Voice tab. Voice-clone prompt preparation is cached after warmup, so repeated sentence-level calls should avoid re-tokenizing the reference audio.

Baseline hardware: NVIDIA GeForce RTX 5060 Ti.

| Run | Calls | Total seconds | Avg seconds | Min | Max | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| 14.05.2026 23:24:54 - 0.2.1-snapshot | 100 | 103.582 | 1.036 | 0.915 | 1.695 | 8754800 |
| 02.07.2026 22:06:25 - 0.2.1-snapshot | 100 | 118.604 | 1.186 | 0.989 | 2.212 | 8762960 |
| 02.07.2026 22:29:04 - 0.2.1-snapshot | 100 | 111.136 | 1.111 | 0.974 | 1.431 | 8762960 |
