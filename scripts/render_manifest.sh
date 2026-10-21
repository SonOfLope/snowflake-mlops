#!/usr/bin/env bash
# Writes dcm/manifest.yml and features/manifest.yml from their templates with the account of the active
# connection. SNOWFLAKE_ACCOUNT is set by the pipeline; locally export it before running.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SNOWFLAKE_ACCOUNT:?set SNOWFLAKE_ACCOUNT to the account identifier, for example ORG-ACCOUNT}"
for d in dcm features; do
  sed "s/\${SNOWFLAKE_ACCOUNT}/${SNOWFLAKE_ACCOUNT}/g" "$d/manifest.template.yml" > "$d/manifest.yml"
done
echo "dcm/manifest.yml and features/manifest.yml rendered for ${SNOWFLAKE_ACCOUNT}"
