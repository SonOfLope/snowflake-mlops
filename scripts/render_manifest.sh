#!/usr/bin/env bash
# Writes features/manifest.yml from the template with the account of the active connection.
# SNOWFLAKE_ACCOUNT is set by the pipeline; locally export it before running.
set -euo pipefail
cd "$(dirname "$0")/../features"
: "${SNOWFLAKE_ACCOUNT:?set SNOWFLAKE_ACCOUNT to the account identifier, for example ORG-ACCOUNT}"
sed "s/\${SNOWFLAKE_ACCOUNT}/${SNOWFLAKE_ACCOUNT}/g" manifest.template.yml > manifest.yml
echo "features/manifest.yml rendered for ${SNOWFLAKE_ACCOUNT}"
