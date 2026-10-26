"""Run one numbered table or figure from the shared inputs."""
from pathlib import Path
import argparse
import csv
import importlib.metadata
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TABLE_SCENARIO = {2: "linear", 3: "nonlinear_kappa0", 4: "nonlinear_kappa1"}


def run(*arguments):
    print("python " + " ".join(map(str, arguments)), flush=True)
    subprocess.run([sys.executable, "-B", *map(str, arguments)], cwd=ROOT, check=True)


def prepare():
    # Restore the byte-identical curves, check the county/year input keys,
    # then align and project each year's data. No fitted results are read.
    run("tools/prepare_data.py")
    run("realdata/run_annual_log.py", "--prepare-only")


def simulation_table(number, workers, summarise_only=False):
    config = json.loads((ROOT / "simulation/config.json").read_text(encoding="utf-8-sig"))
    # Select only the response setting for this table. Seeds, grids, candidates,
    # optimisation budgets and estimators are unchanged from the full study.
    config["scenarios"] = [TABLE_SCENARIO[number]]
    config["workers"] = workers
    config_path = ROOT / f"generated/config/table{number}.json"
    output = f"generated/simulation/table{number}"
    if not summarise_only:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(config, indent=2) + "\n"
        if not config_path.exists() or config_path.read_text(encoding="utf-8") != text:
            config_path.write_text(text, encoding="utf-8")
        run("simulation/run_simulation.py", "--config", config_path.relative_to(ROOT),
            "--output", output, "--workers", workers, "--runs", 200, "--run-start", 1000)
    run("tools/build_findings.py", "--part", "simulation", "--table", number,
        "--simulation-results", output)


def empirical_table(workers, summarise_only=False):
    if not summarise_only:
        prepare()
        run("realdata/run_annual_log.py", "--workers", workers)
    run("realdata/verify_results.py", "--require-all")
    run("tools/build_findings.py", "--part", "realdata")


def reported_empirical():
    # Rebuild published summaries from explicitly supplied held-out predictions.
    # This route never trains a model or replaces a fresh fitting result.
    destination = "results/reported"
    run("tools/prepare_data.py")
    run("tools/build_reported_empirical.py")
    run("figures/plot_mean_absolute_errors.py", "--findings-dir", destination,
        "--figure-dir", destination)
    run("tools/compare_reported.py", "--table", 5, "--results-dir", destination,
        "--output", destination + "/reproduction_comparison.csv")


def reported_simulation():
    # Use the supplied server per-replication scores, not rounded table cells.
    run("tools/build_reported_simulation.py")


def reported_all():
    reported_simulation()
    reported_empirical()
    run("tools/compare_reported.py", "--results-dir", "results/reported",
        "--output", "results/reported/reproduction_comparison.csv")


def figure(number):
    if number == 2:
        run("tools/prepare_data.py")
        run("figures/plot_mean_absolute_errors.py", "--coverage-only")
    else:
        if not (ROOT / "results/table5.csv").is_file():
            raise FileNotFoundError("Run 'python reproduce.py table5' before figure3.")
        # Reconstruct from the newly fitted annual predictions, not from an
        # uploaded summary or a rendered image.
        run("tools/build_findings.py", "--part", "realdata")
        run("figures/plot_mean_absolute_errors.py", "--errors-only")


def show_metrics():
    empirical_table(workers=1, summarise_only=True)
    for name in ("table5.csv", "equal_county_mae.csv", "state_mae.csv"):
        print("\nresults/" + name)
        with (ROOT / "results" / name).open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                print(", ".join(f"{key}={value}" for key, value in row.items()))


def parameters(scope="all"):
    for name in ("simulation/config.json", "config/empirical_protocol.json"):
        if scope == "software" or (scope == "simulation" and name.startswith("config/")) or (scope == "annual" and name.startswith("simulation/")):
            continue
        print(name)
        values = json.loads((ROOT / name).read_text(encoding="utf-8-sig"))
        for key, value in values.items():
            if key != "role":
                print(f"{key}: {json.dumps(value)}")
    if scope in ("annual", "simulation"):
        return
    print("Software:", sys.version.split()[0])
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            name = line.split("==")[0]
            print(name + "==" + importlib.metadata.version(name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item", choices=("check", "prepare", "table2", "table3", "table4", "table5",
                                         "figure2", "figure3", "simulation-reported", "empirical-reported", "reported", "metrics", "parameters", "compare", "all"))
    parser.add_argument("--scope", choices=("all", "simulation", "annual", "software"), default="all",
                        help="Parameter display only; does not change fitting settings.")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--summarise-only", action="store_true",
                        help="Rebuild a completed table from this run's saved predictions; do not refit.")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if os.name == "nt" and args.item in ("table5", "all") and args.workers > 61:
        parser.error("For table5 use at most 61 workers on Windows; 1--4 is recommended.")
    if args.summarise_only and args.item not in ("table2", "table3", "table4", "table5"):
        parser.error("--summarise-only applies to tables only")
    try:
        if args.item == "check":
            run("simulation/run_simulation.py", "--preflight")
        elif args.item == "prepare":
            prepare()
        elif args.item in ("table2", "table3", "table4"):
            simulation_table(int(args.item[-1]), args.workers, args.summarise_only)
        elif args.item == "table5":
            empirical_table(args.workers, args.summarise_only)
        elif args.item == "empirical-reported":
            reported_empirical()
        elif args.item == "simulation-reported":
            reported_simulation()
        elif args.item == "reported":
            reported_all()
        elif args.item in ("figure2", "figure3"):
            figure(int(args.item[-1]))
        elif args.item == "metrics":
            show_metrics()
        elif args.item == "parameters":
            parameters(args.scope)
        elif args.item == "compare":
            run("tools/compare_reported.py")
        else:
            prepare()
            for number in (2, 3, 4):
                simulation_table(number, args.workers)
            empirical_table(args.workers)
            figure(2)
            figure(3)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Stopped: {exc}\n")


if __name__ == "__main__":
    main()
