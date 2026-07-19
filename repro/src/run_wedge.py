from __future__ import annotations

import argparse
import itertools
import math
from pathlib import Path

import numpy as np
import torch

from repro.src.common import ROOT, deterministic, source_pin_audit, summary, write_json


ANGLES = [90, 150, 210, 270, 330]
BOUNDARIES = ["DD", "NN", "DN", "ND"]
K = 6


def fundamental(boundary: str, omega: float) -> float:
    return math.pi / omega if boundary in {"DD", "NN"} else math.pi / (2 * omega)


class WedgeMSN(torch.nn.Module):
    def __init__(self, boundary: str, omega: float, seed: int, adaptive_init: bool):
        super().__init__()
        self.boundary = boundary
        target = fundamental(boundary, omega)
        generator = torch.Generator().manual_seed(seed)
        if adaptive_init:
            self.lower, self.upper = 0.3 * target, 2.5 * target
            initial_mu = (
                torch.rand(K, generator=generator, dtype=torch.float32)
                * (self.upper - self.lower)
                + self.lower
            )
            initial_mu[0] = 0.98 * target
        else:
            self.lower, self.upper = 0.1, 3.0
            initial_mu = (
                torch.rand(K, generator=generator, dtype=torch.float32)
                * (self.upper - self.lower)
                + self.lower
            )
            initial_mu += torch.randn(K, generator=generator, dtype=torch.float32) * 0.1
        initial_c = torch.randn(K, generator=generator, dtype=torch.float32) * 0.1
        self.mu = torch.nn.Parameter(initial_mu)
        self.c = torch.nn.Parameter(initial_c)

    def angular(self, theta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        phase = theta[:, None] * self.mu[None, :]
        if self.boundary in {"DD", "DN"}:
            return torch.sin(phase), self.mu[None, :] * torch.cos(phase)
        return torch.cos(phase), -self.mu[None, :] * torch.sin(phase)

    def forward(self, r: torch.Tensor, theta: torch.Tensor) -> torch.Tensor:
        angular, _ = self.angular(theta)
        radial = r[:, None].clamp_min(1e-12) ** self.mu[None, :]
        return (radial * angular * self.c[None, :]).sum(dim=1)

    def far_edge(self, r: torch.Tensor, omega: float) -> torch.Tensor:
        theta = torch.full_like(r, omega)
        angular, derivative = self.angular(theta)
        radial = r[:, None].clamp_min(1e-12) ** self.mu[None, :]
        basis = angular if self.boundary in {"DD", "ND"} else derivative
        return (radial * basis * self.c[None, :]).sum(dim=1)

    def quantization(self, omega: float) -> torch.Tensor:
        phase = self.mu * omega
        residual = torch.sin(phase) if self.boundary in {"DD", "NN"} else torch.cos(phase)
        return (self.c.abs() * residual.square()).sum()

    def dominant(self) -> tuple[float, float]:
        index = int(torch.argmax(self.c.detach().abs()).item())
        return float(self.mu.detach()[index]), float(self.c.detach()[index])


def train_one(
    boundary: str,
    angle: int,
    seed: int,
    steps: int,
    method: str,
) -> dict[str, object]:
    use_constraint = method == "constraint_adaptive"
    adaptive_init = method in {"constraint_adaptive", "naive_matched_adaptive"}
    deterministic(seed + angle * 10 + BOUNDARIES.index(boundary))
    omega = math.radians(angle)
    target = fundamental(boundary, omega)
    model = WedgeMSN(boundary, omega, seed, adaptive_init)
    generator = torch.Generator().manual_seed(seed + angle * 1000 + BOUNDARIES.index(boundary))
    edge_r = torch.rand(150, generator=generator, dtype=torch.float32) ** 2
    arc_r = torch.ones(300, dtype=torch.float32)
    arc_theta = torch.rand(300, generator=generator, dtype=torch.float32) * omega
    arc_target = (
        torch.sin(target * arc_theta)
        if boundary in {"DD", "DN"}
        else torch.cos(target * arc_theta)
    )
    optimizer = torch.optim.Adam(
        [
            {"params": [model.mu], "lr": 5e-4},
            {"params": [model.c], "lr": 1e-2},
        ]
    )
    for step in range(1, steps + 1):
        optimizer.zero_grad(set_to_none=True)
        data_loss = (model(arc_r, arc_theta) - arc_target).square().mean()
        edge_loss = model.far_edge(edge_r, omega).square().mean()
        loss = 100.0 * (data_loss + edge_loss)
        if use_constraint and step > 1000:
            ramp = min(1.0, (step - 1000) / 1500)
            loss = loss + ramp * model.quantization(omega)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        with torch.no_grad():
            model.mu.clamp_(model.lower, model.upper)
    mu, coefficient = model.dominant()
    phase = mu * omega
    violation = (
        math.sin(phase) ** 2
        if boundary in {"DD", "NN"}
        else math.cos(phase) ** 2
    )
    return {
        "method": method,
        "angle_degrees": angle,
        "boundary": boundary,
        "seed": seed,
        "target_mu": target,
        "dominant_mu": mu,
        "dominant_coefficient": coefficient,
        "relative_error_pct": abs(mu - target) / target * 100,
        "constraint_violation": violation,
        "adaptive_init": adaptive_init,
    }


def aggregate(rows: list[dict[str, object]], method: str) -> dict[str, object]:
    selected = [row for row in rows if row["method"] == method]
    errors = [float(row["relative_error_pct"]) for row in selected]
    violations = [float(row["constraint_violation"]) for row in selected]
    return {
        "method": method,
        "experiments": len(selected),
        "success_pct": 100 * sum(error < 5 for error in errors) / len(errors),
        "error_pct": summary(errors),
        "constraint_violation": summary(violations),
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    methods = ["constraint_adaptive", "naive_default", "naive_matched_adaptive"]
    rows = [
        train_one(boundary, angle, args.seed, args.steps, method)
        for method, angle, boundary in itertools.product(methods, ANGLES, BOUNDARIES)
    ]
    aggregates = {method: aggregate(rows, method) for method in methods}
    constrained = aggregates["constraint_adaptive"]
    default_naive = aggregates["naive_default"]
    matched_naive = aggregates["naive_matched_adaptive"]
    return {
        "paper_id": "PVaFEuNnsD",
        "source_pins": source_pin_audit(),
        "config": {
            "K": K,
            "steps": args.steps,
            "warmup": 1000,
            "ramp": 1500,
            "eta_mu": 5e-4,
            "eta_c": 1e-2,
            "angles": ANGLES,
            "boundaries": BOUNDARIES,
            "scored_paper_package_experiments": 40,
            "matched_initialization_control_experiments": 20,
        },
        "aggregates": aggregates,
        "rows": rows,
        "assessment": {
            "constraint_100pct_success": constrained["success_pct"] == 100.0,
            "constraint_close_to_reported_0_022_mean": abs(
                float(constrained["error_pct"]["mean"]) - 0.022
            )
            <= 0.05,
            "default_naive_close_to_reported_55pct": abs(
                float(default_naive["success_pct"]) - 55.0
            )
            <= 10.0,
            "default_naive_close_to_reported_5_96_mean": abs(
                float(default_naive["error_pct"]["mean"]) - 5.96
            )
            <= 2.0,
            "matched_naive_falsifies_constraint_only_attribution": (
                float(matched_naive["success_pct"]) == 100.0
                and float(matched_naive["error_pct"]["mean"]) < 1.0
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/wedge.json")
    args = parser.parse_args()
    payload = run(args)
    write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
