-- Runs one job of the code bundle on the compute pool, waits for it, and records its job id. Variables: db, job, env, version, run_id.
EXECUTE CODE BUNDLE <% db %>.WORKSPACE.LUCKML
  ENTRYPOINT = 'jobs/<% job %>.py'
  ARGUMENTS = ('--env', '<% env %>', '--version', '<% version %>', '--run-id', '<% run_id %>');

UPDATE <% db %>.WORKSPACE.RUN_LOG
SET JOB_ID = (SELECT RUNTIME_NAME FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.CODE_BUNDLE_HISTORY()) WHERE QUERY_ID = LAST_QUERY_ID())
WHERE RUN_ID = '<% run_id %>' AND STAGE = '<% job %>' AND MODEL_VERSION = '<% version %>';

SELECT RUN_ID, STAGE, MODEL_VERSION, MAPE, GATE_PASSED, JOB_ID
FROM <% db %>.WORKSPACE.RUN_LOG
WHERE RUN_ID = '<% run_id %>' AND STAGE = '<% job %>' AND MODEL_VERSION = '<% version %>';
