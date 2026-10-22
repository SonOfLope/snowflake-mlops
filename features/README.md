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

## A new environment or a new repository

`snow feature init` once per schema creates the `_FEATURE_STORE_METADATA` table and the scaffold above. The pipeline does this on the first run of an environment. Running it on an initialized schema exports the deployed objects into `sources/`, so run it in a scratch directory.

## Feature groups

A feature group declares windowed aggregations (sum, average, count, last value over 7 days, 30 days) from a timestamped source, and the feature store maintains them. This project computes its lags with `LAG` in the data source query instead. Use a feature group when a rolling window over tickets or days is wanted rather than a fixed monthly lag.
