# Run report — 110-blocking-boundary-arms-on-a-call-not-a-state (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/blocking-boundary-arms-call-jqwzo9` (harness-assigned)    **PR:** [#1199](https://github.com/cuioss/plan-marshall/pull/1199)    **Outcome:** completed — all three deliverables landed on the branch, CI green, PR review cycle handled, auto-merge armed at the merge gate

## Outcome per deliverable

- **D1** — completed: source-side derivation established the finalize-phase handshake row is universally
  absent (no emitter), so D2 is a correctness fix; population counts blocked-on-corpus (unreachable, as
  the plan expects) and reported as such.
- **D2** — completed: the blocking-findings gate is armed by a state at two firing sites (pre-merge
  `findings-check`, completion-boundary `assert_finalize_findings_clean`), both consumers covered,
  negative controls fail pre-fix, positive controls admit clean plans.
- **D3** — completed: `qgate resolve-evidenced` resolves only evidenced-fix findings and leaves
  unevidenced ones pending; wired into the self-review delta round; both directions asserted.

## Skills loaded

- `cloud-plan-lane` (first action, via `Skill:`) — the working contract.
- `plan-marshall:ref-code-quality` — read from bundle path (always).
- `pm-plugin-development:plugin-script-architecture` — read from bundle path (always).
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned `claude/*`**, kept as-is per the contract.

## Deliverables

### D1 — GATE: establish the population (mutates nothing)

**Corpus reachability:** the archived-plan corpus lives under a machine-local, git-ignored path
**not present in this clone**. Per the plan's explicit instruction, it was **not searched for**. The
population counts ("how many archived plans carry no finalize-phase handshake row; how many of those
merged with pending actionable findings") are therefore **not derivable from the clone** and are
reported **blocked on corpus access**.

**Source-side derivation (decisive on its own).** The plan states the corpus question is settleable in
the clone: if **no call site emits a finalize-phase capture at all**, the row's absence is structural
and universal. That derivation was performed:

- `plan-marshall/workflow/execution.md` — at the `5-execute → 6-finalize` boundary emits only
  `phase_handshake capture --phase 5-execute` (execute-completion, lines ~415 and ~543 direct-entry),
  **never** `--phase 6-finalize`. The transition `manage-status transition --completed 5-execute`
  inlines `cmd_verify(phase=5-execute)` — drift-only; `_capture_pending_findings_blocking_count`
  raises **only** at `phase == '6-finalize'`, so a `verify --phase 5-execute` never raises the block.
- `automatic-review/` (SKILL + workflow) — **no** `phase_handshake` / `findings-check` call anywhere.
- `phase-6-finalize/workflow/sonar-roundtrip.md` — **no** such call.
- `phase-6-finalize/standards/branch-cleanup.md` — **no** such call. It *refers* to "the existing
  `phase_handshake findings-check` gate" (line 655) as if wired, but never invokes it.
- `cmd_findings_check` (`_handshake_commands.py`) — the read-only gate that raises
  `blocking_findings_present` on pending actionable findings at `--phase 6-finalize` — is **defined,
  documented, and tested**, but **invoked by no orchestration workflow doc**.
- `capture --phase 6-finalize` — described only in prose in
  `ref-workflow-architecture/standards/findings-pipeline.md` (the "issued by the Phase Entry Protocol"
  / "re-issued by automatic-review / sonar-roundtrip" rows) and in
  `plan-marshall/references/phase-handshake.md` (the intra-finalize `findings-check` rows). **Neither
  prose claim is backed by an actual call site.**

**Answer to the universal-vs-incidental gate:** the missing finalize-phase handshake row is
**UNIVERSAL, not incidental** — no code path emits a finalize-phase capture or findings-check, so the
row is structurally absent on every orchestrated plan. The blocking-findings gate has been **inert
fleet-wide**. Per the plan's D1 branch, **D2 is a correctness fix, not a hardening.** The reference
docs that assert the re-issue exists are **stale/false claims** and are corrected as part of D2.

### D2 — the absence of a finalize-phase handshake row is itself a blocking condition

**Design chosen — convert arming from a call to a state.** The blocking-findings raise fires only when
a `capture`/`findings-check` carrying `--phase 6-finalize` is issued (`_invariants.py`
`_capture_pending_findings_blocking_count`, guarded on `phase in _BLOCKING_BOUNDARIES = {'6-finalize'}`).
No orchestration issued one, so the gate was inert. The self-review findings the gate exists to catch are
filed **during** finalize, so the 5→6 **entry** boundary cannot catch them; the gate must live at the
finalize **merge / completion** boundary. Two firing sites now exist:

1. **Pre-merge (fail-closed):** `branch-cleanup.md` § "Pre-merge blocking-findings store gate" issues
   `phase_handshake findings-check --phase 6-finalize` before the merge — making the "existing
   findings-check gate" the doc already referenced (line 655) real, and blocking the merge on a pending
   actionable finding or an unevaluable query.
2. **Completion (state assertion):** `_invariants.assert_finalize_findings_clean` (self-armed at
   `6-finalize`, so a caller cannot disarm it by passing a non-guarded phase) is called by **both**
   lifecycle completion consumers in `_cmd_lifecycle.py` — `cmd_transition` completing `6-finalize` and a
   normal-completion `cmd_archive`. It refuses to mark the plan complete while an actionable finding is
   pending. A deliberate `--reason` archive (abandonment) stays exempt so a low-confidence plan is not
   stranded. On an unevaluable query the completion boundary fails open with a logged WARNING (the
   fail-closed path is owned by the pre-merge gate, where the executor is guaranteed present).

Both consumers of `_BLOCKING_BOUNDARIES` are addressed: `_invariants.py` (adds the self-arming assertion,
predicate unchanged) and `_cmd_lifecycle.py` (calls it from both terminal paths).

**Commits:** `cc7f7a9` (core + tests), `d03cdf8` (pre-merge wiring + doc corrections).

**Negative / positive controls** (`test_manage_status_transition.py`): a pending actionable finding
REFUSES both `cmd_transition --completed 6-finalize` and a normal `cmd_archive`
(`blocking_findings_present`, state unchanged); a clean plan is admitted; a knowledge-type finding never
blocks; a `--reason` archive bypasses; a dry-run does not fire. The negative controls exercise the REAL
predicate via the `_stub_finding_queries` seam and fail against the pre-fix code (which has no completion
gate). Plus a direct `assert_finalize_findings_clean` test in `test_phase_handshake_findings.py`
(raises on pending at 6-finalize with no caller-supplied phase; returns 0 clean; None unevaluable).

### D3 — the self-review loop-back path resolves the findings whose fixes it lands

**Design chosen.** `pre-submission-self-review.md` files a Q-Gate finding per structural defect (Branch B)
but resolves none of its own, so a landed fix left the record stuck at `pending`. New evidence-gated verb
`manage-findings qgate resolve-evidenced` (`_findings_core.resolve_qgate_findings_by_evidence`) transitions
a pending Q-Gate finding to `fixed` ONLY when its `file_path` is in the caller-supplied `--changed-path`
set (the files a landed fix touched); every finding whose file the fix did NOT touch — or that has no
`file_path` — is LEFT `pending`. A premature resolution is self-correcting: the next round's re-surface
re-detects the defect and `add_qgate_finding` REOPENS the record. Wired into the self-review delta round
(Step 1): each loop-back round resolves the prior round's evidenced findings before re-surfacing.

**Commit:** `27951b7`.

**Both directions asserted** (`test_findings_store.py`): file-in-set → `fixed`; file-not-in-set →
`pending` (the important direction); no-file_path → `pending`; mixed batch partitions correctly;
already-resolved untouched; premature resolution reopened; invalid phase errors. Plus the CLI
`--changed-path` input-shape boundary test (`test_manage_findings_cli.py`).

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (3 production scripts, 4 test files), so the
full gate ran: **`./pw verify` → SUCCESS**, 19351 passed / 14 skipped (pre-existing environment guards,
none introduced by this change). Quality gate green throughout (mypy production + test, ruff, SPDX,
plugin-doctor marketplace-wide). No `uv.lock` churn (staged deliverable paths explicitly; verified clean
tree after the build). `UV_HTTP_TIMEOUT=600` was needed — the default 30s timed out fetching deps through
the direct (non-proxied) PyPI path.

## Findings

**Pre-fix negative-control record (plan Verification requirement).** The D2 negative controls
(`test_transition_finalize_refuses_when_actionable_finding_pending`,
`test_archive_refuses_when_actionable_finding_pending`) fail against the pre-fix code: the independent
verification sub-agent confirmed via `git show origin/main:_cmd_lifecycle.py` that the pre-fix module has
zero references to `assert_finalize_findings_clean` / `blocking_findings` / `_finalize_findings_refusal`,
so pre-fix a pending actionable finding does NOT prevent `cmd_transition --completed 6-finalize` from
setting `current_phase='complete'` nor a no-reason `cmd_archive` from moving the directory — both return
success. The gate exists only post-fix; the controls therefore demonstrate the change rather than pass
vacuously.

**Verification sub-agent (independent, `general-purpose`) — pass 1.** Verdict: D1 derivation sound; D2
implemented with both consumers covered, negative control confirmed to fail pre-fix, non-vacuous,
abandonment exemption correctly scoped; D3 both directions asserted, no false-fixed path. It found **six
stale-claim gaps in UNTOUCHED files** (the change makes the old arming mechanism false) and **one
over-broad gate interaction** — all recorded per-instance below with disposition:

1. `workflow-integration-git/standards/worktree-handling.md` — "the phase-6-finalize orchestrator already
   does this for the automated-review → branch-cleanup and sonar-roundtrip → next boundaries". **Fixed**
   (commit `491ccd8`) → corrected to the real pre-merge `findings-check` example.
2. `plan-marshall/SKILL.md` guarded-boundaries list still named the never-wired intra-finalize re-issues.
   **Fixed** → replaced with the two real firing sites + the "5→6 is not a firing site" note.
3. `ref-workflow-architecture/standards/findings-pipeline.md` ASCII diagram box named "6-finalize entry +
   intra-finalize re-issues", and the prose pointed to it as "the current wiring state". **Fixed** →
   diagram box and prose corrected (box width preserved).
4. `plan-marshall/references/phase-handshake.md` findings-check verb doc said "intra-finalize
   **boundaries**" / "the intra-finalize **callers**" (plural) / "advance to branch-cleanup". **Fixed** →
   singular pre-merge caller; halt-the-merge phrasing.
5. `plan-marshall/scripts/_handshake_commands.py` `cmd_findings_check` docstring "the two intra-finalize
   callers". **Fixed** → pre-merge findings-check caller + composite capture.
6. `plan-marshall/scripts/phase_handshake.py` CLI docstring "intra-finalize boundaries". **Fixed** →
   pre-merge finalize gate.
7. Archive-gate interaction: the no-reason `cmd_archive` gate would fire on the `planning.md` cleanup pass
   that archives already-`complete` plans, so a legacy plan carrying a stale pending record (the pre-D3
   residue) could be refused at cleanup. **Fixed** → gate scoped to `current_phase == '6-finalize'`, with
   a new `test_archive_of_already_complete_plan_not_blocked_by_pending_finding` exemption test.

Two minor observations the sub-agent raised were **not acted on** with reasons: (a) the run report was
"in progress" at pass-1 time — expected, it is finalized as the last pre-merge commit; (b) the
`--reason` help text lists `normal_completion` as an example value — a latent bypass token, but no
production caller passes it, so it is left as-is (out of this plan's scope).

Re-verification (pass 2) found one surviving stale claim — the `BlockingFindingsPresent` docstring's first
guarded-boundary bullet still asserted the never-emitted `capture --phase 6-finalize` arming — plus a
minor comment residue. Both **fixed** (commit `09229c4`). Pass 3 confirmed **CLEAN**: all stale claims
resolved, both consumers covered, archive-gate scoping sound (no completion path slips through).

**CI / PR-review findings (CodeRabbit, 4 actionable — all fixed in `f043254`):**

1. `_findings_core.py` `resolve_qgate_findings_by_evidence` ignored the `update_jsonl` result — a failed
   write would report the finding in `resolved` while it stayed `pending` (a fail-open). **Fixed** — the
   result is checked; a failed write reports the finding as still-pending. New test covers it. (Real
   correctness defect in my own code.)
2. `branch-cleanup.md` restated the actionable-type list inline (drift risk vs `_ACTIONABLE_FINDING_TYPES`).
   **Fixed** — replaced my new inline list with a reference to the authoritative set. (The pre-existing
   `SKILL.md` classification paragraph already names `_invariants.py` and keeps its inline list for the
   classification it introduces — replied on-thread, left as-is.)
3. `SKILL.md` / `phase-handshake.md` non-blocking resolution list omitted `rejected`. **Fixed** — added
   `rejected` to both (pre-existing inconsistency; the pending query excludes every non-pending resolution).
4. `worktree-handling.md` — my earlier fix miscategorized the finalize `findings-check` as a `capture` /
   `verify --strict` layer-D drift checkpoint; it gates pending findings, not main-checkout drift.
   **Fixed** — removed it from the layer-D example and clarified it is a separate mechanism. (Real defect
   in my own earlier fix.)

All 4 CodeRabbit threads were replied-to and resolved. CI on every head SHA has been `verify / conclusion`
green (the required check).

## Reviewer participation

Expected reviewer population, derived from the `author_login` of each
`automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `reviewed` | Walkthrough comment + review summary "Actionable comments posted: 4" + 4 inline review-thread findings against the diff; all 4 handled and resolved. |
| `cuioss-review-bot` (pr-agent) | `reviewed` | Issue comment "PR Reviewer Guide 🔍 — PR contains tests; No security concerns identified; No major issues detected." Reviewed the diff, no findings. |
| `sourcery-ai` | `rate-limited` | Review body: "you have reached your weekly rate limit of 500000 diff characters." Engaged but did not review this diff. |

**Coverage: 2 of 3 reviewed** (`coderabbitai`, `cuioss-review-bot`); `sourcery-ai` rate-limited (weekly
quota, outside our control). The § Step 8 shortfall disclosure fired: proceeding on 2-of-3, Sourcery's
absence is a quota limit, not a blocker.

## Cost

- **Tokens:** not available to the agent in this session — this interactive Claude Code cloud session
  exposes no token counter to the agent. Stated plainly rather than estimated.
- **Wall-clock:** the run spanned roughly the interval from the first commit
  (`12dfbfe`, plan-directory move) to the merge-gate arming; each `./pw verify` took ~6 minutes and each
  PR CI cycle's `verify / verify` ~11 minutes, and the run drove three verification sub-agent passes.
- **Population:** this single Claude Code cloud session's usage. ⛔ **NOT comparable** to a plan-marshall
  `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary, which a single interactive cloud session does not share. No comparable
  figure is available, so none is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (read from bundle paths; plugin absent, as the lane anticipates). |
| 2 Branch | Done — `claude/blocking-boundary-arms-call-jqwzo9` on `origin`; **harness-assigned** `claude/*` form, kept as-is. |
| 3 Plan directory | Done — `doc/plans/code-intelligence-substrate/110-blocking-boundary-arms-on-a-call-not-a-state/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — every commit carries the `Co-Authored-By: Claude` trailer; D1/D2/D3 addressed. |
| 4 Per-commit gate | Done — every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (ruff `All checks passed!`, mypy `Success: no issues`, `SPDX-header check passed`, plugin-doctor clean). |
| 4 Pushed | Done — no unpushed commit; pushed after every commit. |
| 5 Build gate | Done — `git diff origin/main...HEAD` includes `*.py` → `./pw verify` → **SUCCESS** (19351 passed, 14 pre-existing skips). |
| 6 Verification sub-agent | Done — 3 passes (`general-purpose`); all findings + dispositions in § Findings; final verdict CLEAN. |
| 7 PR cycle | Done — PR **#1199**; all 4 CodeRabbit comments fixed, replied, and resolved; reviewer participation recorded. |
| 8 Merge gate | Conditions 1–3 met; shortfall (2-of-3) disclosed; auto-merge armed once CI green on the report commit (see § below). |
| 8 Bridge | Done — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | Done — appended here. |
| 9 What have we learned | Done — one contract-change proposal recorded below (awaiting operator approval; not shipped in this PR). |

**GitHub access path:** the **GitHub MCP server** (the cloud path). **Branch form:** harness-assigned
`claude/*`. A `/sync-plugin-cache` is **never owed** by a cloud run — it is a machine-local build step
(reads the git-ignored `target/`, writes `~/.claude/`), not a debt this run records.

## What have we learned (Step 9)

**One contract-change proposal, from this run's own evidence.** The `./pw` build (quality-gate and
verify) failed on its first two attempts with `uv` HTTP timeouts fetching dependencies (`pytest`, `uv`
itself) through the direct, non-proxied PyPI path — the default `UV_HTTP_TIMEOUT` of 30 s was too short
for the large wheels on this session's network. Every `./pw` invocation only succeeded with
`UV_HTTP_TIMEOUT=600`. The cloud-plan-lane § "Build gate" gives every `./pw` call a 10-minute *Bash*
timeout but says nothing about `uv`'s own per-request HTTP timeout, so a first-time runner hits this and
may misread it as a build failure.

- **Proposed edit:** add a one-line note to `cloud-plan-lane` § "Build gate" that a fresh cloud session
  should export `UV_HTTP_TIMEOUT=600` (or higher) for `./pw` calls, because the default 30 s times out
  fetching large wheels through the direct PyPI path.
- **Status:** recorded for the operator; **not shipped in this PR** (a contract amendment ships as its own
  `chore/` branch on approval, per Step 9). Never self-approved.

No other contract gap surfaced: the branch/PR/merge cycle, the verification-dispatch loop, and the
report contract all executed as written.

## Residue

- **D3 producer scope (accepted).** `qgate resolve-evidenced` resolves *any* pending Q-Gate finding of
  the phase whose `file_path` is in the evidence set, not only self-review's own. In the common case
  (self-review runs before the wait region) only self-review findings are pending, so this does not
  over-reach; in a wait-region-originated loop-back it could touch another producer's finding whose file
  the fix touched, which is self-corrected by that producer's re-fetch (re-detect → reopen). Left
  unscoped by design; both verification passes accepted it.
- **Sourcery review deferred** (weekly rate limit). A re-request when its quota resets would add a third
  reviewer's coverage but is not blocking (disclosed at the merge gate).
- **`--reason normal_completion` help-text token** (CodeRabbit-adjacent observation): a latent bypass
  value in `manage-status.py`'s `--reason` help, but no production caller passes it; out of this plan's
  scope, noted for a future cleanup.
