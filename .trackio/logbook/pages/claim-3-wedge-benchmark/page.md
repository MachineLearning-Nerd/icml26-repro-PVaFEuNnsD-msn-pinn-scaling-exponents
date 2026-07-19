# Claim 3 - Wedge benchmark


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_dba035c75971", "created_at": "2026-07-19T21:02:17+00:00", "title": "Verified package result; attribution qualified"}
-->
# Claim 3 — VERIFIED WITH AN ATTRIBUTION QUALIFICATION

The paper-scale package comprises 5 angles × 4 boundary types × 2 methods = **40 runs**. Constraint-aware training reaches **100% success / 0.00399% mean error** (paper: 100% / 0.022%). The default naive implementation reaches **65% / 4.408%** (paper: 55% / 5.96%), reproducing the claimed method-package separation.

The independent matched-initialization control reaches **100% / 0.621%** without the constraint. Thus the package comparison reproduces, but the paper's BC-adaptive initialization and near-truth seed explain part of the gain; the constraint term alone does not explain the full headline ratio.
