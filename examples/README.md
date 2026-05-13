# Examples

This directory contains the static public project page used for GitHub Pages.

The page embeds the example manifest in `voices.js`, so opening `index.html` directly works. Serving over HTTP is still useful for a closer GitHub Pages preview:

```bash
python -m http.server 8055
```

Then open `http://localhost:8055/examples/`.

Runtime examples now live in the root [README.md](../README.md), especially:

- Docker quick start
- HTTP API calls
- Python client usage
- local Taskfile workflows
- Python 3.13 Docker/runtime baseline

Generated language showcase candidates live under `assets/<language>/`:

- `random/`: ten native-language culture/humor samples for review, rotating voice-design profiles and selected non-verbal tags
- `intro/`: three translated OmniVoiceTTS/Hangry Labs introduction candidates
- `clone/`: one reference-clone candidate using `examples/original_clone.mp3`
- `assets/manifest.json`: exact text, language, and file metadata for the generated samples

The current asset set is intentionally oversized so the best examples can be selected and the rest deleted before publication.

This Hangry Labs fork is intentionally focused on local inference, browser UI, HTTP API, and baked Docker images. Upstream training, fine-tuning, data preparation, and benchmark-evaluation examples were removed from this fork; use the original [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) repository for those workflows.
