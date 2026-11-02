-- Refuses a candidate whose MAPE on the months with actuals is worse than the default version's by more than the tolerance.
-- Variables: db, version, tolerance (a fraction, 0.10 allows ten percent worse).
EXECUTE IMMEDIATE $$
DECLARE
  v STRING DEFAULT '<% version %>';
  d STRING;
  candidate FLOAT;
  champion FLOAT;
  regression EXCEPTION (-20001, 'the candidate is worse than the default version beyond the tolerance');
BEGIN
  SHOW VERSIONS IN MODEL <% db %>.MODELS.SITE_TONNES_FORECAST;
  SELECT "name" INTO :d FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "is_default_version" = TRUE;
  IF (d IS NULL OR d = v) THEN
    RETURN 'no default to compare, ' || v || ' passes';
  END IF;
  SELECT AVG(ABS(FORECAST_TONNES - ACTUAL_TONNES) / ACTUAL_TONNES) INTO :candidate
    FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH
    WHERE MODEL_VERSION = :v AND ACTUAL_TONNES > 0;
  SELECT AVG(ABS(c.FORECAST_TONNES - c.ACTUAL_TONNES) / c.ACTUAL_TONNES) INTO :champion
    FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH c
    JOIN <% db %>.WORKSPACE.FORECAST_SITE_MONTH n ON n.ROW_ID = c.ROW_ID AND n.MODEL_VERSION = :v AND n.ACTUAL_TONNES > 0
    WHERE c.MODEL_VERSION = :d AND c.ACTUAL_TONNES > 0;
  IF (candidate IS NULL OR champion IS NULL) THEN
    RETURN 'no common scored months between ' || v || ' and the default ' || d || ', ' || v || ' passes';
  END IF;
  IF (candidate > champion * (1 + <% tolerance %>)) THEN
    RAISE regression;
  END IF;
  RETURN v || ' mape ' || ROUND(candidate, 4) || ' against the default ' || d || ' mape ' || ROUND(champion, 4) || ', passes';
END;
$$;
