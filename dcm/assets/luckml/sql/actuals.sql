-- Writes the actual tonnes onto every version's forecast rows once the month exists in the source view. Variables: db.
UPDATE <% db %>.WORKSPACE.FORECAST_SITE_MONTH f
SET ACTUAL_TONNES = s.TONNES
FROM <% db %>.WORKSPACE.SRC_SITE_MONTH s
WHERE s.SITE_ID = f.SITE_ID AND TO_TIMESTAMP_NTZ(s.MONTH) = f.MONTH AND f.ACTUAL_TONNES IS NULL;
