-- The stage's check after the forecast: rows written, no null forecast, the version present. Variables: db, version.
SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
SELECT
  (SELECT COUNT(*) FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH WHERE MODEL_VERSION = '<% version %>') AS forecast_rows,
  (SELECT COUNT(*) FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH
    WHERE MODEL_VERSION = '<% version %>' AND FORECAST_TONNES IS NULL) AS null_forecasts,
  (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = '<% version %>') AS version_present;
