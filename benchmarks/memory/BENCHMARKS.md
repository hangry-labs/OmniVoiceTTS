# Memory Benchmarks

Memory tests are split by execution device because CPU and GPU memory have different constraints and measurement methods.

- [CPU memory](cpu/BENCHMARKS.md) finds the lowest passing Docker memory limit for six common voice paths, then publishes a conservative whole-GB recommendation.
- [GPU memory](gpu/BENCHMARKS.md) tracks warmed PyTorch allocation and sampled whole-device VRAM for random, designed, direct-clone, and cached-clone generation.

Both suites are manual. They are intentionally excluded from normal tests, validation, release, and CI because they are slow and require controlled host resources.
