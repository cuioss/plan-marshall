# Landing Analysis: PLAN-LB-172 — Consolidated left-over fixes of the PLAN-LB-162 to PLAN-LB-171 landings

epic: live-blockers
workstream: WS-04
pr: #2036 (https://github.com/cuioss/plan-marshall/pull/2036) — MERGED as `78951e23c34791f8c2d246cd6350bee9095e08de`

> Landing record for one plan, in two parts. The first message (`-001`) was a PARTIAL landing: PR open, five of ten
> deliverables, six unresolved threads; it was recorded as such and the row held at `running`. The lane was then
> restarted on the operator's word, resumed from its progress file, shipped D6 to D10, dispositioned every review item
> and merged. This report is the full-ship record from the second message (`-002`). Every figure is labelled OBSERVED
> (re-read by the orchestrator) or CARRIED (the lane's own statement, not re-read).

## Deliverable Fidelity vs Spec

The spec is `plans/PLAN-LB-172-consolidated-leftover-fixes.md` (ten deliverables). OBSERVED against git: the squash
commit `78951e23c` (one parent, `a768b788f`, the ledger land of #2037) changes 54 files, 3470 insertions and 774
deletions; the PR's own branch history lists D1 to D5 (`a39aa80d6` to `a8bd2ffac`) and D6 to D10 (`321aac6c3`,
`29d0254c7`, `0e6e52bdc`, `976e24c2d`, `1acfd12f9`), CARRIED from the lane's progress file and message.

**All ten deliverables shipped.** The lane's `deliverables_done=5` is not a count of shipped work: it counts the five
deliverables (D6 to D10) whose red runs THIS session recorded; D1 to D5 are shipped and green, but their `test-first`
artifacts belong to the interrupted session and were not preserved, so under the Evidence rule their Done-whens are
"met on the tree, not evidenced". The lane says so in its own message; the integer alone would mislead a reader.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 review-body parser never under-counts | shipped-as-specified, not evidenced (carried red runs); one gap at layer 3 | `runbook_lane.py` and the review-gate test file in the diff (OBSERVED). Layer 3: a fence-only section reads 0 (see below). |
| 2 Sonar carry-forward binds itself, decision-verb edges | shipped-as-specified in the form the spec allowed; the binding stays optional for a caller (layer 3) | `sonar.py`, `runbook_lane.py` and the three test files in the diff (OBSERVED). |
| 3 runbook-lane text, docstrings, tests | shipped-modified (code, not text, was wrong) | OBSERVED by the leaf at `runbook_lane.py:1753`: a delegating consumer's paths all answer `buildable` with the delegation named. Two docstrings still describe the removed fallback (layer 3, minor). |
| 4 PR body slot | shipped-as-specified | OBSERVED by the leaf at `ci_base.py:211`/`:383`: anchored `\A…\Z` with `fullmatch`, slot validated before kind; the plan id and the derived `body_slot` are separate values. |
| 5 analyze and handle-open contracts | shipped-as-specified, with a two-reference-point wording in `landing-payload-spec.md` (layer 3, minor) | the five documents and both contract tests in the diff (OBSERVED). |
| 6 `/apply-changes` gap evidence, parity guard | shipped | the three entry points and `test_apply_changes_command_parity.py` in the diff (OBSERVED). The guard sees only withholding keys whose name contains `disable` or `withhold` (leaf, minor). |
| 7 `get use_worktree` failed read | shipped | `_cmd_orchestrator.py` and its test in the diff (OBSERVED). |
| 8 retirement-criteria edges | shipped | `_criteria_snapshot.py`, `_review_support_validate.py`, `review_support.py`, `test_retirement_decision_d4.py` in the diff (OBSERVED). The leaf found it fail-closed. |
| 9 execution-manifest edges | shipped | `_manifest_rules.py`, `manage-execution-manifest.py`, `decision-rules.md`, five tests in the diff (OBSERVED). |
| 10 build-server job log, routed client | shipped; the post-run half of its Done-when does not hold (layer 3, major) | `marshalld.py`, `_marshalld_supervisor.py`, `_build_execute_factory.py`, `build_server.py` in the diff (OBSERVED). |

### The merge record contradicts the merge

OBSERVED through the CI abstraction (`ci pr view 2036`): the PR body, and with it the squash commit message, still
carries the interrupted session's text — "Five of the spec's ten deliverables are shipped in this PR", "Not shipped:
D6 to D10 — not started" and test evidence for D1 to D5 only. The diff ships all ten. The landing message (`-002`)
and this report are the correct record; the commit message of `78951e23c` is wrong about the plan's own scope and
cannot be amended on `main`. Correcting the PR body is an outward-facing act and is the operator's call.

### Surface drift

The spec's Expected Surface declared 50 paths. OBSERVED from the merged file list:

- **Changed, not declared (11):** `build-server-client/scripts/build_server.py`,
  `script-shared/scripts/build/_build_execute_factory.py`, `phase-6-finalize/standards/review-rubric.md`, and eight
  tests (`test_build_execute_routing.py`, `test_build_server_client.py`, five under `manage-execution-manifest/`,
  `phase-6-finalize/test_review_support.py`). The lane's message names the first two; the PR body names none. The
  leaf traced every one to a deliverable (D10 for the build-server files, D8 for the rubric and the review-support
  test, D9 for the manifest tests): no unexplained file.
- **Declared, not changed (7):** `_build_result.py` and `_build_server_protocol.py` (D10 named them as the place the
  routed client folds `log_file_failed`; the fold site is the factory and the client passthrough, neither declared),
  `workflow-integration-sonar/SKILL.md`, `test_sonar_analysis_revision.py`, `test_orchestrator_scope.py`,
  `test_build_result.py`, `test_build_execute_factory.py`.

The under-declaration of D10 is a defect in this orchestrator's own spec (its HYPOTHESIS said the factory was not
read at the landing; it was the fold site). It is recorded, not corrected in place: the plan is shipped.
`plans/PLAN-LB-173-…` carries the same declaration and is not emitted (see Follow-Ups).

## Three-Layer Analysis

- **Dispatch:** one `execution-context-level-5` leaf, read-only, on the `orchestrator.analyze` surface (resolved
  through `manage-config effort resolve-target`, which wrote the `[DISPATCH]` record). Reason: reading 54 changed
  files across ten deliverables is the depth the dispatch rule exists for; the spec crossed the edge as data (a
  condensed excerpt of the deliverables, Done-whens and Expected Surface in the session scratchpad, since the leaf
  may not open `.plan/`). Its report was 36 findings and 8 conformance rows.
- **Re-read by the orchestrator before recording** (each at its `file:line`): `_build_execute_factory.py:805-840`
  and `_build_shared.py:775-805`; `_marshalld_supervisor.py:680-715`; `runbook_lane.py:2530-2579`, `:3695-3716`,
  `:4160-4199`, `:1330-1353`; `_manifest_rules.py:73-102`; `test_analyze_false_claim_contract.py:205-221`. Every
  other `checked` point of the leaf is recorded below as a **leaf reading, not re-read**.
- **Not re-read at all:** `_mask_fenced_code` itself (located by name, not at a line; the fence defect below rests on
  its two re-read ends and on the leaf's statement that it blanks a fence); the red-at-base order of every Done-when
  (only a run shows it); the lane's build logs and test counts.

### Layer 1 — Specified

The premises hold against `c22d103fb` (the leaf checked D1, D3, D4, D7 and D9 against the removed hunks and D10's
pre-spawn leg). Two spec defects, both of this orchestrator's own authoring:

- **(major, leaf reading, re-read at the code)** D2(a) allowed the mechanism "refuse when `count_status_reason`
  names a carry-forward and no marker arrives". That binds only when the caller passes the reason; a caller that
  drops the reason and the flags reaches the original failure (a plain `merge_allowed` for a carried-forward read).
  The Done-when is met because its test supplies the reason. The lane chose a mechanism the spec permitted;
  the spec did not close the premise it was written to close. OBSERVED at `runbook_lane.py:2554-2566`: the refusal
  fires only when the reason is non-empty and starts with the carry-forward prefix.
- **(minor, leaf reading)** D10's Expected Surface named the wrong fold site (see Surface drift).

**Layer 1 verdict:** sound with defects (two, both spec-authoring)

### Layer 2 — Implemented

Every deliverable traces to code and to a test (the file set above, OBSERVED; the test bodies are the leaf's reading).

- **(major, record fidelity, OBSERVED)** The merge commit and PR body say D6 to D10 did not ship; they did. See above.
- **(major, leaf reading, partly re-read)** D10's Done-when "a `log_file_failed` result reaches the caller with its
  reason" is tested with `exit_code -1` only, at `_daemon_result_to_direct`, never through `cmd_run_common`; the
  post-run leg does not meet it (the layer-3 defect below).
- **(minor, leaf reading)** `test_runbook_lane_sonar.py:787` passes the decision's own sentence as `--count-status-reason`,
  which `SKILL.md` says is a separate value from the read's `carried_forward_from_analysed_head`: the test pins an input
  the documented flow never supplies.
- **(minor, partly re-read)** `test_analyze_false_claim_contract.py:216` swallows every exception around the review-gate call
  (OBSERVED), so the "no shell-out" control passes vacuously for any early failure; the leaf adds that its fixture at `:385`
  runs `gh api` unmocked (not re-read).
- **(minor, leaf reading)** D2(d) asks for one flag spelling per value; `sonar-facts` gained a hidden alias on the same
  `dest` (`runbook_lane.py:5021-5032`), so two spellings remain and conflicting values resolve last-wins.
- Not shown by reading: that each new test fails at `c22d103fb`.

**Layer 2 verdict:** implemented with gaps

### Layer 3 — Correct

Three majors, each stated with the line, the trigger and the effect:

1. **A post-run routed log fault renders as `build_failed`, its class and reason lost** (D10). OBSERVED:
   `_build_execute_factory.py:826-840` returns `error_result(daemon_fault, daemon_exit, …)` and deliberately keeps the
   child's own exit code (`:828-832`: "only a PRE-SPAWN fault has none"); `_build_shared.py:791` routes to the
   launch-fault leg only for `exit_code == -1`; the supervisor passes the observed exit code with `log_file_failure_payload`
   at `_marshalld_supervisor.py:688-706`. The two halves disagree: a post-run fault carries exit 0 or 1, so it falls through
   to the build-failure path (`_build_shared.py:1119`, leaf reading, the fall-through itself not re-read). Trigger: a routed
   job whose log is removed or unwritable while the child runs. Effect: a red build with a synthetic "see full log"
   row for a log that does not exist; the widened vanished-log check of D10 never reaches the caller.
2. **The Sonar carry-forward binding is optional for the caller** (D2, and the declined "caller-asserted provenance" item).
   OBSERVED: `--count-status-reason` is read with `getattr(args, 'count_status_reason', None) or ''` at
   `runbook_lane.py:2554` and the refusal needs it; the leaf adds that `sonar.py:1296` reports `count_status: confirmed`
   on a carried-forward read (not re-read). Trigger: a lane that copies `count_status` and `open_count` but drops the reason
   and the marking. Effect: a plain `merge_allowed` from `sonar-gate`, and a current-head figure from `sonar-facts`.
   (Sonar is not enabled in this repository; the defect is in the lane text consumed by Sonar-enabled projects.)
3. **A fence-only review section reads zero findings** (D1). OBSERVED ends: `_body_findings` masks fences before any
   structural read (`runbook_lane.py:4176`), and `_count_section_findings` returns `0` for a span with no rows, no
   nested counts and no text (`:3715`). Leaf reading: `_mask_fenced_code` blanks a fenced block, so a section with no
   declared count whose only content is a fence (for example a `Nitpick comments` summary followed by a suggested
   diff) reads 0 where it read 1; the gate can then answer `all_handled`. Trigger: constructed; bots usually
   declare counts. Effect: an under-count to zero, the direction the spec's count-or-stop rule forbids.

Minors, grouped by file; the first four are re-read, the rest are the leaf's reading and not re-read:

- `_manifest_rules.py:102` (re-read): a `commit_and_push` value that is present but neither a bool nor a `true`/`false`
  string reads `True`, so reconcile backfills push-only steps into a plan with malformed config. The docstring (`:73-79`)
  states this as the documented default; the absent-file case correctly applies the local-only floor.
- `runbook_lane.py:1349` (re-read): the discovery problem is reported only when every workflow is a symlink; with one regular
  workflow plus a symlinked workflow that opts in, the opt-in is skipped and the rule reads as "no CI rule", which hands the
  decision to the architecture fallback. Whether the CI itself follows the link is not shown.
- `runbook_lane.py:2333`: when the marking arrives without `--count-status-reason`, the fallback sentence still says the delta "is not built".
- `runbook_lane.py:1421-1425`, `:1453-1457`: two docstrings still say a `None` skip set falls back to the architecture prose class; the
  module verb list (`:20-26`) omits `--count-status-reason`.
- `runbook_lane.py:4109`: each heading's findings are built before the body-total cap is checked (about 10^6 dicts for a 65k-char body);
  a resource cost, the declined cap-before-materialising item.
- `landing-payload-spec.md:117-137`, `analyze.md:155`, `landing-analysis.md:104`: the post-merge re-read rule is stated three times, differently; one
  input (a pre-merge record when the gate-read time was not kept) gets two answers; line 137's "named instances" sentence is detached.
- `_cmd_orchestrator.py:343` against `manage-config/SKILL.md:1165` and `api-reference.md:218`: in a plan worktree a caller file with invalid JSON
  answers `unreadable` where the documents say `invalid_json`/`not_object`; drift, not fail-open.
- `_marshalld_supervisor.py:496`: `O_NOFOLLOW` protects the leaf only; an ancestor swapped for a symlink after the check at `marshalld.py:855`
  redirects the open (the declined descriptor-chain walk); low impact, the tree is the same user's.
- `marshalld.py:844`: creation hard-codes `.plan`, so "moving the constant moves the creation" holds only while the constant starts with `.plan`.
- `sonar.py:1000`, `runbook_lane.py:2217`: SHA equality is a hex-prefix comparison of at least seven characters, not a resolved-object comparison.
- `test_apply_changes_command_parity.py:143`: the withholding-key check is a name heuristic (`disable`, `withhold`).
- `manage-execution-manifest.py:3829-3840`: one comment block duplicated; `landing-analysis.md:111`: literal timestamps in a worked example.

**Layer 3 not shown by reading:** the lane's `verify`, test counts and whether each new test fails at the base tree.

**Layer 3 verdict:** defects found — three major, reported to the operator in the same turn

### Conformance to the Project's Own Rules

From the leaf's conformance rows; the first, third (fail-closed part) and the spec-surface rule are OBSERVED in the sections above.

- Spec standing constraint "fail closed" — **deviates**: `runbook_lane.py:2554`, `:4176` with `:3715`, `_manifest_rules.py:102`.
- Spec standing constraint "no file outside the Expected Surface unless the PR body names it" — **deviates**: eleven files, the PR body names none (the lane's message names two).
- Documentation Standards, no duplication — **deviates** (the re-read rule three times; a duplicated comment). Current state only — **deviates** (two stale docstrings). No timestamps — **deviates**, illustrative only. No version history — **conforms** (leaf reading).
- `persona-module-tester`, deterministic tests and no real external process — **deviates** at `test_analyze_false_claim_contract.py:216`/`:385`.
- Spec D2(d), one flag spelling — **deviates** at `runbook_lane.py:5021-5032`.
- Lane-reported (CARRIED): one `ci pr comments` redirect to `.plan/temp/`, three guard refusals (`python3 -m json.tool`, a shell-chained command, a `cp`) none retried around the guard, two concurrent builds serialised by the per-directory lock.

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none. Recorded as an unobserved fact, never as zero; `landing-check` reports `total_tokens` missing, so the landing is `complete: false`, and that alone is no defect (ruling of 2026-10-23).
- Duration: not supplied (`unmeasured` surface delta).
- Harness `opencode`, model `deepseek-v4.1-flash/high`, effort high, executor `0.1.2173` (CARRIED).
- Anomalies: the run was interrupted and resumed (state rebuilt from git and the PR; the progress file shows `setup … RESUME`); `deliverables_done=5` undercounts shipped work (see above); the merge record misstates the scope; two `verify` runs were re-attached through the daemon's bounded wait (CARRIED); the lane's self-review round raised three defects and fixed them before the merge (CARRIED).

## Routing and Merge Behavior

- Review: coderabbit (required). OBSERVED by `runbook_lane review-gate --pr-number 2036` on the merged PR: `unresolved_review_threads: 0` and `review_body_findings_total: 48`; the landing's two numbers match the re-read. `review_body_findings_handled` re-reads as 0 here and is **not re-verified**: the provider cannot reproduce the number, and the lane's progress file carries no per-finding `finding:` lines, only aggregates (`38 review-body findings disposed (35 by commit, 3 declined)` after four rounds, then `review-gate all_handled 48/48, 0 threads` at `36148a439`). The landing's `48/48` is therefore a CARRIED statement, consistent with the progress aggregates, not a difference and not a false claim. The landing names five reviews (the fifth, 19:54) and 21 inline threads; the progress file lists four review times (CARRIED). Three findings were declined with reasons on their threads (cap-before-materialising, caller-asserted provenance, ancestor descriptor-chain walk); the leaf judged two of them to leave a residual (layer 3 items above).
- CI/merge: OBSERVED through the CI abstraction: state `merged`, merge commit `78951e23c`, all required checks green (`verify / conclusion`, `verify / verify`, `verify / gate`, `generate-check`, `dependency-review`); `CodeRabbit`, `auto-merge`, `Sourcery review` are `SKIPPED` on the final state, and the lane reports Sourcery refused the diff as over 150,000 characters (CARRIED). Merged through the merge queue (CARRIED, progress file). The merge-gate refusal read in this session's re-run (`body_findings_undisposed`) is a property of the re-run without the lane's dispositions, not of the merge.
- Sonar: `n/a` in the landing; not enabled for this repository; nothing to compare.
- Collisions: none observed.
- Cleanup: `cleanup_owed=false`; the lane's progress file records the worktree and refs pruned (CARRIED).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-172 --status shipped` (`running` → `shipped`)
- [x] row `pr` stamped — `2036`, set at the partial landing and re-read from the row file
- [x] row `landing` stamped — `landings/PLAN-LB-172.md`, same
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-172-consolidated-leftover-fixes`, same
- [x] epic.md narrative reconciled (a Decisions entry; the stranded-PR Watch replaced by Open Defects for the three layer-3 majors, the merge-record misstatement and the minors; the STAGED markers of the source entries that named PLAN-LB-172 stand as shipped)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated
- [x] message archived (`inbox archive`), decision logged
- [ ] PLAN-LB-173 — NOT transitioned: it is obsolete by its own spec but is the operator's call to supersede, and a fix plan for the findings below is staged only on the operator's word

## Follow-Ups

- PLAN-LB-173 (staged, NOT emitted): every one of its six deliverables is done — deliverable 1 (carry PR #2036 to merge) and deliverables 2 to 6 (the old 172 D6 to D10) shipped in the merged PR. Emitting it would re-run shipped work. Supersede it on the operator's word, or re-scope it into the fix plan below.
- Layer 3 (reported to the operator; staged only on the operator's word, then one plan): the three majors above, with the minors grouped by file as above.
- Owed to the operator: `/apply-changes` (the plan edits bundle sources, the `apply-changes` entry points among them), and the correction of the PR #2036 body if the operator wants the record fixed (outward-facing, not done here).
- Still unverified and not acted on: PR #2036's body names `tools-integration-ci/SKILL.md` as the single home of the shared-slot rule; the file is not in the merged change. The leaf did not look; the lead stays open.
- The delegating-consumer case of PLAN-LB-171's dropped deliverable stays unstaged; layer 3 minor `runbook_lane.py:1349` is adjacent to it.
