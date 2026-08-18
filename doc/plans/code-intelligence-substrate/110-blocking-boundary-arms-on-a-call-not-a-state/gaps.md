# Gaps — 110-blocking-boundary-arms-on-a-call-not-a-state

The plan's core mechanism landed and is non-vacuous: `assert_finalize_findings_clean` is self-arming,
both lifecycle completion verbs call it, and every negative control goes red when the guard is
removed (mutation-proven). What remains is that the conversion stopped one step short of the boundary
the plan named. The refusal is carried in the TOON `status` while the process exits 0 (the house
`manage-*` output contract), and the one production caller never parses it — so the gate's firing is
once again indistinguishable from its passing, the plan's own archetype reproduced at the new gate's
consumption site (G1, the load-bearing gap). The state-armed site also runs at `order: 1100`, after
the merge at `order: 70`, so the **merge** boundary is still armed by a call an LLM must issue (G2).
Two further substantive gaps: the completion gate fails open on an unevaluable query with no test, and
a documented `--reason` value silently disarms it. D3's evidence gate is correct in both directions —
both directions independently mutation-proven — but computes its evidence set from an anchor a
loop-back rebase can orphan. The remainder are low-severity doc and report residue.

## G1 — Make the completion-gate refusal observable at its one production caller

- **Kind:** bug
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:23-28`
  (the document's blanket exit-code convention), `:53-63` (`mark-step-done`), `:65-70` (the archive
  call), `:72-75` (the unconditional "Plan archived" log) — the one production caller;
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py:836-838`
  (exit-code contract); `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:46-52`
  (`VERIFY_REFUSAL_ERRORS`)
- **Evidence:** *Measured, not read.* Driving `main()` in-process (`manage-status archive --plan-id X`
  and `manage-status transition --plan-id X --completed 6-finalize`) with
  `_query_pending_count_for_type` stubbed to a pending actionable finding: both emit the
  `blocking_findings_present` TOON, the plan directory survives, and **both raise `SystemExit: 0`**
  (`file_ops.py:1691` `safe_main` → `sys.exit(main_fn())`). The reason is structural: the whole
  exit-code contract is
  `if args.command == 'transition' and isinstance(result, dict) and verify_blocks_transition(result): return 1` / `return 0`,
  so `archive` can never return non-zero at all, and for `transition`
  `verify_blocks_transition` fires only on `status == 'drift'` or an error in `VERIFY_REFUSAL_ERRORS`
  — a five-member set that does not include `blocking_findings_present`.
  ⚠ **Exit 0 is the correct house behaviour, not the defect.**
  `pm-plugin-development:plugin-script-architecture/standards/output-contract.md:64,77-87,215`
  mandates *"Operation failures use `status: error` with exit 0"*; the defect is entirely on the
  consumption side. `archive-plan.md:27` states the exit-0 arm as *"parse the returned TOON and use
  the value as the step describes"* — and § Archive (`:65-75`) **describes no use**: it issues the
  call, then logs `"[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"`
  unconditionally, having already recorded `mark-step-done --outcome done` at `:59-63`. The same
  document demonstrates the correct shape one section earlier — the foreign-PR gate at `:44-51` parses
  `status` and has an explicit `status: blocked` → *"STOP. Do NOT mark the step done and do NOT
  archive."* branch. `grep -rn "blocking_findings_present" test/ --include=*.py` returns 14 hits, all
  in-process handler assertions (`result['error'] == ...`) — no test asserts anything about the CLI
  surface.
- **Why it matters:** on a real refusal the plan directory is not moved, the step is recorded `done`,
  the log says the plan was archived, and `phase-6-finalize/SKILL.md:1612` then renders the final
  output template regardless (*"This step ALWAYS runs"*). The gate fires and nothing downstream can
  tell. This is the exact failure mode the plan exists to remove, relocated from the arming side to
  the consumption side — and it falsifies the shipped claim at
  `plan-marshall/references/phase-handshake.md:253` that *"a missing call is no longer a silent
  pass"*, which holds only if the completion refusal is observable.
- **Action:** amend `archive-plan.md` § Archive to parse the returned TOON `status` before the "Plan
  archived" log, with an explicit `error: blocking_findings_present` branch modelled on the
  foreign-PR gate at `:44-51` (route the pending findings through `verification-feedback` /
  loop-back, do not log the archive, do not run the session-store sweep), and move `mark-step-done`
  so a refused archive is not recorded `done`. ⚠ **Do not "fix" this by making the CLI exit
  non-zero** as the primary remedy — that contradicts `output-contract.md:64,215`. If a non-zero exit
  is wanted as a belt-and-braces second signal, it must be shipped as an *explicit, documented*
  deviation of the same kind `transition`'s drift arm already is (widen `verify_blocks_transition`
  or add a sibling predicate sharing one classifier, and state the deviation in
  `output-contract.md`).
- **Done when:** `archive-plan.md` § Archive contains a documented `blocking_findings_present`
  branch that suppresses the archive log and the `done` outcome; and a test drives
  `manage-status archive` through `main()` with a pending actionable finding and asserts the emitted
  TOON carries `status: error` / `error: blocking_findings_present` (plus, only if the deviation
  above is taken, the chosen exit code).
- **Effort:** M
- **Risk if fixed:** `mark-step-done` reordering interacts with the "archive invalidates the live
  path" constraint documented at `archive-plan.md:55` — the record must still land before the move.
  Any orchestrator that treated the archive step as infallible will now see a new terminal failure.

## G2 — Arm the merge boundary itself on a state, not on a workflow-doc call

- **Kind:** incomplete
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:7`
  (`order: 70`) and `:691-708` (the pre-merge gate);
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:7`
  (`order: 1100`)
- **Evidence:** the plan's D2 requires *"the merge boundary asserts a state that must hold rather than
  trusting a call that must happen"*. The state assertion
  (`_cmd_lifecycle.py:528-531` → `_invariants.py:1459`) is reached only from `archive-plan`, which
  runs 1030 order-units after the merge. The merge is gated only by
  `phase_handshake findings-check --phase 6-finalize`, an instruction in a markdown workflow whose
  verdict an LLM must parse (`branch-cleanup.md:701-706` — *"parse `status`, never the exit code"*).
  A skipped, mis-parsed, or reordered step re-opens exactly the original defect.
- **Why it matters:** the plan's Problem statement is about a plan that **merged** with nineteen
  pending findings. After this fix that merge is still possible; only the subsequent archive is
  refused, which strands the plan post-merge instead of preventing the bad merge.
- **Action:** move the assertion inside the merge action rather than beside it — have the merge-side
  helper (`ci pr safe-merge` / `merge-queue enqueue` path, or a small pre-merge assertion entry point
  in `phase_handshake`) evaluate the blocking-findings state itself and refuse non-zero, so the merge
  cannot proceed without the predicate having been evaluated. The workflow-doc call then becomes
  advisory rather than load-bearing.
- **Done when:** a negative control shows the merge action itself refusing on a pending actionable
  finding **without** any workflow-doc `findings-check` call having been issued, and a positive
  control shows a clean plan merging.
- **Effort:** L
- **Risk if fixed:** the merge path is operator-consent-bound and already carries several barriers
  (`branch-cleanup.md:683-690`); an extra fail-closed predicate there can strand a merge on an
  unevaluable store. The `query_failed` disposition must be routed to the existing
  "UNKNOWN disposition" path rather than to a hard halt.

## G3 — Remove `normal_completion` from the `--reason` help, or stop letting `--reason` disarm the gate

- **Kind:** bug
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py:322-334`
  (help text, `normal_completion` at `:329`);
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:528`
  (`getattr(args, 'reason', None) is None and …`)
- **Evidence:** the help text reads *"Optional structured reason string recorded alongside the archive
  (e.g., low_confidence, dangling_worktree, orphan_directory, normal_completion)"*. The gate at
  `:528` fires only when `--reason` is absent, so `manage-status archive --reason normal_completion`
  archives a plan with pending actionable findings and logs nothing about it.
- **Why it matters:** the exemption is meant to cover *abandonment* — a deliberate close of a plan
  that will never be clean. `normal_completion` is by name the opposite case, and it is advertised in
  the tool's own help. An operator or a future step following that help silently turns off the merge
  gate this plan shipped. The report flags it as out-of-scope residue; post-fix it is a documented
  bypass token, not a cosmetic one.
- **Action:** drop `normal_completion` from the help enumeration (a genuine normal completion passes
  no `--reason`); optionally tighten the exemption to a closed abandonment vocabulary so an arbitrary
  string cannot bypass.
- **Done when:** `grep -rn "normal_completion" marketplace/` returns nothing, and a test asserts that
  the gate still fires for at least one non-abandonment `--reason` value if the vocabulary is closed.
- **Effort:** S
- **Risk if fixed:** if any operator runbook or archived status.json already carries
  `archived_reason: normal_completion`, closing the vocabulary would reject it. Removing the help
  example alone carries no runtime risk.

## G4 — Decide and test the completion boundary's unevaluable-query disposition

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:242-250`
  (the `blocking is None` branch); `_invariants.py:1442-1445` and `:1320-1323` (where `None` is
  produced)
- **Evidence:** `if blocking is None: log_entry(… 'WARNING' … 'was unevaluable … — proceeding; the
  pre-merge findings-check gate owns the fail-closed path'); return None`. `None` is produced by a
  **partial query failure**, not only by an absent executor (`_invariants.py:1442-1445`: *"Partial
  query failure — fall back to 'not applicable'"*). At archive time the executor is present by
  construction, so `None` means the store could not be read — and the plan completes anyway. The
  delegation to the pre-merge gate has no holder here: that gate ran 1030 order-units earlier and is
  itself call-armed (G2). `grep -n "unevaluable\|query_failed"
  test/plan-marshall/manage-status/test_manage_status_transition.py` returns nothing — the branch is
  untested.
- **Why it matters:** the plan forbids a vacuous guard. A guard that proceeds whenever it cannot
  evaluate itself is passable by breaking the thing it reads, and the run report presents the
  completion boundary as the state that closes the hole.
- **Action:** either (a) fail closed at the completion boundary too, returning the same
  `query_failed` envelope `cmd_findings_check` returns (`_handshake_commands.py:699-713`), or
  (b) keep the fail-open but justify it against a holder that actually runs at that point in the
  pipeline. Whichever is chosen, add the missing test.
- **Done when:** a test stubs `_query_pending_count_for_type` to `None` and asserts the chosen
  disposition for both `cmd_transition --completed 6-finalize` and a normal `cmd_archive`, including
  the WARNING/refusal envelope.
- **Effort:** S
- **Risk if fixed:** failing closed could strand a plan in a degenerate environment where the findings
  subsystem is genuinely unreachable — the exact scenario the current comment cites. Pair any switch
  to fail-closed with a documented override.

## G5 — Guard D3's evidence set against a rebased anchor

- **Kind:** bug
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:112-126`
  (the `git -C {worktree_path} diff --name-only {since_ref}..HEAD` evidence computation);
  consumed by `_findings_core.resolve_qgate_findings_by_evidence`
  (`marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:831`)
- **Evidence:** `{since_ref}` is the previous self-review round's `head_at_completion`. A loop-back
  re-enters finalize, whose `order: 3` step `finalize-step-sync-baseline` rebases the feature branch
  onto a freshly-fetched `origin/{base_branch}` (`phase-6-finalize/SKILL.md:161,217`). When the base
  advanced, `{since_ref}` is no longer an ancestor of `HEAD` and the two-dot diff includes every file
  the upstream advance touched. Those paths enter `--changed-path`, and `:831`
  (`if file_path and file_path in changed`) then marks the matching pending finding `fixed` with
  detail *"evidenced by landed change {sha} touching {file}"*. `grep -n
  "merge-base\|is-ancestor\|rebase"` on the workflow file returns **nothing** — there is no ancestry
  check.
- **Why it matters:** the plan states in D3 that *"a finding marked `fixed` without a landed change is
  strictly worse than one left `pending`"*. This path produces exactly that, on the ordinary
  loop-back route, whenever `main` moved during the loop-back. The docstring's self-correction
  argument (`_findings_core.py:808-810`) only holds if a later round re-surfaces the file, which a
  `fixed` record and a `done` outcome do not guarantee.
- **Action:** in the workflow doc, gate the resolve sub-step on
  `git -C {worktree_path} merge-base --is-ancestor {since_ref} HEAD` succeeding; when it fails (the
  anchor was rewritten), **skip the resolution** for that round and say so, rather than resolving
  against a diff that spans an upstream advance. Alternatively derive the evidence set from the
  loop-back's own commits rather than from a range endpoint.
- **Done when:** the workflow file documents the ancestry precondition and the skip branch, and a test
  or worked example shows a post-rebase round leaving prior findings `pending` rather than resolving
  them.
- **Effort:** M
- **Risk if fixed:** skipping resolution on a rebased anchor means more findings stay `pending` into
  the merge gate — which, with G1/G2 fixed, is a refusal rather than a silent pass. Pair with a clear
  operator message.

## G6 — Assert the finalize-phase handshake row, or retire the row from the contract

- **Kind:** omission
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py:657`
  (*"Writes NO handshake row"*); `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md:244-253`
- **Evidence:** D2's literal wording is *"the merge boundary asserts the row exists"*. Nothing at HEAD
  asserts a `6-finalize` handshake row, and the only finalize-phase emitter added
  (`findings-check`) deliberately writes none, so the row remains permanently absent on every plan —
  the condition D1 identified is unchanged. The deliverable was satisfied by a different mechanism
  (re-evaluating the predicate directly).
- **Why it matters:** low, because the substitute mechanism is arguably stronger — it asserts the
  underlying state rather than a proxy for it. But the plan's Problem section warns that *"anything
  reading it as one — including any audit counting 'plans that merged clean' — is reading a number
  nobody computed"*, and that remains true: no finalize row exists for a retrospective to read. No
  consumer reads one today (`grep -rln "pending_findings_blocking_count"` finds no
  retrospective/audit script), so this is latent, not live.
- **Action:** decide explicitly — either have the completion boundary persist a finalize-phase
  attestation row on a clean pass (so a retrospective can distinguish "evaluated clean" from "never
  evaluated"), or state in `references/phase-handshake.md` that no `6-finalize` row is ever written
  and that the absence carries no meaning.
- **Done when:** `references/phase-handshake.md` states the chosen contract, and if a row is written,
  a test asserts it exists after a clean completion and is absent after a refusal.
- **Effort:** M
- **Risk if fixed:** writing a row at completion adds a write to the archive path; a partial write
  there would leave a plan half-completed.

## G7 — Correct the stale "automatic-review → branch-cleanup intra-finalize re-capture" test claim

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py:574-591`
  (`test_pending_pr_comment_blocks_automated_review_to_branch_cleanup`, docstring at `:581`)
- **Evidence:** the docstring reads *"automatic-review → branch-cleanup intra-finalize re-capture."*
  This plan's D1 established that no such boundary re-capture exists or ever existed; the run swept
  the same claim out of six production/doc files but left the test file untouched.
- **Why it matters:** the test is a fine unit test of `cmd_capture`'s predicate, but its name and
  docstring assert a production scenario the codebase does not have. A reader auditing the arming
  question next will find "evidence" of the wiring in the test suite.
- **Action:** rename/re-document to describe what it actually pins — the blocking raise for a pending
  `pr-comment` at a `6-finalize` capture — with no boundary attribution.
- **Done when:** the test name and docstring name no production boundary that has no call site.
- **Effort:** S
- **Risk if fixed:** none beyond a test rename.

## G8 — Correct the stale "sonar-roundtrip → next intra-finalize re-capture" test claim

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py:594-611`
  (`test_pending_sonar_issue_blocks_sonar_roundtrip_to_next`, docstring at `:601`)
- **Evidence:** docstring: *"sonar-roundtrip → next intra-finalize re-capture."* The run report
  itself records (§ D1) that `phase-6-finalize/workflow/sonar-roundtrip.md` contains **no**
  `phase_handshake` call.
- **Why it matters:** same as G7 — a named production boundary that does not exist, preserved in the
  suite after the doc sweep corrected it everywhere else.
- **Action:** rename/re-document to the predicate it actually pins (pending `sonar-issue` blocks a
  `6-finalize` capture).
- **Done when:** the test no longer attributes itself to a `sonar-roundtrip` boundary.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Correct the stale "intra-finalize re-capture loop-back contract" test claim

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py:614-634`
  (`test_intra_finalize_recapture_clears_after_resolution`, docstring at `:621`)
- **Evidence:** docstring: *"The intra-finalize re-capture loop-back contract: clears after fix."*
  The test drives two `cmd_capture --phase 6-finalize` calls, an invocation no orchestration step
  issues.
- **Why it matters:** it names a "contract" that has no implementation, in the file a future auditor
  of this exact question will read first.
- **Action:** rename to describe the capture-level clear-after-resolution behaviour without the
  intra-finalize framing.
- **Done when:** the test name and docstring carry no "intra-finalize contract" claim.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Correct the remaining "intra-finalize" prose in the findings-invariant test module

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py:9` (module docstring,
  *"the intra-finalize re-capture boundary guards"*), `:571` (section header
  *"(f) intra-finalize boundary re-capture (production scenarios)"*), `:833`
  (*"the two intra-finalize callers"*), `:868` (*"The intra-finalize boundary must not advance to
  branch-cleanup"*)
- **Evidence:** four further sites in the same file repeating the arming claim this plan refuted.
  `:833` in particular says *"the two intra-finalize callers"* — the exact phrase the run corrected
  in `_handshake_commands.py`'s docstring (report § Findings item 5) without correcting its mirror in
  the test.
- **Why it matters:** the run's stale-claim sweep covered production docstrings and standards docs but
  not tests, so the refuted claim survives in the suite that documents the very invariant.
- **Action:** replace with the two real firing sites (pre-merge `findings-check`, completion-boundary
  state assertion), matching the corrected wording already in `_handshake_commands.py:662` and
  `references/phase-handshake.md:244-253`.
- **Done when:** `grep -rn "intra-finalize" test/` returns nothing, or returns only text that
  describes the claim as historical.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Correct the run report's production-file count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/110-blocking-boundary-arms-on-a-call-not-a-state/report-01.md`
  § Build gate (*"includes `*.py` (3 production scripts, 4 test files)"*)
- **Evidence:** `git show --stat 66a5d66` lists six production `.py` files — `_findings_core.py`,
  `manage-findings.py`, `_cmd_lifecycle.py`, `_handshake_commands.py`, `_invariants.py`,
  `phase_handshake.py` — plus the four test files. The test count is correct; the production count is
  half the true figure.
- **Why it matters:** confined to the run report, but the figure is the stated basis for the build
  gate firing, and a retrospective reading it under-states the change's production footprint.
- **Action:** correct to six production scripts, or state the count as of the commit it described.
- **Done when:** the report's figure matches `git show --stat 66a5d66`.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Separate the entry-guard set from the completion-guard predicate

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:369-381`
  (completion use) and `:383-394` (entry use); `_invariants.py:1231` (`_BLOCKING_BOUNDARIES`),
  `:1489` (hardcoded `'6-finalize'`)
- **Evidence:** the same one-member frozenset keys two different questions in one function — the
  phase being *completed* at `:378` and the phase being *entered* at `:394`. The helper it dispatches
  to hardcodes `'6-finalize'` regardless. The inline comment at `:369-377` names the distinction but
  the code does not encode it.
- **Why it matters:** benign today. If a second phase were ever added as an entry guard, completing
  that phase would invoke a finalize-named assertion at an unrelated boundary — a silent
  mis-evaluation with no test to catch it.
- **Action:** introduce a distinct constant (e.g. `_COMPLETION_ASSERTED_PHASES = frozenset({'6-finalize'})`)
  for the completion use, leaving `_BLOCKING_BOUNDARIES` to mean entry only, and document both.
- **Done when:** the two uses read from two named sets, and a test adding a second member to the entry
  set does not change completion behaviour.
- **Effort:** S
- **Risk if fixed:** a second constant is one more thing to keep in sync; the docs that currently cite
  `_BLOCKING_BOUNDARIES` (`references/phase-handshake.md:357`) would need the new name.

## G13 — Qualify the documented "transition --completed 6-finalize" firing site

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md:256`;
  `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md:249`;
  `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/findings-pipeline.md:248`
- **Evidence:** all three present *"`manage-status transition --completed 6-finalize` and a
  normal-completion `manage-status archive`"* as the completion firing sites. But
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1610` states: *"A separate
  `manage-status transition --completed 6-finalize` call MUST NOT be issued from this phase; it would
  fail with `file_not_found` because archive has already invalidated the live path."*
- **Why it matters:** a reader counting production coverage sees two guarded completion paths where
  the orchestrated lane has one. It inflates the apparent robustness of the D2 fix — the same
  overstatement class the run's own stale-claim sweep was hunting.
- **Action:** in all three docs, mark the `transition` arm as a defensive path for non-orchestrated
  callers and name `archive` as the orchestrated firing site, cross-referencing
  `phase-6-finalize/SKILL.md`'s prohibition.
- **Done when:** each of the three sites names which arm the finalize orchestrator actually reaches.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — Define the failure handling for an unresolvable delta anchor before the resolve call

- **Kind:** omission
- **Severity:** low
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:118-126`
- **Evidence:** the doc issues `git -C {worktree_path} diff --name-only {since_ref}..HEAD` and
  `git rev-parse HEAD` with no stated handling for a non-zero exit. The surfacer's own
  `since_ref_unresolvable` refusal (documented further down the same file) applies to the *surface*
  call, which happens **after** this resolve sub-step, so an anchor that no longer resolves fails
  here first with no documented branch.
- **Why it matters:** an undocumented failure in an LLM-executed workflow becomes an improvised one.
  The safe action is to skip the resolution (leaving findings pending); nothing says so.
- **Action:** state that a failed anchor diff skips the resolve sub-step and proceeds to the surface
  call, which owns the `since_ref_unresolvable` halt. Fold naturally into the G5 fix.
- **Done when:** the workflow file documents the skip branch for a failed `git diff` at this step.
- **Effort:** S
- **Risk if fixed:** none.
