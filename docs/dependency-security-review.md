# Dependency Security Review

Review date: 28 October 2026. This records the dependency changes prepared for the `1.1-snapshot` runtime. Published release images retain their original dependencies; deploy a newly built snapshot or subsequent release to receive these fixes.

The subsequent [code-scanning security review](code-scanning-security-review.md) addresses three normalization regex findings and documents the remaining file-path false positive. Its newer validation totals supersede the initial counts below.

## Scope And Changes

The repository had 54 open Dependabot alerts covering 29 distinct advisories. Many alerts repeat across `pyproject.toml`, `requirements.txt`, and `uv.lock`. The changes address 48 of those alert records, covering 27 advisories, while preserving Python 3.13 and CUDA 12.8.

| Dependency | Updated version | Alert records addressed | Coverage |
|---|---|---|---|
| `python-multipart` | `0.0.32` | #60-67, #137-140 | Upload/form parser denial of service and parameter smuggling |
| `starlette` | `1.10.0` in `uv.lock`; `1.7.0` in Docker requirements | #50, #72-75 | Host/path reconstruction, form limits, Windows static paths, method dispatch |
| `anyio` | `4.14.2` in `uv.lock`; `4.15.1` in Docker requirements | #122, #124 | TLS hostname validation and process-worker deadlock |
| `certifi` | `2026.10.23` | #152-153 | Removal of compromised CA trust roots |
| `filelock` | `4.2.4` | #145-147, #149-151 | Windows lock-file and SQLite side-file handling |
| `setuptools` | `84.2.1` | #114, #144, #148 | Legacy installation path escape and source-archive exclusions |
| `fsspec` | `2026.9.0` | #141 | Reference-filesystem template injection |
| `msgpack` | `1.2.4` in `uv.lock`; `1.2.3` in Docker requirements | #76, #154 | Unpacker errors and C-extension memory leaks |
| `urllib3` | `2.8.0` | #132-134 | Response memory bounds, deflate streaming, proxy TLS |
| `transformers` | `5.17.0` | #115-117, #125, #130, #135 | Chat-template path traversal and custom-generation consent ordering |
| `torch` / `torchaudio` | `2.10.0+cu128` on Linux/Windows | #51-54, #56, #58 | PyTorch `unpack_sequence` and `lstm_cell` memory corruption |

Both lockfiles were refreshed using targeted package upgrades. Their transitive versions can differ because the project lock covers multiple platforms and Docker requirements target Linux; every version listed above meets the applicable advisory's patched floor.

## Verify Behavior As Well As Version Ranges

The [Transformers custom-generation advisory](https://github.com/advisories/GHSA-x9r9-c232-4q39) lists affected versions only through `5.8.1` and does not identify a patched release. Inspection of published wheels found the unsafe download-before-consent order still present through `5.16.0`. The selected `5.17.0` wheel contains the consent-before-download fix. An offline regression test verifies that rejecting remote code prevents both download and code loading.

A second regression test verifies that malformed `Host` values cannot replace the real path when Starlette constructs a request URL. API, upload, MCP, and standalone-UI tests exercise the updated shared web stack.

Live streaming validation also exposed a request-context lifetime issue: sync stream chunks can resume in different worker contexts, so resetting a token created before an earlier yield can fail when the response finishes. Plain-text and SSML streams now advance and close their generators within one private request context. Regression tests cover changing worker contexts, cleanup, and preserving the caller's context.

## Remaining Advisories

### Accelerate Checkpoint Loading

[GHSA-4j2p-28q2-5m79](https://github.com/advisories/GHSA-4j2p-28q2-5m79), alerts #118-120, concerns unsafe shard paths in `load_checkpoint_in_model` and `load_checkpoint_and_dispatch`. The installed `accelerate==1.13.0` remains affected. The latest published `1.15.0` wheel was also inspected and still joins checkpoint-supplied paths without the proposed containment check, so a version bump would not establish a fix.

OmniVoiceTTS does not call these checkpoint-loading functions or accept model/checkpoint uploads through its speech APIs. Its standard model is pinned to a reviewed revision and loaded through Transformers. This limits exposure in the supported deployment, but the dependency advisory remains unresolved. Treat operator-selected custom checkpoints and code using Accelerate directly as separate trust decisions. Reassess when a verified upstream fix is available.

### PyTorch TorchScript

[GHSA-rrmf-rvhw-rf47](https://github.com/advisories/GHSA-rrmf-rvhw-rf47), alerts #84-86, affects `torch.jit.script` through `2.12.1`; the advisory identifies `2.13.0` as patched. The CUDA 12.8 index does not provide that release. Moving to its CUDA 13 distribution would change the driver/runtime support baseline, so this review retains the matching CUDA 12.8 Torch/torchaudio pair.

OmniVoiceTTS does not accept Python/TorchScript programs from speech requests and does not directly call `torch.jit.script`. The remaining advisory is tracked rather than dismissed. Revisit it with a separately validated CUDA/PyTorch platform upgrade.

### Supplemental Exported-Program Finding

A separate audit of Torch's public version also reports [CVE-2026-4538](https://github.com/pytorch/pytorch/pull/176791), concerning deserialization of untrusted `.pt2` programs through `torch.export.load`. This was absent from the 54 Dependabot records reviewed above; the advisory database covers the previous runtime version as well as `2.10.0` and identifies no patched version. OmniVoiceTTS does not call `torch.export.load` or accept exported programs through its APIs. Keep this finding tracked alongside the TorchScript advisory; do not treat the CUDA-wheel audit skip as a clean result.

## Verification And Follow-up

Use `task validate` for the local test, lockfile, and Dockerfile checks. Verify the actual runtime dependency set in Docker, its compliance bundle, and real generation after rebuilding the dependency layer. Full and tiny images share that layer.

Validation completed for this review:

- `task validate`: 163 tests collected, 162 passed, and one Windows symlink-privilege skip; dependency-lock and Dockerfile checks passed.
- `task codeql`: no unsuppressed findings; four existing reviewed suppressions retained.
- One rebuilt dependency/runtime image passed `pip check` and compliance verification: 39 checksums, two corresponding-source archives, five checked package versions, and 14 NVIDIA license files.
- Live RTX 5070 Ti checks covered random and designed voices, OpenAI-compatible cloning and cached reuse, native and SSML-H progressive streams, multipart cloning, and reference cloning without a supplied transcript. Compact and advanced MCP discovery, generation, and audio download passed.
- CPU random generation and multipart cloning passed. Remote Qwen3-ASR transcripts matched the requested text for all 11 retained smoke audio files, including both complete SSML-H dialogues. These short checks verify integration; they are not new performance benchmark baselines.

The final streaming change was validated through the source-mounted local deployment using the rebuilt dependency image.

Dependency scanners can skip local-version CUDA wheels such as `torch==2.10.0+cu128`; compare their public version with GitHub's advisory range explicitly. An audit reporting no Torch finding is not evidence that the TorchScript advisory is fixed.

Dependabot will re-evaluate the changed manifests after they reach the default branch. No alerts were manually dismissed as part of this review. Six alert records covering the two remaining advisories are expected to remain open.
