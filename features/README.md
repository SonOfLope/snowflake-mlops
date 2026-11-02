# Features

A declarative feature store project. `snow feature plan` shows what would change in `<ENV>_ML_DB.FEATURES`, `snow feature apply` makes it so. The pipeline runs both per environment.

## Layout

```
manifest.yml                    targets (dev, test, prod): account, database, schema, role, warehouse
sources/entities/               the keys features are looked up by (SITE, join key SITE_ID)
sources/datasources/            a named query and its columns (SITE_MONTH_LAGS over WORKSPACE.SRC_SITE_MONTH)
sources/feature_views/          which columns are features, for which entity, on which timestamp, refreshed how often
sources/feature_groups/         aggregated features over a time window, computed by the feature store (none yet)
```

## Add a feature

1. Add the column to the data source query and its `columns` list, or add a new data source.
2. Add the column to the feature view's `features`. A column change is a new `version` of the view, the old version stays until nothing reads it.
3. `snow feature plan --target dev` from this directory, read the operations, then open the pull request.

## A new feature view version

When: a column is added, removed, renamed or computed differently. A change to the refresh frequency or the description is not a new version.

How, in one pull request:

1. Copy `sources/feature_views/SITE_MONTHLY_TONNES.yaml` to `sources/feature_views/SITE_MONTHLY_TONNES_2.yaml` in the same folder, keep `name: SITE_MONTHLY_TONNES`, set `version: "2"` and make the change. The file name only has to be unique; the name and version inside it identify the view. Keep the version 1 file.
2. Point the model at it: `feature_view_version: "2"` in `dcm/assets/luckml/config/<env>.yml`, and the column list in `luckml/data.py` and `luckml/features.py` if columns changed.
3. Merge. The pipeline creates `SITE_MONTHLY_TONNES$2` beside `$1` in each environment, trains on it in dev and promotes as usual. The regression gate compares the new version against the current default, so a worse feature set does not reach production.
4. Once prod's default is trained on version 2, delete the version 1 file in a later pull request; the next apply drops `$1`.

## A new environment or a new repository

`snow feature init` once per schema creates the `_FEATURE_STORE_METADATA` table and the scaffold above. The pipeline does this on the first run of an environment. Running it on an initialized schema exports the deployed objects into `sources/`, so run it in a scratch directory.

## Feature groups

A feature group declares windowed aggregations (sum, average, count, last value over 7 days, 30 days) from a timestamped source, and the feature store maintains them. This project computes its lags with `LAG` in the data source query instead. Use a feature group when a rolling window over tickets or days is wanted rather than a fixed monthly lag.
