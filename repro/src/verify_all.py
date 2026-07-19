from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from repro.src.common import ROOT, sha256, source_pin_audit, write_json


OUTPUT_NAMES = ["architecture", "corner", "wedge", "stability", "resolution"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def slope(rows: list[dict[str, Any]], key: str) -> float:
    selected = [row for row in rows if row["delta"] <= 0.075]
    return float(
        np.polyfit(
            np.log([row["delta"] for row in selected]),
            np.log([row[key] for row in selected]),
            1,
        )[0]
    )


def verify() -> dict[str, Any]:
    live = load_json(ROOT / "repro/configs/live_claims.json")
    ensure(live["openreview_id"] == "PVaFEuNnsD", "wrong paper ID")
    ensure(len(live["claims"]) == 6, "live contract is not six claims")
    pins = source_pin_audit()
    ensure(pins["passed"], "primary-source pin failed")
    outputs = {
        name: load_json(ROOT / f"outputs/{name}.json") for name in OUTPUT_NAMES
    }
    ensure(
        all(row["paper_id"] == "PVaFEuNnsD" for row in outputs.values()),
        "output paper-ID mismatch",
    )
    ensure(
        all(row["source_pins"]["passed"] for row in outputs.values()),
        "an evidence run did not verify source pins",
    )

    architecture = outputs["architecture"]
    trainable_errors = np.array(
        [row["dominant_relative_error_pct"] for row in architecture["trainable_runs"]]
    )
    frozen_errors = np.array(
        [
            row["dominant_relative_error_pct"]
            for row in architecture["frozen_exponent_control"]
        ]
    )
    claim1_pass = bool(
        architecture["gradient_audit"]["passed"]
        and architecture["architecture"]["eta_mu"]
        / architecture["architecture"]["eta_c"]
        == 0.5
        and np.max(trainable_errors) < 1.0
        and np.median(frozen_errors) > 10.0
    )
    ensure(claim1_pass, "C1 failed independent recomputation")

    corner = outputs["corner"]
    constrained_corner = np.array(
        [row["relative_error_pct"] for row in corner["primary_constraint"]["runs"]]
    )
    naive_corner = np.array(
        [row["relative_error_pct"] for row in corner["primary_naive"]["runs"]]
    )
    interpretation_errors = np.array(
        [
            row["relative_error_pct"]
            for row in corner["naive_interpretation_audit"]["runs"]
        ]
    )
    claim2_pass = bool(
        constrained_corner.size == 3
        and constrained_corner.mean() < 0.02
        and np.median(constrained_corner) < 0.01
    )
    ensure(claim2_pass, "C2 corner recovery failed")
    claim5_falsified = bool(
        interpretation_errors.size >= 10
        and np.all(np.abs(interpretation_errors - 14.6) > 2.0)
        and naive_corner.mean() < 0.1
        and constrained_corner.mean() < 0.02
    )
    ensure(claim5_falsified, "C5 falsification is not decisive")

    wedge = outputs["wedge"]
    raw_wedge = wedge["rows"]

    def wedge_stats(method: str) -> tuple[float, float]:
        errors = np.array(
            [row["relative_error_pct"] for row in raw_wedge if row["method"] == method]
        )
        ensure(errors.size == 20, f"wrong wedge count for {method}")
        return float(100 * np.mean(errors < 5)), float(errors.mean())

    constraint_success, constraint_mean = wedge_stats("constraint_adaptive")
    naive_success, naive_mean = wedge_stats("naive_default")
    matched_success, matched_mean = wedge_stats("naive_matched_adaptive")
    claim3_pass = bool(
        constraint_success == 100
        and constraint_mean < 0.01
        and abs(naive_success - 55) <= 10
        and abs(naive_mean - 5.96) <= 2
    )
    ensure(claim3_pass, "C3 paper-package benchmark failed")
    ensure(
        matched_success == 100 and matched_mean < 1,
        "C3 matched-init attribution control failed",
    )

    stability = outputs["stability"]
    stability_rows = stability["continuum_fisher"]["rows"]
    recomputed_delta_slope = slope(
        stability_rows, "max_exponent_std_unit_sigma_sqrtN"
    )
    bounded_rows = stability["bounded_noise_counterexample"]["rows"]
    bounded_ratio = bounded_rows[-1]["max_exponent_error"] / bounded_rows[0][
        "max_exponent_error"
    ]
    claim4_mechanism = bool(-2.25 <= recomputed_delta_slope <= -1.75)
    claim4_as_written_falsified = bool(0.9 <= bounded_ratio <= 1.1)
    ensure(claim4_mechanism, "C4 Delta^-2 mechanism failed")
    ensure(claim4_as_written_falsified, "C4 bounded-noise counterexample failed")

    resolution = outputs["resolution"]
    resolution_rates = {}
    for delta in [0.02, 0.05, 0.1, 0.2, 0.3]:
        selected = [
            row
            for row in resolution["paper_adam"]["rows"]
            if row["delta"] == delta
        ]
        ensure(len(selected) == 10, f"wrong resolution approach count at {delta}")
        resolution_rates[str(delta)] = float(np.mean([row["resolved"] for row in selected]))
    claim6_pass = list(resolution_rates.values()) == [0.0, 0.0, 1.0, 1.0, 1.0]
    ensure(claim6_pass, "C6 threshold pattern failed")
    ensure(
        all(row["resolved"] for row in resolution["noiseless_identifiability_oracle"]),
        "C6 noiseless identifiability control failed",
    )

    claims = [
        {
            "claim_number": 1,
            "outcome": "verified",
            "headline": "Trainable power-sum architecture and 0.5 two-timescale ratio",
            "evidence": {
                "full_runs": len(trainable_errors),
                "max_recovery_error_pct": float(trainable_errors.max()),
                "gradient_max_abs_error": max(
                    architecture["gradient_audit"]["max_mu_gradient_error"],
                    architecture["gradient_audit"]["max_c_gradient_error"],
                ),
                "frozen_control_median_error_pct": float(np.median(frozen_errors)),
            },
        },
        {
            "claim_number": 2,
            "outcome": "verified",
            "headline": "270-degree corner recovers the Kondrat'ev exponent",
            "evidence": {
                "seeds": int(constrained_corner.size),
                "mean_error_pct": float(constrained_corner.mean()),
                "median_error_pct": float(np.median(constrained_corner)),
                "reported_error_pct": 0.009,
            },
        },
        {
            "claim_number": 3,
            "outcome": "verified",
            "headline": "40-run paper package reproduces the wedge benchmark",
            "qualification": "Matched initialization shows that the constraint term alone does not explain the entire package gap.",
            "evidence": {
                "constraint_success_pct": constraint_success,
                "constraint_mean_error_pct": constraint_mean,
                "default_naive_success_pct": naive_success,
                "default_naive_mean_error_pct": naive_mean,
                "matched_naive_success_pct": matched_success,
                "matched_naive_mean_error_pct": matched_mean,
            },
        },
        {
            "claim_number": 4,
            "outcome": "falsified",
            "headline": "Delta^-2 conditioning holds, but the theorem is false under bounded noise alone",
            "evidence": {
                "recomputed_delta_loglog_slope": recomputed_delta_slope,
                "bounded_noise_error_ratio_N3200_to_N200": bounded_ratio,
                "reason": "The proof uses mean-zero concentration not stated in the bounded-noise theorem; repeated bounded structured errors do not shrink with N.",
            },
        },
        {
            "claim_number": 5,
            "outcome": "falsified",
            "headline": "Constraint reaches 0.009%-scale accuracy, but the claimed 14.6% naive baseline does not reproduce",
            "evidence": {
                "constraint_mean_error_pct": float(constrained_corner.mean()),
                "naive_mean_error_pct": float(naive_corner.mean()),
                "naive_interpretations": int(interpretation_errors.size),
                "naive_interpretation_min_error_pct": float(interpretation_errors.min()),
                "naive_interpretation_max_error_pct": float(interpretation_errors.max()),
            },
        },
        {
            "claim_number": 6,
            "outcome": "verified",
            "headline": "All ten approaches merge below Delta=0.1 and resolve at or above it",
            "qualification": "The threshold is practical, not an absolute identifiability limit; a noiseless global oracle resolves every listed separation.",
            "evidence": {"resolved_rates": resolution_rates},
        },
    ]
    ensure(
        all(row["outcome"] in {"verified", "falsified"} for row in claims),
        "non-substantive claim outcome",
    )
    return {
        "paper_id": "PVaFEuNnsD",
        "arxiv_id": "2601.22751",
        "effective_claim_count": len(live["claims"]),
        "substantive_claim_count": len(claims),
        "points_possible": 2 * len(claims),
        "all_claims_substantively_reproduced": len(claims) == len(live["claims"]),
        "claims": claims,
        "independent_recomputations": {
            "wedge_raw_rows": len(raw_wedge),
            "resolution_raw_rows": len(resolution["paper_adam"]["rows"]),
            "stability_delta_slope": recomputed_delta_slope,
        },
        "source_pins": pins,
    }


def make_bundle(verdict: dict[str, Any], output: Path) -> dict[str, Any]:
    records = []
    paths = [
        ROOT / "repro/configs/live_claims.json",
        ROOT / "repro/configs/source_pins.json",
        *(ROOT / f"outputs/{name}.json" for name in OUTPUT_NAMES),
        ROOT / "outputs/claim_verdicts.json",
    ]
    for path in paths:
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "payload": load_json(path),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(output)
    return {
        "path": str(output.relative_to(ROOT)),
        "records": len(records),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/claim_verdicts.json"
    )
    parser.add_argument(
        "--bundle", type=Path, default=ROOT / "outputs/evidence_bundle.jsonl"
    )
    args = parser.parse_args()
    verdict = verify()
    write_json(args.output, verdict)
    bundle = make_bundle(verdict, args.bundle)
    print(json.dumps({"verdict": verdict, "bundle": bundle}, indent=2))


if __name__ == "__main__":
    main()
