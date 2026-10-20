#!/usr/bin/env python3
"""Stage 3A.1b-1b.3R repeat-hierarchy corrective rerun.

The parent S3A1b1b3-v1 statistics are imported unchanged.  This tool changes
only the experimental hierarchy: each repeat is a separate source fit and each
source fit is applied to each target repeat.  The nine applications in one
direction are nested repeat pairs and are never treated as nine independent
sessions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

import gnss_calibration_prototype as parent


CORRECTIVE_MANIFEST = Path(__file__).with_name("stage3a_1b_1b_3r_manifest.yaml")
PARENT_MANIFEST = Path(__file__).with_name("stage3a_1b_1b_3_manifest.yaml")


def load_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = parent.load_manifest(PARENT_MANIFEST)
    corrective = yaml.safe_load(CORRECTIVE_MANIFEST.read_text())
    if corrective.get("manifest_id") != "S3A1b1b3R-v1":
        raise RuntimeError("Expected S3A1b1b3R-v1 corrective manifest")
    if corrective.get("correction_scope") != "repeat_hierarchy_only":
        raise RuntimeError("Corrective scope must be repeat_hierarchy_only")
    return cfg, corrective


def root_3r(repo: Path, corrective: dict[str, Any]) -> Path:
    return repo / corrective["output_root"]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_names(cfg: dict[str, Any], dataset: str) -> list[str]:
    for key, value in cfg["inputs"].items():
        if str(key) == dataset:
            return list(value["runs"].keys())
    raise KeyError(dataset)


def tables_for_run(
    evidence: dict[str, pd.DataFrame],
    doppler: dict[str, pd.DataFrame],
    dataset: str,
    run: str,
) -> list[dict[str, Any]]:
    tables = parent.transfer_tables(evidence, doppler, dataset)
    selected = []
    for table in tables:
        frame = table["frame"]
        selected.append({**table, "frame": frame[frame.run == run].copy()})
    return selected


def support_edges(frame: pd.DataFrame) -> np.ndarray:
    edges = np.unique(
        np.quantile(frame.support, [0, 1 / 3, 2 / 3, 1], method="linear")
    )
    if len(edges) < 2:
        edges = np.array([frame.support.min() - 0.5, frame.support.max() + 0.5])
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def assign_stratum(frame: pd.DataFrame, edges: np.ndarray) -> pd.DataFrame:
    result = frame.copy()
    result["stratum_index"] = pd.cut(
        result.support,
        edges,
        include_lowest=True,
        duplicates="drop",
        labels=False,
    )
    return result


def format_stratum(edges: np.ndarray, index: int) -> str:
    lower = "-inf" if not np.isfinite(edges[index]) else f"{edges[index]:.12g}"
    upper = "inf" if not np.isfinite(edges[index + 1]) else f"{edges[index + 1]:.12g}"
    return f"({lower},{upper}]"


def fit_source_repeat(
    cfg: dict[str, Any],
    thresholds: pd.DataFrame,
    source: str,
    source_run: str,
    source_tables: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    alphas = [float(x) for x in cfg["statistics"]["alpha_grid"]]
    primary_block = int(cfg["statistics"]["primary_block_size_epochs"])
    gap = float(cfg["statistics"]["segment_gap_multiple"])
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    epsilons = [float(x) for x in cfg["statistics"]["contamination_epsilon_grid"]]
    result_rows: list[dict[str, Any]] = []
    boot_specs: list[tuple[int, pd.DataFrame, float, float]] = []
    edges_by_coordinate: dict[str, np.ndarray] = {}

    for table in source_tables:
        coordinate = table["coordinate"]
        sf = (
            table["frame"]
            .replace([np.inf, -np.inf], np.nan)
            .dropna(subset=["value", "support"])
        )
        if sf.empty:
            continue
        edges = support_edges(sf)
        edges_by_coordinate[coordinate] = edges
        sf = assign_stratum(sf, edges)
        sf = parent.assign_blocks(sf, primary_block, gap)
        for stratum_index, sg in sf.groupby("stratum_index", observed=True):
            stratum_index = int(stratum_index)
            support = float(sg.support.median())
            for alpha in alphas:
                p = 1 - alpha
                nominal = parent.nearest_nominal(
                    thresholds, table["channel"], coordinate, support, alpha
                )
                q_source = parent.percentile(sg.value.to_numpy(), p)
                ratio, numerical = parent.ratio_guard(q_source, nominal)
                tail_eff, tail_assessment = parent.tail_status(
                    sg.value.to_numpy(), q_source, sg.block_id.to_numpy(), cfg
                )
                candidate = (
                    tail_assessment in {"Eligible", "Partial"}
                    and numerical == "valid"
                )
                source_occupancy = (
                    float(np.mean(sg.value <= nominal))
                    if np.isfinite(nominal)
                    else math.nan
                )
                result_rows.append(
                    {
                        "source": source,
                        "source_run": source_run,
                        "channel": table["channel"],
                        "coordinate": coordinate,
                        "support_stratum_index": stratum_index,
                        "support_stratum": format_stratum(edges, stratum_index),
                        "source_n": len(sg),
                        "source_support_min": float(sf.support.min()),
                        "source_support_max": float(sf.support.max()),
                        "source_effective_blocks": int(
                            sg.block_id[sg.block_id >= 0].nunique()
                        ),
                        "representative_support": support,
                        "alpha": alpha,
                        "nominal_upper_threshold": nominal,
                        "source_empirical_upper_quantile": q_source,
                        "nominal_mismatch_ratio": ratio,
                        "numerical_status": numerical,
                        "effective_tail_support": tail_eff,
                        "tail_assessment_status": tail_assessment,
                        "empirical_correction_candidate_status": (
                            "candidate" if candidate else "NotAssessed"
                        ),
                        "r_quality_sensitivity_candidate": (
                            max(1.0, ratio) if candidate else math.nan
                        ),
                        "source_nominal_membership_occupancy": source_occupancy,
                        "occupancy_is_transfer_pass_target": False,
                        "repeat_hierarchy": "single_source_repeat",
                    }
                )
                boot_specs.append((len(result_rows) - 1, sg.copy(), nominal, p))

    results = pd.DataFrame(result_rows)
    boot = np.full((reps, len(results)), np.nan)
    contamination_low_boot = {
        epsilon: np.full((reps, len(results)), np.nan) for epsilon in epsilons
    }
    contamination_high_boot = {
        epsilon: np.full((reps, len(results)), np.nan) for epsilon in epsilons
    }
    rng = parent.rng_for(
        cfg, "transfer-3r", source, source_run, "source-block-bootstrap"
    )
    for k, (_, sg, nominal, p) in enumerate(boot_specs):
        blocks = [
            group.value.to_numpy(float)
            for _, group in sg[sg.block_id >= 0].groupby("block_id")
        ]
        if not blocks or not np.isfinite(nominal) or nominal <= 0:
            continue
        probabilities = [p]
        for epsilon in epsilons:
            probabilities.extend(
                [
                    float(np.clip((1 - epsilon) * p, 0, 1)),
                    float(np.clip(epsilon + (1 - epsilon) * p, 0, 1)),
                ]
            )
        for b in range(reps):
            selected = rng.integers(0, len(blocks), len(blocks))
            sample = np.concatenate([blocks[i] for i in selected])
            quantiles = np.quantile(sample, probabilities, method="linear")
            boot[b, k], _ = parent.ratio_guard(float(quantiles[0]), nominal)
            offset = 1
            for epsilon in epsilons:
                contamination_low_boot[epsilon][b, k], _ = parent.ratio_guard(
                    float(quantiles[offset]), nominal
                )
                contamination_high_boot[epsilon][b, k], _ = parent.ratio_guard(
                    float(quantiles[offset + 1]), nominal
                )
                offset += 2

    estimates = results.nominal_mismatch_ratio.to_numpy(float)
    valid_columns = (
        np.isfinite(estimates)
        & (estimates > 0)
        & np.isfinite(boot).any(axis=0)
    )
    low = np.full(len(results), np.nan)
    high = np.full(len(results), np.nan)
    se = np.full(len(results), np.nan)
    if valid_columns.any():
        lo, hi, std, _ = parent.simultaneous_log_ci(
            estimates[valid_columns], boot[:, valid_columns]
        )
        low[valid_columns], high[valid_columns], se[valid_columns] = lo, hi, std
    results["candidate_simultaneous_ci_low"] = low
    results["candidate_simultaneous_ci_high"] = high
    results["candidate_bootstrap_se_log"] = se
    results["candidate_direction"] = np.where(
        low > 1,
        "increase",
        np.where(high < 1, "decrease", "neutral/indeterminate"),
    )

    contamination_rows: list[dict[str, Any]] = []
    for epsilon in epsilons:
        point_low = np.full(len(results), np.nan)
        point_high = np.full(len(results), np.nan)
        for index, sg, nominal, p in boot_specs:
            qlow, qhigh = parent.empirical_quantile_bounds(
                sg.value.to_numpy(), p, epsilon
            )
            point_low[index], _ = parent.ratio_guard(qlow, nominal)
            point_high[index], _ = parent.ratio_guard(qhigh, nominal)
        valid_low = (
            np.isfinite(point_low)
            & (point_low > 0)
            & np.isfinite(contamination_low_boot[epsilon]).any(axis=0)
        )
        valid_high = (
            np.isfinite(point_high)
            & (point_high > 0)
            & np.isfinite(contamination_high_boot[epsilon]).any(axis=0)
        )
        low_ci_low = np.full(len(results), np.nan)
        low_ci_high = np.full(len(results), np.nan)
        high_ci_low = np.full(len(results), np.nan)
        high_ci_high = np.full(len(results), np.nan)
        if valid_low.any():
            lo, hi, _, _ = parent.simultaneous_log_ci(
                point_low[valid_low],
                contamination_low_boot[epsilon][:, valid_low],
            )
            low_ci_low[valid_low], low_ci_high[valid_low] = lo, hi
        if valid_high.any():
            lo, hi, _, _ = parent.simultaneous_log_ci(
                point_high[valid_high],
                contamination_high_boot[epsilon][:, valid_high],
            )
            high_ci_low[valid_high], high_ci_high[valid_high] = lo, hi
        for index in range(len(results)):
            base = results.iloc[index]
            low_status = (
                "valid"
                if np.isfinite(point_low[index]) and point_low[index] > 0
                else "numerical-invalid/NotAssessed"
            )
            high_status = (
                "valid"
                if np.isfinite(point_high[index]) and point_high[index] > 0
                else "numerical-invalid/NotAssessed"
            )
            contamination_rows.append(
                {
                    "source": source,
                    "source_run": source_run,
                    "channel": base.channel,
                    "coordinate": base.coordinate,
                    "support_stratum_index": base.support_stratum_index,
                    "support_stratum": base.support_stratum,
                    "alpha": base.alpha,
                    "epsilon_sensitivity": epsilon,
                    "candidate_ratio_lower_endpoint": point_low[index],
                    "candidate_ratio_lower_simultaneous_ci_low": low_ci_low[index],
                    "candidate_ratio_lower_simultaneous_ci_high": low_ci_high[index],
                    "candidate_ratio_upper_endpoint": point_high[index],
                    "candidate_ratio_upper_simultaneous_ci_low": high_ci_low[index],
                    "candidate_ratio_upper_simultaneous_ci_high": high_ci_high[index],
                    "lower_numerical_status": low_status,
                    "upper_numerical_status": high_status,
                    "interpretation": (
                        "single_source_repeat_bootstrap_contamination_sensitivity"
                    ),
                }
            )
    return results, pd.DataFrame(contamination_rows), edges_by_coordinate


def apply_to_target_repeat(
    cfg: dict[str, Any],
    source_fit: pd.DataFrame,
    edges_by_coordinate: dict[str, np.ndarray],
    target: str,
    target_run: str,
    target_tables: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary_block = int(cfg["statistics"]["primary_block_size_epochs"])
    gap = float(cfg["statistics"]["segment_gap_multiple"])
    tables = {table["coordinate"]: table for table in target_tables}
    pair_rows: list[dict[str, Any]] = []
    applicability_rows: list[dict[str, Any]] = []
    source = str(source_fit.source.iloc[0])
    source_run = str(source_fit.source_run.iloc[0])

    for coordinate, table in tables.items():
        raw = table["frame"].replace([np.inf, -np.inf], np.nan)
        valid = raw.dropna(subset=["value", "support"]).copy()
        edges = edges_by_coordinate[coordinate]
        valid = assign_stratum(valid, edges)
        valid = parent.assign_blocks(valid, primary_block, gap)
        fits = source_fit[source_fit.coordinate == coordinate]
        for _, fit in fits.iterrows():
            group = valid[
                valid.stratum_index == int(fit.support_stratum_index)
            ]
            nominal = float(fit.nominal_upper_threshold)
            candidate_threshold = (
                float(fit.r_quality_sensitivity_candidate) * nominal
                if fit.empirical_correction_candidate_status == "candidate"
                and np.isfinite(fit.r_quality_sensitivity_candidate)
                else math.nan
            )
            nominal_occupancy = (
                float(np.mean(group.value <= nominal))
                if len(group) and np.isfinite(nominal)
                else math.nan
            )
            candidate_occupancy = (
                float(np.mean(group.value <= candidate_threshold))
                if len(group) and np.isfinite(candidate_threshold)
                else math.nan
            )
            row = fit.to_dict()
            row.update(
                {
                    "target": target,
                    "target_run": target_run,
                    "target_n": len(group),
                    "target_effective_blocks": int(
                        group.block_id[group.block_id >= 0].nunique()
                    ),
                    "target_nominal_membership_occupancy": nominal_occupancy,
                    "occupancy_gap_target_minus_source": (
                        nominal_occupancy
                        - float(fit.source_nominal_membership_occupancy)
                        if np.isfinite(nominal_occupancy)
                        else math.nan
                    ),
                    "target_candidate_membership_occupancy": candidate_occupancy,
                    "pair_independent_session_sample": False,
                    "pair_role": "nested_repeat_application",
                }
            )
            pair_rows.append(row)

        source_support_min = float(fits.source_support_min.iloc[0])
        source_support_max = float(fits.source_support_max.iloc[0])
        evidence_valid = raw.value.notna() & raw.support.notna()
        in_domain = evidence_valid & raw.support.between(
            source_support_min, source_support_max
        )
        out_domain = evidence_valid & ~raw.support.between(
            source_support_min, source_support_max
        )
        applicability_rows.append(
            {
                "source": source,
                "source_run": source_run,
                "target": target,
                "target_run": target_run,
                "channel": table["channel"],
                "coordinate": coordinate,
                "source_support_min": source_support_min,
                "source_support_max": source_support_max,
                "target_total": len(raw),
                "target_evidence_valid": int(evidence_valid.sum()),
                "target_evidence_valid_rate": float(evidence_valid.mean()),
                "calibration_applicability_InDomain": int(in_domain.sum()),
                "calibration_applicability_OutOfDomain": int(out_domain.sum()),
                "calibrated_quality_NotAssessed": int((~evidence_valid).sum()),
                "InDomain_rate": float(in_domain.mean()),
                "OutOfDomain_rate": float(out_domain.mean()),
                "NotAssessed_rate": float((~evidence_valid).mean()),
                "pair_independent_session_sample": False,
            }
        )
    return pd.DataFrame(pair_rows), pd.DataFrame(applicability_rows)


def block_sensitivity_for_repeat(
    cfg: dict[str, Any],
    source: str,
    source_run: str,
    tables: list[dict[str, Any]],
) -> pd.DataFrame:
    rows = []
    for block_size in cfg["statistics"]["block_sizes_epochs"]:
        for table in tables:
            frame = (
                table["frame"]
                .replace([np.inf, -np.inf], np.nan)
                .dropna(subset=["value"])
            )
            frame = parent.assign_blocks(
                frame,
                int(block_size),
                cfg["statistics"]["segment_gap_multiple"],
            )
            block_values = frame[frame.block_id >= 0].groupby("block_id").value.median()
            rows.append(
                {
                    "source": source,
                    "source_run": source_run,
                    "channel": table["channel"],
                    "coordinate": table["coordinate"],
                    "block_size_epochs": block_size,
                    "effective_blocks": len(block_values),
                    "median_of_block_medians": parent.percentile(
                        block_values.to_numpy(), 0.5
                    ),
                    "p90_of_block_medians": parent.percentile(
                        block_values.to_numpy(), 0.9
                    ),
                    "repeat_hierarchy": "single_source_repeat",
                }
            )
    return pd.DataFrame(rows)


def command_validate(cfg: dict[str, Any], corrective: dict[str, Any], repo: Path) -> None:
    out = root_3r(repo, corrective) / "validate"
    out.mkdir(parents=True, exist_ok=True)
    parent_root = repo / cfg["output_root"]
    required = [
        parent_root / "validate/validation_report.json",
        parent_root / "synthetic_s0/synthetic_coverage.csv",
        parent_root / "synthetic_s0/synthetic_nominal_thresholds.csv",
        PARENT_MANIFEST,
        CORRECTIVE_MANIFEST,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing frozen parent artifacts: {missing}")
    parent_validation = json.loads(required[0].read_text())
    hashes = [
        {"path": str(path), "sha256": file_sha256(path)} for path in required
    ]
    pd.DataFrame(hashes).to_csv(out / "frozen_input_hashes.csv", index=False)
    parent.write_json(
        out / "validation_report.json",
        {
            "status": "PASS" if parent_validation.get("status") == "PASS" else "FAIL",
            "parent_validation": parent_validation.get("status"),
            "correction_scope": "repeat_hierarchy_only",
            "synthetic_action": "reuse_unchanged",
            "source_fit_unit": "single_repeat",
            "target_application_unit": "single_repeat",
            "pair_independence_claim": False,
        },
    )


def command_audit(cfg: dict[str, Any], corrective: dict[str, Any], repo: Path) -> None:
    root = root_3r(repo, corrective)
    if not (root / "validate/validation_report.json").exists():
        raise RuntimeError("Run 3R validate first")
    out = root / "audit"
    out.mkdir(parents=True, exist_ok=True)
    evidence, _ = parent.load_all(cfg)
    old = pd.read_csv(repo / cfg["output_root"] / "audit/pr_tradeoff_incomparability.csv")
    old = old.rename(
        columns={
            "sampled_pairs": "sampled_within_run_state_pairs",
            "incomparable_count": "within_run_state_pair_incomparable_count",
            "incomparable_rate": "within_run_state_pair_incomparability_rate",
        }
    )
    old.insert(0, "metric", "within_run_state_pair_incomparability")
    old["semantic_unit"] = "random_epoch_state_pair_within_one_run"
    old["same_timestamp_repeat_metric"] = False
    old.to_csv(out / "within_run_state_pair_incomparability.csv", index=False)

    tolerance = float(cfg["statistics"]["timestamp_match_tolerance_seconds"])
    rows = []
    for dataset in ("4.1", "4.2"):
        keys = [key for key in evidence if key.startswith(dataset + ":")]
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                run_a = keys[i].split(":")[1]
                run_b = keys[j].split(":")[1]
                merged = parent.match_pair(
                    evidence[keys[i]][["timestamp", *parent.PR_COORDS]],
                    evidence[keys[j]][["timestamp", *parent.PR_COORDS]],
                    tolerance,
                )
                columns = [
                    *(coordinate + "_a" for coordinate in parent.PR_COORDS),
                    *(coordinate + "_b" for coordinate in parent.PR_COORDS),
                ]
                valid = merged[["timestamp", *columns]].dropna()
                a = valid[[coordinate + "_a" for coordinate in parent.PR_COORDS]].to_numpy(float)
                b = valid[[coordinate + "_b" for coordinate in parent.PR_COORDS]].to_numpy(float)
                pooled = np.vstack([a, b]) if len(valid) else np.empty((0, 3))
                iqr = (
                    np.subtract(*np.nanpercentile(pooled, [75, 25], axis=0))
                    if len(pooled)
                    else np.full(3, np.nan)
                )
                deadband = np.maximum(1e-12, 0.01 * iqr)
                delta = a - b
                incomparable = (
                    (delta > deadband).any(axis=1)
                    & (delta < -deadband).any(axis=1)
                )
                rows.append(
                    {
                        "metric": "same_timestamp_repeat_pair_tradeoff",
                        "dataset": dataset,
                        "run_a": run_a,
                        "run_b": run_b,
                        "matched_complete_pr_timestamps": len(valid),
                        "same_timestamp_incomparable_count": int(incomparable.sum()),
                        "same_timestamp_incomparability_rate": (
                            float(incomparable.mean()) if len(valid) else math.nan
                        ),
                        "deadband_definition": "max(1e-12,0.01*paired_pooled_IQR)_per_coordinate",
                        "semantic_unit": "same_timestamp_nested_repeat_pair",
                        "independent_session_sample": False,
                    }
                )
    pd.DataFrame(rows).to_csv(out / "same_timestamp_repeat_pair_tradeoff.csv", index=False)
    parent.write_json(
        out / "audit_semantics.json",
        {
            "old_pr_tradeoff_filename_semantics": (
                "within-run random epoch-state pairs; not same-timestamp repeats"
            ),
            "renamed_file": "within_run_state_pair_incomparability.csv",
            "new_repeat_file": "same_timestamp_repeat_pair_tradeoff.csv",
        },
    )


def command_transfer(
    cfg: dict[str, Any],
    corrective: dict[str, Any],
    repo: Path,
    source: str,
    target: str,
) -> None:
    root = root_3r(repo, corrective)
    if not (root / "audit/audit_semantics.json").exists():
        raise RuntimeError("Run 3R audit first")
    out = root / f"transfer_{source.replace('.', 'p')}_to_{target.replace('.', 'p')}"
    out.mkdir(parents=True, exist_ok=True)
    parent_root = repo / cfg["output_root"]
    thresholds = pd.read_csv(
        parent_root / "synthetic_s0/synthetic_nominal_thresholds.csv"
    )
    evidence, doppler = parent.load_all(cfg)
    source_fits = []
    pair_assessments = []
    applicability = []
    contamination = []
    blocks = []

    for source_run in run_names(cfg, source):
        source_tables = tables_for_run(evidence, doppler, source, source_run)
        fit, contamination_frame, edges = fit_source_repeat(
            cfg, thresholds, source, source_run, source_tables
        )
        source_fits.append(fit)
        contamination.append(contamination_frame)
        blocks.append(
            block_sensitivity_for_repeat(cfg, source, source_run, source_tables)
        )
        for target_run in run_names(cfg, target):
            target_tables = tables_for_run(evidence, doppler, target, target_run)
            pair, app = apply_to_target_repeat(
                cfg, fit, edges, target, target_run, target_tables
            )
            pair_assessments.append(pair)
            applicability.append(app)

    source_fit = pd.concat(source_fits, ignore_index=True)
    pair_assessment = pd.concat(pair_assessments, ignore_index=True)
    applicability_frame = pd.concat(applicability, ignore_index=True)
    contamination_frame = pd.concat(contamination, ignore_index=True)
    block_frame = pd.concat(blocks, ignore_index=True)
    source_fit.to_csv(out / "source_repeat_calibration_assessment.csv", index=False)
    pair_assessment.to_csv(out / "repeat_pair_transfer_assessment.csv", index=False)
    applicability_frame.to_csv(out / "repeat_pair_applicability.csv", index=False)
    contamination_frame.to_csv(out / "source_repeat_contamination_sensitivity.csv", index=False)
    block_frame.to_csv(out / "source_repeat_block_sensitivity.csv", index=False)
    parent.write_json(
        out / "repeat_hierarchy.json",
        {
            "source": source,
            "target": target,
            "source_repeats": run_names(cfg, source),
            "target_repeats": run_names(cfg, target),
            "matrix_shape": [3, 3],
            "source_fit_count": 3,
            "target_applications_per_source_fit": 3,
            "source_bootstrap_scope": "one source repeat only",
            "nine_pairs_are_independent_sessions": False,
            "summary_rule": "median/range/run sensitivity only",
        },
    )


def status_counts(frame: pd.DataFrame, alpha: float | None = None) -> dict[str, int]:
    selected = frame if alpha is None else frame[np.isclose(frame.alpha, alpha)]
    return {str(k): int(v) for k, v in selected.tail_assessment_status.value_counts().items()}


def command_report(cfg: dict[str, Any], corrective: dict[str, Any], repo: Path) -> None:
    root = root_3r(repo, corrective)
    directions = [("4.1", "4.2"), ("4.2", "4.1")]
    report_dir = root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    old_root = repo / cfg["output_root"]
    transfer_summary_rows = []
    tail_before_after_rows = []
    run_sensitivity_rows = []
    pair_matrix_rows = []
    applicability_rows = []
    contamination_rows = []
    block_rows = []
    ci_before_after_rows = []
    block_before_after_rows = []
    tail_99_detail_frames = []
    applicability_detail_frames = []

    for source, target in directions:
        token = f"{source.replace('.', 'p')}_to_{target.replace('.', 'p')}"
        direction_dir = root / f"transfer_{token}"
        source_fit = pd.read_csv(direction_dir / "source_repeat_calibration_assessment.csv")
        pairs = pd.read_csv(direction_dir / "repeat_pair_transfer_assessment.csv")
        app = pd.read_csv(direction_dir / "repeat_pair_applicability.csv")
        contam = pd.read_csv(direction_dir / "source_repeat_contamination_sensitivity.csv")
        blocks = pd.read_csv(direction_dir / "source_repeat_block_sensitivity.csv")
        old = pd.read_csv(old_root / f"transfer_{token}/transfer_assessment.csv")
        old_blocks = pd.read_csv(old_root / f"transfer_{token}/block_sensitivity.csv")
        tail_99_detail_frames.append(source_fit[np.isclose(source_fit.alpha, 0.01)].copy())
        applicability_detail_frames.append(app.copy())

        counts = Counter(source_fit.tail_assessment_status)
        candidate = Counter(source_fit.empirical_correction_candidate_status)
        transfer_summary_rows.append(
            {
                "source": source,
                "target": target,
                "source_repeat_assessment_rows": len(source_fit),
                "pair_application_rows": len(pairs),
                "eligible": counts.get("Eligible", 0),
                "partial": counts.get("Partial", 0),
                "diagnostic_only": counts.get("DiagnosticOnly", 0),
                "not_assessed_tail": counts.get("NotAssessed", 0),
                "candidate": candidate.get("candidate", 0),
                "candidate_not_assessed": candidate.get("NotAssessed", 0),
                "ratio_median": source_fit.nominal_mismatch_ratio.median(),
                "ratio_min": source_fit.nominal_mismatch_ratio.min(),
                "ratio_max": source_fit.nominal_mismatch_ratio.max(),
                "numerical_invalid": int(
                    source_fit.numerical_status.str.contains("invalid", na=False).sum()
                ),
                "pair_independence_claim": False,
            }
        )
        for scope, frame in [("before_pooled", old), ("after_per_repeat", source_fit)]:
            for alpha in [None, 0.01]:
                counts_for_scope = status_counts(frame, alpha)
                for status in ["Eligible", "Partial", "DiagnosticOnly", "NotAssessed"]:
                    tail_before_after_rows.append(
                        {
                            "source": source,
                            "target": target,
                            "scope": scope,
                            "alpha": "all" if alpha is None else alpha,
                            "tail_status": status,
                            "count": counts_for_scope.get(status, 0),
                            "denominator": len(frame) if alpha is None else int(np.isclose(frame.alpha, alpha).sum()),
                        }
                    )
            ci_width = (
                frame.candidate_simultaneous_ci_high
                / frame.candidate_simultaneous_ci_low
            )
            for alpha in [None, 0.01]:
                selected = frame if alpha is None else frame[np.isclose(frame.alpha, alpha)]
                selected_width = ci_width.loc[selected.index]
                direction_counts = Counter(selected.candidate_direction)
                candidates = Counter(selected.empirical_correction_candidate_status)
                ci_before_after_rows.append(
                    {
                        "source": source,
                        "target": target,
                        "scope": scope,
                        "alpha": "all" if alpha is None else alpha,
                        "rows": len(selected),
                        "eligible_candidate_count": candidates.get("candidate", 0),
                        "eligible_candidate_fraction": candidates.get("candidate", 0) / max(1, len(selected)),
                        "direction_increase_fraction": direction_counts.get("increase", 0) / max(1, len(selected)),
                        "direction_decrease_fraction": direction_counts.get("decrease", 0) / max(1, len(selected)),
                        "direction_neutral_fraction": direction_counts.get("neutral/indeterminate", 0) / max(1, len(selected)),
                        "ci_fold_width_median": selected_width.median(),
                        "ci_fold_width_p90": parent.percentile(selected_width.to_numpy(), 0.9),
                    }
                )

        for scope, frame in [("before_pooled", old_blocks), ("after_per_repeat", blocks)]:
            for size, group in frame.groupby("block_size_epochs"):
                block_before_after_rows.append(
                    {
                        "source": source,
                        "target": target,
                        "scope": scope,
                        "block_size_epochs": size,
                        "rows": len(group),
                        "effective_blocks_min": int(group.effective_blocks.min()),
                        "effective_blocks_median": float(group.effective_blocks.median()),
                        "effective_blocks_max": int(group.effective_blocks.max()),
                    }
                )

        ranked = source_fit.copy()
        ranked["stratum_ordinal"] = ranked.groupby(
            ["source_run", "coordinate", "alpha"]
        ).representative_support.rank(method="dense").astype(int) - 1
        for keys, group in ranked.groupby(
            ["coordinate", "alpha", "stratum_ordinal"], dropna=False
        ):
            direction_counts = Counter(group.candidate_direction)
            agreement = max(direction_counts.values()) / len(group)
            run_sensitivity_rows.append(
                {
                    "source": source,
                    "target": target,
                    "coordinate": keys[0],
                    "alpha": keys[1],
                    "stratum_ordinal": keys[2],
                    "source_repeat_count": len(group),
                    "ratio_median": group.nominal_mismatch_ratio.median(),
                    "ratio_min": group.nominal_mismatch_ratio.min(),
                    "ratio_max": group.nominal_mismatch_ratio.max(),
                    "candidate_direction_mode": direction_counts.most_common(1)[0][0],
                    "candidate_direction_mode_fraction": agreement,
                    "tail_statuses": ";".join(sorted(set(group.tail_assessment_status))),
                    "summary_is_inferential_across_independent_sessions": False,
                }
            )

        for (source_run, target_run), group in pairs.groupby(
            ["source_run", "target_run"]
        ):
            pair_matrix_rows.append(
                {
                    "source": source,
                    "target": target,
                    "source_run": source_run,
                    "target_run": target_run,
                    "rows": len(group),
                    "target_nominal_occupancy_median": group.target_nominal_membership_occupancy.median(),
                    "occupancy_gap_median": group.occupancy_gap_target_minus_source.median(),
                    "pair_is_independent_session_sample": False,
                }
            )

        for (source_run, target_run), group in app.groupby(
            ["source_run", "target_run"]
        ):
            applicability_rows.append(
                {
                    "source": source,
                    "target": target,
                    "source_run": source_run,
                    "target_run": target_run,
                    "InDomain_rate_median_across_coordinates": group.InDomain_rate.median(),
                    "OutOfDomain_rate_median_across_coordinates": group.OutOfDomain_rate.median(),
                    "NotAssessed_rate_median_across_coordinates": group.NotAssessed_rate.median(),
                    "pair_is_independent_session_sample": False,
                }
            )

        contam = contam.copy()
        contam["envelope_fold_width"] = (
            contam.candidate_ratio_upper_endpoint
            / contam.candidate_ratio_lower_endpoint
        )
        for (source_run, epsilon), group in contam.groupby(
            ["source_run", "epsilon_sensitivity"]
        ):
            contamination_rows.append(
                {
                    "source": source,
                    "target": target,
                    "source_run": source_run,
                    "epsilon_sensitivity": epsilon,
                    "median_envelope_fold_width": group.envelope_fold_width.median(),
                    "p90_envelope_fold_width": parent.percentile(
                        group.envelope_fold_width.to_numpy(), 0.9
                    ),
                    "max_envelope_fold_width": group.envelope_fold_width.max(),
                    "numerical_invalid": int(
                        (
                            (group.lower_numerical_status != "valid")
                            | (group.upper_numerical_status != "valid")
                        ).sum()
                    ),
                }
            )
        block_rows.extend(blocks.to_dict("records"))

    transfer_summary = pd.DataFrame(transfer_summary_rows)
    tail_before_after = pd.DataFrame(tail_before_after_rows)
    run_sensitivity = pd.DataFrame(run_sensitivity_rows)
    pair_matrix = pd.DataFrame(pair_matrix_rows)
    applicability_summary = pd.DataFrame(applicability_rows)
    contamination_summary = pd.DataFrame(contamination_rows)
    block_summary = pd.DataFrame(block_rows)
    ci_before_after = pd.DataFrame(ci_before_after_rows)
    block_before_after = pd.DataFrame(block_before_after_rows)
    tail_99_detail = pd.concat(tail_99_detail_frames, ignore_index=True)
    applicability_detail = pd.concat(applicability_detail_frames, ignore_index=True)
    applicability_coordinate_rows = []
    for keys, group in applicability_detail.groupby(
        ["source", "target", "coordinate"]
    ):
        applicability_coordinate_rows.append(
            {
                "source": keys[0],
                "target": keys[1],
                "coordinate": keys[2],
                "nested_repeat_pair_count": len(group),
                "InDomain_rate_median": group.InDomain_rate.median(),
                "InDomain_rate_min": group.InDomain_rate.min(),
                "InDomain_rate_max": group.InDomain_rate.max(),
                "OutOfDomain_rate_median": group.OutOfDomain_rate.median(),
                "OutOfDomain_rate_min": group.OutOfDomain_rate.min(),
                "OutOfDomain_rate_max": group.OutOfDomain_rate.max(),
                "NotAssessed_rate_median": group.NotAssessed_rate.median(),
                "NotAssessed_rate_min": group.NotAssessed_rate.min(),
                "NotAssessed_rate_max": group.NotAssessed_rate.max(),
                "nine_pairs_are_independent_sessions": False,
            }
        )
    applicability_coordinate = pd.DataFrame(applicability_coordinate_rows)
    transfer_summary.to_csv(report_dir / "transfer_summary.csv", index=False)
    tail_before_after.to_csv(report_dir / "tail_status_before_after.csv", index=False)
    run_sensitivity.to_csv(report_dir / "source_repeat_run_sensitivity.csv", index=False)
    pair_matrix.to_csv(report_dir / "repeat_pair_matrix_summary.csv", index=False)
    applicability_summary.to_csv(report_dir / "repeat_pair_applicability_summary.csv", index=False)
    contamination_summary.to_csv(report_dir / "source_repeat_contamination_summary.csv", index=False)
    block_summary.to_csv(report_dir / "source_repeat_block_sensitivity.csv", index=False)
    ci_before_after.to_csv(report_dir / "ci_direction_before_after.csv", index=False)
    block_before_after.to_csv(report_dir / "block_count_before_after.csv", index=False)
    tail_99_detail.to_csv(report_dir / "tail_99_source_repeat_detail.csv", index=False)
    applicability_coordinate.to_csv(report_dir / "applicability_coordinate_run_sensitivity.csv", index=False)

    audit_state = pd.read_csv(root / "audit/within_run_state_pair_incomparability.csv")
    audit_repeat = pd.read_csv(root / "audit/same_timestamp_repeat_pair_tradeoff.csv")
    alpha99 = tail_before_after[tail_before_after.alpha.astype(str) == "0.01"]
    old_99 = alpha99[alpha99.scope == "before_pooled"]
    new_99 = alpha99[alpha99.scope == "after_per_repeat"]
    overall = "PARTIAL"
    direction_unanimous = float(
        (run_sensitivity.candidate_direction_mode_fraction == 1.0).mean()
    )
    decision = {
        "stage": "Stage 3A.1b-1b.3R corrective transfer rerun",
        "overall": overall,
        "correction": "nested repeats are fit/applied separately in 3x3 matrices",
        "synthetic_s0_rerun": False,
        "synthetic_s0_changed": False,
        "prior_preregistration_deviation_none_revision": {
            "revised": True,
            "deviation": "The original transfer pooled C0/C1/C2 or T0/T1/T2 as one source block population, contrary to the frozen nested-repeat hierarchy.",
            "corrected_by": "Stage 3A.1b-1b.3R per-repeat source fits and target applications",
        },
        "stage_3r_preregistration_deviations": [],
        "pair_independence_claim": False,
        "within_run_state_pair_incomparability_rate_range": [
            audit_state.within_run_state_pair_incomparability_rate.min(),
            audit_state.within_run_state_pair_incomparability_rate.max(),
        ],
        "same_timestamp_repeat_pair_incomparability_rate_range": [
            audit_repeat.same_timestamp_incomparability_rate.min(),
            audit_repeat.same_timestamp_incomparability_rate.max(),
        ],
        "tail_99_before": old_99.to_dict("records"),
        "tail_99_after": new_99.to_dict("records"),
        "source_repeat_direction_mode_unanimous_fraction": direction_unanimous,
        "ci_direction_before_after": ci_before_after.to_dict("records"),
        "final_calibrator_selected": False,
        "runtime_parameters_produced": False,
        "dataset_5p2_read": False,
        "gt_or_ape_used": False,
    }
    parent.write_json(report_dir / "prototype_decision_3r.json", decision)
    (old_root / "report/SUPERSEDED_TRANSFER_NOTICE.md").write_text(
        "# Transfer hierarchy correction\n\n"
        "The transfer portion of this artifact set pooled C0/C1/C2 or "
        "T0/T1/T2 as one source block population. That violates the frozen "
        "nested-repeat hierarchy. Transfer block counts, tail eligibility, "
        "bootstrap CIs, candidate directions, applicability, and contamination "
        "inference are superseded by Stage 3A.1b-1b.3R under "
        "`output/stage3a_1b_1b_3r/v1/`. Representation audit and Synthetic S0 "
        "remain in force. The earlier `preregistration deviation = none` claim "
        "is withdrawn.\n"
    )

    lines = [
        "# Stage 3A.1b-1b.3R Corrective Transfer Rerun",
        "",
        f"- Overall result after correction: **{overall}**",
        "- Each source repeat was fitted separately and applied to each target repeat.",
        "- Each direction contains a 3x3 nested-repeat application matrix; the nine pairs are not independent sessions.",
        "- Synthetic S0 was reused unchanged.",
        "- No final calibrator or runtime parameter was produced.",
        "",
        "## Preregistration provenance correction",
        "",
        "The prior claim `preregistration deviation = none` is revised. The original pooled-repeat transfer violated the frozen repeat hierarchy. The 3R outputs correct that deviation without changing statistical parameters.",
        "",
        "## Audit semantics",
        "",
        f"- Within-run random state-pair incomparability range: {audit_state.within_run_state_pair_incomparability_rate.min():.4f}--{audit_state.within_run_state_pair_incomparability_rate.max():.4f}.",
        f"- Same-timestamp nested-repeat tradeoff range: {audit_repeat.same_timestamp_incomparability_rate.min():.4f}--{audit_repeat.same_timestamp_incomparability_rate.max():.4f}.",
        "- These are distinct estimands and are not interchangeable.",
        "",
        "## Transfer",
        "",
    ]
    for _, row in transfer_summary.iterrows():
        lines.append(
            f"- {row.source}->{row.target}: {int(row.source_repeat_assessment_rows)} source-repeat assessment rows; tail Eligible/Partial/DiagnosticOnly/NotAssessed = {int(row.eligible)}/{int(row.partial)}/{int(row.diagnostic_only)}/{int(row.not_assessed_tail)}; ratio median/range = {row.ratio_median:.4f} [{row.ratio_min:.4f}, {row.ratio_max:.4f}]."
        )
    lines.extend(
        [
            "",
            "## Before/after uncertainty",
            "",
        ]
    )
    for source, target in directions:
        before = ci_before_after[
            (ci_before_after.source == source)
            & (ci_before_after.target == target)
            & (ci_before_after.scope == "before_pooled")
            & (ci_before_after.alpha.astype(str) == "all")
        ].iloc[0]
        after = ci_before_after[
            (ci_before_after.source == source)
            & (ci_before_after.target == target)
            & (ci_before_after.scope == "after_per_repeat")
            & (ci_before_after.alpha.astype(str) == "all")
        ].iloc[0]
        lines.append(
            f"- {source}->{target}: median CI fold width {before.ci_fold_width_median:.3f} -> {after.ci_fold_width_median:.3f}; candidate fraction {before.eligible_candidate_fraction:.3f} -> {after.eligible_candidate_fraction:.3f}."
        )
    lines.append(
        f"- Source-repeat direction mode is unanimous in {direction_unanimous:.3f} of matched coordinate/alpha/ordinal-stratum cells; this is run sensitivity, not independent-session validation."
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The overall result remains PARTIAL. The corrected hierarchy changes effective block/tail support and CI directions, so the original pooled transfer counts are not valid inferential evidence. Run sensitivity is reported only by median/range; no nine-pair independence claim is made.",
        ]
    )
    (report_dir / "report_3r.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("audit")
    transfer = sub.add_parser("transfer")
    transfer.add_argument("--source", choices=["4.1", "4.2"], required=True)
    transfer.add_argument("--target", choices=["4.1", "4.2"], required=True)
    sub.add_parser("report")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    cfg, corrective = load_contracts()
    if args.command == "validate":
        command_validate(cfg, corrective, repo)
    elif args.command == "audit":
        command_audit(cfg, corrective, repo)
    elif args.command == "transfer":
        if args.source == args.target:
            raise RuntimeError("Source and target must differ")
        command_transfer(cfg, corrective, repo, args.source, args.target)
    elif args.command == "report":
        command_report(cfg, corrective, repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
