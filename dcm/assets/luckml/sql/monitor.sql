-- One monitor per promoted version, over a view of that version's rows, with a snapshot of the version's training rows as
-- the baseline for drift (a monitor clones its baseline, so it is a table). Variables: db, version, wh.
CREATE OR REPLACE VIEW <% db %>.WORKSPACE.FORECAST_<% version %> AS
  SELECT * FROM <% db %>.WORKSPACE.FORECAST_SITE_MONTH WHERE MODEL_VERSION = '<% version %>';

CREATE OR REPLACE TABLE <% db %>.WORKSPACE.BASELINE_<% version %> AS
  SELECT * FROM <% db %>.WORKSPACE.BASELINE_SITE_MONTH WHERE MODEL_VERSION = '<% version %>';

CREATE MODEL MONITOR IF NOT EXISTS <% db %>.MODELS.SITE_TONNES_FORECAST_<% version %>_MON
WITH
  MODEL = <% db %>.MODELS.SITE_TONNES_FORECAST
  VERSION = <% version %>
  FUNCTION = predict
  SOURCE = <% db %>.WORKSPACE.FORECAST_<% version %>
  BASELINE = <% db %>.WORKSPACE.BASELINE_<% version %>
  WAREHOUSE = <% wh %>
  REFRESH_INTERVAL = '1 day'
  AGGREGATION_WINDOW = '30 days'
  TIMESTAMP_COLUMN = MONTH
  ID_COLUMNS = ('ROW_ID')
  PREDICTION_SCORE_COLUMNS = ('FORECAST_TONNES')
  ACTUAL_SCORE_COLUMNS = ('ACTUAL_TONNES');
