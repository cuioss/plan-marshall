# Settled Narrative — lessons-routing

Closed-subject content relocated verbatim out of `epic.md` by the `cleanup` verb's ledger-compaction
stage (Phase B). Each section below was live narrative about a subject that has since closed; each
carries a pointer back in `epic.md` naming this section's heading in double quotes. Relocated verbatim
— nothing here is re-derived or summarized.

## Lesson Sweeps — 2026-09-22

Relocated from `epic.md` § "Lesson Sweeps" (2026-09-24, `cleanup`, operator-confirmed).

### 2026-09-22 — full corpus sweep (inlined from the retired `lessons-handling-26-09-22-01`)

Opened as a separate dated epic under the then-current model, closed the same day once the operator
ruled `lessons-routing` is always the orchestrator used; its record is inlined here verbatim and its
tree removed.

**Scan.** `manage-lessons list` → 45 total (44 active + 1 pre-existing `superseded` stub, unrelated).
`manage-lessons aggregate` clustered the 44 active into 10 shared-component/cross-ref groups (31
lessons) + 9 standalones (40 parseable) + 4 unresolvable (unparseable metadata header, all from plan
`tracked-orchestrator-store-resolver`, hand-authored directly into files rather than filed via
`manage-lessons add`).

**Ground-truth check.** Spot-checked the one claim closest to a known precedent: `2026-09-21-13-003`
(manage-lessons `set-body` destroys the metadata header `add` wrote) against the just-shipped
`PLAN-TRUTH-144`/PR#1560 (`05b5d1ac4`) — that fix touched `manage-lessons.py`, `_lessons_io.py`,
`_lessons_query.py` for `add`/`remove`/resolution only; `cmd_set_body` was untouched. Still live,
routed as-is. All 44 were 2026-08-24 through 2026-09-21 vintage, most from one recent retrospective
sweep.

⛔⛔ **CORRECTION (2026-09-22, via `truthful-signals`' own inbox forward, drained below): "no lesson found
already-covered" was FALSE for at least 7 of the 44, and possibly 11.** `truthful-signals` had itself
promoted 11 lessons into the corpus the day before (`2026-09-21-10-002`..`-012`, from its own 2026-09-21
inbox drain). This sweep never checked a lesson's provenance against its routing destination: 7 of those
11 (`10-002,003,005,006,007,009,011`) matched `truthful-signals`' own theme and were routed BACK to it as
if new, then deleted from the corpus once queued. `truthful-signals` caught the round-trip (dates one day
apart, thematically obvious) and restored all 7 from its own archived pre-promotion messages — no
permanent loss. The other 4 in that same promoted range (`10-004`→`process-compliance`, `10-008`→
`post-run-quality`, `10-010`/`10-012`→`orchestrator-refactor`) went to DIFFERENT epics and could not
self-detect the duplication; correction notices were filed to all three. See `## Open Defects` below.

**Routing** (5 destinations, one bundled `inbox write --kind candidate-lesson` message per epic,
matched against each epic's own stated ownership scope):

| Destination | Count | Subject |
|---|--:|---|
| `truthful-signals` | 18 | confident-signal-hides-a-caveat / prose-vs-structured-fact / doc-drift patterns, incl. the 4 unresolvable-header lessons forwarded verbatim |
| `process-compliance` | 12 | finalize/worktree mechanism defects + `persona-plan-marshall-agent` foundational-conduct corrections |
| `post-run-quality` | 6 | `plan-retrospective`/metrics/findings/archived-obligation-ownership |
| `review-apparatus` | 5 | `automatic-review`/review-retrospective |
| `orchestrator-refactor` | 3 | `plan-orchestrator`'s own mechanism, per that epic's own aspect 4 |

Plus a sixth, direct `--kind finding` message to `code-intelligence-substrate`: two of the routed
lessons (`2026-09-21-08-002`, `2026-09-21-08-003`) independently surfaced the same live,
already-diagnosed bug in that epic's own `cloud-runs/_audit/analyze.py` (hardcoded developer-machine
paths, confirmed present on `origin/main`) — sent directly rather than left to surface only inside the
process-angle lessons filed to `truthful-signals`.

One candidate was rerouted mid-analysis: `2026-09-20-08-011` (orchestrator-authored specs tripping
`phase-2-refine`'s suspicious-perfect-confidence heuristic) was initially considered for
`orchestrator-refactor` (its provenance names that epic's PLAN-04) but routed to `truthful-signals`
instead — its remedy is a `phase-2-refine` heuristic-tuning question, not an orchestrator-mechanism
one; `orchestrator-refactor` independently tracks the supporting staged-spec population as its own
Watch.

**Retirement.** All 44 routed lessons removed via `manage-lessons remove --coverage-verdict superseded`
(the convention the prior `lessons-handling-26-08-26-01` epic established — `completely_covered`/
`redundant`/`obsolete` don't fit a routed-not-yet-acted-on finding), each tombstone naming its
destination epic and inbox message; the 4 unresolvable ones used `--allow-unreadable`. All 44 calls
returned success with a tombstone written — **zero destroy-without-tombstone incidents**, confirming
`PLAN-TRUTH-144`'s fix holds under load, the exact failure mode that produced this epic's own retired
`PLAN-LR-06` the same day. Also pruned the one pre-existing `superseded` stub via `cleanup-superseded`.
`.plan/local/lessons-learned/` is now empty.

⚠ **Watch carried forward**: four lessons were hand-authored directly into the corpus without a
metadata header, bypassing `manage-lessons add`. Not treated as a script defect (no evidence `add`/
`set-body` themselves are broken for this case), but if it recurs across future sweeps it may be worth
a `manage-lessons` guard against a headerless file entering the corpus at all. *(re-check: next sweep.)*

⚠ **Watch carried forward**: none of the 6 destination messages was confirmed drained by its receiving
epic in this session. *(re-check: next `status`/`cleanup` pass on any of the 5 sibling epics, or
code-intelligence-substrate.)*

## Lesson Sweeps — 2026-09-26

### 2026-09-26 — PM-MCP carry-over sweep (43 lessons; nothing routed to sibling epics)

Driven by `review-apparatus-001` (PM-MCP supersedes Python- and prose-bound plan work; § 5: "a lesson whose
remedy is a Python or prose change routes to the carry-over as a rule or fixture, not to a staged plan").
**Deviation from the lessons-handling Step 4 routing, deliberate:** every cluster's owning sibling epic has
itself parked its queue under the same ruling, so routing a cluster there would only file a message whose
plans cannot be emitted. Every cluster went to ONE destination instead:
`/Users/oliver/git/plan-marshall-mcp/doc/known-defects/lessons-routing-carry-over.md` (the full per-lesson
rows, clusters, PM-MCP mapping, contradictions). `clusters_routed: 0` (inbox), `exception_plans_staged: 0`.

Population: 43 active lessons (`manage-lessons list` at `a88626306`), 42 read, 1 unreadable. Verdicts:
**36 superseded-by-pm-mcp** (carried or dup of TS/RA carry-over), **5 legacy-blocking**, **1 stale**,
**1 unreadable**. 100 lesson rows → 57 carried (32 gap / 18 partial / 7 covered), 43 none (mostly dup of TS).

| Disposition | Lessons |
|---|---|
| clustered-into L-SET | 22-07-001, 22-07-002 |
| clustered-into L-ROSTER | 22-07-004, 22-07-006 |
| clustered-into L-VACUOUS | 22-07-007, 22-08-003, 22-08-004 |
| clustered-into L-SIBLING | 22-07-005, 22-08-002, 22-07-008 |
| clustered-into L-SC (scope_creep finding type / base) | 22-12-001 (unreadable header), 22-15-001, 23-16-001, 24-09-001 |
| clustered-into L-BASE (**legacy-blocking**) | 24-09-003, 24-12-006 |
| clustered-into L-REFIRE | 23-05-003, 23-07-001, 24-09-005, 24-09-008 |
| clustered-into L-SCOPE | 24-12-002, 24-12-003, 24-12-004, 24-12-005 |
| clustered-into L-RETRO | 23-05-001, 23-05-002, 23-05-004, 23-05-005, 23-05-007, 23-05-008 |
| standalone (**legacy-blocking**) | 24-12-001 (foreign_pr_gate ambient branch), 24-05-001 (sync-baseline rebases behind=0), 23-23-001 (local ruff isort churn) |
| standalone | 22-07-003, 22-08-001, 23-05-006, 23-07-002, 23-15-001, 24-09-004, 24-09-006, 24-09-007, 24-16-001 |
| stale | 24-12-007 (fixed forward, #1603 / cuioss-organization 0.30.0) |

(Lesson ids abbreviated: `22-07-001` = `2026-09-22-07-001`.) No lesson was removed from the corpus — removal is
destructive and awaits the operator (see Decisions 2026-09-26).

## Open Defects — superseded by PM-MCP

- ⛔⛔ **Three stranded upstream lessons exist RIGHT NOW** in `cui-jsf-test-basic` — `plan-marshall:recipe-refactor-to-profile-standards`, `plan-marshall:build-maven`, `plan-marshall:workflow-integration-sonar` — in a git-ignored directory, unread by this project. *(source: first-party sample, 2026-08-24. Owned by PLAN-LR-01 (b), routed by PLAN-LR-04.)*
- ⛔ **The `wrong_store` ownership predicate mis-classifies a client's OWN prefixed component as foreign**, because it tests for `marketplace/bundles/{prefix}` which no consumer repo has. Verified against `API-Sheriff` (`api-sheriff:maven-build`, no `marketplace/` directory). *(source: first-party, 2026-08-24. Owned by PLAN-LR-02.)*
- ⚠ **`--allow-foreign-store` is the only escape and it launders the distinction it bypasses** — a lesson filed with it is indistinguishable afterwards from a genuinely local one. *(source: first-party read of `manage-lessons/SKILL.md:108`. Owned by PLAN-LR-02.)*
- ⛔⛔ **A lesson sweep has no way to detect it is re-routing content a destination epic already owns —
  confirmed, not hypothetical.** The 2026-09-22 sweep routed 7 of `truthful-signals`' own 2026-09-21
  promotions (`2026-09-21-10-002,003,005,006,007,009,011`) back to `truthful-signals` as new candidates,
  then deleted the corpus copies once queued; 4 more from the same promoted range went to 3 OTHER epics
  undetected. Root cause: no field on a lesson records which epic (if any) already promoted/dispositioned
  it, so even a same-sender "is this a boomerang" check has no field to read. *(source: `truthful-signals`
  inbox forward, drained 2026-09-22, archived at `inbox/archive/truthful-signals/truthful-signals-002.md`.
  Not yet owned by a staged plan — candidate for a PLAN-LR-07 D6 or a new PLAN-LR-08; do not fold into
  PLAN-LR-07 while it is running, per the operator's parallel launch.)*
- ⚠ **Two consumer repos independently reached OPPOSITE conclusions about the `wrong_store` guard's
  right axis** (Token-Sheriff: refuse harder, treat the override as operator-only; API-Sheriff: file
  locally whenever THIS repo pays the recurring cost, regardless of bundle ownership) — both coherent,
  because "who can fix it" and "who keeps paying for it" are different populations a single store can
  serve only one of. Token-Sheriff's override also RECURRED after a first relocation (PLAN-08 routed
  correctly, PLAN-09 filed two more locally). *(source: `truthful-signals` inbox forward dated
  2026-09-11, drained 2026-09-22 — leads, not independently corroborated from this checkout. Owned by
  PLAN-LR-01 D1/D4 and PLAN-LR-02 D0/D1; PLAN-LR-04 should not assume one-time migration is sufficient
  given the recurrence.)*

## Watches — superseded by PM-MCP

- ⚠ **How the three stranded lessons were filed at all is UNESTABLISHED** — with `--allow-foreign-store`, or before the guard existed. The answer changes whether the guard is being routinely bypassed in practice or was simply added later. *(re-check: PLAN-LR-01 (b), which reads them.)*
- ⚠ **Cross-org issue creation permissions are unverified.** WS-02 assumes a client repo can open an issue on `cuioss/plan-marshall`. The `ci issue` surface exists, but whether a client developer's token can write to a foreign repo is not established. *(re-check: PLAN-LR-03's gate, before any transport is built.)*
- ⚠ **Consumer-repo count is unknown.** Four are named in project memory (`nifi-extensions`, `cui-jsf-test-basic`, `TokenSheriff`, `API-Sheriff`); two were sampled here. The real population bounds how much stranded corpus exists. *(re-check: PLAN-LR-01 (b).)*
