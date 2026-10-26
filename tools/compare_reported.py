"""Compare newly computed tables with the reported reference values.

Run all tables with no arguments, or use --table 2 (3, 4 or 5).
This command reads results; it never copies reference values into results.
"""
from pathlib import Path
import argparse
import csv
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
METRICS = ("rmse_mean", "rmse_sd", "mae_mean", "mae_sd")
SIMULATION_KEYS = ("table", "n", "scenario", "error", "method")
ANNUAL_KEYS = ("method", "n_years")
OUTPUT_FIELDS = ("table", "n", "scenario", "error", "method", "n_years",
                 "metric", "reported", "recomputed", "difference",
                 "absolute_difference", "tolerance", "status")


def read_table(path, table):
    """Reject incomplete schemas and duplicate keys before comparing values."""
    keys = ANNUAL_KEYS if table == 5 else SIMULATION_KEYS
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = set(keys + METRICS)
        if not required.issubset(reader.fieldnames or ()):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise ValueError(f"{path}: missing columns {missing}")
        rows = {}
        for line, row in enumerate(reader, start=2):
            key = tuple(row[name] for name in keys)
            if any(not value for value in key) or key in rows:
                raise ValueError(f"{path}:{line}: missing or duplicate key {key}")
            if table != 5 and row["table"] != str(table):
                raise ValueError(f"{path}:{line}: wrong table number")
            for metric in METRICS:
                value = float(row[metric])
                if not math.isfinite(value):
                    raise ValueError(f"{path}:{line}: nonfinite {metric}")
            rows[key] = row
    if not rows:
        raise ValueError(f"{path}: empty table")
    return rows


def compare(table, results_dir, reference_dir):
    computed_path = results_dir / f"table{table}.csv"
    reported_path = reference_dir / f"table{table}.csv"
    for path in (computed_path, reported_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing file: {path}")
    computed = read_table(computed_path, table)
    reported = read_table(reported_path, table)
    if computed.keys() != reported.keys():
        missing = sorted(reported.keys() - computed.keys())
        extra = sorted(computed.keys() - reported.keys())
        raise ValueError(f"Table {table}: mismatched keys; missing={missing}; extra={extra}")

    # Simulation references contain four-decimal published values: allow only
    # half a rounding unit plus 1e-12 for floating-point subtraction. The annual
    # references retain full precision and use a fixed absolute 1e-10 allowance.
    tolerance = 1e-10 if table == 5 else 0.5e-4 + 1e-12
    output = []
    for key, reference in reported.items():
        actual = computed[key]
        for metric in METRICS:
            expected = float(reference[metric])
            observed = float(actual[metric])
            difference = observed - expected
            row = {name: reference.get(name, "") for name in OUTPUT_FIELDS[:6]}
            row.update(table=table, metric=metric, reported=reference[metric],
                       recomputed=actual[metric], difference=difference,
                       absolute_difference=abs(difference), tolerance=tolerance,
                       status="PASS" if abs(difference) <= tolerance else "DIFFERENT")
            output.append(row)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=int, choices=(2, 3, 4, 5),
                        help="Compare one table; the default compares Tables 2--5.")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--reference-dir", type=Path, default=ROOT / "reference")
    parser.add_argument("--output", type=Path, default=ROOT / "results/reproduction_comparison.csv")
    args = parser.parse_args()
    tables = (args.table,) if args.table is not None else (2, 3, 4, 5)
    try:
        rows = []
        for table in tables:
            rows.extend(compare(table, args.results_dir.resolve(), args.reference_dir.resolve()))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Comparison stopped: {exc}\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    different = sum(row["status"] == "DIFFERENT" for row in rows)
    print(f"Compared {len(rows)} mean/SD values: {len(rows)-different} PASS, {different} DIFFERENT.")
    print(f"Saved {args.output}")
    if different:
        sys.exit(1)


if __name__ == "__main__":
    main()
