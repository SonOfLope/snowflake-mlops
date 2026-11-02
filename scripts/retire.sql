-- Retires every version except the default and the newest ones: its monitor, then its view, then the version.
-- Forecast rows stay as history. Variables: db, keep.
EXECUTE IMMEDIATE $$
DECLARE
  retired STRING DEFAULT '';
  c CURSOR FOR
    SELECT "name" AS v
    FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
    WHERE NOT "is_default_version"
    QUALIFY ROW_NUMBER() OVER (ORDER BY "created_on" DESC) > <% keep %>;
BEGIN
  SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
  FOR r IN c DO
    EXECUTE IMMEDIATE 'DROP MODEL MONITOR IF EXISTS <% db %>.MODELS.SITE_TONNES_FORECAST_' || r.v || '_MON';
    EXECUTE IMMEDIATE 'DROP VIEW IF EXISTS <% db %>.WORKSPACE.FORECAST_' || r.v;
    EXECUTE IMMEDIATE 'ALTER MODEL <% db %>.MODELS.SITE_TONNES_FORECAST DROP VERSION ' || r.v;
    retired := retired || r.v || ' ';
  END FOR;
  RETURN 'retired: ' || COALESCE(NULLIF(TRIM(retired), ''), 'none');
END;
$$;
