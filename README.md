# Reproduce the results in simulation and real data analysis

Unzip the repository and open a terminal in the folder containing `reproduce.py`.
Use 64-bit Python 3.12 (the simulation server used 3.12.7), with CPU execution.

## 1. Install

Windows, in Command Prompt:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
```

Linux or Apple Silicon macOS 14 or later:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

Then run in that environment:

```sh
python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
python reproduce.py check
```

The same commands below work on these platforms without editing paths.
A Linux container is also provided; see [SOFTWARE.md](SOFTWARE.md).

## 2. Tables 2–4: run the simulations from the beginning

```sh
python reproduce.py table2 --workers 4
python reproduce.py table3 --workers 4
python reproduce.py table4 --workers 4
```

Each command generates the data, constructs spatial partitions, tunes and fits
the seven methods, predicts held-out observations and aggregates 200 repetitions.
Open `results/table2.csv`, `results/table3.csv` and `results/table4.csv`,
respectively. Formatted Markdown and LaTeX tables are saved beside them.
Each contains both sample sizes and all three error distributions. Parentheses
give sample SDs across repetitions.

## 3. Table 5: fit the annual data from the beginning

```sh
python reproduce.py prepare
python reproduce.py table5 --workers 4
```

The first command restores the compressed curves and aligns yield, precipitation
and county identifiers. The second fits each year separately using ten outer
folds and inner spatial validation, then evaluates every held-out county.
Open `results/table5.csv`; annual values are in `results/annual_metrics.csv`.
Table 5 averages the 20 annual RMSE and MAE values on the log-yield scale and
reports their sample SDs. Input definitions are in [DATA.md](DATA.md).

## 4. Figures 2–3

After `prepare`, generate Figure 2:

```sh
python reproduce.py figure2
```

Open `results/figure2.pdf`. After Table 5 has finished, generate Figure 3:

```sh
python reproduce.py figure3
```

Open `results/figure3.pdf`. Its numeric source is `results/county_mae.csv`.
The script takes absolute held-out log-yield errors before averaging within
counties. It draws the six panels from county boundaries, not stored images.

## 5. Rebuild all tables and maps from the completed runs

To use the supplied server records and annual predictions without refitting:

```sh
python reproduce.py reported
```

Open `results/reported/table2.csv`–`table5.csv`, `figure2.pdf` and `figure3.pdf`.
The simulation tables are recalculated from 25,200 per-replication metric rows;
Table 5 and Figure 3 are recalculated from 6,152 county-year held-out predictions.
This is a separate reconstruction route, not a new model fit.
`results/reported/reproduction_comparison.csv` lists differences from the
reported reference values. Missing or differing values are reported, not replaced.

Reported targets can be viewed immediately in [reference/](reference/).
The server identifier `SGNNWR` is displayed as `SANNWR`; its fitting code and
random-seed assignment are unchanged.

The analyses were executed by scripts, not through software dialogs. In place
of interface screenshots, the actual server run is documented by:

- [manifest.json](data/simulation/manifest.json): recorded configuration, software versions, source hashes and completion status. Its coverage records 25,200 completed method runs and no incomplete settings.
- [selected_hyperparameters.csv](data/simulation/selected_hyperparameters.csv): method-specific tuning choices for each run, including epochs and validation scores where recorded. The `selected` column contains JSON.
- [coverage.csv](data/simulation/coverage.csv): the completed and expected repetition counts for every setting–method combination.
- [metrics_per_replication.csv.gz](data/simulation/metrics_per_replication.csv.gz): individual RMSE, MAE and elapsed seconds used to construct Tables 2–4.

These machine-readable files retain the complete recorded configuration and
per-run selections in a searchable form. Match selections to metric records
using `m`, `scenario`, `error`, `method` and `run_id`. The commands above rerun the shared code with the recorded
fitting settings.

## 6. Other reported metrics

After step 5, use:

- Annual sample sizes: `generated/data/annual_sample_sizes.csv` (`n`).
- Observed years per county: `generated/data/county_coverage.csv` (`n_years`).
- Annual and county errors: `results/reported/annual_metrics.csv` and `county_mae.csv`.
- Equal-county means (including 0.127 and 0.125): `results/reported/equal_county_mae.csv`.
- State-average errors: `results/reported/state_mae.csv`.
- Mean computation times and SDs: `results/reported/simulation_timing.csv`.

Use `python reproduce.py parameters` to print the fixed settings and versions.
Completed fits are reused when the same fitting command is repeated.
Use `--workers 1` on a small machine or up to `--workers 100` for Tables 2–4
on a suitable server. Table 1 and Figure 1 are descriptive, not numerical analyses.

Upload the extracted contents to GitHub, not this ZIP file. The temperature
data are split into eleven files smaller than 4 MB; `prepare` joins them.

## 7. Code and data locations

### Simulation code

- [simulation/data.py](simulation/data.py): data generation, basis calculations and spatial partitions.
- [simulation/representation.py](simulation/representation.py) and [train_representation.py](simulation/train_representation.py): GWFRN/SGWFRN architecture, joint fitting, staged validation and prediction.
- [simulation/native_linear.py](simulation/native_linear.py), [legacy_gwr.py](simulation/legacy_gwr.py) and [native_neural.py](simulation/native_neural.py): benchmark fitting; supporting neural routines are in [neural_methods.py](simulation/neural_methods.py).
- [simulation/run_simulation.py](simulation/run_simulation.py): independent repetitions and saved predictions. Settings are in [config.json](simulation/config.json).

### Real-data code

- [realdata/real_data.py](realdata/real_data.py): county-year alignment and annual input preparation; [data.py](realdata/data.py) provides the functional basis calculations.
- [realdata/neural_methods.py](realdata/neural_methods.py) and [local_methods.py](realdata/local_methods.py): the proposed networks and neural benchmarks, and the local regression benchmarks, respectively.
- [realdata/run_annual_log.py](realdata/run_annual_log.py): annual ten-fold fitting and held-out predictions. Recorded settings are in [config/empirical_protocol.json](config/empirical_protocol.json).
- [figures/](figures/) draws Figures 2–3; [tools/](tools/) restores inputs, builds tables and compares results.

### Data and supplied results

| Folder | Contents |
|---|---|
| [data/input/](data/input/) | Yield and precipitation records, county identifiers and locations, and compressed daily temperature curves. |
| [data/geography/](data/geography/) | County boundary files for the maps. |
| [data/predictions/](data/predictions/) | Saved annual held-out predictions used to rebuild Table 5 and Figure 3. |
| [data/simulation/](data/simulation/) | Server metrics, selected hyperparameters, coverage and run manifest for Tables 2–4. |
| [reference/](reference/) | Reported table values and PDFs of Figures 2–3 for comparison. |

New computations write to `generated/` and `results/`; these folders are created
by the commands above. Variable definitions and data sources are in [DATA.md](DATA.md),
and software sources and licences are in [SOFTWARE.md](SOFTWARE.md).
