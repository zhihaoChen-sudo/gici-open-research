#!/usr/bin/env python3
"""Stage 3A.1b-1b.4c-E frozen multi-session offline prototype.

Reads only first-solve-before Stage 3A shadow evidence from the development
panel.  It does not read 5.2, trajectory truth/performance, AR/FIX state, or
post-fit residuals, and never changes estimator/configuration files.
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

os.environ.setdefault("MPLCONFIGDIR", "/tmp/gici-stage3a1b1b4c-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import yaml


MANIFEST_ID = "S3A1b1b4cP-v1"
SYSTEMS = ("C", "E", "G", "R")
SOURCE_COLUMNS = {
    "timestamp",
    "pr_evaluation_attempt_count", "pr_finite_success_count",
    "pr_evaluation_failure_count", "pr_p90_abs_normalized",
    "pr_group_count", "pr_group_eligible_count", "pr_factor_eligible_count",
    "pr_insufficient_factor_ratio", "pr_group_shift_all_p90",
    "pr_group_scale_eligible_p90",
    "phase_evaluation_attempt_count", "phase_finite_success_count",
    "phase_evaluation_failure_count",
    "phase_total_count", "phase_both_continued_count",
    "phase_both_new_count", "phase_mixed_count", "phase_any_slip_count",
    "phase_unknown_count",
    "phase_both_continued_ratio", "phase_both_new_ratio",
    "phase_mixed_ratio", "phase_any_slip_ratio", "phase_unknown_ratio",
    "phase_continuity_conditioned_count",
    "phase_continuity_conditioned_p90_abs_normalized",
    "doppler_evaluation_attempt_count", "doppler_finite_success_count",
    "doppler_evaluation_failure_count", "doppler_p90_abs_normalized",
    "doppler_system_count", "doppler_minimum_system_support",
    "doppler_median_system_support",
}
DOPPLER_COLUMNS = {
    "timestamp", "system", "factor_count", "finite_count",
    "evaluation_failure_count", "center_normalized", "scale_normalized",
}


@dataclass(frozen=True)
class Coordinate:
    name: str
    channel: str
    source: str
    value: str
    support: str
    system: str = ""


COORDINATES = [
    Coordinate("pr_p90_abs_normalized", "PR", "source", "pr_p90_abs_normalized", "pr_finite_success_count"),
    Coordinate("pr_group_shift_all_p90", "PR", "source", "pr_group_shift_all_p90", "pr_group_count"),
    Coordinate("pr_group_scale_eligible_p90", "PR", "source", "pr_group_scale_eligible_p90", "pr_group_eligible_count"),
    Coordinate("phase_continuity_conditioned_p90_abs_normalized", "Phase", "source", "phase_continuity_conditioned_p90_abs_normalized", "phase_continuity_conditioned_count"),
    Coordinate("doppler_p90_abs_normalized", "Doppler", "source", "doppler_p90_abs_normalized", "doppler_finite_success_count"),
]
for _system in SYSTEMS:
    COORDINATES.extend([
        Coordinate(f"doppler_{_system}_center_abs", "Doppler", "doppler", "center_normalized", "finite_count", _system),
        Coordinate(f"doppler_{_system}_scale", "Doppler", "doppler", "scale_normalized", "finite_count", _system),
    ])


def json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def child_seed(master: int, *parts: Any) -> int:
    material = "||".join([str(master), *map(str, parts)]).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:16], "big")


def rng_for(cfg: dict[str, Any], *parts: Any) -> np.random.Generator:
    master = int(str(cfg["statistics"]["master_seed_hex"]), 16)
    return np.random.Generator(np.random.PCG64DXSM(child_seed(master, *parts)))


def load_manifest(path: Path) -> dict[str, Any]:
    cfg = yaml.safe_load(path.read_text())
    if cfg.get("manifest_id") != MANIFEST_ID or cfg.get("status") != "frozen":
        raise RuntimeError(f"Expected frozen {MANIFEST_ID} manifest")
    text = path.read_text()
    if "/5.2" in text or "dataset_5.2" not in cfg.get("forbidden_inputs", []):
        raise RuntimeError("Manifest path references forbidden 5.2 or lacks prohibition")
    if not cfg.get("not_runtime_parameter"):
        raise RuntimeError("Prototype constants must be marked non-runtime")
    return cfg


def output_root(cfg: dict[str, Any], repo: Path) -> Path:
    return repo / cfg["output_root"]


def one_file(root: Path, pattern: str, required: bool = True) -> Path | None:
    matches = sorted(root.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    if required:
        raise RuntimeError(f"Expected exactly one {pattern} in {root}, got {len(matches)}")
    return None


def read_selected(path: Path, columns: set[str]) -> pd.DataFrame:
    header = set(pd.read_csv(path, nrows=0).columns)
    missing = sorted(columns - header)
    if missing:
        raise RuntimeError(f"{path}: missing required columns {missing}")
    return pd.read_csv(path, usecols=sorted(columns), na_values=["nan", "-nan", "inf", "-inf"])


def percentile(values: Iterable[Any], p: float) -> float:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    return float(np.quantile(x, p, method="linear")) if len(x) else math.nan


def weighted_quantile(values: np.ndarray, weights: np.ndarray, p: float) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return math.nan
    x = values[valid]
    w = weights[valid]
    order = np.argsort(x, kind="mergesort")
    x, w = x[order], w[order]
    total = float(w.sum())
    if not np.isfinite(total) or total <= 0:
        return math.nan
    index = int(np.searchsorted(np.cumsum(w), p * total, side="left"))
    return float(x[min(index, len(x) - 1)])


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    return weighted_quantile(values, weights, 0.5)


def ratio_guard(numerator: float, denominator: float) -> tuple[float, str]:
    if not (
        np.isfinite(numerator) and np.isfinite(denominator)
        and numerator > 0 and denominator > 0
    ):
        return math.nan, "numerical-invalid/NotAssessed"
    return float(numerator / denominator), "valid"


def direction_from_ci(low: float, high: float) -> str:
    if not (np.isfinite(low) and np.isfinite(high)):
        return "NotAssessed"
    if low > 1:
        return "increase"
    if high < 1:
        return "decrease"
    return "neutral/indeterminate"


def load_panel(cfg: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    source: dict[str, pd.DataFrame] = {}
    doppler: dict[str, pd.DataFrame] = {}
    hashes = []
    for sequence, spec in cfg["primary_realizations"].items():
        root = Path(spec["root"])
        spath = one_file(root, cfg["input_selection"]["source_glob"])
        dpath = one_file(root, cfg["input_selection"]["doppler_glob"])
        assert spath is not None and dpath is not None
        sf = read_selected(spath, SOURCE_COLUMNS)
        df = read_selected(dpath, DOPPLER_COLUMNS)
        for frame in (sf, df):
            frame.insert(0, "sequence", sequence)
            frame.insert(1, "run", str(spec["run"]))
            frame.insert(2, "date_cluster", str(spec["acquisition_date"]))
        source[sequence], doppler[sequence] = sf, df
        for kind, path in (("source", spath), ("doppler_system", dpath)):
            hashes.append({
                "sequence": sequence, "run": spec["run"], "kind": kind,
                "path": str(path), "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return source, doppler, pd.DataFrame(hashes)


def epoch_block_map(frame: pd.DataFrame, block_size: int, gap_multiple: float, min_size: int) -> pd.DataFrame:
    timestamps = np.sort(pd.to_numeric(frame["timestamp"], errors="coerce").dropna().unique())
    if not len(timestamps):
        return pd.DataFrame(columns=["timestamp", "block_local", "block_epochs", "inferential"])
    delta = np.diff(timestamps)
    positive = delta[np.isfinite(delta) & (delta > 0)]
    median_dt = float(np.median(positive)) if len(positive) else math.inf
    breaks = np.r_[True, delta > gap_multiple * median_dt]
    segment = np.cumsum(breaks) - 1
    rows, block_id = [], 0
    for sid in np.unique(segment):
        indices = np.flatnonzero(segment == sid)
        for start in range(0, len(indices), block_size):
            chunk = indices[start:start + block_size]
            inferential = len(chunk) >= min_size
            for index in chunk:
                rows.append({
                    "timestamp": timestamps[index], "block_local": block_id,
                    "block_epochs": len(chunk), "inferential": inferential,
                })
            block_id += 1
    return pd.DataFrame(rows)


def coordinate_frames(
    cfg: dict[str, Any], source: dict[str, pd.DataFrame], doppler: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    block_size = int(cfg["statistics"]["primary_block_size_epochs"])
    min_size = int(cfg["statistics"]["inferential_minimum_block_epochs"])
    gap = float(cfg["statistics"]["segment_gap_multiple"])
    frames: dict[str, list[pd.DataFrame]] = {c.name: [] for c in COORDINATES}
    block_rows = []
    for sequence, sf in source.items():
        mapping = epoch_block_map(sf, block_size, gap, min_size)
        mapping["block_id"] = [f"{sequence}:{int(x)}" for x in mapping["block_local"]]
        for block_id, group in mapping.groupby("block_id", sort=False):
            block_rows.append({
                "sequence": sequence, "date_cluster": sf["date_cluster"].iloc[0],
                "block_id": block_id, "epochs": int(group["block_epochs"].iloc[0]),
                "inferential": bool(group["inferential"].iloc[0]),
                "timestamp_start": float(group["timestamp"].min()),
                "timestamp_end": float(group["timestamp"].max()),
            })
        block_columns = mapping[["timestamp", "block_id", "block_epochs", "inferential"]]
        for coordinate in COORDINATES:
            base = sf if coordinate.source == "source" else doppler[sequence]
            if coordinate.system:
                base = base[base["system"].astype(str) == coordinate.system]
            selected = base[["sequence", "run", "date_cluster", "timestamp", coordinate.value, coordinate.support]].copy()
            selected.columns = ["sequence", "run", "date_cluster", "timestamp", "value", "support"]
            if coordinate.name.endswith("center_abs"):
                selected["signed_value"] = selected["value"]
                selected["value"] = selected["value"].abs()
            else:
                selected["signed_value"] = np.nan
            selected = selected.merge(block_columns, on="timestamp", how="left", validate="many_to_one")
            selected["coordinate"] = coordinate.name
            selected["channel"] = coordinate.channel
            selected["system"] = coordinate.system
            frames[coordinate.name].append(selected)
    return {name: pd.concat(parts, ignore_index=True) for name, parts in frames.items()}, pd.DataFrame(block_rows)


def valid_frame(frame: pd.DataFrame, inferential: bool = True) -> pd.DataFrame:
    result = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["value", "support", "block_id"])
    result = result[result["support"] > 0]
    if inferential:
        result = result[result["inferential"]]
    return result.copy()


def aggregation_weights(frame: pd.DataFrame, aggregation: str) -> np.ndarray:
    if frame.empty:
        return np.array([], dtype=float)
    if aggregation == "sequence_balanced":
        sequences = sorted(frame["sequence"].unique())
        counts = frame.groupby("sequence").size().to_dict()
        return np.array([1.0 / len(sequences) / counts[x] for x in frame["sequence"]], dtype=float)
    if aggregation == "block_weighted":
        blocks = frame["block_id"].unique()
        counts = frame.groupby("block_id").size().to_dict()
        return np.array([1.0 / len(blocks) / counts[x] for x in frame["block_id"]], dtype=float)
    if aggregation == "date_balanced":
        dates = sorted(frame["date_cluster"].unique())
        seq_per_date = frame[["date_cluster", "sequence"]].drop_duplicates().groupby("date_cluster").size().to_dict()
        counts = frame.groupby("sequence").size().to_dict()
        return np.array([
            1.0 / len(dates) / seq_per_date[d] / counts[s]
            for d, s in zip(frame["date_cluster"], frame["sequence"])
        ], dtype=float)
    raise ValueError(aggregation)


def support_edges(frame: pd.DataFrame) -> np.ndarray:
    weights = aggregation_weights(frame, "sequence_balanced")
    q1 = weighted_quantile(frame["support"].to_numpy(float), weights, 1 / 3)
    q2 = weighted_quantile(frame["support"].to_numpy(float), weights, 2 / 3)
    finite_edges = sorted(set(x for x in (q1, q2) if np.isfinite(x)))
    return np.array([-np.inf, *finite_edges, np.inf], dtype=float)


def assign_cell(frame: pd.DataFrame, edges: np.ndarray) -> pd.DataFrame:
    result = frame.copy()
    result["support_cell"] = pd.cut(
        result["support"], edges, include_lowest=True, duplicates="drop", labels=False,
    )
    return result


def nominal_base_coordinate(name: str) -> str:
    if name.startswith("doppler_") and name.endswith("_center_abs"):
        return "doppler_system_center_abs"
    if name.startswith("doppler_") and name.endswith("_scale"):
        return "doppler_system_scale"
    return name


class NominalReference:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.cache: dict[tuple[Any, ...], np.ndarray] = {}
        self.rows: list[dict[str, Any]] = []

    def _normal_p90(self, rng: np.random.Generator, draws: int, n: int) -> np.ndarray:
        output = []
        batch = 5000
        for start in range(0, draws, batch):
            size = min(batch, draws - start)
            z = np.abs(rng.standard_normal((size, n)))
            output.append(np.quantile(z, 0.9, axis=1, method="linear"))
        return np.concatenate(output)

    def _center_or_scale(self, rng: np.random.Generator, draws: int, n: int, scale: bool) -> np.ndarray:
        output = []
        batch = 5000
        for start in range(0, draws, batch):
            size = min(batch, draws - start)
            z = rng.standard_normal((size, n))
            median = np.median(z, axis=1)
            if scale:
                value = 1.4826 * np.median(np.abs(z - median[:, None]), axis=1)
            else:
                value = np.abs(median)
            output.append(value)
        return np.concatenate(output)

    def _pr_group(self, rng: np.random.Generator, draws: int, groups: int, factors: int, scale: bool) -> np.ndarray:
        groups = max(1, groups)
        factors = max(groups * (4 if scale else 1), factors)
        sizes = np.full(groups, factors // groups, dtype=int)
        sizes[: factors % groups] += 1
        output = []
        batch = 2000
        for start in range(0, draws, batch):
            size = min(batch, draws - start)
            summaries = []
            for count in sizes:
                z = rng.standard_normal((size, int(count)))
                median = np.median(z, axis=1)
                if scale:
                    summaries.append(np.maximum(1.0, 1.4826 * np.median(np.abs(z - median[:, None]), axis=1)))
                else:
                    summaries.append(np.abs(median))
            output.append(np.quantile(np.column_stack(summaries), 0.9, axis=1, method="linear"))
        return np.concatenate(output)

    def distribution(self, coordinate: str, support: float, secondary: float) -> tuple[np.ndarray, int, int]:
        base = nominal_base_coordinate(coordinate)
        n = max(1, int(round(support)))
        m = max(1, int(round(secondary))) if np.isfinite(secondary) else n
        key = (base, n, m)
        if key in self.cache:
            return self.cache[key], n, m
        draws = int(self.cfg["statistics"]["synthetic_calibration_draws"])
        rng = rng_for(self.cfg, "4c", "nominal", *key)
        if base in {"pr_p90_abs_normalized", "phase_continuity_conditioned_p90_abs_normalized", "doppler_p90_abs_normalized"}:
            values = self._normal_p90(rng, draws, n)
        elif base == "pr_group_shift_all_p90":
            values = self._pr_group(rng, draws, n, m, False)
        elif base == "pr_group_scale_eligible_p90":
            values = self._pr_group(rng, draws, n, m, True)
        elif base == "doppler_system_center_abs":
            values = self._center_or_scale(rng, draws, n, False)
        elif base == "doppler_system_scale":
            values = self._center_or_scale(rng, draws, n, True)
        else:
            raise KeyError(base)
        self.cache[key] = values
        return values, n, m

    def threshold(self, coordinate: str, support: float, secondary: float, alpha: float) -> tuple[float, float, float, int, int]:
        values, n, m = self.distribution(coordinate, support, secondary)
        p = 1 - alpha
        q = percentile(values, p)
        probability_se = math.sqrt(p * (1 - p) / len(values))
        plow = max(0.0, p - 1.96 * probability_se)
        phigh = min(1.0, p + 1.96 * probability_se)
        return q, percentile(values, plow), percentile(values, phigh), n, m


def secondary_value(
    coordinate: str, sequence_frames: dict[str, pd.DataFrame], selected: pd.DataFrame, weights: np.ndarray,
) -> float:
    if coordinate not in {"pr_group_shift_all_p90", "pr_group_scale_eligible_p90"}:
        return math.nan
    column = "pr_finite_success_count" if coordinate == "pr_group_shift_all_p90" else "pr_factor_eligible_count"
    lookup_parts = []
    for sequence in selected["sequence"].unique():
        src = sequence_frames[sequence][["timestamp", column]].copy()
        src["sequence"] = sequence
        lookup_parts.append(src)
    lookup = pd.concat(lookup_parts, ignore_index=True)
    merged = selected[["sequence", "timestamp"]].merge(lookup, on=["sequence", "timestamp"], how="left", validate="many_to_one")
    return weighted_median(merged[column].to_numpy(float), weights)


def bootstrap_counts(frame: pd.DataFrame, reps: int, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, int]]:
    blocks = sorted(frame["block_id"].unique())
    block_index = {block: index for index, block in enumerate(blocks)}
    result = np.zeros((reps, len(blocks)), dtype=np.int16)
    sequence_block_counts: dict[str, int] = {}
    for sequence, group in frame[["sequence", "block_id"]].drop_duplicates().groupby("sequence"):
        ids = [block_index[x] for x in sorted(group["block_id"].unique())]
        count = len(ids)
        sequence_block_counts[str(sequence)] = count
        if count:
            result[:, ids] = rng.multinomial(count, np.full(count, 1 / count), size=reps)
    return result, sequence_block_counts


def bootstrap_quantiles(
    frame: pd.DataFrame, p_grid: list[float], aggregation: str,
    count_matrix: np.ndarray, global_block_index: dict[str, int], chunk: int = 100,
) -> np.ndarray:
    if frame.empty:
        return np.full((len(count_matrix), len(p_grid)), np.nan)
    ordered = frame.sort_values("value", kind="mergesort")
    values = ordered["value"].to_numpy(float)
    block_ids = np.array([global_block_index[x] for x in ordered["block_id"]], dtype=int)
    sequences = ordered["sequence"].astype(str).to_numpy()
    dates = ordered["date_cluster"].astype(str).to_numpy()
    unique_sequences = sorted(set(sequences))
    unique_dates = sorted(set(dates))
    seq_indices = {s: np.flatnonzero(sequences == s) for s in unique_sequences}
    date_sequences = {d: sorted(set(sequences[dates == d])) for d in unique_dates}
    block_row_count = Counter(ordered["block_id"])
    output = np.full((len(count_matrix), len(p_grid)), np.nan)
    for begin in range(0, len(count_matrix), chunk):
        end = min(len(count_matrix), begin + chunk)
        multiplicity = count_matrix[begin:end, block_ids].astype(float)
        weights = np.zeros_like(multiplicity)
        if aggregation == "sequence_balanced":
            for sequence, indices in seq_indices.items():
                denominator = multiplicity[:, indices].sum(axis=1)
                valid = denominator > 0
                weights[np.ix_(valid, indices)] = multiplicity[np.ix_(valid, indices)] / denominator[valid, None] / len(unique_sequences)
        elif aggregation == "date_balanced":
            for date, members in date_sequences.items():
                for sequence in members:
                    indices = seq_indices[sequence]
                    denominator = multiplicity[:, indices].sum(axis=1)
                    valid = denominator > 0
                    weights[np.ix_(valid, indices)] = multiplicity[np.ix_(valid, indices)] / denominator[valid, None] / len(members) / len(unique_dates)
        elif aggregation == "block_weighted":
            per_row = np.array([1.0 / block_row_count[x] for x in ordered["block_id"]])
            weights = multiplicity * per_row[None, :]
            denominator = weights.sum(axis=1)
            valid = denominator > 0
            weights[valid] /= denominator[valid, None]
        else:
            raise ValueError(aggregation)
        cumulative = np.cumsum(weights, axis=1)
        total = cumulative[:, -1]
        for column, p in enumerate(p_grid):
            target = p * total
            positions = np.argmax(cumulative >= target[:, None], axis=1)
            output[begin:end, column] = values[positions]
    return output


def full_tail_status(alpha: float, blocks: int, tail_blocks: int, sequences: int, dates: int) -> str:
    if np.isclose(alpha, 0.10):
        if blocks >= 20 and tail_blocks >= 10 and sequences >= 3 and dates >= 2:
            return "Eligible"
        if blocks >= 10 and tail_blocks >= 5 and sequences >= 2 and dates >= 2:
            return "Partial"
    elif np.isclose(alpha, 0.05):
        if blocks >= 40 and tail_blocks >= 10 and sequences >= 4 and dates >= 3:
            return "Eligible"
        if blocks >= 20 and tail_blocks >= 5 and sequences >= 3 and dates >= 2:
            return "Partial"
    elif np.isclose(alpha, 0.01):
        return "DiagnosticOnly" if tail_blocks >= 2 else "NotAssessed"
    return "DiagnosticOnly" if tail_blocks >= 2 else "NotAssessed"


def fold_status(alpha: float, blocks: int, tail_blocks: int, sequences: int, dates: int, max_share: float) -> str:
    if np.isclose(alpha, 0.10):
        if blocks >= 20 and tail_blocks >= 10 and sequences >= 3 and dates >= 2:
            return "Assessable"
        if blocks >= 10 and tail_blocks >= 5 and sequences >= 2 and dates >= 2:
            return "Partial"
    elif np.isclose(alpha, 0.05):
        if blocks >= 40 and tail_blocks >= 10 and sequences >= 4 and dates >= 2:
            return "Assessable"
        if blocks >= 20 and tail_blocks >= 5 and sequences >= 3 and dates >= 2:
            return "Partial"
    elif np.isclose(alpha, 0.01):
        if blocks >= 100 and tail_blocks >= 10 and sequences >= 5 and dates >= 2 and max_share <= 0.5:
            return "AssessableForUpgradeReview"
        return "DiagnosticOnly" if tail_blocks >= 2 else "NotAssessed"
    return "DiagnosticOnly" if tail_blocks >= 2 else "NotAssessed"


def tail_counts(frame: pd.DataFrame, threshold: float) -> tuple[int, int, int, int, float]:
    if frame.empty or not np.isfinite(threshold):
        return 0, 0, 0, 0, math.nan
    tail = frame[frame["value"] >= threshold]
    blocks = int(frame["block_id"].nunique())
    tail_blocks = int(tail["block_id"].nunique())
    tail_sequences = int(tail["sequence"].nunique())
    tail_dates = int(tail["date_cluster"].nunique())
    shares = tail[["sequence", "block_id"]].drop_duplicates()["sequence"].value_counts()
    max_share = float(shares.max() / tail_blocks) if tail_blocks else math.nan
    return blocks, tail_blocks, tail_sequences, tail_dates, max_share


def simultaneous_log_ci(estimates: np.ndarray, bootstrap: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, int]:
    valid = np.isfinite(estimates) & (estimates > 0) & np.isfinite(bootstrap).any(axis=0)
    low = np.full(len(estimates), np.nan)
    high = np.full(len(estimates), np.nan)
    se = np.full(len(estimates), np.nan)
    if not valid.any():
        return low, high, se, math.nan, int((~valid).sum())
    point = np.log(estimates[valid])
    boot = np.where((bootstrap[:, valid] > 0) & np.isfinite(bootstrap[:, valid]), np.log(bootstrap[:, valid]), np.nan)
    std = np.nanstd(boot, axis=0, ddof=1)
    usable = np.isfinite(std) & (std > 0)
    z = np.full_like(boot, np.nan)
    z[:, usable] = np.abs((boot[:, usable] - point[usable]) / std[usable])
    row_valid = np.isfinite(z).any(axis=1)
    maxz = np.nanmax(z[row_valid], axis=1) if row_valid.any() else np.array([])
    critical = percentile(maxz, 0.95) if len(maxz) else math.nan
    valid_positions = np.flatnonzero(valid)
    for local, global_position in enumerate(valid_positions):
        se[global_position] = std[local]
        if std[local] == 0:
            low[global_position] = high[global_position] = estimates[global_position]
        elif np.isfinite(critical):
            low[global_position] = math.exp(point[local] - critical * std[local])
            high[global_position] = math.exp(point[local] + critical * std[local])
    return low, high, se, critical, int((~valid).sum())


def fit_analysis(
    cfg: dict[str, Any], name: str, kind: str, sequences: list[str], aggregation: str,
    frames: dict[str, pd.DataFrame], source: dict[str, pd.DataFrame], nominal: NominalReference,
    boundaries_override: dict[str, np.ndarray] | None = None,
    contamination: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    """Fit frozen real/nominal mismatch candidates on training sequences only."""
    alphas = [float(x) for x in cfg["statistics"]["alpha_grid"]]
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    boundaries: dict[str, np.ndarray] = {}
    boundary_rows = []
    for coordinate in COORDINATES:
        frame = valid_frame(frames[coordinate.name])
        frame = frame[frame["sequence"].isin(sequences)]
        edges = (
            np.asarray(boundaries_override[coordinate.name], dtype=float)
            if boundaries_override is not None and coordinate.name in boundaries_override
            else support_edges(frame)
        )
        boundaries[coordinate.name] = edges
        for index in range(len(edges) - 1):
            boundary_rows.append({
                "analysis": name, "coordinate": coordinate.name,
                "support_primary_variable": cfg["coordinate_contract"][nominal_base_coordinate(coordinate.name)]["primary_support_variable"],
                "support_cell": index, "lower": edges[index], "upper": edges[index + 1],
                "rebuilt_from_training_only": boundaries_override is None,
            })

    result_rows: list[dict[str, Any]] = []
    boot_columns: list[np.ndarray] = []
    contamination_specs: list[dict[str, Any]] = []
    ci_family_meta: list[dict[str, Any]] = []
    for channel in ("PR", "Phase", "Doppler"):
        channel_coordinates = [x for x in COORDINATES if x.channel == channel]
        union_blocks = []
        for coordinate in channel_coordinates:
            f = valid_frame(frames[coordinate.name])
            f = f[f["sequence"].isin(sequences)]
            union_blocks.append(f[["sequence", "block_id"]])
        union = pd.concat(union_blocks, ignore_index=True).drop_duplicates()
        rng = rng_for(cfg, "bootstrap", name, aggregation, channel)
        count_matrix, _ = bootstrap_counts(union, reps, rng)
        global_blocks = sorted(union["block_id"].unique())
        global_block_index = {block: index for index, block in enumerate(global_blocks)}
        family_start = len(result_rows)
        for coordinate in channel_coordinates:
            all_coordinate = frames[coordinate.name]
            infer = valid_frame(all_coordinate)
            infer = infer[infer["sequence"].isin(sequences)]
            infer = assign_cell(infer, boundaries[coordinate.name])
            descriptive = valid_frame(all_coordinate, inferential=False)
            descriptive = descriptive[descriptive["sequence"].isin(sequences)]
            descriptive = assign_cell(descriptive, boundaries[coordinate.name])
            for cell_index in sorted(x for x in infer["support_cell"].dropna().unique()):
                cell = infer[infer["support_cell"] == cell_index].copy()
                desc_cell = descriptive[descriptive["support_cell"] == cell_index]
                if cell.empty:
                    continue
                weights = aggregation_weights(cell, aggregation)
                representative_support = weighted_median(cell["support"].to_numpy(float), weights)
                secondary = secondary_value(coordinate.name, source, cell, weights)
                p_grid = sorted(set(
                    [1 - alpha for alpha in alphas]
                    + ([
                        float(np.clip((1 - epsilon) * (1 - alpha), 0, 1))
                        for epsilon in cfg["statistics"]["contamination_epsilon_grid"] for alpha in alphas
                    ] + [
                        float(np.clip(epsilon + (1 - epsilon) * (1 - alpha), 0, 1))
                        for epsilon in cfg["statistics"]["contamination_epsilon_grid"] for alpha in alphas
                    ] if contamination else [])
                ))
                boot_q = bootstrap_quantiles(cell, p_grid, aggregation, count_matrix, global_block_index)
                q_column = {p: index for index, p in enumerate(p_grid)}
                for alpha in alphas:
                    p = 1 - alpha
                    real_q = weighted_quantile(cell["value"].to_numpy(float), weights, p)
                    desc_weights = aggregation_weights(desc_cell, aggregation)
                    descriptive_q = weighted_quantile(desc_cell["value"].to_numpy(float), desc_weights, p)
                    nominal_q, nominal_low, nominal_high, support_n, secondary_n = nominal.threshold(
                        coordinate.name, representative_support, secondary, alpha,
                    )
                    ratio, numerical = ratio_guard(real_q, nominal_q)
                    boot_ratio = np.array([ratio_guard(x, nominal_q)[0] for x in boot_q[:, q_column[p]]])
                    blocks, tail_blocks, tail_sequences, tail_dates, max_share = tail_counts(cell, real_q)
                    if kind == "full_panel":
                        tail_status = full_tail_status(alpha, blocks, tail_blocks, tail_sequences, tail_dates)
                        full_status = tail_status
                        assessability = "NotApplicable"
                    else:
                        tail_status = fold_status(alpha, blocks, tail_blocks, tail_sequences, tail_dates, max_share)
                        full_status = "NotApplicable_fold_is_not_full_panel"
                        assessability = tail_status
                    fidelity = cfg["coordinate_contract"][nominal_base_coordinate(coordinate.name)]["nominal_reference_fidelity"]
                    occupancy = float(np.average(cell["value"] <= nominal_q, weights=weights)) if np.isfinite(nominal_q) else math.nan
                    row_index = len(result_rows)
                    result_rows.append({
                        "analysis": name, "analysis_kind": kind, "aggregation": aggregation,
                        "channel": channel, "coordinate": coordinate.name, "support_cell": int(cell_index),
                        "support_primary_variable": cfg["coordinate_contract"][nominal_base_coordinate(coordinate.name)]["primary_support_variable"],
                        "source_sequences": ";".join(sorted(sequences)), "source_sequence_count": len(sequences),
                        "source_date_count": int(cell["date_cluster"].nunique()),
                        "inferential_n": len(cell), "descriptive_all_epoch_n": len(desc_cell),
                        "representative_primary_support": representative_support,
                        "representative_secondary_support": secondary,
                        "nominal_support_n": support_n, "nominal_secondary_n": secondary_n,
                        "alpha": alpha, "real_inferential_upper_quantile": real_q,
                        "real_descriptive_upper_quantile": descriptive_q,
                        "q_nominal": nominal_q, "q_nominal_mc95_low": nominal_low,
                        "q_nominal_mc95_high": nominal_high,
                        "nominal_reference_fidelity": fidelity,
                        "nominal_mismatch_ratio": ratio, "numerical_status": numerical,
                        "reference_region_membership_occupancy": occupancy,
                        "occupancy_is_calibration_coverage": False,
                        "effective_blocks": blocks, "tail_containing_blocks": tail_blocks,
                        "tail_containing_physical_sequences": tail_sequences,
                        "tail_containing_date_clusters": tail_dates,
                        "maximum_single_sequence_tail_share": max_share,
                        "FullPanelTailStatus": full_status, "FoldAssessability": assessability,
                        "empirical_correction_candidate": True,
                        "normative_correction": False, "row_index": row_index,
                    })
                    boot_columns.append(boot_ratio)
                    if contamination:
                        for epsilon in [float(x) for x in cfg["statistics"]["contamination_epsilon_grid"]]:
                            low_p = float(np.clip((1 - epsilon) * p, 0, 1))
                            high_p = float(np.clip(epsilon + (1 - epsilon) * p, 0, 1))
                            low_q = weighted_quantile(cell["value"].to_numpy(float), weights, low_p)
                            high_q = weighted_quantile(cell["value"].to_numpy(float), weights, high_p)
                            low_ratio, low_num = ratio_guard(low_q, nominal_q)
                            high_ratio, high_num = ratio_guard(high_q, nominal_q)
                            contamination_specs.append({
                                "row_index": row_index, "analysis": name, "channel": channel,
                                "coordinate": coordinate.name, "support_cell": int(cell_index), "alpha": alpha,
                                "epsilon_sensitivity": epsilon,
                                "candidate_ratio_lower_endpoint": low_ratio,
                                "candidate_ratio_upper_endpoint": high_ratio,
                                "lower_numerical_status": low_num, "upper_numerical_status": high_num,
                                "boot_low": np.array([ratio_guard(x, nominal_q)[0] for x in boot_q[:, q_column[low_p]]]),
                                "boot_high": np.array([ratio_guard(x, nominal_q)[0] for x in boot_q[:, q_column[high_p]]]),
                                "hierarchy": "within_sequence_temporal_block_bootstrap_then_equal_sequence_mixture_CDF_contamination_envelope",
                            })
        family_end = len(result_rows)
        if family_end > family_start:
            positions = np.arange(family_start, family_end)
            points = np.array([result_rows[x]["nominal_mismatch_ratio"] for x in positions], dtype=float)
            matrix = np.column_stack([boot_columns[x] for x in positions])
            low, high, se, critical, invalid = simultaneous_log_ci(points, matrix)
            for local, position in enumerate(positions):
                result_rows[position]["candidate_simultaneous_ci_low"] = low[local]
                result_rows[position]["candidate_simultaneous_ci_high"] = high[local]
                result_rows[position]["candidate_bootstrap_se_log"] = se[local]
                result_rows[position]["candidate_direction"] = direction_from_ci(low[local], high[local])
            ci_family_meta.append({
                "analysis": name, "aggregation": aggregation, "channel": channel,
                "family_start_row": family_start, "family_end_row_exclusive": family_end,
                "family_size": family_end - family_start, "simultaneous_critical_95": critical,
                "numerical_invalid_members": invalid,
                "family_definition": "channel_x_analysis-mode-or-fold_x_aggregation_all_coordinate_x_support-cell_x_alpha",
            })

    results = pd.DataFrame(result_rows)
    contamination_rows = []
    if contamination_specs:
        for endpoint in ("low", "high"):
            for channel in ("PR", "Phase", "Doppler"):
                selected = [x for x in contamination_specs if x["channel"] == channel]
                if not selected:
                    continue
                point = np.array([x[f"candidate_ratio_{'lower' if endpoint == 'low' else 'upper'}_endpoint"] for x in selected])
                boot = np.column_stack([x[f"boot_{endpoint}"] for x in selected])
                low, high, _, critical, _ = simultaneous_log_ci(point, boot)
                for index, spec in enumerate(selected):
                    spec[f"{endpoint}_simultaneous_ci_low"] = low[index]
                    spec[f"{endpoint}_simultaneous_ci_high"] = high[index]
                    spec[f"{endpoint}_simultaneous_critical_95"] = critical
        for spec in contamination_specs:
            contamination_rows.append({k: v for k, v in spec.items() if not k.startswith("boot_")})
    return results, pd.DataFrame(boundary_rows), pd.DataFrame(contamination_rows), boundaries


def apply_frozen_to_target(
    fit: pd.DataFrame, target_sequence: str, frames: dict[str, pd.DataFrame], boundaries: dict[str, np.ndarray],
) -> pd.DataFrame:
    rows = []
    for _, candidate in fit.iterrows():
        frame = valid_frame(frames[candidate.coordinate])
        frame = frame[frame["sequence"] == target_sequence]
        frame = assign_cell(frame, boundaries[candidate.coordinate])
        cell = frame[frame["support_cell"] == int(candidate.support_cell)]
        nominal = float(candidate.q_nominal)
        ratio = float(candidate.nominal_mismatch_ratio)
        threshold = nominal * max(1.0, ratio) if np.isfinite(nominal) and np.isfinite(ratio) else math.nan
        rows.append({
            "analysis": candidate.analysis, "target_sequence": target_sequence,
            "channel": candidate.channel, "coordinate": candidate.coordinate,
            "support_cell": candidate.support_cell, "alpha": candidate.alpha,
            "target_n": len(cell),
            "target_nominal_membership_occupancy": float(np.mean(cell.value <= nominal)) if len(cell) and np.isfinite(nominal) else math.nan,
            "target_candidate_membership_occupancy": float(np.mean(cell.value <= threshold)) if len(cell) and np.isfinite(threshold) else math.nan,
            "occupancy_is_transfer_correctness_target": False,
            "target_refit": False,
        })
    return pd.DataFrame(rows)


def contamination_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result["point_envelope_fold_width"] = result["candidate_ratio_upper_endpoint"] / result["candidate_ratio_lower_endpoint"]
    result["sampling_and_contamination_low"] = np.minimum(
        result["candidate_ratio_lower_endpoint"], result["low_simultaneous_ci_low"],
    )
    result["sampling_and_contamination_high"] = np.maximum(
        result["candidate_ratio_upper_endpoint"], result["high_simultaneous_ci_high"],
    )
    result["combined_envelope_fold_width"] = result["sampling_and_contamination_high"] / result["sampling_and_contamination_low"]
    return result


def freeze_nominal_reference(sensitivity: pd.DataFrame, primary: pd.DataFrame) -> pd.DataFrame:
    """Keep primary S0 reference while changing only empirical aggregation weight."""
    keys = ["channel", "coordinate", "support_cell", "alpha"]
    reference = primary[keys + ["q_nominal", "q_nominal_mc95_low", "q_nominal_mc95_high"]].rename(
        columns={x: f"primary_{x}" for x in ("q_nominal", "q_nominal_mc95_low", "q_nominal_mc95_high")}
    )
    result = sensitivity.merge(reference, on=keys, how="left", validate="one_to_one")
    scale = result["q_nominal"] / result["primary_q_nominal"]
    for column in ("nominal_mismatch_ratio", "candidate_simultaneous_ci_low", "candidate_simultaneous_ci_high"):
        result[column] = result[column] * scale
    result["q_nominal"] = result.pop("primary_q_nominal")
    result["q_nominal_mc95_low"] = result.pop("primary_q_nominal_mc95_low")
    result["q_nominal_mc95_high"] = result.pop("primary_q_nominal_mc95_high")
    result["candidate_direction"] = [
        direction_from_ci(low, high)
        for low, high in zip(result["candidate_simultaneous_ci_low"], result["candidate_simultaneous_ci_high"])
    ]
    result["nominal_reference_frozen_from_primary"] = True
    return result


def command_validate(cfg: dict[str, Any], repo: Path) -> None:
    out = output_root(cfg, repo) / "validate"
    out.mkdir(parents=True, exist_ok=True)
    source, doppler, hashes = load_panel(cfg)
    hashes.to_csv(out / "input_hashes.csv", index=False)
    rows, errors = [], []
    for sequence in cfg["primary_realizations"]:
        sf, df = source[sequence], doppler[sequence]
        timestamp_ok = bool(sf["timestamp"].notna().all() and sf["timestamp"].is_monotonic_increasing and not sf["timestamp"].duplicated().any())
        doppler_order = bool(df["timestamp"].notna().all() and df["timestamp"].is_monotonic_increasing)
        source_failures = int(sf[["pr_evaluation_failure_count", "phase_evaluation_failure_count", "doppler_evaluation_failure_count"]].sum().sum())
        doppler_failures = int(df["evaluation_failure_count"].sum())
        closure = {}
        for prefix in ("pr", "doppler"):
            closure[prefix] = bool((
                sf[f"{prefix}_evaluation_attempt_count"]
                - sf[f"{prefix}_finite_success_count"]
                - sf[f"{prefix}_evaluation_failure_count"]
            ).eq(0).all())
        phase_closure = bool((
            sf["phase_total_count"]
            - sf["phase_both_continued_count"]
            - sf["phase_both_new_count"] - sf["phase_mixed_count"]
            - sf["phase_any_slip_count"] - sf["phase_unknown_count"]
        ).eq(0).all())
        row = {
            "sequence": sequence, "primary_run": cfg["primary_realizations"][sequence]["run"],
            "source_epochs": len(sf), "doppler_system_rows": len(df),
            "source_timestamp_order_unique": timestamp_ok, "doppler_timestamp_order": doppler_order,
            "pr_count_closure": closure["pr"], "phase_provenance_count_closure": phase_closure,
            "doppler_count_closure": closure["doppler"],
            "source_evaluation_failures": source_failures,
            "doppler_system_evaluation_failures": doppler_failures,
            "forbidden_columns_loaded": False,
        }
        rows.append(row)
        if not all((timestamp_ok, doppler_order, closure["pr"], phase_closure, closure["doppler"])):
            errors.append(f"{sequence}: primary input integrity failure")
    pd.DataFrame(rows).to_csv(out / "primary_validation.csv", index=False)
    environment = {
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
        "manifest_sha256": sha256(repo / "tools/research/stage3a_1b_1b_4c_manifest.yaml"),
        "forbidden_5.2_read": False, "GT_APE_AR_FIX_read": False,
    }
    write_json(out / "environment.json", environment)
    write_json(out / "validation_report.json", {"status": "PASS" if not errors else "FAIL", "errors": errors})
    if errors:
        raise RuntimeError("; ".join(errors))


def repeat_table(source_frame: pd.DataFrame, doppler_frame: pd.DataFrame) -> pd.DataFrame:
    fields = [x for x in COORDINATES if x.source == "source"]
    table = source_frame[["timestamp", *[x.value for x in fields]]].copy()
    table.columns = ["timestamp", *[x.name for x in fields]]
    for system in SYSTEMS:
        part = doppler_frame[doppler_frame.system.astype(str) == system][
            ["timestamp", "center_normalized", "scale_normalized"]
        ].copy()
        part[f"doppler_{system}_center_abs"] = part.pop("center_normalized").abs()
        part.rename(columns={"scale_normalized": f"doppler_{system}_scale"}, inplace=True)
        table = table.merge(part, on="timestamp", how="left", validate="one_to_one")
    return table


def paired_repeat_bootstrap(
    cfg: dict[str, Any], merged: pd.DataFrame, coordinates: list[str], seed_parts: tuple[Any, ...],
) -> tuple[list[dict[str, Any]], int]:
    block_size = int(cfg["statistics"]["primary_block_size_epochs"])
    mapping = epoch_block_map(
        merged, block_size, float(cfg["statistics"]["segment_gap_multiple"]),
        int(cfg["statistics"]["inferential_minimum_block_epochs"]),
    )
    merged = merged.merge(mapping[["timestamp", "block_local", "inferential"]], on="timestamp", how="left")
    merged = merged[merged.inferential]
    blocks = [x.index.to_numpy() for _, x in merged.groupby("block_local")]
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    clip = float(cfg["statistics"]["fisher_rho_clip"])
    clip_count = 0
    point, boot = [], np.full((reps, len(coordinates)), np.nan)

    def fisher(rho: float) -> float:
        nonlocal clip_count
        if not np.isfinite(rho):
            return math.nan
        clipped = float(np.clip(rho, -clip, clip))
        if clipped != rho:
            clip_count += 1
        return float(np.arctanh(clipped))

    for coordinate in coordinates:
        valid = merged[[f"{coordinate}_a", f"{coordinate}_b"]].dropna()
        rho = stats.spearmanr(valid.iloc[:, 0], valid.iloc[:, 1]).statistic if len(valid) >= 3 else math.nan
        point.append(fisher(float(rho)))
    rng = rng_for(cfg, "repeat", *seed_parts)
    for repeat in range(reps):
        selected = rng.integers(0, len(blocks), len(blocks)) if blocks else []
        indices = np.concatenate([blocks[x] for x in selected]) if len(selected) else np.array([], int)
        sample = merged.loc[indices]
        for index, coordinate in enumerate(coordinates):
            valid = sample[[f"{coordinate}_a", f"{coordinate}_b"]].dropna()
            rho = stats.spearmanr(valid.iloc[:, 0], valid.iloc[:, 1]).statistic if len(valid) >= 3 else math.nan
            boot[repeat, index] = fisher(float(rho))
    point_array = np.asarray(point)
    se = np.nanstd(boot, axis=0, ddof=1)
    z = np.full_like(boot, np.nan)
    usable = np.isfinite(se) & (se > 0) & np.isfinite(point_array)
    z[:, usable] = np.abs((boot[:, usable] - point_array[usable]) / se[usable])
    valid_rows = np.isfinite(z).any(axis=1)
    critical = percentile(np.nanmax(z[valid_rows], axis=1), .95) if valid_rows.any() else math.nan
    rows = []
    for index, coordinate in enumerate(coordinates):
        rho = math.tanh(point_array[index]) if np.isfinite(point_array[index]) else math.nan
        if se[index] == 0:
            low = high = rho
        elif np.isfinite(critical) and np.isfinite(point_array[index]):
            low = math.tanh(point_array[index] - critical * se[index])
            high = math.tanh(point_array[index] + critical * se[index])
        else:
            low = high = math.nan
        valid = merged[[f"{coordinate}_a", f"{coordinate}_b"]].dropna()
        rows.append({
            "coordinate": coordinate, "matched_valid_epochs": len(valid), "spearman": rho,
            "simultaneous_ci_low": low, "simultaneous_ci_high": high,
            "bootstrap_se_fisher": se[index], "effective_blocks": len(blocks),
            "bootstrap_replicates": reps,
        })
    return rows, clip_count


def repeat_audit(cfg: dict[str, Any], primary_source: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    inventory, metrics = [], []
    clip_count = 0
    for sequence in ("4.1", "4.2"):
        available: dict[str, pd.DataFrame] = {}
        for run, root_text in cfg["repeat_sensitivity"][sequence].items():
            root = Path(root_text)
            path = one_file(root, cfg["input_selection"]["source_glob"], required=False)
            doppler_path = one_file(root, cfg["input_selection"]["doppler_glob"], required=False)
            complete = path is not None and doppler_path is not None
            inventory.append({
                "sequence": sequence, "run": run, "root": str(root),
                "available": complete, "source_path": str(path) if path else "",
                "doppler_path": str(doppler_path) if doppler_path else "",
                "status": "Available" if complete else "NotAssessed_missing_artifact",
            })
            if complete:
                available[run] = repeat_table(
                    read_selected(path, SOURCE_COLUMNS), read_selected(doppler_path, DOPPLER_COLUMNS),
                )
        labels = sorted(available)
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                merged = available[labels[i]].merge(
                    available[labels[j]], on="timestamp", how="inner", suffixes=("_a", "_b"),
                    validate="one_to_one",
                )
                coordinates = [x.name for x in COORDINATES]
                rows, clips = paired_repeat_bootstrap(
                    cfg, merged, coordinates, (sequence, labels[i], labels[j]),
                )
                clip_count += clips
                for row in rows:
                    row.update({
                        "sequence": sequence, "run_a": labels[i], "run_b": labels[j],
                        "repeat_role": "nested_sensitivity_not_panel_weight",
                    })
                    metrics.append(row)
    return pd.DataFrame(inventory), pd.DataFrame(metrics), clip_count


def command_audit(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    if json.loads((root / "validate/validation_report.json").read_text())["status"] != "PASS":
        raise RuntimeError("validate must pass first")
    out = root / "audit"
    out.mkdir(parents=True, exist_ok=True)
    source, doppler, _ = load_panel(cfg)
    frames, blocks = coordinate_frames(cfg, source, doppler)
    blocks.to_csv(out / "primary_block_inventory.csv", index=False)
    distribution_rows, support_rows = [], []
    for coordinate in COORDINATES:
        for sequence in cfg["primary_realizations"]:
            full = frames[coordinate.name]
            part = full[full["sequence"] == sequence]
            valid_all = valid_frame(part, inferential=False)
            valid_inf = valid_frame(part)
            distribution_rows.append({
                "sequence": sequence, "channel": coordinate.channel, "coordinate": coordinate.name,
                "rows": len(part), "valid_all": len(valid_all), "valid_rate": len(valid_all) / len(part) if len(part) else math.nan,
                "inferential_rows": len(valid_inf), "q50": percentile(valid_all.value, .5),
                "q90": percentile(valid_all.value, .9), "q95": percentile(valid_all.value, .95),
                "q99": percentile(valid_all.value, .99), "max": percentile(valid_all.value, 1),
            })
            support_rows.append({
                "sequence": sequence, "channel": coordinate.channel, "coordinate": coordinate.name,
                "primary_support_variable": cfg["coordinate_contract"][nominal_base_coordinate(coordinate.name)]["primary_support_variable"],
                "support_min": percentile(valid_all.support, 0), "support_q10": percentile(valid_all.support, .1),
                "support_median": percentile(valid_all.support, .5), "support_q90": percentile(valid_all.support, .9),
                "support_max": percentile(valid_all.support, 1),
            })
    pd.DataFrame(distribution_rows).to_csv(out / "per_sequence_coordinate_distributions.csv", index=False)
    pd.DataFrame(support_rows).to_csv(out / "per_sequence_primary_support.csv", index=False)

    pr_mask_rows, tradeoff_rows = [], []
    pr_names = [x.name for x in COORDINATES if x.channel == "PR"]
    for sequence, sf in source.items():
        mask = sf[pr_names].apply(np.isfinite).astype(int).astype(str).agg("".join, axis=1)
        for pattern, count in mask.value_counts().items():
            pr_mask_rows.append({"sequence": sequence, "mask": pattern, "count": count, "rate": count / len(sf)})
        valid = sf[pr_names].replace([np.inf, -np.inf], np.nan).dropna()
        samples = int(cfg["statistics"]["scalar_pair_samples"])
        if len(valid) >= 2:
            rng = rng_for(cfg, "audit", "pr_incomparability", sequence)
            ia, ib = rng.integers(0, len(valid), samples), rng.integers(0, len(valid), samples)
            values = valid.to_numpy(float)
            iqr = np.subtract(*np.percentile(values, [75, 25], axis=0))
            deadband = np.maximum(1e-12, 0.01 * iqr)
            delta = values[ia] - values[ib]
            incomparable = (delta > deadband).any(axis=1) & (delta < -deadband).any(axis=1)
            ranks = valid.rank(pct=True).to_numpy(float)
            score = ranks.max(axis=1)
            forced = incomparable & (np.abs(score[ia] - score[ib]) > 1e-12)
            tradeoff_rows.append({
                "sequence": sequence, "sampled_within_run_state_pairs": samples,
                "incomparable_count": int(incomparable.sum()), "incomparability_rate": float(incomparable.mean()),
                "forced_scalar_order_rate_given_incomparable": float(forced.sum() / max(1, incomparable.sum())),
                "interpretation": "within_run_state_pair_incomparability_not_same_timestamp_repeat_disagreement",
            })
    pd.DataFrame(pr_mask_rows).to_csv(out / "pr_valid_masks.csv", index=False)
    pd.DataFrame(tradeoff_rows).to_csv(out / "within_run_state_pair_incomparability.csv", index=False)

    doppler_mask_rows = []
    for sequence, df in doppler.items():
        pivot = df.pivot_table(index="timestamp", columns="system", values="finite_count", aggfunc="sum")
        for system in SYSTEMS:
            if system not in pivot:
                pivot[system] = np.nan
        mask = pivot[list(SYSTEMS)].notna().astype(int).astype(str).agg("".join, axis=1)
        for pattern, count in mask.value_counts().items():
            doppler_mask_rows.append({
                "sequence": sequence, "canonical_system_order": "CEGR", "valid_system_mask": pattern,
                "count": count, "rate": count / len(pivot), "missing_filled_zero": False,
            })
    pd.DataFrame(doppler_mask_rows).to_csv(out / "doppler_system_masks.csv", index=False)

    inventory, repeat_metrics, fisher_clips = repeat_audit(cfg, source)
    inventory.to_csv(out / "repeat_artifact_inventory.csv", index=False)
    repeat_metrics.to_csv(out / "repeat_sensitivity.csv", index=False)
    write_json(out / "numerical_guards.json", {
        "fisher_rho_clip": cfg["statistics"]["fisher_rho_clip"],
        "fisher_clipping_count": fisher_clips,
        "log_ratio_requires_strict_positive_finite": True,
        "log_ratio_epsilon_added": False,
    })

    block_sensitivity = []
    for size in cfg["statistics"]["block_sizes_epochs"]:
        for sequence, sf in source.items():
            mapping = epoch_block_map(sf, int(size), float(cfg["statistics"]["segment_gap_multiple"]), int(math.ceil(int(size) * .5)))
            block_sensitivity.append({
                "sequence": sequence, "block_size_epochs": size,
                "all_blocks": int(mapping.block_local.nunique()),
                "inferential_blocks": int(mapping.loc[mapping.inferential, "block_local"].nunique()),
                "descriptive_only_epochs": int((~mapping.inferential).sum()),
            })
    pd.DataFrame(block_sensitivity).to_csv(out / "block_size_sensitivity.csv", index=False)
    write_json(out / "representation_contract.json", {
        "PR": "three-coordinate multivariate partial order; no mandatory scalar",
        "Phase": "conditioned P90 one-sided upper tail",
        "Doppler": "fixed C/E/G/R slots and valid mask; abs center quality; signed direction attribution",
        "artifact_limits": cfg["artifact_limitations"],
    })


def write_fit(root: Path, name: str, fit: pd.DataFrame, boundaries: pd.DataFrame, contamination: pd.DataFrame | None = None) -> None:
    out = root / name
    out.mkdir(parents=True, exist_ok=True)
    fit.to_csv(out / "assessment.csv", index=False)
    boundaries.to_csv(out / "support_boundaries.csv", index=False)
    if contamination is not None:
        contamination_summary(contamination).to_csv(out / "contamination_sensitivity.csv", index=False)


def command_analyze(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    if not (root / "audit/representation_contract.json").exists():
        raise RuntimeError("audit must run first")
    out = root / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    source, doppler, _ = load_panel(cfg)
    frames, _ = coordinate_frames(cfg, source, doppler)
    nominal = NominalReference(cfg)
    all_sequences = list(cfg["primary_realizations"])

    primary, primary_edges, primary_contamination, boundaries = fit_analysis(
        cfg, "full_panel_primary", "full_panel", all_sequences, "sequence_balanced",
        frames, source, nominal, contamination=True,
    )
    write_fit(out, "full_panel_primary", primary, primary_edges, primary_contamination)

    aggregation_fits = [primary.assign(sensitivity_name="sequence_balanced")]
    for aggregation in ("block_weighted", "date_balanced"):
        fit, edge_table, _, _ = fit_analysis(
            cfg, f"full_panel_{aggregation}", "full_panel", all_sequences, aggregation,
            frames, source, nominal, boundaries_override=boundaries,
        )
        fit = freeze_nominal_reference(fit, primary)
        fit["sensitivity_name"] = aggregation
        write_fit(out, f"full_panel_{aggregation}", fit, edge_table)
        aggregation_fits.append(fit)
    pd.concat(aggregation_fits, ignore_index=True).to_csv(out / "aggregation_sensitivity.csv", index=False)

    loso_fits, loso_targets = [], []
    for target in all_sequences:
        training = [x for x in all_sequences if x != target]
        fit, edge_table, _, fold_boundaries = fit_analysis(
            cfg, f"LOSO_hold_{target}", "LOSO", training, "sequence_balanced",
            frames, source, nominal,
        )
        write_fit(out, f"loso/hold_{target}", fit, edge_table)
        loso_fits.append(fit.assign(held_out_sequence=target))
        loso_targets.append(apply_frozen_to_target(fit, target, frames, fold_boundaries))
    pd.concat(loso_fits, ignore_index=True).to_csv(out / "loso_training_candidates.csv", index=False)
    pd.concat(loso_targets, ignore_index=True).to_csv(out / "loso_target_application.csv", index=False)

    ldo_fits, ldo_targets = [], []
    for held_date, targets in cfg["acquisition_date_clusters"].items():
        training = [x for x in all_sequences if x not in targets]
        fit, edge_table, _, fold_boundaries = fit_analysis(
            cfg, f"LDO_hold_{held_date}", "LDO", training, "sequence_balanced",
            frames, source, nominal,
        )
        write_fit(out, f"ldo/hold_{held_date}", fit, edge_table)
        ldo_fits.append(fit.assign(held_out_date=held_date))
        for target in targets:
            ldo_targets.append(apply_frozen_to_target(fit, target, frames, fold_boundaries).assign(held_out_date=held_date))
    pd.concat(ldo_fits, ignore_index=True).to_csv(out / "ldo_training_candidates.csv", index=False)
    pd.concat(ldo_targets, ignore_index=True).to_csv(out / "ldo_target_application.csv", index=False)

    without = [x for x in all_sequences if x != "5.1"]
    weight_fit, weight_edges, _, _ = fit_analysis(
        cfg, "without_5.1_weight_only", "full_panel", without, "sequence_balanced",
        frames, source, nominal, boundaries_override=boundaries,
    )
    weight_fit = freeze_nominal_reference(weight_fit, primary)
    write_fit(out, "five_one_weight_influence", weight_fit, weight_edges)
    refit, refit_edges, _, _ = fit_analysis(
        cfg, "without_5.1_full_refit", "full_panel", without, "sequence_balanced",
        frames, source, nominal,
    )
    write_fit(out, "five_one_refit_influence", refit, refit_edges)

    # Nominal construction/fidelity table is frozen independently of outcomes.
    fidelity_rows = []
    for name, contract in cfg["coordinate_contract"].items():
        fidelity_rows.append({
            "coordinate": name, "channel": contract["channel"],
            "current_evidence_coordinate": contract["current_evidence_coordinate"],
            "primary_support_variable": contract["primary_support_variable"],
            "secondary_support_context": ";".join(contract["secondary_support_context"]),
            "s0_construction": contract["s0_construction"],
            "q_nominal_rule": contract["q_nominal_rule"],
            "NominalReferenceFidelity": contract["nominal_reference_fidelity"],
            "EligibleForNormativeReview_allowed": contract["nominal_reference_fidelity"] == "Full",
        })
    pd.DataFrame(fidelity_rows).to_csv(out / "nominal_reference_fidelity.csv", index=False)


def opposite(a: str, b: str) -> bool:
    return {a, b} == {"increase", "decrease"}


def matched_sensitivity(primary: pd.DataFrame, other: pd.DataFrame, label: str) -> pd.DataFrame:
    keys = ["channel", "coordinate", "support_cell", "alpha"]
    cols = keys + ["nominal_mismatch_ratio", "candidate_direction"]
    merged = primary[cols].merge(other[cols], on=keys, how="left", suffixes=("_primary", "_other"))
    merged["sensitivity"] = label
    merged["ratio_other_over_primary"] = merged["nominal_mismatch_ratio_other"] / merged["nominal_mismatch_ratio_primary"]
    merged["explicit_direction_reversal"] = [opposite(a, b) for a, b in zip(merged.candidate_direction_primary, merged.candidate_direction_other)]
    return merged


def direction_stability(primary: pd.DataFrame, folds: pd.DataFrame, fold_column: str) -> pd.DataFrame:
    rows = []
    for _, base in primary.iterrows():
        group = folds[
            (folds.coordinate == base.coordinate) & (folds.support_cell == base.support_cell)
            & np.isclose(folds.alpha, base.alpha)
        ]
        assessable = group.FoldAssessability.isin(["Assessable", "AssessableForUpgradeReview"])
        no_reverse = np.array([not opposite(base.candidate_direction, x) for x in group.candidate_direction])
        rows.append({
            "channel": base.channel, "coordinate": base.coordinate,
            "support_cell": base.support_cell, "alpha": base.alpha,
            "primary_direction": base.candidate_direction, "folds": len(group),
            "assessable_folds": int(assessable.sum()),
            "assessable_fraction": float(assessable.mean()) if len(group) else math.nan,
            "no_explicit_reversal_folds": int(no_reverse.sum()),
            "no_explicit_reversal_fraction": float(no_reverse.mean()) if len(group) else math.nan,
            "candidate_ratio_median": group.nominal_mismatch_ratio.median(),
            "candidate_ratio_min": group.nominal_mismatch_ratio.min(),
            "candidate_ratio_max": group.nominal_mismatch_ratio.max(),
            "fold_id_field": fold_column,
        })
    return pd.DataFrame(rows)


def boundaries_from_table(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    result = {}
    for coordinate, group in frame.groupby("coordinate"):
        ordered = group.sort_values("support_cell")
        result[coordinate] = np.array([ordered.lower.iloc[0], *ordered.upper.to_list()], dtype=float)
    return result


def support_applicability(
    fits: pd.DataFrame, frames: dict[str, pd.DataFrame], fold_kind: str,
) -> pd.DataFrame:
    rows = []
    sequence_dates = frames[next(iter(frames))][["sequence", "date_cluster"]].drop_duplicates()
    for analysis_name, fit in fits.groupby("analysis"):
        training = str(fit.source_sequences.iloc[0]).split(";")
        if fold_kind == "LOSO":
            targets = [str(fit.held_out_sequence.iloc[0])]
        else:
            held_date = str(fit.held_out_date.iloc[0])
            targets = sorted(sequence_dates.loc[sequence_dates.date_cluster.astype(str) == held_date, "sequence"].unique())
        for coordinate in sorted(fit.coordinate.unique()):
            source_frame = valid_frame(frames[coordinate])
            source_frame = source_frame[source_frame.sequence.isin(training)]
            low, high = source_frame.support.min(), source_frame.support.max()
            for target in targets:
                target_frame = valid_frame(frames[coordinate])
                target_frame = target_frame[target_frame.sequence == target]
                in_range = target_frame.support.between(low, high) if len(target_frame) else pd.Series(dtype=bool)
                rows.append({
                    "fold_kind": fold_kind, "analysis": analysis_name, "target_sequence": target,
                    "coordinate": coordinate, "training_support_min": low,
                    "training_support_max": high, "target_valid_rows": len(target_frame),
                    "prototype_support_domain_in_range_rate": float(in_range.mean()) if len(in_range) else math.nan,
                    "prototype_support_domain_out_of_range_rows": int((~in_range).sum()) if len(in_range) else 0,
                    "CalibrationApplicability": "Unknown_not_established_by_support_range",
                })
    return pd.DataFrame(rows)


def command_report(cfg: dict[str, Any], repo: Path) -> None:
    root = output_root(cfg, repo)
    analysis = root / "analysis"
    out = root / "report"
    out.mkdir(parents=True, exist_ok=True)
    primary = pd.read_csv(analysis / "full_panel_primary/assessment.csv")
    bw = pd.read_csv(analysis / "full_panel_block_weighted/assessment.csv")
    db = pd.read_csv(analysis / "full_panel_date_balanced/assessment.csv")
    weight = pd.read_csv(analysis / "five_one_weight_influence/assessment.csv")
    refit = pd.read_csv(analysis / "five_one_refit_influence/assessment.csv")
    loso = pd.read_csv(analysis / "loso_training_candidates.csv")
    ldo = pd.read_csv(analysis / "ldo_training_candidates.csv")
    contamination = pd.read_csv(analysis / "full_panel_primary/contamination_sensitivity.csv")
    repeat_inventory = pd.read_csv(root / "audit/repeat_artifact_inventory.csv")
    repeat_metrics = pd.read_csv(root / "audit/repeat_sensitivity.csv") if (root / "audit/repeat_sensitivity.csv").stat().st_size > 1 else pd.DataFrame()

    sensitivity = pd.concat([
        matched_sensitivity(primary, bw, "block_weighted"),
        matched_sensitivity(primary, db, "date_balanced"),
        matched_sensitivity(primary, weight, "5.1_weight_influence"),
        matched_sensitivity(primary, refit, "5.1_refit_influence"),
    ], ignore_index=True)
    sensitivity.to_csv(out / "candidate_sensitivity_comparison.csv", index=False)
    direction_stability(primary, loso, "held_out_sequence").to_csv(out / "loso_candidate_stability.csv", index=False)
    direction_stability(primary, ldo, "held_out_date").to_csv(out / "ldo_candidate_stability.csv", index=False)

    source, doppler, _ = load_panel(cfg)
    frames, _ = coordinate_frames(cfg, source, doppler)
    support_applicability(loso, frames, "LOSO").to_csv(out / "loso_prototype_support_domain_applicability.csv", index=False)
    support_applicability(ldo, frames, "LDO").to_csv(out / "ldo_prototype_support_domain_applicability.csv", index=False)

    primary_boundaries = boundaries_from_table(pd.read_csv(analysis / "full_panel_primary/support_boundaries.csv"))
    five_rows = []
    weight_match = matched_sensitivity(primary, weight, "5.1_weight_influence")
    refit_match = matched_sensitivity(primary, refit, "5.1_refit_influence")
    for _, base in primary.iterrows():
        coordinate_frame = assign_cell(valid_frame(frames[base.coordinate]), primary_boundaries[base.coordinate])
        cell = coordinate_frame[coordinate_frame.support_cell == int(base.support_cell)]
        tail = cell[cell.value >= base.real_inferential_upper_quantile]
        tail_blocks = tail[["sequence", "block_id"]].drop_duplicates()
        share = float((tail_blocks.sequence == "5.1").sum() / len(tail_blocks)) if len(tail_blocks) else math.nan
        key = (
            (weight_match.coordinate == base.coordinate) & (weight_match.support_cell == base.support_cell)
            & np.isclose(weight_match.alpha, base.alpha)
        )
        w = weight_match[key].iloc[0]
        r = refit_match[
            (refit_match.coordinate == base.coordinate) & (refit_match.support_cell == base.support_cell)
            & np.isclose(refit_match.alpha, base.alpha)
        ].iloc[0]
        if np.isclose(base.alpha, .10):
            if share <= .5 and .5 <= w.ratio_other_over_primary <= 2 and not w.explicit_direction_reversal and not r.explicit_direction_reversal:
                status = "PASS"
            elif share <= .75 and .25 <= w.ratio_other_over_primary <= 4 and not w.explicit_direction_reversal and not r.explicit_direction_reversal:
                status = "PARTIAL"
            else:
                status = "FAIL"
        else:
            status = "DiagnosticOnly_nonprimary_tail"
        five_rows.append({
            "channel": base.channel, "coordinate": base.coordinate, "support_cell": base.support_cell,
            "alpha": base.alpha, "five_one_tail_block_share": share,
            "5.1_weight_influence_ratio": w.ratio_other_over_primary,
            "5.1_weight_direction_reversal": w.explicit_direction_reversal,
            "5.1_refit_influence_ratio": r.ratio_other_over_primary,
            "5.1_refit_direction_reversal": r.explicit_direction_reversal,
            "dominance_traffic_light": status,
            "not_runtime_parameter": True,
        })
    five_frame = pd.DataFrame(five_rows)
    five_frame.to_csv(out / "five_one_weight_refit_influence.csv", index=False)

    tail_summary = primary.groupby(["channel", "alpha", "FullPanelTailStatus"], dropna=False).size().reset_index(name="rows")
    tail_summary.to_csv(out / "full_panel_tail_support_summary.csv", index=False)
    loso_summary = loso.groupby(["channel", "alpha", "FoldAssessability"], dropna=False).size().reset_index(name="rows")
    ldo_summary = ldo.groupby(["channel", "alpha", "FoldAssessability"], dropna=False).size().reset_index(name="rows")
    loso_summary.to_csv(out / "loso_assessability_summary.csv", index=False)
    ldo_summary.to_csv(out / "ldo_assessability_summary.csv", index=False)

    full99_rows = []
    for _, base in primary[np.isclose(primary.alpha, .01)].iterrows():
        frame = assign_cell(valid_frame(frames[base.coordinate]), primary_boundaries[base.coordinate])
        frame = frame[frame.support_cell == int(base.support_cell)]
        without = frame[frame.sequence != "5.1"]
        wb, wtb, wts, wtd, _ = tail_counts(without, base.real_inferential_upper_quantile)
        support_ok = bool(
            base.effective_blocks >= 100 and base.tail_containing_blocks >= 10
            and base.tail_containing_physical_sequences >= 5
            and base.tail_containing_date_clusters >= 3
            and base.maximum_single_sequence_tail_share <= .5
            and wb >= 50 and wtb >= 5 and wts >= 4 and wtd >= 2
        )
        full99_rows.append({
            "channel": base.channel, "coordinate": base.coordinate,
            "support_cell": base.support_cell, "alpha": base.alpha,
            "full_effective_blocks": base.effective_blocks,
            "full_tail_blocks": base.tail_containing_blocks,
            "full_tail_sequences": base.tail_containing_physical_sequences,
            "full_tail_dates": base.tail_containing_date_clusters,
            "full_max_single_sequence_tail_share": base.maximum_single_sequence_tail_share,
            "without_5.1_effective_blocks": wb, "without_5.1_tail_blocks": wtb,
            "without_5.1_tail_sequences": wts, "without_5.1_tail_dates": wtd,
            "support_prerequisites_met": support_ok,
            "FullPanelTailStatus": "DiagnosticOnly",
            "upgrade_review_status": "Pending_all_stability_criteria" if support_ok else "NotEligible_support",
        })
    full99 = pd.DataFrame(full99_rows)
    full99.to_csv(out / "full_panel_99_tail_upgrade_review.csv", index=False)

    contamination_overview = contamination.groupby(
        ["channel", "alpha", "epsilon_sensitivity"], dropna=False
    ).combined_envelope_fold_width.agg(["count", "median", "max"]).reset_index()
    contamination_overview.to_csv(out / "contamination_sensitivity_summary.csv", index=False)

    mismatch_summary = primary.groupby(["channel", "coordinate", "alpha"], dropna=False).agg(
        candidate_ratio_median=("nominal_mismatch_ratio", "median"),
        candidate_ratio_min=("nominal_mismatch_ratio", "min"),
        candidate_ratio_max=("nominal_mismatch_ratio", "max"),
        increase_rows=("candidate_direction", lambda x: int((x == "increase").sum())),
        decrease_rows=("candidate_direction", lambda x: int((x == "decrease").sum())),
        neutral_rows=("candidate_direction", lambda x: int((x == "neutral/indeterminate").sum())),
    ).reset_index()
    mismatch_summary.to_csv(out / "full_panel_nominal_mismatch_summary.csv", index=False)

    ci_rows, total_log_invalid = [], 0
    for path in sorted(analysis.glob("**/assessment.csv")):
        frame = pd.read_csv(path)
        total_log_invalid += int((frame.numerical_status != "valid").sum())
        for channel, group in frame.groupby("channel"):
            usable = group[
                (group.candidate_bootstrap_se_log > np.finfo(float).eps)
                & (group.nominal_mismatch_ratio > 0)
                & (group.candidate_simultaneous_ci_high > 0)
            ]
            critical = np.log(usable.candidate_simultaneous_ci_high / usable.nominal_mismatch_ratio) / usable.candidate_bootstrap_se_log
            ci_rows.append({
                "family_path": str(path.relative_to(root)), "analysis": group.analysis.iloc[0],
                "aggregation": group.aggregation.iloc[0], "channel": channel,
                "family_members": len(group), "coordinates": group.coordinate.nunique(),
                "support_cells": group[["coordinate", "support_cell"]].drop_duplicates().shape[0],
                "alphas": group.alpha.nunique(),
                "simultaneous_critical_95_median": critical.median(),
                "simultaneous_critical_95_range": critical.max() - critical.min() if len(critical) else math.nan,
                "numerical_invalid_members": int((group.numerical_status != "valid").sum()),
                "family_definition": "channel_x_analysis-mode-or-fold_x_aggregation_all_coordinate_x_support-cell_x_alpha",
            })
    pd.DataFrame(ci_rows).to_csv(out / "simultaneous_ci_family_audit.csv", index=False)

    promotion_rows = []
    for _, row in primary.iterrows():
        key_filter = (
            (loso.coordinate == row.coordinate) & (loso.support_cell == row.support_cell)
            & np.isclose(loso.alpha, row.alpha)
        )
        lrows = loso[key_filter]
        drows = ldo[
            (ldo.coordinate == row.coordinate) & (ldo.support_cell == row.support_cell)
            & np.isclose(ldo.alpha, row.alpha)
        ]
        primary_direction = row.candidate_direction
        loso_assessable = lrows.FoldAssessability.isin(["Assessable", "AssessableForUpgradeReview"])
        ldo_assessable = drows.FoldAssessability.isin(["Assessable", "AssessableForUpgradeReview"])
        loso_no_reverse = not any(opposite(primary_direction, x) for x in lrows.candidate_direction)
        ldo_no_reverse = not any(opposite(primary_direction, x) for x in drows.candidate_direction)
        sens = sensitivity[
            (sensitivity.coordinate == row.coordinate) & (sensitivity.support_cell == row.support_cell)
            & np.isclose(sensitivity.alpha, row.alpha)
        ]
        aggregation_rows = sens[sens.sensitivity.isin(["block_weighted", "date_balanced"])]
        aggregation_ok = bool(
            len(aggregation_rows) == 2
            and (~aggregation_rows.explicit_direction_reversal).all()
            and aggregation_rows.ratio_other_over_primary.between(.5, 2).all()
        )
        five_row = five_frame[
            (five_frame.coordinate == row.coordinate) & (five_frame.support_cell == row.support_cell)
            & np.isclose(five_frame.alpha, row.alpha)
        ]
        five_ok = bool(
            len(five_row) == 1
            and not five_row.iloc[0]["5.1_weight_direction_reversal"]
            and not five_row.iloc[0]["5.1_refit_direction_reversal"]
            and .5 <= five_row.iloc[0]["5.1_weight_influence_ratio"] <= 2
            and .5 <= five_row.iloc[0]["5.1_refit_influence_ratio"] <= 2
            and five_row.iloc[0].five_one_tail_block_share <= .5
        )
        contam = contamination[
            (contamination.coordinate == row.coordinate) & (contamination.support_cell == row.support_cell)
            & np.isclose(contamination.alpha, row.alpha)
        ]
        c10 = contam[np.isclose(contam.epsilon_sensitivity, .10)].combined_envelope_fold_width
        c20 = contam[np.isclose(contam.epsilon_sensitivity, .20)].combined_envelope_fold_width
        contamination_ok = bool(len(c10) and len(c20) and c10.iloc[0] <= 2 and c20.iloc[0] <= 4)
        fidelity_ok = row.nominal_reference_fidelity == "Full"
        tail_ok = row.FullPanelTailStatus == "Eligible"
        loso_ok = len(lrows) >= 9 and float(loso_assessable.mean()) >= cfg["promotion_criteria"]["loso_assessable_fraction_min"] and loso_no_reverse
        ldo_ok = len(drows) == 3 and bool(ldo_assessable.all()) and ldo_no_reverse
        repeat_ok = False  # T1/T2 are absent; no substitution or independence claim is allowed.
        applicability_ok = False  # Full CalibrationApplicability is not established by this prototype.
        eligible = all((fidelity_ok, tail_ok, loso_ok, ldo_ok, aggregation_ok, five_ok, contamination_ok, repeat_ok, applicability_ok))
        blockers = [name for name, passed in (
            ("NominalReferenceFidelity", fidelity_ok), ("FullPanelTailStatus", tail_ok),
            ("LOSO", loso_ok), ("LDO", ldo_ok), ("aggregation", aggregation_ok),
            ("5.1_influence", five_ok), ("contamination", contamination_ok),
            ("repeat_stability", repeat_ok), ("full_CalibrationApplicability", applicability_ok),
        ) if not passed]
        promotion_rows.append({
            "channel": row.channel, "coordinate": row.coordinate, "support_cell": row.support_cell,
            "alpha": row.alpha, "primary_direction": primary_direction,
            "NominalReferenceFidelity": row.nominal_reference_fidelity,
            "full_panel_tail_ok": tail_ok, "loso_ok": loso_ok, "ldo_ok": ldo_ok,
            "aggregation_ok": aggregation_ok, "five_one_weight_and_refit_ok": five_ok,
            "contamination_ok": contamination_ok, "repeat_stability_ok": repeat_ok,
            "full_CalibrationApplicability_ok": applicability_ok,
            "promotion_status": "EligibleForNormativeReview" if eligible else "NotEligible",
            "blockers": ";".join(blockers), "normative_correction": False,
        })
    promotion = pd.DataFrame(promotion_rows)
    promotion.to_csv(out / "correction_promotion_matrix.csv", index=False)

    validation = json.loads((root / "validate/validation_report.json").read_text())
    execution = "PASS" if validation["status"] == "PASS" and len(primary) else "FAIL"
    # Frozen PASS requires a much stronger scientific result than successful execution.
    channels_promoted_or_neutral = {}
    for channel, group in primary.groupby("channel"):
        promoted = (promotion[promotion.channel == channel].promotion_status == "EligibleForNormativeReview").any()
        neutral = (group.candidate_direction == "neutral/indeterminate").all()
        channels_promoted_or_neutral[channel] = bool(promoted or neutral)
    scientific = "PASS" if execution == "PASS" and all(channels_promoted_or_neutral.values()) else ("PARTIAL" if execution == "PASS" else "FAIL")
    deviations = []
    missing_repeats = repeat_inventory[~repeat_inventory.available]
    if len(missing_repeats):
        deviations.append({
            "type": "input_artifact_unavailable",
            "scope": "4.1/4.2 repeat sensitivity",
            "detail": ";".join(f"{r.sequence}:{r.run}" for r in missing_repeats.itertuples()),
            "handling": "NotAssessed; no substitute, refit, rerun, or parameter change",
            "frozen_rule_changed": False,
        })
    decision = {
        "ExecutionIntegrity": execution, "ScientificOutcome": scientific,
        "Stage3A1b1b4cP": "FROZEN", "manifest_id": MANIFEST_ID,
        "primary_sequences": len(cfg["primary_realizations"]),
        "date_clusters": len(cfg["acquisition_date_clusters"]),
        "promotion_eligible_rows": int((promotion.promotion_status == "EligibleForNormativeReview").sum()),
        "promotion_total_rows": len(promotion),
        "full_panel_99_support_prerequisite_rows": int(full99.support_prerequisites_met.sum()),
        "preregistration_deviations": deviations,
        "threshold_or_rule_changed_after_results": False,
        "5.2_read": False, "GT_APE_AR_FIX_read": False,
        "online_cpp_or_config_changed": False,
    }
    write_json(out / "decision.json", decision)
    write_json(out / "preregistration_deviations.json", {"deviations": deviations})
    write_json(out / "execution_corrections.json", {"corrections": [{
        "issue": "Initial audit output contained repeat point estimates only.",
        "correction": "Before final reporting, reran repeat audit with frozen paired 30-epoch block bootstrap, 2000 replicates, Fisher clipping, and simultaneous 95% CI for all channel coordinates.",
        "frozen_parameter_or_rule_changed": False,
        "result_driven_change": False,
        "superseded_output_retained": False,
    }]})

    incomparability = pd.read_csv(root / "audit/within_run_state_pair_incomparability.csv")
    repeat_guard = json.loads((root / "audit/numerical_guards.json").read_text())
    fidelity = pd.read_csv(analysis / "nominal_reference_fidelity.csv")
    summary = {
        "ExecutionIntegrity": execution,
        "ScientificOutcome": scientific,
        "representation_stability": {
            "pr_within_run_state_pair_incomparability_min": incomparability.incomparability_rate.min(),
            "pr_within_run_state_pair_incomparability_median": incomparability.incomparability_rate.median(),
            "pr_within_run_state_pair_incomparability_max": incomparability.incomparability_rate.max(),
            "available_repeat_artifacts": int(repeat_inventory.available.sum()),
            "expected_repeat_artifacts": len(repeat_inventory),
            "repeat_spearman_min": repeat_metrics.spearman.min() if len(repeat_metrics) else math.nan,
            "repeat_spearman_median": repeat_metrics.spearman.median() if len(repeat_metrics) else math.nan,
        },
        "full_panel_tail_rows": tail_summary.to_dict("records"),
        "full_panel_99_support_prerequisite_rows": int(full99.support_prerequisites_met.sum()),
        "loso": direction_stability(primary, loso, "held_out_sequence").to_dict("records"),
        "leave_date_cluster_out": direction_stability(primary, ldo, "held_out_date").to_dict("records"),
        "aggregation_direction_reversals": sensitivity[
            sensitivity.sensitivity.isin(["block_weighted", "date_balanced"])
        ].groupby("sensitivity").explicit_direction_reversal.sum().to_dict(),
        "five_one_direction_reversals": {
            "weight": int(five_frame["5.1_weight_direction_reversal"].sum()),
            "refit": int(five_frame["5.1_refit_direction_reversal"].sum()),
        },
        "promotion_eligible_rows": int((promotion.promotion_status == "EligibleForNormativeReview").sum()),
        "nominal_reference_fidelity": fidelity.NominalReferenceFidelity.value_counts().to_dict(),
        "numerical_guards": repeat_guard,
        "log_ratio_numerical_invalid_across_assessment_files": total_log_invalid,
        "preregistration_deviations": deviations,
    }
    write_json(out / "summary.json", summary)

    lines = [
        "# Stage 3A.1b-1b.4c-E Multi-Session Calibration Prototype",
        "", f"- ExecutionIntegrity: **{execution}**", f"- ScientificOutcome: **{scientific}**",
        f"- Primary physical sequences: {len(cfg['primary_realizations'])}",
        f"- Acquisition-date clusters: {len(cfg['acquisition_date_clusters'])}",
        f"- Correction rows eligible for normative review: {decision['promotion_eligible_rows']}/{len(promotion)}",
        f"- 99% rows meeting support-only upgrade prerequisites: {int(full99.support_prerequisites_met.sum())}/{len(full99)}; all remain DiagnosticOnly pending all stability criteria.",
        "- F_SB is an equal-sequence development-panel estimand, not a universal healthy distribution.",
        "- Real-data occupancy is an outcome descriptor, not calibration coverage or a transfer correctness target.",
        "- No empirical mismatch ratio was promoted to a normative correction.", "",
        "## Nominal-reference fidelity", "",
    ]
    for fidelity_name, count in fidelity.NominalReferenceFidelity.value_counts().items():
        lines.append(f"- {fidelity_name}: {count} base coordinates")
    lines += ["", "## Tail status", ""]
    for row in tail_summary.itertuples():
        lines.append(f"- {row.channel} alpha={row.alpha:g} {row.FullPanelTailStatus}: {row.rows} rows")
    lines += ["", "## Repeat sensitivity", ""]
    lines.append(f"- Available repeat artifacts: {int(repeat_inventory.available.sum())}/{len(repeat_inventory)}")
    lines.append(f"- Computed nested-repeat coordinate rows: {len(repeat_metrics)}")
    if len(missing_repeats):
        lines.append("- Missing repeat artifacts were left NotAssessed; no substitution was made.")
    lines += ["", "## Boundaries", "",
        "- 5.1 weight influence freezes full-panel support boundaries and S0 reference, then removes only 5.1 sequence weight.",
        "- 5.1 refit influence removes 5.1 and rebuilds training support strata/reference/candidate.",
        "- LOSO/LDO rebuild training-only boundaries and apply frozen candidates to targets without target refit.",
        "- Full CalibrationApplicability remains unresolved beyond prototype support-domain applicability.",
        "- 5.2, GT/APE, AR/FIX, online C++, temporal trust, and factor weighting were not used.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")

    fig, ax = plt.subplots(figsize=(11, 5))
    for channel, group in primary.groupby("channel"):
        ax.scatter(np.arange(len(group)), group.nominal_mismatch_ratio, s=14, label=channel)
    ax.axhline(1, color="black", linestyle="--")
    ax.set_yscale("log")
    ax.set_ylabel("Nominal mismatch ratio (candidate only)")
    ax.set_xlabel("Frozen coordinate/support/alpha rows within channel")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "full_panel_nominal_mismatch.png", dpi=160)
    plt.close(fig)

    # Immutable run-facing copy plus artifact hashes. The inventory excludes
    # itself to avoid recursive hashing.
    manifest_path = repo / "tools/research/stage3a_1b_1b_4c_manifest.yaml"
    (out / "frozen_manifest_snapshot.yaml").write_text(manifest_path.read_text())
    artifacts = []
    for path in sorted(root.glob("**/*")):
        if path.is_file() and path.name != "artifact_inventory.csv":
            artifacts.append({
                "path": str(path.relative_to(repo)), "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    pd.DataFrame(artifacts).to_csv(out / "artifact_inventory.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "audit", "analyze", "report", "all"))
    parser.add_argument("--manifest", type=Path, default=Path("tools/research/stage3a_1b_1b_4c_manifest.yaml"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    cfg = load_manifest(args.manifest.resolve())
    repo = args.repo.resolve()
    commands = ("validate", "audit", "analyze", "report") if args.command == "all" else (args.command,)
    for command in commands:
        if command == "validate":
            command_validate(cfg, repo)
        elif command == "audit":
            command_audit(cfg, repo)
        elif command == "analyze":
            command_analyze(cfg, repo)
        elif command == "report":
            command_report(cfg, repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
