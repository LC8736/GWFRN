"""Recalculate the reported annual and county errors from saved OOF predictions."""
from pathlib import Path
import argparse
import hashlib
import json

import build_findings

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path,
                        default=ROOT / "data/predictions/annual_oof_logY.csv.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "results/reported")
    args = parser.parse_args()
    predictions, output = args.predictions.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    build_findings.OUT = output
    build_findings.empirical(saved_predictions=predictions)
    input_name = str(predictions.relative_to(ROOT)).replace("\\", "/") if predictions.is_relative_to(ROOT) else predictions.name
    audit = dict(input=input_name,
                 sha256=hashlib.sha256(predictions.read_bytes()).hexdigest(),
                 source_county_years=6152, counties=403, years=20, methods=7,
                 operation="aggregation of saved out-of-fold predictions; no model fitting")
    (output / "empirical_aggregation.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    print("Saved Table 5, annual errors, county errors and state summaries in results/reported/.")


if __name__ == "__main__":
    main()
