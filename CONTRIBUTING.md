# Contributing

Work happens on a branch, in a Snowsight Workspace opened from this repository, and reaches an environment only through the pipeline.

## Set up once

1. In Snowsight, Projects, Workspaces, From Git repository. Repository URL: this repository in Azure DevOps. Credentials: the Git API integration and secret from `bootstrap/README.md` step 8. Role `FR_AI_ENGINEER`.
2. In the Workspace, create a branch named after the change. Never work on `main`.
3. Session context: role `FR_AI_ENGINEER`, warehouse `ML_WH`, database `DEV_ML_DB`, schema `WORKSPACE`.

## Change the model, the features or the objects

1. Experiment in a notebook in the Workspace. Read `DEV_ML_DB.FEATURES.SITE_MONTHLY_TONNES$1`. Log trial versions to `DEV_ML_DB.MODELS.SITE_TONNES_FORECAST` with a `VEXP_` prefix. Compare them under AI and ML, Models. Nothing a notebook creates leaves dev.
2. Put the change where the pipeline reads it. Model and jobs in `src/luckml` and `jobs`, features in `features/sources` (see `features/README.md`), `WORKSPACE` objects in `dcm/sources/definitions`, per-environment values in `config`.
3. Run `pytest -q` and `ruff check .` in the Workspace terminal or locally.
4. Commit and push the branch from the Workspace.
5. Open the pull request in Azure DevOps. The branch policy runs `Validate`: lint, tests, `snow dcm plan` and `snow feature plan` against dev. Read the plans in the run before asking for review.
6. After the merge the pipeline trains in dev, promotes to test, and to prod after the approval.

## Rules

- No secret, account identifier or environment literal in code. Environment values live in `config/<env>.yml` and the two manifests.
- A version is named by the pipeline, `V<build id>`. Trial versions carry the `VEXP_` prefix.
- A change to a feature view that alters its columns is a new feature view version.
- `main` is protected. Pull requests only.
