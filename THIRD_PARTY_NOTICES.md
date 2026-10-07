# Third-Party Notices

OmniVoiceTTS includes, downloads, or depends on third-party software and model
artifacts. Each component remains subject to its own license. The Apache-2.0
license for this repository's source code does not relicense those components.

This inventory is provided for compliance and provenance. It is not legal
advice. Anyone redistributing a modified image or selecting a different model
must review the terms of the exact artifacts they distribute.

## OmniVoice Code And Model

### OmniVoice source code

- Project: [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice)
- Copyright: Xiaomi Corp., the OmniVoice authors, and contributors
- License: Apache License 2.0
- Use here: upstream model implementation and inference code, modified by
  Hangry Labs for the packaged runtime, UI, APIs, and operational tooling.

The upstream copyright headers are retained in derived source files. The root
[`NOTICE`](NOTICE) identifies the distribution and the broad classes of Hangry
Labs modifications.

### OmniVoice pretrained checkpoint

- Model: [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice)
- Default reviewed revision: `c5fdb5ccb189668d56333f77ba2629f4cd7535f4`
- Upstream license statement: `CC-BY-NC` due to training-data constraints
- Use here: the default speech-synthesis checkpoint

The upstream model card does not identify a Creative Commons version number.
This project therefore records the license exactly as upstream states it and
does not silently reinterpret it as a particular CC BY-NC version. The
noncommercial restriction applies to the pretrained model even though this
repository's source code is Apache-2.0. Hangry Labs does not grant commercial
rights to the checkpoint.

The full Docker image contains this checkpoint under `/app/baked-models` and
incrementally seeds missing or changed cache files into the persistent model
cache at startup. The merge preserves user-downloaded models. The tiny image
downloads the same pinned revision into the persistent volume on first use. A
copy of the reviewed model card is included in
`/app/third_party/licenses/omnivoice-model`.

### Higgs Audio 2 tokenizer

- Component: Higgs Audio 2 tokenizer embedded in the OmniVoice checkpoint
- Original project: [bosonai/higgs-audio-v2-tokenizer](https://huggingface.co/bosonai/higgs-audio-v2-tokenizer)
- License: Boson Higgs Audio 2 Community License Agreement, incorporating the
  Meta Llama 3 Community License Agreement
- Use here: audio encoding and decoding required by OmniVoice

The Boson agreement includes attribution, acceptable-use, redistribution, and
commercial-scale conditions. Among other terms, products or services with
more than 100,000 annual active users in the preceding calendar year require
an expanded license from Boson AI. Read the complete bundled agreements before
using or redistributing the tokenizer.

Required attribution from those agreements:

> Meta Llama 3 is licensed under the Meta Llama 3 Community License, Copyright
> © Meta Platforms, Inc. All Rights Reserved.

> Boson Higgs Audio 2 is licensed under the Boson Community License, Copyright
> © Boson AI USA, Inc. All Rights Reserved.

Prominent product attribution required by the Meta agreement:

> Built with Meta Llama 3

Prominent product attribution required by the Boson agreement:

> Built with Higgs Materials licensed from Boson AI USA, Inc., Copyright Boson
> AI USA, Inc., All Rights Reserved and Meta Llama 3 licensed under the Meta
> Llama 3 Community License, Copyright Meta Platforms, Inc., All Right Reserved

Exact copies are bundled at:

- `/app/third_party/licenses/boson-higgs-audio-2/LICENSE`
- `/app/third_party/licenses/meta-llama-3/LICENSE`

## Optional Reference Transcription

### Whisper large-v3-turbo

- Model: [openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo)
- Default reviewed revision: `41f01f3fe87f28c78e2fbf8b568835947dd65ed9`
- Copyright: OpenAI
- License: MIT
- Use here: optional transcription of clone references when no transcript is
  supplied; it can remain unloaded in normal TTS-only use.

The full image prefetched by the standard build contains this model. The MIT
license is bundled at `/app/third_party/licenses/openai-whisper/LICENSE`.

## Runtime Libraries

### Model Context Protocol Python SDK

- Project: [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- Version currently used: 2.3.0
- Copyright: the Model Context Protocol authors and contributors
- License: MIT
- Use here: opt-in Streamable HTTP MCP endpoints and protocol types for local
  AI-agent integration.

The installed distribution includes its MIT license text in package metadata.

### num2words

- Version: `0.5.14`
- Project: [savoirfairelinux/num2words](https://github.com/savoirfairelinux/num2words)
- License: GNU Lesser General Public License 2.1
- Use here: number normalization

### Python-SoXR and libsoxr

- Version: `1.1.0`
- Project: [dofuuz/python-soxr](https://github.com/dofuuz/python-soxr)
- License: GNU Lesser General Public License 2.1 or later, with additional
  notices for bundled PFFFT/FFTPACK material
- Use here: audio resampling through librosa

The Docker compliance bundle contains the exact checksum-verified source
distributions and installed license files for both LGPL components. Their
source archives are ordinary preferred-form source and are not modified by
this project.

### SSML-H Tools

- Package: `ssml-h-tools==0.1.0`
- Project: [Hangry-Labs/ssml-h-tools](https://github.com/Hangry-Labs/ssml-h-tools)
- License: Apache License 2.0
- Use here: hardened parsing, validation, and planning for SSML-H input

The installed package retains its `LICENSE` and `NOTICE` files; copies are
also placed in the Docker compliance bundle.

### PyTorch and NVIDIA CUDA runtime wheels

PyTorch is distributed under BSD-3-Clause terms and includes additional
notices. CUDA, cuDNN, NCCL, and related NVIDIA wheels are subject to the
license files supplied by NVIDIA in each installed distribution. Those files
remain installed under `/usr/local/lib/python3.13/site-packages`, are copied
into `/app/third_party/licenses/python`, and are indexed in
`/app/third_party/PYTHON_PACKAGES.md`.

### Remaining Python packages

Every installed Python distribution retains the metadata and license files
supplied by its publisher. The image generates `PYTHON_PACKAGES.md` from the
actual installed environment so transitive dependencies are visible instead
of being represented by an incomplete hand-maintained list.

## Browser Libraries

### Lucide and Feather icons

- Project: [lucide-icons/lucide](https://github.com/lucide-icons/lucide)
- License: ISC
- Feather-derived icons: MIT, Copyright 2013-present Cole Bemis
- Bundled license: [`omnivoice/standalone_ui/static/vendor/lucide/LICENSE`](omnivoice/standalone_ui/static/vendor/lucide/LICENSE)

### WaveSurfer.js

- Project: [katspaugh/wavesurfer.js](https://github.com/katspaugh/wavesurfer.js)
- Copyright: 2012-2023 katspaugh and contributors
- License: BSD 3-Clause
- Bundled license: [`omnivoice/standalone_ui/static/vendor/wavesurfer/LICENSE`](omnivoice/standalone_ui/static/vendor/wavesurfer/LICENSE)

## Docker System Packages

The runtime image installs FFmpeg from Debian. Its detailed package copyright
record remains at `/usr/share/doc/ffmpeg/copyright`; the compliance bundle
also copies that record and identifies the exact installed Debian binary and
source package versions. Debian's corresponding-source pages are linked from
`/app/third_party/SOURCE_MANIFEST.md`.

The Python base image and all other Debian packages remain governed by their
respective terms. Debian copyright records under `/usr/share/doc` and common
license texts under `/usr/share/common-licenses` are retained in the image.

## Project Media

The branded images, UI screenshots, checked-in generated speech examples, and
project-maintained clone-reference fixture are distributed as documentation
or test/demo assets. Generated speech provenance does not alter or supersede
the licenses and usage restrictions of the models used to create it. Users
must independently obtain rights and consent for any reference recordings or
voices they add.

## Docker Compliance Bundle

Both Docker variants include `/app/third_party` with:

- exact Boson Higgs Audio 2, Meta Llama 3, and OpenAI Whisper license texts;
- the reviewed OmniVoice model card and required attribution notices;
- exact source archives and licenses for `num2words==0.5.14` and
  `soxr==1.1.0`;
- browser-library, SSML-H Tools, PyTorch, NVIDIA, and FFmpeg notices;
- a generated inventory of all installed Python packages;
- exact Debian source coordinates for FFmpeg;
- retained build inputs, SHA-256 checksums, and an offline verifier.

Run `/app/third_party/build/verify_compliance_bundle.py /app/third_party`
inside an image, or run `task compliance-test` after building the tiny image.
