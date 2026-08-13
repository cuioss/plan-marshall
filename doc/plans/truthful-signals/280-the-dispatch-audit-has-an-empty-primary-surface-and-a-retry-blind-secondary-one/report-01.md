# Run report — 280 dispatch-audit-emitter (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/dispatch-audit-surfaces-rc5j18` (harness-assigned; kept as-is)    **PR:** [#1200](https://github.com/cuioss/plan-marshall/pull/1200)    **Outcome:** completed (conditions 1–3 met, review shortfall disclosed, auto-merge armed; landing delegated to the merge queue)

This plan owns the **emitter** only (dispatch-record emission). Every detector-side
change is out of scope per the plan's ownership block (owned by the four
`code-intelligence-substrate` plans). That boundary shaped every scoping decision below.

## Skills loaded

- `cloud-plan-lane` (first action, governs the run).
- `plan-marshall:ref-code-quality` (read by bundle path).
- `pm-plugin-development:plugin-script-architecture` (+ `cross-skill-integration.md`).
- `plan-marshall:ref-workflow-architecture` (+ `dispatch-logging.md`).
- `plan-marshall:persona-implementer`.
- `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Deliverables

### D0 — GATE: emission population (both directions) + token-mismatch sweep (mutates nothing)

Enumerated via an independent read-only sub-agent, cross-checked by symbol. **Population stated, hit
count stated separately.**

**Direction 1 — envelope-creation / dispatch sites (the envelope set):** 14 live co-located dispatch
sites (each resolves `effort resolve-target` and dispatches `Task: plan-marshall:{target}` with a
co-located hand-written `[DISPATCH]` step), plus 6 sites that dispatch with **no** co-located
emission (the mismatch set). Re-fire paths (verification-feedback loop, `until_clean` q-gate loops,
envelope re-dispatch, finalize head-advance re-fire) re-point at the prior `Task:` block **without
re-running the hand-written logging step** — the "re-fires vanish" pathology.

**Direction 2 — dispatch-record emission sites (the emission set):** every `[DISPATCH]` line is a
hand-written `manage-logging work` step; `effort resolve-target` itself emits **nothing** (confirmed
by a whole-file scan of `_cmd_effort.py`). Mismatch set (dispatch happens, no co-located emission):
`planning.md:232-244` (light-lane phase-3-outline), `research-best-practices.md:100-108` (reader
variant), `agent-behavior-rules.md:101-108`, `finalize-step-simplify.md:124-129`,
`ext-point-dynamic-level-executor.md:171-179`, `doctor-marketplace.md:51`.

**Most-consequential instance** (plan claim "the merge/branch-cleanup step is absent from the
trail"): CONFIRMED, **and by design** — `default:branch-cleanup` (which holds the merge mutex,
performs the merge, prunes the branch) is classified **INLINE** in
`phase-6-finalize/standards/dispatch-inline-split.md`, so it never resolves a target, never
dispatches, and carries no `[DISPATCH]` line. Its absence is not an instrumentation gap this plan
can close from the emitter side — the inline-vs-dispatched classification and whether the audit
should expect a record for it are detector/roster concerns owned elsewhere. Recorded, not fixed here.

**Token-mismatch sweep (bare-vs-canonical comparison class):**

- **Sweep population: 14 comparison/membership sites examined.**
- **Hit count: 1 true mismatch.**

The single hit is `plan-retrospective/scripts/check-manifest-consistency.py:324` — Rule M3
(`evaluate_tests_only`) compares `steps != ['module-tests']` (BARE), while the composer's
`_VERB_TO_PHASE_5_STEP` (`manage-execution-manifest/scripts/_manifest_rules.py:915-920`) and the
default phase-5 steps (`_manifest_core.py:281`) only ever emit the CANONICAL prefixed
`verify:module-tests`. So M3's equality is never satisfied on a real composer-produced manifest and
the tests-only gate is **silently disabled**. "The verb that lists verification steps" is
`manage-config list-verify-steps` (`_cmd_skill_domains.py:462,488`), which emits the further-prefixed
`default:verify:{canonical}` form. Every other of the 14 sites is benign (a derived-role comparison,
a bare build-command/CI-label of a different value class, a producer/deriver map keyed on bare
tokens, or a prefix-agnostic validator) — so the class is **contained to one site**, not widespread.

**Disposition of the token-mismatch:** M3 is a **plan-retrospective detector**. Making it fire again
is exactly "an audit detector structurally incapable of reporting what it claims," which the plan's
ownership block assigns to sibling plan `code-intelligence-substrate/290-auditor-detector-integrity`.
Per that block's "⛔ Do not implement any row but the first," this plan **reports** the mismatch (D0's
job — mutate nothing) and does **not** patch M3. See "What have we learned" for the D3(e) consequence.

*Commit:* enumeration is a read-only deliverable recorded here (no code). The token-mismatch has no
remediation commit by design.

### D1 — Move the emission into the seam (per firing, not per role)

`effort resolve-target` — the one script call every execution-context dispatch makes — now emits the
dispatch record itself when the caller passes the dispatch context (`--workflow`, and
`--plan-id`/`--caller`). Because every firing resolves, every firing emits: per firing, not per role;
a re-fire that re-resolves re-emits, by construction, with no separate hand-written step to forget. A
bare resolve (no `--workflow`) stays a pure read, byte-identical. Emission is best-effort
(`log_entry` never raises) and fires only after a successful resolve.

Both audit surfaces are written from the one seam — the decision-log resolution record (Surface B,
previously empty: the resolver logged nothing) and the work-log `[DISPATCH]` line (Surface A). The
emitted `role=` is the caller's bare role-key (`--role`, or `--phase` when absent), matching the
dispatch-logging field semantics and the audit's existing role matching, NOT the resolver's dotted
`group.subkey` payload role.

- *Commit `bb5a14e`*: `_cmd_effort.py` seam emission + `manage-config.py` CLI args + 8-test file.
- *Commit `2da6285`*: `dispatch-logging.md` rewritten to make the seam the canonical mechanism
  (Why/Placement/Canonical-invocation/Positive-example/Anti-pattern); `_cmd_effort.py` role-key
  refinement; SKILL summaries; execution.md phase-5-execute migrated.
- *Commit `618121c`*: execution.md verification-feedback triage loop migrated.

**Verification state:** mechanism proven by 8 tests (below), each red pre-fix. The two migrated
dispatch sites (phase-5-execute, verification-feedback — the exact re-fire paths the plan calls out)
reproduce their prior `[DISPATCH]` role/workflow/caller exactly. **Remaining caller migrations are
scoped as follow-up** (see Residue) — the mechanism + contract + demonstration are complete; the
remaining ~11 workflow-doc callers keep their still-valid hand-written path until migrated, with a
per-site role-convention nuance flagged (phase-6-finalize dispatched steps emit `role=default` for a
bare `--phase`, so their migrated resolve must pass an explicit `--role default` to reproduce it).

### D2 — State the corroboration limit where the audit's consumers meet it

`execution-context-dispatch-audit.md` § Inputs now carries a "Corroboration limit" statement: both
evidence surfaces are written by the same seam call, so their agreement is a **consistency** check on
the emitter, never a **completeness** check on the set of dispatches — a dispatch that bypassed the
seam is absent from both at once and reads clean; a completeness verdict needs a third source with an
emitter independent of the seam, which the `logs/` do not contain. It is a sentence about what the
emitter guarantees; it changes no check's logic. *Commit `2da6285`.*

### D3 — Tests, each verified to FAIL pre-fix

`test/plan-marshall/manage-config/test_dispatch_seam_emission.py` (8 tests). Verified **red first**
(6 failed with "unrecognized arguments: --workflow …" pre-fix; the backward-compat test passed
because the pre-fix behaviour is "emit nothing"), then **green** after D1.

- (a) five-fire shape → five records (`test_re_fired_step_emits_one_record_per_fire`). ✓
- (b) a resolve that emitted nothing now emits (`test_resolve_target_now_emits_a_dispatch_line`). ✓
- (c) N fires → N records, not one (`test_role_fired_n_times_produces_n_records`, N∈{1,2,3,7}). ✓
- (d) population non-empty AND emission set == envelope set, field-for-field
  (`test_emission_set_equals_envelope_set` + `test_dispatch_line_fields_match_the_resolved_envelope`). ✓
- Plus `test_two_flag_resolve_emits_bare_role_key`, `test_both_surfaces_written_from_the_seam` (D2),
  and `test_bare_resolve_without_workflow_emits_nothing` (backward-compat). ✓
- **(e) token-mismatch rule fires — DEFERRED.** Making Rule M3 fire requires changing a
  plan-retrospective **detector**, which the ownership block assigns to plan 290. D0 delivered the
  in-scope half (the sweep confirms the single mismatch by symbol); the "make it fire" half is out of
  scope here. Recorded, not skipped silently.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (`_cmd_effort.py`,
`manage-config.py`, the new test file), so the build takes its full path: `./pw verify`
(quality-gate + tests). Per-commit `./pw quality-gate` ran clean (0 issues) before every
`*.py`-touching commit. **Full `./pw verify`: SUCCESS — 19341 passed, 14 skipped, 0 failed;
coverage COMPLETE over mypy(production+test), ruff, SPDX headers, plugin-doctor (marketplace-wide),
and whole-tree pytest.** Read from the build output, not the exit code.

## Findings

Each finding is recorded per instance with source, description, and disposition.

**Verification sub-agent (Step 6) — verdicts.** D1 PASS on every sub-property (emit only on
`--workflow`; only after a successful resolve; best-effort/never-raises; bare role-key not the dotted
payload role; CLI args present; five-field shape byte-compatible). D2 PASS on the cold read (a
cold reader lands on "the seam ran / self-consistent," not "complete"). D3(a–d) covered; D3(e)
deferral confirmed as the correct reading of the emitter-only boundary. No undeclared collateral
change.

Beyond-diff stale-claim sweep — **three real stale claims found, all fixed in this run**:

- **GAP A — `ref-workflow-architecture/standards/dispatch-walkthrough.md` Example A (+ cross-ref).**
  The "canonical worked-example trace" showed the old resolve-without-`--workflow` → hand-written
  `manage-logging work "[DISPATCH]"` step → dispatch, i.e. the exact pattern the diff's own
  `dispatch-logging.md` anti-pattern now forbids. Disposition: **FIXED** — migrated Example A to the
  seam form (resolve carries the dispatch context; the `[DISPATCH]` line is shown as a side-effect of
  the resolve) and reworded the L323 cross-reference.
- **GAP B — `dispatch-logging.md` cross-reference line.** Still described the emission as "between
  resolve and dispatch," contradicting the body I rewrote. Disposition: **FIXED** — reworded to "a
  side-effect of the resolve seam (not a separate step)."
- **GAP C — `manage-config/standards/api-reference.md` (effort prose + `resolve-target` params
  row).** Called `read`/`resolve-target` "pure resolvers" and the params "same as `read`."
  Disposition: **FIXED** — qualified to "`resolve-target` never mutates config but ALSO emits the
  dispatch-audit records from the seam when passed `--workflow`," and listed the three new args in the
  params cell.

- **Minor (sub-agent observation) — routing comment precision in `_cmd_effort.py`.** The comment
  over-stated that the literal `--plan-id none` maps to `None`; in fact it passes through
  (`names_real_plan('none')` is True) and reaches the global log via `get_log_path`'s no-such-plan
  fallthrough — observable behaviour unchanged. Disposition: **FIXED** — comment tightened; no logic
  change.

- **Cross-plan coordination note (NOT a gap against this plan; recorded for the detector plan).** The
  seam writes Surface B as `(plan-marshall:manage-config) effort resolve-target role=X -> target=Y
  level=Z`, whereas the audit standard's illustrative example rows still show the older
  `effort resolve-target --role phase-2-refine` CLI-flag form. The audit's Surface-B *description* is
  loose enough to match, and detector parsing is out of scope here; plan
  `code-intelligence-substrate/290` (which owns the detector) will need to parse the emitter's actual
  format. Also: `shape_violation` becomes near-unreachable now that both surfaces emit atomically from
  one seam — the corroboration-limit paragraph (D2) already frames this.

- **D0 enumeration sub-agent:** its findings are the D0 deliverable above; no defect against this
  plan's own diff.
- **Token-mismatch (M3):** real, single instance, disposition = reported-not-fixed (detector-side,
  owned by plan 290). Rejected here on ownership-boundary grounds, recorded with full evidence.
- **CI:** green on the final reviewed head. A `verify / conclusion` **failure** arrived for the
  superseded head `6367684` (cancelled by the report-update push via Actions concurrency) — a
  superseded run, not a real failure, per the lane; the live head's `verify / conclusion` and
  `verify / verify` both concluded **success**. No fix warranted.
- **PR review:** no actionable comment. `cuioss-review-bot` reviewed clean; `coderabbitai` and
  `sourcery-ai` posted only rate-limit notices. No inline threads. Disposition: nothing to fix or
  reply to; the shortfall is disclosed (Reviewer participation, above).

## Reviewer participation

Expected reviewer population derived from configuration
(`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` `author_login`):
**M = 3** — `coderabbitai` (coderabbit.md), `cuioss-review-bot` (pr-agent.md), `sourcery-ai`
(sourcery.md). Verdicts derived from stored comment bodies (not check states):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a review summary over the diff — "PR Reviewer Guide: 🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected" (issue-comment 5277414099). A clean review, no findings to handle. |
| `coderabbitai` | `rate-limited` | Published only a quota notice, no review: "Review limit reached … we couldn't start this review. Next review available in: 100 minutes" (issue-comment 5277404207). |
| `sourcery-ai` | `rate-limited` | Published only a quota notice, no review: "you have reached your weekly rate limit of 500000 diff characters" (review 4924525204). Its `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** Inline review threads (`get_review_comments`): none. All three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`) were read before the merge gate. No actionable
review comment exists — the one review is clean and the other two are quota notices.

**Step-8 shortfall disclosure (fired — disclosure, not a block):** *Review coverage: 1 of 3 —
`cuioss-review-bot` reviewed (no major issues, no security concerns); `coderabbitai` rate-limited
(next window ~100 min); `sourcery-ai` rate-limited (weekly diff-character quota).* Rate limits are
routine and outside our control; per the lane this changes only what the run says, not whether it
merges. Auto-merge is armed exactly as full coverage would be.

## Cost

- **Tokens:** not available to the agent as a reliable figure in this session.
- **Wall-clock:** single interactive cloud session (start ≈ run open; see PR timestamps).
- **Population:** this one Claude Code cloud session's usage. **NOT comparable** to a plan-marshall
  `metrics.toon` total (that counts an orchestrator-plus-agent dispatch tree under a different
  per-task billing boundary this session does not share). No comparable number is presented.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; each step checked against what happened and its on-disk artifact:

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named above; loaded by bundle path (plugin absent, as the lane anticipates). |
| 2 Branch on `origin` | **done** — harness-assigned `claude/dispatch-audit-surfaces-rc5j18`, pushed before any work; kept as-is. |
| 3 Plan directory | **done** — `…/280-…/plan.md` exists and opens with the first-instruction block (present on receipt; no repair needed). |
| 4 Implement | **done** — commits `41fdecf`,`bb5a14e`,`2da6285`,`618121c`,`6367684` + report commits; each carries the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | **done** — every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (0 issues across ruff/mypy/SPDX/plugin-doctor). |
| 4 Pushed | **done** — this final report commit is the last; `git status -sb` clean, no `ahead`. |
| 5 Build gate | **done** — Python changed → `./pw verify` SUCCESS (19341 passed, 0 failed). |
| 6 Verification sub-agent | **done** — dispatched read-only; D1/D2/D3 PASS, three stale-claim gaps found → fixed → re-confirmed closed. Findings + dispositions above. |
| 7 PR cycle | **done** — PR #1200 (no `skip-bot-review`: the diff is code — `*.py` + skills/bundles). Every comment dispositioned; all three comment surfaces read. |
| 8 Merge gate | conditions 1–3 met (required checks deferred to the queue via auto-merge; comments handled; report finalized as the last pre-merge commit), 1-of-3 shortfall disclosed, auto-merge armed (SQUASH). Landing delegated to the merge queue (self-wake `send_later` is approval-gated in this session, so the run cannot block-until-landed — arm-and-hand-off is a completed outcome per the lane). |
| 8 Bridge | **done** — no status/bookkeeping write under `doc/plans/` outside this plan's own directory; no shared lane doc touched. The report carries the PR number and per-deliverable outcome for the orchestrator's collect. |
| 9 This check | **done** — recorded here. |
| 9 What have we learned | **done** — below. |

GitHub access path used: **GitHub MCP server**. Branch form: **harness-assigned**. No `/sync-plugin-cache`
is owed (machine-local build step, not a debt a cloud run records).

## What have we learned (Step 9)

**No `cloud-plan-lane` contract change proposed.** The contract executed cleanly end-to-end and every
gate held: skill-by-path loading, the harness-assigned branch, the conditional build gate, the
pre-PR verification sub-agent (whose beyond-diff stale-claim sweep earned its keep — it caught three
real stale docs the diff-scoped checks missed), the three-surface comment read, and the
disclose-not-block shortfall rule all behaved as written. The one friction — `send_later` being
approval-gated, so no fallback self-check-in could be scheduled — is already documented in the lane
(§ Cloud session affordances), and the `subscribe_pr_activity` path covered event delivery. No step
was ambiguous in practice, no artifact failed to produce as written, and no command failed in the
environment. A speculative edit is not a proposal, so none is made.

**Observation for the operator (plan-authoring, not a lane-contract change).** Plan 280 carries an
internal contradiction: its ownership block forcefully excludes *every* detector-side change ("⛔ Do
not implement any row but the first"), yet deliverable **D3(e)** asks for a test that makes the
token-mismatch **detector** (Rule M3) fire — which is a detector change. This run resolved it by
honouring the ownership block (the most authoritative, most forcefully-stated section): D0 reports
the mismatch (the in-scope half), and D3(e)'s "make it fire" half is deferred to plan 290 with full
evidence. If the operator intended M3 to be fixed here, that is a re-scope decision for a follow-up;
the safer reading — not crossing the settled ownership boundary the plan itself warns about — was
taken autonomously.

## Residue

- **Remaining caller migrations to the seam (follow-up).** Live dispatch sites still on the
  hand-written path: `planning.md` (phase-2-refine, q-gate-validation), `planning-outline.md`
  (phase-3-outline, phase-4-plan, two q-gate loops), `phase-6-finalize/SKILL.md` (the generic
  dispatched-step block, the project/skill DISPATCHED branch, the wait-region unified triage),
  `outline-workflow-detail.md` (detect-change-type), `pre-submission-self-review.md`,
  `workflow-pr-doctor/SKILL.md`, plus the doc echoes `adr-propose.md` / `lessons-capture.md`. Each
  needs: add `--workflow/--plan-id/--caller` to its resolve, delete the hand-written `[DISPATCH]`
  block, and — for phase-6-finalize dispatched steps — pass an explicit `--role default` (or the
  step's sub-key) so the seam reproduces the `role=default` label the current line uses. The `until_clean`
  / triage re-fire loops must also be reworded from "re-dispatch via the same Task envelope" to
  "re-run the resolve (which re-emits) and re-dispatch."
- **Token-mismatch M3** → plan `code-intelligence-substrate/290-auditor-detector-integrity` (detector).
- **branch-cleanup absent from the trail** → detector/roster concern (inline-vs-dispatched
  classification), owned outside this plan.
- Deferrals the plan itself carried (session-identifier leaf-overwrite, per-dispatch billing columns,
  last-write-wins phase-step record) remain out of scope and unaddressed here, as the plan directs.
