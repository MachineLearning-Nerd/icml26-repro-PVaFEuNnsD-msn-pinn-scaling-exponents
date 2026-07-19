from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
import torch

from repro.src.common import ROOT, deterministic, source_pin_audit, summary, write_json


DELTAS = [0.02, 0.05, 0.1, 0.2, 0.3]


INITIALIZATIONS: list[tuple[str, tuple[float, float] | None]] = [
    ("fixed_0.40_0.80", (0.4, 0.8)),
    ("fixed_0.48_0.56", (0.48, 0.56)),
    ("fixed_0.30_1.00", (0.3, 1.0)),
    ("fixed_0.20_0.70", (0.2, 0.7)),
    ("fixed_0.45_0.65", (0.45, 0.65)),
    ("paper_random_seed_0", None),
    ("paper_random_seed_1", None),
    ("paper_random_seed_2", None),
    ("paper_random_seed_3", None),
    ("paper_random_seed_4", None),
]


def fit_adam(
    delta: float,
    name: str,
    initial: tuple[float, float] | None,
    epochs: int,
) -> dict[str, object]:
    random_seed = int(name.rsplit("_", 1)[-1]) if name.startswith("paper_random") else 0
    deterministic(10_000 + int(delta * 10_000) + random_seed)
    x = torch.linspace(0.1, 1.0, 200, dtype=torch.float64) ** 2
    y = x**0.5 + x ** (0.5 + delta)
    if initial is None:
        generator = torch.Generator().manual_seed(random_seed + int(delta * 10_000))
        mu0 = torch.rand(2, generator=generator, dtype=torch.float64) * 2.9 + 0.1
        mu0 += torch.randn(2, generator=generator, dtype=torch.float64) * 0.1
        c0 = torch.randn(2, generator=generator, dtype=torch.float64) * 0.1
    else:
        mu0 = torch.tensor(initial, dtype=torch.float64)
        c0 = torch.ones(2, dtype=torch.float64)
    initial_exponents = mu0.clone()
    mu = torch.nn.Parameter(mu0)
    coefficients = torch.nn.Parameter(c0)
    optimizer = torch.optim.Adam(
        [
            {"params": [mu], "lr": 0.005},
            {"params": [coefficients], "lr": 0.01},
        ]
    )
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        prediction = (x[:, None] ** mu[None, :] * coefficients[None, :]).sum(dim=1)
        loss = (prediction - y).square().mean() + 0.001 * coefficients.abs().mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_([mu, coefficients], 1.0)
        optimizer.step()
        with torch.no_grad():
            mu.clamp_(0.1, 3.0)
    order = torch.argsort(mu.detach())
    exponents = mu.detach()[order].numpy()
    fitted_coefficients = coefficients.detach()[order].numpy()
    target = np.array([0.5, 0.5 + delta])
    errors = np.abs(exponents - target) / target * 100.0
    recovered_separation = float(exponents[1] - exponents[0])
    active = bool(np.min(np.abs(fitted_coefficients)) >= 0.1)
    resolved = bool(
        active and np.max(errors) < 5.0 and recovered_separation >= 0.5 * delta
    )
    return {
        "delta": delta,
        "approach": name,
        "initial_exponents": initial_exponents.tolist(),
        "exponents": exponents.tolist(),
        "coefficients": fitted_coefficients.tolist(),
        "relative_errors_pct": errors.tolist(),
        "recovered_separation": recovered_separation,
        "both_terms_active": active,
        "resolved": resolved,
        "loss": float(loss.detach()),
    }


def fit_two_exponents(
    x: np.ndarray, y: np.ndarray, starts: list[tuple[float, float]]
) -> dict[str, object]:
    candidates = []
    for start in starts:
        def residual(parameters: np.ndarray) -> np.ndarray:
            c = parameters[:2]
            mu = parameters[2:]
            return x[:, None] ** mu[None, :] @ c - y

        fit = least_squares(
            residual,
            np.array([1.0, 1.0, *start]),
            bounds=([-4, -4, 0.1, 0.1], [4, 4, 1.2, 1.2]),
            xtol=1e-11,
            ftol=1e-11,
            gtol=1e-11,
            max_nfev=3000,
        )
        candidates.append((float(fit.cost), fit.x))
    cost, parameters = min(candidates, key=lambda row: row[0])
    order = np.argsort(parameters[2:])
    return {
        "cost": cost,
        "coefficients": parameters[:2][order].tolist(),
        "exponents": parameters[2:][order].tolist(),
    }


def run(args: argparse.Namespace) -> dict:
    adam_rows = [
        fit_adam(delta, name, initial, args.epochs)
        for delta in DELTAS
        for name, initial in INITIALIZATIONS
    ]
    adam_aggregates = []
    for delta in DELTAS:
        selected = [row for row in adam_rows if row["delta"] == delta]
        adam_aggregates.append(
            {
                "delta": delta,
                "resolved_count": sum(bool(row["resolved"]) for row in selected),
                "approaches": len(selected),
                "resolved_rate": sum(bool(row["resolved"]) for row in selected)
                / len(selected),
                "recovered_separation": summary(
                    [float(row["recovered_separation"]) for row in selected]
                ),
            }
        )

    base_t = np.linspace(np.sqrt(0.01), 1.0, args.samples)
    x = base_t**2
    starts = [
        (a, b)
        for a in (0.25, 0.4, 0.5, 0.65, 0.85)
        for b in (0.3, 0.48, 0.6, 0.8, 1.0)
        if abs(a - b) >= 0.05
    ]
    rows = []
    for delta in DELTAS:
        target = np.array([0.5, 0.5 + delta])
        truth = x**target[0] + x**target[1]
        for seed in range(args.noisy_oracle_seeds):
            rng = np.random.default_rng(seed + int(delta * 10_000))
            y = truth + rng.normal(0.0, args.sigma, size=x.size)
            fitted = fit_two_exponents(x, y, starts)
            exponents = np.asarray(fitted["exponents"])
            errors = np.abs(exponents - target) / target * 100.0
            recovered_separation = float(exponents[1] - exponents[0])
            # Predeclared resolution criterion: both exponent errors <5% and at
            # least half the true separation is retained. This distinguishes a
            # genuine pair from two nearly merged redundant terms.
            resolved = bool(
                np.max(errors) < 5.0 and recovered_separation >= 0.5 * delta
            )
            rows.append(
                {
                    "delta": delta,
                    "seed": seed,
                    "exponents": fitted["exponents"],
                    "coefficients": fitted["coefficients"],
                    "relative_errors_pct": errors.tolist(),
                    "recovered_separation": recovered_separation,
                    "resolved": resolved,
                    "cost": fitted["cost"],
                }
            )
    aggregates = []
    for delta in DELTAS:
        selected = [row for row in rows if row["delta"] == delta]
        separations = [float(row["recovered_separation"]) for row in selected]
        aggregates.append(
            {
                "delta": delta,
                "resolved_count": sum(bool(row["resolved"]) for row in selected),
                "trials": len(selected),
                "resolved_rate": sum(bool(row["resolved"]) for row in selected)
                / len(selected),
                "recovered_separation": summary(separations),
            }
        )
    by_delta = {row["delta"]: row for row in adam_aggregates}

    # Independent noiseless global-oracle control. Starting one optimization at
    # the true parameters is legitimate for testing identifiability rather than
    # optimizer basin size; a zero-residual distinct solution exists at every
    # listed Delta, including 0.02.
    noiseless_oracle = []
    for delta in DELTAS:
        truth = x**0.5 + x ** (0.5 + delta)
        fitted = fit_two_exponents(
            x,
            truth,
            [(0.5, 0.5 + delta), (0.4, 0.8), (0.3, 1.0)],
        )
        exponents = np.asarray(fitted["exponents"])
        error = float(np.max(np.abs(exponents - np.array([0.5, 0.5 + delta]))))
        noiseless_oracle.append(
            {
                "delta": delta,
                "exponents": fitted["exponents"],
                "max_absolute_error": error,
                "cost": fitted["cost"],
                "resolved": error < 1e-7,
            }
        )
    return {
        "paper_id": "PVaFEuNnsD",
        "source_pins": source_pin_audit(),
        "config": {
            "samples": args.samples,
            "sigma": args.sigma,
            "adam_epochs": args.epochs,
            "adam_approaches": len(INITIALIZATIONS),
            "noisy_oracle_seeds": args.noisy_oracle_seeds,
            "multi_starts": len(starts),
            "deltas": DELTAS,
            "criterion": "both relative exponent errors <5% and recovered separation >= Delta/2",
        },
        "paper_adam": {"aggregates": adam_aggregates, "rows": adam_rows},
        "noisy_global_oracle": {"aggregates": aggregates, "rows": rows},
        "noiseless_identifiability_oracle": noiseless_oracle,
        "assessment": {
            "all_at_or_above_0_1_majority_resolved": all(
                by_delta[delta]["resolved_rate"] >= 0.5 for delta in (0.1, 0.2, 0.3)
            ),
            "all_below_0_1_majority_unresolved": all(
                by_delta[delta]["resolved_rate"] < 0.5 for delta in (0.02, 0.05)
            ),
            "absolute_rayleigh_limit_rejected_by_noiseless_oracle": all(
                row["resolved"] for row in noiseless_oracle
            ),
            "interpretation": "Delta=0.1 can be a practical optimizer/noise threshold, not a fundamental identifiability limit",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--sigma", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=10_000)
    parser.add_argument("--noisy-oracle-seeds", type=int, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/resolution.json")
    args = parser.parse_args()
    payload = run(args)
    write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
