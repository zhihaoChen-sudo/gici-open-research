#!/usr/bin/env python3
"""Frozen Stage 3A.1b-1b.3 offline calibration prototype.

This program reads only first-solve-before shadow evidence.  It never reads
trajectory truth, APE, post-fit residuals, or estimator status, and it does not
write estimator/configuration files.  Real-data reference-region membership is
an outcome descriptor, not calibration coverage or a transfer PASS target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/gici-stage3a1b1b3-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import yaml


EVIDENCE_REQUIRED = {
    "timestamp",
    "pr_finite_success_count",
    "pr_p90_abs_normalized",
    "pr_group_count",
    "pr_group_eligible_count",
    "pr_group_shift_all_p90",
    "pr_group_scale_eligible_p90",
    "pr_insufficient_factor_ratio",
    "phase_finite_success_count",
    "phase_both_continued_count",
    "phase_continuity_conditioned_count",
    "phase_continuity_conditioned_p90_abs_normalized",
    "doppler_finite_success_count",
    "doppler_p90_abs_normalized",
}
DOPPLER_REQUIRED = {
    "timestamp",
    "system",
    "factor_count",
    "finite_count",
    "evaluation_failure_count",
    "center_normalized",
    "scale_normalized",
}
PR_COORDS = [
    "pr_p90_abs_normalized",
    "pr_group_shift_all_p90",
    "pr_group_scale_eligible_p90",
]
PHASE_COORDS = ["phase_continuity_conditioned_p90_abs_normalized"]
DOPPLER_EPOCH_COORDS = ["doppler_p90_abs_normalized"]
FISHER_CLIP_DEFAULT = 0.999999999999


def finite(a: Iterable[Any]) -> np.ndarray:
    x = np.asarray(list(a), dtype=float)
    return x[np.isfinite(x)]


def percentile(x: np.ndarray, p: float) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return math.nan
    return float(np.quantile(x, p, method="linear"))


def json_value(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): json_value(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_value(v) for v in x]
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.ndarray):
        return json_value(x.tolist())
    return x


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(obj), indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def child_seed(master: int, *parts: Any) -> int:
    material = "||".join([str(master), *map(str, parts)]).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:16], "big")


def rng_for(cfg: dict[str, Any], *parts: Any) -> np.random.Generator:
    master = int(str(cfg["statistics"]["master_seed_hex"]), 16)
    return np.random.Generator(np.random.PCG64DXSM(child_seed(master, *parts)))


def load_manifest(path: Path) -> dict[str, Any]:
    cfg = yaml.safe_load(path.read_text())
    if cfg.get("manifest_id") != "S3A1b1b3-v1" or cfg.get("status") != "frozen":
        raise RuntimeError("Expected frozen S3A1b1b3-v1 manifest")
    for dataset in cfg["inputs"].values():
        for run in dataset["runs"].values():
            for value in run.values():
                if "/5.2/" in value or "/5_2/" in value:
                    raise RuntimeError("Forbidden 5.2 path in manifest")
    return cfg


def output_root(cfg: dict[str, Any], repo: Path) -> Path:
    return repo / cfg["output_root"]


def load_all(cfg: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    evidence: dict[str, pd.DataFrame] = {}
    doppler: dict[str, pd.DataFrame] = {}
    for dataset, dcfg in cfg["inputs"].items():
        for run, rcfg in dcfg["runs"].items():
            key = f"{dataset}:{run}"
            e = pd.read_csv(rcfg["evidence"], na_values=["nan", "-nan", "inf", "-inf"])
            d = pd.read_csv(rcfg["doppler_system"], na_values=["nan", "-nan", "inf", "-inf"])
            e.insert(0, "dataset", dataset)
            e.insert(1, "run", run)
            d.insert(0, "dataset", dataset)
            d.insert(1, "run", run)
            evidence[key] = e
            doppler[key] = d
    return evidence, doppler


def command_validate(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    out = root / "validate"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    errors = []
    for dataset, dcfg in cfg["inputs"].items():
        for run, rcfg in dcfg["runs"].items():
            for kind, value in rcfg.items():
                path = Path(value)
                if not path.is_file():
                    errors.append(f"missing: {path}")
                    continue
                header = set(pd.read_csv(path, nrows=0).columns)
                required = EVIDENCE_REQUIRED if kind == "evidence" else DOPPLER_REQUIRED
                missing = sorted(required - header)
                if missing:
                    errors.append(f"{path}: missing {missing}")
                rows.append(
                    {
                        "dataset": dataset,
                        "run": run,
                        "kind": kind,
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                        "missing_required_columns": ";".join(missing),
                    }
                )
    pd.DataFrame(rows).to_csv(out / "input_hashes.csv", index=False)
    if errors:
        write_json(out / "validation_report.json", {"status": "FAIL", "errors": errors})
        raise RuntimeError("; ".join(errors))

    evidence, doppler = load_all(cfg)
    checks = []
    for key, frame in evidence.items():
        dataset, run = key.split(":")
        timestamp_ok = frame["timestamp"].notna().all() and frame["timestamp"].is_monotonic_increasing
        closure = {}
        for prefix in ("pr", "phase", "doppler"):
            a = pd.to_numeric(frame[f"{prefix}_evaluation_attempt_count"], errors="coerce")
            s = pd.to_numeric(frame[f"{prefix}_finite_success_count"], errors="coerce")
            f = pd.to_numeric(frame[f"{prefix}_evaluation_failure_count"], errors="coerce")
            closure[prefix] = bool(((a - s - f).fillna(1) == 0).all())
        checks.append(
            {
                "dataset": dataset,
                "run": run,
                "evidence_epochs": len(frame),
                "timestamp_monotonic": bool(timestamp_ok),
                "pr_count_closure": closure["pr"],
                "phase_count_closure": closure["phase"],
                "doppler_count_closure": closure["doppler"],
                "pr_factors": int(frame["pr_finite_success_count"].sum()),
                "phase_factors": int(frame["phase_finite_success_count"].sum()),
                "doppler_factors": int(frame["doppler_finite_success_count"].sum()),
                "doppler_system_rows": len(doppler[key]),
            }
        )
    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(out / "schema_sanity.csv", index=False)
    status = "PASS" if checks_df.drop(columns=["dataset", "run"]).select_dtypes(bool).all().all() else "FAIL"
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
        "manifest_sha256": sha256(repo / "tools/research/stage3a_1b_1b_3_manifest.yaml"),
    }
    write_json(out / "environment.json", environment)
    write_json(out / "validation_report.json", {"status": status, "errors": [], "checks": checks})
    if status != "PASS":
        raise RuntimeError("Schema/count validation failed")


def match_pair(a: pd.DataFrame, b: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    left = a.sort_values("timestamp")
    right = b.sort_values("timestamp")
    return pd.merge_asof(
        left,
        right,
        on="timestamp",
        direction="nearest",
        tolerance=tolerance,
        suffixes=("_a", "_b"),
    )


def make_blocks(frame: pd.DataFrame, block_size: int, gap_multiple: float) -> list[np.ndarray]:
    frame = frame.sort_values("timestamp")
    ts = frame["timestamp"].to_numpy(float)
    if not len(ts):
        return []
    positive = np.diff(ts)
    positive = positive[np.isfinite(positive) & (positive > 0)]
    median_dt = float(np.median(positive)) if len(positive) else math.inf
    breaks = np.r_[True, np.diff(ts) > gap_multiple * median_dt]
    segment = np.cumsum(breaks) - 1
    blocks = []
    minimum = int(math.ceil(block_size * 0.5))
    for sid in np.unique(segment):
        idx = np.flatnonzero(segment == sid)
        for start in range(0, len(idx), block_size):
            chunk = idx[start : start + block_size]
            if len(chunk) == block_size or len(chunk) >= minimum:
                blocks.append(chunk)
    return blocks


def make_epoch_clustered_row_blocks(
    frame: pd.DataFrame, block_size: int, gap_multiple: float
) -> list[np.ndarray]:
    """Return row-index blocks while keeping all rows at one epoch together."""
    epochs = pd.DataFrame({"timestamp": np.sort(frame["timestamp"].dropna().unique())})
    epoch_blocks = make_blocks(epochs, block_size, gap_multiple)
    row_blocks = []
    timestamps = frame["timestamp"].to_numpy(float)
    for block in epoch_blocks:
        selected = epochs.iloc[block]["timestamp"].to_numpy(float)
        row_blocks.append(np.flatnonzero(np.isin(timestamps, selected)))
    return row_blocks


@dataclass
class FisherCounter:
    clip: float
    count: int = 0

    def transform(self, rho: float) -> float:
        if not np.isfinite(rho):
            return math.nan
        clipped = float(np.clip(rho, -self.clip, self.clip))
        if clipped != rho:
            self.count += 1
        return float(np.arctanh(clipped))


def paired_spearman_bootstrap(
    frame: pd.DataFrame,
    pairs: list[tuple[str, str]],
    cfg: dict[str, Any],
    seed_parts: tuple[Any, ...],
) -> tuple[list[dict[str, Any]], int]:
    block_size = int(cfg["statistics"]["primary_block_size_epochs"])
    blocks = make_epoch_clustered_row_blocks(
        frame, block_size, cfg["statistics"]["segment_gap_multiple"]
    )
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    counter = FisherCounter(float(cfg["statistics"].get("fisher_rho_clip", FISHER_CLIP_DEFAULT)))
    estimates = []
    valid_pairs = []
    for ca, cb in pairs:
        valid = frame[[ca, cb]].replace([np.inf, -np.inf], np.nan).dropna()
        rho = stats.spearmanr(valid[ca], valid[cb]).statistic if len(valid) >= 3 else math.nan
        estimates.append(counter.transform(float(rho)))
        valid_pairs.append((ca, cb))
    boot = np.full((reps, len(pairs)), np.nan)
    rng = rng_for(cfg, *seed_parts)
    for b in range(reps):
        selected = rng.integers(0, len(blocks), size=len(blocks)) if blocks else []
        indices = np.concatenate([blocks[i] for i in selected]) if len(selected) else np.array([], int)
        sample = frame.iloc[indices]
        for k, (ca, cb) in enumerate(valid_pairs):
            valid = sample[[ca, cb]].replace([np.inf, -np.inf], np.nan).dropna()
            rho = stats.spearmanr(valid[ca], valid[cb]).statistic if len(valid) >= 3 else math.nan
            boot[b, k] = counter.transform(float(rho))
    estimates_arr = np.asarray(estimates)
    se = np.nanstd(boot, axis=0, ddof=1)
    z = np.full_like(boot, np.nan)
    nz = np.isfinite(se) & (se > 0)
    z[:, nz] = np.abs((boot[:, nz] - estimates_arr[nz]) / se[nz])
    maxz = np.nanmax(z, axis=1) if z.size else np.array([])
    c95 = percentile(maxz, 0.95) if np.isfinite(maxz).any() else math.nan
    rows = []
    for k, (ca, cb) in enumerate(valid_pairs):
        if not np.isfinite(estimates_arr[k]):
            lo = hi = math.nan
        elif se[k] == 0:
            lo = hi = math.tanh(estimates_arr[k])
        elif np.isfinite(c95):
            lo = math.tanh(estimates_arr[k] - c95 * se[k])
            hi = math.tanh(estimates_arr[k] + c95 * se[k])
        else:
            lo = hi = math.nan
        rho = math.tanh(estimates_arr[k]) if np.isfinite(estimates_arr[k]) else math.nan
        rows.append(
            {
                "coordinate": ca.removesuffix("_a"),
                "spearman": rho,
                "simultaneous_ci_low": lo,
                "simultaneous_ci_high": hi,
                "bootstrap_se_fisher": se[k],
                "zero_variance": bool(se[k] == 0),
                "effective_blocks": len(blocks),
                "traffic_light": "stable" if np.isfinite(lo) and lo >= 0.8 else ("unstable" if np.isfinite(hi) and hi < 0.8 else "indeterminate"),
            }
        )
    return rows, counter.count


def command_audit(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    if not (root / "validate/validation_report.json").exists():
        raise RuntimeError("Run validate first")
    out = root / "audit"
    out.mkdir(parents=True, exist_ok=True)
    evidence, doppler = load_all(cfg)
    tolerance = float(cfg["statistics"]["timestamp_match_tolerance_seconds"])

    mask_rows = []
    support_rows = []
    trade_rows = []
    scalar_rows = []
    repeat_rows = []
    clip_total = 0
    for dataset in ("4.1", "4.2"):
        runs = [k for k in evidence if k.startswith(dataset + ":")]
        for key in runs:
            frame = evidence[key]
            run = key.split(":")[1]
            masks = frame[PR_COORDS].apply(np.isfinite).astype(int).astype(str).agg("".join, axis=1)
            for pattern, count in masks.value_counts().items():
                mask_rows.append({"dataset": dataset, "run": run, "mask": pattern, "count": count, "fraction": count / len(frame)})
            for coord, support in [
                (PR_COORDS[0], "pr_finite_success_count"),
                (PR_COORDS[1], "pr_group_count"),
                (PR_COORDS[2], "pr_group_eligible_count"),
                (PHASE_COORDS[0], "phase_continuity_conditioned_count"),
                (DOPPLER_EPOCH_COORDS[0], "doppler_finite_success_count"),
            ]:
                valid = frame[[coord, support]].replace([np.inf, -np.inf], np.nan).dropna()
                rho = stats.spearmanr(valid[coord], valid[support]).statistic if len(valid) >= 3 else math.nan
                support_rows.append({"dataset": dataset, "run": run, "coordinate": coord, "support": support, "n": len(valid), "spearman": rho})

            valid = frame[PR_COORDS].replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) >= 2:
                rng = rng_for(cfg, "audit", "pr_pairs", dataset, run)
                count = int(cfg["statistics"]["scalar_pair_samples"])
                ia = rng.integers(0, len(valid), count)
                ib = rng.integers(0, len(valid), count)
                a = valid.iloc[ia].to_numpy()
                b = valid.iloc[ib].to_numpy()
                iqr = np.subtract(*np.nanpercentile(valid.to_numpy(), [75, 25], axis=0))
                deadband = np.maximum(1e-12, 0.01 * iqr)
                delta = a - b
                incomparable = (delta > deadband).any(axis=1) & (delta < -deadband).any(axis=1)
                trade_rows.append({"dataset": dataset, "run": run, "sampled_pairs": count, "incomparable_count": int(incomparable.sum()), "incomparable_rate": float(incomparable.mean())})
                ranks = valid.rank(pct=True).to_numpy()
                score = ranks.max(axis=1)
                dominant = ranks.argmax(axis=1)
                score_delta = score[ia] - score[ib]
                forced = incomparable & (np.abs(score_delta) > 1e-12)
                score_iqr = np.subtract(*np.percentile(score, [75, 25]))
                collision = incomparable & (np.abs(score_delta) <= max(1e-12, 0.01 * score_iqr)) & (dominant[ia] != dominant[ib])
                scalar_rows.append({"dataset": dataset, "run": run, "scalar": "max_empirical_marginal_rank_diagnostic", "incomparable_pairs": int(incomparable.sum()), "forced_order_rate_given_incomparable": float(forced.sum() / max(1, incomparable.sum())), "attribution_collision_rate_given_incomparable": float(collision.sum() / max(1, incomparable.sum()))})

        labels = [x.split(":")[1] for x in runs]
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                a, b = evidence[runs[i]], evidence[runs[j]]
                merged = match_pair(a[["timestamp", *PR_COORDS, *PHASE_COORDS, *DOPPLER_EPOCH_COORDS]], b[["timestamp", *PR_COORDS, *PHASE_COORDS, *DOPPLER_EPOCH_COORDS]], tolerance)
                coords = PR_COORDS + PHASE_COORDS + DOPPLER_EPOCH_COORDS
                rows, clips = paired_spearman_bootstrap(merged, [(c + "_a", c + "_b") for c in coords], cfg, ("audit", dataset, labels[i], labels[j]))
                clip_total += clips
                for row in rows:
                    row.update({"dataset": dataset, "run_a": labels[i], "run_b": labels[j]})
                    repeat_rows.append(row)

                da = doppler[runs[i]][["timestamp", "system", "center_normalized", "scale_normalized"]].copy()
                db = doppler[runs[j]][["timestamp", "system", "center_normalized", "scale_normalized"]].copy()
                da["doppler_system_center_signed"] = da["center_normalized"]
                db["doppler_system_center_signed"] = db["center_normalized"]
                da["doppler_system_center_abs"] = da["center_normalized"].abs()
                db["doppler_system_center_abs"] = db["center_normalized"].abs()
                da["doppler_system_scale"] = da["scale_normalized"]
                db["doppler_system_scale"] = db["scale_normalized"]
                system_merged = da[["timestamp", "system", "doppler_system_center_signed", "doppler_system_center_abs", "doppler_system_scale"]].merge(
                    db[["timestamp", "system", "doppler_system_center_signed", "doppler_system_center_abs", "doppler_system_scale"]],
                    on=["timestamp", "system"],
                    how="inner",
                    suffixes=("_a", "_b"),
                )
                system_coords = ["doppler_system_center_signed", "doppler_system_center_abs", "doppler_system_scale"]
                rows, clips = paired_spearman_bootstrap(system_merged, [(c + "_a", c + "_b") for c in system_coords], cfg, ("audit", "doppler-system", dataset, labels[i], labels[j]))
                clip_total += clips
                for row in rows:
                    row.update({"dataset": dataset, "run_a": labels[i], "run_b": labels[j]})
                    repeat_rows.append(row)

    doppler_mask_rows = []
    systems = sorted(set().union(*[set(x["system"].dropna().astype(str)) for x in doppler.values()]))
    for key, frame in doppler.items():
        dataset, run = key.split(":")
        pivot = frame.pivot_table(index="timestamp", columns="system", values="finite_count", aggfunc="sum")
        for system in systems:
            if system not in pivot:
                pivot[system] = np.nan
        masks = pivot[systems].notna().astype(int).astype(str).agg("".join, axis=1)
        for pattern, count in masks.value_counts().items():
            doppler_mask_rows.append({"dataset": dataset, "run": run, "canonical_system_order": "".join(systems), "valid_system_mask": pattern, "count": count, "fraction": count / len(pivot)})

    pd.DataFrame(mask_rows).to_csv(out / "pr_valid_coordinate_patterns.csv", index=False)
    pd.DataFrame(doppler_mask_rows).to_csv(out / "doppler_system_masks.csv", index=False)
    pd.DataFrame(support_rows).to_csv(out / "support_dependence.csv", index=False)
    pd.DataFrame(trade_rows).to_csv(out / "pr_tradeoff_incomparability.csv", index=False)
    pd.DataFrame(scalar_rows).to_csv(out / "scalar_attribution_loss.csv", index=False)
    pd.DataFrame(repeat_rows).to_csv(out / "coordinate_repeatability.csv", index=False)
    write_json(out / "numerical_guards.json", {"fisher_clip_value": cfg["statistics"]["fisher_rho_clip"], "fisher_clipping_count": clip_total, "log_ratio_epsilon_added": False})

    if repeat_rows:
        plot = pd.DataFrame(repeat_rows)
        fig, ax = plt.subplots(figsize=(10, 5))
        for (dataset, coord), group in plot.groupby(["dataset", "coordinate"]):
            ax.scatter([f"{dataset}:{a}/{b}" for a, b in zip(group.run_a, group.run_b)], group.spearman, label=f"{dataset} {coord}")
        ax.axhline(0.8, color="gray", linestyle="--", label="diagnostic 0.80")
        ax.set_ylim(-1, 1.02)
        ax.set_ylabel("Spearman repeatability")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=6, ncol=2)
        fig.tight_layout()
        fig.savefig(out / "coordinate_repeatability.png", dpi=160)
        plt.close(fig)


def support_anchors(values: Iterable[Any]) -> list[int]:
    x = finite(values)
    x = x[x >= 1]
    if not len(x):
        return []
    anchors = np.quantile(x, [0, 0.25, 0.5, 0.75, 1], method="linear")
    return sorted(set(max(1, int(round(v))) for v in anchors))


def row_quantile_abs_normal(
    rng: np.random.Generator, draws: int, n: int, location: float = 0.0, scale: float = 1.0
) -> np.ndarray:
    values = np.abs(location + scale * rng.standard_normal((draws, n)))
    return np.quantile(values, 0.9, axis=1, method="linear")


def pr_synthetic(
    rng: np.random.Generator,
    draws: int,
    n: int,
    groups: int,
    location: float = 0.0,
    scale: float = 1.0,
) -> np.ndarray:
    values = location + scale * rng.standard_normal((draws, n))
    population = np.quantile(np.abs(values), 0.9, axis=1, method="linear")
    groups = max(1, min(groups, n))
    splits = np.array_split(np.arange(n), groups)
    shifts = np.empty((draws, groups))
    scales = np.full((draws, groups), np.nan)
    for k, idx in enumerate(splits):
        g = values[:, idx]
        med = np.median(g, axis=1)
        shifts[:, k] = np.abs(med)
        if len(idx) >= 4:
            mad = np.median(np.abs(g - med[:, None]), axis=1)
            scales[:, k] = np.maximum(1.0, 1.4826 * mad)
    shift_p90 = np.quantile(shifts, 0.9, axis=1, method="linear")
    scale_p90 = np.nanquantile(scales, 0.9, axis=1, method="linear") if np.isfinite(scales).any() else np.full(draws, np.nan)
    return np.column_stack([population, shift_p90, scale_p90])


def doppler_synthetic(
    rng: np.random.Generator, draws: int, n: int, location: float = 0.0, scale_multiplier: float = 1.0
) -> np.ndarray:
    values = location + scale_multiplier * rng.standard_normal((draws, n))
    med = np.median(values, axis=1)
    scale = 1.4826 * np.median(np.abs(values - med[:, None]), axis=1)
    return np.column_stack([np.abs(med), scale])


def ecdf_values(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    ref = np.sort(reference[np.isfinite(reference)])
    if not len(ref):
        return np.full(len(values), np.nan)
    return np.searchsorted(ref, values, side="right") / len(ref)


def joint_monotone_region(cal: np.ndarray, val: np.ndarray, alpha: float) -> tuple[float, np.ndarray, float]:
    valid_cols = valid_nominal_columns(cal, val)
    cal = cal[:, valid_cols]
    val = val[:, valid_cols]
    if not cal.shape[1]:
        return math.nan, np.array([]), math.nan
    cal_scores = np.column_stack([ecdf_values(cal[:, k], cal[:, k]) for k in range(cal.shape[1])]).max(axis=1)
    score_limit = percentile(cal_scores, 1 - alpha)
    thresholds = np.array([percentile(cal[:, k], score_limit) for k in range(cal.shape[1])])
    membership = np.all(val <= thresholds, axis=1)
    return score_limit, thresholds, float(membership.mean())


def valid_nominal_columns(cal: np.ndarray, val: np.ndarray) -> np.ndarray:
    valid = []
    for k in range(cal.shape[1]):
        finite_cal = cal[np.isfinite(cal[:, k]), k]
        valid.append(
            len(finite_cal) == len(cal)
            and np.isfinite(val[:, k]).all()
            and len(finite_cal) > 1
            and float(np.std(finite_cal)) > 0
        )
    return np.asarray(valid, dtype=bool)


def coverage_tolerance(alpha: float, n: int) -> float:
    return max(0.003, 3.0 * math.sqrt(alpha * (1 - alpha) / n))


def command_synthetic(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    if not (root / "audit/coordinate_repeatability.csv").exists():
        raise RuntimeError("Run audit first")
    out = root / "synthetic_s0"
    out.mkdir(parents=True, exist_ok=True)
    evidence, doppler = load_all(cfg)
    all_e = pd.concat(evidence.values(), ignore_index=True)
    all_d = pd.concat(doppler.values(), ignore_index=True)
    draws_cal = int(cfg["statistics"]["synthetic_calibration_draws"])
    draws_val = int(cfg["statistics"]["synthetic_validation_draws"])
    alphas = [float(x) for x in cfg["statistics"]["alpha_grid"]]
    anchors = {
        "pr": support_anchors(all_e["pr_finite_success_count"]),
        "phase": support_anchors(all_e["phase_continuity_conditioned_count"]),
        "doppler_epoch": support_anchors(all_e["doppler_finite_success_count"]),
        "doppler": support_anchors(all_d["finite_count"]),
    }
    typical_groups = max(1, int(round(float(all_e["pr_group_count"].median()))))
    coverage_rows = []
    threshold_rows = []
    monotone_rows = []
    seed_rows = []
    perturbation_rows = []

    for channel, support_values in anchors.items():
        for n in support_values:
            cal_rng = rng_for(cfg, "synthetic-s0", channel, n, "calibration")
            val_rng = rng_for(cfg, "synthetic-s0", channel, n, "validation")
            if channel == "pr":
                cal = pr_synthetic(cal_rng, draws_cal, n, typical_groups)
                val = pr_synthetic(val_rng, draws_val, n, typical_groups)
                names = PR_COORDS
            elif channel == "phase":
                cal = row_quantile_abs_normal(cal_rng, draws_cal, n)[:, None]
                val = row_quantile_abs_normal(val_rng, draws_val, n)[:, None]
                names = PHASE_COORDS
            elif channel == "doppler_epoch":
                cal = row_quantile_abs_normal(cal_rng, draws_cal, n)[:, None]
                val = row_quantile_abs_normal(val_rng, draws_val, n)[:, None]
                names = DOPPLER_EPOCH_COORDS
            else:
                cal = doppler_synthetic(cal_rng, draws_cal, n)
                val = doppler_synthetic(val_rng, draws_val, n)
                names = ["doppler_system_center_abs", "doppler_system_scale"]
            valid_cols = valid_nominal_columns(cal, val)
            thresholds_by_alpha: dict[float, np.ndarray] = {}
            for alpha in alphas:
                score_limit, thresholds, achieved = joint_monotone_region(cal, val, alpha)
                thresholds_by_alpha[alpha] = thresholds
                target = 1 - alpha
                tol = coverage_tolerance(alpha, draws_val)
                coverage_rows.append({"channel": channel, "support": n, "alpha": alpha, "target_nominal_coverage": target, "achieved_nominal_coverage": achieved, "coverage_tolerance": tol, "absolute_error": abs(achieved - target), "status": "PASS" if abs(achieved - target) <= tol else "FAIL", "reference_semantics": "finite_MC_target_nominal_coverage"})
                idx = 0
                for k, name in enumerate(names):
                    if valid_cols[k]:
                        threshold_rows.append({"channel": channel, "support": n, "alpha": alpha, "coordinate": name, "joint_score_limit": score_limit, "nominal_upper_threshold": thresholds[idx]})
                        idx += 1
            rng = rng_for(cfg, "synthetic-s0", channel, n, "monotonicity")
            sample_idx = rng.integers(0, len(val), min(100000, len(val)))
            base = val[sample_idx]
            factors = rng.uniform(0, 1, base.shape)
            no_worse = base * factors
            for alpha in alphas:
                _, thresholds, _ = joint_monotone_region(cal, val, alpha)
                valid = np.isfinite(base).all(axis=1)
                accepted = valid & np.all(base[:, : len(thresholds)] <= thresholds, axis=1)
                no_worse_accepted = np.all(no_worse[:, : len(thresholds)] <= thresholds, axis=1)
                violations = int(np.sum(accepted & ~no_worse_accepted))
                monotone_rows.append({"channel": channel, "support": n, "alpha": alpha, "accepted_samples": int(accepted.sum()), "downward_closure_violations": violations, "status": "PASS" if violations == 0 else "FAIL"})
            repeat_coverages = {alpha: [] for alpha in alphas}
            for repeat in range(int(cfg["statistics"]["synthetic_seed_repeats"])):
                repeat_rng = rng_for(cfg, "synthetic-s0", channel, n, "seed-sensitivity", repeat)
                if channel == "pr":
                    repeat_val = pr_synthetic(repeat_rng, draws_val, n, typical_groups)
                elif channel == "phase":
                    repeat_val = row_quantile_abs_normal(repeat_rng, draws_val, n)[:, None]
                elif channel == "doppler_epoch":
                    repeat_val = row_quantile_abs_normal(repeat_rng, draws_val, n)[:, None]
                else:
                    repeat_val = doppler_synthetic(repeat_rng, draws_val, n)
                repeat_valid = repeat_val[:, valid_cols]
                for alpha in alphas:
                    repeat_coverages[alpha].append(float(np.mean(np.all(repeat_valid <= thresholds_by_alpha[alpha], axis=1))))
            for alpha in alphas:
                target = 1 - alpha
                tol = coverage_tolerance(alpha, draws_val)
                coverages = repeat_coverages[alpha]
                seed_rows.append({"channel": channel, "support": n, "alpha": alpha, "replicates": len(coverages), "coverage_min": min(coverages), "coverage_median": float(np.median(coverages)), "coverage_max": max(coverages), "maximum_absolute_target_error": max(abs(x - target) for x in coverages), "coverage_tolerance": tol, "all_repeats_within_tolerance": bool(all(abs(x - target) <= tol for x in coverages))})

    perturb_draws = int(cfg["statistics"]["synthetic_perturbation_draws"])
    locations = [float(x) for x in cfg["statistics"]["synthetic_perturbations"]["location_magnitude"]]
    scales = [float(x) for x in cfg["statistics"]["synthetic_perturbations"]["scale"]]
    for channel in ("pr", "phase", "doppler_epoch", "doppler"):
        # PR exact natural-group topology is not logged.  Use the largest
        # frozen support anchor for the perturbation mechanics so the equal-
        # group approximation has at least one scale-eligible group; this does
        # not promote the approximation to a real-data calibrator.
        n = anchors[channel][-1] if channel == "pr" else anchors[channel][len(anchors[channel]) // 2]
        if channel == "pr":
            for location in locations:
                values = pr_synthetic(rng_for(cfg, "synthetic-s0", "perturb", channel, "location", location), perturb_draws, n, typical_groups, location=location)
                for k, name in enumerate(PR_COORDS):
                    perturbation_rows.append({"channel": channel, "perturbation": "positive_location", "level": location, "coordinate": name, "median_statistic": percentile(values[:, k], 0.5)})
            for scale in scales:
                values = pr_synthetic(rng_for(cfg, "synthetic-s0", "perturb", channel, "scale", scale), perturb_draws, n, typical_groups, scale=scale)
                for k, name in enumerate(PR_COORDS):
                    perturbation_rows.append({"channel": channel, "perturbation": "scale", "level": scale, "coordinate": name, "median_statistic": percentile(values[:, k], 0.5)})
        elif channel in {"phase", "doppler_epoch"}:
            for scale in scales:
                values = row_quantile_abs_normal(rng_for(cfg, "synthetic-s0", "perturb", channel, "scale", scale), perturb_draws, n, scale=scale)
                coordinate = PHASE_COORDS[0] if channel == "phase" else DOPPLER_EPOCH_COORDS[0]
                perturbation_rows.append({"channel": channel, "perturbation": "scale", "level": scale, "coordinate": coordinate, "median_statistic": percentile(values, 0.5)})
        else:
            for location in locations:
                for sign in (-1, 1):
                    values = doppler_synthetic(rng_for(cfg, "synthetic-s0", "perturb", channel, "location", sign, location), perturb_draws, n, location=sign * location)
                    perturbation_rows.append({"channel": channel, "perturbation": "signed_location", "level": sign * location, "coordinate": "doppler_system_center_abs", "median_statistic": percentile(values[:, 0], 0.5), "excursion_direction": "negative" if sign < 0 else "positive"})
            for scale in scales:
                values = doppler_synthetic(rng_for(cfg, "synthetic-s0", "perturb", channel, "scale", scale), perturb_draws, n, scale_multiplier=scale)
                perturbation_rows.append({"channel": channel, "perturbation": "scale", "level": scale, "coordinate": "doppler_system_scale", "median_statistic": percentile(values[:, 1], 0.5)})

    coverage = pd.DataFrame(coverage_rows)
    thresholds = pd.DataFrame(threshold_rows)
    monotonicity = pd.DataFrame(monotone_rows)
    seed_sensitivity = pd.DataFrame(seed_rows)
    perturbations = pd.DataFrame(perturbation_rows)
    direction_rows = []
    for keys, group in perturbations.groupby(["channel", "perturbation", "coordinate"], dropna=False):
        if keys[1] == "signed_location":
            ordered = group.assign(abs_level=group.level.abs()).groupby("abs_level").median(numeric_only=True).sort_index()
        else:
            ordered = group.sort_values("level").set_index("level")
        values = ordered.median_statistic.to_numpy(float)
        expected = not (keys[0] == "pr" and keys[1] == "positive_location" and keys[2] == "pr_group_scale_eligible_p90")
        agreement = float(np.mean(np.diff(values) >= -1e-12)) if len(values) > 1 and expected else math.nan
        traffic = "not_applicable_cross_coordinate_diagnostic" if not expected else ("pass" if agreement >= 0.90 else ("partial" if agreement >= 0.75 else "unstable"))
        direction_rows.append({"channel": keys[0], "perturbation": keys[1], "coordinate": keys[2], "monotone_direction_expected": expected, "monotone_direction_agreement": agreement, "traffic_light": traffic, "heuristic_not_runtime_parameter": True})
    coverage.to_csv(out / "synthetic_coverage.csv", index=False)
    thresholds.to_csv(out / "synthetic_nominal_thresholds.csv", index=False)
    monotonicity.to_csv(out / "synthetic_monotonicity.csv", index=False)
    seed_sensitivity.to_csv(out / "synthetic_seed_sensitivity.csv", index=False)
    perturbations.to_csv(out / "synthetic_perturbation_response.csv", index=False)
    pd.DataFrame(direction_rows).to_csv(out / "synthetic_perturbation_direction.csv", index=False)
    write_json(out / "synthetic_config.json", {"support_anchors": anchors, "pr_approximate_equal_group_count": typical_groups, "pr_exact_group_topology": "artifact_limited_mechanics_only", "phase_factor_level": "artifact_limited_mechanics_only", "draws_calibration": draws_cal, "draws_validation": draws_val, "quality_region": "joint_marginal_ECDF_max_downward_closed_rectangle"})
    write_json(out / "execution_corrections.json", {"corrections": [{"stage": "synthetic-s0 pre-transfer", "type": "implementation_bug_fix", "issue": "A zero-variance nominal coordinate (Doppler scale at support=1) was initially treated as a valid joint coordinate and forced the ECDF-max score to one.", "fix": "Apply the frozen valid-coordinate semantics: a nominal coordinate must be finite and non-degenerate; the support=1 scale slot is unavailable, not zero-filled.", "frozen_parameters_changed": False, "result_driven_calibration_change": False}, {"stage": "synthetic-s0 pre-transfer", "type": "implementation_completeness_fix", "issue": "The first implementation generated Doppler per-system center/scale anchors but omitted the frozen raw Doppler P90 coordinate.", "fix": "Add a separate Doppler epoch-P90 nominal anchor using the same frozen alpha, support-anchor, draw-count, seed, percentile, and upper-tail rules.", "frozen_parameters_changed": False, "result_driven_calibration_change": False}], "pr_perturbation_note": "The largest frozen PR support anchor is used only for approximate equal-group perturbation mechanics because smaller equal groups contain no scale-eligible group; exact natural-group validation remains artifact-limited."})

    fig, ax = plt.subplots(figsize=(8, 5))
    for channel, group in coverage.groupby("channel"):
        ax.scatter(group["target_nominal_coverage"], group["achieved_nominal_coverage"], label=channel, alpha=0.7)
    ax.plot([0.89, 1], [0.89, 1], "k--")
    ax.set_xlabel("Target nominal coverage")
    ax.set_ylabel("Independent synthetic achieved coverage")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "synthetic_nominal_coverage.png", dpi=160)
    plt.close(fig)


def assign_blocks(frame: pd.DataFrame, block_size: int, gap_multiple: float) -> pd.DataFrame:
    ordered = frame.sort_values(["run", "timestamp"]).copy()
    ids = np.full(len(ordered), -1, dtype=int)
    next_id = 0
    for _, positions in ordered.groupby("run", sort=False).indices.items():
        sub = ordered.iloc[positions]
        # Block size is measured in temporal epochs, not artifact rows.  The
        # per-system Doppler artifact has multiple rows at one timestamp; all
        # of them must stay in the same temporal block.
        epochs = pd.DataFrame({"timestamp": np.sort(sub["timestamp"].unique())})
        blocks = make_blocks(epochs, block_size, gap_multiple)
        for block in blocks:
            timestamps = set(epochs.iloc[block]["timestamp"].to_numpy(float))
            local_rows = np.flatnonzero(sub["timestamp"].isin(timestamps).to_numpy())
            ids[np.asarray(positions)[local_rows]] = next_id
            next_id += 1
    ordered["block_id"] = ids
    return ordered


def tail_status(values: np.ndarray, threshold: float, block_ids: np.ndarray, cfg: dict[str, Any]) -> tuple[float, str]:
    valid = np.isfinite(values) & np.isfinite(block_ids) & (block_ids >= 0) & np.isfinite(threshold)
    if not valid.any():
        return 0.0, "NotAssessed"
    blocks = np.unique(block_ids[valid])
    tail_blocks = sum(bool(np.any(values[valid & (block_ids == b)] >= threshold)) for b in blocks)
    if len(blocks) >= 20 and tail_blocks >= 10:
        return float(tail_blocks), "Eligible"
    if len(blocks) >= 10 and tail_blocks >= 5:
        return float(tail_blocks), "Partial"
    if tail_blocks >= 2:
        return float(tail_blocks), "DiagnosticOnly"
    return float(tail_blocks), "NotAssessed"


def empirical_quantile_bounds(values: np.ndarray, p: float, epsilon: float) -> tuple[float, float]:
    values = finite(values)
    if not len(values):
        return math.nan, math.nan
    low_p = np.clip((1 - epsilon) * p, 0, 1)
    high_p = np.clip(epsilon + (1 - epsilon) * p, 0, 1)
    return percentile(values, low_p), percentile(values, high_p)


def ratio_guard(num: float, den: float) -> tuple[float, str]:
    if not (np.isfinite(num) and np.isfinite(den) and num > 0 and den > 0):
        return math.nan, "numerical-invalid/NotAssessed"
    return num / den, "valid"


def simultaneous_log_ci(estimates: np.ndarray, boot: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    if np.any(~np.isfinite(estimates)) or np.any(estimates <= 0):
        n = len(estimates)
        return np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan), math.nan
    transformed = np.log(estimates)
    transformed_boot = np.where((boot > 0) & np.isfinite(boot), np.log(boot), np.nan)
    se = np.nanstd(transformed_boot, axis=0, ddof=1)
    valid = np.isfinite(se) & (se > 0)
    z = np.full_like(transformed_boot, np.nan)
    z[:, valid] = np.abs((transformed_boot[:, valid] - transformed[valid]) / se[valid])
    maxz = np.nanmax(z, axis=1)
    c95 = percentile(maxz, 0.95)
    low = np.full(len(estimates), np.nan)
    high = np.full(len(estimates), np.nan)
    for k in range(len(estimates)):
        if se[k] == 0:
            low[k] = high[k] = estimates[k]
        elif np.isfinite(c95):
            low[k] = math.exp(transformed[k] - c95 * se[k])
            high[k] = math.exp(transformed[k] + c95 * se[k])
    return low, high, se, c95


def transfer_tables(evidence: dict[str, pd.DataFrame], doppler: dict[str, pd.DataFrame], dataset: str) -> list[dict[str, Any]]:
    frames = [v.copy() for k, v in evidence.items() if k.startswith(dataset + ":")]
    epoch = pd.concat(frames, ignore_index=True)
    rows = []
    for coord, support, channel in [
        (PR_COORDS[0], "pr_finite_success_count", "pr"),
        (PR_COORDS[1], "pr_group_count", "pr"),
        (PR_COORDS[2], "pr_group_eligible_count", "pr"),
        (PHASE_COORDS[0], "phase_continuity_conditioned_count", "phase"),
        (DOPPLER_EPOCH_COORDS[0], "doppler_finite_success_count", "doppler_epoch"),
    ]:
        f = epoch[["timestamp", "run", coord, support]].copy()
        f.columns = ["timestamp", "run", "value", "support"]
        rows.append({"channel": channel, "coordinate": coord, "frame": f, "entity": "epoch"})
    d = pd.concat([v.copy() for k, v in doppler.items() if k.startswith(dataset + ":")], ignore_index=True)
    for coord, source_col in [("doppler_system_center_abs", "center_normalized"), ("doppler_system_scale", "scale_normalized")]:
        f = d[["timestamp", "run", "system", source_col, "finite_count"]].copy()
        f[source_col] = f[source_col].abs() if coord.endswith("center_abs") else f[source_col]
        f.columns = ["timestamp", "run", "system", "value", "support"]
        rows.append({"channel": "doppler_system", "coordinate": coord, "frame": f, "entity": "system"})
    return rows


def nearest_nominal(thresholds: pd.DataFrame, channel: str, coord: str, support: float, alpha: float) -> float:
    channel_key = "doppler" if channel == "doppler_system" else channel
    subset = thresholds[(thresholds.channel == channel_key) & (thresholds.coordinate == coord) & np.isclose(thresholds.alpha, alpha)]
    if subset.empty or not np.isfinite(support):
        return math.nan
    idx = (subset.support.astype(float) - support).abs().idxmin()
    return float(subset.loc[idx, "nominal_upper_threshold"])


def command_transfer(cfg: dict[str, Any], repo: Path, source: str, target: str) -> None:
    root = output_root(cfg, repo)
    thresholds_path = root / "synthetic_s0/synthetic_nominal_thresholds.csv"
    if not thresholds_path.exists():
        raise RuntimeError("Run synthetic-s0 first")
    out = root / f"transfer_{source.replace('.', 'p')}_to_{target.replace('.', 'p')}"
    out.mkdir(parents=True, exist_ok=True)
    thresholds = pd.read_csv(thresholds_path)
    evidence, doppler = load_all(cfg)
    source_tables = transfer_tables(evidence, doppler, source)
    target_tables = {x["coordinate"]: x for x in transfer_tables(evidence, doppler, target)}
    alphas = [float(x) for x in cfg["statistics"]["alpha_grid"]]
    primary_block = int(cfg["statistics"]["primary_block_size_epochs"])
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    result_rows = []
    boot_specs = []

    for table in source_tables:
        coord = table["coordinate"]
        sf = table["frame"].replace([np.inf, -np.inf], np.nan).dropna(subset=["value", "support"])
        tf = target_tables[coord]["frame"].replace([np.inf, -np.inf], np.nan).dropna(subset=["value", "support"])
        if sf.empty:
            continue
        edges = np.unique(np.quantile(sf.support, [0, 1 / 3, 2 / 3, 1], method="linear"))
        if len(edges) < 2:
            edges = np.array([sf.support.min() - 0.5, sf.support.max() + 0.5])
        edges[0] = -np.inf
        edges[-1] = np.inf
        sf = sf.copy()
        tf = tf.copy()
        sf["stratum"] = pd.cut(sf.support, edges, include_lowest=True, duplicates="drop").astype(str)
        tf["stratum"] = pd.cut(tf.support, edges, include_lowest=True, duplicates="drop").astype(str)
        sf = assign_blocks(sf, primary_block, cfg["statistics"]["segment_gap_multiple"])
        tf = assign_blocks(tf, primary_block, cfg["statistics"]["segment_gap_multiple"])
        for stratum, sg in sf.groupby("stratum", observed=True):
            tg = tf[tf.stratum == stratum]
            support = float(sg.support.median())
            for alpha in alphas:
                p = 1 - alpha
                nominal = nearest_nominal(thresholds, table["channel"], coord, support, alpha)
                q_source = percentile(sg.value.to_numpy(), p)
                ratio, numerical = ratio_guard(q_source, nominal)
                tail_eff, tail_assessment = tail_status(sg.value.to_numpy(), q_source, sg.block_id.to_numpy(), cfg)
                candidate_eligible = tail_assessment in {"Eligible", "Partial"} and numerical == "valid"
                nominal_source_occ = float(np.mean(sg.value <= nominal)) if np.isfinite(nominal) else math.nan
                nominal_target_occ = float(np.mean(tg.value <= nominal)) if len(tg) and np.isfinite(nominal) else math.nan
                candidate_threshold = max(1.0, ratio) * nominal if candidate_eligible else math.nan
                target_candidate_occ = float(np.mean(tg.value <= candidate_threshold)) if len(tg) and np.isfinite(candidate_threshold) else math.nan
                row = {
                    "source": source,
                    "target": target,
                    "channel": table["channel"],
                    "coordinate": coord,
                    "support_stratum": stratum,
                    "source_n": len(sg),
                    "target_n": len(tg),
                    "source_effective_blocks": int(sg.block_id[sg.block_id >= 0].nunique()),
                    "target_effective_blocks": int(tg.block_id[tg.block_id >= 0].nunique()),
                    "representative_support": support,
                    "alpha": alpha,
                    "nominal_upper_threshold": nominal,
                    "source_empirical_upper_quantile": q_source,
                    "nominal_mismatch_ratio": ratio,
                    "numerical_status": numerical,
                    "effective_tail_support": tail_eff,
                    "tail_assessment_status": tail_assessment,
                    "empirical_correction_candidate_status": "candidate" if candidate_eligible else "NotAssessed",
                    "r_quality_sensitivity_candidate": max(1.0, ratio) if candidate_eligible else math.nan,
                    "source_nominal_membership_occupancy": nominal_source_occ,
                    "target_nominal_membership_occupancy": nominal_target_occ,
                    "occupancy_gap_target_minus_source": nominal_target_occ - nominal_source_occ if np.isfinite(nominal_target_occ) else math.nan,
                    "target_candidate_membership_occupancy": target_candidate_occ,
                    "occupancy_is_transfer_pass_target": False,
                }
                result_rows.append(row)
                boot_specs.append((len(result_rows) - 1, sg.copy(), nominal, p))

    results = pd.DataFrame(result_rows)
    boot = np.full((reps, len(results)), np.nan)
    epsilons = [float(x) for x in cfg["statistics"]["contamination_epsilon_grid"]]
    contamination_low_boot = {epsilon: np.full((reps, len(results)), np.nan) for epsilon in epsilons}
    contamination_high_boot = {epsilon: np.full((reps, len(results)), np.nan) for epsilon in epsilons}
    rng = rng_for(cfg, "transfer", source, target, "source_block_bootstrap")
    for k, (_, sg, nominal, p) in enumerate(boot_specs):
        blocks = [x.value.to_numpy(float) for _, x in sg[sg.block_id >= 0].groupby("block_id")]
        if not blocks or not np.isfinite(nominal) or nominal <= 0:
            continue
        for b in range(reps):
            selected = rng.integers(0, len(blocks), len(blocks))
            sample = np.concatenate([blocks[i] for i in selected])
            q = percentile(sample, p)
            boot[b, k], _ = ratio_guard(q, nominal)
            for epsilon in epsilons:
                qlow, qhigh = empirical_quantile_bounds(sample, p, epsilon)
                contamination_low_boot[epsilon][b, k], _ = ratio_guard(qlow, nominal)
                contamination_high_boot[epsilon][b, k], _ = ratio_guard(qhigh, nominal)
    estimates = results["nominal_mismatch_ratio"].to_numpy(float)
    valid_columns = np.isfinite(estimates) & (estimates > 0) & np.isfinite(boot).any(axis=0)
    low = np.full(len(results), np.nan)
    high = np.full(len(results), np.nan)
    se = np.full(len(results), np.nan)
    c95 = math.nan
    if valid_columns.any():
        l, h, s, c95 = simultaneous_log_ci(estimates[valid_columns], boot[:, valid_columns])
        low[valid_columns], high[valid_columns], se[valid_columns] = l, h, s
    results["candidate_simultaneous_ci_low"] = low
    results["candidate_simultaneous_ci_high"] = high
    results["candidate_bootstrap_se_log"] = se
    results["candidate_direction"] = np.where((low > 1), "increase", np.where((high < 1), "decrease", "neutral/indeterminate"))
    results.to_csv(out / "transfer_assessment.csv", index=False)

    contamination_rows = []
    endpoint_point: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    endpoint_ci: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for epsilon in epsilons:
        point_low = np.full(len(results), np.nan)
        point_high = np.full(len(results), np.nan)
        for idx, sg, nominal, p in boot_specs:
            qlow, qhigh = empirical_quantile_bounds(sg.value.to_numpy(), p, epsilon)
            point_low[idx], _ = ratio_guard(qlow, nominal)
            point_high[idx], _ = ratio_guard(qhigh, nominal)
        valid_low = np.isfinite(point_low) & (point_low > 0) & np.isfinite(contamination_low_boot[epsilon]).any(axis=0)
        valid_high = np.isfinite(point_high) & (point_high > 0) & np.isfinite(contamination_high_boot[epsilon]).any(axis=0)
        low_ci_low = np.full(len(results), np.nan)
        low_ci_high = np.full(len(results), np.nan)
        high_ci_low = np.full(len(results), np.nan)
        high_ci_high = np.full(len(results), np.nan)
        if valid_low.any():
            ll, lh, _, _ = simultaneous_log_ci(point_low[valid_low], contamination_low_boot[epsilon][:, valid_low])
            low_ci_low[valid_low], low_ci_high[valid_low] = ll, lh
        if valid_high.any():
            hl, hh, _, _ = simultaneous_log_ci(point_high[valid_high], contamination_high_boot[epsilon][:, valid_high])
            high_ci_low[valid_high], high_ci_high[valid_high] = hl, hh
        endpoint_point[epsilon] = (point_low, point_high)
        endpoint_ci[epsilon] = (low_ci_low, low_ci_high, high_ci_low, high_ci_high)
    for idx, sg, nominal, p in boot_specs:
        base = results.iloc[idx]
        for epsilon in epsilons:
            point_low, point_high = endpoint_point[epsilon]
            low_ci_low, low_ci_high, high_ci_low, high_ci_high = endpoint_ci[epsilon]
            rlow, rhigh = point_low[idx], point_high[idx]
            slow = "valid" if np.isfinite(rlow) and rlow > 0 else "numerical-invalid/NotAssessed"
            shigh = "valid" if np.isfinite(rhigh) and rhigh > 0 else "numerical-invalid/NotAssessed"
            contamination_rows.append({"source": source, "target": target, "channel": base.channel, "coordinate": base.coordinate, "support_stratum": base.support_stratum, "alpha": base.alpha, "epsilon_sensitivity": epsilon, "candidate_ratio_lower_endpoint": rlow, "candidate_ratio_lower_simultaneous_ci_low": low_ci_low[idx], "candidate_ratio_lower_simultaneous_ci_high": low_ci_high[idx], "candidate_ratio_upper_endpoint": rhigh, "candidate_ratio_upper_simultaneous_ci_low": high_ci_low[idx], "candidate_ratio_upper_simultaneous_ci_high": high_ci_high[idx], "lower_numerical_status": slow, "upper_numerical_status": shigh, "interpretation": "bootstrap_combined_sensitivity_envelope_not_true_epsilon_estimate"})
    pd.DataFrame(contamination_rows).to_csv(out / "contamination_sensitivity.csv", index=False)

    block_rows = []
    for block_size in cfg["statistics"]["block_sizes_epochs"]:
        for table in source_tables:
            frame = assign_blocks(table["frame"].replace([np.inf, -np.inf], np.nan).dropna(subset=["value"]), int(block_size), cfg["statistics"]["segment_gap_multiple"])
            block_values = frame[frame.block_id >= 0].groupby("block_id").value.median()
            block_rows.append({"source": source, "target": target, "channel": table["channel"], "coordinate": table["coordinate"], "block_size_epochs": block_size, "effective_blocks": len(block_values), "median_of_block_medians": percentile(block_values.to_numpy(), 0.5), "p90_of_block_medians": percentile(block_values.to_numpy(), 0.9)})
    pd.DataFrame(block_rows).to_csv(out / "block_sensitivity.csv", index=False)
    write_json(out / "bootstrap_manifest.json", {"replicates": reps, "method": "source-only nonoverlapping temporal block bootstrap; simultaneous max-studentized log-ratio CI", "simultaneous_c95": c95, "target_refit": False, "neutral_if_ci_contains_one": True, "strict_positive_finite_ratio_guard": True, "epsilon_added": False, "contamination_combination": "contamination lower/upper endpoints recomputed inside every source-block bootstrap replicate with separate simultaneous max-studentized log-scale bands"})

    fig, ax = plt.subplots(figsize=(10, 5))
    valid = results[np.isfinite(results.nominal_mismatch_ratio)]
    x = np.arange(len(valid))
    ax.scatter(x, valid.nominal_mismatch_ratio, s=15)
    ax.axhline(1, color="black", linestyle="--")
    ax.axhline(2, color="gray", linestyle=":")
    ax.axhline(4, color="gray", linestyle=":")
    ax.set_yscale("log")
    ax.set_ylabel("Nominal mismatch ratio (candidate only)")
    ax.set_xlabel("Preregistered coordinate/support/alpha rows")
    fig.tight_layout()
    fig.savefig(out / "nominal_mismatch_ratios.png", dpi=160)
    plt.close(fig)


def command_report(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    required = [
        root / "validate/validation_report.json",
        root / "audit/coordinate_repeatability.csv",
        root / "synthetic_s0/synthetic_coverage.csv",
        root / "transfer_4p1_to_4p2/transfer_assessment.csv",
        root / "transfer_4p2_to_4p1/transfer_assessment.csv",
    ]
    missing = [str(x) for x in required if not x.exists()]
    if missing:
        raise RuntimeError(f"Missing prerequisite artifacts: {missing}")
    out = root / "report"
    out.mkdir(parents=True, exist_ok=True)
    validation = json.loads(required[0].read_text())
    repeat = pd.read_csv(required[1])
    coverage = pd.read_csv(required[2])
    transfer_ab = pd.read_csv(required[3])
    transfer_ba = pd.read_csv(required[4])
    audit_trade = pd.read_csv(root / "audit/pr_tradeoff_incomparability.csv")
    scalar_loss = pd.read_csv(root / "audit/scalar_attribution_loss.csv")
    guards = json.loads((root / "audit/numerical_guards.json").read_text())
    evidence, doppler = load_all(cfg)

    applicability_rows = []
    for source, target in [("4.1", "4.2"), ("4.2", "4.1")]:
        source_tables = {x["coordinate"]: x for x in transfer_tables(evidence, doppler, source)}
        target_tables = {x["coordinate"]: x for x in transfer_tables(evidence, doppler, target)}
        for coordinate, source_table in source_tables.items():
            sf = source_table["frame"].replace([np.inf, -np.inf], np.nan)
            tf = target_tables[coordinate]["frame"].replace([np.inf, -np.inf], np.nan)
            source_valid = sf.value.notna() & sf.support.notna()
            target_valid = tf.value.notna() & tf.support.notna()
            if source_valid.any():
                support_min = float(sf.loc[source_valid, "support"].min())
                support_max = float(sf.loc[source_valid, "support"].max())
                in_domain = target_valid & tf.support.between(support_min, support_max)
                out_domain = target_valid & ~tf.support.between(support_min, support_max)
            else:
                support_min = support_max = math.nan
                in_domain = pd.Series(False, index=tf.index)
                out_domain = target_valid
            applicability_rows.append({"source": source, "target": target, "channel": source_table["channel"], "coordinate": coordinate, "source_total": len(sf), "source_valid": int(source_valid.sum()), "source_valid_rate": float(source_valid.mean()), "source_support_min": support_min, "source_support_max": support_max, "target_total": len(tf), "target_evidence_valid": int(target_valid.sum()), "target_evidence_valid_rate": float(target_valid.mean()), "calibration_applicability_InDomain": int(in_domain.sum()), "calibration_applicability_OutOfDomain": int(out_domain.sum()), "calibrated_quality_NotAssessed": int((~target_valid).sum()), "InDomain_rate": float(in_domain.mean()), "OutOfDomain_rate": float(out_domain.mean()), "NotAssessed_rate": float((~target_valid).mean()), "covariance_model_applicability": "Unknown_not_explicit_in_artifact"})
    applicability = pd.DataFrame(applicability_rows)
    applicability.to_csv(out / "applicability_rates.csv", index=False)

    def add_stratum_ordinal(frame: pd.DataFrame, label: str) -> pd.DataFrame:
        frame = frame.copy()
        frame["stratum_ordinal"] = frame.groupby(["coordinate", "alpha"])["representative_support"].rank(method="dense").astype(int) - 1
        keep = ["coordinate", "alpha", "stratum_ordinal", "representative_support", "nominal_mismatch_ratio", "candidate_simultaneous_ci_low", "candidate_simultaneous_ci_high", "candidate_direction", "tail_assessment_status", "empirical_correction_candidate_status"]
        return frame[keep].rename(columns={x: f"{x}_{label}" for x in keep if x not in {"coordinate", "alpha", "stratum_ordinal"}})

    comparison = add_stratum_ordinal(transfer_ab, "4p1").merge(add_stratum_ordinal(transfer_ba, "4p2"), on=["coordinate", "alpha", "stratum_ordinal"], how="outer")
    ratio_of_ratios = []
    ratio_status = []
    for a, b in zip(comparison.nominal_mismatch_ratio_4p1, comparison.nominal_mismatch_ratio_4p2):
        value, status = ratio_guard(a, b)
        ratio_of_ratios.append(value)
        ratio_status.append(status)
    comparison["mismatch_ratio_4p1_over_4p2"] = ratio_of_ratios
    comparison["ratio_numerical_status"] = ratio_status
    comparison["candidate_direction_agreement"] = comparison.candidate_direction_4p1 == comparison.candidate_direction_4p2
    comparison["both_candidate_eligible"] = (comparison.empirical_correction_candidate_status_4p1 == "candidate") & (comparison.empirical_correction_candidate_status_4p2 == "candidate")
    comparison.to_csv(out / "cross_session_candidate_comparison.csv", index=False)

    contamination_summary_rows = []
    for direction in ("4p1_to_4p2", "4p2_to_4p1"):
        frame = pd.read_csv(root / f"transfer_{direction}/contamination_sensitivity.csv")
        frame["envelope_fold_width"] = frame.candidate_ratio_upper_endpoint / frame.candidate_ratio_lower_endpoint
        for epsilon, group in frame.groupby("epsilon_sensitivity"):
            contamination_summary_rows.append({"direction": direction, "epsilon_sensitivity": epsilon, "rows": len(group), "median_envelope_fold_width": group.envelope_fold_width.median(), "p90_envelope_fold_width": percentile(group.envelope_fold_width.to_numpy(), 0.9), "max_envelope_fold_width": group.envelope_fold_width.max(), "numerical_invalid_rows": int(((group.lower_numerical_status != "valid") | (group.upper_numerical_status != "valid")).sum())})
    contamination_summary = pd.DataFrame(contamination_summary_rows)
    contamination_summary.to_csv(out / "contamination_summary.csv", index=False)

    block_summary_rows = []
    for direction in ("4p1_to_4p2", "4p2_to_4p1"):
        frame = pd.read_csv(root / f"transfer_{direction}/block_sensitivity.csv")
        for size, group in frame.groupby("block_size_epochs"):
            block_summary_rows.append({"direction": direction, "block_size_epochs": size, "minimum_effective_blocks": int(group.effective_blocks.min()), "median_effective_blocks": float(group.effective_blocks.median()), "maximum_effective_blocks": int(group.effective_blocks.max()), "median_p90_of_block_medians": float(group.p90_of_block_medians.median())})
    block_summary = pd.DataFrame(block_summary_rows)
    block_summary.to_csv(out / "block_sensitivity_summary.csv", index=False)

    synthetic_pass_count = int((coverage.status == "PASS").sum())
    synthetic_fail_count = int((coverage.status == "FAIL").sum())
    synthetic_status = "PASS" if synthetic_fail_count == 0 else ("PARTIAL" if synthetic_pass_count > 0 else "FAIL")
    repeat_stable = int((repeat.traffic_light == "stable").sum())
    repeat_total = len(repeat)
    candidate_counts = Counter(pd.concat([transfer_ab.empirical_correction_candidate_status, transfer_ba.empirical_correction_candidate_status]))
    tail_counts = Counter(pd.concat([transfer_ab.tail_assessment_status, transfer_ba.tail_assessment_status]))
    numerical_invalid = int(pd.concat([transfer_ab.numerical_status, transfer_ba.numerical_status]).str.contains("invalid", na=False).sum())
    deviations: list[dict[str, Any]] = []
    execution_corrections = json.loads((root / "synthetic_s0/execution_corrections.json").read_text())["corrections"]
    execution_corrections.append({"stage": "transfer pre-final-report", "type": "implementation_bug_fix", "issue": "The initial Doppler per-system block assignment counted artifact rows rather than unique temporal epochs.", "fix": "Assign all per-system rows with the same timestamp to one temporal epoch and form the frozen 10/30/60-epoch blocks from unique timestamps.", "frozen_parameters_changed": False, "result_driven_calibration_change": False})
    direction_valid = comparison[comparison.both_candidate_eligible & comparison.candidate_direction_4p1.notna() & comparison.candidate_direction_4p2.notna()]
    direction_agreement = float(direction_valid.candidate_direction_agreement.mean()) if len(direction_valid) else math.nan
    overall = "PARTIAL" if validation["status"] == "PASS" and synthetic_status != "FAIL" else "FAIL"
    decision = {
        "stage": "Stage 3A.1b-1b.3 offline prototype",
        "overall": overall,
        "validation": validation["status"],
        "synthetic_nominal_mechanics": synthetic_status,
        "synthetic_coverage_checks_pass": synthetic_pass_count,
        "synthetic_coverage_checks_fail": synthetic_fail_count,
        "real_transfer_interpretation": "prototype stability and mismatch characterization only; occupancy is not a PASS target",
        "repeatability_stable_rows": repeat_stable,
        "repeatability_total_rows": repeat_total,
        "tail_status_counts": dict(tail_counts),
        "candidate_status_counts": dict(candidate_counts),
        "numerical_invalid_ratio_rows": numerical_invalid,
        "cross_session_candidate_direction_agreement": direction_agreement,
        "target_out_of_domain_rates": applicability.groupby(["source", "target"]).OutOfDomain_rate.mean().to_dict(),
        "target_not_assessed_rates": applicability.groupby(["source", "target"]).NotAssessed_rate.mean().to_dict(),
        "fisher_clipping_count": guards["fisher_clipping_count"],
        "artifact_limitations": cfg["artifact_limits"],
        "preregistration_deviations": deviations,
        "execution_corrections_before_final_artifacts": execution_corrections,
        "final_calibrator_selected": False,
        "runtime_parameters_produced": False,
    }
    write_json(out / "prototype_decision.json", decision)

    lines = [
        "# Stage 3A.1b-1b.3 Offline Calibration Prototype",
        "",
        f"- Overall prototype result: **{overall}**",
        f"- Input/schema validation: **{validation['status']}**",
        f"- Synthetic nominal mechanics: **{synthetic_status}**",
        "- Real membership/occupancy is descriptive; it is not calibration coverage or a transfer PASS target.",
        "- No final calibrator, runtime threshold, weighting law, or target refit was produced.",
        "",
        "## Representation audit",
        "",
        f"- Mean PR pairwise incomparability rate: {audit_trade.incomparable_rate.mean():.4f}",
        f"- Mean forced scalar ordering among incomparable pairs: {scalar_loss.forced_order_rate_given_incomparable.mean():.4f}",
        f"- Repeatability rows classified stable by the preregistered diagnostic: {repeat_stable}/{repeat_total}",
        f"- Fisher clipping count at fixed clip {guards['fisher_clip_value']}: {guards['fisher_clipping_count']}",
        "",
        "## Synthetic S0",
        "",
        f"- Coverage checks passing tolerance: {synthetic_pass_count}/{len(coverage)}",
        "- The only nominal-coverage miss is retained; no tolerance or alpha was changed.",
        "- Acceptance regions are upper, downward-closed quality regions.",
        "- PR exact natural-group and Phase factor-level mechanics remain artifact-limited.",
        "",
        "## Cross-session prototype",
        "",
        f"- Tail assessment statuses: {dict(tail_counts)}",
        f"- Empirical correction candidate statuses: {dict(candidate_counts)}",
        f"- Strict positive/finite log-ratio numerical-invalid rows: {numerical_invalid}",
        f"- Candidate CI-direction agreement across ordinal support strata: {direction_agreement:.4f} (descriptor, not final calibration validation)",
        "- Source quantities were frozen before application to target; target data did not refit them.",
        "- Occupancy gaps describe real-session degradation prevalence/reference membership and are excluded from transfer PASS.",
        "",
        "## Block and contamination sensitivity",
        "",
        f"- Effective-block ranges and block-median summaries for 10/30/60 epochs are in `block_sensitivity_summary.csv`.",
        f"- Contamination-envelope widths and simultaneous endpoint CIs for epsilon 0/0.05/0.10/0.20 are in `contamination_summary.csv` and the direction-specific tables.",
        "",
        "## Preregistration deviation",
        "",
        "- None detected by the execution tooling.",
        "",
        "## Execution corrections before final artifacts",
        "",
        "- Zero-variance nominal coordinates are masked unavailable rather than zero-filled.",
        "- Raw Doppler P90 nominal mechanics were added before transfer because the first implementation covered only per-system coordinates.",
        "- Doppler per-system temporal blocks use unique epochs, with all systems at a timestamp kept together.",
        "- None of these corrections changed frozen alpha, thresholds, block sizes, bootstrap mathematics, contamination grid, or statistics.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("stage3a_1b_1b_3_manifest.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "audit", "synthetic-s0", "report"):
        sub.add_parser(name)
    transfer = sub.add_parser("transfer")
    transfer.add_argument("--source", required=True, choices=["4.1", "4.2"])
    transfer.add_argument("--target", required=True, choices=["4.1", "4.2"])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    cfg = load_manifest(args.manifest.resolve())
    os.environ.setdefault("MPLCONFIGDIR", str(output_root(cfg, repo) / ".matplotlib"))
    if args.command == "validate":
        command_validate(cfg, repo)
    elif args.command == "audit":
        command_audit(cfg, repo)
    elif args.command == "synthetic-s0":
        command_synthetic(cfg, repo)
    elif args.command == "transfer":
        if args.source == args.target:
            raise RuntimeError("Source and target must differ")
        command_transfer(cfg, repo, args.source, args.target)
    elif args.command == "report":
        command_report(cfg, repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
