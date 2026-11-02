-- One monitor per promoted version, over a view of that version's rows, with a snapshot of the version's training rows as
-- the baseline for drift (a monitor clones its baseline, so it is a table). Variables: db, schema, model, version, wh.
CREATE OR REPLACE VIEW <% db %>.<% schema %>.<% model %>_<% version %> AS
  SELECT * FROM <% db %>.<% schema %>.SITE_MONTH_FORECAST WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>';

CREATE OR REPLACE TABLE <% db %>.<% schema %>.<% model %>_<% version %>_BASELINE AS
  SELECT * FROM <% db %>.<% schema %>.SITE_MONTH_BASELINE WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>';

CREATE MODEL MONITOR IF NOT EXISTS <% db %>.MODELS.<% model %>_<% version %>_MON
WITH
  MODEL = <% db %>.MODELS.<% model %>
  VERSION = <% version %>
  FUNCTION = predict
  SOURCE = <% db %>.<% schema %>.<% model %>_<% version %>
  BASELINE = <% db %>.<% schema %>.<% model %>_<% version %>_BASELINE
  WAREHOUSE = <% wh %>
  REFRESH_INTERVAL = '1 day'
  AGGREGATION_WINDOW = '30 days'
  TIMESTAMP_COLUMN = MONTH
  ID_COLUMNS = ('ROW_ID')
  PREDICTION_SCORE_COLUMNS = ('FORECAST_TONNES')
  ACTUAL_SCORE_COLUMNS = ('ACTUAL_TONNES');
