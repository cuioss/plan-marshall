# Landing Analysis: PLAN-LB-140 — generated Antigravity documents name the native sub-agent mechanism, and the dispatch seam carries the resolved level

epic: live-blockers
workstream: WS-04
pr: #1968 (merge commit `4ee75be3ecbbd153900951f88d15abfb22bb6ae2`, one parent `242617bcf166b4c67429e078dda6330403f5781f`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-140-antigravity-native-dispatch`, `merge_state=merged`, `deliverables 2/2`). It is `complete: false` on `total_tokens` alone (out of scope, as for every runbook landing in this epic). The row was `staged` when the message arrived: the operator was handed the command and the lane ran and merged before any `running` transition was recorded, so the row goes `staged` to `shipped` in this reconciliation.

The squash commit has one parent and touches 20 paths (read with `git diff --name-only 242617bcf 4ee75be3e`): 9 bundle files, 5 files under `marketplace/targets/`, `doc/developer/antigravity.adoc` and 5 test files.

The facts block agrees with ground truth: `unresolved_review_threads=0` and `review_body_findings_total=7` equal the provider's numbers from `runbook_lane review-gate --pr-number 1968` (7 ids: `nitpick-1`, `additional-1`, `inline-1` to `inline-5`). `review_body_findings_handled=7` was re-read from the run's progress file: seven coderabbit `finding:` lines (`nitpick-1`, `additional-1`, `inline-1` to `inline-4`, and the two coderabbit thread lines), each with a commit or a reason. The bare `review-gate` re-run reports `handled: 0` and `merge_allowed: false` because it holds no dispositions input, which is not a difference. `sonar_open_new_issues=n/a`. No false claim found.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the emitter transforms every Markdown file of a skill, and a dispatch line becomes the native instruction | shipped-as-specified, one sub-clause vacuous at base | `mapping.json:48-52` maps `Task:` to `rewrite_dispatch_block`; `body_transform_engine.py:507-555` applier, `make_sub_file_transformer` the dispatch-only sub-file pass; `emitter.py:212-233` sends `.md` sub-files through it; generated-tree test `test_generated_plan_marshall_workflow_carries_no_bare_dispatch_line` (leaf read, not re-read). The sub-file scope choice (dispatch applier only) is the one the spec asked to be decided and pinned, and is pinned both ways |
| D2 — the dispatch seam is called by the orchestrator with the resolved level and the spawning-tool signal, and the inline branch writes one boundary row | shipped-modified | `execution.md:178-189` (re-read): seam call with `--agent {target}` and `spawning_tool_available`, success dispatches, no-op takes the inline branch, one `record-dispatch-boundary` row per envelope. The spec's "reached with an explicit `dispatch_mode: inline`" is not what the documented call does: it passes no `dispatch_mode` and reaches the inline arm through `spawning_tool_available: false`; the pin is carried by both runtimes and is an output marker on the no-op (see L1-3) |

Spec sub-points: the HYPOTHESIS that `record-dispatch-boundary` records a row for the inline branch is confirmed (leaf read of `manage-metrics.py:3777-3846`, not re-read). The HYPOTHESIS that the sub-file transform restricted to the dispatch applier suffices is confirmed. The HYPOTHESIS that `test_body_transform_engine.py` pins `preserve` is refuted: the file is not in the diff. The seam is called by no leaf document any more: a read-only search of the plan-marshall bundle for `subagent dispatch` in the five documents that matter (`execute-task/SKILL.md`, `phase-5-execute/SKILL.md`, `phase-5-execute/standards/operations.md`, `phase-5-execute/standards/workflow.md`, `agents/execution-context.md`) finds the words only as prose about generic dispatch, never as the seam command (the search ran as a read-only `grep` through Bash because the Grep tool is unavailable this session).

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for; a second full-ship landing (PLAN-LB-144) was drained in the same firing and got its own leaf.
- **Verdict:** layer 1 findings (4: 2 minor, 2 info); layer 2 findings (5: 4 minor, 1 info); layer 3 findings (8: 5 minor, 3 info). The layer-3 defects are reported to the operator in the same turn; none is major.

Re-read: `opencode_runtime.py:2930-2999`; `execution.md:150-250`; `body_transform_engine.py:500-555`; `phase-5-execute/standards/operations.md:68-97`; `phase-5-execute/SKILL.md:584-595`; `antigravity.adoc:154-163`; the bundle listing at `4ee75be3e`; the progress file's `finding:` lines; the provider through `review-gate`; the changed path list through git. **Not re-read** (unverified leads, recorded as such): the generated-tree and emitter tests, `emitter.py` and `target.py` (the leaf's reading of the sub-file loop), `mapping.json`, `antigravity_runtime.py`, `runtime_base.py`, `contract.md:1341-1353`, `manage-metrics.py:3777-3846`, `phase-6-finalize/SKILL.md:701`, the test-side findings (the surviving mutation on the `spawning_tool_available: false` arm; the test whose name says "writes one boundary row" but reads an integer in the payload), the mixed tab and space indentation reading (`body_transform_engine.py:465,498`), the claim that the surface of the engine's transforms 1 to 3 in `antigravity.adoc` is incomplete beyond the sentence quoted there, and every conformance row. The leaf also could not search content, so its two premise checks (a caller outside the three documents; `spawning_tool_available` appearing only in the runtimes, the contract and two tests) are `not_shown_by_reading` from the leaf; the orchestrator's own search above settles the leaf-document half only.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | Premise D1 holds at the parent: the body transformer runs on `SKILL.md` only and every other skill file is copied byte for byte | checked (leaf; not re-read) | confirms | `emitter.py` at `242617bcf`, `~L230`, `~L247-250` |
| L1-2 | The second D1 Done-when (the generated `phase-5-execute` and `execute-task` documents carry no bare `Task:` line) cannot fail for `execute-task`: the skill holds `SKILL.md` and two scripts and no line of it starts with `Task:`; the `phase-5-execute` half fails at base because `standards/operations.md` carries three bare `Task:` blocks (re-read at `:74,87,~124`) | checked | confirms | `execute-task/SKILL.md` at `242617bcf` (leaf, lines 31-39 not read); `phase-5-execute/standards/operations.md:74,87` (re-read) |
| L1-3 | D2 asks for both `spawning_tool_available` and an explicit `dispatch_mode: inline` to reach the inline branch; the documented call carries only the signal, and `dispatch_mode` is an input pin no documented caller uses and also an output marker on the no-op, so the spec's two routes to the inline branch are redundant | checked | refutes | `execution.md:183,187` (re-read) |
| L1-4 | The spec cites the OpenCode inline branch at `L2596-2606`; at the parent it sits at about `L2935-2944`, so the line cite was stale at the parent (the spec was written at `9cd644892`, which the leaf did not read) | checked (against the parent only) | refutes | `opencode_runtime.py` at `242617bcf`, diff hunk `-2935` |

No finding names a corpus claim of a staged spec of this epic, so no re-grounding verdict is persisted (the spec itself is the shipped one).

**Layer 1 verdict:** findings — 4 (2 minor, 2 info)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `mapping.json:48-52`; `body_transform_engine.py:176-199,262,288-316,507-555,621-655`; `emitter.py:212-233,275`; `target.py:59` | `test_generated_plan_marshall_workflow_carries_no_bare_dispatch_line`, `test_a_markdown_sub_file_is_written_through_the_dispatch_applier_only`, `test_without_a_sub_file_transformer_a_markdown_sub_file_is_byte_identical`, `test_a_crlf_sub_file_keeps_its_line_endings_across_the_rewrite`, and the applier tests in `test_body_transforms.py` (leaf read; the lane's `mutation-after` log paths not opened) | the `execute-task` half of the Done-when is vacuous at base (the lane flags it itself) | checked (leaf; not re-read) |
| D2 | `execution.md:178-189` (re-read); `opencode_runtime.py:2940-2988` (re-read); `antigravity_runtime.py:991-1018`; `runtime_base.py:284-285` | `test_the_dispatch_branch_calls_the_seam_with_the_resolved_target_and_the_spawning_signal`, `test_a_leaf_document_does_not_resolve_the_subagent_seam[…]` (router), `test_subagent_dispatch_explicit_inline_dispatch_mode_writes_one_boundary_row`, `test_subagent_dispatch_rejects_an_unknown_dispatch_mode` (leaf read) | see L2-1 to L2-5 | checked (partly re-read) |

- **L2-1 (minor):** the narrative's claim C5, "the OpenCode runtime change only consumes one more context key and validates the boolean", is not what the diff does. `opencode_runtime.py:2950-2964` adds a `dispatch_mode` pin branch and an `invalid_argument` rejection, and `:2971` and `:2987` add the `dispatch_mode` and `dispatch_boundary_rows` extras on two further no-op arms (re-read). The rest of the claim holds: both runtimes agree and the keys are consumed, not merged into the prompt (leaf read, not re-read).
- **L2-2 (minor):** 14 of the 20 paths are on the declared surface (two of them, `opencode_runtime.py` and `runtime_base.py`, as hypotheses). Six are outside it: `marketplace/targets/antigravity/target.py` (wiring), `marketplace/targets/component_targets.py` (docstring), `doc/developer/antigravity.adoc`, `platform-runtime/standards/contract.md` (`:1341,1350-1353`), `phase-6-finalize/SKILL.md` (`:701`, prose wording that no Done-when requires) and `test_opencode_runtime.py`. The other five are explained by D1 or D2 (the leaf's reading); the lane's section for files outside the surface lists none by name, and `contract.md` is in no list of its narrative. The change of `phase-6-finalize/SKILL.md` is the one no deliverable explains (leaf; not re-read).
- **L2-3 (minor, not re-read):** the D2 test whose name says it "writes one boundary row" reads only the payload's `dispatch_boundary_rows == 1`; no test drives `record-dispatch-boundary` for an inline envelope.
- **L2-4 (minor, not re-read):** the `extra` marker on the `spawning_tool_available: False` arm, the arm the documented orchestrator call reaches, is asserted by no added test; removing it would keep the new tests green (`antigravity_runtime.py:1018`, `opencode_runtime.py:2971`).
- **L2-5 (info):** the lane's claim C9 (a row is recorded for any cause in the set, dispatched or not) holds (`manage-metrics.py:3777-3846`, leaf read); the row has no dispatch-mode column, so an inline row and a dispatched row cannot be told apart in the ledger.

**Layer 2 verdict:** findings — 5 (4 minor, 1 info)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `opencode_runtime.py:2940,2965` (re-read) | `--context '{"task_tool_available": "false"}'`, or `0` | The legacy flag is read with `context.get('task_tool_available', True)` and tested only with `is False`; a string `"false"` or `0` is not `False`, so the dispatch proceeds to `success`. The new `spawning_tool_available` check beside it rejects a non-boolean as `invalid_argument` (`:2944-2949`), so the two flags now disagree on malformed input and the older one fails open. Whether the older flag's line predates the plan was not checked | minor |
| L3-2 | `execution.md:186-189,241` (re-read) | an inline envelope returning no `<usage>` | The boundary row's `--total-tokens`, `--tool-uses` and `--duration-ms` take `0` "when the field is absent" (`:241`), while the seam's own text says usage propagates as unknown (`opencode_runtime.py:2962,2970`). A measured-looking zero is recorded for an inline envelope, and the B7 no-progress predicate (`consumed_tokens > 50000`, `:247`) can then never hold for it, so an inline stall is never reclassified as `error`. The lane reports the related coverage-denominator effect itself | minor |
| L3-3 | `body_transform_engine.py:529-553` (re-read) | a standards sub-file that quotes Claude syntax as an example: a fenced `Task: x` followed by an indented `prompt:` block | The applier has no notion of a code fence, so a quoted dispatch example is rewritten as if it were a dispatch. That contradicts the stated reason (`make_sub_file_transformer`'s docstring) that quoted examples must ship verbatim for `Skill:` and `Read:`. The real dispatch templates in `execution.md:156-169` are themselves inside a fence, so fence-awareness cannot simply be added: the distinction would have to come from the block's shape | minor |
| L3-4 | `phase-5-execute/standards/operations.md:74-94` (re-read; the bundle listing at `4ee75be3e` shows no `pm-dev-builder` bundle) | the generated Antigravity `operations.md` | The three build-delegation templates (`subagent_type: pm-dev-builder:maven-builder` and `npm-builder`, and a third at about `:124`) are now rewritten into imperative `invoke_subagent` instructions naming `maven-builder` and `npm-builder`. No `pm-dev-builder` bundle exists, and the reader of that document is a leaf. The generated document tells a leaf to dispatch an agent that does not exist. The lane lists these templates as residue (a leaf is told not to issue them on every harness); the new effect is that the Antigravity text is now an imperative instruction | minor |
| L3-5 | `phase-5-execute/SKILL.md:588,591` (re-read) | the generated or source `phase-5-execute` | `:588` still says to delegate "via `Task:`", which contradicts `:591` ("resolved by the orchestrator, not here") and the rule that a leaf never dispatches; `:591`'s own label still reads "Per-task". Prose drift next to the new paragraph | minor |
| L3-6 | `body_transform_engine.py:529,551-552` (re-read) | a dispatch header line ending in `\x85`, ` ` or a lone `\r` | `splitlines(keepends=True)` splits on those characters and the newline is computed only from `'\n'`, so the emitted instruction loses its terminator and runs into the next line. No governed document is known to carry such a character | info |
| L3-7 | `antigravity.adoc:159` (re-read) | the developer document | It says transforms 1 and 2 run on `SKILL.md` (and agent and command bodies) only; the third transform and the inline-code idiom rewrite are not named, so the statement is incomplete (whether they skip sub-files was not re-read at `body_transform_engine.py:637-655`) | info |
| L3-8 | `runtime_base.py:284-285` (leaf; not re-read) | `toon_noop(..., extra={'status': ...})` | `data.update(extra)` can overwrite `status`, `operation` or `reason` without a check; the two current callers pass only the two new keys | info |

**Layer 3 not shown by reading:** whether any `phase-5-execute` step itself calls `record-dispatch-boundary` and so writes a second row for an inline envelope (the leaf read `SKILL.md:575-599` and `operations.md` only, and they carry none); that no caller of the seam exists outside the three former documents (the leaf had no search; my own search covered the leaf documents only); the Claude runtime body; the `runtime` fixture of the runtime tests; `_boundary_coverage_state`; `dispatch-logging.md`; the `PLAN_MARSHALL_HOME` fixture use of the runtime tests. What only a run could show: that the generated tree of all three documents carries no bare line after a full `generate-antigravity` (the lane's test reads the real bundle, which is the nearest by reading).

**Layer 3 verdict:** findings — 8 (5 minor, 3 info); none major

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md, Documentation Standards and the spec's standing constraint | Current state only; no comment describes a change or the old behaviour | deviates (leaf; not re-read) | `test_platform_runtime_router.py`: the section header "(PLAN-LB-140 D2)" and the comment "Every document that used to resolve the seam from inside a leaf"; `test_emitter_skill_dir.py` `test_skill_file_is_emitted_byte_identical` docstring ("now takes rather than the plain copy path it took before"). Production docstrings conform |
| `plan-marshall:ref-code-quality` | Comments are accurate and attached to the code they describe | deviates (leaf; not re-read) | `test_platform_runtime_router.py` about `:38-40`: the conftest `PYTHONPATH` comment now sits above `from conftest import PROJECT_ROOT`, below the cross-skill imports |
| `pm-dev-python:pytest-testing` and the spec | Tests state their purpose | deviates (leaf; not re-read) | `test_body_transforms.py`: three new tests have no docstring (`test_a_complete_dispatch_template_passes_the_guard`, `test_targeted_dispatch_block_becomes_an_invoke_subagent_instruction`, `test_dispatch_block_rewrite_is_idempotent`) |
| Spec standing constraint | Tests use the `PLAN_MARSHALL_HOME` fixture | not_shown_by_reading | the runtime tests' `runtime` fixture was not read |
| `pm-dev-python:python-core` and `ref-code-quality` | Fail closed on invalid input | deviates | `opencode_runtime.py:2944-2956` rejects a non-boolean `spawning_tool_available` and an unknown `dispatch_mode`, while `:2940,2965` let a non-boolean `task_tool_available` through as available (re-read; L3-1) |
| `persona-plan-marshall-agent` and `ref-workflow-architecture/standards/agents.md` | A leaf never dispatches | deviates | the seam moved to the orchestrator (`execution.md:178`, conforms), but `phase-5-execute/SKILL.md:588` and `operations.md:3,74,87` still give the leaf `Task:` delegation (re-read; L3-4, L3-5) |
| Body-transform fail-closed discipline | An un-dispositioned or incomplete idiom fails the build | conforms (leaf; not re-read) | `body_transform_engine.py:262,288-316`; `_KNOWN_DISPOSITIONS` includes `rewrite_dispatch_block` |
| Spec standing constraint | Generated documents are fixed in the mapping, the engine and the emitter | conforms (leaf; not re-read) | the diff edits no file under `target/` |
| Spec standing constraint | Executor regeneration only if a verb or flag is added | conforms (leaf; not re-read) | `dispatch_mode` is a `--context` key; no argparse verb or flag is in the diff |
| Spec D1 | OpenCode's mapping untouched | conforms | `marketplace/targets/opencode/mapping.json` is not in the 20-path diff (read with git) |

## Metrics and Anomalies

- Tokens: `unknown` (the runbook lane measures none; out of scope per the operator's focus rule).
- Duration: the lane reports `verify` at 917 s local and 1678 s in CI at its longest; eight `verify` and six `module-tests` builds, all through the build server with no fallback (the lane's report, not re-read).
- Anomalies: none beyond the above. The lane reports two guard refusals (an `Edit` in the main checkout, refused with R7; a chained `grep` pipe, refused with R1), 19 read-class shell operations that the rule counts (`grep` 7, `tail` 8, `ls` 2, `wc` 1, `awk` 1), and that its own review rounds ended at the round limit with the last fixes not re-reviewed. The lane states all of that itself; none changed a result.

## Routing and Merge Behavior

- Review: required `coderabbit` (`quota_limited`, `review_complete_after_handling`) reviewed `dcffb2365` and later heads; optional `sourcery` reviewed `dcffb2365`. Seven review-body findings from CodeRabbit, seven dispositions in the progress file (5 fixed by commit, 2 fixed by commit and re-checked, per the lane). The 21 Sourcery threads and 5 CodeRabbit threads are resolved (0 unresolved at the merged head, re-read from the provider). The standing authorization (one handled CodeRabbit review is the review) applied; no re-trigger was needed for the later heads.
- CI/merge: merged through the merge queue as a squash with one parent; CI `verify / verify` SUCCESS on `f2799a1e4` per the lane (not read separately; the merge went through the queue).
- Sonar: `n/a`, the project has no Sonar (operator rule). No anomaly.
- Collision: the plan ran beside PLAN-LB-143 (one shared file, `opencode_runtime.py`, as the gate predicted); no rebase conflict is reported.

## Reconciliation Actions

- [ ] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-140 --status shipped`
- [ ] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-140 --field pr --value 1968`
- [ ] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-140 --field landing --value landings/PLAN-LB-140.md`
- [ ] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-140 --field plan_marshall_plan_id --value rb-lb-140-antigravity-native-dispatch`
- [ ] epic.md narrative reconciled against the queue rows (queue annotation, decision)
- [ ] inbox message `rb-lb-140-antigravity-native-dispatch-001.md` archived
- [ ] resume anchor updated in `resume_anchor.md`
- [ ] `queue-view.md` regenerated

## Follow-Ups

- **Harness sync owed:** the generated Antigravity tree changes (the spec's standing constraint). No executor regeneration follows from this plan (no verb or flag added; the leaf reading).
- **PLAN-LB-136** (staged, shares `antigravity_runtime.py` and its test with this plan, and carries a `Depends on` line naming itself as the order on that file): its prerequisite order is now moot, the file's inline-branch hunks have landed; its outline re-reads `antigravity_runtime.py` at `4ee75be3e` before lifting the helpers out. Its overlap with PLAN-LB-143 (two files) stands.
- **Layer-3 residue (L3-1 to L3-8) is one surface** (the dispatch seam and the sub-file transform): no fix plan is staged without the operator's word, and then it is one plan for the surface, not one per defect. L3-1 (a legacy flag that fails open on malformed input), L3-2 (zero tokens recorded for an inline envelope) and L3-4 (a generated imperative instruction naming a bundle that does not exist) are the three with an effect a user can meet.
