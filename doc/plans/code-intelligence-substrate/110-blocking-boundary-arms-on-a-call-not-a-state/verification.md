# Verification — 110-blocking-boundary-arms-on-a-call-not-a-state

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed as PR #1199, squash-merged as `66a5d66` (`fix(finalize): arm the blocking-findings
gate on a state, not a call (#1199)`). Every branch SHA the report cites (`cc7f7a9`, `d03cdf8`,
`27951b7`, `491ccd8`, `09229c4`, `f043254`, `12dfbfe`) is absent from `main` — expected under
squash-merge, and `09229c4` / `f043254` are confirmed as real head SHAs by the PR's review records.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: population — how many plans carry no finalize handshake row | Corpus unreachable → blocked; source-side derivation shows the row is *universally* absent (no emitter), so D2 is a correctness fix | Re-derived at HEAD: still no `capture --phase 6-finalize` call site anywhere in `marketplace/`; the one new emitter is a `findings-check` (which writes no row). Population honestly reported as blocked | CONFIRMED |
| D2 | The absence of a finalize-phase row is itself a blocking condition | Two firing sites: pre-merge `findings-check` (fail-closed) + completion `assert_finalize_findings_clean` (state); both consumers covered; negative controls fail pre-fix | Both sites exist and the completion assertion is genuinely non-vacuous (mutation-proven). But the state-armed site fires at `order: 1100`, **after** the merge at `order: 70`; the merge boundary itself is still armed by a call in a workflow doc; no row-existence assertion exists; and the completion refusal is carried only in a TOON `status` that its one production caller never parses | PARTIAL |
| D3 | Self-review loop-back resolves the findings whose fixes it lands | `qgate resolve-evidenced` resolves only evidenced fixes, leaves unevidenced pending; wired into the delta round; both directions asserted | Implemented and mutation-proven in both directions; wired at `pre-submission-self-review.md` Step 1. One correctness caveat: the evidence set is a two-dot diff across an anchor a loop-back rebase can orphan | CONFIRMED (with a correctness caveat, see § Correctness review) |

## Per-deliverable detail

### D1 — GATE: establish the population (mutates nothing)

- **Required (plan):** *"both counts are reported with the population size, and the
  universal-versus-incidental question is answered"*; with the explicit escape that if no corpus is
  reachable, derive the call-site question from the clone and report the population **blocked**.
- **Claimed (report):** corpus not present in this clone and deliberately not searched for; source-side
  derivation shows no call site emits a finalize-phase capture → the row is **universal**, not
  incidental → D2 is a correctness fix.
- **Found / re-derived at HEAD:**
  - `grep -rn "capture --phase" marketplace/ --include=*.md` returns only *prose about* the arming
    (`references/phase-handshake.md:253`, `findings-pipeline.md:252`, `invariant-check-summary.md:51`)
    and the generic call-site description at `references/phase-handshake.md:357`, which enumerates
    `planning.md` (1-init…4-plan) and `execution.md` (4-plan→5-execute, 5-execute→6-finalize). No
    workflow doc issues `capture --phase 6-finalize`.
  - The single `findings-check --phase 6-finalize` call site is
    `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:697-700` —
    added by this plan.
  - `cmd_findings_check` writes **no** handshake row by contract
    (`_handshake_commands.py:657` — *"Writes NO handshake row"*), so the finalize-phase row is still
    structurally absent at HEAD. D1's central finding survives the fix.
- **Checks run:** the two greps above; false-negative control — the same `grep -rn "capture --phase"`
  pattern does return hits (4 prose sites), so the negative on call sites is a real negative.
- **Verdict:** CONFIRMED. The population counts are honestly reported as blocked-on-corpus rather than
  invented, which is exactly what the plan's *"D1's honesty"* verification clause demands.

### D2 — the absence of a finalize-phase handshake row is itself a blocking condition

- **Required (plan):** ⛔ *"Convert the arming condition from a call to a state: the merge boundary
  asserts the row exists, rather than the row's writer asserting the findings are clean."* Plus:
  *Done when:* the negative control fails before the change and passes after, and a positive control
  confirms a clean plan is still admitted. Plus the Verification clause: *"Both consumers are
  verified, not just the one that was changed."*
- **Claimed (report):** two firing sites — pre-merge `findings-check` (fail-closed) and the
  completion-boundary `assert_finalize_findings_clean` called from `cmd_transition` and `cmd_archive`;
  negative controls fail pre-fix; abandonment exemption scoped.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1459-1492` —
    `assert_finalize_findings_clean(plan_id, metadata)`, self-arming: it hardcodes `'6-finalize'`
    when delegating (`:1489`), so a caller cannot disarm it by passing another phase. Predicate
    unchanged (`_capture_pending_findings_blocking_count`, `:1396-1456`; `_BLOCKING_BOUNDARIES`
    still `frozenset({'6-finalize'})` at `:1231`; raise still gated at `:1449`).
  - `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:194-251` —
    `_finalize_findings_refusal`, the shared refusal helper.
  - `_cmd_lifecycle.py:378-381` — `cmd_transition` gate (`args.completed in _BLOCKING_BOUNDARIES`).
  - `_cmd_lifecycle.py:528-531` — `cmd_archive` gate, scoped to `reason is None and
    current_phase == '6-finalize'`.
  - `branch-cleanup.md:691-708` — the pre-merge `findings-check` gate, documented fail-closed on
    `query_failed`, with the fail-closed behaviour implemented at `_handshake_commands.py:699-713`.
  - Both named consumers of `_BLOCKING_BOUNDARIES` are addressed: `_invariants.py` and
    `_cmd_lifecycle.py` (import at `_cmd_lifecycle.py:15-19`).
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/manage-status/test_manage_status_transition.py
    -o addopts=""` → **68 passed**.
  - Mutation: replaced both gate conditions with `if False and …` (both firing sites disabled) and
    re-ran → **2 failed** —
    `test_transition_finalize_refuses_when_actionable_finding_pending` and
    `test_archive_refuses_when_actionable_finding_pending`, the latter with
    `AssertionError: assert 'success' == 'error'`. Restored from a byte snapshot at
    `/tmp/verify-110-mutsweep/`; `git status --porcelain` clean for that path afterwards. The
    negative controls are **non-vacuous** and would go green only with the gate present, which
    independently reproduces the report's pre-fix claim.
- **Verdict:** PARTIAL. The state assertion is real, self-arming, non-vacuous, correctly scoped, and
  covers both consumers — that half is CONFIRMED. Three shortfalls against the literal deliverable:
  1. **The merge boundary is not the state-armed one.** `branch-cleanup` merges at `order: 70`
     (`branch-cleanup.md:7`); `archive-plan` runs at `order: 1100` (`archive-plan.md:7`). The
     completion state assertion therefore evaluates **after** the merge already happened. The merge
     itself is gated only by the pre-merge `findings-check`, which is *a call an LLM workflow doc must
     issue* — the exact arming shape the plan set out to eliminate. The plan's Problem statement is
     about a plan that **merged** with pending findings; that path is now caught only by a call.
  2. **No row-existence assertion exists.** The literal deliverable is *"the merge boundary asserts
     the row exists"*. Nothing at HEAD asserts a finalize-phase handshake row, and `findings-check`
     deliberately writes none, so the row remains permanently absent. The predicate is re-evaluated
     directly instead — defensible (it asserts the underlying state rather than a proxy), but a
     different mechanism from the one specified.
  3. **The refusal is unobservable at its one production firing site** — see § Correctness review G1.

### D3 — the self-review loop-back path resolves the findings whose fixes it lands

- **Required (plan):** *Done when:* a loop-back that lands a fix transitions the corresponding
  finding, and a finding with no evidenced fix is left alone — **both asserted**. ⚠ *"Do not let this
  auto-resolve a finding whose fix cannot be evidenced."*
- **Claimed (report):** `qgate resolve-evidenced` / `resolve_qgate_findings_by_evidence`; resolves
  only when `file_path ∈ --changed-path`; wired into the delta round; both directions asserted.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:786-857` —
    the function. Evidence test at `:831` (`if file_path and file_path in changed`); the
    write-result check at `:832-847` (`(resolved if updated else left_pending).append(entry)`).
  - CLI: `manage-findings.py:228-235` (handler), `:435-455` (parser, `--changed-path` repeatable,
    `--evidence-sha`).
  - Docs: `manage-findings/SKILL.md:370-382`.
  - Wiring: `phase-6-finalize/workflow/pre-submission-self-review.md:112-126` — delta rounds only,
    evidence computed as `git -C {worktree_path} diff --name-only {since_ref}..HEAD`.
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/manage-findings/test_findings_store.py
    -o addopts=""` → **71 passed**.
  - Mutation 1: replaced the evidence test at `:831` with `if True:` → **3 failed**
    (`test_resolve_evidenced_leaves_finding_whose_file_unchanged`,
    `…_leaves_finding_with_no_file_path`, `…_mixed_batch_partitions_by_evidence`). The
    *important direction* is proven non-vacuous.
  - Mutation 2: replaced the write-result branch at `:847` with an unconditional
    `resolved.append(entry)` → **1 failed**
    (`test_resolve_evidenced_failed_write_reported_as_pending_not_resolved`:
    *"A failed write must not be reported as a resolution"*). The CodeRabbit fail-open fix the report
    claims is real and covered.
  - Both files restored from `/tmp/verify-110-mutsweep/` snapshots; `git status --porcelain` shows
    neither file modified.
  - Path-form compatibility check: the surfacer emits project-relative paths
    (`_self_review_detectors.py:460`, `self_review.py:494` — `str(p.relative_to(project_dir))`), which
    matches `git diff --name-only` output, so the string comparison at `:831` is not structurally
    dead.
- **Verdict:** CONFIRMED, with one correctness caveat (the anchor's ancestry is never checked — see
  § Correctness review G5).

## Correctness review

Defects found by reading the shipped code and its calling workflow docs.

1. **The completion gate's refusal is invisible at its one production caller** (high).
   `manage-status.py:836-838` is the entire exit-code contract:
   `if args.command == 'transition' and isinstance(result, dict) and verify_blocks_transition(result): return 1` / `return 0`.
   `verify_blocks_transition` (`_cmd_lifecycle.py:182-191`) returns True only for `status == 'drift'`
   or an error in `VERIFY_REFUSAL_ERRORS` (`_cmd_lifecycle.py:46-52`), a set that does **not** contain
   `blocking_findings_present`. So a refused `archive` and a refused `transition --completed
   6-finalize` both exit **0** — **measured**, not inferred: driving `main()` in-process for both
   commands with a stubbed pending actionable finding emits the `blocking_findings_present` TOON,
   leaves the plan directory in place, and raises `SystemExit: 0` in both cases (via `safe_main`,
   `file_ops.py:1691`).
   ⚠ **Exit 0 is the documented house contract, not the defect** —
   `pm-plugin-development:plugin-script-architecture/standards/output-contract.md:64,77-87,215`
   requires operation failures to carry `status: error` at exit 0. The defect is the consumption
   side. `archive-plan.md:23-28` states a blanket convention whose exit-0 arm is *"parse the returned
   TOON and use the value as the step describes"* — and § Archive (`:65-75`) **describes no use**: it
   issues `manage-status archive`, then logs `"[STATUS] … Plan archived: {plan_id}"` unconditionally;
   the step's own `mark-step-done --outcome done` was already issued at `:59-63`, *before* the
   archive. The same document shows the correct shape one section earlier — the foreign-PR gate
   (`:44-51`) parses `status` and carries an explicit *"STOP. Do NOT mark the step done and do NOT
   archive."* branch. Consequence: on a real refusal the plan directory is silently not moved, the
   step is recorded `done`, the log claims the plan was archived, and `phase-6-finalize/SKILL.md:1612`
   renders the final output template regardless. It also falsifies the shipped claim at
   `references/phase-handshake.md:253` that *"a missing call is no longer a silent pass"*. This is
   the plan's own archetype — a gate whose firing is indistinguishable from its passing — reproduced
   at the new gate's consumption site.
2. **The state-armed gate fires only after the merge** (medium — see § Adversarial review A6).
   Orders re-read from frontmatter:
   `pre-submission-self-review.md:7 → order: 7`, `branch-cleanup.md:7 → order: 70`,
   `archive-plan.md:7 → order: 1100`. Self-review findings are filed at 7; the merge happens at 70;
   the state assertion runs at 1100. A skipped or mis-parsed pre-merge `findings-check` still lets the
   merge through, and the state gate can then only strand the plan post-merge. Checked and *not*
   found: the gate's nesting under the `state == open AND merge_consent == explicit_yes` barrier
   (`branch-cleanup.md:683`) opens no conditional hole, because § "Merge PR (if not yet merged)"
   (`:1248-1250`) carries the identical condition.
3. **Fail-open branch inside the new gate** (medium). `_cmd_lifecycle.py:242-250`: when
   `assert_finalize_findings_clean` returns `None` (executor unreachable **or a partial query
   failure** — `_invariants.py:1442-1445`, `:1320-1323`), the boundary logs a WARNING and **proceeds**.
   In production the executor is present by construction (the call itself runs through it), so `None`
   there means a genuine query failure, and the plan completes and archives without the invariant ever
   having been evaluated. The docstring defends this by pointing at the pre-merge `findings-check` as
   the fail-closed owner — but that gate is (a) call-armed and (b) already past by the time archive
   runs, so the delegation has no holder at this point in the pipeline.
4. **A documented `--reason` value disarms the gate** (medium). `manage-status.py:322-334` still
   advertises `normal_completion` as an example `--reason`: *"(e.g., low_confidence,
   dangling_worktree, orphan_directory, normal_completion)"*. Any `--reason` bypasses the new gate
   (`_cmd_lifecycle.py:528`). Before this plan the value was inert; after it, an operator or step that
   follows the help text turns the completion gate off. The report lists this as out-of-scope residue;
   it is materially more consequential post-fix than it was pre-fix.
5. **D3's evidence set is a two-dot diff across an anchor a rebase can orphan** (medium).
   `pre-submission-self-review.md:113` computes evidence as
   `git -C {worktree_path} diff --name-only {since_ref}..HEAD`, where `{since_ref}` is the *previous*
   self-review round's `head_at_completion` (`:103-106`). Two rebases can orphan that anchor:
   `finalize-step-sync-baseline` (`order: 3`, `presets: [full]` only) rebases the feature branch onto
   a freshly-fetched `origin/{base_branch}` (`phase-6-finalize/SKILL.md:161,217`), and
   `branch-cleanup` (`order: 70`, every preset, `advances_main_via_rebase: true`) performs the same
   rebase before merging (`branch-cleanup.md:11,356`) — so the exposure is preset-independent. When
   the base advanced, the anchor is no longer an ancestor of `HEAD`, and the two-dot diff (endpoint
   comparison — `git diff A..B` is `git diff A B`) then includes every
   file the upstream advance touched. Those files enter `--changed-path`, and a pending self-review
   finding on any of them is marked `fixed` with detail *"evidenced by landed change … touching …"*
   though no loop-back fix touched it. That is precisely the *"finding marked `fixed` without a
   landed change"* the plan calls strictly worse than leaving it pending. There is no
   `git merge-base --is-ancestor` guard anywhere in the file (`grep -n "merge-base\|is-ancestor\|
   rebase"` on it returns nothing). The `add_qgate_finding` re-surface/reopen mechanism the docstring
   cites as self-correcting only fires if a later round re-surfaces that file — not guaranteed once
   the record reads `fixed` and the round records `done`.
6. **`_BLOCKING_BOUNDARIES` is overloaded** (low). `_cmd_lifecycle.py:378` reuses the *entry*-guard
   set as the *completion*-guard predicate, while `:394` uses it for entry in the same function. With
   one member the two readings coincide. If a second phase were ever added as an entry guard,
   completing it would invoke a helper hardcoded to evaluate `'6-finalize'`
   (`_invariants.py:1489`) — a finalize-named assertion at an unrelated boundary. The comment at
   `:369-377` names the distinction but the code still keys both on one set.
7. **The refuted arming claim survives, unswept, in the findings-invariant test module** (low).
   The run corrected the claim in six production/doc files but not in
   `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py`, which still attributes guards
   to production boundaries D1 proved have no call site: the module docstring (`:9`), the section
   header (`:571`), three test docstrings (`:581`, `:601`, `:621`) and two docstrings inside helper
   prose (`:833`, `:868`) — plus **two further sites the word-keyed sweep would miss**, because they
   carry the attribution in the test *name* without the string "intra-finalize":
   `test_capture_blocks_automated_review_to_branch_cleanup_boundary` (`:156`, docstring `:159`) and
   `test_capture_blocks_sonar_roundtrip_next_boundary` (`:171`, docstring `:174`). The tests
   themselves are sound unit tests of `cmd_capture`'s predicate; only their attribution is false.
   Filed as G7–G10.
8. **The anchor-diff step has no documented failure branch** (low).
   `pre-submission-self-review.md:112-118` issues `git diff --name-only {since_ref}..HEAD` and
   `git rev-parse HEAD` with no stated handling for a non-zero exit. The file's own
   `since_ref_unresolvable` halt (`:146`) governs the *surface* call, which runs after this
   sub-step, so an anchor that no longer resolves fails here first with nothing said about it — an
   undocumented failure in an LLM-executed workflow becomes an improvised one. Filed as G14.

Nothing else in the shipped diff is wrong on the paths I read: the predicate is genuinely unchanged,
the abandonment and already-complete exemptions are correctly scoped and tested, the pre-merge
`findings-check` fail-closed `query_failed` translation is implemented as documented, and the D3
write-result check closes the fail-open CodeRabbit found.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D2 completion gate (transition) | `test_manage_status_transition.py:1851-1870` (negative), `:1873-1885` (positive), `:1887-1897` (knowledge-type) | Gate disabled → `test_transition_finalize_refuses_when_actionable_finding_pending` FAILED |
| D2 completion gate (archive) | `:1899-1916` (negative), `:1918-1928` (positive), `:1930-1946` (`--reason` exemption), `:1948-1960` (dry-run), `:1962-1985` (already-complete cleanup exemption) | Gate disabled → `test_archive_refuses_when_actionable_finding_pending` FAILED (`assert 'success' == 'error'`) |
| D2 assertion helper | `test_phase_handshake_findings.py:890-921` (raises on pending, 0 clean, None unevaluable) | Direct unit coverage of all three returns |
| D2 pre-merge gate | `test_phase_handshake_findings.py:829-877` (envelope parity, worktree refusal, fail-closed `query_failed`) | The fail-closed test drives `_query_pending_count_for_type → None` and asserts `query_failed` |
| D3 | `test_findings_store.py:904-1050` (7 cases), `test_manage_findings_cli.py:269-291` (CLI input shape) | Evidence test forced TRUE → 3 FAILED (`…leaves_finding_whose_file_unchanged`, `…leaves_finding_with_no_file_path`, `…mixed_batch_partitions_by_evidence`); evidence test forced FALSE → 3 FAILED (`…transitions_finding_whose_file_changed`, `…mixed_batch_partitions_by_evidence`, `…premature_resolution_is_self_correcting`); write-check neutralised → 1 FAILED. **Both directions independently non-vacuous** |

Two coverage gaps on load-bearing paths:

- **The fail-open branch is untested.** `_finalize_findings_refusal`'s `blocking is None → proceed
  with WARNING` path (`_cmd_lifecycle.py:242-250`) has no test. `grep -n "unevaluable\|query_failed"
  test/plan-marshall/manage-status/test_manage_status_transition.py` returns nothing; the only
  unevaluable coverage is at the `_invariants` and `findings-check` level.
- **No CLI-boundary test for the new refusal.** `grep -rn "blocking_findings_present" test/
  --include=*.py` returns 14 hits, every one an in-process handler assertion (`result['error'] ==
  …`); nothing drives `main()` and asserts what `manage-status archive` emits to a shell caller.
  I supplied that measurement myself (§ Correctness review 1): the TOON is correct and the exit code
  is 0 — which is contract-conformant, so the missing coverage is of the *TOON envelope at the CLI*,
  not of an exit code. That is the surface defect G1 names.

No vacuous or tautological guard was found among the tests this plan added: every negative control I
mutated went red.

## Report accuracy

Verified claim-by-claim against the tree at `61a43e5`. The following held exactly:

- The D1 derivation (no finalize-phase emitter) — re-derived independently, still true.
- The two firing sites, both consumers of `_BLOCKING_BOUNDARIES` addressed, the self-arming design,
  the abandonment and already-complete exemptions.
- The negative controls fail pre-fix — reproduced by mutation rather than taken on trust.
- All six stale-claim fixes are present at HEAD: `worktree-handling.md:215` (now *"a separate
  mechanism … not a `capture`/`verify --strict` checkpoint"*), `plan-marshall/SKILL.md:253-258`
  (two real firing sites + the "5→6 is not a firing site" note), `findings-pipeline.md:51,117,247-252`,
  `references/phase-handshake.md:244-253`, `_handshake_commands.py:662,669`, `phase_handshake.py:18`.
- All four CodeRabbit fixes are present: the `update_jsonl` result check
  (`_findings_core.py:832-847`, with its test), the `branch-cleanup.md:693` reference to the
  authoritative `_ACTIONABLE_FINDING_TYPES` instead of an inline list, `rejected` added to both
  non-blocking resolution lists (`plan-marshall/SKILL.md:260`,
  `references/phase-handshake.md` / `_invariants.py:83-90`), and the `worktree-handling.md`
  re-categorisation.
- Reviewer participation. Checked against the PR: `sourcery-ai[bot]` review body is verbatim
  *"you have reached your weekly rate limit of 500000 diff characters"*; `coderabbitai[bot]` posted
  *"Actionable comments posted: 4"* against `09229c4`. The 2-of-3 coverage claim holds.

Inaccurate or unverifiable claims:

- **"3 production scripts, 4 test files"** (§ Build gate) — **understated**. `git show --stat
  66a5d66` lists **six** production `.py` files (`_findings_core.py`, `manage-findings.py`,
  `_cmd_lifecycle.py`, `_handshake_commands.py`, `_invariants.py`, `phase_handshake.py`) and four
  test files. The test-file count is right; the production count is half the true figure.
- **"`./pw verify` → SUCCESS, 19351 passed / 14 skipped"** — **UNVERIFIABLE** by design of this audit
  (the brief forbids running the full suite, and the figure is a point-in-time measurement that
  cannot be re-derived from the tree). The targeted files I did run are green.
- **"both consumers covered"** is true of `_BLOCKING_BOUNDARIES` but slightly overstates production
  reach: `phase-6-finalize/SKILL.md:1610` states *"A separate `manage-status transition --completed
  6-finalize` call MUST NOT be issued from this phase"*, so of the two documented completion firing
  sites only `cmd_archive` is reachable in the orchestrated lane. The transition arm is a defensive
  path, not a production one — and `plan-marshall/SKILL.md:256`,
  `references/phase-handshake.md:249` and `findings-pipeline.md:248` all present it without that
  caveat.
- The report's § D2 sentence *"the completion boundary catches a plan that reached completion without
  this gate having run"* (echoed at `branch-cleanup.md:708`) is true of the *state*, but the run
  report never notes that the catch happens **after** the merge and that its refusal exits 0 into a
  caller that does not read it. Not a false statement; an omitted material qualifier on the plan's
  central claim.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **D3 producer scope (accepted)** — `resolve-evidenced` resolves any pending Q-Gate finding of the phase, not only self-review's own | **Open by design** | `_findings_core.py:826-849` iterates every record with `resolution == 'pending'`; there is no `source` filter. Behaviour is as declared; the acceptance still stands |
| **Sourcery review deferred** (weekly rate limit) | **Moot** | PR #1199 merged as `66a5d66`; Sourcery's review body confirms the rate limit. No re-request is possible against a merged PR |
| **`--reason normal_completion` help-text token** | **Still open, and now load-bearing** | `manage-status.py:329` still lists `normal_completion` among the `--reason` examples; `_cmd_lifecycle.py:528` makes any `--reason` bypass the new gate. Filed as G3 |
| **Contract-change proposal: `UV_HTTP_TIMEOUT=600` note in `cloud-plan-lane`** (§ What have we learned, "not shipped in this PR") | **Closed by a later plan** | `git log --grep="#1199"` surfaces `b25cb05 chore(cloud-plan-lane): note UV_HTTP_TIMEOUT=600 for ./pw in cloud sessions (#1202)` |

## Out-of-scope and collateral

The plan's three exclusions were respected:

- **Weakening the predicate** — not done. `_ACTIONABLE_FINDING_TYPES`, the pending-resolution
  aggregation, and the raise guard at `_invariants.py:1449` are byte-for-byte the pre-existing logic;
  `assert_finalize_findings_clean` only delegates to it.
- **Adding more blocking boundaries** — not done. `_BLOCKING_BOUNDARIES` is still
  `frozenset({'6-finalize'})` (`_invariants.py:1231`).
- **Any guard shipped without a negative control** — respected; both new guards carry negative
  controls that I proved go red when the guard is removed.

Collateral beyond the plan's declared surface, all declared in the report and all corrective rather
than additive: `worktree-handling.md`, `plan-marshall/SKILL.md`, `findings-pipeline.md`,
`phase_handshake.py`, `_handshake_commands.py` docstrings. No undeclared change found in the merge
diff — the 19 changed files map one-to-one onto the plan's surface plus the six declared stale-claim
corrections.

## Method and coverage

**What I did.** Read `plan.md` and `report-01.md` in full; read the shipped implementation
(`_invariants.py`, `_cmd_lifecycle.py`, `_findings_core.py`, `manage-findings.py`,
`_handshake_commands.py`, `manage-status.py` main) and the four calling/contract documents
(`branch-cleanup.md`, `pre-submission-self-review.md`, `archive-plan.md`,
`phase-6-finalize/SKILL.md`); re-derived D1's absence claim with a grep whose pattern I confirmed
returns hits elsewhere; re-derived the changed-file counts from `git show --stat 66a5d66`; checked
step ordering from `order:` frontmatter rather than from the report's narrative; verified the PR's
reviewer set through the GitHub API.

**Tests.** Ran three files with `UV_PYTHON=3.12 UV_HTTP_TIMEOUT=600 uv run python -m pytest <file>
-o addopts=""`:
`test_manage_status_transition.py` (68 passed), `test_findings_store.py` (71 passed),
plus the mutation sweep below. Did **not** run `./pw verify` (out of scope per the brief).

**Mutation sweep.** Snapshots written to `/tmp/verify-110-mutsweep/` before any edit; three mutations
applied one at a time (disable both D2 gates; neutralise the D3 evidence test; neutralise the D3
write-result check); each restored by copying the snapshot back, never with git. `git status
--porcelain` confirms neither `_cmd_lifecycle.py` nor `_findings_core.py` is modified in the working
tree at the end of this audit.

**What I could not check.**

- The archived-plan corpus (D1's population question) — machine-local and git-ignored, and the plan
  explicitly forbids searching for it. The population counts remain **UNVERIFIABLE**, exactly as the
  report states.
- The `./pw verify` totals (19351/14) — a point-in-time measurement, not re-derivable from the tree,
  and the brief excludes running the full suite.
- The pre-fix behaviour by direct execution — the branch commits were squashed away, so I reproduced
  the pre-fix condition by mutation instead (disabling the gate), which is equivalent evidence for the
  non-vacuity question and is what I report.
- Runtime behaviour of the LLM-executed workflow docs (whether an orchestrator would in practice parse
  the `findings-check` status, or notice a silent archive refusal). These are prose instructions with
  no executable contract; my findings there are read from the doc text and the exit-code path, not
  from an observed run.
