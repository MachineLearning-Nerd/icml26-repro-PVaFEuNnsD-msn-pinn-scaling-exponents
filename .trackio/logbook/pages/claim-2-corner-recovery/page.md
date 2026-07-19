# Claim 2 - Corner recovery


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_326f8ffa9a7b", "created_at": "2026-07-19T21:02:16+00:00", "title": "Verified 270-degree Kondrat'ev exponent"}
-->
# Claim 2 — VERIFIED

At full source scale (`K=4`, 15,000 epochs, 200 arc points, 100 points per edge, two-timescale Adam), the literal constraint-aware loss recovers `mu≈2/3` over **3 seeds** with mean error **0.01114%** and median **0.00367%** (paper: 0.009%). The Figure-2 delayed-activation interpretation independently gives 0.00875%.

A polar finite-difference Laplacian check over 36 cells independently confirms that every `r^mu sin(mu theta)` basis term is harmonic, with maximum residual below `2.5e-7`.
