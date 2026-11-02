-- Retires every version except the default and the newest ones: its monitor, then its view and baseline table, then the version.
-- Forecast rows stay as history. The two WORKSPACE names belong to versions promoted before the family schema existed.
-- Variables: db, schema, model, keep.
EXECUTE IMMEDIATE $$
DECLARE
  retired STRING DEFAULT '';
  c CURSOR FOR
    SELECT "name" AS v
    FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
    WHERE NOT "is_default_version"
    QUALIFY ROW_NUMBER() OVER (ORDER BY "created_on" DESC) > <% keep %>;
BEGIN
  SHOW VERSIONS IN MODEL <% db %>.MODELS.<% model %>;
  FOR r IN c DO
    EXECUTE IMMEDIATE 'DROP MODEL MONITOR IF EXISTS <% db %>.MODELS.<% model %>_' || r.v || '_MON';
    EXECUTE IMMEDIATE 'DROP VIEW IF EXISTS <% db %>.<% schema %>.<% model %>_' || r.v;
    EXECUTE IMMEDIATE 'DROP TABLE IF EXISTS <% db %>.<% schema %>.<% model %>_' || r.v || '_BASELINE';
    EXECUTE IMMEDIATE 'DROP VIEW IF EXISTS <% db %>.WORKSPACE.FORECAST_' || r.v;
    EXECUTE IMMEDIATE 'DROP TABLE IF EXISTS <% db %>.WORKSPACE.BASELINE_' || r.v;
    EXECUTE IMMEDIATE 'ALTER MODEL <% db %>.MODELS.<% model %> DROP VERSION ' || r.v;
    retired := retired || r.v || ' ';
  END FOR;
  RETURN 'retired: ' || COALESCE(NULLIF(TRIM(retired), ''), 'none');
END;
$$;
