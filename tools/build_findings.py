"""Build tables and map values from complete held-out prediction records.

Calculate RMSE/MAE within each repetition or year, then average those metrics.
"""
from pathlib import Path
import argparse
import csv
import gzip
import json
import math
import statistics as stats
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SIMULATION = ROOT / "generated/simulation"
REALDATA = ROOT / "generated/realdata"
METHODS = ("GWR", "SGWR", "GNNWR", "SANNWR", "FNN", "GWFRN", "SGWFRN")
YEARS = range(1999, 2019)
ERRORS = ("normal", "student_t", "bimodal")
SCENARIOS = ("linear", "nonlinear_kappa0", "nonlinear_kappa1")
TABLES = (2, 3, 4)


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def metrics(errors):
    return math.sqrt(stats.fmean(e*e for e in errors)), stats.fmean(abs(e) for e in errors)


def close(left, right, label):
    if not math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-10):
        raise AssertionError(f"{label}: saved and recomputed quantities disagree.")


def mark(mean, sd, ordered, latex=False):
    # Mark only the mean, never its SD. Ranking uses unrounded values.
    unique = sorted(set(ordered))
    text = f"{mean:.4f}"
    if mean == unique[0]:
        text = (r"\textbf{" + text + "}") if latex else f"**{text}**"
    elif len(unique) > 1 and mean == unique[1]:
        text = (r"\underline{" + text + "}") if latex else f"<u>{text}</u>"
    return text + f" ({sd:.4f})"


def display_method(name):
    """Use the manuscript abbreviation without changing the fitted method."""
    return "SANNWR" if name == "SGNNWR" else name


def export_simulation_tables(rows, destination, tables=(2, 3, 4)):
    """Write the same table layout for new fits and saved per-run metrics."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows = [dict(row, method=display_method(row["method"])) for row in rows]
    for number in tables:
        scenario = SCENARIOS[number-2]
        selected = [row for row in rows if row["scenario"] == scenario]
        found = {(int(row["m"]), row["error"], row["method"]): row for row in selected}
        expected = {(m, error, method) for m in (30, 40) for error in ERRORS for method in METHODS}
        if len(found) != len(selected) or set(found) != expected:
            raise AssertionError(f"Table {number} has incomplete or duplicate summary cells.")
        numeric, md, tex = [], [], []
        header = " | ".join(f"{e} {metric.upper()}" for e in ERRORS for metric in ("rmse", "mae"))
        md += [f"# Table {number}", "", "| n | Method | " + header + " |", "|---:|---|" + "---:|"*6]
        tex += [r"\begin{tabular}{rlrrrrrr}", r"\toprule", "n & Method & " + header.replace(" | ", " & ") + r" \\", r"\midrule"]
        for m in (30, 40):
            for method in METHODS:
                cells, tcells = [], []
                for error in ERRORS:
                    row = found[m, error, method]
                    numeric.append(dict(table=number, n=m*m, scenario=scenario, error=error, method=method,
                                        **{k: row[k] for k in ("rmse_mean", "rmse_sd", "mae_mean", "mae_sd")}))
                    for metric in ("rmse", "mae"):
                        values = [float(found[m, error, method2][metric+"_mean"]) for method2 in METHODS]
                        a, b = float(row[metric+"_mean"]), float(row[metric+"_sd"])
                        if not math.isfinite(a) or not math.isfinite(b) or a < 0 or b < 0:
                            raise ValueError("Summary means and SDs must be finite and nonnegative.")
                        cells.append(mark(a, b, values)); tcells.append(mark(a, b, values, latex=True))
                md.append(f"| {m*m} | {method} | " + " | ".join(cells) + " |")
                tex.append(f"{m*m} & {method} & " + " & ".join(tcells) + r" \\")
            tex.append(r"\midrule")
        tex[-1:] = [r"\bottomrule", r"\end{tabular}"]
        write(destination / f"table{number}.csv", numeric)
        (destination / f"table{number}.md").write_text("\n".join(md)+"\n", encoding="utf-8")
        (destination / f"table{number}.tex").write_text("\n".join(tex)+"\n", encoding="utf-8")


def simulation():
    import numpy as np
    output = SIMULATION
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    if (config["replications"] != 200 or config["run_start"] != 1000
            or {display_method(method) for method in config["methods"]} != set(METHODS)
            or set(config["lattice_sizes"]) != {30, 40}
            or set(config["scenarios"]) != {SCENARIOS[n-2] for n in TABLES}
            or set(config["errors"]) != set(ERRORS)):
        raise AssertionError("Each requested table requires all 200 repetitions, both grids, all errors and seven methods.")
    expected = {(m, s, e, method, r) for m in (30, 40) for s in config["scenarios"]
                for e in ERRORS for method in METHODS for r in range(1000, 1200)}
    observed = set()
    for path in (output / "records").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        key = (record["m"], record["scenario"], record["error"],
               display_method(record["method"]), record["run_id"])
        if key not in expected:
            continue
        if key in observed or record.get("status") != "completed" or record["signature"] != manifest["signature"]:
            raise AssertionError(f"Duplicate, incomplete or incompatible record: {path.name}")
        prediction = (output / record["prediction_file"]).resolve()
        if not prediction.is_relative_to(output.resolve()):
            raise ValueError("Prediction path escapes its run directory.")
        with np.load(prediction, allow_pickle=False) as data:
            errors = data["yhat"] - data["y_true"]
            if len(errors) != key[0]**2 // 10 or not np.isfinite(errors).all():
                raise AssertionError("Unexpected held-out count or nonfinite prediction.")
            close(np.sqrt(np.mean(errors**2)), record["rmse"], "simulation RMSE")
            close(np.mean(np.abs(errors)), record["mae"], "simulation MAE")
        observed.add(key)
    if observed != expected:
        raise AssertionError(f"Missing {len(expected-observed)} of {len(expected)} simulation records.")
    subprocess.run([sys.executable, "-B", str(ROOT / "simulation/report.py"), str(output)], check=True)
    rows = read(output / "summary_metrics.csv")
    export_simulation_tables(rows, OUT, TABLES)
    print(f"Saved table(s) {','.join(map(str, TABLES))}: {len(observed)} prediction files checked.")


def saved_empirical_rows(path):
    """Check compact saved OOF predictions against the supplied source records."""
    import numpy as np
    columns = ("Year", "CountyI", "outer_fold", "Yield_original", "log_Yield",
               *(f"{method}_log_yhat" for method in METHODS))
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(columns):
            raise ValueError("Saved predictions have missing or unexpected columns.")
        rows = list(reader)
    sources = read(ROOT / "data/input/regdat_1.csv")
    locations = read(ROOT / "data/input/loc_info.csv")
    if len({r["CountyI"] for r in locations}) != len(locations):
        raise AssertionError("Duplicate county in the location register.")
    county_ids = {r["CountyI"] for r in locations}
    expected = {}
    for row in sources:
        year = int(row["Year"])
        if year not in YEARS:
            continue
        key = year, row["CountyI"]
        if key in expected or key[1] not in county_ids:
            raise AssertionError("Duplicate or unmatched source county-year.")
        expected[key] = row
    seen, annual = set(), {year: [] for year in YEARS}
    for row in rows:
        key = int(row["Year"]), row["CountyI"]
        if key in seen or key not in expected:
            raise AssertionError("Duplicate or unmatched prediction county-year.")
        seen.add(key)
        source = expected[key]
        response = float(source["Yield"])
        if not math.isfinite(response) or response <= 0:
            raise AssertionError("Source yield must be finite and positive.")
        close(row["Yield_original"], response, "saved original yield")
        close(row["log_Yield"], math.log(response), "saved log yield")
        for method in METHODS:
            prediction = float(row[f"{method}_log_yhat"])
            if not math.isfinite(prediction):
                raise AssertionError("Nonfinite saved prediction.")
            row[f"{method}_log_error_yhat_minus_y"] = prediction - float(row["log_Yield"])
        annual[key[0]].append(row)
    if seen != set(expected) or len(seen) != 6152 or len(county_ids) != 403:
        raise AssertionError("Saved predictions must cover all 6,152 source county-years and 403 counties.")
    for year, selected in annual.items():
        selected.sort(key=lambda row: int(row["CountyI"]))
        # This is the published annual ten-fold partition, not a new split.
        labels = np.full(len(selected), -1, dtype=int)
        permutation = np.random.default_rng(year).permutation(len(selected))
        for fold, indices in enumerate(np.array_split(permutation, 10)):
            labels[indices] = fold
        if not np.array_equal([int(row["outer_fold"]) for row in selected], labels):
            raise AssertionError(f"Saved fold assignments differ from the annual protocol: {year}.")
    return annual


def empirical(saved_predictions=None):
    compact = saved_empirical_rows(saved_predictions) if saved_predictions is not None else None
    annual, all_rows, county_errors, coverage = [], [], {}, {}
    for year in YEARS:
        base = REALDATA / "by_year" / str(year)
        rows = compact[year] if compact is not None else read(base / "oof_predictions_logY.csv")
        ids = [r["CountyI"] for r in rows]
        if len(set(ids)) != len(ids) or set(int(r["outer_fold"]) for r in rows) != set(range(10)):
            raise AssertionError(f"Invalid or incomplete OOF keys/folds in {year}.")
        for r in rows:
            if int(r["Year"]) != year:
                raise AssertionError("Wrong year in prediction file.")
            close(math.log(float(r["Yield_original"])), r["log_Yield"], "log response")
            coverage.setdefault(r["CountyI"], set()).add(year)
        for method in METHODS:
            errors = []
            if compact is None:
                seen = set()
                for fold in range(10):
                    rec = json.loads((base / "records" / f"fold{fold:02d}_{method}.json").read_text(encoding="utf-8"))
                    if rec["year"] != year or rec["fold"] != fold or rec["method"] != method:
                        raise AssertionError("Wrong method/year/fold in record.")
                    for county, prediction in zip(rec["county_id"], rec["log_yhat"]):
                        if county in seen:
                            raise AssertionError("County was predicted more than once in a year.")
                        seen.add(county)
                        match = next(r for r in rows if r["CountyI"] == county)
                        if int(match["outer_fold"]) != fold:
                            raise AssertionError("Fold label differs from prediction record.")
                        close(prediction, match[f"{method}_log_yhat"], "OOF prediction")
                if seen != set(ids):
                    raise AssertionError("Every county must be tested exactly once per year.")
            for r in rows:
                error = float(r[f"{method}_log_yhat"]) - float(r["log_Yield"])
                close(error, r[f"{method}_log_error_yhat_minus_y"], "signed prediction error")
                errors.append(error)
                county_errors.setdefault((r["CountyI"], method), []).append(abs(error))
            rmse, mae = metrics(errors)
            annual.append(dict(year=year, method=method, n=len(rows), rmse=rmse, mae=mae))
        all_rows.extend(rows)
    if len(coverage) != 403 or len(all_rows) != 6152:
        raise AssertionError("Expected 403 counties and 6,152 county-years.")
    write(OUT / "annual_metrics.csv", annual)
    summary = []
    for method in METHODS:
        selected = [r for r in annual if r["method"] == method]
        summary.append(dict(method=method, n_years=20,
                            rmse_mean=stats.fmean(r["rmse"] for r in selected),
                            rmse_sd=stats.stdev(r["rmse"] for r in selected),
                            mae_mean=stats.fmean(r["mae"] for r in selected),
                            mae_sd=stats.stdev(r["mae"] for r in selected)))
    write(OUT / "table5.csv", summary)
    columns = ("GWR", "SGWR", "FNN", "GNNWR", "SANNWR", "GWFRN", "SGWFRN")
    keyed = {r["method"]: r for r in summary}
    md = ["# Table 5", "", "| Metric | " + " | ".join(columns) + " |", "|---|" + "---:|"*7]
    tex = [r"\begin{tabular}{lrrrrrrr}", r"\toprule", "Metric & " + " & ".join(columns) + r" \\", r"\midrule"]
    for metric in ("rmse", "mae"):
        means = [keyed[m][metric+"_mean"] for m in columns]
        # Table 5 marks only the best mean (unlike Tables 2--4).
        cells, tcells = [], []
        for method in columns:
            value = keyed[method]
            a, b = value[metric+"_mean"], value[metric+"_sd"]
            text = f"{a:.4f}"
            cells.append((f"**{text}**" if a == min(means) else text) + f" ({b:.4f})")
            tcells.append(((r"\textbf{"+text+"}") if a == min(means) else text) + f" ({b:.4f})")
        md.append("| " + metric.upper() + " | " + " | ".join(cells) + " |")
        tex.append(metric.upper() + " & " + " & ".join(tcells) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "table5.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    (OUT / "table5.tex").write_text("\n".join(tex)+"\n", encoding="utf-8")
    locations = {r["CountyI"]: r for r in read(ROOT / "data/input/loc_info.csv")}
    counties = []
    for county in sorted(coverage, key=int):
        loc = locations[county]
        row = dict(CountyI=county, state=loc["state"], county=loc["county"],
                   GEOID=loc["State.ANSI"].zfill(2)+loc["County.ANSI"].zfill(3),
                   n_years=len(coverage[county]))
        for method in METHODS:
            row[f"{method}_mean_absolute_error_logY"] = stats.fmean(county_errors[county, method])
        counties.append(row)
    write(OUT / "county_mae.csv", counties)
    area = [dict(method=m, equal_county_mean=stats.fmean(r[f"{m}_mean_absolute_error_logY"] for r in counties)) for m in METHODS]
    write(OUT / "equal_county_mae.csv", area)
    states = []
    for state in sorted(set(r["state"] for r in counties)):
        selected = [r for r in counties if r["state"] == state]
        for method in METHODS:
            states.append(dict(state=state, method=method, n_counties=len(selected),
                               equal_county_mae=stats.fmean(r[f"{method}_mean_absolute_error_logY"] for r in selected)))
    write(OUT / "state_mae.csv", states)
    origin = "saved OOF predictions" if compact is not None else "per-fold fit records"
    print(f"PASS Table 5 and map metrics from {origin}: 20 years, 7 methods, 6,152 county-years.")


def main():
    global OUT, REALDATA, SIMULATION, TABLES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("simulation", "realdata", "all"), default="all")
    parser.add_argument("--realdata-results", type=Path, default=REALDATA)
    parser.add_argument("--simulation-results", type=Path, default=SIMULATION)
    parser.add_argument("--table", type=int, choices=(2, 3, 4))
    parser.add_argument("--saved-predictions", type=Path,
                        help="Explicitly aggregate saved compact OOF predictions; do not fit models.")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    if args.saved_predictions is not None and args.part == "simulation":
        parser.error("--saved-predictions applies only to empirical aggregation")
    REALDATA, SIMULATION, OUT = args.realdata_results.resolve(), args.simulation_results.resolve(), args.output.resolve()
    if args.table is not None:
        TABLES = (args.table,)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.part in ("simulation", "all"):
        simulation()
    if args.part in ("realdata", "all"):
        empirical(saved_predictions=args.saved_predictions)


if __name__ == "__main__":
    main()
