# Research record

## 2026-07-19/20 — candidate audit

The historical challenge fallback listed three claims, but the current anchored
contract contains six. The six texts were fetched and pinned before ownership.
No DineshAI Space or active registry owner existed. A competitor's earlier
high-quality three-claim report was inspected only to identify risks: it found a
naive corner error below 0.1% rather than 14.6%, and naive wedge performance of
100%/0.601% rather than 55%/5.96% because it used near-truth initialization for
both arms.

Primary arXiv source `2601.22751` was downloaded. The source archive hash is
`25029ab...9462`; extracted TeX is `f6f3d10...bc0`. The paper says code is in
the supplement, but OpenReview returned 403 and GitHub searches found no author
repository. We therefore proceeded clean-room only after establishing a
full-scale CPU path for all six claims.

## Protocol resolution

The paper has meaningful internal ambiguities:

1. Algorithm 1 uses coefficient initialization std 0.01, Appendix H.4 says 0.1.
2. Figure 2 says the constraint activates around epoch 2000, Appendix H.5 says
   high constraint weight from epoch 1 through 5000.
3. The wedge package says constraint-aware training includes BC-adaptive bounds,
   near-fundamental initialization, warmup, and ramp; the scored wording calls
   the comparator merely “without the constraint term.”
4. The stability theorem assumes bounded noise but its proof invokes stochastic
   concentration.
5. Table 10 does not state all optimizer/noise details, while its discussion
   informally substitutes sigma≈0.01.

These were treated as experimental questions, not silently resolved to favor the
claim.

## Corner approaches

The full primary protocol uses PyTorch-default float32, K=4, 15,000 epochs,
eta_mu=.005, eta_c=.01, boundary weight 100, sparsity .001, 200 arc points, 100
points per edge, and literal `sum |c| sin²(mu omega)`. Three seeds were run for
both arms. Eleven predeclared naive interpretations were retained:

1. Appendix-literal defaults.
2. Algorithm coefficient std .01.
3. No exponent perturbation.
4. Uniform rather than random collocation.
5. One mean over all boundary points.
6. No sparsity.
7. Slow exponent LR ratio .1.
8. Unit boundary weight.
9. Arc-only interpretation.
10. Edge-only interpretation.
11. Float64 precision.

Four constraint forms/schedules were also retained: literal, normalized detached,
unweighted, and delayed epoch-2000 activation. Float64 was initially used, then
rejected as primary because the paper's PyTorch configuration implies float32;
the complete float32 suite was rerun. This correction changed the constraint
mean to 0.0111% and removed a float64 local-minimum failure. No naive
interpretation reproduced 14.6%.

## Wedge approaches

All five angles and four BC types were run for:

- constraint-aware with BC-adaptive bounds/near-fundamental initialization;
- default naive with global [.1,3] initialization;
- matched naive with the same adaptive initialization as constraint-aware.

This yields 60 full 5,000-step runs. The scored package comparison reproduces
within predeclared tolerances. The matched control demonstrates that part of the
reported gap is due to initialization/protocol changes rather than the
constraint term alone.

## Stability analysis

The continuum Fisher matrix for parameters `(c1,c2,mu1,mu2)` was calculated from
exact moments `integral x^p log(x)^q = (-1)^q q!/(p+1)^(q+1)` at 100 decimal
digits. Across Delta=.01–.075, maximum exponent standard error has log-log slope
`-1.9232`, supporting the claimed Delta^-2 conditioning. Numerical quadrature
independently checks the moments.

For the theorem's literal bounded-noise assumption, a 200-point design with a
fixed bounded structured perturbation was repeated 1,2,4,8,16 times. Exponent
bias stays at about .101852 and the N=3200/N=200 ratio is 1.000003. Thus bounded
noise alone does not concentrate; mean-zero/independent noise is required.

## Resolution study

Ten initialization approaches were run at each Delta in [.02,.05,.1,.2,.3],
each for 10,000 Adam epochs at N=200. Every approach merges below .1 and every
approach resolves at/above .1. A separate noiseless nonlinear least-squares
oracle resolves all five pairs exactly, showing that the threshold is practical
rather than a fundamental non-identifiability result. A noisy oracle is retained
as an additional difficulty diagnostic, not used to manufacture the headline.

## Final independent audit

`verify_all.py` recomputes every decision from raw rows and does not trust stored
summary fields. It assigns verified outcomes to C1/C2/C3/C6 and falsified
outcomes to C4/C5. The hash-bound bundle contains eight records and round-trips
every JSON payload. Sixteen tests cover source hashes, gradients, harmonicity,
BC quantization and swapped-BC controls, exact moments/quadrature, Fisher
conditioning, bounded-noise falsification, corner outcomes, 60 wedge rows, and
the complete 50-cell resolution decision grid.

The publication gate refreshes the live six-claim contract, reruns the verifier
and tests, validates Trackio tags/pin/local-path artifact size, checks the bundle,
and scans all publishable text for secrets, environment files, and absolute-path
leaks. It passed before queue insertion.
