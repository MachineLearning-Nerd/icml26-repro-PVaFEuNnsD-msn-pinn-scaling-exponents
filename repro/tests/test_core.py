import json
import math

import numpy as np
import pytest
import torch

from repro.src.common import ROOT, source_pin_audit
from repro.src.run_corner import OMEGA, TRUE_ALPHA, laplacian_finite_difference
from repro.src.run_stability import continuum_fisher, moment
from repro.src.run_wedge import fundamental


def test_source_pins_are_exact():
    assert source_pin_audit()["passed"]


def test_corner_basis_is_harmonic_independently():
    values = [
        abs(laplacian_finite_difference(mu, r, theta, 1e-4))
        for mu in (0.37, 2 / 3, 1.21)
        for r in (0.2, 0.5, 0.8)
        for theta in (0.4, 1.3, 3.1)
    ]
    assert max(values) < 4e-7


def test_corner_quantization_and_wrong_angle_control():
    assert abs(math.sin(TRUE_ALPHA * OMEGA)) < 1e-14
    wrong_omega = math.radians(240)
    assert abs(math.sin(TRUE_ALPHA * wrong_omega)) > 0.3


@pytest.mark.parametrize(
    ("boundary", "angle", "expected"),
    [
        ("DD", 270, 2 / 3),
        ("NN", 90, 2.0),
        ("DN", 270, 1 / 3),
        ("ND", 150, 0.6),
    ],
)
def test_wedge_fundamentals(boundary, angle, expected):
    assert fundamental(boundary, math.radians(angle)) == pytest.approx(expected)


def test_mixed_boundary_wrong_quantization_control():
    omega = math.radians(270)
    mu = fundamental("DN", omega)
    assert abs(math.cos(mu * omega)) < 1e-14
    assert abs(math.sin(mu * omega)) > 0.99


def test_exact_log_moment_formula_against_quadrature():
    import scipy.integrate

    for power in (0.4, 1.0, 2.3):
        for degree in range(4):
            numerical = scipy.integrate.quad(
                lambda x: x**power * math.log(x) ** degree, 0, 1
            )[0]
            assert float(moment(power, degree)) == pytest.approx(numerical, abs=1e-10)


def test_full_fisher_is_positive_definite_for_distinct_exponents():
    eigenvalues = np.linalg.eigvalsh(np.asarray(continuum_fisher(0.1).tolist(), dtype=float))
    assert eigenvalues.min() > 0


def load_output(name):
    path = ROOT / f"outputs/{name}.json"
    assert path.is_file(), f"missing full-scale output {path}"
    return json.loads(path.read_text())


def test_claim1_full_output():
    data = load_output("architecture")
    assert data["source_pins"]["passed"]
    assert data["gradient_audit"]["passed"]
    assert data["assessment"]["both_parameter_blocks_move"]
    assert data["architecture"]["eta_mu_over_eta_c"] == 0.5
    assert data["trainable_error_pct"]["maximum"] < 1.0
    assert data["frozen_error_pct"]["median"] > 10.0


def test_claim4_full_output_and_bounded_noise_control():
    data = load_output("stability")
    fisher = data["continuum_fisher"]
    assert fisher["delta_minus_two_supported"]
    assert -2.25 < fisher["small_delta_exponent_std_loglog_slope"] < -1.75
    control = data["bounded_noise_counterexample"]
    assert control["n_minus_half_without_mean_zero_rejected"]
    assert control["error_ratio_last_to_first"] == pytest.approx(1.0, rel=1e-4)


def test_claim2_corner_recovery_full_output():
    data = load_output("corner")
    constrained = data["primary_constraint"]
    assert constrained["error_pct"]["n"] == 3
    assert constrained["error_pct"]["mean"] < 0.02
    assert constrained["error_pct"]["median"] < 0.01
    assert data["headline_assessment"]["constraint_recovery_close_to_0_009_pct"]
    assert data["independent_harmonicity_check"]["max_abs_laplacian"] < 4e-7


def test_claim5_naive_comparison_is_substantively_falsified():
    data = load_output("corner")
    audit = data["naive_interpretation_audit"]
    assert audit["predeclared_count"] >= 10
    assert not audit["reported_14_6_reproduced_within_2pp"]
    assert data["primary_naive"]["error_pct"]["mean"] < 0.1
    assert data["primary_constraint"]["error_pct"]["mean"] < 0.02
    delayed = next(
        row
        for row in data["constraint_form_audit"]
        if row["protocol"] == "figure_delayed_epoch_2000"
    )
    assert delayed["relative_error_pct"] == pytest.approx(0.009, abs=0.003)


def test_claim3_full_wedge_benchmark_and_matched_control():
    data = load_output("wedge")
    assert data["config"]["scored_paper_package_experiments"] == 40
    assert data["config"]["matched_initialization_control_experiments"] == 20
    constrained = data["aggregates"]["constraint_adaptive"]
    naive = data["aggregates"]["naive_default"]
    matched = data["aggregates"]["naive_matched_adaptive"]
    assert constrained["experiments"] == naive["experiments"] == matched["experiments"] == 20
    assert constrained["success_pct"] == 100
    assert constrained["error_pct"]["mean"] < 0.01
    assert naive["success_pct"] == pytest.approx(55, abs=10)
    assert naive["error_pct"]["mean"] == pytest.approx(5.96, abs=2)
    assert matched["success_pct"] == 100
    assert matched["error_pct"]["mean"] < 1
    assert data["assessment"]["matched_naive_falsifies_constraint_only_attribution"]


def test_claim6_full_output():
    data = load_output("resolution")
    assessment = data["assessment"]
    assert assessment["all_at_or_above_0_1_majority_resolved"]
    assert assessment["all_below_0_1_majority_unresolved"]
    assert assessment["absolute_rayleigh_limit_rejected_by_noiseless_oracle"]
    aggregates = data["paper_adam"]["aggregates"]
    assert sum(row["approaches"] for row in aggregates) == 50
    assert [row["resolved_rate"] for row in aggregates] == [0, 0, 1, 1, 1]
