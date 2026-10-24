# Landing Analysis: PLAN-LB-80 — The repository's skill veto fails closed, narrows exactly and reaches every seam

epic: live-blockers
workstream: WS-01
pr: #1854 (`f4bb6a040`, merge queue, base `main`)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction or `guard.log`.
> **(store)** = read from the OpenCode session database, read-only (counts, tool names, command words, times; no message
> text). Nothing was executed. Token usage is out of scope by the 2026-10-23 ruling and is not analysed. The correctness of
> the veto logic was not re-executed: it rests on the PR's tests and green CI.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all four sessions **(store)** (root plus three self-review
sub-agents, all `succeeded`, none killed), 22 h 14 min wall clock (2026-10-23T15:32:08Z to 2026-10-24T13:45:53Z).

All four deliverables are met as the landing states them, CI is green and no review thread is open **(re-read)**. The report
is accurate on the points the store can settle: the single guard refusal, the seven operator question calls (five reported
cases, one of which was asked three times), the three lane-text loads, the zero edits outside the worktree and the Sonar reads.
Debits: the declared persona and six domain skills were never loaded (disclosed, the run's own largest miss); the report says
one server restart where the store shows two; and the last head (`5ad090512`) fixes a CodeRabbit major finding with changed
logic that no reviewer saw.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 Unreadable `marshal.json` reports instead of reading as "no exclusions" | shipped-as-specified | `extension_base.py` (+226), `test_exclusion_fail_closed.py` (349), absent-file regression guard kept **(re-read: diff)** |
| D2 Bundle-qualified exclusion narrows exactly | shipped-as-specified, evidence `mutation-after` | `is_excluded` change, own-bundle and other-bundle tests, mutation logs cited |
| D3 Optionals offered to a module are the ones it can use; `phase-4-plan` names no call no script makes | shipped-as-specified | `_cmd_client_query.py`, `phase-4-plan/SKILL.md`, `manage_personas.py` (+229) |
| D4 Every read seam applies the veto | shipped-as-specified | `_cmd_enrich.py`, `_cmd_skill_resolution.py`, `manage-solution-outline.py`, three new test modules |

Claimed `deliverables_done=4` of 4; the table agrees. Several clauses carry `order=none` or `mutation-after`; the landing
labels each honestly.

**Surface.** Spec declared 12 entries (3 directories); the diff has 19 files (+1438/-124) **(re-read)**. Added outside the
declaration, all five disclosed in the landing: `extension-contract.md`, `_cmd_client_render.py`, `_cmd_suggest.py`,
`test/plan-marshall/manage-config/test_skill_resolution_exclusions.py` and `test/plan-marshall/manage-solution-outline/
test_get_module_context_exclusions.py`. Declared but untouched: none. The shipped spec is not edited.

## Findings by the orchestrator

- **Lane text re-read after restarts** **(store)**: loaded at 15:32Z, again at 12:49Z (a minute after a restart notice at
  12:48Z) and again at 13:39Z (after a second restart notice at 13:38Z). Better than LB-86 and LB-88. **The landing reports
  one restart; the store shows two** (both fall after the PR merged, around cleanup).
- **Operator questions** **(store)**: seven `question` calls (15:32Z, 19:56Z, 23:35Z, 11:04Z, 12:50Z, 13:28Z, 13:30Z) =
  the five cases in the landing, with the cleanup question asked three times (aborted by a restart, dismissed, answered).
- **Skills not loaded** **(store)**: the root loaded three skills, all the lane skill. The persona and the six domain skills
  were never loaded, as disclosed.
- **Guard attribution** **(re-read, store)**: exactly one refusal line in the tree (R1, 22:24:56Z) = the landing's. No edit
  outside the worktree (100 worktree edits, 9 under `.plan/temp/`, 8 PR bodies). Read-class shell calls: `tail` 5, `wc` 1,
  `find` 1; the landing names `tail` four times, `wc` once and a `sed`/`sort` pipeline, so `find` is unlisted and a `git grep`
  it reports could not be matched in the store by command text.
- **Sonar** **(store)**: three `read_open_issues` calls (08:41Z, 09:46Z, 10:35Z), all `open_issue_count: 0`, a `sonar-gate`
  verdict `merge_allowed: true` at 09:46Z, then `sonar-facts` for the landing. The second runbook landing whose measured count
  was written by the run itself (after PLAN-LB-88).
- **Reviews** **(re-read)**: CodeRabbit reviewed `66cf6fb2c` and `0afb10f0e`; the re-trigger on `5ad090512` was refused on
  quota. Sourcery refused (optional). Every thread resolved.
- **Last head unreviewed, second instance.** `5ad090512` fixes two CodeRabbit round-2 findings (a major: the flattening sweep
  applied one domain's owner to another domain's bare cell skill) by changing resolver logic, with a mutation record but no
  reviewer. It merged on the standing authorization without a question. The 2026-10-23 ruling asks the plan to retry a
  re-review and to ask the operator when the quota blocks it; the lane text as merged
  (§ 7, standing authorization conditions 1-4) has no ask step, and this run met all four conditions, so it followed the lane
  as written. Whether the ruling's "ask if the quota blocks" applies here is an open point for the operator. Same shape as LB-88.
- **Stray files in the main checkout**: the run's cleanup hit a dirty main checkout (an untracked test file from the running
  PLAN-LB-55 and a `uv.lock` drift). Both were cleared by the operator earlier today; not this run's.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1854; `landing` `landings/PLAN-LB-80.md`; `plan_marshall_plan_id` `lb-80-lb-76-completion`
- [x] epic.md: Queue annotation, model-comparison Watch (grade), the unreviewed-last-head Watch extended (second instance)
- [x] resume anchor and `queue-view.md` regenerated

## Follow-Ups

- Residue the landing lists (`skill-domains list` swallows a per-extension failure, `enrich all` reports success over errors,
  consumer enumerations under-list the veto) is accepted under the focus rule: none blocks a plan from running.
- None staged.
