-- Prints the log of the last execution of one job of the code bundle, from the account event table. Variables: db, job.
SELECT e.VALUE::STRING AS LINE
FROM SNOWFLAKE.TELEMETRY.EVENTS e
JOIN (
  SELECT SPLIT_PART(RUNTIME_NAME, '.', 3) AS SERVICE
  FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.CODE_BUNDLE_HISTORY())
  WHERE CODE_BUNDLE_NAME = 'LUCKML' AND DATABASE_NAME = '<% db %>' AND ENTRYPOINT = 'jobs/<% job %>.py'
  ORDER BY START_TIME DESC
  LIMIT 1
) j ON e.RESOURCE_ATTRIBUTES:"snow.service.name" = j.SERVICE
WHERE e.RESOURCE_ATTRIBUTES:"snow.database.name" = '<% db %>' AND e.RECORD_TYPE = 'LOG'
ORDER BY e.TIMESTAMP;
