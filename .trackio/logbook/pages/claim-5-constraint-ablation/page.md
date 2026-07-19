# Claim 5 - Constraint ablation


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_0804a421d0f3", "created_at": "2026-07-19T21:02:18+00:00", "title": "Falsified 14.6% naive baseline"}
-->
# Claim 5 — FALSIFIED

The constraint-aware endpoint reproduces: mean error is **0.01114%**, including a Figure-2-schedule run at 0.00875%. The claimed naive endpoint does not: the three-seed primary naive mean is **0.04123%**, already near the true exponent without the explicit constraint.

To avoid declaring failure from one interpretation, we ran **11 materially distinct source-supported protocols** (coefficient initialization, exponent perturbation, random/uniform collocation, boundary aggregation, sparsity, learning-rate ratio, boundary weighting, arc/edge interpretation, and precision). Their errors range from **0.00046% to 300.000%**; none is within two percentage points of 14.6%.
