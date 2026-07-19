from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from repro.src.common import ROOT, sha256, source_pin_audit, write_json


PAPER = "PVaFEuNnsD"
BUNDLE = ROOT / "outputs/evidence_bundle.jsonl"
ANCHORED_URL = "https://huggingface.co/spaces/ICML-2026-agent-repro/challenge/resolve/main/claims_anchored.json"


def run(arguments: list[str]) -> str:
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("$ " + " ".join(arguments))
    print(completed.stdout, end="")
    if completed.returncode:
        raise RuntimeError(f"command failed with exit {completed.returncode}")
    return completed.stdout


def refresh_live_claims() -> list[str]:
    request = urllib.request.Request(
        ANCHORED_URL, headers={"User-Agent": "icml26-reproduction-gate/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        remote = json.load(response)
    local = json.loads((ROOT / "repro/configs/live_claims.json").read_text())
    remote_claims = [row["text"] for row in remote[PAPER]]
    if remote_claims != local["claims"] or len(remote_claims) != 6:
        raise RuntimeError("live anchored claim wording/count drifted")
    return remote_claims


def validate_bundle() -> dict[str, Any]:
    records = [json.loads(line) for line in BUNDLE.read_text().splitlines() if line]
    expected = [
        "repro/configs/live_claims.json",
        "repro/configs/source_pins.json",
        "outputs/architecture.json",
        "outputs/corner.json",
        "outputs/wedge.json",
        "outputs/stability.json",
        "outputs/resolution.json",
        "outputs/claim_verdicts.json",
    ]
    if [row["path"] for row in records] != expected:
        raise RuntimeError("evidence bundle path order mismatch")
    for record in records:
        path = ROOT / record["path"]
        if not path.is_file():
            raise RuntimeError(f"bundle source missing: {record['path']}")
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise RuntimeError(f"bundle source hash/size mismatch: {record['path']}")
        if json.loads(path.read_text()) != record["payload"]:
            raise RuntimeError(f"bundle embedded payload mismatch: {record['path']}")
    return {
        "records": len(records),
        "bytes": BUNDLE.stat().st_size,
        "sha256": sha256(BUNDLE),
    }


def validate_trackio() -> dict[str, Any]:
    metadata = json.loads((ROOT / ".trackio/metadata.json").read_text())
    if metadata.get("space_id") != f"DineshAI/{PAPER}":
        raise RuntimeError("wrong Trackio Space target")
    if set(metadata.get("tags", [])) != {"icml2026-repro", f"paper-{PAPER}"}:
        raise RuntimeError("required Trackio tags missing")
    matches = [
        row
        for row in metadata.get("local_path_artifacts", [])
        if row.get("path") == "outputs/evidence_bundle.jsonl"
    ]
    if len(matches) != 1:
        raise RuntimeError("evidence bundle is not registered exactly once")
    artifact = matches[0]
    if artifact.get("artifact_type") != "dataset" or artifact.get("size") != BUNDLE.stat().st_size:
        raise RuntimeError("registered Trackio artifact type/size mismatch")
    conclusion = ROOT / ".trackio/logbook/pages/conclusion/page.md"
    if not conclusion.is_file() or f"FULL_GATE_READY: {PAPER}" not in conclusion.read_text():
        raise RuntimeError("Conclusion marker missing")
    conclusion_rows = [
        json.loads(line)
        for line in conclusion.read_text().splitlines()
        if line.startswith("{")
    ]
    if sum(bool(row.get("pinned")) for row in conclusion_rows) != 1:
        raise RuntimeError("Conclusion must contain exactly one pinned cell")
    return {
        "space_id": metadata["space_id"],
        "tags": metadata["tags"],
        "registered_bundle_bytes": artifact["size"],
        "pinned_conclusion_cells": 1,
    }


def hygiene() -> dict[str, Any]:
    absolute_prefix = "/" + "home" + "/dineshai/"
    secret = re.compile(
        r"(?i)(hf_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|api[_-]?key\s*[:=]\s*['\"][^'\"]+)"
    )
    suffixes = {".py", ".sh", ".json", ".jsonl", ".md", ".txt", ".toml", ".yaml", ".yml"}
    absolute_hits, secret_hits, env_files = [], [], []
    scanned = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part in {".git", ".venv", "__pycache__", "upstream"} for part in path.parts
        ):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == ".trackio/metadata.json" or relative.endswith((".sync.log", ".sync_lock")):
            continue
        if path.name == ".env" or path.name.startswith(".env."):
            env_files.append(relative)
        if path.suffix.lower() not in suffixes:
            continue
        scanned += 1
        text = path.read_text(errors="replace")
        if absolute_prefix in text:
            absolute_hits.append(relative)
        if secret.search(text):
            secret_hits.append(relative)
    if absolute_hits or secret_hits or env_files:
        raise RuntimeError(
            json.dumps(
                {
                    "absolute_path_hits": absolute_hits,
                    "secret_hits": secret_hits,
                    "env_files": env_files,
                },
                sort_keys=True,
            )
        )
    return {
        "text_files_scanned": scanned,
        "absolute_path_hits": [],
        "secret_hits": [],
        "env_files": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/PUBLICATION_GATE_PASSED.json"
    )
    args = parser.parse_args()
    claims = refresh_live_claims()
    if not source_pin_audit()["passed"]:
        raise RuntimeError("source pin failed")
    run(["uv", "run", "python", "-m", "repro.src.verify_all"])
    run(["uv", "run", "pytest", "-q"])
    verdict = json.loads((ROOT / "outputs/claim_verdicts.json").read_text())
    if (
        verdict["effective_claim_count"] != 6
        or verdict["substantive_claim_count"] != 6
        or not verdict["all_claims_substantively_reproduced"]
        or any(row["outcome"] not in {"verified", "falsified"} for row in verdict["claims"])
    ):
        raise RuntimeError("claim verdict is not complete/substantive")
    bundle = validate_bundle()
    trackio = validate_trackio()
    gate = {
        "paper": PAPER,
        "arxiv_id": "2601.22751",
        "live_claim_source": ANCHORED_URL,
        "live_claim_count": len(claims),
        "substantive_claim_count": verdict["substantive_claim_count"],
        "verified_claims": sum(row["outcome"] == "verified" for row in verdict["claims"]),
        "falsified_claims": sum(row["outcome"] == "falsified" for row in verdict["claims"]),
        "maximum_points": verdict["points_possible"],
        "tests_passed": True,
        "publication_gate_passed": True,
        "bundle": bundle,
        "trackio": trackio,
        "hygiene": hygiene(),
    }
    write_json(args.output, gate)
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
