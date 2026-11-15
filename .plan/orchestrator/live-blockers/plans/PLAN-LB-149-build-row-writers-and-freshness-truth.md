# PLAN-LB-149: A build row is credited only for the tree it built, no writer's row is refused for a fact it never claimed, and a lone Gradle task row is a scoped row

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-149-build-row-writers-and-freshness-truth.md` and is queued as one row file, `queue/PLAN-LB-149.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-13 ("go through the open plan / open / issues and cleanup / update the remaining plan(s) after
> that land and emit") as plan D of the per-surface fix plans settled on 2026-11-12, from the PLAN-LB-146 landing (`landings/PLAN-LB-146.md`:
> two majors F1 and F2, F4, L2-1, D-1 to D-3) and the PLAN-LB-144 landing (`landings/PLAN-LB-144.md`: the lone Gradle row, decided by the
> operator on 2026-11-12). One plan for one surface, per the operator's rule of 2026-11-11. Grounded against `main` at `877a05ac7` by a
> read-only leaf, with the orchestrator re-reading the ledger writer, the gate's verdict function and the recorder's plan-id lines. Every
> Done-when below fails at `877a05ac7` unless it says "holds at". The operator's second decision of 2026-11-12 (a deliverable retired with no
> successor) is NOT in this plan: grounding showed its premise fails for a deliverable with a frozen spec clause, and it waits for the
> operator. No Sonar. No token or measurement work.

## Objective

The PLAN-LB-146 change made every build row name the tree it hashed, but three of its edges credit or refuse the wrong thing. A writer that
records nothing about the tree (an executor generated from the previous template, the `manage-change-ledger append --kind build` command)
still gets both keys written as `null`, and the freshness gate reads a present `null` as unreadable and refuses the row for good, so the push
gate halts with a remedy that only writes another refused row. A build run with `--audit-plan-id X` from another directory records X's
worktree hash twice for a tree it never built, and the gate reads it fresh. A one-task Gradle row (`:core:test`) is read as a whole-tree
claim although the two-task shape of the same subproject is a narrow row. This plan fixes those three, bounds the pre-build tree hash, and
makes the documents and their pins say what the code does.

## Deliverables

1. **A writer that recorded nothing about the tree omits the two tree keys; only a writer that tried and failed writes an explicit null.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `build_record` (`_ledger_core.py`) writes `worktree_root` and `worktree_sha_at_dispatch` only when the caller passed a value; an
     explicit `None` still writes `null`, which the gate refuses as unreadable. The CLI `append --kind build` and the routing seam's
     auxiliary row (`_build_execute_factory.py`) pass nothing, so their rows have no key and the gate reads them as it read every row before
     the keys existed. The executor template keeps passing explicit values.
   - Decide at outline, and record in the PR, whether the CLI can instead record the root it hashed (it computes a hash itself); the default is
     to omit. A raw `.` is never recorded as a root.
   - The gate's own comments, the `build_record` docstring, the recorder's docstring and both documents state one rule: an absent key means
     the writer did not record the fact (the legacy shape, matched on the completion hash as before), and a present `null` means the writer
     tried and could not.
   - Rollout consequence, stated in the PR: a row from an executor not yet regenerated is read as the pre-change reading until regeneration;
     the regeneration stays owed but no longer halts the push gate.

   *Done when:* each of these fails at `877a05ac7`: `build_record` called without the two keyword arguments returns a row with neither key; a
   row appended by `manage-change-ledger append --kind build --status success` has neither key and the freshness gate over it reads fresh and
   not `stale` / `worktree_root_unreadable`. These hold at `877a05ac7`: a present `null` dispatch hash never matches, a present `null` root
   never matches, a row without the root key is read as before, a row without a dispatch hash matches on its completion hash, and a recorder
   row for an unresolvable root records an explicit `null` and is refused.

2. **The recorder hashes the tree the wrapped build ran in, never the tree of a plan the build did not touch.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - In the executor's `main()` the root the recorder resolves comes from the plan id the wrapper itself reads (`--plan-id`) and from the
     `--project-dir` the wrapper builds in, not from `--audit-plan-id`, which the executor strips before the wrapper runs. The row's
     `plan_id` may stay the attribution value. A plan-less dispatch with `--project-dir Y` records Y.
   - The docstring that says naming another plan's tree "is what makes the mismatch visible" is removed: the gate compared that plan with itself.
   - Verify-first (see Claim Labels): whether a build the daemon routes (`--resolved-project-dir`) reaches this recorder with the same
     arguments; the fix covers the executor's own `main()`, and the PR states what it found about the routed child.

   *Done when:* each of these fails at `877a05ac7`: the executor's `main()` driven with `pyproject_build run --audit-plan-id X` from the main
   checkout (a real git tree, a plan X with a worktree) writes a row whose `worktree_root` is the main checkout and the gate for X reads it
   stale with a root mismatch; a plan-less `--project-dir Y` dispatch records Y's root. These hold at `877a05ac7`: a dispatch with
   `--plan-id X` records X's worktree root and hash (the existing recorder tests keep their stated purpose); a dispatch from X's own worktree
   records the same hash as before.

3. **The pre-build tree hash is bounded, and a failed git call is no hash.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_run_git` in `worktree_sha.py` passes a timeout following the house pattern (a module constant, `subprocess.SubprocessError` caught), and
     `compute_worktree_sha` answers `None` when the `diff` or the `ls-files` call failed or timed out. Today the return codes are discarded, so
     a failed call hashes as HEAD plus an empty diff, the clean-tree hash, and a naive timeout would turn into a false match.
   - Verify-first: read every caller of `compute_worktree_sha` and state what each does with `None` (the recorder records an explicit null,
     which is refused; any other caller is named and checked).

   *Done when:* each of these fails at `877a05ac7`: with `subprocess.run` stubbed to raise a timeout on the `diff` call, `compute_worktree_sha`
   answers `None`; `_run_git` passes a `timeout` argument. These hold at `877a05ac7`: the existing `test_worktree_sha.py` cases, including the
   missing-git case.

4. **A lone `:module:task` Gradle row is a scoped row of its subproject.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - Decided by the operator on 2026-11-12. `parse_row_scope` (`_freshness_crosscheck.py`) returns the narrow `RowScope` for a lone
     `:`-prefixed non-npm task the way it already does for two tasks: the head token is the canonical and the subproject path derived from the
     task token is its scope. When the derivation is empty (a payload such as `: :`) the row is unreadable (`None`), never whole-tree; that
     closes the second fail-open the PLAN-LB-144 landing (L3-2) names in the same function.
   - The module's own comments at the lone-task branch and its change-history phrases, and `manage-tasks/SKILL.md` where it states the lone
     reading, say the new rule.

   *Done when:* each of these fails at `877a05ac7`: `parse_row_scope` of a lone `:core:test` row returns scope `('core',)`; the gate over a
   ledger whose only same-sha row is `:core:test`, against a whole-tree change, answers `stale` / `build_scope_narrow`; a root `:build` row
   beside a lone `:core:test` row against a whole-tree change is refused; `parse_row_scope` of `: :` returns `None`. These hold at
   `877a05ac7`: a lone-task row confined to its own subproject against a change confined to that subproject is not refused as narrow; the
   two-task shape reads as before.

5. **The documents and the pins say what the writers, the gate and the client do.**
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: documenter
   - `manage-change-ledger/SKILL.md` and `manage-tasks/SKILL.md` carry one statement of the absent-versus-null rule and no longer contradict each
     other; `manage-change-ledger/SKILL.md` no longer says the executor writes its row through `append --kind build` (the template imports
     `build_record` directly). `build-server-client/SKILL.md` says plan-less outcomes go to the global work log, in both places it says "plan
     work log".
   - The old-behaviour and change-history wording the PLAN-LB-146 landing and the grounding read list is replaced by a statement of the
     current behaviour (Claim Labels list the phrases and lines). Remove the claim in the template and in the gate that a failed capture reads
     as "no mid-build rewrite": the gate refuses it.
   - The doc-contract test `test_build_tree_naming_doc_contract.py` pins retired text the old documents really held: the plan-less sweep
     searches the sentence the parent document carried (`silent by design`), and every pin's `retired` string is either text the parent held
     or is relabelled as a planted mutation. The `_D2_` italic-marker statement in the rubric documents is corrected or the regex is.

   *Done when:* each of these fails at `877a05ac7`: the plan-less sweep fails on a planted copy of the parent document's
   `**Plan-less builds are silent by design.**`; no pin's `retired` string is absent from the parent text unless it is labelled a planted
   mutation; the two documents state one rule on an absent and a null key. These hold at `877a05ac7`: the sweep holds on the shipped tree;
   every existing pin still passes on the changed documents and fails on its planted control.

Split guard: five deliverables, one theme (a build fact names its tree and no writer is refused for what it did not claim). D1 and D2 share the
recorder; D3 is `worktree_sha.py`; D4 is a different module of `manage-tasks`; D5 is prose and ships last. D3 and D4 share no function with
D1 or D2 and can ship separately if one is blocked, which the PR records.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- Fail closed: an unresolvable root, an explicit `null`, an unreadable row and a failed hash never read as "same tree" or "matching". The only
  admission this plan widens is a row whose writer recorded NOTHING about the tree, which is the legacy shape the gate already admits.
- One reader per concept: the recorder and the gate resolve the root through the same resolver call; no second copy.
- The recorder stays fire-and-forget: an exception at the ledger boundary never fails the build.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so; a gate test drives the real
  function; a recorder test drives the rendered template's real `main()` where the Done-when names it.
- The template changes (D2), so the PR states that an executor regeneration is owed in every project.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `build_record` writes `worktree_root` and `worktree_sha_at_dispatch` unconditionally, as `None` when the caller passes nothing — read at `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` § `build_record` (L139-155, L253-254)
- OBSERVED: the gate reads a key ABSENT as `unrecorded` (legacy, matched as before) and a key PRESENT with a null or empty value as `unreadable` and refuses — read at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` § `_row_tree_verdicts` (L346-387) and the route order (L313-322)
- OBSERVED: three production callers of `build_record`: the executor template (L1216-1230, passes both keys), the CLI `manage-change-ledger.py` (L141-149, passes neither) and the routing seam's auxiliary row (`script-shared/scripts/build/_build_execute_factory.py` L563-574, present-null keys, `worktree_sha=None`, never a candidate) — leaf search by `grep -rn build_record` over `marketplace/` and `test/`
- OBSERVED: no production caller of `manage-change-ledger append --kind build`; the SKILL.md statement that the executor writes through it is refuted, the template imports `build_record` directly (L435-439) — leaf search
- OBSERVED: in this source checkout a stale executor's pinned directory for `manage-change-ledger` is the live `marketplace/bundles` tree, so it imports the HEAD `_ledger_core` and its old call (no keyword arguments) writes present-null rows the live gate refuses — leaf trace of `generate_executor.py` (L2028-2029, L2077-2094) and the template bootstrap (L179-241, L323-367); the rendered `.plan/execute-script.py` was not read
- HYPOTHESIS: in a consumer project whose pinned cache version has been pruned, the self-heal imports the newest cache's `_ledger_core` and the same refusal follows; which gate copy then dispatches is not shown — confirm/refute at `execute-script.py.template` § bootstrap (verify-at-outline, D1; the fix does not depend on it)
- OBSERVED: the recorder's plan id is `extract_plan_id(script_args) or audit_plan_id`, with `--audit-plan-id` stripped before the wrapped script runs — read at `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` § `main` (L2343, L2365-2366); the hash and root follow from it (L2423, L1103-1108, L1213-1215; leaf)
- OBSERVED: the wrapper builds `cwd_checkout_root()` when no `--project-dir` is given and `abspath(--project-dir)` when it is, and the build subprocess is started with no `cwd=` — leaf read of `script-shared/scripts/build/_build_cli.py` (L747-758), `script-shared/scripts/resolve_project_dir.py` (L111-136) and the template (L2457-2462)
- OBSERVED: no test covers `--audit-plan-id` or `--project-dir` on the recorder — leaf search of `test/plan-marshall/tools-script-executor/test_build_tree_identity_recorder.py`
- HYPOTHESIS: a build the daemon routes (`--resolved-project-dir`) reaches this recorder with the arguments `main()` reads, so the fix covers it — confirm/refute at `script-shared/scripts/build/_build_execute_factory.py` (L1888-1925) and `manage-build-server/scripts/marshalld.py` (verify-at-outline, D2; the leaf did not read `marshalld.py`)
- OBSERVED: `_run_git` runs `subprocess.run(['git', ...], cwd=..., capture_output=True, check=False)` with no `timeout`, catches only `(OSError, ValueError)`, and `compute_worktree_sha` discards the return codes of `diff` and `ls-files` (L88, L93, L95) — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/worktree_sha.py` § `_run_git`, `compute_worktree_sha` (L58-118; leaf)
- OBSERVED: the house pattern is `_GIT_TIMEOUT_SECONDS = 60` with `(OSError, subprocess.SubprocessError)` caught (`_plan_state_exemption.py` L64, L103-112, L134-143) and `timeout=15` plus `TimeoutExpired` for the root resolution (`file_ops.py` L1018-1028) — leaf read
- OBSERVED: a lone `:core:test` task returns `RowScope(':core:test', ())`, an empty scope, because the multi-task branch needs `len(payload) > 1` and the lone row falls to `payload = payload[:1]`; the row is then canonical-unknown and the verdict `UNDETERMINED`, which passes as an inability — read at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` § `parse_row_scope` (L882-895, leaf-traced through L1021-1051, L1254-1272, L1376-1377, L1426)
- OBSERVED: a `: :` payload derives an empty subproject scope today and reads whole-tree — read at `_freshness_crosscheck.py` § `_gradle_subproject_scope` (L744-751; leaf)
- OBSERVED: `_required()` in the gate fixtures is whole-tree by default, so the lone-row test's "not refused" outcome is a whole-tree pass — leaf read of `test/plan-marshall/manage-tasks/_freshness_notation_crosscheck_fixtures.py` (L195-216)
- OBSERVED: three tests pin the lone-row reading and flip with the change: `test_freshness_notation_crosscheck.py` L1159-1179, L1223-1232 and L1248-1256; L1235-1246 compares two equal refusals and likely still holds (not run) — leaf read
- OBSERVED: the sweep test `test_no_document_still_describes_the_plan_less_submit_as_silent` searches `A plan-less build is silent by design.`, a sentence the parent never held; the parent said `**Plan-less builds are silent by design.**`; pins 2 to 8 of the doc-contract test use `retired` strings the parent did not hold (a wrapped line, `Re-run the build.`, `The hash is computed against whatever directory…`), and only pin 1 is real parent text — leaf comparison with `git show e81ddd6b1:` and `git log -S`
- OBSERVED: the two documents contradict each other (`manage-change-ledger/SKILL.md` L387 "both optional and None for a row written before they existed" and "the payload-less CLI writer needs no change"; `manage-tasks/SKILL.md` L309-317 a present null is unreadable); the gate's own comment at L265-269 says `unrecorded` is "absent or null" against its code at L366-371; the recorder's docstring at L1129-1131 says a failed capture reads as "no mid-build rewrite" while the gate refuses it as `worktree_dispatch_hash_unreadable`; `build-server-client/SKILL.md` L139 and L164 say "plan work log" for plan-less outcomes that go to the global log — leaf read, the code side re-read for the gate and the writer
- OBSERVED: the change-history phrases to replace: `manage-tasks/SKILL.md` L299-300, L310, L313, L594, L772, L836; `build-server-client/SKILL.md` L78, L142-144, L158-159; `build_server.py` L292-295; the template L1083-1084, L1097-1098; the gate L79, L80-81, L355, L962, L1027; test docstrings `test_freshness_build_tree_identity.py` L7-8 and `test_build_tree_identity_recorder.py` L5-6 — leaf search at `877a05ac7`, not re-read
- OBSERVED: `L3-3` of the PLAN-LB-144 landing: `_criteria_snapshot.py` L150 refuses `_D2_` while `review-rubric.md` L32 and `functional-review.md` L279 say italic markers are accepted — leaf read; fails closed
- OBSERVED: no running row declares a path of this plan: PLAN-LB-136 (Antigravity rules, the runtimes, `phase-4-plan/SKILL.md`, the manifest) and PLAN-LB-148 (the lane's review check, the GitHub scripts, `bot_registry.py` and their documents) share none of the files below; no PLAN-LB-136 or PLAN-LB-148 worktree is among those listed — leaf read of both specs and `git worktree list`
- Verify-first clause: before scoping D1, drive the current executor's call (no keyword arguments) and the CLI through `build_record` and the gate and state which refusal each row gets, so the red runs the Done-when asks for exist; a writer that does not reach the refusal narrows D1 and the PR says so. Before scoping D2, read where the wrapper's `--project-dir` and `--plan-id` reach the recorder for a routed build. Before scoping D3, read every caller of `compute_worktree_sha`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` — `build_record` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py` — the `append` build writer (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — the routing seam's auxiliary row, only if its keys must be omitted (D1; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — the legacy-versus-null comments and docstrings, the change-history phrases (D1, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — `main`, `_ledger_tree_root`, `_capture_dispatch_tree_state` and their docstrings (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/worktree_sha.py` — `_run_git`, `compute_worktree_sha` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `parse_row_scope` and its comments (D4, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` (D4, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/scripts/build_server.py` — `_audit_log_plan_less` wording (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — the `_D2_` statement only (D5)
- OBSERVED: `test/plan-marshall/manage-change-ledger/test_manage_change_ledger.py` and `test/plan-marshall/manage-change-ledger/test_manage_change_ledger_append.py` (D1)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_build_tree_identity.py` (D1, D5)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_build_tree_identity_recorder.py` (D2, D5)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_generate_executor.py` — only if the template imports something new (D2)
- OBSERVED: `test/plan-marshall/script-shared/test_worktree_sha.py` (D3)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` (D4)
- OBSERVED: `test/plan-marshall/manage-tasks/test_build_tree_naming_doc_contract.py` (D5)

## Dependencies and Sequencing

- Depends on: PLAN-LB-146 (shipped, `877a05ac7`); PLAN-LB-144 (shipped).
- Overlaps with: none among the running rows (Claim Labels). The shipped PLAN-LB-146 edited the same files; the lane works against `877a05ac7` or later.
- Adjacent to, not in this plan: the operator's second decision of 2026-11-12 (a deliverable retired with no successor), which waits for the operator because the grounding showed the "remove it from the outline" route does not close a deliverable whose spec Done-when is frozen; the PLAN-LB-144 residue that sits in other files (the findings-store rewrite in `jsonl_store.py`, a silent legacy-row case in `review_completeness.py`, the remedy text in `pre_merge_gate.py`), which the grounding read graded but did not stage; and the executor regeneration, which this plan makes no longer blocking but does not perform.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-149-build-row-writers-and-freshness-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
