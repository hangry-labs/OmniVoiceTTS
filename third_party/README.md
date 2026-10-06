# Docker Compliance Bundle

Published OmniVoiceTTS Docker images contain `/app/third_party` so recipients
can inspect model agreements, dependency licenses, package provenance, and
corresponding source without relying only on mutable external pages.

The bundle is assembled from checksum-pinned primary sources during the image
build. It includes model-license material, exact LGPL source archives,
installed package licenses, a complete Python distribution inventory, Debian
source coordinates, the relevant build inputs, and an offline verifier.

Run:

```bash
python /app/third_party/build/verify_compliance_bundle.py /app/third_party
```

The project-owned source remains Apache-2.0. The model-powered server and
Docker images are mixed-license distributions. Read `/app/NOTICE`,
`/app/THIRD_PARTY_NOTICES.md`, and the complete files in this directory before
redistributing or deploying the image. These records are factual provenance,
not legal advice.
