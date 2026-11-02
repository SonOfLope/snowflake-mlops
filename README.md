# LuckData-Snowflake-MLOps

The monthly site tonnes forecast as code on Snowflake. A small Python package trains a LightGBM model on a feature view, logs the version to the Model Registry, writes a batch forecast and creates a monitor. One Azure DevOps pipeline promotes the code from dev to test to prod; each environment trains its own model on its own data, under its own identity, prod behind an approval. Every month a Snowflake task graph retrains in prod and keeps the better of the new model and the current one. The platform objects it runs on (databases, roles, service users, compute pool, warehouse) are declared in `LuckData-IaC-Snowflake-Horizon`; this repository never creates them.

![Lifecycle](img/mlops-sdlc.png)

## Lifecycle

1. **Experiment in dev.** An AI engineer works directly in `DEV_ML_DB` as `FR_AI_ENGINEER`, from a Workspace notebook or an IDE, and logs as many versions as the work needs. Nothing here touches `main`.
2. **Pull request.** The candidate's code goes on a branch. The branch policy runs the `Validate` stage: `ruff`, `pytest`, `snow dcm plan` and `snow feature plan` against dev, signed in as `SVC_MLOPS_DEV`.
3. **Main, dev.** The merge runs `Validate` again, then the `Dev` stage deploys the schema objects, the code bundle and the monthly task graph (DCM) and the feature views, then runs four jobs on `ML_CPU_POOL`: **train** a challenger `V<build>` on dev data (held-out weighted error under `gate_wape_max`, else nothing is logged), **forecast** with it, **gate** it against dev's current default on the months with actuals, **promote** it (verify, monitor, make it the default, retire old versions when enabled).
4. **Test.** The same steps on `TEST_ML_DB` with test data. Test proves the reviewed code trains, forecasts and passes the gates on a second dataset.
5. **Prod.** After the approval on the `LuckData-Snowflake-MLOps-prod` environment, the same steps on `PROD_ML_DB` with production data. The default version in prod is what production code calls; it moves only when a challenger passes the regression gate there.
6. **Every month, in prod.** The task graph `PROD_ML_DB.WORKSPACE.MONTHLY_CYCLE` forecasts the next months with the current default, then trains a challenger `M<yyyymmddhhmi>` on the latest data, forecasts, gates and promotes it with the same jobs. A challenger that loses leaves the champion in place. The graph is declared in every environment and started only in prod.

`docs/architecture.md` walks the diagram journey by journey.

## Metrics

Every training run scores the challenger on the held-out months, on rows with a positive actual, and stores the result with the version in the registry and in `RUN_LOG.METRICS`. Two numbers block, the rest inform.

| Metric | Definition | Role |
|---|---|---|
| `wape` | sum of absolute errors over sum of actual tonnes | the gate metric: under `gate_wape_max` to be logged, within `regression_tolerance` of the default's to be promoted |
| `mape` | mean of per-row percentage errors | reported; a small site with a large miss dominates it, which is why it does not gate |
| `bias` | sum of signed errors over sum of actuals; positive means over-forecast | reported |
| `median_ape`, `p90_ape` | the middle and the worst tenth of the per-row errors | reported |
| `rmse` | root mean squared error, in tonnes | reported |
| `stockout_rate`, `excess_rate` | share of rows under-forecast, or over-forecast, by more than 20 percent | reported |
| `persistence_wape`, `seasonal_naive_wape` | the error of the trailing three-month average and of the same month last year, on the same rows | reported; a model that does not beat them is not earning its keep |

A metric becomes blocking only when the business decides a release should stop on it; until then it is a number people read, and an alert can watch.

## Layout

```
azure-pipelines.yml            Validate, Dev, Test, Prod (approval)
pipelines/templates/           tools.yml (Python environment), snow-step.yml (signed-in step), deploy-env.yml (the steps per environment)
dcm/                           DCM project: WORKSPACE view, tables, stage, the LUCKML code bundle and the MONTHLY_CYCLE task graph
dcm/assets/luckml/             the code bundle: code_bundle.yml, the luckml package, jobs/ (train, forecast, gate, promote), sql/, config/
features/                      declarative feature store: SITE entity, SITE_MONTH_LAGS source, SITE_MONTHLY_TONNES view
scripts/                       run_job.sql and job_output.sql, the pipeline's two SQL steps
tests/                         unit tests, no Snowflake connection needed
bootstrap/README.md            what to create in Azure DevOps and Snowflake before the first run
docs/architecture.md           the diagram explained
CONTRIBUTING.md                how a change is made and reaches an environment
features/README.md             the feature store project
img/                           the lifecycle, quality gates and sign-in diagrams, editable in draw.io
```

## Local run

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
snow connection add                      # a connection for your user, role FR_AI_ENGINEER
export SNOWFLAKE_CONNECTION_NAME=<name>
export SNOWFLAKE_CLI_FEATURES_ENABLE_FEATURE_STORE=true

.venv/bin/pytest -q && .venv/bin/ruff check .
(cd dcm && snow dcm plan -c <name> --target dev)
(cd features && snow feature plan -c <name> --database DEV_ML_DB --schema FEATURES --target dev)

```

The jobs run only through the pipeline, as the code bundle `DEV_ML_DB.WORKSPACE.LUCKML` that the DCM deploy creates. To run one by hand after a deploy, with a role that holds usage on the bundle and the pool:

```sql
USE DATABASE DEV_ML_DB; USE SCHEMA WORKSPACE;
EXECUTE CODE BUNDLE DEV_ML_DB.WORKSPACE.LUCKML
  ENTRYPOINT = 'jobs/train.py'
  ARGUMENTS = ('--env', 'dev', '--version', 'VEXP_1', '--run-id', 'manual');
```

## Pipeline variables

Set on the pipeline definition, not in the YAML, so the file is the same everywhere.

| Variable | Value |
|---|---|
| `serviceConnectionDev`, `serviceConnectionTest`, `serviceConnectionProd` | the three service connections, one managed identity each |
| `snowflakeAccount` | the account identifier, `<org>-<account>`, the one the targets in `dcm/manifest.yml` and `features/manifest.yml` name |
| `agentPool` | the Linux agent pool that runs the pipeline, Python 3.12 on the agents |

## Bootstrap

`bootstrap/README.md` lists what has to exist before the first run, in order.

## What the production model adds

This repository carries the pattern on a deliberately small model. The production forecast brings its own feature views and training code into the same places (`features/`, `src/luckml/`, `jobs/`), a task graph in `WORKSPACE` so the forecast runs monthly without a pipeline run, the ODS view that reporting reads over `WORKSPACE.FORECAST_SITE_MONTH` (declared in `LuckData-Snowflake`), and a scheduled retrain that registers a candidate in test for a person to promote.

## Versions

`requirements.in` holds the floors, `requirements.txt` the exact versions resolved from them, for the pipeline agent and local work. The jobs themselves run on the Snowflake ML runtime pinned by `runtime_version` in `dcm/assets/luckml/code_bundle.yml`. To move to the latest usable set, resolve again and let `Validate` prove it:

```bash
uv pip compile --upgrade --python-version 3.12 requirements.in -o requirements.txt
```

`lightgbm` is pinned to the version the Snowflake container runtime ships, so a model logged inside a job is the same library locally.
