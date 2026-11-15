envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-07T16:39:12Z

# Low-severity findings and open recurrences (api-sheriff-0-2-0 close-out, 2026-11-07)

Final hand-off from the `api-sheriff-0-2-0` close-out. Three low findings not yet in lessons-routing, and two recurrences of items plan-marshall already holds, sent so the backlog knows they are still live.

## 1. The `landing-facts` step list is ambiguous (emit-landing format) — LOW

Five landings (PLAN-V02-07, -48, -49, -50, -51) parse the finalize step list "with a last-colon split" because step ids such as `default:branch-cleanup` contain the separator used for the outcome. Every consumer has to know the workaround. **Ask:** emit the step list as structured rows (`step`, `outcome`) or use a separator that cannot occur in a step id. Related fix on the plan-marshall side: live-blockers PLAN-LB-107 (namespaced step keys lost in a TOON status read).

## 2. The finalize architecture refresh misses a stale project description (manage-architecture refresh / marshall-steward) — LOW

After nine of twelve `doc/plan/` files were deleted (PLAN-V02-03, then all of them in PLAN-V02-18), `.plan/project-architecture/_project.json` and `documentation/enriched.json` still describe "remaining implementation plans under doc/plan/" (and, since 2026-11-07, a retired quality report). The finalize architecture refresh reported no structural change and did not rewrite them; only `/marshall-steward` regenerates them. **Ask:** the refresh flags descriptor text that cites paths that no longer exist.

## 3. Config staleness has no prompt (marshall-steward staleness signalling) — LOW, optional

`marshal.json` stayed stale against the executor or plugin for most of api-sheriff-0-2-0 (0.1.1916 vs 0.1.1924; 0.1.1986 vs 0.1.2036 at close-out); the remedy is always "operator runs `/marshall-steward`", tracked by hand as an epic Watch for weeks. The executor-skew half is already routed (`as-023`, `as-067`, `lr-007`, `lr-010`); only the config half is open, and it may be by design.

## Recurrence A — no CI verb reads a `main` run by merge commit (`tools-integration-ci`)

Still open at plan-marshall HEAD: `ci checks status` takes only `--pr-number` / `--head`. Delivered pre-lessons-routing as truthful-signals `api-sheriff-deployment-configurability-013`, folded into PLAN-TRUTH-150 (parked) and carried into live-blockers `backlog.md` § 2.7 "CI abstraction gaps". api-sheriff-0-2-0 owed the post-merge `deploy-snapshot` check on every landing it could not read through the abstraction (inherited constraint (16+20)). Sent as a recurrence so § 2.7 carries a current data point.

## Recurrence B — `module-tests` DEGRADED at whole-tree scope after the zero-bundle fix (pre-push gate in a Maven reactor)

PLAN-V02-52 (api-sheriff-0-2-0, #554, 2026-11-01): `module-tests` ran DEGRADED at whole-tree scope after #1866 fixed the zero-bundle half (class `as-005` / `as-022` / `as-037` / `as-065`; INDEX "the zero-bundle half is fixed by #1866"). Unrouted recurrences of the same class also occurred on V02-14, -19, -21, -26. Evidence that the module-tests half is still live.
