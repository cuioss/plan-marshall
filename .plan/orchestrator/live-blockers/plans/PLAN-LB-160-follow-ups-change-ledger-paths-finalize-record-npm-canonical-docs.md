# PLAN-LB-160: Follow-ups from the PLAN-LB-158 landing — a change-ledger row that records every path, a finalize commit whose missing row is seen, and the stale statements left beside it

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

The PLAN-LB-158 lane answered five review findings and one stale-statement sweep with "pre-existing, outside this plan's surface". They are small, share one theme (the `kind=change` ledger row and the commands that feed it), and are closed here in one plan because the operator asked for a single small plan:

1. **A row that loses paths.** A merge commit's changed paths are enumerated with `git diff`, which follows the user's rename detection, so a renamed file records only its new path. The append verb splits `--changed-paths` on commas and trims each segment, so a path with a comma, or with leading or trailing whitespace, is stored altered.
2. **A failure nobody reads.** The `commit` verb reports `ledger_recorded: false` when it cannot write the row, and its docstring says the `5-execute` boundary's `bookkeeping_gap` refusal then surfaces it. That boundary runs before `6-finalize`, so for a `6-finalize` commit nothing is shown to read the flag.
3. **Stale or unfollowable statements.** The changed-path commands in the phase documents read `-z`, which the Bash tool shows as spaces; one test comment and possibly the `cwd-policy` document family still describe the pre-PLAN-LB-153 row owners or resolvers; npm's chained `verify` carries no canonical identity beside every other canonical.

## Deliverables

1. The `cwd-policy` document family states what the merged code does: where a statement says the `resolve_main_anchored_path` resolver is the only departure from cwd-relative resolution and the `commit` verb's ledger write (a path taken from the target tree it was handed, not from the caller's cwd) contradicts it, the statement is corrected or narrowed; where no statement is contradicted, the plan changes no document and its message says which documents were read and why none needed a change. No statement is rewritten as a history note.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation, pm-plugin-development:plugin-architecture
   - Persona: documenter
2. A merge commit's `kind=change` row records every path the merge changed, a rename's old path included: the merge enumeration in `workflow-integration-git/scripts/git-workflow.py` (`_commit_changed_paths`, the first-parent branch) turns rename detection off, and every document that states that command (`manage-change-ledger/SKILL.md`, `workflow-integration-git/SKILL.md`, the phase-5 and recovery documents that name the first-parent form) states the same command. The non-merge branch, the `--root` handling and the NUL parsing are unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
3. A `kind=change` row stores a changed path without alteration, and the documented procedure that produces the list can be followed through the Bash tool. A path containing a comma, a space, a leading or trailing space, or a non-ASCII character reaches the ledger exactly as git printed it, through the real `append` verb. The verb gains a lossless way to receive the list (the outline chooses the shape — a repeatable single-path flag, or a file of NUL-separated paths under `.plan/temp/` — and names its reason); the comma-separated form keeps working for a caller that does not need it. The phase-5, finalize and recovery documents that name the changed-path commands state a form an agent can follow given that the Bash tool renders a NUL byte as a space: the documented command and the way its output reaches the verb must not depend on the reader seeing a NUL.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
4. A `6-finalize` commit whose row failed to record is visible to the caller that made the commit. The outline settles first what reads a finalize-phase row (verify-first clause below); then either (a) the finalize commit paths that call the `commit` verb read `ledger_recorded`, log a WARNING decision naming `ledger_error` and the ready-to-run `append` invocation, and do not report the step as cleanly done while the row is missing, or (b) when no consumer exists for a finalize-phase row, the claim in `_record_commit_change`'s docstring and in `workflow-integration-git/SKILL.md` that the boundary surfaces the missing row is corrected to say it does not for a `6-finalize` commit, and the plan states that no row is owed there. Either way the docstring and the skill document stop claiming a refusal that cannot fire.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
5. npm's chained `verify` carries the canonical identity on every hop it emits, as every other canonical string does: `build_chained_commands` in `script-shared/scripts/build/_build_shared.py` takes the canonical name and emits `--canonical {name}` on each chained invocation, and npm's discovery passes `verify`. No run-path guard reads an npm canonical today, so no behaviour changes; the change removes the one canonical string that claims no identity.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
6. Tests pin deliverables 2 to 5 and the stale comment: a real merge commit that renames a file through the merged branch records both paths (the test builds a real repository, as the existing rename-edge tests do, and fails against the unfixed enumeration); a path with a comma, a space, a leading space and a non-ASCII character round-trips through the real `append` verb byte for byte, and the comma-separated form still stores what it stored; a `6-finalize` commit whose row cannot be written yields the visible outcome deliverable 4 settled on, and the docstring claim it replaced is gone; npm's chained `verify` string carries `--canonical verify` on every hop and the existing npm discovery tests still pass. The comment in `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py` that says "outside both settlement owners" names the three row owners the code now has. The doc-contract assertions in `test/plan-marshall/phase-5-execute/test_phase5_change_ledger.py` that pin the changed-path commands are updated to the commands deliverables 2 and 3 settle on, and every other test that passed before still passes.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The merge enumeration (D2) changes which paths a merge row records and nothing about which commits get a row, the row's other fields, or the non-merge enumeration.
- The lossless input (D3) must not change how an existing comma-separated caller's list is stored when no path contains a comma, and must not move the paths' git-sourcing to anything but git: the contract that the caller git-sources the paths stays, and nothing computes a list from a deliverable's `affected_files`.
- D4 adds no new refusal code and no new gate. It makes an existing outcome visible; it does not make a finalize commit refuse.
- D5 changes no run-path behaviour: no guard reads an npm canonical, and the regeneration obligation the PLAN-LB-158 change documented already covers the new flag, so this plan adds no new one.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Recorded and not changed by this plan: the `--canonical` regeneration obligation for every consumer project (documented in `extension-api/standards/build-api-reference.md`, an operator note for the release); whether a persisted `module-tests` command without `--canonical` keeps the zero-test guard inert (traced by an `architecture resolve` read after `/apply-changes`, not a code change); the PLAN-LB-157 `loop_back` admission; the PLAN-LB-159 first-drift record order.
- Scope-bloat note: six deliverables, kept in one plan on the operator's word and because every one is a few lines or a few sentences; deliverables 1 and 5 are the two the outline may shrink (D1 can close with no document change, D5 changes no behaviour). Presumptive-split guard: if the outline finds D4 needs a new dispatcher step rather than a read of an existing return, it hands D4 back as its own plan instead of growing this one.

## Claim Labels

- OBSERVED (re-read at HEAD): the merge branch enumerates with `git diff --name-only -r -z {sha}^1 {sha}`, no rename option — `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` lines 1044-1047; the non-merge branch uses `diff-tree`, which does not follow `diff.renames`.
- OBSERVED (re-read at HEAD): `_split_changed_paths` splits on `,` and trims every segment — `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py` lines 86-96; the flag's help names it comma-separated (`:502-504`).
- OBSERVED (re-read at HEAD): `_record_commit_change` returns `{'recorded': False, 'error': ...}` on an unreadable path list or an `OSError`, and its docstring says the boundary's `bookkeeping_gap` refusal surfaces it — `git-workflow.py` lines 1084-1087; `cmd_commit` reports `ledger_recorded` and `ledger_error` for a `6-finalize` commit or a `--record-change` one (`:1265-1270`).
- OBSERVED (searched at HEAD): `ledger_recorded` appears in no script outside `git-workflow.py` and in no document outside `workflow-integration-git/SKILL.md` and one test (`test_source_commit_gate_commit_path.py`); nothing in the repository reads it.
- OBSERVED (probed at HEAD): the Bash tool renders the NUL separators of `git diff-tree ... -z` output as spaces — five paths came back as one space-separated line.
- OBSERVED (re-read at HEAD): npm's chained `verify` is `build_chained_commands(skill, [f'run build{ws_arg}', f'run test{ws_arg}'])`, which emits `--command-args` per hop and no `--canonical` — `_build_shared.py` lines 92-109, `build-npm/scripts/_npm_cmd_discover.py:379`; the non-chained branch at `:381` goes through `build_canonical_commands`, which does.
- OBSERVED (re-read at HEAD): the stale comment is at `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py` line 713, "A commit made outside both settlement owners carries no row".
- OBSERVED (lane-reported by the PLAN-LB-158 landing, location not given): `cwd-policy.md` and five sibling documents still describe the main-anchored resolver as the only departure from cwd-relative resolution. At HEAD `cwd-policy.md` lines 34 and 92 call `resolve_main_anchored_path` "the single deliberate exception to cwd-relative resolution" and "the ONE sanctioned main-anchored resolver"; whether the `commit` verb's target-anchored ledger write contradicts that wording, and which five siblings carry it, was NOT established here.
- HYPOTHESIS: the `cwd-policy` statements are contradicted by the `commit` verb's write, because a path taken from `--project-dir` is not cwd-relative — confirm/refute by reading each candidate sentence (verify-at-outline); a refutation closes D1 with no document change.
- HYPOTHESIS: a `6-finalize` row has no consumer that would refuse on its absence — confirm/refute by searching the readers of `kind=change` rows (`pre-commit-verify-freshness`, the `5-execute` boundary, `plan-retrospective`) for any read that includes finalize-phase rows (verify-at-outline).
- HYPOTHESIS: the phase-5 document-contract test `test_phase5_change_ledger.py` pins the `-z` and `--root` text of the changed-path command and needs the same update as the documents — confirm/refute at the file (verify-at-outline).
- Verify-first clause: the outline settles (a) which `cwd-policy` family sentences, if any, the `commit` verb's write contradicts; (b) what reads a finalize-phase `kind=change` row, which decides D4's branch; (c) the lossless-input shape for D3 and why — a repeatable single-path flag against a NUL-separated file — including how an agent running under the one-command-per-call rule produces it.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/standards/cwd-policy.md` and its sibling documents that carry the same statement (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py`
- HYPOTHESIS: the finalize commit callers' documents under `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` that call the `commit` verb (verify-at-outline)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py`
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/test_phase5_change_ledger.py` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-change-ledger/`, `test/plan-marshall/workflow-integration-git/` and `test/plan-marshall/build-npm/` for the new tests (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-153, -156, -158 and -159 are shipped).
- Overlaps with: none staged; the queue holds no running or staged plan. Re-read before emitting: PLAN-LB-158 changed `manage-change-ledger/SKILL.md`, `workflow-integration-git/SKILL.md`, `phase-5-execute/SKILL.md`, `execution.md`, `_build_shared.py` and `test_phase5_change_ledger.py`'s documents; this plan edits the same files and so must start from the merged `main`, which the runbook lane's base does.
- Adjacent to: `PLAN-LB-153` (the hand-back commit row) and `PLAN-LB-158` (the `-z --root` commands, the `--canonical` channel) shipped the surfaces D2, D3 and D5 change.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-160-follow-ups-change-ledger-paths-finalize-record-npm-canonical-docs.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
