-- Copies one model version from the previous environment's registry into this one, idempotently, with its comment.
-- Variables: db (target database), src_db (source database), version.
EXECUTE IMMEDIATE $$
DECLARE
  v STRING DEFAULT '<% version %>';
  c STRING;
  n INTEGER;
BEGIN
  SHOW VERSIONS IN MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST;
  SELECT "comment" INTO :c FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = :v;
  SHOW MODELS LIKE 'SITE_TONNES_FORECAST' IN SCHEMA <% db %>.MODELS;
  SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
  IF (n = 0) THEN
    EXECUTE IMMEDIATE 'CREATE MODEL <% db %>.MODELS.SITE_TONNES_FORECAST WITH VERSION ' || v ||
                      ' FROM MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST VERSION ' || v;
  ELSE
    SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
    SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = :v;
    IF (n > 0) THEN
      RETURN 'exists ' || v;
    END IF;
    EXECUTE IMMEDIATE 'ALTER MODEL <% db %>.MODELS.SITE_TONNES_FORECAST ADD VERSION ' || v ||
                      ' FROM MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST VERSION ' || v;
  END IF;
  IF (c IS NOT NULL) THEN
    EXECUTE IMMEDIATE 'ALTER MODEL <% db %>.MODELS.SITE_TONNES_FORECAST MODIFY VERSION ' || v || ' SET COMMENT = ''' || REPLACE(c, '''', '''''') || '''';
  END IF;
  RETURN 'promoted ' || v;
END;
$$;
