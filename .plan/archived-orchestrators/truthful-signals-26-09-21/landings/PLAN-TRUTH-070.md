# Landing Analysis: PLAN-TRUTH-070 — runtime edge paths that crash or silently lose data

epic: truthful-signals
workstream: WS-01
pr: #1132 — merged as `ff4462148`

> Written from the operator's paste plus the plan's own landing message
> (`runtime-edge-paths-…-011`), with the material claims corroborated first-party.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as `ff4462148` | corroborated | `git log origin/main` — `ff4462148 fix: repair 6 runtime edge-path defects, retire lstrip('./') sweep (#1132)` |
| Plan archived, worktree removed | corroborated | absent from `manage-status list` |
| Registry-pin trap re-armed | **corroborated as to the trap, CONTRADICTED as to the numbers** | see § The pin, below |
| Messages 012/013 belong to `review-apparatus` | corroborated and **actioned** | both carry `likely_epic=review-apparatus` in their own envelope headers; transferred as `truthful-signals-027` |

## Deliverable Fidelity vs Spec

All five shipped. The two findings worth keeping are not in the deliverable list.

| Deliverable | Verdict |
|---|---|
| D1 two silent-wrong-result defects in core helpers (R5 `get_metadata_content_split`, R6 bulk-resolve erasing `resolution_detail`) | shipped-as-specified |
| D2 `compute_total_elapsed` timezone-mismatch crash (R7) | shipped-as-specified |
| D3 `Retry-After` crash + missing password guard (R2, R3) | shipped-as-specified |
| D4 retire the prefix-strip idiom | **shipped-corrected — the spec's population was wrong** |
| D5 population-derived source-tree guard | shipped-as-specified (409 files scanned, 3 offenders named) |

### ⭐⭐ The spec was wrong and its own instruction is what caught it

The spec asserted `plugin_discover.py`'s six `lstrip('./')` sites *"are now gone"* and carried the
HYPOTHESIS that a sweep would find nothing further. **The real D4 population was 9 sites across 3 files,
not 3 across 2** — `_cmd_manage.py`, `plugin_discover.py` (**not** clean, contrary to the spec's
re-verified-at-HEAD claim), and `opencode/emitter.py`.

⇒ **The spec's re-verification was stale, and the spec's own standing instruction — *"population-derive
the sweep; do not fix the three known sites and call the class closed"* — is what made the discrepancy
visible.** A rule this epic wrote caught an error this epic made. That is the strongest possible
evidence for the population-derived-detector rule, and it is worth more than the six fixes.

### ⭐⭐ Two independent read-only reviews softened a severity by REASONING instead of EXECUTING

Both phase-2-refine and phase-3-outline recorded a correction to R10: that the collapsed empty string
*"currently fails safe to `False`"* at its one call site. **Executing the pre-fix source refuted it.**
`_is_marketplace_bundle_module('../marketplace/bundles/foo')` returned **`True`** pre-fix — and so did
the embedded `marketplace/bundles/../../etc/foo`. **It fails OPEN**, mis-classifying traversal paths as
in-bundle.

⛔ **Two review passes, independently, moved a severity in the safe direction by reading a call site
rather than running it.** ⭐ **The operator's pre-fix-proof call is what caught it** — the requirement
was not merely that tests be red before green (8 red + 10 red, with 15,233/18,040 other tests passing),
it was that the *pre-fix behaviour be observed*. **A red test proves a test fails; executing the pre-fix
source proves what the code does.** Those are different claims and only the second refuted the
softening. Carried as finding `eb608d`.

## Routing and Merge Behavior

⛔⛔ **THE REVIEW BARRIER WAS NOT SATISFIED — THIS LANDING IS CI-VERIFIED, NOT BOT-REVIEWED.**

The merge proceeded under an explicit operator authorization recorded as
`merge_authorizations.barrier-ask-override` (`gap_class: review-barrier-gap`, granted
2026-08-09T19:39:45Z at HEAD `cbb184c9d`), over `participation_complete=false` with
`unproven_bots=[pr-agent, coderabbit, sourcery]` — `pr-agent=participated_stale`,
`coderabbit=refused_awaitable`, `sourcery=refused_hard`. **No reviewer produced an actionable comment on
this diff.** The configured disposition was `fail_into_loopback`, so this was a **deliberate operator
departure from standing config**, not the configured ask path.

⭐ **Recorded exactly as the plan asked**: read this landing as CI-and-local-gates verified, **not** as
reviewed. ⚠ **Fourth consecutive plan** where the required-bot quorum was satisfied by a bot that found
nothing or by an override — #1122, #1123, #1125, #1132. Routed to `review-apparatus` (`-027`).

**Green where it was green:** CI across 13 checks including whole-tree `verify` at the merged HEAD;
`plugin-doctor` clean over 31 rules; pre-submission self-review clean over 56 candidates; every
regression test verified red-before-green.

**Three gates did real work rather than rubber-stamping**, and this is worth recording against the
finalize-cost question: `simplify` found dead code **the plan itself had introduced** (R10 left
`project_path` unread, and the new test added a constant purely to feed it); self-review verified a
**falsifiable** claim — that R2 was not implemented by widening the outer `except`, which matters
because `json.JSONDecodeError` subclasses `ValueError`; and the pre-merge barrier caught the
participation verdict flipping `true → false` at an unchanged HEAD.

## Metrics

3.3M tokens / **79.8M billing-weighted**, 3h21m worked over 9h14m wall (5h53m idle).
⚠ **Per-phase figures are RETIRED as evidence in this epic** and are not interpreted here. What the
table does show without needing the retired decomposition: **6-finalize is the largest single row on
both axes** (1.34M tokens, 37.9M billing) — consistent with #1125's 68%, and the third consecutive plan
where finalize dominates.

## ⛔ Ledger Write-Boundary — CROSSED

`PLAN-TRUTH-070`'s row was found already `shipped` with `pr: 1132` and `plan_marshall_plan_id` stamped
**before this analysis ran. I did not make those transitions**, and the plan's own report states
*"Epic row PLAN-TRUTH-070 → shipped, PR 1132"* as a completed action.

- **No sanctioned writer exists**: a search of `phase-6-finalize/**` and `.claude/skills/**` for
  `orchestrator queue`, `--set-row`, or `--transition` returns **nothing**. So this was not a finalize
  step doing its job.
- **The write was incomplete in the diagnostic way**: `landing` was left empty, which is exactly the
  `(!) missing:` gap the START-HERE completeness marker exists to surface. **A partial reconciliation is
  the failure mode the boundary prevents** — the row reads settled while the analysis that would have
  produced the landing record had not happened.
- ⚠ **Alternative not excluded**: the operator may have stamped it by hand. Recorded as a boundary
  crossing of unestablished authorship rather than as an accusation.

⇒ Recorded as an Open Defect. The ledger write-boundary is what the entire inbox channel exists to
enforce; a plan that writes the row it is supposed to *message about* removes the orchestrator's
verification step — and here that step is the one that found the four items above.

## Residue — the six findings carried NOWHERE ELSE

Nine findings remained `pending` and do not survive the plan directory. Three were carried as separate
messages; **these six were not, and are preserved here because this record is now their only home.**

| Hash | Component | Observation |
|---|---|---|
| `f2543e` | `workflow-integration-git` | `prune-local-and-remote-ref` errors on the branch `worktree-remove` already deleted, **then aborts before the remote-ref prune** — a stale `origin/` ref survived and needed a manual `git update-ref -d`. ⭐ An abort-midway after a partial success, the shape the pin-repair script had to be split to avoid |
| `d0cd33` | `build-pyproject` | whole-tree `module-tests` (642s) exceeds its learned daemon timeout **while the superset `verify` completes in 215–537s** — the subset times out and the superset does not |
| `3ae562` | `manage-build-server` | the daemon interaction-audit log holds **none** of this session's ~15 builds, yet reports `count: 17` **as a complete answer**. ⭐ Textbook: a count with no population, over a log that is missing its content |
| `866492` | `phase-6-finalize` | the PR intent-section budget truncates the **tail**, and the tail is the **non-goals** — the one section whose absence generates false review findings. ⭐ **Second independent report** of this (the first was delegated as `truthful-signals-026`), and it sits in `phase-6-finalize` itself |
| `045711` | `manage-providers` | `Retry-After` delta-seconds honoured verbatim with **no upper clamp** — deliberately NOT fixed here (a contract change, and a test pins current behaviour) |
| `1d3916` | `manage-solution-outline` | `get-module-context` unusable at phase-3 for any `use_worktree=true` plan *(carried separately as a `finding`, listed for completeness)* |

⚠ Three of these — `f2543e`, `3ae562`, `866492` — are **defects in plan-marshall's own finalize
machinery, observed while finalizing**, and `866492` is inside `phase-6-finalize` itself.

## Reconciliation Actions

- [x] row `status` → `shipped` *(pre-existing; see § Ledger Write-Boundary)*
- [x] row `pr` = `1132` *(pre-existing)*
- [x] row `plan_marshall_plan_id` *(pre-existing)*
- [x] row `landing` stamped — `landings/PLAN-TRUTH-070.md` *(the missing third stamp)*
- [x] messages 012/013 transferred to `review-apparatus` as `truthful-signals-027`
- [x] Open Defects opened: ledger write-boundary crossing; the six orphaned residue findings
- [x] **PLAN-TRUTH-071 re-scoped** — see Follow-Ups

## Follow-Ups

1. ⛔ **PLAN-TRUTH-071's `lstrip` deliverable is ALREADY SATISFIED by this landing.** The
   `opencode/emitter.py` overlap was carried here rather than handed off. **Re-scope -071 before
   emitting it** — a plan whose deliverable already shipped will either no-op or re-do settled work, and
   the D5 guard now fails the build if it is re-introduced.
2. **The pin.** See below — the trap is armed, but not in the shape the report states.
3. **The inbox is NOT drained** and deliberately so — three plans are at 6-finalize and may still be
   emitting. Draining now would re-run the #1122 hazard.
