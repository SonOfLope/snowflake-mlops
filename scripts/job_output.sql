-- Prints the log of the last execution of one job of the code bundle, through the governed events view. Variables: db, job.
SET svc = (SELECT SPLIT_PART(RUNTIME_NAME, '.', 3)
           FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.CODE_BUNDLE_HISTORY())
           WHERE CODE_BUNDLE_NAME = 'LUCKML' AND DATABASE_NAME = '<% db %>' AND ENTRYPOINT = 'jobs/<% job %>.py'
           ORDER BY START_TIME DESC LIMIT 1);
SELECT VALUE::STRING AS LINE
FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
WHERE RESOURCE_ATTRIBUTES:"snow.service.name" = $svc
  AND RESOURCE_ATTRIBUTES:"snow.database.name" = '<% db %>'
  AND RECORD_TYPE = 'LOG'
ORDER BY TIMESTAMP;
