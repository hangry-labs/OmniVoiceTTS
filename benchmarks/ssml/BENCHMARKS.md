# ssml_h_reliability

End-to-end dialogue-completion benchmark for SSML-H dynamic voices. It generates the exact two-character sample included in the browser UI, transcribes each WAV through the local Qwen3-ASR service, and requires the normalized transcript to match `Are we ready? Yes, all preparations are complete.` exactly. Every TTS WAV is generated and staged before the separate ASR transcription phase begins.

The workload uses one full TTS-to-ASR warmup followed by deterministic fixed seeds. Seed `2717518076` is retained as the first measured case because it reproducibly omitted Elisabeth's final sentence when an omitted `h:sample` was derived from dialogue text. A pre-fix diagnostic probe completed 7 of 8 calls (87.5%); the separately captured failure artifact ended at `Yes, everything.`. Current behavior uses one fixed internal reference sentence whenever `h:sample` is omitted, so dialogue content never becomes voice-training material. The browser sample keeps Elisabeth's complete reply inside one prosody scope to avoid splitting a short turn into separate model generations.

This is a semantic completion regression benchmark, not a voice-quality score. ASR can occasionally make recognition errors, so every failed row must be inspected using the detailed transcript and audio hash in `runs.json` and the per-run evidence in `DETAILS.md`.

| Run | Hardware | Calls | Policy | Passed | Completion | Total seconds | Avg TTS | Avg ASR | Min bytes | Max bytes | ASR model |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 06.10.2026 13:48:01 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | dialogue-derived combined sample | 20 | 100.0% | 108.361 | 5.349 | 0.069 | 143046 | 165598 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 14:05:42 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample, no unit retry | 10 | 50.0% | 123.303 | 6.094 | 0.071 | 80892 | 164168 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 14:12:34 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample + initial unit retry | 20 | 100.0% | 136.181 | 6.748 | 0.061 | 143968 | 192170 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 14:16:06 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample + bounded short-unit retry | 20 | 100.0% | 145.361 | 7.207 | 0.060 | 135964 | 164168 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 14:30:27 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample + original contiguous prosody wording + bounded retry | 19 | 95.0% | 107.643 | 5.306 | 0.075 | 150860 | 174512 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 14:35:22 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample + stable contiguous prosody turn + bounded retry | 20 | 100.0% | 93.472 | 4.591 | 0.082 | 162474 | 182158 | Qwen/Qwen3-ASR-0.6B-hf |
| 06.10.2026 17:57:54 - 1.0-snapshot | NVIDIA GeForce RTX 5070 Ti | 20 | fixed internal sample + stable contiguous prosody turn + bounded retry | 20 | 100.0% | 95.708 | 4.477 | 0.073 | 162474 | 182158 | Qwen/Qwen3-ASR-0.6B-hf |
