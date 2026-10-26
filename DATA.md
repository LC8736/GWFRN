# Input data

`simulation/data.py` generates the simulated curves, scalar predictors,
locations, responses and spatial partitions. No external simulation dataset
is required. The configuration is fixed in `simulation/config.json`.

`data/simulation/metrics_per_replication.csv.gz` contains 25,200 supplied
server records: 18 settings, seven methods and 200 repetitions (1000–1199).
Each record has RMSE, MAE and elapsed seconds. The same folder contains the
server's coverage and summary CSVs, `selected_hyperparameters.csv`, and its run
manifest. The selected-parameter file has one row per setting, method and
repetition; its `selected` column stores the method-specific choices as JSON.
Machine-specific paths were removed from the manifest.
Individual simulation predictions and fitted models were not included in the
supplied aggregate output. The `simulation-reported` command averages the
per-replication scores; full fitting commands generate predictions afresh.

The server identifier `SGNNWR` is displayed as `SANNWR` in manuscript tables.
This changes the label only, not the fitted method or its random seeds.

`data/input/regdat_1.csv` contains county-year identifiers, Yield and avgPRCP.
Yield is analysed as its natural logarithm; avgPRCP is the only scalar predictor.
Area is not used. `loc_info.csv` supplies county locations and ANSI identifiers.

The eleven gzip parts restore `fundat.csv`: 6,340 rows and 730 columns. Its
rows correspond to `regdat_1.csv` before filtering or sorting. Columns 1–365
are supplied centred maximum-temperature curves; columns 366–730 are centred
minimum-temperature curves. They are source-study inputs, not raw station
records. `prepare` checks the source hashes and keeps 1999–2018, giving 6,152
observed county-years in 403 counties. Fitting-sample scaling is applied inside
each model. The original station-download/centring code was not supplied.

The supplied `avgPRCP` column is mean daily precipitation in mm/day. It is read
directly from `regdat_1.csv`; the scripts do not download or reconstruct station
records. Input checks include its checksum, finite values and county-year keys.
County boundaries are the Census 2018 `cb_2018_us_county_5m` files in `data/geography/`.

County sample: Park, Li and Li, https://doi.org/10.1093/jrsssc/qlag023.
Agency sources: https://quickstats.nass.usda.gov/ and
https://www.ncei.noaa.gov/cdo-web/.
Boundaries: https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_5m.zip.
Permission to redistribute the supplied assembled data was confirmed.

`data/predictions/annual_oof_logY.csv.gz` contains the retained held-out
predictions used for Table 5 and Figure 3: one row per observed county-year,
with its fold, observed yield and predictions from the seven methods. These
are saved model outputs, not raw predictors. The `empirical-reported` command
validates them against the input data and rebuilds the reported summaries;
the separate `table5` command refits the models from the input data.
