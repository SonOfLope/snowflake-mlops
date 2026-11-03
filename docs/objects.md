# Objects

What exists in each environment's ML database, who creates it, and what it holds. `<ENV>` is `DEV`, `TEST` or `PROD`. The database, its four schemas, the roles and the service users come from `LuckData-IaC-Snowflake-Horizon`; everything below is created by this repository's pipeline as `RBAC_ML_DEPLOYER_<ENV>`.

## WORKSPACE

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `MLOPS` | DCM project | `snow dcm create` | the deployment history of everything DCM declares |
| `SRC_SITE_MONTH` | view | DCM | monthly tonnes per site, read from `<ENV>_DB.ODS.FCT_SITE_MONTH`; carries the data expectations on the source |
| `RUN_LOG` | table | DCM, filled by the jobs | one row per job run of any model, `MODEL` names it; a training row carries `WAPE`, `MAPE` and every metric in `METRICS` |
| `LUCKML` | code bundle | DCM, from `dcm/assets/luckml` | the package, the job entry points and the config |
| `FORECAST_SITE_MONTH`, `BASELINE_SITE_MONTH` | views | the move to `SALES_FORECASTING`, once | the old names of the two tables now in `SALES_FORECASTING`, read by the monitors of the versions promoted before the move; drop them with the last of those versions |
| `FORECAST_V<n>`, `BASELINE_V<n>` | views | `sql/monitor.sql`, before the move | the per-version views of those same versions; the retire step drops them |
| `JOB_RESULTS` | stage | DCM | the code bundle's result stage: one folder per job run, `LUCKML/<JOB>_<id>/`, holding the entry point's result (a few bytes); the jobs write their output to the tables, nothing reads this stage, purge it freely |
| `IMAGES` | image repository | `LuckData-IaC-Snowflake-Horizon` | container images for a model served as a service; empty, the jobs run on Snowflake's ML runtime image |

```sql
select RUN_ID, STAGE, MODEL_VERSION, WAPE, METRICS:bias::float as BIAS, GATE_PASSED from PROD_ML_DB.WORKSPACE.RUN_LOG
where STAGE = 'train' order by RUN_AT desc limit 1;
```

## FEATURES

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `SITE_MONTHLY_TONNES$1` | dynamic table | `snow feature apply` | the feature view, version 1, refreshed daily |
| `_FEATURE_STORE_METADATA` | table | `snow feature init` | the feature store's own catalogue; never edit |
| `SNOWML_SNAPSHOT_STATUS` | table | `snow feature init` | the feature store's refresh bookkeeping; never edit |
| `SNOWML_FEATURE_STORE_*` | tags | `snow feature init` | mark entities and feature views for discovery |

```sql
select SITE_ID, MONTH, TONNES, LAG_1, LAG_2, LAG_3, MONTH_NUM
from PROD_ML_DB.FEATURES."SITE_MONTHLY_TONNES$1" order by SITE_ID, MONTH desc limit 1;
```

## SALES_FORECASTING

The family schema: what the sales forecasting models write. A second model of the family (a nowcast, for example) writes the same tables under its own `MODEL`.

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `SITE_MONTH_FORECAST` | table | DCM, filled by the train job (held-out months) and the forecast job (months ahead) | one row per site, month, model and version; actuals filled as months close |
| `SITE_MONTH_BASELINE` | table | DCM, filled by the train job | the rows each version was trained on, scored by it; its monitor's reference for drift |
| `SITE_TONNES_FORECAST_V<n>` | view | `sql/monitor.sql` in the bundle | the rows of version `V<n>` only, the source of its monitor |
| `SITE_TONNES_FORECAST_V<n>_BASELINE` | table | `sql/monitor.sql` in the bundle | a snapshot of the training rows of version `V<n>`, the baseline of its monitor; a monitor clones its baseline, so it is a table |
| `SITE_TONNES_MONTHLY` | task graph | DCM | the monthly cycle: `SITE_TONNES_MONTHLY_START`, `_FORECAST_DEFAULT`, `_CHECK_DATA`, `_TRAIN`, `_FORECAST_CHALLENGER`, `_GATE`, `_PROMOTE`; started in prod only |

```sql
select SITE_ID, MONTH, FORECAST_TONNES, ACTUAL_TONNES, MODEL_VERSION
from PROD_ML_DB.SALES_FORECASTING.SITE_MONTH_FORECAST where MODEL = 'SITE_TONNES_FORECAST' and MODEL_VERSION = 'V118'
order by SITE_ID, MONTH limit 3;
-- 101 | 2026-07-01 | 25589.1 | 29699.7 | V118   held-out month, actual known
-- 101 | 2026-10-01 | 22537.9 |    null | V118   month ahead, actual written when the month closes
```

## MODELS

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `SITE_TONNES_FORECAST` | model | the training job, in every environment | one version per pipeline run, `V<build id>`, and per monthly run, `M<yyyymmddhhmi>`; the default is what production calls |
| `SITE_TONNES_FORECAST_V<n>_MON` | model monitor | `sql/monitor.sql` in the bundle | MAPE, MAE, RMSE, drift and counts per month for version `V<n>` |

```sql
show versions in model PROD_ML_DB.MODELS.SITE_TONNES_FORECAST;
select * from table(MODEL_MONITOR_PERFORMANCE_METRIC(
  'PROD_ML_DB.MODELS.SITE_TONNES_FORECAST_V118_MON', 'MAPE', '1 month', '2026-06-01'::timestamp_ntz, current_timestamp()::timestamp_ntz));
```

## Growth and cleanup

Each pipeline run adds, per environment, a model version, a `SITE_TONNES_FORECAST_V<n>` view, a `SITE_TONNES_FORECAST_V<n>_BASELINE` table, a monitor, one set of forecast rows and one set of baseline rows for that version.

The promote job retires old versions after making a challenger the default, in the pipeline and in the monthly graph, as `SVC_MLOPS_<ENV>`, the owner of these objects. Two settings in `dcm/assets/luckml/config/<env>.yml` control it:

```yaml
retire_enabled: false    # true to retire; false logs "nothing retired"
retain_versions: 50      # versions kept besides the default
```

When enabled, `sql/retire.sql` in the bundle keeps the default and the newest `retain_versions` other versions, and for every older one drops its monitor, then its view and baseline table, then the version. The forecast rows stay as history. A rerun drops nothing more, and a monitor or view already removed is skipped. The run log prints `retired: V92 V93` or `retired: none`.

`RBAC_ML_DEPLOYER_<ENV>` is held by no person; an administrator can act with it through `SYSADMIN` to repair an environment, not as the way to clean up.
