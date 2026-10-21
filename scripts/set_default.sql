-- Makes one version the default, the one production code calls. Variables: db, version.
ALTER MODEL <% db %>.MODELS.SITE_TONNES_FORECAST SET DEFAULT_VERSION = <% version %>;
