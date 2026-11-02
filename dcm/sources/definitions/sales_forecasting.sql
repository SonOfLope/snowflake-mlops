-- The sales forecasting family: what its models write, one row per site, month, model and version. MODEL is the last
-- column so a table moved here from WORKSPACE is altered into shape. The monthly task graph is in cycle.sql.
DEFINE TABLE {{ db }}.SALES_FORECASTING.SITE_MONTH_FORECAST (
  ROW_ID VARCHAR NOT NULL,
  SITE_ID NUMBER(38,0),
  MONTH TIMESTAMP_NTZ,
  MONTH_NUM NUMBER(2,0),
  LAG_1 NUMBER(18,1),
  LAG_2 NUMBER(18,1),
  LAG_3 NUMBER(18,1),
  FORECAST_TONNES NUMBER(18,1),
  ACTUAL_TONNES NUMBER(18,1),
  MODEL_VERSION VARCHAR,
  RUN_ID VARCHAR,
  RUN_AT TIMESTAMP_NTZ,
  MODEL VARCHAR
) COMMENT = 'Forecast rows per site and month, one set per model version; actuals filled as months close.'
  DATA_METRIC_SCHEDULE = '{{ dq_schedule }}';

DEFINE TABLE {{ db }}.SALES_FORECASTING.SITE_MONTH_BASELINE (
  ROW_ID VARCHAR NOT NULL,
  SITE_ID NUMBER(38,0),
  MONTH TIMESTAMP_NTZ,
  MONTH_NUM NUMBER(2,0),
  LAG_1 NUMBER(18,1),
  LAG_2 NUMBER(18,1),
  LAG_3 NUMBER(18,1),
  FORECAST_TONNES NUMBER(18,1),
  ACTUAL_TONNES NUMBER(18,1),
  MODEL_VERSION VARCHAR,
  RUN_ID VARCHAR,
  RUN_AT TIMESTAMP_NTZ,
  MODEL VARCHAR
) COMMENT = 'The rows each model version was trained on, scored by that version: the reference its monitor measures drift against.';
