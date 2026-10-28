# CPU Memory Benchmark Details

## CPU Precision Opt-In Validation: 28 October 2026

The FP32 option changes CPU TTS weight precision only. CPU TTS now defaults to FP16; the earlier memory-limit matrix used FP32 and remains historical evidence, not a new FP16 minimum-memory measurement.

A bounded live check used the existing Docker runtime, the saved `benchmark_original_clone` profile with its known reference transcript, native CPU execution through `/v1/audio/speech`, seed `4242`, and 16 generation steps. The text was `CPU speech is ready for this test.` One cold HTTP request was made per mode; changing the preference unloaded the CPU model and prompt cache first, while the CUDA model remained loaded in FP16.

| CPU TTS weights | Cold request seconds | Output seconds | Expected words recovered by remote ASR |
|---|---:|---:|---|
| FP16 (default) | 51.824 | 2.09 | Yes |
| FP32 (opt-in) | 15.927 | 2.08 | Yes |

This single short-request comparison is functional validation, not a repeated speed benchmark, universal speedup claim, or memory-limit recommendation. Both outputs contained the intended words; numerical precision changes may produce different waveforms. FP32 uses more storage for the affected TTS weights, but total process RAM need not double. No new full CPU memory matrix was run for this feature.

The installed single-file CPU CLI also generated a valid WAV at its default FP16 setting, and the installed batch CLI generated two valid WAVs with `--cpu-fp32`; all three transcripts matched their requested words. System UI persistence was checked across a container restart, and the local preference was restored to FP16 afterward. GPU precision and separately loaded tokenizer/ASR precision are unchanged.

Each scenario starts in a fresh CPU-only Docker container for every configured memory limit. Docker memory and swap limits are identical, preventing host swap from hiding an out-of-memory condition. The runner records startup failures, request failures, OOM state, peak container memory, request duration, and the first passing limit.

The published recommendation adds 512 MiB to the first passing limit and rounds up to a whole GiB. This is deliberate operational headroom, not a guarantee for longer text or concurrent requests. Direct and stored clone cases without a transcript may lazy-load ASR and therefore require substantially more memory.

Raw historical attempts are retained in `runs.json`. New official runs append a detailed attempt table below.

## 06.10.2026 18:00:55 - 1.0-snapshot

- Image: `omnivoicetts:test`
- Docker: `29.6.2` on `Docker Desktop`
- Benchmark text: This CPU memory benchmark uses a realistic two-sentence request to estimate the RAM needed for local text to speech with common voice modes.
- Text length: `140` characters
- Comment: v1.0-snapshot baseline; isolated CPU containers; GPU services stopped

| Scenario | Limit | Result | Peak MiB | Seconds | OOM killed | Notes |
|---|---:|---|---:|---:|---|---|
| RV | 1536m | pass | 853.2 | 86.084 | False | status load_asr=False resolved_device=cpu |
| RV | 2048m | pass | 1732.6 | 36.910 | False | status load_asr=False resolved_device=cpu |
| **RV result** | **1536m** | **recommend 2 GB** |  | | | |
| DV | 1536m | pass | 855.0 | 35.556 | False | status load_asr=False resolved_device=cpu |
| DV | 2048m | pass | 822.5 | 35.712 | False | status load_asr=False resolved_device=cpu |
| **DV result** | **1536m** | **recommend 2 GB** |  | | | |
| CR-NT | 1536m | request-failed | 600.5 | 1.852 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 2048m | request-failed | 601.7 | 2.083 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 2560m | request-failed | 601.8 | 2.267 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 3072m | request-failed | 601.7 | 2.312 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 4096m | request-failed | 3822.6 | 11.626 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 5120m | pass | 4117.5 | 68.507 | False | status load_asr=False resolved_device=cpu |
| CR-NT | 6144m | pass | 4146.2 | 71.107 | False | status load_asr=False resolved_device=cpu |
| **CR-NT result** | **5120m** | **recommend 6 GB** |  | | | |
| CR-TX | 1536m | pass | 1012.0 | 52.246 | False | status load_asr=False resolved_device=cpu |
| CR-TX | 2048m | pass | 976.5 | 52.034 | False | status load_asr=False resolved_device=cpu |
| **CR-TX result** | **1536m** | **recommend 2 GB** |  | | | |
| SV-NT | 1536m | request-failed | 176.3 | 1.674 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 2048m | request-failed | 873.0 | 1.803 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 2560m | request-failed | 0.0 | 1.782 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 3072m | request-failed | 601.5 | 1.841 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 4096m | request-failed | 3833.9 | 11.452 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 5120m | request-failed | 4106.2 | 15.135 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 6144m | pass | 5205.0 | 66.334 | False | status load_asr=False resolved_device=cpu |
| SV-NT | 7168m | pass | 4190.2 | 66.796 | False | status load_asr=False resolved_device=cpu |
| **SV-NT result** | **6144m** | **recommend 7 GB** |  | | | |
| SV-TX | 1536m | request-failed | 600.9 | 1.886 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-TX | 2048m | request-failed | 626.7 | 2.404 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-TX | 2560m | pass | 2047.0 | 53.915 | False | status load_asr=False resolved_device=cpu |
| SV-TX | 3072m | pass | 2019.3 | 53.726 | False | status load_asr=False resolved_device=cpu |
| **SV-TX result** | **2560m** | **recommend 3 GB** |  | | | |

## 28.10.2026 18:03:34 - 1.1-snapshot

- Image: `omnivoicetts:security-check`
- Docker: `29.9.2` on `Docker Desktop`
- Benchmark text: This CPU memory benchmark uses a realistic two-sentence request to estimate the RAM needed for local text to speech with common voice modes.
- Text length: `140` characters
- Comment: PR283 post-fix; source3481d51 plus guard; Torch2.10-cu128 Transformers5.17; existing tiny runtime image1f806c3d; canonical six-scenario140-char matrix; read-only cached models; isolated profiles/settings; no concurrent local inference

| Scenario | Limit | Result | Peak MiB | Seconds | OOM killed | Notes |
|---|---:|---|---:|---:|---|---|
| RV | 1536m | pass | 883.2 | 34.092 | False | status load_asr=False resolved_device=cpu |
| RV | 2048m | pass | 869.6 | 34.592 | False | status load_asr=False resolved_device=cpu |
| **RV result** | **1536m** | **recommend 2 GB** |  | | | |
| DV | 1536m | pass | 874.0 | 37.898 | False | status load_asr=False resolved_device=cpu |
| DV | 2048m | pass | 948.8 | 34.118 | False | status load_asr=False resolved_device=cpu |
| **DV result** | **1536m** | **recommend 2 GB** |  | | | |
| CR-NT | 1536m | request-failed | 917.6 | 1.653 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 2048m | request-failed | 1220.6 | 1.781 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 2560m | request-failed | 1812.5 | 1.905 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 3072m | request-failed | 802.9 | 1.892 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 4096m | request-failed | 3881.0 | 11.664 | True | RemoteDisconnected: Remote end closed connection without response |
| CR-NT | 5120m | pass | 4156.4 | 65.798 | False | status load_asr=False resolved_device=cpu |
| CR-NT | 6144m | pass | 4168.7 | 64.736 | False | status load_asr=False resolved_device=cpu |
| **CR-NT result** | **5120m** | **recommend 6 GB** |  | | | |
| CR-TX | 1536m | pass | 1047.6 | 52.302 | False | status load_asr=False resolved_device=cpu |
| CR-TX | 2048m | pass | 1020.0 | 51.013 | False | status load_asr=False resolved_device=cpu |
| **CR-TX result** | **1536m** | **recommend 2 GB** |  | | | |
| SV-NT | 1536m | request-failed | 1188.9 | 1.770 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 2048m | request-failed | 1225.7 | 1.754 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 2560m | request-failed | 0.0 | 1.723 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 3072m | request-failed | 638.3 | 2.149 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 4096m | request-failed | 3881.0 | 11.131 | True | RemoteDisconnected: Remote end closed connection without response |
| SV-NT | 5120m | pass | 4167.7 | 65.289 | False | status load_asr=False resolved_device=cpu |
| SV-NT | 6144m | pass | 4147.2 | 64.567 | False | status load_asr=False resolved_device=cpu |
| **SV-NT result** | **5120m** | **recommend 6 GB** |  | | | |
| SV-TX | 1536m | pass | 1019.0 | 55.259 | False | status load_asr=False resolved_device=cpu |
| SV-TX | 2048m | pass | 1028.1 | 52.814 | False | status load_asr=False resolved_device=cpu |
| **SV-TX result** | **1536m** | **recommend 2 GB** |  | | | |
