-- The stage's check after the forecast: rows written, no null forecast, the version present, its baseline written.
-- Variables: db, schema, model, version.
SHOW VERSIONS IN MODEL <% db %>.MODELS.<% model %>;
SELECT
  (SELECT COUNT(*) FROM <% db %>.<% schema %>.SITE_MONTH_FORECAST
    WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>') AS forecast_rows,
  (SELECT COUNT(*) FROM <% db %>.<% schema %>.SITE_MONTH_FORECAST
    WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>' AND FORECAST_TONNES IS NULL) AS null_forecasts,
  (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = '<% version %>') AS version_present,
  (SELECT COUNT(*) FROM <% db %>.<% schema %>.SITE_MONTH_BASELINE WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>') AS baseline_rows;
