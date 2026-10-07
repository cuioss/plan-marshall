# Run report — 180-finalize-dispatch-manifest-observability (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/finalize-dispatch-manifest-observability-nrxcwr` (harness-assigned; kept as-is)    **PR:** [#1232](https://github.com/cuioss/plan-marshall/pull/1232)    **Outcome:** completed (conditions 1–3 met, 1-of-3 review shortfall disclosed, auto-merge armed; landing delegated to the merge queue)

## Skills loaded

- `cloud-plan-lane` (first action, governs the run).
- `plan-marshall:ref-code-quality` (read by bundle path).
- `pm-plugin-development:plugin-script-architecture` (read by bundle path).

The plan's surface is `phase-6-finalize`/`manage-status` scripts + workflow docs + tests. The
implementation worked directly against the concrete source (`_cmd_effort.py`, `_cmd_mark_step.py`, the
finalize `SKILL.md`, the roster doc, and the tests) whose contracts the two always-load skills govern;
no additional bundle skill needed loading beyond reading those source files directly. Both plugin
notations were unavailable (plugin cache absent, as the lane anticipates) and were read by bundle
path.

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Ordering constraint (Notes) — re-derived from the clone

The plan carries a hard ordering constraint: (1) the sibling audit plan (170) runs FIRST; (2) the
other epic's roster correction lands before D6. Both re-derived from the clone rather than trusted:

- **Sibling audit (plan 170) LANDED.** `c93431f fix(plan-retrospective): make the dispatch audit
  deterministic and fail-able (#1225)` is on `origin/main`. The dispatch audit is now a deterministic,
  fail-able detector (`check-dispatch-audit.py`), so this plan can measure its own divergence.
- **Roster correction LANDED.** The roster (`dispatch-inline-split.md`) already classifies
  `default:architecture-refresh` as **inline** (agreeing with its standards doc's inline
  self-classification), and `test_dispatch_roster_closure.py` check (f) already enforces that
  agreement with a mutation guard reproducing the pre-fix (dispatched-roster) shape. The
  architecture-refresh classification divergence is already corrected at HEAD.
- **Seam producer LANDED.** `1da26b1 fix(dispatch-audit): emit the dispatch record from the
  resolve-target seam, per firing (#1200)` wired `_cmd_effort.py::_emit_dispatch_records`, which emits
  `[DISPATCH]` (work-log) + the decision-log record per-firing when `effort resolve-target` is passed
  `--workflow`. Plan 170's report Residue explicitly names "the sibling emission plan" (this plan) as
  owner of migrating finalize resolves to that seam.

## Deliverables

### D1 — GATE: map the observability seams (mutates nothing)

Each defect confirmed or refuted at its own site at HEAD. Split re-evaluated at outline: proceeding
unsplit is upheld — D2/D3/D6 share one surface (the dispatch/step emission seams and their tests) and
splitting would race on `phase-6-finalize/SKILL.md` and `test_dispatch_roster_closure.py`.

| Defect (Problem) | Deliverable | Verdict at HEAD | Write seam |
|---|---|---|---|
| Dispatch line wired to first entry, not spawn | D2 | **CONFIRMED (live).** Finalize hand-writes `[DISPATCH]` at 3 sites (SKILL.md ~600, ~982, ~1417) and passes NO `--workflow` to its `effort resolve-target` calls, so the per-firing seam never fires for finalize — the forbidden per-role hand-written pattern `dispatch-logging.md` replaced. | `effort resolve-target` seam (`_cmd_effort.py::_emit_dispatch_records`, landed #1200) |
| Step markers per-handler, population path-dependent | D3 (part 1) | **CONFIRMED (live).** Completion emission is 5 hand-written per-handler sites (SKILL.md 822/887/941/1117/1238), a convention enforced by a test rather than fused to the write. | `mark-step-done` (`_cmd_mark_step.py`) |
| Handshake and log line are two separate obligations | D3 (part 2) | **CONFIRMED (live).** `mark-step-done` writes only the status record (no logging import); the `[STEP] Completed step:` line is separate prose. | `mark-step-done` |
| head-at-completion peer omittable | D3 (peer) | **REFUTED.** Fail-closed guard already refuses a head-dependent `done` without `--head-at-completion` (`_cmd_mark_step.py:274-290`), and the read side re-fires + reports UNVERIFIED for a legacy SHA-less record (SKILL.md:661-662). Peer already closed both directions. |
| Resume path emits no step instrumentation | D4 | **REFUTED.** No separate resume mode; re-entry is one unified FOR loop (SKILL.md:641,652,1685). Every EXECUTED step emits item-2 start (:708) + item-7 completion (:1238). Only intentional SKIP branches omit the completion line, and they still log an INFO skip-decision line (:692–702). The epic `plan-orchestrator/workflow/resume.md` never re-runs finalize steps. Coverage-population note (D4 obligation): there is no resume-specific population because observability is uniform across the single re-entry mechanism. |
| Retrospective mode keys on wrong signal | D5 | **REFUTED (failure unreachable).** Mode still keys on `--iteration` presence (`plan-retrospective/SKILL.md:74`), and user-invocable mode writes no tail (:36,:423) — but the finalize dispatch **forwards `--iteration`** (`phase-6-finalize/SKILL.md:1007`), landing in the record-WRITING mode, and `external-step-contract.md:24` + the dispatcher's `assert-step-recorded --require-terminal` guard (SKILL.md:1088-1117) backstop any missing record with an attributed halt. D5's "done when" (dispatch selects intended mode AND record written) is already met. Version-stale flag confirmed: the tail now carries payload in two shapes. |
| Roster contradicts its own closure invariant; classification wrong | D6 | **PARTIALLY LIVE.** The known divergence (`architecture-refresh` dispatched-in-roster vs inline-in-doc) is ALREADY corrected — roster + doc agree, and check (f) in `test_dispatch_roster_closure.py` already reads both docs with a mutation guard reproducing the pre-fix shape. Residue: check (f)'s file population is **pinned** (`_D5E_STEP_DOC_PATHS`), not derived from the roster/registry population. D6's "done when" (derived, not pinned) is the remaining gap. |

**Ordering constraint** (Notes) re-derived from the clone — both satisfied (see § Ordering constraint).

Live work: **D2, D3, D6.** Refuted with evidence: **D4, D5, D3-peer.**

### D2 — emit the dispatch line from the resolve seam, per spawn — **DONE** (commit `23c7df8`)

Migrated all four finalize `effort resolve-target` sites (the agent-suitable-built-in preamble, the
item-5 built-in and project/skill branches, the item-7c unified-triage hook) to pass
`--workflow`/`--plan-id`/`--caller plan-marshall:phase-6-finalize`, so the resolve seam
(`_cmd_effort.py::_emit_dispatch_records`, landed #1200) emits both `[DISPATCH]` and its paired
decision-log record **per firing**; dropped the three hand-written `[DISPATCH]` blocks (they
double-emit and reintroduce the per-role blind spot). This is placement work, not contract work: the
line's shape and the seam already existed; only finalize's use of them was wrong. Migrating finalize
also makes the dispatch audit's `shape_violation` evaluable for finalize (Surface B was empty before —
plan 170's residue). Verification (N>1): the seam's per-firing property is covered by
`test_dispatch_seam_emission.py` (5 fires → 5 records; N∈{1,2,3,7}); added
`test_finalize_dispatch_emits_one_line_per_spawn` (3 finalize spawns → 3 lines under the finalize
caller). Rewrote roster-closure check (e): every `Task:` spawn is preceded by a `--workflow` seam
resolve, and no hand-written `[DISPATCH]` survives, with mutation guards on the pre-fix shape.

### D3 — fuse the completion marker to the handshake — **DONE** (commit `e9e3259`)

`mark-step-done` (`_cmd_mark_step.py::_emit_completion_marker`) now emits the
`[STEP] (plan-marshall:phase-6-finalize) Completed step: {step}` line as a side effect of every
terminal write for a `6-finalize` step, scoped to that phase so the emission surface — and the
out-of-scope dispatch audit's `completion_count` — is unchanged for every other phase. Removed the
five hand-written completion emits from SKILL.md (the two Signal-Gate skips, the dispatch-timeout
path, the post-dispatch-guard halt, the item-7 happy path) and rewrote the pairing prose: the line
now rides the handshake structurally on every recording path. Added `--no-completion-log`, carried by
exactly one call — the item-5f `head_at_completion` re-stamp, which revises an already-emitted `done`
— so exactly one line survives per step. Verified by removing the prose emit and confirming a step
still produces its marker (`test_mark_step_completion_emission.py`, 5 cases: emit / every-outcome /
suppress / phase-scope / idempotent) and rewrote `test_step_completion_emission.py` to pin the
fusion's two structural invariants (no hand-written emit survives; no terminal-exit block suppresses
the fused emission), with mutation guards. **Peer (`head_at_completion`) REFUTED, left unchanged** —
the fail-closed guard already refuses a head-dependent `done` without a SHA (`_cmd_mark_step.py:274`),
closing the peer from both directions.

### D4 — the resume path emits step instrumentation — **REFUTED at HEAD** (no change)

There is no separate resume mode. Re-entry is one unified FOR loop (SKILL.md:641,652,1685); every
step it EXECUTES emits its item-2 start and item-3-fused (was item-7) completion marker. Only
intentional SKIP branches omit the completion line, and they log an INFO skip-decision line
(SKILL.md:686). The epic `plan-orchestrator/workflow/resume.md` never re-runs finalize steps. **D4's
coverage-population obligation** ("any coverage figure must state whether its population included a
resume"): there is no resume-specific population, because observability is uniform across the single
re-entry mechanism — a step that executes is instrumented regardless of how the run re-entered.

### D5 — fix the retrospective mode-resolution signal — **REFUTED at HEAD** (no change)

The claim-labelled HYPOTHESIS — "the retrospective's mode resolution keys on an argument **the
dispatch does not pass**" — is **false at HEAD**. The authoritative Mode-resolution rule
(`plan-retrospective/SKILL.md:70`) keys on "invoked by `phase-6-finalize`"; the detection heuristic
(:74) uses `--iteration` presence as the observable proxy for that, and the finalize dispatcher
**always forwards `--iteration`** — the generic dispatched project/skill branch passes
`--iteration {iteration}` (SKILL.md item 5), and `loop_back_iteration` is always defined (≥0). So the
retrospective always lands in the record-writing finalize-step mode, and its `mark-step-done` tail is
written. Two independent backstops guarantee the record regardless: `external-step-contract.md:24`
(every external step MUST terminate with `mark-step-done`) and the dispatcher's
`assert-step-recorded --require-terminal` guard (SKILL.md item 5d), which converts any missing record
into an attributed `step_record_missing` halt. Version-stale flag confirmed (the tail now carries
payload in two shapes). D5's "done when" (dispatch selects the intended mode AND record written) holds
at HEAD; a speculative edit to the working, backstopped, multi-consumer mode-resolution mechanism is
not a proposal (lane rule), so none is made.

### D6 — correctness assertion over the roster, derived not pinned — **DONE** (commit `0ee7375`)

The cross-document **correctness** check (roster classification vs the step's own doc
self-classification) already existed as check (f) in `test_dispatch_roster_closure.py`, but read its
population from a hardcoded file list (`_D5E_STEP_DOC_PATHS`) — a hand-maintained mirror of a derived
set, the exact archetype the plan forbids (n≥5). De-pinned it: the population is now DERIVED from the
finalize-step registry via `find_implementors` (the same discovery the dispatcher and head-dependence
use), so every registered step's own doc is read for a self-classification sentence with no pinned
list. Replaced the pinned-existence guard with a registry non-degeneracy guard; kept the mutation
guard. **Verified the derived check FAILS against the divergent state** (Verification requirement):
temporarily moved `architecture-refresh` to the dispatched roster and confirmed
`test_touched_step_docs_agree_with_the_roster_classification` fails — it discovered
`architecture-refresh.md` via the registry, read its `**inline**` self-classification, and flagged the
disagreement — then reverted; the test passes on the corrected tree. Did **not** add a second
hand-written pin. The known divergence (architecture-refresh dispatched-in-roster vs inline-in-doc)
was already corrected at HEAD by the other epic's roster correction (ordering constraint satisfied),
so the detector passes on the live tree and the failure is demonstrated against a reconstructed
divergence, exactly as the plan's mutation-guard discipline prescribes.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (`_cmd_mark_step.py`,
`manage-status.py`, four test files), so the build takes its full path. Per-commit `./pw quality-gate`
ran clean (`issues[0]`, `coverage: COMPLETE`) before each `*.py`-touching commit. **Full `./pw verify`:
SUCCESS — 19638 passed, 14 skipped, 0 failed; coverage COMPLETE over mypy(production, 399 files), ruff,
SPDX, plugin-doctor (marketplace-wide), mypy(test, 735 files), and whole-tree pytest** (525 s). Read
from the build output, not the exit code. One intermediate `test-compile` failure — a `no-any-return`
in the new `test_mark_step_completion_emission.py` `_mark` helper (returning the `Any` result of a
`load_script_module`-loaded `cmd_mark_step_done` from a `-> dict` function, the exact test-only type
error the lane warns `test-compile` catches that `quality-gate` + `module-tests` would miss) — fixed
by binding the result to a typed local (`a906bad`) and re-verified green.

## Findings

### Verification sub-agent (Step 6)

An independent read-only sub-agent verified the diff against `plan.md`. **Verdict: D2/D3/D6
implemented as specified and correctly tested; the D4/D5/D3-peer refutations are sound from source.**
It surfaced one in-diff correctness contradiction and five beyond-diff stale-claim / doc-gap findings
that the first-pass sweep had not recorded; all six were fixed (commit `c9b48e8`), and a **re-dispatch
confirmed all six cleanly resolved with no new contradiction or stale claim** (the F2/F3 audit edit
verified comment-only).

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | sub-agent, in-diff, **correctness** | `_cmd_mark_step.py` docstring + `manage-status.py` `--help` named the item-7a merge-anyway resolution as a `--no-completion-log` carrier, contradicting SKILL.md (item-5f is the only carrier; item-7a is the escalate-ask step's first/only terminal write and MUST emit). An implementer following `--help` would silence the only completion line for an escalate-ask-merged step. | **FIXED** (`c9b48e8`) — both script docs corrected to agree with SKILL.md; re-verified. |
| F2 | sub-agent, beyond-diff | `check-dispatch-audit.py:91` comment called the finalize `[DISPATCH]` line hand-written by the dispatcher — false after D2 (rides the resolve seam). | **FIXED** (`c9b48e8`) — comment corrected; audit logic + tests untouched. |
| F3 | sub-agent, beyond-diff | `check-dispatch-audit.py:110` comment called the `[STEP]` line "dispatcher-emitted" — false after D3 (emitted by `mark-step-done`). | **FIXED** (`c9b48e8`) — comment corrected (comment-only). |
| F4 | sub-agent, beyond-diff | `dispatch-inline-split.md:15` said the `[DISPATCH]` emission is "fused to the dispatch branch" — false after D2 (resolve seam). | **FIXED** (`c9b48e8`). |
| F5 | sub-agent, doc gap | `manage-status/SKILL.md` did not document the new `--no-completion-log` flag or the finalize `[STEP]` emission side-effect. | **FIXED** (`c9b48e8`) — added to usage block, parameter list, and a new "Fused completion emission" subsection. |
| F6 | sub-agent, beyond-diff | `dispatch-walkthrough.md` item-7c example showed the pre-seam bare resolve for the dispatch D2 migrated. | **FIXED** (`c9b48e8`) — aligned to the canonical seam form. |
| nit | re-verify | `manage-status.py` `--help` missing a possessive apostrophe ("step first" → "step's first"). | **FIXED** (user-facing `--help` polish). |

**Out-of-scope boundary honored:** the fix to the two `check-dispatch-audit.py` comments (F2/F3) is
comment-only — the dispatch audit's logic and its tests, owned by the sibling plan (170, landed as
#1225), are byte-identical. Correcting a comment MY emission change falsified is the lane's
stale-claim discipline, not a change to the audit surface.

No sub-agent finding was rejected. No undeclared collateral change (the `effort resolve-target` seam
itself was not touched, honoring the plan's "if recording requires touching effort resolution, stop
and coordinate" constraint).

### CI

On the report-finalize head, `verify / gate`, `review / review`, `dependency-review`, and
`generate-check` concluded **success**; `verify / verify` (the heavy build carrying the required
`verify / conclusion`) was **in_progress** at the merge gate. No self-wake is available in this cloud
session, so — per the lane — auto-merge was armed while `verify` runs; the merge queue admits the PR
only when the ruleset's required contexts pass, and re-verifies on `merge_group`. The full `./pw
verify` ran green locally over the identical tree (19638 passed). No CI failure observed.

### PR review

No actionable review comment. All three comment surfaces were read before the merge gate
(`get_comments`, `get_reviews`, `get_review_comments`); inline review threads: **none**.
`cuioss-review-bot` posted a clean review ("PR contains tests · No security concerns identified · No
major issues detected") — nothing to fix or reply to. `coderabbitai` and `sourcery-ai` posted only
rate-limit notices. Disposition: nothing actionable; the coverage shortfall is disclosed below.

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:
**M = 3** — `coderabbitai` (coderabbit.md:27), `cuioss-review-bot` (pr-agent.md:55), `sourcery-ai`
(sourcery.md:25). Verdicts derived from the stored comment bodies (not check states):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a review over the diff — "PR Reviewer Guide 🔍 · 🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected" (issue-comment 5295894580). Clean; no findings to handle. |
| `coderabbitai` | `rate-limited` | Published only a quota notice, no review: "Review limit reached … Next review available in: 74 minutes" (issue-comment 5295887831). |
| `sourcery-ai` | `rate-limited` | Published only a quota notice, no review: "you have reached your weekly rate limit of 500000 diff characters" (review 4939402503). Its `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** **Step-8 shortfall disclosure (fired — disclosure, not a block):** *Review
coverage: 1 of 3 — `cuioss-review-bot` reviewed (tests present, no security concerns, no major
issues); `coderabbitai` rate-limited (next window ~74 min); `sourcery-ai` rate-limited (weekly
diff-character quota).* Rate limits are routine and outside our control; per the lane this changes
only what the run says, not whether it merges. Auto-merge armed exactly as full coverage would be.

## Cost

- **Tokens:** not available to the agent as a reliable figure in this session.
- **Wall-clock:** single interactive Claude Code cloud session (see PR #1232 timestamps for the
  finalize window; `./pw verify` alone was ~525 s).
- **Population:** this one cloud session's usage as the harness counts it. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total (which counts the orchestrator-plus-agent dispatch tree under a
  per-task billing boundary this single interactive session does not share). No comparable number is
  presented.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; each step checked against what happened and its on-disk artifact:

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — `cloud-plan-lane`, `ref-code-quality`, `plugin-script-architecture` loaded by bundle path (plugin absent, as the lane anticipates). Domain skills read as the surface was confirmed. |
| 2 Branch on `origin` | **done** — harness-assigned `claude/finalize-dispatch-manifest-observability-nrxcwr`, pushed before any work; kept as-is. |
| 3 Plan directory | **done** — `…/180-…/plan.md` exists and opens with the first-instruction block (present on receipt; no repair needed). |
| 4 Implement | **done** — commits `b8c03e3`,`23c7df8`,`e9e3259`,`0ee7375`,`a906bad`,`d5af83f`,`c9b48e8`,`7de83e6` (+ this final report commit); each carries the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | **done** — every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`issues[0]`, `coverage: COMPLETE`). |
| 4 Pushed | **done** — this final report commit is the last; no unpushed commit remains. |
| 5 Build gate | **done** — Python changed → full `./pw verify` SUCCESS (19638 passed, 0 failed); coverage COMPLETE including `test-compile` (the one intermediate failure it caught was fixed and re-verified). |
| 6 Verification sub-agent | **done** — dispatched read-only; all live deliverables MET and refutations sound; six findings fixed (`c9b48e8`) and a re-dispatch confirmed clean. Findings + dispositions above. |
| 7 PR cycle | **done** — PR #1232 (no `skip-bot-review`: the diff is code — `*.py` + skills/bundles). Every comment dispositioned; all three comment surfaces read. |
| 8 Merge gate | conditions 1–3 met (required `verify` deferred to the queue via auto-merge; no open comments; report finalized as the last pre-merge commit), 1-of-3 shortfall disclosed, auto-merge armed (SQUASH). Landing delegated to the merge queue (no self-wake in this session — arm-and-hand-off is a completed outcome per the lane). |
| 8 Bridge | **done** — no status/bookkeeping write under `doc/plans/` outside this plan's own directory; no shared lane doc touched. The report carries the PR number and per-deliverable outcome for the orchestrator's collect. |
| 9 This check | **done** — recorded here. |
| 9 What have we learned | **done** — below. |

GitHub access path used: **GitHub MCP server**. Branch form: **harness-assigned**. No
`/sync-plugin-cache` is owed (machine-local build step, not a debt a cloud run records). A local
executor sync IS owed on the developer machine after this lands, since the diff edits
`marketplace/bundles/**` (recorded here per the lane's Plugin-Cache-Sync carve-out).

## What have we learned (Step 9)

**No `cloud-plan-lane` contract change proposed.** The contract executed cleanly end to end:
skill-by-path loading, the harness-assigned branch pushed before any work, the conditional build gate
(Python → full `verify`), the pre-PR verification sub-agent (whose beyond-diff stale-claim sweep
earned its keep — it caught six real stale claims/gaps the diff-scoped checks missed, including one
in-diff correctness contradiction), the three-surface comment read, and the disclose-not-block
shortfall rule all behaved as written. The `test-compile` warning the lane documents was hit exactly
as described (a `load_script_module`-`Any` returned from a `-> dict` test helper) and fixed. No step
was ambiguous in practice and no step's artifact failed to produce as written. A speculative edit is
not a proposal, so none is made.

**Observation for the operator (plan-authoring, not a lane-contract change).** Plan 180 was heavily
**version-stale**: three of its six deliverables (D4, D5, D3-peer) were already resolved at HEAD by
sibling/subsequent work, and its central live pieces (D2/D3) were the emission-side migration plan
170's own report Residue had named as owed. The plan anticipated exactly this (D1 is a GATE that
"confirms or refutes each defect at its own site", and every claim carried a "confirm the current
shape, not the filed one" instruction), so the run re-grounded each defect from source and reported
the refutations with evidence rather than implementing against a stale brief. This is the intended
behaviour of a retrospective-derived plan, not a defect — but it is worth the operator's eye that the
plan's realized scope (D2+D3+D6 + a de-pin) was materially smaller than its six-deliverable framing,
and that the split-guard "proceed unsplit" verdict held up: D2/D3/D6 genuinely shared one surface
(the dispatch/step emission seams and their tests) and would have raced had they been split.

## Residue

- **`[STEP] … Executing step:` start marker is still hand-written prose** (SKILL.md item 2), not
  fused. D3 fused only the COMPLETION marker (the plan's target — the "handshake and log line are two
  obligations" defect is about completion). The start marker is already loop-driven (item 2 fires
  every iteration), so it is structurally covered; fusing it too would be a symmetric follow-up but is
  out of this plan's scope and carries the same cross-phase / audit-`completion_count` blast-radius
  question D3 resolved by phase-scoping.
- **`coderabbitai` / `sourcery-ai` reviews did not run** (both rate-limited). If a full-coverage
  review is wanted, a re-request after their windows reopen (~74 min for coderabbit; weekly for
  sourcery) would exercise them against this diff — not owed by the lane (disclose-not-block), noted
  for completeness.
- **Local executor sync owed on the developer machine** after this lands (the diff edits
  `marketplace/bundles/**`); a cloud run neither performs nor owes `/sync-plugin-cache`, but the local
  developer sync is real.
