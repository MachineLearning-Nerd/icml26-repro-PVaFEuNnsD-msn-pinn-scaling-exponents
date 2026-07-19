# Methods


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_e2e7f36184af", "created_at": "2026-07-19T21:02:19+00:00", "title": "Clean-room protocol and provenance"}
-->
# Methods

- Primary source: arXiv `2601.22751`; the 1,699,287-byte source archive and extracted TeX are SHA-256 pinned.
- The paper says code is in its OpenReview supplement, but that endpoint returned HTTP 403 and no public author repository was found. This is a clean-room implementation.
- CPU only, PyTorch float32 for paper-faithful optimizer runs; float64/100-digit arithmetic for independent checks.
- Full commands: `run_architecture` (3×10k), `run_corner` (15k per arm), `run_wedge` (60×5k), `run_stability` (100 digits), and `run_resolution` (50×10k plus oracles).
- Final outcomes are recomputed from raw rows by `repro/src/verify_all.py`; summaries are not trusted as the verification oracle.
- The hash-bound JSONL bundle contains the exact live wording, source pins, all raw outputs, and final claim outcomes.


---
<!-- trackio-cell
{"type": "code", "id": "cell_c88c6903afca", "created_at": "2026-07-19T21:02:38+00:00", "title": "Run: uv (exit 0)", "command": ["uv", "run", "python", "-m", "repro.src.verify_all"], "exit_code": 0, "duration_s": 1.666}
-->
````bash
$ uv run python -m repro.src.verify_all
````

exit 0 · 1.7s


````output
{
  "verdict": {
    "paper_id": "PVaFEuNnsD",
    "arxiv_id": "2601.22751",
    "effective_claim_count": 6,
    "substantive_claim_count": 6,
    "points_possible": 12,
    "all_claims_substantively_reproduced": true,
    "claims": [
      {
        "claim_number": 1,
        "outcome": "verified",
        "headline": "Trainable power-sum architecture and 0.5 two-timescale ratio",
        "evidence": {
          "full_runs": 3,
          "max_recovery_error_pct": 0.6425886482718579,
          "gradient_max_abs_error": 1.0267342531733448e-11,
          "frozen_control_median_error_pct": 23.78917680087047
        }
      },
      {
        "claim_number": 2,
        "outcome": "verified",
        "headline": "270-degree corner recovers the Kondrat'ev exponent",
        "evidence": {
          "seeds": 3,
          "mean_error_pct": 0.011135141054791076,
          "median_error_pct": 0.003668665885930844,
          "reported_error_pct": 0.009
        }
      },
      {
        "claim_number": 3,
        "outcome": "verified",
        "headline": "40-run paper package reproduces the wedge benchmark",
        "qualification": "Matched initialization shows that the constraint term alone does not explain the entire package gap.",
        "evidence": {
          "constraint_success_pct": 100.0,
          "constraint_mean_error_pct": 0.0039896368980394765,
          "default_naive_success_pct": 65.0,
          "default_naive_mean_error_pct": 4.407574484745661,
          "matched_naive_success_pct": 100.0,
          "matched_naive_mean_error_pct": 0.6207009653250367
        }
      },
      {
        "claim_number": 4,
        "outcome": "falsified",
        "headline": "Delta^-2 conditioning holds, but the theorem is false under bounded noise alone",
        "evidence": {
          "recomputed_delta_loglog_slope": -1.9232043604946778,
          "bounded_noise_error_ratio_N3200_to_N200": 1.0000029534150818,
          "reason": "The proof uses mean-zero concentration not stated in the bounded-noise theorem; repeated bounded structured errors do not shrink with N."
        }
      },
      {
        "claim_number": 5,
        "outcome": "falsified",
        "headline": "Constraint reaches 0.009%-scale accuracy, but the claimed 14.6% naive baseline does not reproduce",
        "evidence": {
          "constraint_mean_error_pct": 0.011135141054791076,
          "naive_mean_error_pct": 0.041228532791132144,
          "naive_interpretations": 11,
          "naive_interpretation_min_error_pct": 0.00046060961091942687,
          "naive_interpretation_max_error_pct": 300.0000476837159
        }
      },
      {
        "claim_number": 6,
        "outcome": "verified",
        "headline": "All ten approaches merge below Delta=0.1 and resolve at or above it",
        "qualification": "The threshold is practical, not an absolute identifiability limit; a noiseless global oracle resolves every listed separation.",
        "evidence": {
          "resolved_rates": {
            "0.02": 0.0,
            "0.05": 0.0,
            "0.1": 1.0,
            "0.2": 1.0,
            "0.3": 1.0
          }
        }
      }
    ],
    "independent_recomputations": {
      "wedge_raw_rows": 60,
      "resolution_raw_rows": 50,
      "stability_delta_slope": -1.9232043604946778
    },
    "source_pins": {
      "checks": {
        "source_tar": {
          "path": "upstream/arxiv-2601.22751-source.tar",
          "exists": true,
          "bytes": 1699287,
          "expected_bytes": 1699287,
          "sha256": "25029ab7f42fdc9688c36c3fcba636a0956cb5fb07a8b85fac824268a6bf9462",
          "expected_sha256": "25029ab7f42fdc9688c36c3fcba636a0956cb5fb07a8b85fac824268a6bf9462",
          "passed": true
        },
        "tex": {
          "path": "upstream/msn_pinn_arxiv.tex",
          "exists": true,
          "bytes": 106039,
          "expected_bytes": 106039,
          "sha256": "f6f3d10a1e0c1a8a5a665cb91fdfe0726a481e38be920dd936ec065aef30dbc0",
          "expected_sha256": "f6f3d10a1e0c1a8a5a665cb91fdfe0726a481e38be920dd936ec065aef30dbc0",
          "passed": true
        }
      },
      "passed": true
    }
  },
  "bundle": {
    "path": "outputs/evidence_bundle.jsonl",
    "records": 8,
    "bytes": 85489,
    "sha256": "6d883ac73afcf42a3bcd836c631303f735db802d6fb62e999d4606ad8c020b43"
  }
}

````


---
<!-- trackio-cell
{"type": "code", "id": "cell_1d7c75d501fc", "created_at": "2026-07-19T21:04:52+00:00", "title": "Run: uv (exit 0)", "command": ["uv", "run", "python", "-m", "repro.src.verify_all"], "exit_code": 0, "duration_s": 1.659}
-->
````bash
$ uv run python -m repro.src.verify_all
````

exit 0 · 1.7s


````output
{
  "verdict": {
    "paper_id": "PVaFEuNnsD",
    "arxiv_id": "2601.22751",
    "effective_claim_count": 6,
    "substantive_claim_count": 6,
    "points_possible": 12,
    "all_claims_substantively_reproduced": true,
    "claims": [
      {
        "claim_number": 1,
        "outcome": "verified",
        "headline": "Trainable power-sum architecture and 0.5 two-timescale ratio",
        "evidence": {
          "full_runs": 3,
          "max_recovery_error_pct": 0.6425886482718579,
          "gradient_max_abs_error": 1.0267342531733448e-11,
          "frozen_control_median_error_pct": 23.78917680087047
        }
      },
      {
        "claim_number": 2,
        "outcome": "verified",
        "headline": "270-degree corner recovers the Kondrat'ev exponent",
        "evidence": {
          "seeds": 3,
          "mean_error_pct": 0.011135141054791076,
          "median_error_pct": 0.003668665885930844,
          "reported_error_pct": 0.009
        }
      },
      {
        "claim_number": 3,
        "outcome": "verified",
        "headline": "40-run paper package reproduces the wedge benchmark",
        "qualification": "Matched initialization shows that the constraint term alone does not explain the entire package gap.",
        "evidence": {
          "constraint_success_pct": 100.0,
          "constraint_mean_error_pct": 0.0039896368980394765,
          "default_naive_success_pct": 65.0,
          "default_naive_mean_error_pct": 4.407574484745661,
          "matched_naive_success_pct": 100.0,
          "matched_naive_mean_error_pct": 0.6207009653250367
        }
      },
      {
        "claim_number": 4,
        "outcome": "falsified",
        "headline": "Delta^-2 conditioning holds, but the theorem is false under bounded noise alone",
        "evidence": {
          "recomputed_delta_loglog_slope": -1.9232043604946778,
          "bounded_noise_error_ratio_N3200_to_N200": 1.0000029534150818,
          "reason": "The proof uses mean-zero concentration not stated in the bounded-noise theorem; repeated bounded structured errors do not shrink with N."
        }
      },
      {
        "claim_number": 5,
        "outcome": "falsified",
        "headline": "Constraint reaches 0.009%-scale accuracy, but the claimed 14.6% naive baseline does not reproduce",
        "evidence": {
          "constraint_mean_error_pct": 0.011135141054791076,
          "naive_mean_error_pct": 0.041228532791132144,
          "naive_interpretations": 11,
          "naive_interpretation_min_error_pct": 0.00046060961091942687,
          "naive_interpretation_max_error_pct": 300.0000476837159
        }
      },
      {
        "claim_number": 6,
        "outcome": "verified",
        "headline": "All ten approaches merge below Delta=0.1 and resolve at or above it",
        "qualification": "The threshold is practical, not an absolute identifiability limit; a noiseless global oracle resolves every listed separation.",
        "evidence": {
          "resolved_rates": {
            "0.02": 0.0,
            "0.05": 0.0,
            "0.1": 1.0,
            "0.2": 1.0,
            "0.3": 1.0
          }
        }
      }
    ],
    "independent_recomputations": {
      "wedge_raw_rows": 60,
      "resolution_raw_rows": 50,
      "stability_delta_slope": -1.9232043604946778
    },
    "source_pins": {
      "checks": {
        "source_tar": {
          "path": "upstream/arxiv-2601.22751-source.tar",
          "exists": true,
          "bytes": 1699287,
          "expected_bytes": 1699287,
          "sha256": "25029ab7f42fdc9688c36c3fcba636a0956cb5fb07a8b85fac824268a6bf9462",
          "expected_sha256": "25029ab7f42fdc9688c36c3fcba636a0956cb5fb07a8b85fac824268a6bf9462",
          "passed": true
        },
        "tex": {
          "path": "upstream/msn_pinn_arxiv.tex",
          "exists": true,
          "bytes": 106039,
          "expected_bytes": 106039,
          "sha256": "f6f3d10a1e0c1a8a5a665cb91fdfe0726a481e38be920dd936ec065aef30dbc0",
          "expected_sha256": "f6f3d10a1e0c1a8a5a665cb91fdfe0726a481e38be920dd936ec065aef30dbc0",
          "passed": true
        }
      },
      "passed": true
    }
  },
  "bundle": {
    "path": "outputs/evidence_bundle.jsonl",
    "records": 8,
    "bytes": 85582,
    "sha256": "63822870e91b03c3898eb8fd14acf8dc49a32fc82449460122499ace6b8c635a"
  }
}

````


---
<!-- trackio-cell
{"type": "artifact", "id": "cell_765971901d6b", "created_at": "2026-07-19T21:04:52+00:00", "title": "Artifact: evidence_bundle.jsonl", "path": "outputs/evidence_bundle.jsonl", "size": 85582, "artifact_type": "dataset", "auto": true}
-->
**📦 Artifact** `outputs/evidence_bundle.jsonl` · dataset · 85.6 kB

https://huggingface.co/buckets/DineshAI/PVaFEuNnsD-artifacts#logbook-files/outputs/evidence_bundle.jsonl
