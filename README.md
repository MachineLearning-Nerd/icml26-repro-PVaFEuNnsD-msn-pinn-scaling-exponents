# Reproduction: Physics-Informed Müntz–Szász Networks

Clean-room, full-contract reproduction of all six live jury claims for
OpenReview `PVaFEuNnsD`, arXiv `2601.22751`.

The suite covers the trainable power-law architecture, the 270-degree corner,
the full 40-run wedge benchmark, separation-dependent stability, the constraint
ablation, and the complete five-separation resolution study. Exact agreements
and falsifications are reported with equal weight; no headline is force-fit.

All six live claim slots have substantive outcomes: **four verified and two
falsified (12 possible challenge points)**.

| Claim | Outcome | Main measured result |
| --- | --- | --- |
| C1: architecture/two timescales | Verified | 0.5 LR ratio; gradient error ≤1.03e-11; max recovery error 0.643% |
| C2: 270° corner | Verified | 0.0111% mean / 0.00367% median error (paper 0.009%) |
| C3: 40-run wedge package | Verified, qualified | constraint 100%/0.00399%; naive 65%/4.41% |
| C4: stability theorem | Falsified as written | Δ slope −1.923 verifies mechanism; bounded noise does not yield N^-1/2 |
| C5: 14.6%→0.009% ablation | Falsified | constraint 0.0111%, but naive already 0.0412%; 11 interpretations miss 14.6% |
| C6: Δ=0.1 threshold | Verified, qualified | 0/10 resolve below 0.1; 10/10 resolve at/above 0.1 |

## Environment

```bash
uv sync --python 3.12
```

## Evidence commands

All commands run from this directory using relative paths:

```bash
uv run python -m repro.src.run_architecture --epochs 10000 --seeds 3
uv run python -m repro.src.run_corner --epochs 15000 --seeds 3 --audit-seed 17
uv run python -m repro.src.run_wedge --steps 5000 --seed 0
uv run python -m repro.src.run_stability --precision 100 --sigma 0.001
uv run python -m repro.src.run_resolution --epochs 10000 --noisy-oracle-seeds 10
uv run python -m repro.src.verify_all
uv run pytest -q
uv run python -m repro.src.prepublish_gate
```

The final gate refreshes the live six-claim wording, recomputes every outcome
from raw rows, validates the hash-bound bundle, checks Trackio tags/artifact
metadata, reruns 16 tests, and scans for secrets and leaked absolute paths.

## Primary-source pin

- arXiv: `2601.22751`
- source tar SHA-256: `25029ab7f42fdc9688c36c3fcba636a0956cb5fb07a8b85fac824268a6bf9462`
- extracted TeX SHA-256: `f6f3d10a1e0c1a8a5a665cb91fdfe0726a481e38be920dd936ec065aef30dbc0`

The paper says code is available in its OpenReview supplementary material, but
the attachment returned HTTP 403 during the audit and no public author
repository was found. This implementation is clean-room.

## Evidence bundle

`outputs/evidence_bundle.jsonl` contains eight hash/size/payload-bound records:
the exact live claims, source pins, five raw result files, and the independently
recomputed claim verdicts. Gate hash:
`63822870e91b03c3898eb8fd14acf8dc49a32fc82449460122499ace6b8c635a`.
