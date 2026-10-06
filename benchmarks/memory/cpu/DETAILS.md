# CPU Memory Benchmark Details

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
