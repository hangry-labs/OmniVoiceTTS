# Code-Scanning Security Review

Review date: 28 October 2026. This supplements the [dependency security review](dependency-security-review.md) with source-level findings from GitHub CodeQL.

## Findings

GitHub's latest Python analysis of commit `b1d7b012e05ee29edc56b03a3395f8b989dcc5cc` reported four open alerts. The local scan found the same four, but previously accepted them through reviewed source suppressions. A local result with no unsuppressed findings therefore did not mean GitHub had no open alerts.

| Alert | Location | Assessment and resolution |
|---|---|---|
| [#21](https://github.com/hangry-labs/OmniVoiceTTS/security/code-scanning/21) | English structured-text normalization | Fixed ambiguous numeric/identifier repetition and repeated email matching attempts. Added possessive quantifiers and token boundaries that prevent restarting inside malformed tokens. |
| [#22](https://github.com/hangry-labs/OmniVoiceTTS/security/code-scanning/22) | Malayalam fraction recognition | Fixed backtracking over digit sequences with possessive quantifiers. Supported fraction behavior remains covered by the existing normalization tests. |
| [#23](https://github.com/hangry-labs/OmniVoiceTTS/security/code-scanning/23) | Vietnamese identifier recognition | Replaced overlapping optional whitespace runs with one unambiguous separator structure. Optional `là` and colon separators remain supported. |
| [#24](https://github.com/hangry-labs/OmniVoiceTTS/security/code-scanning/24) | `safe_existing_file_path` | Reviewed false positive at the file-existence check: canonical containment validation already precedes it. Retained the documented local suppression and expanded the boundary tests. |

The three regex suppressions were removed. The existing 20,000-character normalization limit remains in force, but that limit alone does not justify accepting costly backtracking. A targeted probe of an identifier prefix followed by spaces consumed about four CPU seconds at the maximum input length before the fix. The updated pattern completed below the single-run CPU timer resolution on the test host. These are targeted security regression probes, not inference performance benchmarks.

## File-Path Finding

The helper expands and canonicalizes both the requested path and each configured safe root with `realpath`. It requires their `commonpath` to equal the complete root before checking the file or returning the path. This rejects parent traversal, sibling directories whose names merely share the root's prefix, and symlinks escaping the allowed tree. The existence check highlighted by CodeQL runs only after those checks.

The tests cover ordinary allowed files, missing files, outside files, `..` traversal, prefix collisions, escaping symlinks, and valid in-root symlinks. All seven pass in Linux Docker. Two symlink cases skip on the Windows host because creating symlinks requires unavailable privileges.

The retained assumption is that configured safe roots and their directory structure are controlled by the operator. This validation is not a defense against a hostile local process changing filesystem links between validation and a later open.

Suggested rationale if the maintained GitHub alert is dismissed as a false positive:

> The reported `is_file()` call follows canonical `realpath` resolution and an explicit `commonpath` equality check against configured allowed roots. Tests reject outside paths, parent traversal, same-prefix sibling directories, and symlinks escaping the allowed tree, while accepting ordinary files and in-root symlinks. All seven boundary tests pass in Linux Docker. The finding does not account for this containment validation.

## Validation And Publication

- `task validate`: 172 tests collected, 169 passed, three Windows symlink-privilege skips; dependency-lock and Dockerfile checks passed.
- `task codeql`: the raw SARIF contains only the reviewed path finding. None of the three regex findings remain, and none are suppressed.
- Linux Docker: all 29 focused normalization and file-path tests passed, including both symlink cases.
- Regression coverage checks the maximum-length adversarial inputs within a CPU budget, expected normalization output, and Vietnamese identifier separator variants.
- The refreshed local API passed English, Malayalam, and Vietnamese normalization probes and the maximum-length Vietnamese whitespace case. Warmed GPU generation produced byte-identical WAV output for normalized numeric text and its explicit spoken equivalent with the same seed.

No GitHub alerts were manually dismissed. Once these source changes are published and GitHub scans them, alerts #21-23 should close. Alert #24 remains an explicitly documented false positive unless it is dismissed with the reviewed rationale.

## Compatibility And Speech Quality

The CodeQL changes leave model weights, voice conditioning, attention, sampling parameters, and audio processing unchanged. They affect optional structured-text normalization, which remains disabled by default through `normalize_text=false`.

A differential comparison against pre-hardening revision `b1d7b01` covered 1,792 cases:

| Input set | Cases | Comparison |
|---|---:|---|
| All manifest text entries, including localized introductions | 300 | Identical normalized text and metadata |
| English email addresses with varied punctuation and local/domain forms | 1,200 | Identical |
| English identifiers, dates, and phone numbers | 44 | Identical |
| Malayalam structured values | 60 | Identical |
| Vietnamese structured values and identifier contexts | 84 | Identical |
| English numeric and currency values | 96 | 74 identical; 22 correct complete amounts, decimals, or explicit signs previously mishandled |
| Additional boundary/malformed-token cases | 8 | Four identifier-prefix cases retain their old output; four malformed cases are preserved instead of partially rewritten |

The broader comparison caught an overly strict identifier boundary in the initial hardening and exposed existing sentence-final currency fallback errors. The final recognizers preserve hyphen-prefixed identifiers, including after non-ASCII words, support Western and Indian comma grouping, preserve explicit amount signs, and recognize complete values before sentence-ending punctuation. For example, `Pay $1,234.56.` now becomes `Pay one thousand, two hundred and thirty four dollars and fifty six cents.` rather than partially verbalizing the amount.

After model warm-up, GPU generation for both that amount and `-AB12` produced byte-identical WAVs to requests containing their explicit expected spoken forms with normalization disabled and the same fixed seed. This verifies the text-to-inference handoff for those cases.

These checks found no voice-quality degradation attributable to the CodeQL changes. They cover the documented sample set and targeted boundary cases, not every possible input. The full ASR-based speech-quality benchmark was not rerun as part of this targeted review.
