# Notebooks

Analysis that people run, never the pipeline. Nothing here is deployed: the folder is outside the code bundle and the DCM project, and a push that only touches it does not run the pipeline.

Open them in the Snowsight Workspace of this repository (see `CONTRIBUTING.md`) as `FR_AI_ENGINEER`, which reads every environment, or locally with a named connection. A notebook takes its inputs in its first cell, environment and version names, so the same notebook serves dev, test and prod.

| Notebook | When | Reads |
|---|---|---|
| `regression_eda.ipynb` | the regression gate refused a challenger (see `docs/runbook.md`) | `RUN_LOG`, the two versions' metrics, `FORECAST_SITE_MONTH` for both, the feature view, the monitors |

Commit notebooks with their outputs cleared, so no data or account name travels with the file.
