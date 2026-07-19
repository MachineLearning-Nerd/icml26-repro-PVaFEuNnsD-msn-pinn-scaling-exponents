# Claim 1 - Architecture


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_9cbd0bc82cff", "created_at": "2026-07-19T21:02:16+00:00", "title": "Verified trainable power sums and two timescales"}
-->
# Claim 1 — VERIFIED

The implementation is exactly `u_theta(x)=sum_k c_k x^mu_k`, with both parameter blocks trainable and separate Adam groups `eta_c=0.01`, `eta_mu=0.005` (ratio **0.5**). Three full 10,000-epoch runs recover the exponent with maximum relative error **0.6426%**. Centered finite differences match autograd within **1.03e-11**.

The frozen-exponent control has median error **23.79%**, demonstrating that the reported recovery is not coefficient fitting mislabeled as exponent learning.
