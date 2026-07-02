# cpu_memory

CPU-only Docker memory-limit benchmark for OpenAI-compatible speech requests.

Each run starts one CPU container per scenario and Docker memory limit, then records the lowest passing limit as a conservative whole-GB RAM recommendation. The recommendation adds 512 MiB headroom to the lowest passing limit before rounding up to whole GB. The detailed pass/fail attempts are stored in `cpu-memory.json`.

The benchmark text is intentionally one realistic short request, around 100-200 characters. Results are not a guarantee for long text, concurrent requests, larger outputs, or different host memory behavior.

Scenario shortcuts:

- `RV`: Random/no-prompt voice: no reference audio, no design instructions, no stored profile.
- `DV`: Voice design/generate voice: explicit design instructions, no reference audio.
- `CR-NT`: Direct clone reference without transcript. This may lazy-load ASR.
- `CR-TX`: Direct clone reference with transcript.
- `SV-NT`: Stored voice profile without transcript. This may lazy-load ASR.
- `SV-TX`: Stored voice profile with transcript.

| Date | Text chars | Version | RV | DV | CR-NT | CR-TX | SV-NT | SV-TX |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 02.07.2026 21:29:38 - 0.2.1-snapshot | 140 | 0.2.1-snapshot | 2 GB | 2 GB | 6 GB | 2 GB | 7 GB | 3 GB |
