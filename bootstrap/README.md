# bootstrap

What has to exist before the pipeline runs for the first time, in the order it has to be created. Names follow the
`<domain>-<purpose>-<region>-<type>` pattern of the data platform's Azure resources and are proposals to confirm with
the platform team; the Azure DevOps names are the ones `azure-pipelines.yml` expects, change both together. The
governance repository's own bootstrap (`LuckData-IaC-Snowflake-Horizon/bootstrap/README.md`) runs first; it creates
the databases, roles, pool and warehouse this pipeline uses.

1. **User-assigned managed identities** `data-snowflakemlops-eus2-dev-mi`, `-test-mi`, `-prod-mi` in the data
   platform resource group. Reader on that group, nothing else in Azure.
2. **Service connections** `LuckData-Snowflake-MLOps-dev`, `-test`, `-prod` in the Azure DevOps project. Azure
   Resource Manager, workload identity federation, manual. The first page of each dialog shows an issuer and a
   subject identifier. Copy both.
3. **Federated credentials** on each identity, from the infrastructure repository or the portal. Issuer and subject
   identifier from step 2, audience `api://AzureADTokenExchange`.
4. **Finish the service connections.** Subscription id and name, tenant id, and each identity's client id as the
   service principal id. Verify.
5. **Environments** `LuckData-Snowflake-MLOps-dev`, `-test`, `-prod`. An approval check on prod with the people who
   may approve a production model.
6. **Pipeline** `LuckData-Snowflake-MLOps` from `azure-pipelines.yml`, authorized on the three service connections and
   the three environments, with the variables `serviceConnectionDev`, `serviceConnectionTest`,
   `serviceConnectionProd` (the connection names), `snowflakeAccount` (`<org>-<account>`) and `agentPool` (a Linux pool
   whose agents have Python 3.12).
7. **Account identifier** in `dcm/manifest.yml` and `features/manifest.yml`: every target names the account the
   pipeline deploys to, `<org>-<account>`, the same value as the `snowflakeAccount` variable. One account with three
   databases today; if an environment moves to its own account, its target changes here.
8. **Branch policy** on `main` with this pipeline as a build validation, so a pull request runs `Validate`.
9. **Service users.** In `LuckData-IaC-Snowflake-Horizon`, declare `SVC_MLOPS_DEV`, `SVC_MLOPS_TEST` and
   `SVC_MLOPS_PROD` in `environments/account/config/service_users.yaml`, `TYPE = SERVICE`, default role
   `RBAC_ML_DEPLOYER_<ENV>`, default warehouse `ML_WH`, workload identity `OIDC` with the issuer and subject from
   step 2 and the audiences `fb60f99c-7a34-4190-8149-302f77469936` and `api://AzureADTokenExchange`. Its pipeline
   creates them.
10. **First run** of the pipeline on `main`. `Validate` and `Dev` run, `Test` follows, `Prod` after its approval.
