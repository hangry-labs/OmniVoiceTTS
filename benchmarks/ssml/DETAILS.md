# SSML-H Reliability Details

This benchmark repeatedly generates the fixed two-character browser example and transcribes each result with the locked local Qwen3-ASR service. It is designed to detect missing dialogue turns and truncated final speech, not to assign a subjective voice-quality score. Generation and transcription are separate phases: all WAVs are staged first, then Qwen is warmed once and the measured files are transcribed.

The first deterministic seed is a known pre-fix failure case. Every measured call records its transcript, timing, size, response seed, and audio hash in `runs.json`. New official runs append their complete per-call evidence below so an ASR mismatch can be distinguished from a TTS omission.

## 06.10.2026 17:57:54 - 1.0-snapshot

- Hardware: `NVIDIA GeForce RTX 5070 Ti`
- Policy: fixed internal sample + stable contiguous prosody turn + bounded retry
- Expected transcript: `Are we ready? Yes, all preparations are complete.`
- Warmup transcript: `Are we ready? Yes, all preparations are complete.`
- Comment: v1.0-snapshot baseline; staged TTS phase followed by warmed Qwen3-ASR phase; RTX 5070 Ti

| Call | Seed | Result | TTS seconds | ASR seconds | Audio seconds | Bytes | Transcript | SHA-256 |
|---:|---:|---|---:|---:|---:|---:|---|---|
| 1 | 2717518076 | pass | 4.646 | 0.066 | 3.510 | 168544 | Are we ready? Yes, all preparations are complete. | `b607e3a8da615718405507ee717c710e84b410313ee92e428c7194d2d0bb33d8` |
| 2 | 2717518077 | pass | 4.482 | 0.086 | 3.527 | 169362 | Are we ready? Yes, all preparations are complete. | `af8b43a517ab412ecaadca32f10607ed8dbc6ed97b7a9ed9de570855d7430f1e` |
| 3 | 2717518078 | pass | 4.596 | 0.064 | 3.561 | 170976 | Are we ready? Yes, all preparations are complete. | `b49a2ef78dff700c927fb8b3bf413e9a70c2486d3b1ec6f0f10681b0d337353a` |
| 4 | 412095174 | pass | 4.442 | 0.088 | 3.476 | 166890 | Are we ready? Yes, all preparations are complete. | `60924812d93c8974720207d5b21e2895d32fbe8c40fbb71810860e6bd9fcc7c3` |
| 5 | 3888510638 | pass | 4.466 | 0.065 | 3.794 | 182158 | Are we ready? Yes, all preparations are complete. | `4d2563e485854e97ae338500c8a327a9d0566f1c834ec66d25efde9b0591c674` |
| 6 | 1485887814 | pass | 4.498 | 0.070 | 3.565 | 171146 | Are we ready? Yes, all preparations are complete. | `231811b35f9f70cb781b1f82ed4b887b8e67f1cf39ad57df2457dbe5a7bc8c2b` |
| 7 | 2163181999 | pass | 4.295 | 0.076 | 3.541 | 170000 | Are we ready? Yes, all preparations are complete. | `877d1854ad03ebad82d64d56868f9628cc610f99fdf043809f1d1b65239aa58f` |
| 8 | 3432834366 | pass | 4.517 | 0.065 | 3.714 | 178332 | Are we ready? Yes, all preparations are complete. | `33818480a7d6e88d51bddd21a5c7ad94d23f82bf40e15d83bdbab968d7833f0e` |
| 9 | 1257281928 | pass | 4.363 | 0.077 | 3.678 | 176566 | Are we ready? Yes, all preparations are complete. | `c75871d6c37e9f63a75c256292881f342d55f862f3f3fbb5bf5b4060d6e3c754` |
| 10 | 3509819213 | pass | 4.558 | 0.065 | 3.568 | 171302 | Are we ready? Yes, all preparations are complete. | `c96d704f67dfde320d30247237441f61c04cbc0eca651e5b139111cc9d0e3811` |
| 11 | 992516492 | pass | 4.338 | 0.075 | 3.762 | 180610 | Are we ready? Yes, all preparations are complete. | `a60a42bf736da1fbbe3d72f9c1a9928b4b658bd895407ea20443a70586ee51a4` |
| 12 | 2908409029 | pass | 4.700 | 0.082 | 3.680 | 176688 | Are we ready? Yes, all preparations are complete. | `77b7b4afaec65a65c69a351b9c3d5bb8f0912f5b037d3ca8bd422a40ccdf4144` |
| 13 | 1816140917 | pass | 4.419 | 0.068 | 3.704 | 177824 | Are we ready? Yes, all preparations are complete. | `1d4af87a3d22ea24eab2aa35d650ecffd92900b24b03f687fb415f038a219eb5` |
| 14 | 3707527105 | pass | 4.549 | 0.094 | 3.673 | 176334 | Are we ready? Yes, all preparations are complete. | `05e2734e1bc11702044a4b0dd2197b9b4c45190d6eb418e3b80a3666ed5d4f5a` |
| 15 | 635817482 | pass | 4.504 | 0.070 | 3.749 | 179982 | Are we ready? Yes, all preparations are complete. | `8516d3d9f71e4c0473ab04047449eb7db3db9510598804588dcb791ffe559ceb` |
| 16 | 2342177711 | pass | 4.405 | 0.077 | 3.490 | 167588 | Are we ready? Yes, all preparations are complete. | `81b4f8ec2ad4207d2232046d85c6cab8285d9167f011d7da7bd3142f2a4b826c` |
| 17 | 1074398955 | pass | 4.547 | 0.066 | 3.384 | 162474 | Are we ready? Yes, all preparations are complete. | `7b3772a30fc5591449080359a284f6179dfa87fcd411a715116a9e1da4e7cb84` |
| 18 | 3146820204 | pass | 4.368 | 0.068 | 3.600 | 172858 | Are we ready? Yes, all preparations are complete. | `c659aa2a624e27e97a3c7293507da7af12c9837f9676c7c14b005fac8fb49b7b` |
| 19 | 1593680337 | pass | 4.479 | 0.069 | 3.552 | 170534 | Are we ready? Yes, all preparations are complete. | `fbeee0a1b13a00328995557f1de93b9168310871d1f008e3792396b51499ddbe` |
| 20 | 2593145086 | pass | 4.369 | 0.063 | 3.667 | 176054 | Are we ready? Yes, all preparations are complete. | `3b1f3aaa65bfe20a7dcb8f5c95b8932bbebede70b69ed81dcca0645bf79e4fcb` |
