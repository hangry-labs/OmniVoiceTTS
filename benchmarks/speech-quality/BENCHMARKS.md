# OmniVoiceTTS Speech Quality Benchmarks

Append one row per official multilingual TTS-to-ASR benchmark run.

> **Interpretation:** These results are provisional comparative regression signals, not measurements of absolute TTS accuracy. They track correlated movement between like-for-like runs using one fixed English clone voice and an imperfect ASR judge. A score change identifies audio that needs investigation and human listening; it does not independently prove a TTS improvement or degradation. Random voices, voice design, multiple speakers, and native-language references are not covered by this track.

The fixed workload uses `examples/assets/manifest.json`: one localized clone example per judge-supported language warms both services, then the first two random sentences from each selected language are generated five times. The runner obtains the supported language set from the locked Qwen3-ASR service before building the workload; unsupported judge languages are excluded from generation and every aggregate. Every measured WAV uses the same baked clone reference, known reference transcript, decoding settings, and sentence-specific seed. All TTS WAVs are generated first and staged temporarily; only after generation finishes does the local Qwen3-ASR service transcribe them with deterministic decoding. Generation and transcription are never interleaved.

Exact matching ignores Unicode compatibility differences, case, punctuation, and whitespace. Similarity is a normalized character-sequence comparison. Repeat consistency requires all five normalized ASR transcripts for a sentence to be identical. These are regression signals from a fixed ASR judge, not objective speech-quality or intelligibility scores.

Timing covers measured HTTP requests only. TTS real-time factor is generation time divided by produced audio duration, so lower is better. Before warmup the runner clears unused TTS allocator blocks and resets TTS PyTorch peak counters without unloading models or clone prompts. Qwen is fully warmed before the ASR baseline snapshot and receives a final keepalive transcription immediately before the endpoint snapshot. The TTS process peak remains useful, but whole-device VRAM here includes resident Qwen, Windows, and other GPU consumers and is diagnostic only. Use the dedicated GPU-memory suite with Qwen stopped for authoritative TTS VRAM comparisons.

| Run | ASR model | GPU | Languages | Calls | Exact | Repeat consistency | Mean similarity | Total TTS | Avg TTS | P95 TTS | TTS RTF | Avg ASR | TTS peak allocated MiB | Peak device VRAM MiB | Errors |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 06.10.2026 17:52:00 - 1.0-snapshot | Qwen/Qwen3-ASR-0.6B-hf | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | 20 | 200 | 62.50% | 95.00% | 88.46% | 260.553 | 1.303 | 1.417 | 0.3020 | 0.101 | 3714.5 | 10354 | 0 |
| 06.10.2026 18:27:34 - 1.0-snapshot | Qwen/Qwen3-ASR-0.6B-hf | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | 18 | 180 | 69.44% | 94.44% | 98.29% | 235.685 | 1.309 | 1.421 | 0.3026 | 0.096 | 3379.2 | 9700 | 0 |
| 06.10.2026 18:40:59 - 1.0-snapshot | Qwen/Qwen3-ASR-0.6B-hf | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | 18 | 180 | 69.44% | 100.00% | 98.28% | 229.603 | 1.276 | 1.370 | 0.2948 | 0.091 | 2167.3 | 8829 | 0 |
<!-- benchmark-rows:end -->

The initial 20-language row predates judge-supported workload filtering and includes Bengali and Urdu. It is retained as historical evidence but is not part of the canonical comparison below.

## Preliminary Comparison Ranges

These are investigation thresholds, not release pass/fail rules. They are based on the two canonical 18-language runs of the same 180 calls and should be widened only when additional clean baselines provide evidence.

| Signal | Canonical run 1 | Canonical run 2 | Preliminary healthy range |
|---|---:|---:|---|
| Request errors | 0 | 0 | Must remain 0 |
| Exact transcripts | 69.44% | 69.44% | Investigate any decline |
| Repeat-consistent cases | 94.44% | 100.00% | 94.44-100%; investigate below 34/36 consistent cases |
| Mean similarity | 98.29% | 98.28% | Investigate a decline greater than 0.25 points |
| Average TTS | 1.309s | 1.276s | Within 5% on an otherwise idle matching host |
| P95 TTS | 1.421s | 1.370s | Within 5% on an otherwise idle matching host |
| TTS RTF | 0.3026 | 0.2948 | Within 5% on an otherwise idle matching host |
| Average ASR | 0.096s | 0.091s | Diagnostic only; within 10% is normal |
| ASR endpoint VRAM drift | 0 MiB | 0 MiB | At most 64 MiB after final keepalive |

All 180 audio hashes matched across the canonical runs. Qwen produced the same normalized transcript for 178/180 identical WAVs; `standard_arabic_random_01_r1` and `polish_random_01_r1` varied. This establishes audio hashes as the stronger TTS-determinism signal and explains the observed repeat-consistency range. With unchanged code, models, seeds, and runtime, any audio-hash change should be investigated. Intentional model or generation changes are expected to establish a new baseline rather than preserve hashes.
