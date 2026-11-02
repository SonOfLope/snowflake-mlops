-- Compares a candidate's wape (weighted error) on the months with actuals to the default version's; returns a line starting with FAIL
-- when it is worse by more than the tolerance, and the caller fails on it.
-- Variables: db, version, tolerance (a fraction, 0.10 allows ten percent worse).
EXECUTE IMMEDIATE $$
DECLARE
  v STRING DEFAULT '<% version %>';
  d STRING;
  candidate FLOAT;
  champion FLOAT;
BEGIN
  SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
  SELECT "name" INTO :d FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "is_default_version" = TRUE;
  IF (d IS NULL OR d = v) THEN
    RETURN 'no default to compare, ' || v || ' passes';
  END IF;
  SELECT SUM(ABS(FORECAST_TONNES - ACTUAL_TONNES)) / SUM(ACTUAL_TONNES) INTO :candidate
    FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH
    WHERE MODEL_VERSION = :v AND ACTUAL_TONNES > 0;
  SELECT SUM(ABS(c.FORECAST_TONNES - c.ACTUAL_TONNES)) / SUM(c.ACTUAL_TONNES) INTO :champion
    FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH c
    JOIN <% db %>.WORKSPACE.FORECAST_SITE_MONTH n ON n.ROW_ID = c.ROW_ID AND n.MODEL_VERSION = :v AND n.ACTUAL_TONNES > 0
    WHERE c.MODEL_VERSION = :d AND c.ACTUAL_TONNES > 0;
  IF (candidate IS NULL OR champion IS NULL) THEN
    RETURN 'no common scored months between ' || v || ' and the default ' || d || ', ' || v || ' passes';
  END IF;
  IF (candidate > champion * (1 + <% tolerance %>)) THEN
    RETURN 'FAIL ' || v || ' wape ' || ROUND(candidate, 4) || ' against the default ' || d || ' wape ' || ROUND(champion, 4) || ', beyond the tolerance';
  END IF;
  RETURN v || ' wape ' || ROUND(candidate, 4) || ' against the default ' || d || ' wape ' || ROUND(champion, 4) || ', passes';
END;
$$;
