from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]


def deterministic(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.use_deterministic_algorithms(True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def summary(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if array.size > 1 else 0.0,
        "median": float(np.median(array)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
    }


def source_pin_audit() -> dict[str, Any]:
    pins = json.loads((ROOT / "repro/configs/source_pins.json").read_text())
    checks = {}
    for name in ("source_tar", "tex"):
        row = pins[name]
        path = ROOT / row["path"]
        checks[name] = {
            "path": row["path"],
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "expected_bytes": row["bytes"],
            "sha256": sha256(path) if path.is_file() else None,
            "expected_sha256": row["sha256"],
        }
        checks[name]["passed"] = (
            checks[name]["exists"]
            and checks[name]["bytes"] == checks[name]["expected_bytes"]
            and checks[name]["sha256"] == checks[name]["expected_sha256"]
        )
    return {"checks": checks, "passed": all(row["passed"] for row in checks.values())}

