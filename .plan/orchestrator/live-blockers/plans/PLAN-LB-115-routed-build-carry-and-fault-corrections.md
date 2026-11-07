# PLAN-LB-115: The routed-build carry cannot refuse a build outside the move-back window, and the routed fault reports what the child said

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-115-routed-build-carry-and-fault-corrections.md` and is queued as one row file, `queue/PLAN-LB-115.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word after the PLAN-LB-112 landing was read on three layers (`landings/PLAN-LB-112.md`, merge `7d4182f46`).
> It is the follow-up for that landing's layer-3 findings L3-1 to L3-7 and the weak tests and comments of layer 2 (L2-4, L2-5). The
> layer-3 findings of PLAN-LB-111 and PLAN-LB-113 are already carried by PLAN-LB-114 and are not repeated here. The leaf's report was
> re-read at `file:line` for the points labelled OBSERVED below; the rest are HYPOTHESIS with a verify-first clause.

## Objective

PLAN-LB-112 made a daemon-routed build keep its tree in the finalize move-back window by appending `--resolved-project-dir` to the
routed argv, and made a child's pre-tool refusal reach the caller under its own name. Reading the merged code found that the carry is
appended to every routed build with a real `--plan-id`, not only to builds in the window, so a project whose executor was generated
before that change has every routed plan build refused until the executor is regenerated, with no in-process fallback. It also found
that the routed fault drops fields the child emitted, that one refusal loses its diagnostic fields in the formatter, and that three
fault paths still collapse into a red build or into a different name.

After this plan, a routed plan build outside the window runs whatever the executor's age; the window case still reports its own fault;
a routed fault carries the fields the child emitted under the names it emitted them; and the tests and comments say what holds.

## Deliverables

1. **A stale executor cannot turn a routed plan build outside the move-back window into a refusal.**
   - The routing process appends the carry for every routed argv that names a real plan (`_carry_resolved_tree`). A child whose
     executor predates the carry flag refuses it as `unknown_flag`, reported as `invalid_invocation`. The routed result is returned
     as-is; there is no in-process fallback after a routed result.
   - The outline chooses how the carry is limited. Candidates: carry only when the routing process can tell the child needs it (the
     plan record is absent from the tree the child will start in); or, when the child answers `invalid_invocation` with `unknown_flag`
     naming the carry flag, re-run once without the carry; or both. Constraints: the plan id still reaches the ledger row and slot
     accounting, the window case still works on a current executor, `--plan-id` and `--project-dir` stay mutually exclusive, and a
     tree that cannot be resolved stays an error, never a default to the main checkout.
   - The seam recognises the plan flag in every spelling the child's parser accepts: the exact spelling and the `=` form. The `run`
     subparser sets `allow_abbrev=False` (`_build_cli.py:205-207`), and the routing process parses its own argv with the same parser,
     so an abbreviation never reaches `_flag_value`; this bullet is closed and needs no change (re-grounded at `f84eb0e36`).
   - If the carry's documented behaviour changes, the INTERNAL bullet that documents the flag changes with it.

   *Done when:* a fixture whose executor surface lacks the carry flag shows a routed plan build outside the window running and
   returning the build's own result; the same executor inside the window returns the refusal as itself, not as a red build; a current
   executor behaves as PLAN-LB-112 shipped it. The first case is red at HEAD.

2. **A routed fault reports what the child said, and the remaining collapses are closed.**
   - **Field names.** The routed result carries the child's `message` as `message` and its `reason` as `reason`. Today a body with only
     `message` is carried as `reason` and `message` is dropped, so a consumer that reads `message` on the direct path gets nothing on
     the routed one. Direct and routed agree on the field names for the same fault.
   - **Refusal fields.** The carried-tree refusal's documented diagnostic fields (`resolved_project_dir`, `plan_id`) reach the output.
     Either the formatter whitelist carries them on both the TOON and the JSON path, or the refusal is emitted through a path that
     does not drop them.
   - **Per-block reading.** The verdict reader takes each key from the block that holds the verdict, not the last occurrence anywhere
     in the log, so an earlier column-zero line cannot supply the fault's `reason`.
   - **Exit -1.** Closed by re-grounding: a failure payload from the daemon carries a positive return code, narrowing happens only on
     exit 0, and -1 appears only on the killed and unrecognised arms (`_marshalld_supervisor.py:182-184,266,281,477-483`); the
     pre-tool emitters exit 2 (`_build_cli.py:753,765,769`). A genuine launch fault (-1, no pre-tool body) stays a launch fault. Only a
     real log shape that shows -1 beside a pre-tool body reopens it; none is known.
   - **Unreachable build queue.** A failed build-queue acquire raises a bare `RuntimeError` at two places: the slot acquire of a real
     plan id, and, since the per-directory lock, the directory-lock acquire that EVERY in-process build takes, plan-less builds
     included, in the daemon child and directly (`_build_queue_slot.py:368,408` and `:583`, fed by `:509-510`). `cmd_run` catches
     `DirectoryBusy` and `BuildQueueTimeout` and nothing else (`_build_execute_factory.py:1812-1815`). Both failures reach the caller
     as a structured, named fault, not as a crash, and not as `build_failed` plus the synthetic row.
   - **Exit-code contract.** The result emitter's `Returns` statement names the codes it returns, including the child's own code for a
     pre-tool fault.

   *Done when:* one fixture per bullet is green, and each is red at HEAD except the matched controls: a build that ran and failed
   keeps `build_failed` and its rows, and a genuine launch fault keeps its launch-fault name.

3. **The tests say what they test, and the comments state the current behaviour.**
   - The slot-refusal test builds its log from the producer's real output shape (`message`, `tool`, `command`, `max_retries`,
     `plan_id`, no `reason`), not a hand-written shape, and asserts the field names D2 settles.
   - The "one spelling" test is replaced by one that can fail: it parses the routed argv with the child's parser, so a one-sided
     rename fails it. Its docstring no longer says the flag is declared in two modules.
   - The moved-back routed test either uses the fixture it requests or drops the parameter, and one test drives the child's own entry
     point with the carried tree in the window, so the Done-when of PLAN-LB-112 D2 ("the result is the build's own") is borne by a
     single test rather than read from several.
   - Two comments state transitional wording against the documentation standard: the `ERROR_INVALID_INVOCATION` docstring ("This
     branch adds a flag … generated before this change") and the `_PLAN_ID_FLAG` docstring ("the pre-carry behaviour"). Both state
     the current behaviour and nothing about a change. The per-directory build merge added more of the same class, which this
     bullet also takes: `_build_execute_factory.py:1048-1051` ("the very confusion D2 removes") and `:1780` ("as before"),
     `_build_shared.py:887-890` ("historical `running`"), `_build_queue_slot.py:346-347` ("the prior behaviour").
   - The hand-back's job status can now be `queued`: the `_build_result.py:166` comment ("always 'running' on this shape") and the
     `_running_hand_back` docstring (`_build_execute_factory.py:1028`) say the current behaviour.
   - The log reader's "only the failure path pays for it" statement is true or removed (re-grounded: it is false, the success leg
     calls the reader too, `_marshalld_supervisor.py:477-478` and `_build_execute_factory.py:752-753`).

   *Done when:* each changed test fails when the property it names is broken (shown by a mutation or a red run, recorded in the PR),
   and no comment in the touched modules describes a change rather than the current behaviour.

4. **The routed-result mapping that PLAN-LB-110 widened is decided, and its reach is pinned.** *(L1-4, L3-6 of `landings/PLAN-LB-110.md`;
   delivered with D2, which edits the same mapping)*
   - PLAN-LB-110 (merge `9c8eb94c2`) changed the shared routed result for every tool: on the routed failure leg a child verdict that is
     neither success nor error is re-rendered as itself instead of `error/build_failed` (`_build_execute_factory.py:821-834` at
     `f84eb0e36`), and an indeterminate result carries the child's own `message:` (`:978-998`), with `LogVerdict.message` added in
     `_build_server_protocol.py`. The spec of that plan limited shared changes to one reason value.
   - Re-grounding at `f84eb0e36` settled the reach: a routed timeout or killed child does NOT arrive as `failure`. The wrapper exits 0
     with its own status (`_build_shared.py:852,872,909`), the supervisor maps timeout to timeout and killed to killed
     (`_build_server_protocol.py:200-207`), and those verdicts take the legs at `_build_execute_factory.py:775-797`. The new hunk
     therefore reaches only an indeterminate, a running or a foreign status, so the reach into pyproject, Gradle and npm is far
     narrower than the PLAN-LB-110 report assumed. The gate reaction to `timeout` and `killed` is still unread (settle it at outline).
   - Two texts say the opposite and are false: the docstring at `_build_execute_factory.py:696-700` (the wire "cannot carry"
     timeout or killed) and the test `test_a_non_finish_verdict_arriving_as_failure_is_rendered_as_itself`
     (`test_build_execute_routing.py` about `:1513-1535`), which scripts a wire shape the supervisor does not produce.
   - D2's field-name rule and this hunk are one mapping: the outline states one rule for what a routed child verdict becomes, once in
     the result emitter's `Returns` statement, and keeps the Maven selector reason carried across the routed hop.
   - The five tests of `TestIndeterminateReasonCarry` (`test_build_execute_routing.py:1460-1559`) stay green or are rewritten to the
     settled rule with a docstring that says why.

   *Done when:* the docstring and the test named above state or script what the supervisor and the wrapper produce (a timeout and a
   killed child each reach the caller as themselves, pinned by a fixture, `order: none` where HEAD already does it); the Maven
   selector-miss reason still reaches the caller across the routed hop on both wire legs; a routed child that failed after running
   keeps `build_failed` and its rows (control).

Split guard: four deliverables, one fault path. D1 is the only behaviour fork and can be run alone; D2 and D4 edit the same result
mapping and are delivered together; D3 is the test and comment pass over all.

## Standing Constraints

- **Settle each HYPOTHESIS first.** The verify-first clauses below come before any change; a refuted claim is dropped from the
  deliverable, not worked around.
- **A routing fault is never a red build.** Anything that stops the tool from running is reported as itself. `build_failed` means the
  tool ran and failed.
- **Leave routing alone.** Do not change the semantics of `--execution-mode`, `build-routing` or the `--project-dir` absolutisation.
- **The strict `get-worktree-path` gate is kept.** Do not add a fallback to that verb.
- **Fail closed.** A tree that cannot be resolved is an error, not a default to the main checkout.
- **The carry stays marker-gated.** `carried_tree_outside_daemon_job` is not weakened.
- **Documentation states the current behaviour.** No comment or doc describes a change, a branch or a prior state.
- **Tests state their purpose.** Every new or changed test states what it protects, uses the `PLAN_MARSHALL_HOME` fixture, never reads
  the real `~/.plan-marshall` or this repository's live `.plan/marshal.json`, and is shown red at HEAD where its Done-when says so.
- **The daemon side takes effect only after a reconcile.** A live record from a worktree before the merge is NOT a Done-when. The PR's
  evidence is the fixture suite, and the landing lists any post-merge live check as owed.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: the carry is appended to every routed argv that names a real plan — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` L1036-1039, at `7d4182f46`.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: carry call at _build_execute_factory.py L1107-1133 (call site L1268), moved +94
- OBSERVED: a routed result is returned to the caller with no in-process fallback — read at `_build_execute_factory.py` L1588-1619.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: no in-process fallback after a routed result, _build_execute_factory.py L1712-1744
- OBSERVED: a pre-change executor's refusal of the carry is documented as `unknown_flag` reported as `invalid_invocation` — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` L290-299 (the same text carries the
  transitional wording D3 removes).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: ERROR_INVALID_INVOCATION docs at _build_result.py L283-301, transitional text L291-300
- OBSERVED: the direct `worktree_resolution_failed` body carries its text in `message` only — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/resolve_project_dir.py` L294-301.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: resolve_project_dir.py L294-301 unchanged
- OBSERVED: the routed fault takes `reason = fault_reason or fault_message` and a corrective only when the message differs, and the
  routed result emits `message` only from the corrective — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py` L1300-1304 and
  `_build_execute_factory.py` L824-830.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_server_protocol.py L1319-1323 (JSON path L1434-1438); _build_execute_factory.py L878-884
- OBSERVED: `_build_server_protocol.py` reads `error:`, `reason:`, `message:`, `wrapper:` and `project_dir:` as last-wins scalars across
  the whole log — read at L1275-1284.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: last-wins scalars at _build_server_protocol.py L1294-1303
- OBSERVED: the carried-tree refusal is printed through `format_toon` (`_build_cli.py` L752), its payload carries
  `resolved_project_dir` and `plan_id` (`resolve_project_dir.py` L331-332), and the formatter's extra-field list has neither
  (`_build_format.py` L41-58).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_cli.py L752; resolve_project_dir.py L331-332; _build_format.py L41-65 (LB-108 added seven fields, not these two)
- OBSERVED: the launch-fault branch (`exit_code == -1`) precedes the pre-tool branch, and the routed mapping passes `exit_code or 2`,
  which keeps -1 — read at `_build_shared.py` L758 and L795, and `_build_execute_factory.py` L833.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_shared.py L773, L810; _build_execute_factory.py L887
- OBSERVED: a failed build-queue acquire raises `RuntimeError` (`_build_queue_slot.py` L339) and `cmd_run` catches only
  `BuildQueueTimeout` (`_build_execute_factory.py` L1668).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_queue_slot.py L368, L408; cmd_run catches DirectoryBusy and BuildQueueTimeout only, _build_execute_factory.py L1812-1815; gap widened by LB-108 (directory lock, L583)
- OBSERVED: the producer of `queue_saturated` writes `message`, `tool`, `command`, `max_retries` and `plan_id` and no `reason`
  (`_build_execute_factory.py` L1247-1255); the test writes `reason: max_retries` (`test_build_execute_routing.py` L1203).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: producer _build_execute_factory.py L1345-1353; test writes reason max_retries at test_build_execute_routing.py L1418
- OBSERVED: `_RESOLVED_PROJECT_DIR_FLAG` is imported from `_build_cli` (`_build_execute_factory.py` L49), so the one-spelling test
  (`test_build_execute_factory.py` L1554-1563) compares a constant with itself.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py L49; test_build_execute_factory.py L1554-1563 unchanged
- OBSERVED: the moved-back routed test requests `moved_back_window` and never uses it (`test_build_execute_routing.py` L939-966).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_build_execute_routing.py L1154-1181 (moved +215 by LB-108)
- OBSERVED: the `_PLAN_ID_FLAG` docstring says "the pre-carry behaviour" (`_build_execute_factory.py` L986-987).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py L1080-1081
- OBSERVED: `_flag_value` matches the exact `--plan-id` token and the `--plan-id=` form only (`_build_execute_factory.py` L1042-1064).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _flag_value at _build_execute_factory.py L1136-1158
- HYPOTHESIS: a stale executor still matches its recorded script digest and applies its old surface, so the refusal happens in
  practice and not only in the documentation — confirm/refute at the executor's surface validation and digest check (verify-at-outline).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: surface applies only when script path and sha match (execute-script.py.template L1353-1382); flag lives in _build_cli.py so the wrapper sha is unchanged; D1 reproduction still owed
- HYPOTHESIS: the child's argparse accepts an abbreviation of `--plan-id` — confirm/refute at the build CLI's parser and the
  executor's surface check (verify-at-outline).
  - verdict: contradicted | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: yes | evidence: run subparser sets allow_abbrev=False (_build_cli.py L205-207, L629-633); spec D1 bullet closed in this edit
- HYPOTHESIS: a real job log can hold an earlier column-zero `reason:` line before a pre-tool body that has only `message:` —
  confirm/refute against the log shapes the daemon child writes (verify-at-outline). If it cannot, the per-block bullet is dropped.
  - verdict: unverifiable | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: reader is last-wins (proto L1294-1303); whether a real log holds an earlier column-zero reason line is a runtime fact
- HYPOTHESIS: the daemon can report a job failure with exit code -1 beside a pre-tool body — confirm/refute at `marshalld.py`
  § the job outcome (verify-at-outline). If it cannot, the exit -1 bullet is dropped.
  - verdict: contradicted | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: yes | evidence: failure payload carries a positive return code, -1 only on killed and unrecognised arms (_marshalld_supervisor.py L182-184, L266, L281, L477-483); pre-tool emitters exit 2; spec D2 exit -1 bullet closed in this edit
- HYPOTHESIS: an uncaught `RuntimeError` from the queue acquire in a daemon child reaches the caller as `build_failed` plus the
  synthetic row — confirm/refute at the wrapper's top-level exception handler (`safe_main`) (verify-at-outline).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: client side: a verdict naming neither fault set maps to build_failed, _build_execute_factory.py L835-842; safe_main not read
- HYPOTHESIS: the "only the failure path pays for it" statement in the log reader is inaccurate because the success-leg cross-check
  also calls it — confirm/refute at `_build_server_protocol.py` § `read_log_verdict` and `_build_execute_factory.py` § the success
  cross-check (verify-at-outline).
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: statement at proto L1386-1388 is false: success leg also calls the reader, supervisor L477-478 and factory L752-753
- HYPOTHESIS: the child, run from the worktree with the plan directory absent, performs plan-id-keyed work there (queue slot and
  liveness, the work log, the build-results path) that can recreate `.plan/local/plans/{id}` in the worktree or fail — confirm/refute
  at `_build_execute_factory.py` § `cmd_run` and `_build_queue_slot.py` (verify-at-outline). If it does, it is part of D1.
  - verdict: unverifiable | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_result.py L404-411 mkdir(parents=True) and _build_queue_slot.py L306-307 read; get_build_results_dir resolution from a worktree cwd not read
- OBSERVED: the routed failure leg re-renders a verdict whose status is not success or error through `_result_for_log_verdict`, and an
  indeterminate result uses the log's `message` with whitespace collapsed — `_build_execute_factory.py` L786-799 and L943-963, read at
  `9c8eb94c2`.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: LB-110 hunks at _build_execute_factory.py L821-834 and L978-998 (moved +35)
- HYPOTHESIS: a routed pyproject, Gradle or npm child that reports timeout or killed arrives on the wire as `failure`, and the gates
  that previously saw `build_failed` now see `timeout` or `killed` — confirm/refute at `_build_server_protocol.py` § the log verdict
  reader, `marshalld.py` § the job outcome, and the gate steps in `pre-push-quality-gate.md` (verify-at-outline). It decides D4.
  - verdict: contradicted | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: yes | evidence: wrapper exits 0 with its own status (_build_shared.py L852, L872, L909); supervisor maps timeout and killed to themselves (proto L200-207); only indeterminate, running and foreign reach the LB-110 hunk; spec D4 rewritten in this edit
- Verify-first clause (D4): read PLAN-LB-110's hunks in `_build_execute_factory.py` and `test_build_execute_routing.py` as they stand on
  `main` and re-read this spec's line references against them; every L-number above moved.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: hunks and TestIndeterminateReasonCarry (L1460-1559) found; every cited line moved
- Verify-first clause (D1): reproduce the stale-executor refusal at HEAD before changing anything, by a fixture whose executor surface
  lacks the carry flag. If the refusal does not occur, D1 is closed and only the documentation of the residual remains.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: carry code L1075-1158 untouched by LB-108, LB-110 and LB-119; clause applies as written
- Verify-first clause (D2): settle each HYPOTHESIS bullet above before its fix is scoped. LB-108's in-process lock work may already
  change the queue-acquire path; re-read it at outline before D2's unreachable-queue bullet is scoped.
  - verdict: corroborated | checked_at: f84eb0e36bc5787ffca65c8d392d46ffb83a9126 | by: live-blockers/cleanup | rescoped: n/a | evidence: LB-108 merged and did not close the queue-acquire gap (_build_queue_slot.py L368, L408, L583; factory L1812-1815); re-read still required at outline

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — the carry seam, the routed result mapping, the queue catch, two docstrings (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py` — the verdict reader and `ChildFault` (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — the pre-tool branch, the launch-fault ordering, the exit-code statement (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` — the fault sets and the transitional docstring (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py` — the carry flag declaration and the carried-tree refusal output (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_format.py` — the extra-field list (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/resolve_project_dir.py` — only if the refusal's emitter changes (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_queue_slot.py` — the directory-lock and slot acquire failures raise a bare `RuntimeError` (D2); one comment (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md` — only if the carry's documented behaviour changes (D1; verify-at-outline)
- OBSERVED: `test/plan-marshall/build-server/test_build_execute_routing.py` — routed fixtures (D1, D2, D3)
- OBSERVED: `test/plan-marshall/script-shared/test_build_cli.py` — carry consumption and the refusal output (D1, D2, D3)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py` — factory guards (D1, D3)

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-112 (PR 1910) is shipped and present in HEAD; this plan builds on its carry and its pre-tool fault set.
- **PLAN-LB-108 is merged** (`9bd6a39d2`, PR 1922) and its sequencing is satisfied. Its `queued` wait status and per-directory lock
  moved `_build_execute_factory.py` and `test_build_execute_routing.py`, and widened the unreachable-queue gap D2 closes. The line
  references above are as read at `f84eb0e36`; re-read them at the outline.
- **Overlaps with the running PLAN-LB-121** on no file (re-checked by the corpus read at `f84eb0e36`).
- **Overlaps with PLAN-LB-87 (parked)** on `_build_execute_factory.py`; if it is un-parked, run it in sequence.
- **Adjacent to** (left untouched): `_status_query.py` (the strict gate), `marshalld.py` and the daemon scheduler (LB-108's), the lane's
  build routing text, and the gate-row writer `_append_gate_build_row`, which records a routed pre-tool fault as `status=error`
  with no error class (an info-level finding of the landing; fails closed, not carried).
- **Owed outside this plan, operator-run:** regenerate the executor in every project before a routed plan build can use the carry
  (D1 narrows the exposure; it does not replace the regeneration), and a live routed check in the window.
- **Running plans:** checked at emit by the disjointness gate; none were checked in this draft.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-115-routed-build-carry-and-fault-corrections.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
