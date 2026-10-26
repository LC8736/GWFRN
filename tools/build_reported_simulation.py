"""Rebuild Tables 2--4 from the supplied 200-run server metrics."""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics as stats

import build_findings

ROOT = Path(__file__).resolve().parents[1]
RUNS = range(1000, 1200)
FIELDS = ("m", "scenario", "error", "method", "run_id", "rmse", "mae", "seconds")


def read_metrics(path):
    """Require every planned cell and reject duplicate or invalid run records."""
    expected = {(m, scenario, error, method, run) for m in (30, 40)
                for scenario in build_findings.SCENARIOS for error in build_findings.ERRORS
                for method in build_findings.METHODS for run in RUNS}
    opener = gzip.open if path.suffix == ".gz" else open
    observed, groups = set(), {}
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(FIELDS):
            raise ValueError("The server metric CSV must contain exactly the eight documented columns.")
        for line, row in enumerate(reader, start=2):
            try:
                method = build_findings.display_method(row["method"])
                key = int(row["m"]), row["scenario"], row["error"], method, int(row["run_id"])
                values = tuple(float(row[field]) for field in ("rmse", "mae", "seconds"))
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"Invalid metric record at line {line}.") from exc
            if key not in expected or key in observed:
                raise ValueError(f"Unexpected or duplicate metric record at line {line}: {key}")
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError(f"RMSE, MAE and seconds must be finite and nonnegative: line {line}.")
            observed.add(key)
            groups.setdefault(key[:4], []).append((key[4], *values))
    if observed != expected:
        raise ValueError(f"Missing {len(expected - observed)} of {len(expected)} planned server metric records.")
    return groups, len(observed)


def aggregate(groups):
    """Average within each setting/method; SD is across the 200 repetitions."""
    summary, timing, coverage = [], [], []
    for m in (30, 40):
        for scenario in build_findings.SCENARIOS:
            for error in build_findings.ERRORS:
                for method in build_findings.METHODS:
                    values = sorted(groups[m, scenario, error, method])
                    if len(values) != 200:
                        raise AssertionError("Each summary cell must contain 200 repetitions.")
                    row = dict(m=m, scenario=scenario, error=error, method=method, n=200)
                    for position, metric in ((1, "rmse"), (2, "mae")):
                        observations = [value[position] for value in values]
                        row[metric+"_mean"] = stats.fmean(observations)
                        row[metric+"_sd"] = stats.stdev(observations)
                    summary.append(row)
                    seconds = [value[3] for value in values]
                    timing.append(dict(m=m, n=m*m, scenario=scenario, error=error,
                                       method=method, n_replications=200,
                                       seconds_mean=stats.fmean(seconds), seconds_sd=stats.stdev(seconds)))
                    coverage.append(dict(m=m, scenario=scenario, error=error, method=method,
                                         n_complete=200, n_expected=200))
    return summary, timing, coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path,
                        default=ROOT / "data/simulation/metrics_per_replication.csv.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "results/reported")
    args = parser.parse_args()
    source, destination = args.metrics.resolve(), args.output.resolve()
    groups, count = read_metrics(source)
    summary, timing, coverage = aggregate(groups)
    destination.mkdir(parents=True, exist_ok=True)
    build_findings.export_simulation_tables(summary, destination)
    build_findings.write(destination / "simulation_summary.csv", summary)
    build_findings.write(destination / "simulation_timing.csv", timing)
    build_findings.write(destination / "simulation_coverage.csv", coverage)
    name = source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.name
    audit = dict(input=name, sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 metric_records=count, settings=18, methods=7, replications=200,
                 run_start=1000, run_end=1199, standard_deviation="sample SD, ddof=1",
                 operation="aggregation of saved per-replication server metrics; no model fitting",
                 display_alias={"SGNNWR": "SANNWR"})
    (destination / "simulation_aggregation.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    print("Saved Tables 2--4 and method times from 25,200 server metric records; no model fitting.")


if __name__ == "__main__":
    main()
