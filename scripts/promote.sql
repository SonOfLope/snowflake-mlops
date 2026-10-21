-- Copies one model version from the previous environment's registry into this one, idempotently.
-- Variables: db (target database), src_db (source database), version.
EXECUTE IMMEDIATE $$
DECLARE
  v STRING DEFAULT '<% version %>';
  n INTEGER;
BEGIN
  SHOW MODELS LIKE 'SITE_TONNES_FORECAST' IN SCHEMA <% db %>.MODELS;
  SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
  IF (n = 0) THEN
    EXECUTE IMMEDIATE 'CREATE MODEL <% db %>.MODELS.SITE_TONNES_FORECAST WITH VERSION ' || v ||
                      ' FROM MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST VERSION ' || v;
    RETURN 'created model with version ' || v;
  END IF;
  SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
  SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = :v;
  IF (n > 0) THEN
    RETURN 'exists ' || v;
  END IF;
  EXECUTE IMMEDIATE 'ALTER MODEL <% db %>.MODELS.SITE_TONNES_FORECAST ADD VERSION ' || v ||
                    ' FROM MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST VERSION ' || v;
  RETURN 'added ' || v;
END;
$$;
