# PLAN-LB-146: A build result names the tree it built, and the freshness gate and the executor hash the same tree

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-146-build-result-names-the-tree-built.md` and is queued as one row file, `queue/PLAN-LB-146.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged by the analyze drain of 2026-11-11 from `lessons-routing` findings 085 (a quality gate that rewrites files leaves the freshness gate
> unclearable, from pm-mcp-core plan `plan-v2-93-http-tests-annotations`) and 086 (a raw build-server submit with no plan selector builds
> the main checkout and reports success, from API-Sheriff plan `plan-23-session-route-scope-parity`), both graded high by the operator in
> the 2026-11-10 drain of that epic's inbox. Grounded against `main` at `280e6c404` by a read-only leaf, with the orchestrator re-reading
> the executor's row recording, the gate's root resolution and the submit verb. Finding 085's mechanism was **only partly** confirmed (see
> the Claim Labels) and a stronger one was found beside it. Every Done-when below fails at `280e6c404` unless it is a stated hold. No Sonar.
> No token or measurement work.

## Objective

Two build facts are recorded against a tree nobody names. The executor stamps each build row with the hash of the directory it happened to
run in (`os.getcwd()`) at completion, while the freshness gate hashes the plan's resolved worktree root, so a build dispatched from another
directory records the wrong tree and re-running it the same way can never clear the gate. And a raw build-server submit with no plan
builds whatever `--project-path` names and answers with a reply that does not say which tree that was, so a green result for the main
checkout is indistinguishable from one for the plan's worktree. This plan makes the recorded hash and the gate's hash come from one root,
makes a gate that rewrote the tree say so, and makes a submit and its wait name the tree they built.

## Deliverables

1. **The build row and the freshness gate hash the same tree.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: implementer
   - The executor's `_append_build_ledger_record` resolves the root the freshness gate resolves for the same plan — the plan's worktree
     root through the shared plan-context resolver — and hashes that, instead of `os.getcwd()`. A plan-less dispatch keeps the working
     directory. The row records the root it hashed, so the two readings can be compared.
   - The gate names a row whose recorded root differs from its own as that mismatch, never as `stale` with no cause.
   - Decide at outline, and record in the PR, how an already-recorded row without a root is read (this spec's default: as today, with no
     mismatch claim).

   *Done when:* each of these fails at `280e6c404`: a build dispatched with its working directory at the main checkout and `--plan-id` of
   a plan with a worktree records the worktree's hash and the gate then reads it as matching the worktree tree; the same dispatch's row
   carries the root it hashed; a row hashed against another root reads as a root mismatch at the gate. These hold at `280e6c404`: a
   dispatch whose working directory is already the plan's worktree root records the same hash as before; a plan-less dispatch records the
   working directory's hash.

2. **A build that rewrote the tree is named, and a long build cannot fold a later edit into its success.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: implementer
   - The row records the tree hash at dispatch as well as at completion. When they differ, the gate's `stale` verdict names the cause
     (the build changed the tree, commit the rewrite and re-run) instead of reading `build_indeterminate` against a dispatch row that
     carries `unknown`.
   - Decide at outline, and record in the PR, between this spec's default (disclose, and match only on the completion hash) and accepting a
     row whose dispatch hash equals the current tree when the difference is the gate's own rewrite. The second option credits a row for a
     tree it did not build; it is chosen only if the outline can show the rewrite is the gate's own.
   - A file edited while a long build runs is no longer silently part of the success row's tree: the dispatch/completion difference
     makes that visible.

   *Done when:* each of these fails at `280e6c404`: a build whose gate rewrites a tracked file between dispatch and completion records both
   hashes and the freshness gate's reason names the rewrite; a build during which a file was edited records differing hashes. These hold at
   `280e6c404`: a build that changes nothing records equal hashes and a success row for the current tree reads fresh; a re-run on the
   clean committed tree clears a stale verdict.

3. **A build-server submit and its wait name the tree they built.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - The submit reply carries `exec_path`, `project_path` and `plan_id` (with `NO_PLAN` stated, not blank), and the wait reply passes them
     through, so a caller compares the tree built with the tree it meant. The kind=job ledger row already stores the project path; the
     reply reads it from the job spec the client built.
   - A plan-less submission is written to the work log as plan-less rather than left out, so a green result for the main checkout leaves a
     trace beside the plan's own builds. This plan does NOT refuse a plan-less submit of the main checkout: that is a legitimate build (this
     session's own `generate-*` calls ran it, `plan=NO_PLAN`, through the wrapper path that already prints that line).
   - Decide at outline, and record in the PR, whether the daemon's `wait` reply needs a change or the client can read the fields from its
     own job record; this spec's default is the client side only.

   *Done when:* each of these fails at `280e6c404`: a plan-less `submit` of the main checkout returns a reply carrying `exec_path`,
   `project_path` and `plan_id: NO_PLAN`; the matching `wait` reply carries the same three; the work log records the plan-less
   submission. These hold at `280e6c404`: a submit that names a plan returns the fields it returns today and keeps its work-log line;
   a plan-less submit is still accepted and queued.

4. **The documents and the pins say what the recorder, the gate and the client do.**
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: documenter
   - `manage-tasks/SKILL.md`, `build-server-client/SKILL.md` and the executor template's own prose state the root the row is hashed
     against, the two hashes and the reply fields. A doc-contract test pins each statement with a control that plants the old sentence.
   - The executor template changed, so the PR states that an executor regeneration is owed in every project.

   *Done when:* the doc-contract test passes on the changed documents and fails on a planted copy of the old sentence, for each pinned
   document; it fails at `280e6c404` because no document states a root or two hashes.

Split guard: four deliverables, one theme (a build fact names its tree). D1 and D2 share the recorder and the gate, D3 is the client; D3
shares no function with D1 or D2 and can ship separately if one is blocked, which the PR records.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- Fail closed: an unresolvable root, an unreadable ledger row and an unreadable job record never read as "same tree" or "matching".
- One reader per concept: the recorder and the gate resolve the root through the same resolver call, not two copies of it.
- The recorder stays fire-and-forget (an exception at the ledger boundary never fails the build); a recording fault is not read as a
  recorded row.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so. A gate test drives the
  real function and not an assembled verdict.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the executor stamps a build row with `compute_worktree_sha(os.getcwd())` at completion — read at `tools-script-executor/templates/execute-script.py.template` § `_append_build_ledger_record`, L1112-1129
- OBSERVED: the freshness gate hashes `resolve_plan_context(plan_id, ensure=False).worktree_path`, falling back to the working directory only when the worktree is unresolvable — read at `manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` L665-675
- OBSERVED: `run_submit` sets the plan id to `NO_PLAN` when absent, takes `exec_path` from `--exec-path` or `--project-path` (itself the working directory by default), builds the job spec from the caller's command, and returns only `status`, `job_status`, `job_id`, `attached` and `queued_behind`; the comment at L437-440 says `_audit_log` treats the sentinel as absent — read at `build-server-client/scripts/build_server.py` § `run_submit`, L435-524
- OBSERVED: a main-checkout `generate-claude` call routed through the daemon printed `plan=NO_PLAN` on the wrapper path in this drain (the wrapper states the plan; the raw submit does not)
- HYPOTHESIS: the executor writes exactly one kind=build row per build-executing dispatch, after the subprocess exits, and no dispatch-time kind=build row exists; the submit-time row the build server writes is kind=job, which the gate ignores — confirm/refute at `execute-script.py.template` § main (L2436-2461), `build-server-client/scripts/build_server.py` L323-340, `manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` L721-727 (leaf read; verify-at-outline)
- HYPOTHESIS: finding 085's mechanism holds only for a non-idempotent rewrite: a gate that rewrites tracked files stamps its success against the dirty end-state hash, a pre-commit check on that same dirty tree matches, and after the commit an idempotent re-run on the clean tree records the clean hash and clears the verdict; "re-running can never clear it" holds only when every run re-dirties the tree in a way later removed — confirm/refute at `execute-script.py.template` § `_append_build_ledger_record` and `manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` § `_stale_reason` (leaf read, L261-271; verify-at-outline, the finding's two jobs `8af4fa43` and `e01bad99` are not available to read)
- HYPOTHESIS: the same end-state capture allows a false fresh — a file edited during a long build is folded into the success row's hash — confirm/refute at `execute-script.py.template` § `_append_build_ledger_record` (leaf read; not re-read)
- HYPOTHESIS: a build dispatched with a working directory other than the worktree root (for example `--project-dir {worktree}` from the main checkout) records the wrong tree's hash and re-running it the same way never clears the gate; a subdirectory working directory also changes the cwd-relative `git ls-files --others` output — confirm/refute at `script-shared/scripts/worktree_sha.py` § `compute_worktree_sha` (leaf read, L78-118)
- HYPOTHESIS: the daemon's `submit` verifier checks registration, argument shape and path containment only, the main-checkout root equals the canonical root and is accepted, and the plan id is used for audit attribution and never for admission — confirm/refute at `manage-build-server/scripts/marshalld.py` § `_submit` and `manage-build-server/scripts/_marshalld_verifier.py` § `verify_submit` (leaf read, L473-514 and L232-306 with L170-173)
- HYPOTHESIS: the wait reply carries only the passthrough status fields (job id, elapsed, exit code, log file and similar) and no tree — confirm/refute at `build-server-client/scripts/build_server.py` § `_PASSTHROUGH_STATUS_FIELDS` (leaf read, L107-131, L292-315)
- HYPOTHESIS: the shipped PLAN-LB-107, 120, 124 and 130 lineage changed scope and notation reading and the unreadable-row handling and none of them changed where or when the hash is captured — confirm/refute with `git log` of the template and the gate (leaf read; nothing touched these files since `e7033b83a`)
- Verify-first clause: before scoping D2, reproduce finding 085's two cases by reading the executor and the gate (a rewriting gate, then an idempotent re-run) and state which of the two the report was; a refuted "cannot clear" narrows D2 to the disclosure.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — `_append_build_ledger_record` (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — the root resolution at L665-675 and `_stale_reason` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/worktree_sha.py` — only if the root must be passed or recorded here (D1; prefer no change)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/scripts/build_server.py` — `run_submit`, the wait reply, the plan-less audit log (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — only if the `wait` reply must change on the daemon side (D3; prefer no change)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` and `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` (D4)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/test_generate_executor.py` — the recorder's tests, or a new module beside it (D1, D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py`, `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` and `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness_unresolvable_worktree_falls_back_to_cwd.py` — the gate's tests and the one that pins the working-directory fallback (D1, D2; the files exist, found with `architecture find`)
- OBSERVED: `test/plan-marshall/build-server/test_build_server_client.py` — the submit and wait tests (D3; the file exists, found with `architecture find`; there is no `test/plan-marshall/build-server-client/` directory)
- HYPOTHESIS: a new doc-contract test module for D4 placed beside the existing tests of those two skills; its path is named at outline

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-144 on `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` and `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` (two files, so an overlap prompt is due at emit; PLAN-LB-144 names both as HYPOTHESIS entries, the first for its notation-scope paragraph and the second only if its Gradle ledger needs a fixture helper). Sequence after PLAN-LB-144. PLAN-LB-144 D4 edits `manage-tasks/scripts/_freshness_crosscheck.py` and its tests, a different module of the same skill; this plan edits `_cmd_pre_commit_verify_freshness.py`. Finding 085 sits on the same gate as PLAN-LB-144 D4 and is NOT folded into it: the mechanism differs (the recorded hash, not the Gradle submodule row).
- Adjacent to: the shipped wrapper-path work PLAN-LB-104, PLAN-LB-112 and PLAN-LB-115 (a routed build resolves the tree the caller named), which does not cover the raw `submit` verb; `lessons-routing` findings 068 (a freshness pass on a 5-test row labelled whole-tree, the false-pass direction) and 076 (a routed build that misreports a routing failure as `build_failed`), whose dispositions were not read here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-146-build-result-names-the-tree-built.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
