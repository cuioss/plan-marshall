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
