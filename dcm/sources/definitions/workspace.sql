DEFINE VIEW {{ db }}.WORKSPACE.SRC_SITE_MONTH
  COMMENT = 'Monthly tonnes per site, the model input, read from the data platform.'
  AS SELECT SITE_ID, MONTH, TONNES FROM {{ src_db }}.ODS.FCT_SITE_MONTH;

DEFINE TABLE {{ db }}.WORKSPACE.FORECAST_SITE_MONTH (
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
  RUN_AT TIMESTAMP_NTZ
) COMMENT = 'Forecast rows per site and month, one set per model version; actuals filled as months close.';

DEFINE TABLE {{ db }}.WORKSPACE.RUN_LOG (
  RUN_ID VARCHAR,
  STAGE VARCHAR,
  MODEL_VERSION VARCHAR,
  MAPE NUMBER(9,4),
  GATE_PASSED BOOLEAN,
  JOB_ID VARCHAR,
  RUN_AT TIMESTAMP_NTZ
) COMMENT = 'One row per pipeline step that trained or forecast.';

DEFINE STAGE {{ db }}.WORKSPACE.CODE
  COMMENT = 'Results the ML Jobs write, the code bundle result stage.';

DEFINE CODE BUNDLE {{ db }}.WORKSPACE.LUCKML
  FROM 'asset://luckml/'
  COMMENT = 'Training and forecast jobs, run on ML_CPU_POOL with EXECUTE CODE BUNDLE.';
