---
layout: default
title: Examples guide
permalink: /examples/guide/
---
# OmniVoiceTTS examples

[Listen to voice examples](https://hangry-labs.github.io/OmniVoiceTTS/examples/)
or [SSML-H conversations](https://hangry-labs.github.io/OmniVoiceTTS/examples/ssml-h.html).

## Voices and languages

Choose one of 20 speech languages to hear ten voice-variety samples, randomized
introductions and a cross-language clone of the shared English reference voice.
The original player supports playback, seeking, mute and a shared volume control.
Selecting a language also translates the gallery. Norwegian has translated
gallery controls with English recordings. Arabic and Urdu use right-to-left
gallery content while the website header keeps its own direction.

The six website locales serve the actual translated READMEs. Other speech
languages remain selectable within the gallery; direct links such as `?lang=ar`
still work. The `language` query parameter remembers a speech selection while
`lang` selects the website documentation language.

## SSML-H conversations

The conversation showcase includes a featured two-character exchange and two
additional dialogues, their transcripts, voice declarations, request settings
and copyable SSML-H source. These are generated examples, not live inference.

## Local preview

Run `task pages` for the complete website, `task pages-build` for a static
build, or `task pages-test` for staging and routing checks. These commands do
not load speech models or use a GPU. See the [website guide](../site/README.md).

The `index.md` and `ssml-h.md` wrappers include the existing standalone HTML
content in the shared website shell. Player code, translations, manifests and
recordings remain shared between both presentations. Opening `index.html` or
`ssml-h.html` directly still works when the assets are kept together. To preview
the standalone files over HTTP:

```bash
python -m http.server 8055
```

Open <http://localhost:8055/examples/>.

## Recordings and provenance

Generated language showcase recordings live under `assets/<language>/`:

- `random/`: ten native-language culture/humor samples. Plain-text samples rotate voice-design profiles. Samples with bracket expression tags such as `[laughter]`, `[sigh]`, and `[surprise-ah]` intentionally use no voice-design `instruct` because OmniVoice can produce unstable non-speech audio when voice design is combined with bracket tags.
- `intro/`: three translated OmniVoiceTTS/Hangry Labs introduction candidates
- `clone/`: one reference-clone candidate using `examples/original_clone.mp3`
- `assets/manifest.json`: exact text, language, and file metadata for the generated samples

The gallery selects these recordings from the shared manifest; no model is loaded for playback.

This Hangry Labs fork is intentionally focused on local inference, browser UI, HTTP API, and baked Docker images. Upstream training, fine-tuning, data preparation, and benchmark-evaluation examples were removed from this fork; use the original [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) repository for those workflows.
