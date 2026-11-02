-- One release: the forecast tables move from WORKSPACE to SALES_FORECASTING with their rows, as a copy, since a table cannot
-- be renamed out of a managed access schema by its owner. Each table leaves the project's management first (its data metric
-- attachments too), so the deploy that follows adopts the copy at the new name, adds the MODEL column and attaches the checks
-- again. The old names stay as views for the monitors of the versions promoted before. Does nothing once the tables have
-- moved, and tolerates a table already released by an earlier attempt. Variables: db.
EXECUTE IMMEDIATE $$
DECLARE
  moved STRING DEFAULT '';
  present NUMBER;
  released NUMBER;
BEGIN
  SELECT COUNT(*) INTO :present FROM <% db %>.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'WORKSPACE' AND TABLE_NAME = 'FORECAST_SITE_MONTH' AND TABLE_TYPE = 'BASE TABLE';
  IF (present = 1) THEN
    SELECT SYSTEM$UNMANAGE_FROM_DCM_PROJECT('<% db %>.WORKSPACE.MLOPS', '
ATTACH DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  TO TABLE <% db %>.WORKSPACE.FORECAST_SITE_MONTH
  ON (FORECAST_TONNES)
  EXPECTATION NO_NULL_FORECAST (VALUE = 0);
ATTACH DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  TO TABLE <% db %>.WORKSPACE.FORECAST_SITE_MONTH
  ON (ROW_ID, MODEL_VERSION)
  EXPECTATION ONE_ROW_PER_VERSION_SITE_MONTH (VALUE = 0);
') INTO :released;
    IF (released = 1) THEN
      RETURN 'FAIL the project released one of the two data metric attachments of FORECAST_SITE_MONTH, nothing moved';
    END IF;
    SELECT SYSTEM$UNMANAGE_ENTITY_FROM_DCM_PROJECT('<% db %>.WORKSPACE.MLOPS', 'TABLE', '<% db %>.WORKSPACE.FORECAST_SITE_MONTH') INTO :released;
    CREATE TABLE <% db %>.SALES_FORECASTING.SITE_MONTH_FORECAST AS SELECT * FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH;
    DROP TABLE <% db %>.WORKSPACE.FORECAST_SITE_MONTH;
    CREATE VIEW <% db %>.WORKSPACE.FORECAST_SITE_MONTH AS SELECT * FROM <% db %>.SALES_FORECASTING.SITE_MONTH_FORECAST;
    moved := moved || 'FORECAST_SITE_MONTH ';
  END IF;
  SELECT COUNT(*) INTO :present FROM <% db %>.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'WORKSPACE' AND TABLE_NAME = 'BASELINE_SITE_MONTH' AND TABLE_TYPE = 'BASE TABLE';
  IF (present = 1) THEN
    SELECT SYSTEM$UNMANAGE_ENTITY_FROM_DCM_PROJECT('<% db %>.WORKSPACE.MLOPS', 'TABLE', '<% db %>.WORKSPACE.BASELINE_SITE_MONTH') INTO :released;
    CREATE TABLE <% db %>.SALES_FORECASTING.SITE_MONTH_BASELINE AS SELECT * FROM <% db %>.WORKSPACE.BASELINE_SITE_MONTH;
    DROP TABLE <% db %>.WORKSPACE.BASELINE_SITE_MONTH;
    CREATE VIEW <% db %>.WORKSPACE.BASELINE_SITE_MONTH AS SELECT * FROM <% db %>.SALES_FORECASTING.SITE_MONTH_BASELINE;
    moved := moved || 'BASELINE_SITE_MONTH ';
  END IF;
  RETURN 'moved: ' || COALESCE(NULLIF(TRIM(moved), ''), 'none, already in SALES_FORECASTING');
END;
$$;
