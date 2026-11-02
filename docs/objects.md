# Objects

What exists in each environment's ML database, who creates it, and what it holds. `<ENV>` is `DEV`, `TEST` or `PROD`. The database, its three schemas, the roles and the service users come from `LuckData-IaC-Snowflake-Horizon`; everything below is created by this repository's pipeline as `RBAC_ML_DEPLOYER_<ENV>`.

## WORKSPACE

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `MLOPS` | DCM project | `snow dcm create` | the deployment history of everything DCM declares |
| `SRC_SITE_MONTH` | view | DCM | monthly tonnes per site, read from `<ENV>_DB.ODS.FCT_SITE_MONTH` |
| `FORECAST_SITE_MONTH` | table | DCM, filled by the forecast job | one row per site, month and model version |
| `RUN_LOG` | table | DCM, filled by the jobs | one row per training or forecast run |
| `LUCKML` | code bundle | DCM, from `dcm/assets/luckml` | the package, the two job entry points and the config |
| `FORECAST_V<n>` | view | `scripts/monitor.sql` | the rows of version `V<n>` only, the source of its monitor |
| `JOB_RESULTS` | stage | DCM | the code bundle's result stage; empty, the jobs write to tables |

```sql
select SITE_ID, MONTH, FORECAST_TONNES, ACTUAL_TONNES, MODEL_VERSION
from PROD_ML_DB.WORKSPACE.FORECAST_SITE_MONTH where MODEL_VERSION = 'V118' order by SITE_ID, MONTH limit 3;
-- 101 | 2026-07-01 | 25589.1 | 29699.7 | V118   held-out month, actual known
-- 101 | 2026-10-01 | 22537.9 |    null | V118   month ahead, actual written when the month closes

select RUN_ID, STAGE, MODEL_VERSION, MAPE, GATE_PASSED, JOB_ID from PROD_ML_DB.WORKSPACE.RUN_LOG order by RUN_AT desc limit 2;
-- 118 | forecast | V118 | null   | true | PROD_ML_DB.WORKSPACE.FORECAST_...
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

## MODELS

| Object | Kind | Created by | Holds |
|---|---|---|---|
| `SITE_TONNES_FORECAST` | model | the training job in dev, `scripts/promote.sql` elsewhere | one version per pipeline run, `V<build id>`; the default is what production calls |
| `SITE_TONNES_FORECAST_V<n>_MON` | model monitor | `scripts/monitor.sql` | MAPE, MAE, RMSE, drift and counts per month for version `V<n>` |

```sql
show versions in model PROD_ML_DB.MODELS.SITE_TONNES_FORECAST;
select * from table(MODEL_MONITOR_PERFORMANCE_METRIC(
  'PROD_ML_DB.MODELS.SITE_TONNES_FORECAST_V118_MON', 'MAPE', '1 month', '2026-06-01'::timestamp_ntz, current_timestamp()::timestamp_ntz));
```

## Growth and cleanup

Each pipeline run adds, per environment, a model version, a `FORECAST_V<n>` view, a monitor, and one set of forecast rows for that version.

The pipeline retires old versions as its last step in each environment, as `SVC_MLOPS_<ENV>`, the owner of these objects. Two settings in `dcm/assets/luckml/config/<env>.yml` control it:

```yaml
retire_enabled: false    # true to retire; false logs "nothing retired"
retain_versions: 50      # versions kept besides the default
```

When enabled, `scripts/retire.sql` keeps the default and the newest `retain_versions` other versions, and for every older one drops its monitor, then its view, then the version. The forecast rows stay as history. A rerun drops nothing more, and a monitor or view already removed is skipped. The run log prints `retired: V92 V93` or `retired: none`.

`RBAC_ML_DEPLOYER_<ENV>` is held by no person; an administrator can act with it through `SYSADMIN` to repair an environment, not as the way to clean up.
