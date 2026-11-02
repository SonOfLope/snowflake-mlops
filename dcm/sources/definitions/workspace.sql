DEFINE VIEW {{ db }}.WORKSPACE.SRC_SITE_MONTH
  COMMENT = 'Monthly tonnes per site, the model input, read from the data platform.'
  DATA_METRIC_SCHEDULE = '{{ dq_schedule }}'
  AS SELECT SITE_ID, MONTH, TONNES FROM {{ src_db }}.ODS.FCT_SITE_MONTH;

DEFINE TABLE {{ db }}.WORKSPACE.RUN_LOG (
  RUN_ID VARCHAR,
  STAGE VARCHAR,
  MODEL_VERSION VARCHAR,
  MAPE NUMBER(9,4),
  GATE_PASSED BOOLEAN,
  JOB_ID VARCHAR,
  RUN_AT TIMESTAMP_NTZ,
  WAPE NUMBER(9,4),
  METRICS VARIANT,
  MODEL VARCHAR
) COMMENT = 'One row per job run of any model; METRICS holds every held-out metric of a training run.';

DEFINE STAGE {{ db }}.WORKSPACE.JOB_RESULTS
  COMMENT = 'Result stage of the LUCKML code bundle; the jobs write their output to tables.';

DEFINE CODE BUNDLE {{ db }}.WORKSPACE.LUCKML
  FROM 'asset://luckml/'
  COMMENT = 'Training and forecast jobs, run on ML_CPU_POOL with EXECUTE CODE BUNDLE.';
