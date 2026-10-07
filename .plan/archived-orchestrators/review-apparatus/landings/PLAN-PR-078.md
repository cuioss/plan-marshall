# Landing Analysis: PLAN-PR-078 — cuioss-review-bot fleet opt-in, and removal of the legacy repo-local config

epic: review-apparatus
workstream: WS-02
pr: #1704 (host, `d42dc6a94`) plus nine foreign PRs listed below

> Landing record for one shipped plan, written by the `analyze` verb (inbox scan, 2026-10-07) from two
> landing messages: `plan-pr-078-review-bot-fleet-opt-in-001.md` (the fleet report, written at the end of
> execute, facts block incomplete) and `-011.md` (the finalize landing, complete). The facts in `-011` win;
> the per-repository table is `-001`'s. Plan id `plan-pr-078-review-bot-fleet-opt-in`.

## Verdict

**Shipped, with the rollout a little over a third done: 7 of 20 in-scope repositories carry the opt-in.**
The other 13 were deliberately not written, because their existing `.github/project.yml` fails the org
schema on keys this rollout does not touch and the spec binds "reported, never force-written". The operator
chose to fix the schema first; that follow-up is lesson `2026-10-06-15-001`.

## What was corroborated, and how

| Claim | Verdict | Evidence (read 2026-10-07) |
|---|---|---|
| Host PR #1704 merged | corroborated | `origin/main` tip `d42dc6a94` "chore(review-bot): opt in the cuioss fleet and drop legacy config (#1704)" |
| API-Sheriff #399 merged (`278e5d34`) | corroborated | `ci --project-dir … pr view --pr-number 399`: `state: merged`, same merge commit |
| TokenSheriff #782 merged (`21f56fe7`) | corroborated | same read, `state: merged` |
| cui-http #273 merged (`74739adf`) | corroborated | same read, `state: merged` |
| cui-java-module-template #156 merged (`b6d98fc7`) | corroborated | same read, `state: merged` |
| cui-open-rewrite #190 merged (`630d7920`) | corroborated | same read, `state: merged` |
| plan-marshall-mcp #33 merged (`2c8f776d`) | corroborated | same read, `state: merged` |
| playwright-test-artifacts #185 merged (`5de59d8d`) | corroborated | same read, `state: merged` |
| coderabbit #6 merged (`bf1042a4`) | corroborated | same read, `state: merged` |
| cuioss-organization #307 merged (npm release guard) | corroborated | same read, `state: merged`, `fee796fa` |
| Finalize step outcomes, token total, merge mechanism | corroborated | `manage-status read --plan-id plan-pr-078-review-bot-fleet-opt-in`: every step `done`, `merge_mechanism: merge_queue`, `merge_state: merged`, `cleanup_owed: false`, `total_tokens: 8442614` |
| Per-repository default-branch state (caller, `.pr_agent.toml`, opt-in block, packs) for the 20 repositories | **not re-read here** | the sender's 60 `ci repo file read` observations of 2026-10-06 ~17:50Z stand as its first-party report |
| Live verification on plan-marshall-mcp #34 (charter line names pack `java`) | **not re-read here** | the sender's reviewer-run log read (run 37504777427) |
| The 13 schema verdicts | **not re-read here**, and weak at the source | the sender read `schema.json` by hand; no validator ran |

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0b: guard the npm release path, release, bump the playwright pin | shipped-as-specified | cuioss-organization #307 merged, released as v0.36.0; the operator cut the release by hand (a leaf may not) |
| D0: derive and confirm the pack table | shipped-as-specified | operator-confirmed table recorded in the plan; one persisted cell (plan-marshall-mcp) is wrong per the landing's own residue |
| D1: migrate the three legacy repositories | shipped-modified | #399, #782, #273 merged; **validated on the added block only** — their whole-file schema check is still owed |
| D2: enroll the seventeen repositories | **shipped-modified: 4 of 17** | #156, #190, #33, #185 merged; 13 deferred unwritten on the org schema |
| D3: fix the stale reference in `cuioss/coderabbit` | shipped-as-specified | coderabbit #6 merged |
| D4: verify the rollout live per repository | **shipped-modified: 1 of 7** | plan-marshall-mcp live-verified; the other six reported `unverified` with a reason each, as the spec requires |
| D5: the final report | shipped-as-specified | message `-001` states its population and lists every repository's end state |
| added-unplanned: `ci checks logs --scope --match --job` in plan-marshall | added-unplanned | the host diff of #1704 (14 files); the spec declared **no** plan-marshall file |

The landing's `deliverables_done=10` of 10 counts closed tasks, not full outcomes; the table above is the
outcome reading.

## The 13 deferred repositories

cui-core-ui-model, cui-jsf-components, cui-portal-ui, cui-java-tools, cui-jsf-test-basic, cui-portal-core,
cui-reference-documentation, cui-test-keycloak-integration, nifi-extensions, cui-test-generator,
cui-test-juli-logger, cui-test-mockwebserver-junit5, cui-test-value-objects.

Two schema causes, per the sender: `github-automation.auto-merge-build-timeout` is not a schema property,
and two-part versions (`2.7-SNAPSHOT`) fail the three-part pattern. The confirmed packs per repository are
in message `-001`.

## Metrics and Anomalies

- Tokens: 8.44M against a 2.5M anchor. Finalize (3.50M) cost more than execute (2.86M).
- Duration: 114,951 s wall (about 32 h), including operator waits.
- Anomalies:
  - `pre-submission-self-review` did not converge: three loop-back rounds (2, 4, 6 findings, all doc
    contract drift), closed by the operator; `acceptance=accepted`, `may_close=no`. Each loop-back re-fired
    simplify (5 firings), lessons-housekeeping (3) and plugin-doctor (3).
  - One execute dispatch is recorded `harness_cancellation` with zero tokens although it worked for over
    half an hour; five more are recorded `voluntary_checkpoint` where the leaf was blocked on the operator.
  - The worktree executor went stale mid-plan (new `ci checks logs` flags rejected) and had to be regenerated.
  - The release cut was refused inside the leaf as a production deploy and done by the operator.

## Routing and Merge Behavior

- Review: only CodeRabbit left records that could be judged on #1704 (3 real defects, fixed in `f80ed122b`
  before merge). cuioss-review-bot and Sourcery left none; the store shows neither that they reviewed nor
  that they did not. On the second pass the completion poll ended with CodeRabbit still `in_progress`. The
  three "fixed" replies were posted about 25 minutes before the fix commit existed.
- CI/merge: all checks green; merged through the merge queue; branch cleanup complete, nothing owed.
- Surface: the spec declared no plan-marshall file and the host PR touched 14. No other row of this epic is
  live, so nothing collided.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `#1704`
- [x] row `landing` stamped `landings/PLAN-PR-078.md`
- [x] row `plan_marshall_plan_id` stamped `plan-pr-078-review-bot-fleet-opt-in`
- [x] epic.md Open Defects and Watches reconciled (2026-10-07 entries)
- [x] resume anchor updated, `queue-view.md` regenerated

## Follow-Ups

- **The 13 unenrolled repositories, the whole-file re-validation of the three migrated ones, and a runnable
  validator** — already tracked as lesson `2026-10-06-15-001`; not staged a second time here.
- **Six enrolled repositories unverified live** (API-Sheriff, TokenSheriff, cui-http,
  cui-java-module-template, cui-open-rewrite, playwright-test-artifacts) — Watch in `epic.md`.
- **Nine candidate lessons** from the plan retrospective (`-002` … `-010`) — promoted to the lessons corpus.
- **Small open items the plan named and did not fix** — Watch in `epic.md`: the `job_not_found` edge case in
  `_github_ci.py`; the wrong plan-marshall-mcp cell in the persisted pack table; leftover local
  `feature/plan-pr-078-review-bot-fleet-opt-in` branches in the foreign checkouts; the unestablished state
  of coderabbit's v0.36.0 pin-bump PR; why both reviewer jobs were skipped on API-Sheriff #400.
