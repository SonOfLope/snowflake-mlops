-- Makes one version the default, the one production code calls. Variables: db, model, version.
ALTER MODEL <% db %>.MODELS.<% model %> SET DEFAULT_VERSION = <% version %>;
