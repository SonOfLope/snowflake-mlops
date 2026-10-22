# Architecture

![Lifecycle](../img/mlops-sdlc.png)

Three repositories share the work. `LuckData-IaC-Snowflake-Horizon` declares the identities, databases, roles, pool and warehouse. `LuckData-Snowflake` deploys the source views the model reads and the ODS view reporting consumes. This repository deploys the model's own objects and moves one version from dev to prod. The journeys below are the numbered arrows on the diagram.

## A0, experiments

The AI engineer signs in to Snowsight as `FR_AI_ENGINEER`, which holds admin on `DEV_ML_DB.FEATURES`, `WORKSPACE` and `MODELS`, and works in a Workspace notebook or an IDE against the dev feature view. Versions logged this way live in `DEV_ML_DB.MODELS` beside the pipeline's and never leave dev. The same role has read only on test and prod.

## A1 to A6, code to prod

A branch and a pull request (A1) run `Validate` through the branch policy on `main`: lint, unit tests, `snow dcm plan` and `snow feature plan` as `SVC_MLOPS_DEV` (A2). A merge to `main` runs `Validate` again and continues (A3) to `Dev`, then `Test` when dev verified (A4), then the approval check on the prod environment (A5) and `Prod` (A6). A pull request run stops after `Validate`.

## B1 and B2, one identity per environment

Each stage is a deployment job on its own Azure DevOps environment and signs in through its own service connection. The connection's federated token (B1) is presented to Snowflake as `SVC_MLOPS_<ENV>`, a service user that holds `RBAC_ML_DEPLOYER_<ENV>` and nothing else. No key pair, no secret, nothing to rotate. The dev identity cannot read `TEST_ML_DB`; the boundary proof below shows the refusal.

Under that role the stage runs the same steps (B2): `snow dcm deploy` for the `WORKSPACE` view, tables and stage; `snow feature apply` for the feature view in `FEATURES`; the code to the `CODE` stage; the version (trained in dev as an ML Job on `ML_CPU_POOL`, copied elsewhere); the batch forecast as a second ML Job; `actuals.sql`, which writes the closed months' actuals onto every version's rows, and `regression.sql`, which refuses a candidate whose MAPE on those months is worse than the current default's beyond a tolerance; `verify.sql` and the monitor; `set_default.sql`, so each environment's default is its last version that passed.

## C1 and C2, promotion

Test receives the exact version dev logged, by `CREATE MODEL ... FROM MODEL` across databases (C1), through the `USAGE` and `READ` its deployer holds on dev's models (`MODELS_R` of the previous environment; the copy reads the model's artifacts, which `USAGE` alone does not allow). Prod does the same from test (C2). The default version in prod is what production code calls, and it moves only after the regression gate in prod passed. A rerun with a version already present is a no-op, and the copy carries the version's comment.

## D1, the data

Each `<ENV>_ML_DB.WORKSPACE.SRC_SITE_MONTH` view reads `<ENV>_DB.ODS.FCT_SITE_MONTH` through the `SILVER_R` and `ODS_R` database roles. The feature view computes the lags over it.

## F1, consumption

Reporting reads an ODS view in `PROD_DB` over `PROD_ML_DB.WORKSPACE.FORECAST_SITE_MONTH`, declared and deployed by `LuckData-Snowflake`, so a model change never reaches a report without passing the three environments.

## Boundary proof

The dev deployer role against the test database, as recorded on the first run:

```
select count(*) from TEST_ML_DB.WORKSPACE.FORECAST_SITE_MONTH
select count(*) from TEST_ML_DB.WORKSPACE.FORECAST_SITE_MONTH
002003 (02000): 01c7e095-0003-18b4-0003-b95e0020fb3e: SQL compilation error:
Database 'TEST_ML_DB' does not exist or not authorized. Your primary role
RBAC_ML_DEPLOYER_DEV must have USAGE or any other privilege granted on
DATABASE TEST_ML_DB.
```
