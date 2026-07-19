# Status

- OpenReview ID: `PVaFEuNnsD`
- arXiv: `2601.22751`
- Effective live contract: 6 anchored claims / 12 possible points
- Owner: `codex-msn-pinn-six-claims`
- State: `local_gate_passed`
- Current step: GitHub push, then atomic canonical HF enqueue
- Next: shared publisher promotes the registered 85,582-byte bundle and performs public readback
- Queue invariant: this paper is not eligible for `backlog.json` until every live claim and the complete publication gate pass

## Source availability

The arXiv source is pinned locally. The paper says its code is in the OpenReview
supplement, but the attachment endpoint currently returns HTTP 403 and no public
author repository was found. The reproduction is therefore clean-room. A prior
competitor implementation is used only as discrepancy evidence, never as the
implementation source.

## Known scored discrepancy

The historical three-claim jury treated naive-baseline differences as secondary.
The current anchored C3 and C5 explicitly score those comparisons. A previous
full-scale run measured a naive corner error below 0.1% instead of 14.6%, and a
naive wedge result of 100% / 0.601% instead of 55% / 5.96%. The present work must
resolve or substantively falsify those exact comparisons and report all outcomes.

## Completed evidence

- C1 verified: three full 10,000-epoch runs; finite-difference gradient error
  at most `1.03e-11`; frozen-exponent control rejected.
- C2 verified: three full 15,000-epoch float32 runs, `0.011135%` mean error;
  delayed Figure-2 schedule `0.008747%`.
- C3 verified with attribution qualification: all 40 scored runs plus 20
  matched-initialization controls; constraint `100%/0.003990%`, default naive
  `65%/4.4076%`, matched naive `100%/0.6207%`.
- C4 falsified as literally stated: 100-digit Fisher slope `-1.9232` supports
  `Delta^-2`, but a bounded structured-noise counterexample has N=3200/N=200
  exponent-error ratio `1.000003`, rejecting the unstated `N^-1/2` step.
- C5 falsified: constraint endpoint reproduces, but primary naive is
  `0.04123%`, not `14.6%`; eleven materially distinct interpretations fail to
  reproduce 14.6%.
- C6 verified as practical threshold: all ten approaches merge at `.02/.05`
  and all ten resolve at `.1/.2/.3`; noiseless oracle rejects an absolute
  identifiability interpretation.
- Independent verifier: 6/6 substantive outcomes, 12 possible points.
- Tests: 16/16.
- Publication gate: passed at `2026-07-20T02:35+05:30`.
- Bundle: 85,582 bytes, SHA-256
  `63822870e91b03c3898eb8fd14acf8dc49a32fc82449460122499ace6b8c635a`.
