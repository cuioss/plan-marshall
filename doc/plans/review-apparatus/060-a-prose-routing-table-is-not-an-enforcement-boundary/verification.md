# Verification — 060-a-prose-routing-table-is-not-an-enforcement-boundary

**Landed as:** PR #1182, squash commit `ff11803b`
**Verdict:** partially-implemented

## Method

Read in full: `plan.md`, `report-01.md`, and the landed diff (`git show --stat ff11803b`,
`git show ff11803b -- <path>` for each of the four non-plan paths).

Ground truth taken from the current tree at `61a43e53` (branch
`claude/review-apparatus-analysis-mcf8md`). Read in the current tree:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  (`_resolve_base_queue_state`, `_refuse_on_required_merge_queue`, `cmd_pr_merge`,
  `cmd_pr_auto_merge`, `cmd_pr_safe_merge`, `cmd_pr_merge_queue`, `_safe_merge_delegate_ns`)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
  (`handlers: HandlerMap` registry, `_probe_merge_queue_state`)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`
  (`handlers: HandlerMap`, `_probe_merge_train_state`, `_refuse_on_required_merge_train`,
  `_corroborate_merge`, `cmd_pr_merge_queue`, `cmd_pr_merge`, `cmd_pr_auto_merge`,
  `cmd_pr_safe_merge`)
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
  (`dispatch`, `make_error`, the `pr merge-queue` parser)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (§ "Merge routing (`use_merge_queue`)", § "The dispatch set is CLOSED", the five
  `**Observability (mandatory)**` blocks, § "Rebase Branch onto Base")
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md`,
  `.../standards/gitlab-impl.md`, `.../standards/leaf-command-reference.md`
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md`
- `test/_shared/_merge_shaped_roster.py`, `test/_shared/_dispatch_roster.py`,
  `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`,
  `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py`,
  `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py`
- `.claude/skills/cloud-plan-lane/SKILL.md`, both at HEAD and at `ff11803b`
  (`git show ff11803b:.claude/skills/cloud-plan-lane/SKILL.md`), so the report is judged against the
  contract that governed it rather than a later one.

Searches run (each absence asserted below is backed by one of these):

- `grep -rn "_merge_shaped_roster" --include=*.md --include=*.py .` — consumers of the new helper.
- `grep -rn "pr safe-merge|pr merge-queue|pr auto-merge|ci pr merge" marketplace/bundles/ --include=*.md -l`
  — every doc naming a merge-shaped verb, then each hit read.
- `grep -rln "_MERGE_TRAIN_INELIGIBLE_HINT" .` — every copy of the changed message constant.
- `grep -rn "print(" ` over the two new test files, and `grep -rn "terminal_summary|report_header|pytest_report" test/conftest.py`
  — whether the population size reaches a passing run's output.
- `git log --oneline -- <path>` for each landed path, and `git log --oneline -S'<symbol>' -- <path>`
  for `ci pr merge-queue` in `landing-cycle.md`, `there is **no probe**` in `branch-cleanup.md`,
  `Verification loop exit` and `rev-list --count HEAD..origin/main` in the lane skill.

Ran: `uv run python -m pytest test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py -o addopts="" -q`
→ **18 passed in 7.79s**. No full build was run; no repository file was modified other than this file
and `gaps.md`.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | The population is derived and published with its size and its derivation method, or the null result is stated with the same evidence | 8 members = 4 verbs × 2 providers, derived from each `handlers: HandlerMap` literal; null result published; CI-wait route recorded as a near-miss | Both registries carry exactly `('pr','merge')`, `('pr','auto-merge')`, `('pr','safe-merge')`, `('pr','merge-queue')`; the near-miss quote is verbatim at `branch-cleanup.md:418` as of `ff11803b` | **Met** |
| D1 | Every D0 member refuses an off-routing dispatch, and the caller enumeration is published alongside — including any sanctioned exception found and how it is preserved | All 8 already guarded; `auto-merge` is the sanctioned exception; caller enumeration published | 7 of 8 carry a callee-side check. `gitlab:merge-queue` performs **no** state check — it POSTs and reads the provider's HTTP error. The published caller enumeration misnames the marshall-steward caller's verb | **Not met** |
| D2 | A departure from a documented route emits a record naming the route, the expected branch, and the verb actually dispatched | Already instrumented at all `use_merge_queue` sites; the callee refusal is the departure record; nothing new to instrument | The five `**Observability (mandatory)**` blocks exist; the refusals name the routed verb. But an off-routing `pr auto-merge` emits **no** departure record at all — it succeeds silently | **Partially met** |
| D3 | All three arms hold and the population size appears in the test's own output | 18 tests; non-emptiness first; size 8 published; every member covered; falsifiability measured by four mutations | The two files exist and 18 tests pass. The size appears only inside assertion **failure** messages — a passing run prints nothing. One arm (`[gitlab:merge-queue]` off-routing) is stub-manufactured and asserts only `status == 'error'` | **Partially met** |

### D0 — derive the population of prose-routed verb sets

**Met, and independently reproduced.** `github_ops.py:1876-1879` registers `('pr','merge'): cmd_pr_merge`,
`('pr','auto-merge'): cmd_pr_auto_merge`, `('pr','safe-merge'): cmd_pr_safe_merge`,
`('pr','merge-queue'): cmd_pr_merge_queue`; `gitlab_ops.py:2568-2571` registers the same four. The
derived population is 8. CONFIRMED.

The report's per-member guard table is accurate against the tree for all eight rows, including its
honest entry for GitLab `merge-queue` — *"merge-train POST; refuses (error) on 404/ineligible"*, which
correctly does **not** claim a probe.

The published null result — the merge routing is the only full four-part prose-routed verb set — was
not disproved. `grep -rn "ci branch delete|branch delete "` and `grep -rn "pr close"` over
`marketplace/bundles/plan-marshall/skills/**/*.md` find no second documented multi-branch route that
selects between CI verbs with a destructive member; the only other closed-set statement,
`branch-cleanup-rereview.md:3`, explicitly inherits the merge routing's own set rather than defining a
new one. PLAUSIBLE (a null result cannot be positively confirmed, but the searches that would have
refuted it came back empty).

The recorded near-miss is real: `branch-cleanup.md` § "Rebase Branch onto Base" / "CI gate before the
merge" routes `ci checks status` against `ci checks wait --adaptive` on the same `use_merge_queue`
flag, and the cited sentence *"the two paths are NOT symmetric"* is at line 418 in the file as it
stood at `ff11803b` (line 441 today). Both members are read-only, so part (d) genuinely fails.
CONFIRMED.

### D1 — callee-side refusal for every member

**Not met.** Seven of eight members carry a real callee-side check:

- `_github_pr.py:1467` — `cmd_pr_merge` calls `_refuse_on_required_merge_queue`, which at
  `_github_pr.py:1278-1281` refuses when `discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED`.
- `_github_pr.py:1687` — `cmd_pr_safe_merge` calls the same preflight before polling.
- `_github_pr.py:1894-1897` — `cmd_pr_merge_queue` refuses when `discriminator != MERGE_QUEUE_ELIGIBLE_CONFIGURED`.
- `_github_pr.py:1627` — `cmd_pr_auto_merge` probes via `_resolve_base_queue_state` and reports
  `disposition`.
- `gitlab_ops.py:1955` — `cmd_pr_merge` calls `_refuse_on_required_merge_train` (`gitlab_ops.py:622`,
  which probes at line 633 and refuses at line 639).
- `gitlab_ops.py:2202` — `cmd_pr_safe_merge` calls the same preflight.
- `gitlab_ops.py:2118` — `cmd_pr_auto_merge` calls `_probe_merge_train_state` and reports `disposition`.

The eighth, **`gitlab:merge-queue`, performs no state check at all.** `gitlab_ops.py:681-720`
(`cmd_pr_merge_queue`) goes straight from `_resolve_mr_iid` and `get_project_path` to
`run_glab(['api', '-X', 'POST', endpoint])`; `_probe_merge_train_state()` — which exists at
`gitlab_ops.py:567` and is used by all three of its siblings — is never called. The refusal is
whatever the provider returns:

```python
    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint])
    if returncode != 0:
        stderr_text = stderr.strip()
        if _is_auth_scope_error(stderr_text) or 'http 404' in stderr_text.lower():
```

This is exactly the asymmetry the plan's four-part shape names as part (c), surviving *inside* the
derived population, at the one member whose sibling on the other provider probes first. On a project
where `_probe_merge_train_state()` would return `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED`
(`merge_trains_enabled=false`), the callee has no opinion — if the endpoint ever answers 2xx there,
the verb returns `enqueued: true` for an MR that joined no train, which is the same false-green shape
the plan exists to close. CONFIRMED (the absence of the call); the 2xx consequence is PLAUSIBLE — it
depends on provider behaviour nobody in this repository has measured.

**The published caller enumeration is wrong.** The report states *"the marshall-steward landing cycle
uses `safe-merge`"*. `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md:152-154`
dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
  --head {branch}
```

unconditionally, with no `use_merge_queue` routing and no fallback (§ "Step 5: … merge via the queue",
sub-step (c): *"**(c) Merge via the platform merge queue** — WITHOUT `--delete-branch`"*).
`git log --oneline -S'ci pr merge-queue' -- <that file>` returns only `27be6350` (an ancestor of
`ff11803b`), so this was already true when the plan ran. CONFIRMED.

That matters beyond bookkeeping: this is a sanctioned caller that dispatches a merge-shaped verb
against a base whose queue state it never checks, and on a repository with no configured queue it is
refused by the callee with no documented remedy path. The plan's UNKNOWN claim — *"some legitimate
caller depends on reaching a D0 member outside its route"* — was resolved "in the negative" on an
enumeration that missed this caller.

### D2 — observability at the routing decision

**Partially met.** The five `**Observability (mandatory)**` blocks are present in `branch-cleanup.md`
(lines 360, 416, 614, 1269, 1541), and the two named locks exist:
`test_every_use_merge_queue_consumption_site_is_observable` (`test_branch_cleanup_merge_queue_routing.py:946`)
and `test_merge_routing_decision_precedes_the_dispatch_it_selects` (line 1034). CONFIRMED.

The refusal messages do name the route: `_github_pr.py:1281` names the base branch and
`"ci pr merge-queue"`; `_github_pr.py:1897` names the base branch and `"ci pr safe-merge"`;
`gitlab_ops.py:639` names `"ci pr merge-queue"`; `gitlab_ops.py:715` now names `"ci pr safe-merge"`.

The gap is the **sanctioned exception**. An off-routing `ci pr auto-merge` — a departure from the
closed dispatch set — returns `status: success` with `disposition: enqueued` and emits no record that a
route was departed from, naming neither the route nor the verb the route required. `ci_base.py:1978`
(`dispatch`) carries no logging either, so the router — named in the plan's Expected surface as *"the
router that performs the dispatch"* — records nothing. D2's *Done when* ("a departure from a
documented route emits a record naming the route, the expected branch, and the verb actually
dispatched") therefore does not hold on the one path the plan explicitly declined to make refuse.
CONFIRMED.

### D3 — tests

**Partially met.** Both artifacts exist and are the only versions in history
(`git log --oneline -- test/_shared/_merge_shaped_roster.py test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`
returns `ff11803b` alone). The suite runs green: **18 passed**.

Arm-by-arm:

- `test_merge_shaped_population_is_derived_nonempty_and_sized` (line 246) asserts `_MEMBERS` truthy
  **first**, then `== 8`, then 4-per-provider. This satisfies D3(c)'s non-emptiness-first obligation.
  CONFIRMED.
- `test_every_derived_member_has_an_offrouting_scenario` (line 277) catches a registered verb with no
  scenario. CONFIRMED — but only for a verb whose **name** is already in `MERGE_SHAPED_VERBS`
  (`_merge_shaped_roster.py:43`). A newly registered merge-shaped verb under a new name
  (`queue-merge`, `merge-train`, …) is filtered out by `merge_shaped_keys` before either test sees it,
  and the `verbs_by_provider == set(MERGE_SHAPED_VERBS)` assertion at line 270 only detects a member
  *disappearing*. The vocabulary is a hand-list — the same shape D0 was forbidden to produce — though
  it is inherited byte-for-byte from the first-instance guard (`test_branch_cleanup_merge_queue_routing.py:153`),
  so it is a residual rather than a regression. CONFIRMED.
- `test_offrouting_dispatch_is_refused_at_the_callee` (line 300) is genuine for 7 members. For
  `[gitlab:merge-queue]` it is not: `_dispatch` (line 234) sets `mt_post_ok = not (verb == 'merge-queue' and mode == 'off_routing')`
  and the stub returns `(1, '', 'HTTP 404: not found')`. The monkeypatched `_probe_merge_train_state`
  is never read by that handler. The assertion is `result.get('status') == 'error'` — and
  `ci_base.make_error` (line 777) returns `{'status': 'error', …}` on **every** failure branch, so
  the arm passes for any non-zero `run_glab` exit. It measures "a failed API call yields an error",
  not a callee-side guard. CONFIRMED.
- `test_compliant_route_succeeds` (line 336) is a real regression lock for the other 7; for
  `[gitlab:merge-queue]` it is the mirror tautology (POST stubbed to succeed → `enqueued: true`).

**The population size does not appear in a passing run's output.** It appears only inside the
`assert … , (f'…{size}…')` failure messages. `grep -rn "print("` over both new files returns nothing,
and `test/conftest.py` defines no `pytest_terminal_summary` / `pytest_report_header` hook. The actual
run output is `..................  [100%]` / `18 passed`. D3's *Done when* clause "the population size
appears in the test's own output" is therefore not literally satisfied — the parametrized node IDs
(`[github:merge]`, …) enumerate the members under `-v`, but no size is printed. CONFIRMED.

## Report-claim audit

`report-01.md` carries every section the lane contract required **at the time it landed**
(`git show ff11803b:.claude/skills/cloud-plan-lane/SKILL.md` § Report, lines 846-896: Skills loaded,
Deliverables, Build gate, Findings, Reviewer participation, Cost, Contract check, What have we
learned, Residue). The later-added `> **Verification loop exit:**` line and the stale-base
re-verification figure are **not** owed here — `git log -S'Verification loop exit'` and
`git log -S'rev-list --count HEAD..origin/main'` over the lane skill return `7d61d671` (#1297) and
`2cbcb1f3` (#1299), both after #1182.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Header `**Outcome:** _in progress_` | **FALSE / contract violation** | The contract at landing (`… SKILL.md:844`) admits exactly `completed \| partial \| blocked`. `git log --oneline -- <plan dir>` returns `ff11803b` alone, so this is the only version ever committed: the report was never finalized even though the work merged |
| 2 | § Build gate: *"No production source was changed by this plan"* | **FALSE** | `git show ff11803b --name-status` lists `M marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` (+12/−1). The report's own F3 describes making that change. The two statements contradict each other inside one document |
| 3 | § Build gate: the `*.py` footprint *"= two test files"* | **FALSE** | The landed diff's Python footprint is four files: the two new test files plus `gitlab_ops.py` and `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py` |
| 4 | § D1: *"the marshall-steward landing cycle uses `safe-merge`"* | **FALSE** | `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md:152-154` dispatches `ci pr merge-queue --head {branch}`; `git log -S` dates that to `27be6350`, an ancestor of `ff11803b` |
| 5 | § Residue / § D3: *"dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s off-routing test"* | **FALSE** | Removing the `if _is_auth_scope_error(...) or 'http 404' ...` block at `gitlab_ops.py:713` leaves `return make_error('pr_merge_queue', f'Failed to enqueue MR {iid} onto the merge train', stderr_text)` at line 720, and `make_error` (`ci_base.py:783`) always sets `status: 'error'`. The off-routing arm asserts only `status == 'error'`, so it stays green under that mutation. The structural falsifiability argument is not merely unmeasured — it is wrong |
| 6 | § D1: *"every D0 member refuses an off-routing dispatch"* | **OVERSTATED** | True for 7 of 8. `gitlab_ops.py:681-720` contains no queue/train state read; see D1 above |
| 7 | § D3: *"the population size (8) appears in the test's own output"* | **OVERSTATED** | It appears only in assertion failure messages; the passing run prints `18 passed` and nothing else |
| 8 | § D3 heading: *"tests, each verified to fail pre-fix by mutation"* | **OVERSTATED** | The body itself narrows this: 4 mutations over 16 behavioural parametrizations, and the 8 compliant-route tests are labelled a regression lock that "passes both pre- and post-mutation". The heading and the body disagree |
| 9 | § Contract check, Step 8: *"Landing recorded to the operator (see below)"* | **FALSE (dangling)** | No landing record appears anywhere below that row in the file |
| 10 | § D0: the 8-member population and the per-member guard table | **ACCURATE** | Both registries read; all eight handler bodies read; every guard named in the table exists at the line cited in § Deliverables above |
| 11 | § D3: the helper's regexes are *"byte-identical"* to the first-instance source-guard's | **ACCURATE** | `_merge_shaped_roster.py:54,57` and `test_branch_cleanup_merge_queue_routing.py:219,223` are character-for-character the same two patterns, with the same `re.DOTALL` |
| 12 | § D0: the near-miss quote at *"line 418"* | **ACCURATE** | `git show ff11803b:…/branch-cleanup.md \| grep -n "NOT symmetric"` → line 418 (441 today) |
| 13 | § D2: the two named locks | **ACCURATE** | `test_branch_cleanup_merge_queue_routing.py:946` and `:1034` |
| 14 | § Reviewer participation: the three `author_login` values derived from the registry docs | **ACCURATE** | `coderabbit.md:36` `coderabbitai`, `sourcery.md:29` `sourcery-ai`, `pr-agent.md:58` `cuioss-review-bot` |
| 15 | § F3: the fix is at the call site and `_MERGE_TRAIN_INELIGIBLE_HINT` is untouched | **ACCURATE** | The constant at `gitlab_ops.py:554-558` is unchanged and still used bare by `cmd_repo_merge_queue_enable` at line 813 |
| 16 | § Build gate: `./pw verify` → 19160 passed, 14 skipped | **UNVERIFIABLE** | Not re-run (out of scope). The two new test files pass on the current tree |
| 17 | § D3: the four mutation runs and their observed payloads | **UNVERIFIABLE** | Mutations were reverted; no artifact survives. Claim 5 shows at least the *structural* extrapolation beside them is wrong |

**The report's own completeness is a finding.** Beyond the unset `Outcome`, the closing sentence
*"The report is finalized as the last pre-merge commit; that push re-triggers the reviewers…"* describes
a commit that never happened: the plan directory has exactly one commit in its history. The run armed
auto-merge and never returned, so the reviewer verdicts stated for the final head are predictions
("their expected verdicts are unchanged"), not readings — which the contract's *"A claim is not an
outcome"* rule (§ Rules that outrank convenience) forbids.

## Correctness review

1. **`gitlab_ops.cmd_pr_merge_queue` has no callee-side off-routing guard** (`gitlab_ops.py:681-720`).
   The sibling probe `_probe_merge_train_state()` exists at line 567 and is called by
   `_refuse_on_required_merge_train` (line 633), `cmd_pr_auto_merge` (line 2118) and
   `cmd_repo_merge_queue_probe` (line 751) — but not here. The verb's refusal is delegated to the
   provider's HTTP status. CONFIRMED.

2. **The `[gitlab:merge-queue]` off-routing test cannot fail for the reason it claims.** Its refusal
   is manufactured by the stub (`test_merge_shaped_offrouting_refusal.py:158-171, 234`) and its
   assertion (`status == 'error'`, line 325) is satisfied by every `make_error` return in the handler.
   A guard could be deleted and the arm would stay green. CONFIRMED — this is the "test that would
   pass both before and after the fix" shape.

3. **The derivation's verb vocabulary is a hand-list** (`_merge_shaped_roster.py:43`). The module
   docstring is honest about it (*"This is the VOCABULARY the derivation filters against — not a
   membership claim"*), but the consequence is that "population-complete" means complete over four
   pre-named verbs. A fifth merge-shaped verb registered under a new name is invisible to both the new
   behavioural guard and the first-instance source guard. CONFIRMED.

4. **No defect found in the F3 message change itself.** `gitlab_ops.py:713-720` appends the remedy to
   the shared hint at the call site only, leaving `_MERGE_TRAIN_INELIGIBLE_HINT` and its second
   consumer (`cmd_repo_merge_queue_enable`, line 813) untouched — which is what the report says it
   did, and is correct: `repo merge-queue enable` is not a merge dispatch and `safe-merge` is not its
   alternative. CONFIRMED.

5. **No fail-open, idempotence, or None-handling defect found** in the paths this plan touched.
   `_resolve_base_queue_state` (`_github_pr.py:1211`) and `_refuse_on_required_merge_train`
   (`gitlab_ops.py:622-641`) both fail closed on probe error, as their docstrings claim, and the code
   matches. `_merge_shaped_roster._handler_map_body` raises `AssertionError` rather than returning an
   empty body on a registry-regex miss (lines 67-73) — the correct choice for a population source.

## Completeness review

1. **Two doc consumers of the changed refusal were not updated.** The GitHub sibling's remedy is
   spelled out in prose; the GitLab one is not, even though the code now carries it:
   - `tools-integration-ci/standards/pr-operations.md` § "The enqueue is corroborated", GitHub bullet:
     *"On any other eligibility value it returns `status: error` naming both remedies — run
     `/marshall-steward` → Configuration → Merge Queue to provision the queue, or disable the plan's
     `use_merge_queue` step param to merge immediately via `ci pr safe-merge`."* The GitLab bullet
     directly beneath it says only *"a failure surfaces as the actionable ineligible error"*.
   - `pr-operations.md:378`: *"the invocation returns `status: error, operation: pr_merge_queue` with
     the actionable ineligible message"* — no mention of the routed alternative.
   - `tools-integration-ci/standards/gitlab-impl.md:120-127`: *"its 403/404 is the refusal … The
     actionable-ineligible contract itself is cross-provider"* — no mention of the routed alternative.

   CONFIRMED by reading all three, found via
   `grep -rn "pr safe-merge|pr merge-queue|pr auto-merge|ci pr merge" marketplace/bundles/ --include=*.md -l`.

2. **The lock on the new message covers one of the two entry conditions.** The `safe-merge` assertion
   was added to `test_cmd_pr_merge_queue_ineligible_on_403` only
   (`test_gitlab_merge_queue.py:66-85`); `test_cmd_pr_merge_queue_ineligible_on_404` (line 88) asserts
   nothing about the message. Both reach the same branch, so this is a coverage asymmetry rather than
   a hole — but the 404 condition is the one the plan's own scenario model treats as the off-routing
   signature.

3. **The shared helper has exactly one consumer.** `grep -rn "_merge_shaped_roster"` over `*.py` and
   `*.md` finds `test_merge_shaped_offrouting_refusal.py:71` and prose references only. The
   first-instance guard still carries `_registry_keys` / `_registry_handler_names` /
   `_merge_shaped_registry_keys` (`test_branch_cleanup_merge_queue_routing.py:476, 496, 511`). The
   "single-source" discipline the helper's docstring names is not yet realised anywhere.

4. **`ci_base.dispatch` is uninstrumented** (`ci_base.py:1978`). The plan named `ci.py` / `ci_base.py`
   as the router in its Expected surface; D2's record-a-departure obligation could have been
   discharged there for every verb at once and was not.

## Out-of-scope compliance

Compliant on all four exclusions. CONFIRMED against `git show ff11803b --name-status`:

- **Strengthening the prose** — `branch-cleanup.md` is untouched by this commit.
- **Treating "the caller is documented to route correctly" as a guarantee** — the remedy shipped is a
  test bound to a derived population plus a callee-side message, not a caller-side rule.
- **Answering why the executor left the routing** — no explanation is offered anywhere in
  `report-01.md`; the run did not manufacture one.
- **Expanding into non-CI verb sets** — the diff touches only the CI abstraction and its tests.

The one production edit (`gitlab_ops.py`) is not a scope breach: it is the direct product of the
plan's own § Verification cold-read mandate, and it changes a callee-side message rather than the
routing prose.

## Residue status

| Residue item recorded in `report-01.md` | Status |
|---|---|
| Source-guard consolidation onto the shared roster helper (F1 follow-up) | **Still open.** `test_branch_cleanup_merge_queue_routing.py:476/496/511` still define their own derivation; nothing imports `_merge_shaped_roster` except the new behavioural suite. `git log --oneline -- test/_shared/_merge_shaped_roster.py` shows no later commit |
| GitLab `merge-queue` off-routing falsifiability is argued, not mutation-measured | **Still open, and the argument is refuted.** See report-claim 5: the named mutation would not flip the test, because the fallback `make_error` keeps `status: error` |

## Summary

**Counts by severity:** 2 blockers (G1, G2), 4 major (G3–G6), 5 minor (G7–G11) — see `gaps.md` for the
actionable form. Three of the eleven are confirmed false report claims (G3, G4, G5).

Bottom line: the plan's substance largely landed and is real — D0's 8-member derivation is
reproducible from the tree, seven of the eight members carry a genuine callee-side check, the two new
test files exist and run green, and the cold-read message fix is correct and locked. But D1's *Done
when* fails on both halves: `gitlab:merge-queue` has no callee-side state check at all (the one member
where the plan's own part-(c) asymmetry survives inside the population it derived), and the published
caller enumeration misnames the marshall-steward landing cycle's verb — the very caller that
unconditionally dispatches a merge-shaped verb outside any route. The test arm that was supposed to
cover that member cannot fail for the reason it claims, and the report's structural argument that it
could is demonstrably wrong. Compounding this, `report-01.md` was never finalized (`Outcome: _in
progress_`), and its Build-gate section asserts "No production source was changed by this plan" in
direct contradiction of the diff it shipped with and of its own F3 finding.
