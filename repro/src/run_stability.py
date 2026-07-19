from __future__ import annotations

import argparse
import math
from pathlib import Path

import mpmath as mp
import numpy as np

from repro.src.common import ROOT, source_pin_audit, write_json


def moment(power: mp.mpf, log_degree: int) -> mp.mpf:
    return (-1) ** log_degree * mp.factorial(log_degree) / (
        power + 1
    ) ** (log_degree + 1)


def continuum_fisher(delta: float, coefficient: float = 1.0) -> mp.matrix:
    # Jacobian columns for (c1,c2,mu1,mu2) at alpha=(.5,.5+Delta).
    alpha = [mp.mpf("0.5"), mp.mpf("0.5") + mp.mpf(str(delta))]
    descriptors = [
        (alpha[0], 0, mp.mpf(1)),
        (alpha[1], 0, mp.mpf(1)),
        (alpha[0], 1, mp.mpf(str(coefficient))),
        (alpha[1], 1, mp.mpf(str(coefficient))),
    ]
    output = mp.matrix(4, 4)
    for row, (a, la, scale_a) in enumerate(descriptors):
        for column, (b, lb, scale_b) in enumerate(descriptors):
            output[row, column] = scale_a * scale_b * moment(a + b, la + lb)
    return output


def slope(x: list[float], y: list[float]) -> float:
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def run(args: argparse.Namespace) -> dict:
    mp.mp.dps = args.precision
    deltas = [0.01, 0.015, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3]
    rows = []
    for delta in deltas:
        fisher = continuum_fisher(delta)
        covariance = fisher**-1
        exponent_std = max(mp.sqrt(covariance[2, 2]), mp.sqrt(covariance[3, 3]))
        eigvals = sorted(mp.eigsy(fisher, eigvals_only=True))
        rows.append(
            {
                "delta": delta,
                "max_exponent_std_unit_sigma_sqrtN": float(exponent_std),
                "scaled_by_delta_squared": float(exponent_std * delta**2),
                "minimum_full_fisher_eigenvalue": float(eigvals[0]),
            }
        )
    small = [row for row in rows if row["delta"] <= 0.075]
    std_slope = slope(
        [row["delta"] for row in small],
        [row["max_exponent_std_unit_sigma_sqrtN"] for row in small],
    )
    eigen_slope = slope(
        [row["delta"] for row in small],
        [row["minimum_full_fisher_eigenvalue"] for row in small],
    )

    # The theorem states merely |epsilon_i|<=sigma, but its proof invokes
    # concentration. A constant signed perturbation is a deterministic control:
    # duplicating the same samples cannot reduce its least-squares bias as N^-1/2.
    x_base = np.linspace(0.01, 1.0, 200)
    alpha = np.array([0.5, 0.7])
    true_y = x_base[:, None] ** alpha[None, :] @ np.ones(2)
    bias_rows = []
    from scipy.optimize import least_squares

    for repeats in [1, 2, 4, 8, 16]:
        x = np.tile(x_base, repeats)
        # Structured bounded error aligned with log(x); same design is repeated.
        epsilon = args.sigma * np.tile(np.sign(np.log(x_base) + 0.8), repeats)
        y = np.tile(true_y, repeats) + epsilon

        def residual(parameters: np.ndarray) -> np.ndarray:
            c = parameters[:2]
            mu = parameters[2:]
            return x[:, None] ** mu[None, :] @ c - y

        fit = least_squares(
            residual,
            np.array([1.0, 1.0, 0.49, 0.71]),
            bounds=([-3, -3, 0.2, 0.2], [3, 3, 1.2, 1.2]),
            xtol=1e-13,
            ftol=1e-13,
            gtol=1e-13,
            max_nfev=5000,
        )
        estimated = np.sort(fit.x[2:])
        bias_rows.append(
            {
                "N": int(x.size),
                "max_exponent_error": float(np.max(np.abs(estimated - alpha))),
                "cost": float(fit.cost),
            }
        )

    return {
        "paper_id": "PVaFEuNnsD",
        "source_pins": source_pin_audit(),
        "continuum_fisher": {
            "precision_digits": args.precision,
            "rows": rows,
            "small_delta_exponent_std_loglog_slope": std_slope,
            "small_delta_min_eigenvalue_loglog_slope": eigen_slope,
            "delta_minus_two_supported": -2.25 <= std_slope <= -1.75,
        },
        "bounded_noise_counterexample": {
            "sigma": args.sigma,
            "construction": "repeat identical 200-point design and identical bounded structured errors",
            "rows": bias_rows,
            "error_ratio_last_to_first": bias_rows[-1]["max_exponent_error"]
            / bias_rows[0]["max_exponent_error"],
            "n_minus_half_without_mean_zero_rejected": bias_rows[-1][
                "max_exponent_error"
            ]
            > 0.9 * bias_rows[0]["max_exponent_error"],
        },
        "assessment": {
            "separation_mechanism_verified": -2.25 <= std_slope <= -1.75,
            "theorem_as_written_missing_stochastic_noise_assumption": True,
            "reason": "bounded errors alone do not concentrate as N^{-1/2}; the proof silently uses mean-zero concentration",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precision", type=int, default=100)
    parser.add_argument("--sigma", type=float, default=0.001)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/stability.json")
    args = parser.parse_args()
    payload = run(args)
    write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()

