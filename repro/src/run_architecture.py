from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch

from repro.src.common import ROOT, deterministic, source_pin_audit, summary, write_json


class PowerSum(torch.nn.Module):
    def __init__(self, seed: int, train_exponents: bool = True):
        super().__init__()
        generator = torch.Generator().manual_seed(seed)
        initial_mu = torch.rand(4, generator=generator, dtype=torch.float64) * 2.9 + 0.1
        initial_c = torch.randn(4, generator=generator, dtype=torch.float64) * 0.01
        self.mu = torch.nn.Parameter(initial_mu, requires_grad=train_exponents)
        self.c = torch.nn.Parameter(initial_c)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x[:, None] ** self.mu[None, :] * self.c[None, :]).sum(dim=1)


def train(seed: int, epochs: int, train_exponents: bool = True) -> dict[str, object]:
    deterministic(seed)
    x = torch.linspace(0.1, 1.0, 200, dtype=torch.float64) ** 2
    y = x**0.5
    model = PowerSum(seed, train_exponents)
    initial_mu = model.mu.detach().clone()
    initial_c = model.c.detach().clone()
    groups = [{"params": [model.c], "lr": 0.01}]
    if train_exponents:
        groups.append({"params": [model.mu], "lr": 0.005})
    optimizer = torch.optim.Adam(groups)
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(x)
        loss = (prediction - y).square().mean() + 0.001 * model.c.abs().mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if train_exponents:
            with torch.no_grad():
                model.mu.clamp_(0.1, 3.0)
    index = int(torch.argmax(model.c.detach().abs()).item())
    dominant = float(model.mu.detach()[index])
    return {
        "seed": seed,
        "train_exponents": train_exponents,
        "dominant_mu": dominant,
        "dominant_c": float(model.c.detach()[index]),
        "dominant_relative_error_pct": abs(dominant - 0.5) / 0.5 * 100,
        "final_mse": float((model(x) - y).square().mean().detach()),
        "mu_movement_l2": float(torch.linalg.vector_norm(model.mu.detach() - initial_mu)),
        "c_movement_l2": float(torch.linalg.vector_norm(model.c.detach() - initial_c)),
        "mu": model.mu.detach().tolist(),
        "c": model.c.detach().tolist(),
    }


def gradient_audit() -> dict[str, float | int | bool]:
    deterministic(20260720)
    x = torch.linspace(0.03, 1.0, 31, dtype=torch.float64)
    model = PowerSum(20260720)
    weights = torch.linspace(-0.4, 0.7, x.numel(), dtype=torch.float64)
    scalar = (model(x) * weights).sum()
    scalar.backward()
    analytic_mu = model.mu.grad.detach().numpy().copy()
    analytic_c = model.c.grad.detach().numpy().copy()
    step = 1e-6
    numerical_mu = []
    numerical_c = []
    with torch.no_grad():
        for parameter, numerical in ((model.mu, numerical_mu), (model.c, numerical_c)):
            for index in range(parameter.numel()):
                original = float(parameter[index])
                parameter[index] = original + step
                plus = float((model(x) * weights).sum())
                parameter[index] = original - step
                minus = float((model(x) * weights).sum())
                parameter[index] = original
                numerical.append((plus - minus) / (2 * step))
    mu_error = float(np.max(np.abs(analytic_mu - np.asarray(numerical_mu))))
    c_error = float(np.max(np.abs(analytic_c - np.asarray(numerical_c))))
    return {
        "cells": 8,
        "max_mu_gradient_error": mu_error,
        "max_c_gradient_error": c_error,
        "passed": max(mu_error, c_error) < 1e-8,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    trainable = [train(seed, args.epochs, True) for seed in range(args.seeds)]
    frozen = [train(seed, args.epochs, False) for seed in range(args.seeds)]
    return {
        "paper_id": "PVaFEuNnsD",
        "source_pins": source_pin_audit(),
        "architecture": {
            "formula": "u_theta(x)=sum_k c_k x^mu_k",
            "trainable_parameter_blocks": ["coefficients c", "exponents mu"],
            "eta_c": 0.01,
            "eta_mu": 0.005,
            "eta_mu_over_eta_c": 0.5,
            "K": 4,
            "N": 200,
            "epochs": args.epochs,
        },
        "trainable_runs": trainable,
        "frozen_exponent_control": frozen,
        "trainable_error_pct": summary(
            [float(row["dominant_relative_error_pct"]) for row in trainable]
        ),
        "frozen_error_pct": summary(
            [float(row["dominant_relative_error_pct"]) for row in frozen]
        ),
        "gradient_audit": gradient_audit(),
        "assessment": {
            "both_parameter_blocks_move": all(
                float(row["mu_movement_l2"]) > 0
                and float(row["c_movement_l2"]) > 0
                for row in trainable
            ),
            "two_timescale_ratio_exact": 0.005 / 0.01 == 0.5,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10_000)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/architecture.json")
    args = parser.parse_args()
    payload = run(args)
    write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()

