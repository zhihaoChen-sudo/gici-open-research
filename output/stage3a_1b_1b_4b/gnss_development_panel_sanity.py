#!/usr/bin/env python3
"""Stage 3A.1b-1b.4b development-panel sanity/provenance/support audit.

The input whitelist is deliberately narrow.  This tool never reads solutions,
GT/APE, post-fit residuals, rejection/AR diagnostics, event labels, or dataset
5.2.  It performs no calibration, fitting, threshold selection, or trajectory
evaluation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import re
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


SOURCE_PREFIX = "gnss_source_reliability_evidence-"
DOPPLER_PREFIX = "gnss_doppler_system_evidence-"
PREOPT_PREFIX = "gnss_preopt_residual_diagnostics-"
FORBIDDEN_TOKENS = ("/5.2/", "/5.2", "position_ape", "ground_truth", "solution")

SOURCE_REQUIRED = {
    "timestamp",
    "pr_evaluation_attempt_count", "pr_finite_success_count", "pr_evaluation_failure_count",
    "phase_evaluation_attempt_count", "phase_finite_success_count", "phase_evaluation_failure_count",
    "doppler_evaluation_attempt_count", "doppler_finite_success_count", "doppler_evaluation_failure_count",
    "pr_p90_abs_normalized", "pr_group_count", "pr_group_eligible_count",
    "pr_group_insufficient_count", "pr_factor_count", "pr_factor_eligible_count",
    "pr_factor_insufficient_count", "pr_eligible_group_ratio", "pr_eligible_factor_ratio",
    "pr_insufficient_group_ratio", "pr_insufficient_factor_ratio",
    "pr_group_shift_all_p90", "pr_group_scale_eligible_p90",
    "phase_total_count", "phase_both_continued_count", "phase_both_continued_ratio",
    "phase_both_new_count", "phase_both_new_ratio", "phase_mixed_count", "phase_mixed_ratio",
    "phase_any_slip_count", "phase_any_slip_ratio", "phase_unknown_count", "phase_unknown_ratio",
    "phase_continuity_conditioned_count", "phase_continuity_conditioned_p90_abs_normalized",
    "doppler_p90_abs_normalized", "doppler_system_count", "doppler_minimum_system_support",
    "doppler_median_system_support", "unique_used_satellite_count", "gdop", "gdop_valid",
    "elevation_sample_count", "elevation_valid", "elevation_p10_deg", "elevation_median_deg",
}
DOPPLER_REQUIRED = {
    "timestamp", "system", "factor_count", "finite_count", "evaluation_failure_count",
    "center_normalized", "scale_normalized",
}
PREOPT_REQUIRED = {
    "timestamp", "measurement_type", "rov_prn", "prn", "normalized_residual",
    "raw_residual", "effective_sigma",
}

PR_COORDS = ("pr_p90_abs_normalized", "pr_group_shift_all_p90", "pr_group_scale_eligible_p90")
SUPPORT_FIELDS = (
    "pr_finite_success_count", "pr_group_count", "pr_group_eligible_count",
    "phase_finite_success_count", "phase_continuity_conditioned_count",
    "doppler_finite_success_count", "doppler_system_count", "unique_used_satellite_count",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(jsonable(value), indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: jsonable(v) for k, v in row.items()})


def only_file(directory: Path, prefix: str) -> Path:
    matches = sorted(directory.glob(prefix + "*.csv"))
    if len(matches) != 1:
        raise RuntimeError(f"{directory}: expected exactly one {prefix}*.csv, found {len(matches)}")
    path = matches[0]
    text = str(path)
    if any(token in text for token in FORBIDDEN_TOKENS):
        raise RuntimeError(f"forbidden path: {path}")
    return path


def f(parts: list[bytes], idx: dict[str, int], name: str) -> float:
    try:
        return float(parts[idx[name]])
    except (ValueError, OverflowError):
        return math.nan


def i(parts: list[bytes], idx: dict[str, int], name: str) -> int:
    value = f(parts, idx, name)
    return int(value) if math.isfinite(value) else -1


def ratio_ok(num: int, den: int, value: float, tol: float = 1e-10) -> bool:
    if den == 0:
        return not math.isfinite(value)
    return math.isfinite(value) and abs(value - num / den) <= tol


def quantiles(values: list[float]) -> dict[str, float | None]:
    finite = sorted(v for v in values if math.isfinite(v))
    if not finite:
        return {"min": None, "p05": None, "median": None, "p95": None, "max": None}

    def q(p: float) -> float:
        if len(finite) == 1:
            return finite[0]
        pos = p * (len(finite) - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        return finite[lo] + (pos - lo) * (finite[hi] - finite[lo])

    return {"min": finite[0], "p05": q(0.05), "median": q(0.5), "p95": q(0.95), "max": finite[-1]}


def parse_source(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    rows: list[dict[str, Any]] = []
    masks: Counter[str] = Counter()
    phase_available = 0
    phase_category_totals = Counter()
    closure = Counter()
    failures = Counter()
    unexpected_nonfinite = Counter()
    invalid_context_sentinel = Counter()
    supports: dict[str, list[float]] = {key: [] for key in SUPPORT_FIELDS}
    context: dict[str, list[float]] = defaultdict(list)
    timestamps: list[float] = []
    width_errors = 0

    with path.open("rb") as stream:
        raw_header = stream.readline()
        h.update(raw_header)
        header = raw_header.decode().rstrip("\r\n").split(",")
        idx = {name: pos for pos, name in enumerate(header)}
        missing = sorted(SOURCE_REQUIRED - set(header))
        if missing:
            return {"fatal": f"missing source columns {missing}", "header": header, "sha256": ""}
        for raw in stream:
            h.update(raw)
            parts = raw.rstrip(b"\r\n").split(b",")
            if not parts or parts == [b""]:
                continue
            if len(parts) != len(header):
                width_errors += 1
                continue
            ts = f(parts, idx, "timestamp")
            timestamps.append(ts)
            row: dict[str, Any] = {"timestamp": ts}
            for prefix in ("pr", "phase", "doppler"):
                a = i(parts, idx, f"{prefix}_evaluation_attempt_count")
                s = i(parts, idx, f"{prefix}_finite_success_count")
                e = i(parts, idx, f"{prefix}_evaluation_failure_count")
                row[f"{prefix}_success"] = s
                failures[prefix] += max(e, 0)
                if a != s + e:
                    closure[f"{prefix}_attempt"] += 1

            pg = i(parts, idx, "pr_group_count")
            pge = i(parts, idx, "pr_group_eligible_count")
            pgi = i(parts, idx, "pr_group_insufficient_count")
            pf = i(parts, idx, "pr_factor_count")
            pfe = i(parts, idx, "pr_factor_eligible_count")
            pfi = i(parts, idx, "pr_factor_insufficient_count")
            if pg != pge + pgi:
                closure["pr_group_partition"] += 1
            if pf != pfe + pfi or pf != row["pr_success"]:
                closure["pr_factor_partition"] += 1
            for name, num, den in (
                ("pr_eligible_group_ratio", pge, pg),
                ("pr_insufficient_group_ratio", pgi, pg),
                ("pr_eligible_factor_ratio", pfe, pf),
                ("pr_insufficient_factor_ratio", pfi, pf),
            ):
                if not ratio_ok(num, den, f(parts, idx, name)):
                    closure[name] += 1

            pt = i(parts, idx, "phase_total_count")
            phase_parts = [
                i(parts, idx, "phase_both_continued_count"),
                i(parts, idx, "phase_both_new_count"),
                i(parts, idx, "phase_mixed_count"),
                i(parts, idx, "phase_any_slip_count"),
                i(parts, idx, "phase_unknown_count"),
            ]
            for name, count in zip(
                ("continued", "new", "mixed", "slip", "unknown"), phase_parts
            ):
                phase_category_totals[name] += count
            phase_category_totals["total"] += pt
            if pt != row["phase_success"] or sum(phase_parts) != pt:
                closure["phase_category_partition"] += 1
            phase_ratio_fields = (
                "phase_both_continued_ratio", "phase_both_new_ratio", "phase_mixed_ratio",
                "phase_any_slip_ratio", "phase_unknown_ratio",
            )
            for count, name in zip(phase_parts, phase_ratio_fields):
                if not ratio_ok(count, pt, f(parts, idx, name)):
                    closure[name] += 1
            conditioned = i(parts, idx, "phase_continuity_conditioned_count")
            if conditioned > phase_parts[0]:
                closure["phase_conditioned_le_continued"] += 1
            phase_p90 = f(parts, idx, "phase_continuity_conditioned_p90_abs_normalized")
            if conditioned > 0 and math.isfinite(phase_p90):
                phase_available += 1
            elif conditioned > 0 or math.isfinite(phase_p90):
                unexpected_nonfinite["phase_conditioned"] += 1

            coords = [f(parts, idx, name) for name in PR_COORDS]
            masks["".join("1" if math.isfinite(x) else "0" for x in coords)] += 1
            if row["pr_success"] > 0 and not math.isfinite(coords[0]):
                unexpected_nonfinite["pr_population"] += 1
            if pg > 0 and not math.isfinite(coords[1]):
                unexpected_nonfinite["pr_group_shift"] += 1
            if pge > 0 and not math.isfinite(coords[2]):
                unexpected_nonfinite["pr_group_scale"] += 1

            doppler_p90 = f(parts, idx, "doppler_p90_abs_normalized")
            if row["doppler_success"] > 0 and not math.isfinite(doppler_p90):
                unexpected_nonfinite["doppler_p90"] += 1

            for name in SUPPORT_FIELDS:
                supports[name].append(f(parts, idx, name))
            gdop_valid = i(parts, idx, "gdop_valid")
            elevation_valid = i(parts, idx, "elevation_valid")
            context["unique_used_satellite_count"].append(
                f(parts, idx, "unique_used_satellite_count")
            )
            context["elevation_sample_count"].append(f(parts, idx, "elevation_sample_count"))
            context["gdop_valid"].append(float(gdop_valid))
            context["elevation_valid"].append(float(elevation_valid))
            gdop_value = f(parts, idx, "gdop")
            if gdop_valid:
                context["gdop"].append(gdop_value)
            elif math.isfinite(gdop_value):
                invalid_context_sentinel["gdop"] += 1
            if gdop_valid and not math.isfinite(gdop_value):
                unexpected_nonfinite["gdop_validity"] += 1
            elevation_p10 = f(parts, idx, "elevation_p10_deg")
            elevation_median = f(parts, idx, "elevation_median_deg")
            if elevation_valid:
                context["elevation_p10_deg"].append(elevation_p10)
                context["elevation_median_deg"].append(elevation_median)
            if elevation_valid and (
                not math.isfinite(elevation_p10) or not math.isfinite(elevation_median)
            ):
                unexpected_nonfinite["elevation_validity"] += 1

            row["phase_conditioned_count"] = conditioned
            row["doppler_system_count"] = i(parts, idx, "doppler_system_count")
            rows.append(row)

    monotonic = all(math.isfinite(v) for v in timestamps) and all(
        a < b for a, b in zip(timestamps, timestamps[1:])
    )
    return {
        "fatal": None,
        "header": header,
        "header_sha256": hashlib.sha256((",".join(header)).encode()).hexdigest(),
        "sha256": h.hexdigest(),
        "rows": rows,
        "row_count": len(rows),
        "width_errors": width_errors,
        "timestamp_order": monotonic,
        "closure": dict(closure),
        "failures": dict(failures),
        "unexpected_nonfinite": dict(unexpected_nonfinite),
        "invalid_context_sentinel": dict(invalid_context_sentinel),
        "pr_masks": masks,
        "phase_available": phase_available,
        "phase_category_totals": dict(phase_category_totals),
        "supports": supports,
        "context": context,
    }


def parse_doppler(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    by_ts: dict[float, dict[str, Any]] = defaultdict(lambda: {
        "factor": 0, "finite": 0, "failure": 0, "systems": set(), "rows": 0,
    })
    timestamps: list[float] = []
    systems: set[str] = set()
    width_errors = 0
    closure_errors = 0
    unexpected_nonfinite = 0
    mask_counts: Counter[str] = Counter()

    with path.open("rb") as stream:
        raw_header = stream.readline()
        h.update(raw_header)
        header = raw_header.decode().rstrip("\r\n").split(",")
        idx = {name: pos for pos, name in enumerate(header)}
        missing = sorted(DOPPLER_REQUIRED - set(header))
        if missing:
            return {"fatal": f"missing doppler columns {missing}", "header": header, "sha256": ""}
        for raw in stream:
            h.update(raw)
            parts = raw.rstrip(b"\r\n").split(b",")
            if not parts or parts == [b""]:
                continue
            if len(parts) != len(header):
                width_errors += 1
                continue
            ts = f(parts, idx, "timestamp")
            timestamps.append(ts)
            system = parts[idx["system"]].decode()
            factor = i(parts, idx, "factor_count")
            finite_count = i(parts, idx, "finite_count")
            failure = i(parts, idx, "evaluation_failure_count")
            if factor != finite_count + failure:
                closure_errors += 1
            center = f(parts, idx, "center_normalized")
            scale = f(parts, idx, "scale_normalized")
            if finite_count > 0 and not math.isfinite(center):
                unexpected_nonfinite += 1
            if finite_count >= 2 and not math.isfinite(scale):
                unexpected_nonfinite += 1
            item = by_ts[ts]
            item["factor"] += factor
            item["finite"] += finite_count
            item["failure"] += failure
            item["systems"].add(system)
            item["rows"] += 1
            systems.add(system)
    for item in by_ts.values():
        mask_counts["".join(sorted(item["systems"]))] += 1
    monotonic = all(math.isfinite(v) for v in timestamps) and all(
        a <= b for a, b in zip(timestamps, timestamps[1:])
    )
    return {
        "fatal": None,
        "header": header,
        "header_sha256": hashlib.sha256((",".join(header)).encode()).hexdigest(),
        "sha256": h.hexdigest(),
        "row_count": len(timestamps),
        "width_errors": width_errors,
        "timestamp_order": monotonic,
        "closure_errors": closure_errors,
        "unexpected_nonfinite": unexpected_nonfinite,
        "by_ts": by_ts,
        "systems": systems,
        "masks": mask_counts,
    }


def parse_preopt(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    by_ts: dict[float, Counter[str]] = defaultdict(Counter)
    systems: dict[str, set[str]] = defaultdict(set)
    timestamps: list[float] = []
    width_errors = 0
    nonfinite = Counter()

    with path.open("rb") as stream:
        raw_header = stream.readline()
        h.update(raw_header)
        header = raw_header.decode().rstrip("\r\n").split(",")
        idx = {name: pos for pos, name in enumerate(header)}
        missing = sorted(PREOPT_REQUIRED - set(header))
        if missing:
            return {"fatal": f"missing preopt columns {missing}", "header": header, "sha256": ""}
        for raw in stream:
            h.update(raw)
            parts = raw.rstrip(b"\r\n").split(b",")
            if not parts or parts == [b""]:
                continue
            if len(parts) != len(header):
                width_errors += 1
                continue
            ts = f(parts, idx, "timestamp")
            timestamps.append(ts)
            kind = parts[idx["measurement_type"]].decode()
            by_ts[ts][kind] += 1
            prn_field = "prn" if kind == "doppler" else "rov_prn"
            prn = parts[idx[prn_field]].decode()
            if prn:
                systems[kind].add(prn[0])
            for name in ("normalized_residual", "raw_residual", "effective_sigma"):
                value = f(parts, idx, name)
                if not math.isfinite(value) or (name == "effective_sigma" and value <= 0.0):
                    nonfinite[name] += 1
    monotonic = all(math.isfinite(v) for v in timestamps) and all(
        a <= b for a, b in zip(timestamps, timestamps[1:])
    )
    return {
        "fatal": None,
        "header": header,
        "header_sha256": hashlib.sha256((",".join(header)).encode()).hexdigest(),
        "sha256": h.hexdigest(),
        "row_count": len(timestamps),
        "width_errors": width_errors,
        "timestamp_order": monotonic,
        "nonfinite": dict(nonfinite),
        "by_ts": by_ts,
        "systems": systems,
    }


def strip_identity(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in {"path", "start_time", "log_intermediate_data_directory", "file_directory"}:
                continue
            out[key] = strip_identity(item)
        return out
    if isinstance(value, list):
        return [strip_identity(item) for item in value]
    return value


def nested_find(value: Any, key: str) -> list[Any]:
    found = []
    if isinstance(value, dict):
        for name, item in value.items():
            if name == key:
                found.append(item)
            found.extend(nested_find(item, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(nested_find(item, key))
    return found


def config_audit(config: Path, reference_normalized: Any, expected_flags: dict[str, Any],
                 evidence_mtime_ns: int, accepted_prior: bool) -> dict[str, Any]:
    if not config.is_file():
        return {"status": "Unbound", "errors": "missing config", "sha256": ""}
    parsed = yaml.safe_load(config.read_text())
    normalized = strip_identity(parsed)
    semantic_match = normalized == reference_normalized
    mismatches = []
    for key, expected in expected_flags.items():
        values = nested_find(parsed, key)
        actual = values[0] if len(values) == 1 else values
        if actual != expected:
            mismatches.append(f"{key}={actual!r}, expected {expected!r}")
    config_precedes = config.stat().st_mtime_ns <= evidence_mtime_ns
    if accepted_prior:
        status = (
            "AcceptedWithUserReportedRunConfig"
            if mismatches or not semantic_match or not config_precedes
            else "AcceptedWithUserReportedUncertainty"
        )
    elif mismatches or not semantic_match:
        status = "Conflict"
    elif config_precedes:
        status = "MetadataLinked"
    else:
        status = "Unbound"
    return {
        "status": status,
        "errors": "; ".join(mismatches),
        "sha256": sha256(config),
        "config_precedes_evidence": config_precedes,
        "semantic_match_to_4.1": semantic_match,
    }


def artifact_time_ns(path: Path) -> int:
    match = re.search(r"-(\d{8})-(\d{6})\.csv$", path.name)
    if not match:
        return path.stat().st_mtime_ns
    value = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    return int(value.timestamp() * 1.0e9)


def input_metadata(config_path: Path) -> list[dict[str, Any]]:
    parsed = yaml.safe_load(config_path.read_text())
    paths = []
    for path in nested_find(parsed, "path"):
        if not isinstance(path, str) or not path.startswith("/home/czh/Projects/gici-data/"):
            continue
        if any(token in path for token in ("output", "log", "5.2")):
            continue
        p = Path(path)
        row = {"path": path, "exists": p.is_file()}
        if p.is_file():
            stat = p.stat()
            row.update({"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
            tag = Path(path + ".tag")
            row["tag_exists"] = tag.is_file()
            row["tag_sha256"] = sha256(tag) if tag.is_file() else ""
        paths.append(row)
    return paths


def run_audit(sequence: str, run: str, directory: Path, config: Path,
              reference_normalized: Any, expected_flags: dict[str, Any],
              accepted_prior: bool) -> dict[str, Any]:
    files = {
        "source": only_file(directory, SOURCE_PREFIX),
        "doppler": only_file(directory, DOPPLER_PREFIX),
        "preopt": only_file(directory, PREOPT_PREFIX),
    }
    source = parse_source(files["source"])
    doppler = parse_doppler(files["doppler"])
    preopt = parse_preopt(files["preopt"])
    fatal = [x["fatal"] for x in (source, doppler, preopt) if x.get("fatal")]
    evidence_mtime_ns = min(artifact_time_ns(path) for path in files.values())
    provenance = config_audit(config, reference_normalized, expected_flags, evidence_mtime_ns, accepted_prior)

    cross = Counter()
    if not fatal:
        for row in source["rows"]:
            ts = row["timestamp"]
            factor = preopt["by_ts"].get(ts, Counter())
            if factor.get("dd_pseudorange", 0) != row["pr_success"]:
                cross["pr_preopt"] += 1
            if factor.get("dd_phaserange", 0) != row["phase_success"]:
                cross["phase_preopt"] += 1
            if factor.get("doppler", 0) != row["doppler_success"]:
                cross["doppler_preopt"] += 1
            ds = doppler["by_ts"].get(ts)
            if ds is None:
                if row["doppler_success"] > 0:
                    cross["doppler_system_missing_epoch"] += 1
            else:
                if ds["finite"] != row["doppler_success"]:
                    cross["doppler_system_finite"] += 1
                if ds["failure"] != 0:
                    cross["doppler_system_failure"] += 1
                if len(ds["systems"]) != row["doppler_system_count"]:
                    cross["doppler_system_count"] += 1
        source_ts = {row["timestamp"] for row in source["rows"]}
        if set(preopt["by_ts"]) - source_ts:
            cross["preopt_extra_timestamp"] = len(set(preopt["by_ts"]) - source_ts)
        if set(doppler["by_ts"]) - source_ts:
            cross["doppler_extra_timestamp"] = len(set(doppler["by_ts"]) - source_ts)

    reject_reasons = []
    partial_reasons = []
    if fatal:
        reject_reasons.extend(fatal)
    for kind, parsed in (("source", source), ("doppler", doppler), ("preopt", preopt)):
        if parsed.get("width_errors", 0):
            reject_reasons.append(f"{kind}_row_width={parsed['width_errors']}")
        if parsed.get("timestamp_order") is False:
            reject_reasons.append(f"{kind}_timestamp_order")
    if source.get("closure"):
        reject_reasons.append("source_closure=" + json.dumps(source["closure"], sort_keys=True))
    if doppler.get("closure_errors", 0):
        reject_reasons.append(f"doppler_row_closure={doppler['closure_errors']}")
    if cross:
        reject_reasons.append("factor_summary_disagreement=" + json.dumps(dict(cross), sort_keys=True))
    total_failures = sum(source.get("failures", {}).values()) + sum(
        item["failure"] for item in doppler.get("by_ts", {}).values()
    )
    if total_failures:
        partial_reasons.append(f"evaluation_failures={total_failures}")
    unexpected = sum(source.get("unexpected_nonfinite", {}).values()) + doppler.get(
        "unexpected_nonfinite", 0
    ) + sum(preopt.get("nonfinite", {}).values())
    if unexpected:
        partial_reasons.append(f"unexpected_nonfinite={unexpected}")
    if source.get("phase_available", 0) == 0:
        partial_reasons.append("phase_conditioned_unavailable_all_epochs")
    if not doppler.get("systems"):
        partial_reasons.append("doppler_unavailable_all_epochs")
    if provenance["status"] in {"Conflict", "Unbound"}:
        partial_reasons.append("config_provenance_" + provenance["status"].lower())

    classification = "Reject" if reject_reasons else "Partial" if partial_reasons else "EligibleForPanel"
    return {
        "sequence": sequence,
        "run": run,
        "directory": directory,
        "files": files,
        "source": source,
        "doppler": doppler,
        "preopt": preopt,
        "provenance": provenance,
        "cross": dict(cross),
        "classification": classification,
        "reject_reasons": reject_reasons,
        "partial_reasons": partial_reasons,
        "total_failures": total_failures,
        "unexpected_nonfinite": unexpected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    cfg = yaml.safe_load(args.manifest.read_text())
    if cfg.get("manifest_id") != "S3A1b1b4b-v1" or cfg.get("calibrator_fitting") is not False:
        raise RuntimeError("expected frozen no-fit S3A1b1b4b-v1 manifest")
    manifest_text = args.manifest.read_text()
    if "5.2:" in manifest_text or "/5.2/" in manifest_text:
        raise RuntimeError("manifest contains forbidden 5.2 input")

    output = args.repo / cfg["output_root"]
    output.mkdir(parents=True, exist_ok=True)
    reference_config = Path(cfg["sequences"]["4.1"]["config"])
    reference_normalized = strip_identity(yaml.safe_load(reference_config.read_text()))
    expected_flags = cfg["expected_shadow_flags"]

    audits = []
    input_rows = []
    for sequence, sequence_cfg in cfg["sequences"].items():
        config = Path(sequence_cfg["config"])
        for item in input_metadata(config):
            input_rows.append({"sequence": sequence, **item})
        for run, directory in sequence_cfg["runs"].items():
            audits.append(run_audit(
                sequence, run, Path(directory), config, reference_normalized, expected_flags,
                bool(sequence_cfg.get("accepted_prior_user_reported_provenance", False)),
            ))

    canonical_headers: dict[str, set[str]] = defaultdict(set)
    for audit in audits:
        for kind in ("source", "doppler", "preopt"):
            canonical_headers[kind].add(audit[kind].get("header_sha256", ""))
    schema_global = {kind: len(values - {""}) == 1 for kind, values in canonical_headers.items()}

    reference_audits = [a for a in audits if a["sequence"] in cfg["reference_sequences"]]
    reference_pr_masks = set().union(*(set(a["source"]["pr_masks"]) for a in reference_audits))
    reference_doppler_masks = set().union(*(set(a["doppler"]["masks"]) for a in reference_audits))
    reference_ranges = {}
    for field in SUPPORT_FIELDS:
        values = [v for a in reference_audits for v in a["source"]["supports"][field] if math.isfinite(v)]
        reference_ranges[field] = (min(values), max(values)) if values else (math.nan, math.nan)

    run_rows = []
    support_rows = []
    support_domain_rows = []
    mask_rows = []
    system_rows = []
    hash_rows = []
    provenance_rows = []
    for audit in audits:
        source = audit["source"]
        doppler = audit["doppler"]
        preopt = audit["preopt"]
        unseen_pr = sum(count for mask, count in source["pr_masks"].items() if mask not in reference_pr_masks)
        unseen_doppler = sum(count for mask, count in doppler["masks"].items() if mask not in reference_doppler_masks)
        run_rows.append({
            "sequence": audit["sequence"], "run": audit["run"],
            "classification": audit["classification"],
            "evidence_epochs": source["row_count"],
            "pr_factors": sum(row["pr_success"] for row in source["rows"]),
            "phase_factors": sum(row["phase_success"] for row in source["rows"]),
            "doppler_factors": sum(row["doppler_success"] for row in source["rows"]),
            "evaluation_failures": audit["total_failures"],
            "unexpected_nonfinite": audit["unexpected_nonfinite"],
            "gdop_invalid_sentinel_epochs": source.get("invalid_context_sentinel", {}).get("gdop", 0),
            "source_timestamp_order": source["timestamp_order"],
            "doppler_timestamp_order": doppler["timestamp_order"],
            "preopt_timestamp_order": preopt["timestamp_order"],
            "closure_failures": sum(source["closure"].values()) + doppler["closure_errors"] + sum(audit["cross"].values()),
            "phase_conditioned_available_epochs": source["phase_available"],
            "phase_conditioned_available_rate": source["phase_available"] / source["row_count"] if source["row_count"] else math.nan,
            "phase_continued_ratio_overall": source["phase_category_totals"].get("continued", 0) / max(1, source["phase_category_totals"].get("total", 0)),
            "phase_new_ratio_overall": source["phase_category_totals"].get("new", 0) / max(1, source["phase_category_totals"].get("total", 0)),
            "phase_mixed_ratio_overall": source["phase_category_totals"].get("mixed", 0) / max(1, source["phase_category_totals"].get("total", 0)),
            "phase_slip_ratio_overall": source["phase_category_totals"].get("slip", 0) / max(1, source["phase_category_totals"].get("total", 0)),
            "phase_unknown_count": source["phase_category_totals"].get("unknown", 0),
            "pr_complete_coordinate_rate": source["pr_masks"].get("111", 0) / source["row_count"] if source["row_count"] else math.nan,
            "pr_unseen_mask_epochs": unseen_pr,
            "doppler_unseen_mask_epochs": unseen_doppler,
            "doppler_cegr_mask_rate": doppler["masks"].get("CEGR", 0) / sum(doppler["masks"].values()) if doppler["masks"] else math.nan,
            "satellite_support_min": quantiles(source["supports"]["unique_used_satellite_count"])["min"],
            "satellite_support_median": quantiles(source["supports"]["unique_used_satellite_count"])["median"],
            "satellite_support_max": quantiles(source["supports"]["unique_used_satellite_count"])["max"],
            "gdop_valid_rate": statistics.fmean(source["context"]["gdop_valid"]) if source["context"]["gdop_valid"] else math.nan,
            "gdop_valid_median": quantiles(source["context"]["gdop"])["median"],
            "gdop_valid_max": quantiles(source["context"]["gdop"])["max"],
            "elevation_valid_rate": statistics.fmean(source["context"]["elevation_valid"]) if source["context"]["elevation_valid"] else math.nan,
            "elevation_p10_median_deg": quantiles(source["context"]["elevation_p10_deg"])["median"],
            "systems_pr": "".join(sorted(preopt["systems"].get("dd_pseudorange", set()))),
            "systems_phase": "".join(sorted(preopt["systems"].get("dd_phaserange", set()))),
            "systems_doppler": "".join(sorted(preopt["systems"].get("doppler", set()))),
            "provenance_status": audit["provenance"]["status"],
            "reject_reasons": "; ".join(audit["reject_reasons"]),
            "partial_reasons": "; ".join(audit["partial_reasons"]),
        })
        for field, values in source["supports"].items():
            stats = quantiles(values)
            lo, hi = reference_ranges[field]
            outside = sum(1 for value in values if math.isfinite(value) and not (lo <= value <= hi))
            support_rows.append({
                "sequence": audit["sequence"], "run": audit["run"], "field": field,
                **stats, "reference_4.1_4.2_min": lo, "reference_4.1_4.2_max": hi,
                "outside_reference_count": outside,
                "outside_reference_rate": outside / len(values) if values else math.nan,
            })
            support_domain_rows.append({
                "sequence": audit["sequence"], "run": audit["run"], "field": field,
                "outside_reference_count": outside,
                "outside_reference_rate": outside / len(values) if values else math.nan,
                "reference_4.1_4.2_min": lo, "reference_4.1_4.2_max": hi,
                "observed_min": stats["min"], "observed_max": stats["max"],
            })
        for field, values in source["context"].items():
            support_rows.append({
                "sequence": audit["sequence"], "run": audit["run"], "field": field,
                **quantiles(values), "reference_4.1_4.2_min": "", "reference_4.1_4.2_max": "",
                "outside_reference_count": "", "outside_reference_rate": "",
            })
        for kind, counts, reference in (
            ("pr_valid_mask", source["pr_masks"], reference_pr_masks),
            ("doppler_system_mask", doppler["masks"], reference_doppler_masks),
        ):
            for mask, count in sorted(counts.items()):
                mask_rows.append({
                    "sequence": audit["sequence"], "run": audit["run"], "kind": kind,
                    "mask": mask, "count": count,
                    "rate": count / sum(counts.values()), "seen_in_4.1_4.2": mask in reference,
                })
        for channel, values in preopt["systems"].items():
            for system in sorted(values):
                system_rows.append({
                    "sequence": audit["sequence"], "run": audit["run"],
                    "channel": channel, "system": system,
                })
        for kind in ("source", "doppler", "preopt"):
            hash_rows.append({
                "sequence": audit["sequence"], "run": audit["run"], "kind": kind,
                "path": str(audit["files"][kind]), "bytes": audit["files"][kind].stat().st_size,
                "sha256": audit[kind]["sha256"], "header_sha256": audit[kind]["header_sha256"],
            })
        provenance_rows.append({
            "sequence": audit["sequence"], "run": audit["run"],
            **audit["provenance"],
            "binary_binding": "unverified",
            "candidate_binary": cfg["candidate_binary"]["path"],
        })

    sequence_rows = []
    order = {"EligibleForPanel": 0, "Partial": 1, "Reject": 2}
    for sequence in cfg["sequences"]:
        selected = [row for row in run_rows if row["sequence"] == sequence]
        classification = max((row["classification"] for row in selected), key=order.get)
        sequence_rows.append({
            "sequence": sequence,
            "classification": classification,
            "run_count": len(selected),
            "evidence_epochs_per_run": ";".join(str(row["evidence_epochs"]) for row in selected),
            "representative_physical_epoch_count": statistics.median(row["evidence_epochs"] for row in selected),
            "pr_factors_per_run": ";".join(str(row["pr_factors"]) for row in selected),
            "phase_factors_per_run": ";".join(str(row["phase_factors"]) for row in selected),
            "doppler_factors_per_run": ";".join(str(row["doppler_factors"]) for row in selected),
            "evaluation_failures_max_per_run": max(row["evaluation_failures"] for row in selected),
            "closure_failures_max_per_run": max(row["closure_failures"] for row in selected),
            "notes": " | ".join(filter(None, (
                "; ".join(filter(None, (row["reject_reasons"], row["partial_reasons"])))
                for row in selected
            ))),
        })

    candidate = Path(cfg["candidate_binary"]["path"])
    environment = {
        "manifest_sha256": sha256(args.manifest),
        "source_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=args.repo, text=True).strip(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repo, text=True).strip(),
        "candidate_binary_path": str(candidate),
        "candidate_binary_sha256": sha256(candidate) if candidate.is_file() else "",
        "candidate_binary_actual_run_binding": "unverified",
        "dataset_5.2_read": False,
        "gt_ape_ar_fix_solution_read": False,
        "calibrator_fitting": False,
    }
    overall = "PASS" if all(row["classification"] == "EligibleForPanel" for row in sequence_rows) else (
        "FAIL" if any(row["classification"] == "Reject" for row in sequence_rows) else "PARTIAL"
    )
    decision = {
        "stage": cfg["stage"],
        "overall": overall,
        "schema_identical_across_runs": schema_global,
        "sequences": sequence_rows,
        "reference_pr_masks": sorted(reference_pr_masks),
        "reference_doppler_system_masks": sorted(reference_doppler_masks),
        "provenance_limit": "CSV/config/input metadata are hashed or fingerprinted, but no run artifact binds the actual executable hash; current config is not automatically the run config.",
        "support_domain_scope": "prototype support-domain only, not complete CalibrationApplicability",
        "calibrator_fitting": False,
        "dataset_5.2_read": False,
    }

    write_csv(output / "run_sanity.csv", run_rows)
    write_csv(output / "sequence_decision.csv", sequence_rows)
    write_csv(output / "support_summary.csv", support_rows)
    write_csv(output / "support_domain_summary.csv", support_domain_rows)
    write_csv(output / "mask_patterns.csv", mask_rows)
    write_csv(output / "system_participation.csv", system_rows)
    write_csv(output / "evidence_hashes.csv", hash_rows)
    write_csv(output / "provenance.csv", provenance_rows)
    write_csv(output / "raw_input_metadata_fingerprints.csv", input_rows)
    write_json(output / "environment.json", environment)
    write_json(output / "decision.json", decision)

    lines = [
        "# Stage 3A.1b-1b.4b Development Panel Evidence Sanity Audit", "",
        f"- Overall: **{overall}**", "- Calibrator fitting: **not performed**",
        "- 5.2 / GT / APE / AR-FIX / solution inputs read: **no**", "",
        "## Sequence decisions", "",
        "| Sequence | Decision | Runs | Epochs per run | PR per run | Phase per run | Doppler per run | Max failures/run | Max closure/run | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in sequence_rows:
        lines.append(
            f"| {row['sequence']} | {row['classification']} | {row['run_count']} | "
            f"{row['evidence_epochs_per_run']} | {row['pr_factors_per_run']} | {row['phase_factors_per_run']} | "
            f"{row['doppler_factors_per_run']} | {row['evaluation_failures_max_per_run']} | "
            f"{row['closure_failures_max_per_run']} | {row['notes']} |"
        )
    lines.extend([
        "", "## Run-level availability and shared context", "",
        "| Sequence/run | PR complete mask | Phase conditioned | Doppler CEGR mask | Satellites min/median/max | GDOP valid rate/median/max | Elevation valid rate/P10 median |",
        "|---|---:|---:|---:|---|---|---|",
    ])
    for row in run_rows:
        lines.append(
            f"| {row['sequence']}/{row['run']} | {row['pr_complete_coordinate_rate']:.4f} | "
            f"{row['phase_conditioned_available_rate']:.4f} | {row['doppler_cegr_mask_rate']:.4f} | "
            f"{row['satellite_support_min']:.0f}/{row['satellite_support_median']:.0f}/{row['satellite_support_max']:.0f} | "
            f"{row['gdop_valid_rate']:.4f}/{row['gdop_valid_median']}/{row['gdop_valid_max']} | "
            f"{row['elevation_valid_rate']:.4f}/{row['elevation_p10_median_deg']} |"
        )
    unseen = [row for row in mask_rows if not row["seen_in_4.1_4.2"]]
    lines.extend(["", "## Unseen valid patterns relative to 4.1/4.2", ""])
    if unseen:
        lines.extend([
            "| Sequence/run | Kind | Mask | Count | Rate |",
            "|---|---|---|---:|---:|",
        ])
        for row in unseen:
            lines.append(
                f"| {row['sequence']}/{row['run']} | {row['kind']} | {row['mask']} | "
                f"{row['count']} | {row['rate']:.6f} |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Phase provenance composition", ""])
    lines.extend([
        "| Sequence/run | Continued | New | Mixed | Slip | Unknown count |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in run_rows:
        lines.append(
            f"| {row['sequence']}/{row['run']} | {row['phase_continued_ratio_overall']:.6f} | "
            f"{row['phase_new_ratio_overall']:.6f} | {row['phase_mixed_ratio_overall']:.6f} | "
            f"{row['phase_slip_ratio_overall']:.6f} | {row['phase_unknown_count']} |"
        )
    outside_rows = [row for row in support_domain_rows if row["outside_reference_count"]]
    lines.extend(["", "## Support outside the 4.1/4.2 prototype range", ""])
    if outside_rows:
        lines.extend([
            "| Sequence/run | Support field | Outside count | Rate | Observed min/max | Reference min/max |",
            "|---|---|---:|---:|---|---|",
        ])
        for row in outside_rows:
            lines.append(
                f"| {row['sequence']}/{row['run']} | {row['field']} | "
                f"{row['outside_reference_count']} | {row['outside_reference_rate']:.6f} | "
                f"{row['observed_min']}/{row['observed_max']} | "
                f"{row['reference_4.1_4.2_min']}/{row['reference_4.1_4.2_max']} |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## 4.1/4.2 prototype support ranges", ""])
    for field, (lo, hi) in reference_ranges.items():
        lines.append(f"- `{field}`: {lo} -- {hi}")
    lines.extend([
        "", "## Provenance boundary", "",
        "The evidence CSVs and current configs are hashed, and raw inputs have metadata/tag fingerprints. "
        "No run artifact binds an executable hash to an evidence directory, so binary provenance remains unverified. "
        "A current config that postdates an output is not treated as proof of the run config.", "",
        "Support-range and unseen-mask results are prototype support-domain descriptors only. "
        "They neither measure complete CalibrationApplicability nor trigger quality rejection.", "",
    ])
    (output / "report.md").write_text("\n".join(lines))
    return 0 if overall != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
