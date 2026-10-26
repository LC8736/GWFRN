# Software

The pinned environment is in `requirements.txt`. All analyses run through Python
scripts; no manual GIS or graphical-interface analysis is used. Fixed proposed
settings are in `simulation/config.json` and `config/empirical_protocol.json`.
`python reproduce.py parameters` prints them and the installed versions.

The supplied simulation ran on Windows Server 2022 with Python 3.12.7 and
CPU execution. Its configuration and package versions are recorded in
`data/simulation/manifest.json`. The two server shards used 35 workers each;
the original code permits up to 100. Workers change scheduling, not seeds or
fitting budgets. `simulation/source_provenance.json` records the original
archive and the relative-output-path adaptations in this deposit.
The actual selected values are in `data/simulation/selected_hyperparameters.csv`;
these are distinct from the candidate grids in `simulation/config.json`.
The manifest, selected values, coverage and per-replication metrics are supplied
as machine-readable run documentation in place of software-interface screenshots.

- GWR: PySAL `mgwr` 2.2.1, https://github.com/pysal/mgwr. Gaussian local regression;
  five spatial folds select a positive-distance-quantile bandwidth.
- SGWR simulation: FastSGWR ALPHA selector, commit
  `965a0dadb7a9d1c18de323d62f7a41236286734a`, https://github.com/Lessani252/FastSGWR.
  Its native AICc search and kernel mixture are used with held-out WLS prediction.
  The annual analysis uses the spatial-CV mixture adapter in `realdata/local_methods.py`.
- GNNWR: https://github.com/zjuwss/gnnwr, commit
  `2711bdee9821bfe242992d2eb885a78be1cf2628`, installed distribution 0.1.17.
  Simulation uses its author model class, automatic architecture, Adagrad 0.1,
  batch 32, dropout 0.2 and weight decay 0.001. Maximum epochs 3000, patience 100.
  The annual adapter uses its SWNN architecture with Adam 0.02 and batch 50.
- FNN simulation: PyTorch port of FuncNN `fnn.fit`, commit
  `1dfe17b5f8b3d92f568709b03675114108d1bd11`, https://github.com/cran/FuncNN.
  Widths 64/64, sigmoid/linear, Adam 0.001, batch 32, at most 100 epochs,
  patience 15. Annual FNN uses ReLU 64/32, Adam 0.005, batch 50,
  at most 3000 epochs, patience 100.
- SANNWR: paper-based SAPDNN 2–3–1 and SWNN 50–20 implementation,
  https://www.mdpi.com/2220-9964/11/12/620. Adam 0.02, at most 3000 epochs,
  patience 100; simulation batch 16 and annual batch 50. A singleton final
  batch is avoided for batch normalisation.

The annual GNNWR and SANNWR SWNN layers use widths 50/20, PReLU (initial
slope 0.4), dropout 0.70 and batch normalisation. SANNWR uses the same SWNN
settings in simulation. Other defaults remain in the versioned source.

Only required upstream source excerpts are included in `simulation/upstream/`,
with their GPL-3.0/MIT notices. FNN and SANNWR ports are not author executables.
Third-party software and source data retain their respective rights; no new
licence over those materials is asserted here.

Simulation uses known target heads during joint fitting and conditional ridge
readout. The retained annual implementation uses fitting-location heads and
conditional prediction. These settings are unchanged in this deposit. Exact
prediction-level empirical retraining agreement with the reported results has
not yet been established. The separate `empirical-reported` command rebuilds
Table 5 and Figures 2–3 from the supplied retained predictions without fitting;
its outputs are kept under `results/reported/`.

For a Linux container, run `docker build -t gwfrn .` in this folder. For example,
`docker run --rm gwfrn check` checks the packaged environment. To keep generated
outputs, run `docker create --name gwfrn-run gwfrn reported`, then
`docker start -a gwfrn-run` and `docker cp gwfrn-run:/work/results ./container-results`.
Use a different container name for another run. A fixed CPU environment limits
software variation; bitwise equality across operating systems is not assumed.
