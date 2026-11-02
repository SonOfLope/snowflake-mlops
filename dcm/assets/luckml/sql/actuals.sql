-- Writes the actual tonnes onto every model's forecast rows once the month exists in the source view. Variables: db, schema.
UPDATE <% db %>.<% schema %>.SITE_MONTH_FORECAST f
SET ACTUAL_TONNES = s.TONNES
FROM <% db %>.WORKSPACE.SRC_SITE_MONTH s
WHERE s.SITE_ID = f.SITE_ID AND TO_TIMESTAMP_NTZ(s.MONTH) = f.MONTH AND f.ACTUAL_TONNES IS NULL;
