#!/usr/bin/env python3
"""Validate the factor-row field count of GNSS residual diagnostic CSVs."""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def check_file(path: Path) -> int:
    with path.open(newline="") as stream:
        rows = csv.reader(stream)
        try:
            header = next(rows)
        except StopIteration:
            print(f"{path}: empty file", file=sys.stderr)
            return 1

        header_count = len(header)
        try:
            measurement_type_index = header.index("measurement_type")
        except ValueError:
            print(f"{path}: missing measurement_type column", file=sys.stderr)
            return 1

        mismatches = Counter()
        total_rows = 0
        for line_number, row in enumerate(rows, start=2):
            if not row:
                continue
            total_rows += 1
            if len(row) == header_count:
                continue
            measurement_type = (
                row[measurement_type_index]
                if measurement_type_index < len(row)
                else "unknown"
            )
            mismatches[measurement_type] += 1
            print(
                f"{path}:{line_number}: {len(row)} fields; expected {header_count} "
                f"(measurement_type={measurement_type})",
                file=sys.stderr,
            )

    print(f"{path}: header_fields={header_count}, data_rows={total_rows}")
    for measurement_type in ("dd_pseudorange", "dd_phaserange", "doppler"):
        print(
            f"{path}: {measurement_type}_field_count_mismatches="
            f"{mismatches[measurement_type]}"
        )
    for measurement_type, count in sorted(mismatches.items()):
        if measurement_type not in {"dd_pseudorange", "dd_phaserange", "doppler"}:
            print(f"{path}: {measurement_type}_field_count_mismatches={count}")
    return sum(mismatches.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path, help="diagnostic CSV file")
    arguments = parser.parse_args()
    failed = False
    for path in arguments.csv:
        failed = bool(check_file(path)) or failed
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
