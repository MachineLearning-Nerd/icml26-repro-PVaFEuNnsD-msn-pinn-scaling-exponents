from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import torch

from repro.src.common import ROOT, deterministic, source_pin_audit, summary, write_json


OMEGA = 1.5 * math.pi
TRUE_ALPHA = 2.0 / 3.0
K = 4
MU_MIN, MU_MAX = 0.1, 3.0


@dataclass(frozen=True)
class Protocol:
    name: str
    eta_mu: float = 0.005
    eta_c: float = 0.01
    coefficient_std: float = 0.1
    exponent_perturbation_std: float = 0.1
    boundary_weight: float = 100.0
    sparsity_weight: float = 0.001
    deterministic_points: bool = False
    aggregate_boundary_points: bool = False
    include_arc: bool = True
    include_far_edge: bool = True
    constraint_form: str = "literal"
    activation_epoch: int = 1
    dtype: str = "float32"


PRIMARY = Protocol(name="appendix_literal")

# Ten materially distinct readings of underspecified or internally inconsistent
# source details. They are an audit, not a model-selection grid: every result is
# retained, and the primary result is fixed above before execution.
NAIVE_INTERPRETATIONS = [
    PRIMARY,
    replace(PRIMARY, name="algorithm_c_std_0.01", coefficient_std=0.01),
    replace(PRIMARY, name="no_mu_perturbation", exponent_perturbation_std=0.0),
    replace(PRIMARY, name="uniform_collocation", deterministic_points=True),
    replace(PRIMARY, name="all_boundary_point_mean", aggregate_boundary_points=True),
    replace(PRIMARY, name="no_sparsity", sparsity_weight=0.0),
    replace(PRIMARY, name="slow_mu_0.1_ratio", eta_mu=0.001),
    replace(PRIMARY, name="unit_boundary_weight", boundary_weight=1.0),
    replace(PRIMARY, name="arc_only_interpretation", include_far_edge=False),
    replace(PRIMARY, name="edge_only_interpretation", include_arc=False),
    replace(PRIMARY, name="higher_precision_float64", dtype="float64"),
]


class CornerMSN(torch.nn.Module):
    def __init__(self, protocol: Protocol, seed: int):
        super().__init__()
        dtype = torch.float32 if protocol.dtype == "float32" else torch.float64
        generator = torch.Generator().manual_seed(seed)
        initial_mu = torch.rand(K, generator=generator, dtype=dtype)
        initial_mu = initial_mu * (MU_MAX - MU_MIN) + MU_MIN
        if protocol.exponent_perturbation_std:
            initial_mu += (
                torch.randn(K, generator=generator, dtype=dtype)
                * protocol.exponent_perturbation_std
            )
        initial_c = (
            torch.randn(K, generator=generator, dtype=dtype)
            * protocol.coefficient_std
        )
        self.mu = torch.nn.Parameter(initial_mu)
        self.c = torch.nn.Parameter(initial_c)

    def forward(self, r: torch.Tensor, theta: torch.Tensor) -> torch.Tensor:
        radial = r[:, None].clamp_min(1e-12) ** self.mu[None, :]
        angular = torch.sin(theta[:, None] * self.mu[None, :])
        return (radial * angular * self.c[None, :]).sum(dim=1)

    def dominant(self) -> tuple[float, float, int]:
        index = int(torch.argmax(self.c.detach().abs()).item())
        return (
            float(self.mu.detach()[index]),
            float(self.c.detach()[index]),
            index,
        )


def sample_points(protocol: Protocol, seed: int) -> dict[str, torch.Tensor]:
    dtype = torch.float32 if protocol.dtype == "float32" else torch.float64
    generator = torch.Generator().manual_seed(seed + 100_000)
    if protocol.deterministic_points:
        arc_theta = (torch.arange(200, dtype=dtype) + 0.5) / 200 * OMEGA
        edge_radius = ((torch.arange(100, dtype=dtype) + 0.5) / 100) ** 2
    else:
        arc_theta = torch.rand(200, generator=generator, dtype=dtype) * OMEGA
        edge_radius = torch.rand(100, generator=generator, dtype=dtype) ** 2
    return {
        "arc_r": torch.ones(200, dtype=dtype),
        "arc_theta": arc_theta,
        "arc_target": torch.sin(TRUE_ALPHA * arc_theta),
        "edge_r": edge_radius,
        "edge_theta": torch.full((100,), OMEGA, dtype=dtype),
    }


def boundary_components(
    model: CornerMSN, points: dict[str, torch.Tensor]
) -> tuple[torch.Tensor, torch.Tensor]:
    arc_residual = model(points["arc_r"], points["arc_theta"]) - points["arc_target"]
    edge_residual = model(points["edge_r"], points["edge_theta"])
    return arc_residual, edge_residual


def boundary_loss(
    model: CornerMSN, points: dict[str, torch.Tensor], protocol: Protocol
) -> torch.Tensor:
    arc, edge = boundary_components(model, points)
    selected = []
    if protocol.include_arc:
        selected.append(arc)
    if protocol.include_far_edge:
        selected.append(edge)
    if protocol.aggregate_boundary_points:
        return torch.cat(selected).square().mean()
    return sum(residual.square().mean() for residual in selected)


def constraint_loss(model: CornerMSN, form: str) -> torch.Tensor:
    quantization = torch.sin(model.mu * OMEGA).square()
    if form == "literal":
        return (model.c.abs() * quantization).sum()
    if form == "normalized_detached":
        weights = model.c.detach().abs()
        return ((weights / weights.sum().clamp_min(1e-12)) * quantization).sum()
    if form == "unweighted":
        return quantization.sum()
    raise ValueError(f"unknown constraint form: {form}")


def train(
    seed: int,
    epochs: int,
    protocol: Protocol,
    use_constraint: bool,
) -> dict[str, float | int | str | bool]:
    deterministic(seed)
    model = CornerMSN(protocol, seed)
    points = sample_points(protocol, seed)
    optimizer = torch.optim.Adam(
        [
            {"params": [model.mu], "lr": protocol.eta_mu},
            {"params": [model.c], "lr": protocol.eta_c},
        ]
    )
    initial_mu = model.mu.detach().tolist()
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad(set_to_none=True)
        bc = boundary_loss(model, points, protocol)
        loss = protocol.boundary_weight * bc
        loss = loss + protocol.sparsity_weight * model.c.abs().mean()
        if use_constraint and epoch >= protocol.activation_epoch:
            weight = 10.0 if epoch <= 5000 else 1.0
            loss = loss + weight * constraint_loss(model, protocol.constraint_form)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        with torch.no_grad():
            model.mu.clamp_(MU_MIN, MU_MAX)
    mu, coefficient, index = model.dominant()
    arc, edge = boundary_components(model, points)
    return {
        "protocol": protocol.name,
        "seed": seed,
        "use_constraint": use_constraint,
        "mu_dominant": mu,
        "coefficient_dominant": coefficient,
        "dominant_index": index,
        "relative_error_pct": abs(mu - TRUE_ALPHA) / TRUE_ALPHA * 100.0,
        "arc_mse": float(arc.detach().square().mean()),
        "far_edge_mse": float(edge.detach().square().mean()),
        "sin_mu_omega": math.sin(mu * OMEGA),
        "initial_mu": initial_mu,
    }


def laplacian_finite_difference(mu: float, r: float, theta: float, h: float) -> float:
    # Independent polar-coordinate finite difference for r^mu sin(mu theta).
    def u(rr: float, tt: float) -> float:
        return rr**mu * math.sin(mu * tt)

    ur = (u(r + h, theta) - u(r - h, theta)) / (2 * h)
    urr = (u(r + h, theta) - 2 * u(r, theta) + u(r - h, theta)) / h**2
    utt = (u(r, theta + h) - 2 * u(r, theta) + u(r, theta - h)) / h**2
    return urr + ur / r + utt / r**2


def run(args: argparse.Namespace) -> dict:
    primary_naive = [train(seed, args.epochs, PRIMARY, False) for seed in range(args.seeds)]
    constraint_protocols = [
        PRIMARY,
        replace(PRIMARY, name="normalized_detached", constraint_form="normalized_detached"),
        replace(PRIMARY, name="unweighted", constraint_form="unweighted"),
        replace(PRIMARY, name="figure_delayed_epoch_2000", activation_epoch=2000),
    ]
    primary_constraint = [
        train(seed, args.epochs, PRIMARY, True) for seed in range(args.seeds)
    ]
    interpretation_runs = [
        train(args.audit_seed, args.epochs, protocol, False)
        for protocol in NAIVE_INTERPRETATIONS
    ]
    constraint_form_runs = [
        train(args.audit_seed, args.epochs, protocol, True)
        for protocol in constraint_protocols
    ]
    fd_values = [
        abs(laplacian_finite_difference(mu, r, theta, 1e-4))
        for mu in (0.37, 2 / 3, 1.21, 2.4)
        for r in (0.2, 0.5, 0.8)
        for theta in (0.4, 1.3, 3.1)
    ]
    naive_errors = [float(row["relative_error_pct"]) for row in primary_naive]
    constraint_errors = [
        float(row["relative_error_pct"]) for row in primary_constraint
    ]
    interpretation_errors = [
        float(row["relative_error_pct"]) for row in interpretation_runs
    ]
    return {
        "paper_id": "PVaFEuNnsD",
        "config": {
            "K": K,
            "omega_degrees": 270,
            "true_alpha": TRUE_ALPHA,
            "epochs": args.epochs,
            "primary_seeds": args.seeds,
            "audit_seed": args.audit_seed,
            "primary_protocol": asdict(PRIMARY),
        },
        "source_pins": source_pin_audit(),
        "primary_naive": {
            "runs": primary_naive,
            "error_pct": summary(naive_errors),
        },
        "primary_constraint": {
            "runs": primary_constraint,
            "error_pct": summary(constraint_errors),
        },
        "naive_interpretation_audit": {
            "predeclared_count": len(NAIVE_INTERPRETATIONS),
            "runs": interpretation_runs,
            "error_pct": summary(interpretation_errors),
            "reported_14_6_reproduced_within_2pp": any(
                abs(error - 14.6) <= 2.0 for error in interpretation_errors
            ),
        },
        "constraint_form_audit": constraint_form_runs,
        "independent_harmonicity_check": {
            "method": "polar finite differences, independent of analytic cancellation",
            "cells": len(fd_values),
            "max_abs_laplacian": max(fd_values),
        },
        "headline_assessment": {
            "constraint_recovery_close_to_0_009_pct": float(np.median(constraint_errors))
            <= 0.05,
            "naive_14_6_pct_reproduced": any(
                abs(error - 14.6) <= 2.0 for error in interpretation_errors
            ),
            "constraint_beats_primary_naive": float(np.median(constraint_errors))
            < float(np.median(naive_errors)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15_000)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--audit-seed", type=int, default=17)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/corner.json")
    args = parser.parse_args()
    payload = run(args)
    write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
