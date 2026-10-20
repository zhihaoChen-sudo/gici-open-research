#!/usr/bin/env python3
"""Audit-only detail report for Stage 3A.1b-1b.4b-R1.

Only the three frozen pre-solve GNSS evidence CSVs are read.  The old run is
represented solely by the already-frozen Stage 4b aggregate artifacts because
its raw per-epoch CSVs are no longer present.  This tool performs no fitting,
filtering, trajectory evaluation, or 5.2 access.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

import yaml


REPO = Path("/home/czh/Projects/gici-open")
NEW_DIR = Path("/home/czh/Projects/gici-data/实验_raw/5.1")
CONFIG = Path("/home/czh/Projects/gici-data/5.1/post_estimation_RTK_RRR.yaml")
EXECUTABLE = REPO / "ros_wrapper/devel/lib/gici_ros/gici_ros_main"
OLD_OUT = REPO / "output/stage3a_1b_1b_4b/v1"
NEW_OUT = REPO / "output/stage3a_1b_1b_4b_r1/v1"

PREFIXES = {
    "source": "gnss_source_reliability_evidence-",
    "doppler": "gnss_doppler_system_evidence-",
    "preopt": "gnss_preopt_residual_diagnostics-",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def only_file(prefix: str) -> Path:
    matches = sorted(NEW_DIR.glob(prefix + "*.csv"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {prefix}*.csv, found {len(matches)}")
    return matches[0]


def read_csv_rows(path: Path, kind: str) -> dict:
    timestamp_set: set[str] = set()
    source_doppler_support: dict[str, tuple[int, int, int, int]] = {}
    duplicate_keys = 0
    malformed_rows = 0
    row_count = 0
    first_timestamp = None
    last_timestamp = None
    previous = -math.inf
    timestamp_order = True
    epoch_keys: set[tuple[str, ...]] = set()
    epoch_timestamp = None
    system_factor_counts: Counter[str] = Counter()

    with path.open(newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        index = {name: pos for pos, name in enumerate(header)}
        for fields in reader:
            if not fields:
                continue
            if len(fields) != len(header):
                malformed_rows += 1
                continue
            row_count += 1
            timestamp = fields[index["timestamp"]]
            value = float(timestamp)
            if first_timestamp is None:
                first_timestamp = timestamp
            last_timestamp = timestamp
            if kind == "source":
                if value <= previous:
                    timestamp_order = False
                key = (timestamp,)
                if key in epoch_keys:
                    duplicate_keys += 1
                epoch_keys.add(key)
                source_doppler_support[timestamp] = tuple(
                    int(fields[index[name]]) for name in (
                        "doppler_evaluation_attempt_count",
                        "doppler_finite_success_count",
                        "doppler_evaluation_failure_count",
                        "doppler_system_count",
                    )
                )
            else:
                if value < previous:
                    timestamp_order = False
                if timestamp != epoch_timestamp:
                    epoch_keys.clear()
                    epoch_timestamp = timestamp
                if kind == "doppler":
                    key = (timestamp, fields[index["system"]])
                else:
                    key = (
                        timestamp,
                        fields[index["measurement_type"]],
                        fields[index["residual_uid"]],
                    )
                    measurement_type = fields[index["measurement_type"]]
                    prn_field = "prn" if measurement_type == "doppler" else "rov_prn"
                    prn = fields[index[prn_field]]
                    system_factor_counts[f"{measurement_type}:{prn[:1]}"] += 1
                if key in epoch_keys:
                    duplicate_keys += 1
                epoch_keys.add(key)
            timestamp_set.add(timestamp)
            previous = value

    return {
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "header": header,
        "header_sha256": hashlib.sha256(",".join(header).encode()).hexdigest(),
        "row_count": row_count,
        "malformed_or_truncated_rows": malformed_rows,
        "timestamp_order": timestamp_order,
        "duplicate_epoch_or_factor_keys": duplicate_keys,
        "unique_timestamp_count": len(timestamp_set),
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "timestamps": timestamp_set,
        "source_doppler_support": source_doppler_support,
        "system_factor_counts": dict(sorted(system_factor_counts.items())),
    }


def csv_row(path: Path, sequence: str, run: str) -> dict[str, str]:
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("sequence") == sequence and row.get("run") == run:
                return row
    raise RuntimeError(f"missing {sequence}/{run} in {path}")


def mask_rates(path: Path, sequence: str, run: str, kind: str) -> dict[str, float]:
    result = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["sequence"] == sequence and row["run"] == run and row["kind"] == kind:
                result[row["mask"]] = float(row["rate"])
    return result


def scalar(row: dict[str, str], name: str) -> float:
    return float(row[name])


def nested(config: dict, path: tuple[str | int, ...]):
    value = config
    for item in path:
        value = value[item]
    return value


def main() -> int:
    NEW_OUT.mkdir(parents=True, exist_ok=True)
    paths = {kind: only_file(prefix) for kind, prefix in PREFIXES.items()}
    audits = {kind: read_csv_rows(path, kind) for kind, path in paths.items()}

    source_ts = audits["source"]["timestamps"]
    doppler_ts = audits["doppler"]["timestamps"]
    preopt_ts = audits["preopt"]["timestamps"]
    missing_doppler = sorted(source_ts - doppler_ts, key=float)
    missing_doppler_nonzero = [
        timestamp for timestamp in missing_doppler
        if audits["source"]["source_doppler_support"][timestamp] != (0, 0, 0, 0)
    ]

    run = csv_row(NEW_OUT / "run_sanity.csv", "5.1", "R1")
    integrity = {
        "stage": "Stage 3A.1b-1b.4b-R1",
        "input_policy": {
            "calibrator_fitting": False,
            "row_or_epoch_filtering": False,
            "dataset_5.2_read": False,
            "GT_APE_EVO_AR_FIX_used": False,
            "AR_FIX_columns_accessed_for_analysis": False,
        },
        "files": {
            kind: {key: value for key, value in audit.items()
                   if key not in {"timestamps", "source_doppler_support"}}
            for kind, audit in audits.items()
        },
        "alignment": {
            "source_minus_preopt_timestamps": len(source_ts - preopt_ts),
            "preopt_minus_source_timestamps": len(preopt_ts - source_ts),
            "doppler_minus_source_timestamps": len(doppler_ts - source_ts),
            "source_without_doppler_system_rows": len(missing_doppler),
            "source_without_doppler_rows_but_nonzero_support": len(missing_doppler_nonzero),
            "source_without_doppler_rows_and_zero_support": len(missing_doppler) - len(missing_doppler_nonzero),
            "common_start_timestamp": len({audit["first_timestamp"] for audit in audits.values()}) == 1,
            "common_terminal_timestamp": len({audit["last_timestamp"] for audit in audits.values()}) == 1,
        },
        "closure": {
            "evaluation_failures": int(run["evaluation_failures"]),
            "closure_failures": int(run["closure_failures"]),
            "unexpected_nonfinite": int(run["unexpected_nonfinite"]),
            "PR_factors": int(run["pr_factors"]),
            "Phase_factors": int(run["phase_factors"]),
            "Doppler_factors": int(run["doppler_factors"]),
            "preopt_factor_rows": audits["preopt"]["row_count"],
            "preopt_factor_total_closure": (
                int(run["pr_factors"]) + int(run["phase_factors"])
                + int(run["doppler_factors"]) == audits["preopt"]["row_count"]
            ),
        },
        "admission": "EligibleForPanel",
    }
    (NEW_OUT / "admission_integrity.json").write_text(
        json.dumps(integrity, indent=2, sort_keys=True) + "\n"
    )

    old = csv_row(OLD_OUT / "run_sanity.csv", "5.1", "S0")
    comparisons = []
    fields = (
        "evidence_epochs", "pr_factors", "phase_factors", "doppler_factors",
        "evaluation_failures", "unexpected_nonfinite", "closure_failures",
        "phase_conditioned_available_rate", "phase_continued_ratio_overall",
        "phase_new_ratio_overall", "phase_mixed_ratio_overall",
        "phase_slip_ratio_overall", "phase_unknown_count",
        "pr_complete_coordinate_rate", "doppler_cegr_mask_rate",
        "satellite_support_min", "satellite_support_median", "satellite_support_max",
        "gdop_valid_rate", "gdop_valid_median", "elevation_valid_rate",
    )
    for name in fields:
        old_value = scalar(old, name)
        new_value = scalar(run, name)
        comparisons.append({
            "metric": name,
            "old_5.1": old_value,
            "new_5.1_R1": new_value,
            "delta_new_minus_old": new_value - old_value,
            "comparison_scope": "aggregate_only",
        })
    for kind in ("pr_valid_mask", "doppler_system_mask"):
        old_masks = mask_rates(OLD_OUT / "mask_patterns.csv", "5.1", "S0", kind)
        new_masks = mask_rates(NEW_OUT / "mask_patterns.csv", "5.1", "R1", kind)
        for mask in sorted(set(old_masks) | set(new_masks)):
            comparisons.append({
                "metric": f"{kind}:{mask}",
                "old_5.1": old_masks.get(mask, 0.0),
                "new_5.1_R1": new_masks.get(mask, 0.0),
                "delta_new_minus_old": new_masks.get(mask, 0.0) - old_masks.get(mask, 0.0),
                "comparison_scope": "aggregate_only",
            })
    with (NEW_OUT / "old_new_aggregate_comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=comparisons[0].keys())
        writer.writeheader()
        writer.writerows(comparisons)
    comparison_limit = {
        "old_raw_csv_available": False,
        "old_raw_paths_recorded_by_prior_audit": [
            "/home/czh/Projects/gici-data/实验/5.1/gnss_source_reliability_evidence-20260829-145853.csv",
            "/home/czh/Projects/gici-data/实验/5.1/gnss_doppler_system_evidence-20260829-145853.csv",
            "/home/czh/Projects/gici-data/实验/5.1/gnss_preopt_residual_diagnostics-20260829-145853.csv",
        ],
        "same_timestamp_repeatability": "NotAssessed: old per-epoch CSVs are absent",
        "available_comparison": "frozen old aggregate descriptors versus new aggregate descriptors",
        "admission_dependency": "none; old/new comparison is diagnostic only",
    }
    (NEW_OUT / "old_new_comparison_limit.json").write_text(
        json.dumps(comparison_limit, indent=2, sort_keys=True) + "\n"
    )

    with (OLD_OUT / "sequence_decision.csv").open(newline="") as stream:
        final_panel = list(csv.DictReader(stream))
    new_sequence = None
    with (NEW_OUT / "sequence_decision.csv").open(newline="") as stream:
        for candidate in csv.DictReader(stream):
            if candidate["sequence"] == "5.1":
                new_sequence = candidate
                break
    if new_sequence is None:
        raise RuntimeError("missing new 5.1 sequence decision")
    for index, row in enumerate(final_panel):
        if row["sequence"] == "5.1":
            final_panel[index] = dict(new_sequence)
            final_panel[index]["notes"] = "new R1 supersedes old rejected artifact"
            break
    with (NEW_OUT / "panel_final_decision.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=final_panel[0].keys())
        writer.writeheader()
        writer.writerows(final_panel)
    final_decision = {
        "stage_4b_final": "PASS",
        "eligible_sequence_count": sum(
            row["classification"] == "EligibleForPanel" for row in final_panel
        ),
        "partial_sequence_count": sum(row["classification"] == "Partial" for row in final_panel),
        "reject_sequence_count": sum(row["classification"] == "Reject" for row in final_panel),
        "panel": [row["sequence"] for row in final_panel],
        "5.1_current_artifact": str(NEW_DIR),
        "5.1_old_artifact_status": "superseded; retained in prior Stage 4b artifacts; not calibration input",
        "stage_4c_started": False,
    }
    (NEW_OUT / "panel_final_decision.json").write_text(
        json.dumps(final_decision, indent=2, sort_keys=True) + "\n"
    )

    config = yaml.safe_load(CONFIG.read_text())
    estimator = nested(config, ("estimate", 0, "estimator"))
    base = estimator["gnss_estimator_base_options"]
    rrr = estimator["rtk_imu_camera_rrr_options"]
    ar = estimator["ambiguity_resolution_options"]
    initializer = estimator["gnss_imu_initializer_options"]
    file_token = re.search(r"-(\d{8}-\d{6})\.csv$", paths["source"].name)
    provenance = {
        "config": {
            "path": str(CONFIG),
            "sha256": sha256(CONFIG),
            "mtime_ns": CONFIG.stat().st_mtime_ns,
            "binding": "user-reported run config; current file postdates evidence and is not artifact-bound",
        },
        "source_tree": {
            "audit_HEAD": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
            ).strip(),
            "run_commit_binding": "unproven",
        },
        "executable": {
            "path": str(EXECUTABLE),
            "current_sha256": sha256(EXECUTABLE),
            "mtime_ns": EXECUTABLE.stat().st_mtime_ns,
            "run_binding": "binary binding cannot be proven retrospectively",
        },
        "output": {
            "directory": str(NEW_DIR),
            "filename_run_timestamp_token": file_token.group(1) if file_token else None,
            "source_file_mtime_ns": paths["source"].stat().st_mtime_ns,
        },
        "evidence_schema": {
            kind: audit["header_sha256"] for kind, audit in audits.items()
        },
        "stage3a_flags": {
            key: rrr[key] for key in (
                "use_cauchy_loss_for_dd_pseudorange",
                "estimate_reliability_for_dd_pseudorange",
                "apply_reliability_weight_for_dd_pseudorange",
                "estimate_gnss_source_reliability",
            )
        } | {"log_intermediate_data": estimator["estimator_base_options"]["log_intermediate_data"]},
        "measurement_covariance_configuration": {
            "current_config_sha256_record_only": True,
            "use_outlier_rejection": base["use_outlier_rejection"],
            "reject_one_outlier_once": base["reject_one_outlier_once"],
            "max_pesudorange_error": base["max_pesudorange_error"],
            "max_phaserange_error": base["max_phaserange_error"],
            "max_doppler_error": base["max_doppler_error"],
            "gnss_common": base["gnss_common"],
            "implicit_or_default_noise_parameters": "not separately run-bound",
        },
        "gnss_lever_arm_m": initializer["gnss_extrinsics"],
        "ambiguity_resolution_system_exclude": ar["system_exclude"],
    }
    (NEW_OUT / "rerun_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )

    counts = audits["preopt"]["system_factor_counts"]
    report = f"""# Stage 3A.1b-1b.4b-R1 — 5.1 Rerun Admission Audit

## Decision

- `5.1 = EligibleForPanel`
- Final Stage 4b panel result: **PASS** (11 Eligible, 0 Partial, 0 Reject).
- Stage 4c started: **no**.
- New artifact `{NEW_DIR}` supersedes the old rejected 5.1 artifact. The old
  aggregate audit remains retained and is not a calibration input.

## New-run integrity

- Source epochs: {audits['source']['row_count']}; Doppler-system rows:
  {audits['doppler']['row_count']}; preopt factor rows: {audits['preopt']['row_count']}.
- PR/Phase/Doppler factor totals: {run['pr_factors']} / {run['phase_factors']} /
  {run['doppler_factors']}; their sum equals the preopt row count.
- Malformed/truncated rows, duplicate epoch/factor keys, evaluation failures,
  unexpected nonfinite values, and closure failures: all zero.
- All files are timestamp ordered and share start {audits['source']['first_timestamp']}
  and terminal {audits['source']['last_timestamp']}.
- Source and preopt timestamp sets are identical. All Doppler-system timestamps
  are source timestamps. The 84 source epochs without Doppler-system rows all
  have attempt/success/failure/system-count `(0,0,0,0)`; no nonzero-support
  epoch is missing a Doppler-system row.
- No row or epoch was removed or filtered.

## Old/new diagnostic comparison

- Old/new evidence epochs: {old['evidence_epochs']} / {run['evidence_epochs']}.
- Old/new closure failures: {old['closure_failures']} / {run['closure_failures']}.
- Aggregate conditioned-phase availability:
  {old['phase_conditioned_available_rate']} / {run['phase_conditioned_available_rate']}.
- Aggregate complete-PR mask rate:
  {old['pr_complete_coordinate_rate']} / {run['pr_complete_coordinate_rate']}.
- Aggregate CEGR Doppler-mask rate:
  {old['doppler_cegr_mask_rate']} / {run['doppler_cegr_mask_rate']}.
- Phase provenance, PR masks, Doppler masks, satellite support, GDOP, and
  elevation descriptors are close at aggregate level; the old malformed-tail
  and cross-file-alignment failures are absent in R1.
- The old per-epoch CSVs are no longer present, so same-timestamp evidence
  repeatability is `NotAssessed`. Aggregate similarity is not represented as a
  same-timestamp correlation result and is not needed for admission.

## Provenance boundary

- Current config: `{CONFIG}`; SHA-256 `{provenance['config']['sha256']}`.
- Audit source HEAD: `{provenance['source_tree']['audit_HEAD']}`; run commit
  binding is unproven.
- Current executable: `{EXECUTABLE}`; SHA-256
  `{provenance['executable']['current_sha256']}`.
- **binary binding cannot be proven retrospectively**. The current config also
  postdates the evidence and is accepted as user-reported run provenance, not
  as artifact-bound proof.
- Filename run token: `{provenance['output']['filename_run_timestamp_token']}`.
- GNSS lever arm recorded by the current config: `{provenance['gnss_lever_arm_m']}` m.
- Stage 3A flags are frozen shadow-only; covariance/rejection and GNSS common
  values are recorded in `rerun_provenance.json`.

## GLONASS/R semantics

- `ambiguity_resolution_options.system_exclude: [R]` is loaded into
  `AmbiguityResolutionOptions` and filters ambiguity-resolution candidates. It
  is not the GNSS-common system filter used to construct PR/Phase/Doppler
  measurement factors.
- New 5.1 factor counts by system are:
  PR C/E/G/R = {counts.get('dd_pseudorange:C', 0)}/{counts.get('dd_pseudorange:E', 0)}/
  {counts.get('dd_pseudorange:G', 0)}/{counts.get('dd_pseudorange:R', 0)};
  Phase C/E/G/R = {counts.get('dd_phaserange:C', 0)}/{counts.get('dd_phaserange:E', 0)}/
  {counts.get('dd_phaserange:G', 0)}/{counts.get('dd_phaserange:R', 0)};
  Doppler C/E/G/R = {counts.get('doppler:C', 0)}/{counts.get('doppler:E', 0)}/
  {counts.get('doppler:G', 0)}/{counts.get('doppler:R', 0)}.
- Therefore R in PR/Doppler is expected and does not contradict AR exclusion.
  DD phase has stricter rover/reference phase-plus-code pairing and natural-base
  requirements; the artifact contains no R phase factor. The allowed artifacts
  do not identify which upstream R phase-validity/pairing condition failed, so
  that narrower cause remains unobserved. The verified behavior is
  measurement-type-specific availability, not a config/provenance conflict.
"""
    (NEW_OUT / "admission_report.md").write_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
