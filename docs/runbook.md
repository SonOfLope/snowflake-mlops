# Runbook

What to do when a run stops. In every case the environment's default version is unchanged: nothing is promoted until every check in that environment passed, and a failure in test or prod never touches the other environments.

Where to look first:

- The pipeline run's step log, which prints the job's own output.
- `<ENV>_ML_DB.WORKSPACE.RUN_LOG`: one row per train, forecast, gate and promote, with the verdict or the error in `METRICS`.
- Snowsight, Monitoring, Task History, for a monthly graph run.
- Snowsight, the object's Data Quality tab, for an expectation.

## The regression gate fails in test but passed in dev

The same code trained on test data produced a challenger worse than test's default by more than `regression_tolerance`. The code is not the problem, dev proved it trains and passes there; the difference is the data or the champion.

1. Read the verdict. The gate step log and `RUN_LOG` (`STAGE = 'gate'`) carry the line `FAIL V<build> wape 0.25 against the default V<n> wape 0.19, beyond the tolerance`.
2. Compare the two versions' held-out metrics, both trained on test data: `METRICS` of their training rows in `RUN_LOG`, or the version's Overview in Snowsight. A large `bias` points at a feature change; a `p90_ape` jump points at a few sites.
3. Open `notebooks/regression_eda.ipynb` in the Workspace with the environment and the two versions; it does steps 2 and 3 in depth, site by site and month by month.
4. Compare the data dev and test trained on: months present, rows per month, the newest month. At Luck, test is a refreshed clone of prod and dev may lag; a stale source on either side explains most differences.
5. Decide:
   - **Data was wrong.** Fix the source, then run the pipeline again from `main` (a rerun of the failed stage reuses the version already trained and fails the same way; a new run trains a new one).
   - **The change is worse on test data.** It does not ship. Revert or improve it and open a new pull request. Dev's default already moved to the challenger; that is dev, and it moves again with the next one.
   - **Marginal loss on a small holdout.** Three months by a few sites is noise-prone. Do not loosen the tolerance for one change; widen `eval_months` if the window is too short.

## A data expectation fails

`snow dcm test` after a deploy, or `MONTHLY_CHECK_DATA` in the graph, named an expectation. Nothing trained.

| Expectation | Likely cause | Fix |
|---|---|---|
| `PREVIOUS_MONTH_PRESENT` | the source has not loaded the previous month yet, or the schedule ran before the close | wait for the load, or move `cycle_schedule`; the actuals refresh picks the month up at the next run |
| `ENOUGH_HISTORY` | sites dropped from the source, or a new environment with little data | fix the source; lower `min_source_rows` in the manifest only for a small environment |
| `NO_NULL_TONNES`, `NO_NEGATIVE_TONNES`, `ONE_ROW_PER_SITE_MONTH` | a defect in the fact table | fix it where the fact is built, in `LuckData-Snowflake`; never patch it in the ML database |
| `NO_NULL_FORECAST`, `ONE_ROW_PER_VERSION_SITE_MONTH` | a bug in the forecast job, or rows of an old version | fix the job through a pull request; delete the offending version's rows |

Then run again: the pipeline from `main`, or the graph by executing its root task, `EXECUTE TASK <ENV>_ML_DB.WORKSPACE.MONTHLY_START`, as a role that owns it. Until the alert exists, nobody is told when a graph task fails; check Task History after the third of the month.

## The monitor shows drift

Each drift chart on a version's Monitoring tab has one point per 30-day window, the distance between that window's values and the version's training rows; drift is a point well above the ones before it. It is computed the day the forecast is written, so it is the first chart to react when a month looks unlike training. In order: the count charts (a site missing from the source moves every distance), the data expectations on `SRC_SITE_MONTH` for that month, then the same month a year earlier on the same chart, since tonnes are seasonal and a yearly movement is not drift. A departure that holds for two windows is a reason to train a challenger before the monthly cycle does, a run queued with `retrainProd` set; the regression gate decides whether it replaces the default.

## Roll the default back

`ALTER MODEL <ENV>_ML_DB.MODELS.SITE_TONNES_FORECAST SET DEFAULT_VERSION = <previous>;` as the environment's deployer, through the pipeline or an administrator. The previous version's forecast rows and monitor are still there, since the retire step keeps the newest versions.
