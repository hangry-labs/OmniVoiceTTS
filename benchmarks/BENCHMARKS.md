# OmniVoiceTTS Benchmarks

Benchmark category logs are append-only tables. Each row is one benchmark run for one benchmark category.

## Purpose

These benchmarks track OmniVoiceTTS runtime performance across versions, refactors, dependency changes, Docker image changes, and future performance work. The goal is not to produce a universal score; it is to catch local improvements and regressions under a repeatable workload.

More categories may be added as the product changes; keeping one append-only file per category makes version-to-version comparisons easy to scan.

Current baseline hardware: NVIDIA GeForce RTX 5060 Ti. AMD ROCm support is not validated because the maintainer does not have AMD hardware; AMD testing would require an AMD GPU donation or a reliable community tester.

## Methodology

- Workload source: `examples/assets/manifest.json`.
- Selection: first two random samples from each manifest language, repeated deterministically to the configured call count.
- Default measured calls: 100 per category.
- Each category is prewarmed immediately before that category is measured, so one stage's cold start or timeout does not distort later stages.
- Detailed JSON results are stored in `example-generation.json`.

## Categories

- `warm_random` (`random_voice` in JSON): measured no-reference calls after that stage's warmup. This should usually be fastest because no voice clone prompt is prepared.
- `warm_predefined` (`predefined_voice` in JSON): measured named built-in or saved OpenAI-compatible voice calls after warmup. This covers voices created in the UI Add Voice tab and the benchmark built-in clone alias. Voice clone prompt preparation is cached after warmup.
- `warm_direct_reference` (`direct_reference_audio` in JSON): measured direct `ref_audio` calls after warmup. This is the original ad hoc cloning path and intentionally does not use the stored-voice cache.
- `prewarm_random`: warmup calls for the no-reference path.
- `prewarm_predefined`: warmup calls for the cached predefined voice path.
- `prewarm_direct_reference`: warmup calls for the direct `ref_audio` path.

- [warm_random](WARM_RANDOM.md)
- [warm_predefined](WARM_PREDEFINED.md)
- [warm_direct_reference](WARM_DIRECT_REFERENCE.md)
- [prewarm_random](PREWARM_RANDOM.md)
- [prewarm_predefined](PREWARM_PREDEFINED.md)
- [prewarm_direct_reference](PREWARM_DIRECT_REFERENCE.md)

Detailed machine-readable run data is stored in `example-generation.json`.
