# Architecture

![Lifecycle](../img/mlops-sdlc.png)

Three repositories share the work. `LuckData-IaC-Snowflake-Horizon` declares the identities, databases, roles, pool and warehouse. `LuckData-Snowflake` deploys the source views the model reads and the ODS view reporting consumes. This repository deploys the model's own objects and moves one version from dev to prod. The journeys below are the numbered arrows on the diagram.

## A0, experiments

The AI engineer signs in to Snowsight as `FR_AI_ENGINEER`, which holds admin on `DEV_ML_DB.FEATURES`, `WORKSPACE` and `MODELS`, and works in a Workspace against the dev feature view. Versions logged this way live in `DEV_ML_DB.MODELS` beside the pipeline's and never leave dev. The same role has read only on test and prod.

The Workspace is created from this repository (Projects, Workspaces, From Git repository, this repository's URL, a personal branch), which needs the Git API integration and secret from the bootstrap. Day to day:

1. Create or open the Workspace on a branch named after the change, with role `FR_AI_ENGINEER`, warehouse `ML_WH`, context `DEV_ML_DB.WORKSPACE`.
2. Experiment in a notebook beside the code: read `DEV_ML_DB.FEATURES.SITE_MONTHLY_TONNES$1`, train, log versions to `DEV_ML_DB.MODELS.SITE_TONNES_FORECAST` under names that cannot collide with the pipeline's `V<build>` (a `VEXP_` prefix), compare them in the Models page.
3. Put the change into the code and the YAML the pipeline runs (`src/luckml`, `jobs`, `features/sources`, `dcm/sources`), run the unit tests, commit and push the branch from the Workspace.
4. Open the pull request. The branch policy runs `Validate`, which shows the DCM and feature store plans against dev as `SVC_MLOPS_DEV`. After the merge the pipeline trains, promotes and forecasts.

A notebook is a place to try things, not a deployable. Nothing a notebook creates is read by test or prod.

## A1 to A6, code to prod

A branch and a pull request (A1) run `Validate` through the branch policy on `main`: lint, unit tests, `snow dcm plan` and `snow feature plan` as `SVC_MLOPS_DEV` (A2). A merge to `main` runs `Validate` again and continues (A3) to `Dev`, then `Test` when dev verified (A4), then the approval check on the prod environment (A5) and `Prod` (A6). A pull request run stops after `Validate`.

## B1 and B2, one identity per environment

Each stage is a deployment job on its own Azure DevOps environment and signs in through its own service connection. The connection's federated token (B1) is presented to Snowflake as `SVC_MLOPS_<ENV>`, a service user that holds `RBAC_ML_DEPLOYER_<ENV>` and nothing else. No key pair, no secret, nothing to rotate. The dev identity cannot read `TEST_ML_DB`; the boundary proof below shows the refusal.

Under that role the stage runs the same six steps (B2): `snow dcm deploy` for the `WORKSPACE` view, tables and stage; `snow feature apply` for the feature view in `FEATURES`; the code to the `CODE` stage; the version (trained in dev as an ML Job on `ML_CPU_POOL`, copied elsewhere); the batch forecast as a second ML Job; `verify.sql` and the monitor.

## C1 and C2, promotion

Test receives the exact version dev logged, by `CREATE MODEL ... FROM MODEL` across databases (C1), through the `USAGE` and `READ` its deployer holds on dev's models (`MODELS_R` of the previous environment; the copy reads the model's artifacts, which `USAGE` alone does not allow). Prod does the same from test and sets the version as the default (C2), which is what production code calls. A rerun with a version already present is a no-op.

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
