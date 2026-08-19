# Verification — 060-a-prose-routing-table-is-not-an-enforcement-boundary

**Landed as:** PR #1182, squash commit `ff11803b`
**Verdict:** partially-implemented

## Method

Read in full: `plan.md`, `report-01.md`, and the landed diff (`git show --stat ff11803b`,
`git show ff11803b -- <path>` for each of the four non-plan paths).

Ground truth taken from the working tree of branch `claude/review-apparatus-analysis-mcf8md`
(`500d8061`). Read in the current tree:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  (`_resolve_base_queue_state`, `_refuse_on_required_merge_queue`, `cmd_pr_merge`,
  `cmd_pr_auto_merge`, `cmd_pr_safe_merge`, `cmd_pr_merge_queue`, `_safe_merge_delegate_ns`)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
  (`handlers: HandlerMap` registry, `_probe_merge_queue_state`)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`
  (`handlers: HandlerMap`, `_probe_merge_train_state`, `_refuse_on_required_merge_train`,
  `_corroborate_merge`, `cmd_pr_merge_queue`, `cmd_pr_merge`, `cmd_pr_auto_merge`,
  `cmd_pr_safe_merge`, `cmd_branch_delete`)
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
  (`dispatch`, `make_error`, the `pr merge` / `pr auto-merge` / `pr safe-merge` / `pr merge-queue`
  parsers)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (§ "Merge routing (`use_merge_queue`)", § "The dispatch set is CLOSED", every
  `**Observability (mandatory)**` block, § "Rebase Branch onto Base", § post-merge cleanup)
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
- The caller enumeration, which needs **two** searches because one alone is incomplete:
  `grep -rn "tools-integration-ci:ci pr merge-queue\|…safe-merge\|…auto-merge\|…pr merge" marketplace/bundles/ .claude/`
  finds every dispatch line whose script token is adjacent to the noun, and
  `grep -n "execute-script.py plan-marshall:tools-integration-ci" …/branch-cleanup.md` finds the two
  that interpose `--project-dir {worktree_path}` and which the first search therefore misses. Each hit
  was read in context. `grep -rn "pr merge-queue\|pr safe-merge\|pr auto-merge" --include=*.py marketplace/ .claude/`
  covers the Python and project-local surfaces.
- `grep -rln "_MERGE_TRAIN_INELIGIBLE_HINT" .` — every copy of the changed message constant (one
  definition, two consumers, plus one comment mention in a test).
- `grep -rn "print(" ` over the two new test files, and
  `grep -rn "pytest_terminal_summary\|pytest_report_header" test/` — whether the population size
  reaches a passing run's output. Both return nothing.
- `grep -rlnE "ci branch delete|ci pr close|branch delete " marketplace/bundles/…/skills --include=*.md`,
  `grep -n "execute-script.py plan-marshall:tools-integration-ci" …/branch-cleanup.md`, and
  `grep -n "force-push\|'push'" workflow-integration-git/scripts/*.py` — a second four-part routed
  verb set with a destructive member, inside and outside the CI abstraction.
- `grep -n "_probe_merge_train_state" …/gitlab_ops.py` and
  `grep -n "Could not determine project path\|if not owner or not repo:"` over both provider modules
  — every call site of the GitLab probe, and the scope-resolution failure handling on both providers.
- `git log --oneline -- <path>` for each landed path, `git rev-list --parents -n 1 ff11803b`
  (merge shape), `git merge-base --is-ancestor` for each cited commit, and
  `git log --oneline -S'<symbol>' -- <path>` for `ci pr merge-queue` in `landing-cycle.md`,
  `Verification loop exit` and `rev-list --count HEAD..origin/main` in the lane skill.

Executed:

- `uv run python -m pytest … -o addopts="" -q` on the three suites in scope:
  `test_merge_shaped_offrouting_refusal.py` → **18 passed**,
  `test_branch_cleanup_merge_queue_routing.py` → **23 passed**,
  `test_gitlab_merge_queue.py` → **16 passed**.
- Source mutations, each applied from a byte snapshot and restored from that snapshot
  (never `git checkout`), with `git status --porcelain` re-checked clean afterwards. Their results
  are reported inline below.
- A dispatch probe over all 8 members × both modes, printing each result envelope and the CLI calls
  each handler actually issued.
- A scope-failure probe of the GitLab merge-train preflight (`get_project_path` stubbed empty,
  `run_api` stubbed to raise if reached), reported inline under § Correctness review item 5.

GitHub surfaces for PR #1182 were read through the GitHub MCP server (`get`, `get_reviews`,
`get_comments`, `get_check_runs`, `get_commits`), because two report claims are about those surfaces
and cannot be settled from a clone.

No repository file was modified other than this file and `gaps.md`. No full build was run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | The population is derived and published with its size and its derivation method, or the null result is stated with the same evidence | 8 members = 4 verbs × 2 providers, derived from each `handlers: HandlerMap` literal; null result published; CI-wait route recorded as a near-miss | Both registries carry exactly `('pr','merge')`, `('pr','auto-merge')`, `('pr','safe-merge')`, `('pr','merge-queue')`; the near-miss quote is verbatim at `branch-cleanup.md:418` as of `ff11803b` | **Met** |
| D1 | Every D0 member refuses an off-routing dispatch, and the caller enumeration is published alongside — including any sanctioned exception found and how it is preserved | All 8 already guarded; `auto-merge` is the sanctioned exception; caller enumeration published | All 8 do return `status: error` (or the sanctioned `disposition`) off-routing, but 7 reach that verdict from a callee-side state read while `gitlab:merge-queue` delegates it to the provider's HTTP status **after** issuing the POST. The GitLab preflight the other two GitLab members share additionally fails **open** on an unresolvable project scope. The published caller enumeration misnames the marshall-steward caller's verb | **Partially met** |
| D2 | A departure from a documented route emits a record naming the route, the expected branch, and the verb actually dispatched | Already instrumented at all `use_merge_queue` sites; the callee refusal is the departure record; nothing new to instrument | Every `**Observability (mandatory)**` block exists and is paired with a consumption site; the refusals name the routed verb. But an off-routing `pr auto-merge` emits **no** departure record — it succeeds naming the branch and the disposition, never the route — and neither GitLab refusal names the scope it applies to | **Partially met** |
| D3 | All three arms hold and the population size appears in the test's own output | 18 tests; non-emptiness first; size 8 published; every member covered; falsifiability measured by four mutations | The two files exist and 18 tests pass. The size appears only inside assertion **failure** messages — a passing run prints nothing. One arm (`[gitlab:merge-queue]` off-routing) is stub-manufactured and asserts only `status == 'error'`. A merge-shaped verb registered under a new name is invisible to both population guards | **Partially met** |

### D0 — derive the population of prose-routed verb sets

**Met, and independently reproduced.** `github_ops.py:1876-1879` registers `('pr','merge'): cmd_pr_merge`,
`('pr','auto-merge'): cmd_pr_auto_merge`, `('pr','safe-merge'): cmd_pr_safe_merge`,
`('pr','merge-queue'): cmd_pr_merge_queue`; `gitlab_ops.py:2569-2572` registers the same four. The
derived population is 8. CONFIRMED.

The report's per-member guard table is accurate against the tree for all eight rows, including its
honest entry for GitLab `merge-queue` — *"merge-train POST; refuses (error) on 404/ineligible"*, which
correctly does **not** claim a probe.

The published null result — the merge routing is the only full four-part prose-routed verb set — was
not disproved. Four candidate second instances were checked and rejected:

- `branch-cleanup-rereview.md:3` — the only other closed-set statement; it explicitly inherits the
  merge routing's own set rather than defining a new one.
- The post-merge cleanup route (`branch-cleanup.md:1539-1545`) is keyed on the same `use_merge_queue`
  flag and its destructive sibling `('branch','delete')` is registered on both providers — but the
  route selects between two *descriptions of who already deleted the branch* and then dispatches a
  single `workflow-integration-git` verb on both branches, so part (a) ("a documented multi-branch
  route" between CI verbs) fails.
- The **pre-merge rebase route** (`branch-cleanup.md:357-408`, § "Rebase Branch onto Base") is the
  strongest candidate outside the CI abstraction: keyed on the same `use_merge_queue` flag, it is a
  documented two-branch route whose `false` branch dispatches `force-push-with-lease` — a genuinely
  destructive, irreversible remote history rewrite — so it satisfies (a) and (d) where the CI-wait
  near-miss below fails (d). It is rejected on (b) and (c): `git-workflow` registers **no** unguarded
  force-push sibling (`grep -n "force-push\|'push'"` over
  `workflow-integration-git/scripts/*.py` finds `force-push-with-lease` as the sole such verb,
  registered once at `git-workflow.py:2030`), and that one verb carries its own callee-side refusal —
  `_cmd_force_push.py:176-183` returns `status: error, message: 'refusing to force-push to base
  branch'` when the branch is `main`/`master`. With no reachable-outside sibling there is no checking
  asymmetry to exploit, so the shape does not close. This also independently supports the plan's
  *Out of scope* bar on expanding into non-CI verb sets: the one non-CI route that carries a
  destructive member is already guarded at its callee.
- `grep -rlnE "ci branch delete|ci pr close|branch delete "` over the bundle's `*.md` returns five
  files (`workflow-integration-github/SKILL.md`, `persona-plan-marshall-agent/standards/argument-naming.md`,
  `tools-integration-ci/SKILL.md`, `tools-integration-ci/standards/pr-operations.md`,
  `phase-6-finalize/standards/branch-cleanup.md`), each read: none carries a second multi-branch
  route selecting between CI verbs with a destructive member.

PLAUSIBLE (a null result cannot be positively confirmed, but the searches that would have refuted it
came back empty).

The recorded near-miss is real: `branch-cleanup.md` § "Rebase Branch onto Base" / "CI gate before the
merge" routes `ci checks status` against `ci checks wait --adaptive` on the same `use_merge_queue`
flag, and the cited sentence *"the two paths are NOT symmetric"* is at line 418 in the file as it
stood at `ff11803b` (line 441 today). Both members are read-only, so part (d) genuinely fails.
CONFIRMED.

### D1 — callee-side refusal for every member

**Partially met.** Seven of eight members reach their off-routing verdict from a callee-side state
read — five by refusing on it, two (the sanctioned `auto-merge` pair) by reporting the disposition it
implies:

- `_github_pr.py:1467` — `cmd_pr_merge` calls `_refuse_on_required_merge_queue`, which at
  `_github_pr.py:1278-1286` refuses when `discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED`.
- `_github_pr.py:1687` — `cmd_pr_safe_merge` calls the same preflight before polling.
- `_github_pr.py:1894-1903` — `cmd_pr_merge_queue` refuses when `discriminator != MERGE_QUEUE_ELIGIBLE_CONFIGURED`.
- `_github_pr.py:1627` — `cmd_pr_auto_merge` probes via `_resolve_base_queue_state` and reports
  `disposition`.
- `gitlab_ops.py:1955` — `cmd_pr_merge` calls `_refuse_on_required_merge_train` (`gitlab_ops.py:622`,
  which probes at line 633 and refuses at lines 636-643).
- `gitlab_ops.py:2202` — `cmd_pr_safe_merge` calls the same preflight.
- `gitlab_ops.py:2118` — `cmd_pr_auto_merge` calls `_probe_merge_train_state` and reports `disposition`.

**The eighth, `gitlab:merge-queue`, reads no queue/train state.** `gitlab_ops.py:681-720`
(`cmd_pr_merge_queue`) goes straight from `_resolve_mr_iid` and `get_project_path` to
`run_glab(['api', '-X', 'POST', endpoint])`; `_probe_merge_train_state()` — which exists at
`gitlab_ops.py:567` and is called at lines 633, 751, 776 and 2118 — is not called here. The refusal
is whatever the provider returns:

```python
    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint])
    if returncode != 0:
        stderr_text = stderr.strip()
        if _is_auth_scope_error(stderr_text) or 'http 404' in stderr_text.lower():
```

CONFIRMED (the absence of the call), and MEASURED by a probe that dispatches every member in both
modes and records the CLI calls each handler issued. Stated exactly, because the arithmetic matters:

| Off-routing outcome | Members | CLI issued before the verdict |
|---|---|---|
| `status: error` from a callee-side state read | 5 — `github:merge`, `github:safe-merge`, `github:merge-queue`, `gitlab:merge`, `gitlab:safe-merge` | none (`captured == []`) |
| `status: error` from the provider's HTTP status | 1 — `gitlab:merge-queue` | `['api', '-X', 'POST', 'projects/octo%2Frepo/merge_trains/merge_requests/42']` |
| `status: success`, `disposition: enqueued` (the sanctioned exception) | 2 — `github:auto-merge`, `gitlab:auto-merge` | the scheduling call (`gh pr merge --auto --merge` / `glab mr merge --when-pipeline-succeeds`) |

So **six** members refuse off-routing, not eight, and five of those six refuse with no CLI call at
all. `gitlab:merge-queue` issues the identical POST in **both** the off-routing and the compliant run
— the two differ only in what the stub returns — so its refusal lands *after* the side-effecting
call, whereas the GitHub sibling's docstring makes the pre-call ordering explicit precisely to keep
"the failure path free of side effects". The two `auto-merge` members do not refuse at all and are not
counted as refusals here; that is the sanctioned exception, not a shortfall.

**This asymmetry is documented as deliberate, and that is what bounds it.**
`pr-operations.md:55` states *"**GitLab**: **no probe** — the POST to the dedicated merge-train
endpoint is itself the corroboration (it succeeds only against a real train), and its HTTP 403/404 is
the refusal"*, and `gitlab-impl.md:120-127` gives the same rationale. So this is a design choice with
a stated basis, not an omission — but the basis is an unverified assumption about provider behaviour,
which is the exact assumption class the plan exists to remove. The concrete exposure is on the success
side rather than the refusal side: `gitlab_ops.py:722-738` derives `enqueued: True` from
`returncode == 0` alone and swallows a `json.JSONDecodeError` on the car read-back, so any 2xx — from
a project where `_probe_merge_train_state()` would return `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED` — yields
`enqueued: true` with an empty `merge_train_car_id`. Its GitHub sibling publishes
`enqueue_corroboration` from a probe verdict instead. The 2xx-on-unconfigured case is PLAUSIBLE, not
confirmed: nobody in this repository has measured it.

**The published caller enumeration is wrong.** The report states *"the marshall-steward landing cycle
uses `safe-merge`"*. `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md:152-154`
dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
  --head {branch}
```

unconditionally, with no `use_merge_queue` routing and no fallback (§ "Step 5: … merge via the queue",
sub-step (c): *"**(c) Merge via the platform merge queue** — WITHOUT `--delete-branch`"*).
`git log --oneline -S'ci pr merge-queue' -- <that file>` returns only `27be6350`, which
`git merge-base --is-ancestor 27be6350 ff11803b` confirms is an ancestor of `ff11803b`, so this was
already true when the plan ran. CONFIRMED.

That matters beyond bookkeeping: this is a sanctioned caller that dispatches a merge-shaped verb
against a base whose queue state it never checks, and on a repository with no configured queue it is
refused by the GitHub callee (`_github_pr.py:1894`) with no documented remedy path. The plan's UNKNOWN
claim — *"some legitimate caller depends on reaching a D0 member outside its route"* — was resolved
"in the negative" on an enumeration that missed this caller.

Re-derived independently, and the search matters: a contiguous
`grep -rn "tools-integration-ci:ci pr merge-queue\|…safe-merge\|…auto-merge\|…pr merge"` over
`marketplace/bundles/` and `.claude/` returns **seven** dispatch lines but **misses
`branch-cleanup.md`'s own two**, because those interpose `--project-dir {worktree_path}` between the
script token and the noun. The enumeration that actually closes is the union of that search with
`grep -n "execute-script.py plan-marshall:tools-integration-ci" branch-cleanup.md`, which yields
`branch-cleanup.md:1299` (`pr merge-queue`) and `:1321` (`pr safe-merge`). The complete result: the
only documented dispatch lines of a merge-shaped `ci pr` verb outside the reference /
canonical-invocation docs (`tools-integration-ci/SKILL.md:320,330`, `pr-operations.md:199,247,312,359`,
and the argument-shape table at `persona-plan-marshall-agent/standards/argument-naming.md:166`) are
`branch-cleanup.md`'s routed pair and `landing-cycle.md:153`. No Python or project-local surface
dispatches one: `grep -rn "pr merge-queue\|pr safe-merge\|pr auto-merge" --include=*.py marketplace/ .claude/`
returns only a comment in `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:450`.

### D2 — observability at the routing decision

**Partially met.** Every `**Observability (mandatory)**` block is present in `branch-cleanup.md`
(lines 360, 416, 614, 1269, 1541) and each is paired with a `use_merge_queue` consumption site — a
probe of the pairing `test_every_use_merge_queue_consumption_site_is_observable` performs returns 5
reads and 5 markers, injectively paired. The report says "all four `use_merge_queue` sites", which was
correct at landing: the same probe against `git show ff11803b:…/branch-cleanup.md` returns 4 reads and
4 markers. A later plan added the fifth site with its block. The two named locks exist:
`test_every_use_merge_queue_consumption_site_is_observable` (`test_branch_cleanup_merge_queue_routing.py:946`)
and `test_merge_routing_decision_precedes_the_dispatch_it_selects` (line 1034). CONFIRMED.

The refusal messages do name the route: `_github_pr.py:1281-1284` names the base branch and
`"ci pr merge-queue"`; `_github_pr.py:1897-1901` names the base branch and `"ci pr safe-merge"`;
`gitlab_ops.py:639-641` names `"ci pr merge-queue"`; `gitlab_ops.py:715-717` now names
`"ci pr safe-merge"`. A cold read of all four leads a reader to a correct next verb.

**One element of the *Done when* is missing on GitLab: the expected scope.** D2 requires the record to
name "the route, the expected branch, and the verb actually dispatched". The two GitHub refusals name
the base branch; **neither GitLab refusal names any scope at all**. `gitlab_ops.py:639-641` says
*"This project has merge trains enabled"* with no project identity, and its `detail` argument is the
probe's `'merge_trains_enabled=true'` (`gitlab_ops.py:598`), which carries none either;
`gitlab_ops.py:715-717` inherits `_MERGE_TRAIN_INELIGIBLE_HINT` (`:554-558`), whose *"This project is
not eligible"* is likewise anonymous — only the un-routed fallback at `:720` names the MR (`f'Failed
to enqueue MR {iid} …'`). That a GitLab merge train is project-scoped rather than branch-scoped is
real and documented (`gitlab_ops.py:610-616`), so "the expected branch" has no GitLab analogue — but
the *project path* is resolved in both paths (`get_project_path()`) and is simply not put in the
record. CONFIRMED by reading all four messages and the probe's return values.

The larger gap is the **sanctioned exception**. An off-routing `ci pr auto-merge` — a verb
`branch-cleanup.md:1265` marks **never** reachable from the routed step — returns `status: success`
with `disposition: enqueued`, naming the base branch and the operation dispatched but no route.
`ci_base.py:1978-2032` (`dispatch`) carries no logging either, so the router — named in the plan's
Expected surface as *"the router that performs the dispatch"* — records nothing. D2's *Done when*
("a departure from a documented route emits a record naming the route, the expected branch, and the
verb actually dispatched") therefore does not hold on the one path the plan explicitly declined to
make refuse. CONFIRMED.

### D3 — tests

**Partially met.** Both artifacts exist and are the only versions in history
(`git log --oneline -- test/_shared/_merge_shaped_roster.py test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`
returns `ff11803b` alone). The suite runs green: **18 passed** (2 population arms + 8 + 8
parametrizations).

Arm-by-arm:

- `test_merge_shaped_population_is_derived_nonempty_and_sized` (line 246) asserts `_MEMBERS` truthy
  **first**, then `== 8`, then 4-per-provider. This satisfies D3(c)'s non-emptiness-first obligation.
  CONFIRMED.
- `test_every_derived_member_has_an_offrouting_scenario` (line 277) cannot do what the report claims
  for it. MEASURED: injecting `('pr','queue-merge'): cmd_pr_merge_queue` into the GitHub registry
  literal leaves **both** population guards green (41 passed across the two files). `merge_shaped_keys`
  (`_merge_shaped_roster.py:97-107`) filters registry keys by `key[1] in MERGE_SHAPED_VERBS`
  (`_merge_shaped_roster.py:43`), so a merge-shaped verb under a new name never enters `_MEMBERS`; the
  `verbs_by_provider == set(MERGE_SHAPED_VERBS)` assertion at line 270 detects a member *disappearing*,
  never one appearing. The test guards the vocabulary-to-scenario coupling only. The vocabulary is a
  hand-list — the same shape D0 was forbidden to produce — inherited byte-for-byte from the
  first-instance guard (`test_branch_cleanup_merge_queue_routing.py:153`), so the hand-list itself is a
  residual rather than a regression; the report's capability claim about it is not.
- `test_offrouting_dispatch_is_refused_at_the_callee` (lines 300-328) is genuine for 7 members. For
  `[gitlab:merge-queue]` it is not: `_dispatch` (line 206) sets
  `mt_post_ok = not (verb == 'merge-queue' and mode == 'off_routing')` at line 234 and the stub
  (lines 158-171) returns `(1, '', 'HTTP 404: not found')`. The monkeypatched `_probe_merge_train_state`
  is never read by that handler. The assertion (line 325) is `result.get('status') == 'error'` — and
  `ci_base.make_error` (`ci_base.py:777`, setting `status: 'error'` at line 783) returns that on
  **every** failure branch, so the arm passes for any non-zero `run_glab` exit. It measures "a failed
  API call yields an error", not a callee-side guard. CONFIRMED, and MEASURED below.
- `test_compliant_route_succeeds` (lines 336-357) is a real regression lock for the other 7; for
  `[gitlab:merge-queue]` it is the mirror tautology (POST stubbed to succeed → `enqueued: true`), and
  the probe confirms both modes issue the identical POST.

**The population size does not appear in a passing run's output.** It appears only inside the
`assert … , (f'…{size}…')` failure messages. `grep -rn "print("` over both new files returns nothing,
and `grep -rln "pytest_terminal_summary|pytest_report_header" test/` returns nothing, so no conftest
supplies one. The observed output of a green run is `..................  [100%]` / `18 passed`. D3's
*Done when* clause "the population size appears in the test's own output" is therefore not literally
satisfied — the parametrized node IDs (`[github:merge]`, …) enumerate the members under `-v`, but no
size is printed. CONFIRMED.

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
| 1 | Header `**Outcome:** _in progress_` | **FALSE / contract violation** | The contract at landing (`… SKILL.md:844`) admits exactly `completed \| partial \| blocked`. The landed file carries `_in progress_`, so the field was never set to a legal value before the merge. (Per-file history is no evidence either way here: `git rev-list --parents -n 1 ff11803b` shows one parent, so the PR was squashed and every path it touched necessarily lands in exactly one commit) |
| 2 | § Build gate: *"No production source was changed by this plan"* | **FALSE** | `git show ff11803b --name-status` lists `M marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`; `--numstat` gives it as **+11/−1**. The report's own F3 describes making that change. The two statements contradict each other inside one document |
| 3 | § Build gate: the `*.py` footprint *"= two test files"* | **FALSE** | The landed diff's Python footprint is four files: the two new test files (`_merge_shaped_roster.py` +128, `test_merge_shaped_offrouting_refusal.py` +357) plus `gitlab_ops.py` (+11/−1) and `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py` (+4) |
| 4 | § D1: *"the marshall-steward landing cycle uses `safe-merge`"* | **FALSE** | `landing-cycle.md:152-154` dispatches `ci pr merge-queue --head {branch}`; `git log -S` dates that to `27be6350`, an ancestor of `ff11803b` |
| 5 | § Residue / § D3: *"dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s off-routing test"* | **FALSE, measured** | Deleting the `if _is_auth_scope_error(…) or 'http 404' …:` block (`gitlab_ops.py:708-719`) leaves `return make_error('pr_merge_queue', f'Failed to enqueue MR {iid} onto the merge train', stderr_text)` at line 720, and `make_error` always sets `status: 'error'`. Run under that mutant, `test_merge_shaped_offrouting_refusal.py` reports **18 passed**. The structural falsifiability argument is not merely unmeasured — it is wrong. (The mutation is not invisible tree-wide: it turns `test_gitlab_merge_queue.py::test_cmd_pr_merge_queue_ineligible_on_403` red on its `'safe-merge' in message` assertion, while the 404 sibling stays green) |
| 6 | § D3: *"a new merge-shaped verb added to a registry without an off-routing scenario fails `test_every_derived_member_has_an_offrouting_scenario` rather than being silently skipped"* | **FALSE, measured** | Injecting `('pr','queue-merge'): cmd_pr_merge_queue` into `github_ops.py`'s registry literal leaves both population guards green (41 passed). The verb is filtered out by `merge_shaped_keys` before either test sees it |
| 7 | § Reviewer participation: `sourcery-ai` = *"`silent` … no review artifact and no notice was published"* | **FALSE** | The PR's **reviews** surface carries a `sourcery-ai[bot]` review (`state: COMMENTED`, id 4915308445) whose entire body is a refusal notice: *"you have reached your weekly rate limit of 500000 diff characters"*. The check-run half of the claim is accurate — `Sourcery review` concluded `skipped` — but the bot was **rate-limited and said so**, not silent. The report describes reading "both comment surfaces (conversation or inline review threads)"; the PR-level reviews surface is a third one, and it was missed. The 1-of-3 coverage figure is unaffected (a refusal is not a review); what is wrong is the cause stated to the operator — the § Step 8 disclosure reads *"`sourcery-ai` skipped/silent"* where the observable cause is a rate limit, which reopens, unlike a skip |
| 8 | § D1: *"every D0 member refuses an off-routing dispatch"* | **OVERSTATED** | All 8 do return an error (or the sanctioned disposition) under the suite's stubs, but 7 do so from a callee-side state read with no CLI call, while `gitlab:merge-queue` issues the POST and reads the provider's status; see D1 above |
| 9 | § D3: *"the population size (8) appears in the test's own output"* | **OVERSTATED** | It appears only in assertion failure messages; the passing run prints `18 passed` and nothing else |
| 10 | § D3 heading: *"tests, each verified to fail pre-fix by mutation"* | **OVERSTATED** | The body itself narrows this: 4 mutations over 16 behavioural parametrizations, and the 8 compliant-route tests are labelled a regression lock that "passes both pre- and post-mutation". The heading and the body disagree |
| 11 | § Contract check, Step 8: *"Landing recorded to the operator (see below)"* | **FALSE (dangling)** | No landing record appears anywhere below that row in the file — the sections after it are the GitHub-access/branch-form note, "What have we learned" and "Residue" |
| 12 | § D0: the 8-member population and the per-member guard table | **ACCURATE** | Both registries read; all eight handler bodies read; every guard named in the table exists at the line cited in § D1 above |
| 13 | § D3: the helper's regexes are *"byte-identical"* to the first-instance source-guard's | **ACCURATE** | `_merge_shaped_roster.py:54,57` and `test_branch_cleanup_merge_queue_routing.py:219,222` are character-for-character the same two patterns, with the same `re.DOTALL` |
| 14 | § D0: the near-miss quote at *"line 418"* | **ACCURATE** | `git show ff11803b:…/branch-cleanup.md \| grep -n "NOT symmetric"` → line 418 (441 today) |
| 15 | § D2: the two named locks | **ACCURATE** | `test_branch_cleanup_merge_queue_routing.py:946` and `:1034` |
| 16 | § Reviewer participation: the three `author_login` values derived from the registry docs | **ACCURATE** | `coderabbit.md:36` `coderabbitai`, `sourcery.md:29` `sourcery-ai`, `pr-agent.md:58` `cuioss-review-bot`. The `cuioss-review-bot` verdict and its quoted body are accurate against the PR's conversation surface, and `coderabbitai`'s rate-limit notice is real |
| 17 | § F3: the fix is at the call site and `_MERGE_TRAIN_INELIGIBLE_HINT` is untouched | **ACCURATE** | The constant at `gitlab_ops.py:554-558` is unchanged and still used bare by `cmd_repo_merge_queue_enable` at line 813 |
| 18 | § Build gate: `./pw verify` → 19160 passed, 14 skipped | **UNVERIFIABLE** | Not re-run (out of scope). The three suites this plan touches pass on the current tree |
| 19 | § D3: the four mutation runs and their observed payloads | **UNVERIFIABLE** | Mutations were reverted; no artifact survives. Claim 5 shows the *structural* extrapolation beside them is wrong, but says nothing about the four measured runs themselves |

**On the report's own completeness.** Beyond the unset `Outcome`, the report's closing sentence
*"The report is finalized as the last pre-merge commit; that push re-triggers the reviewers…"*
describes a commit that **does** exist: the PR's commit list ends with
`0a77146e` *"docs(review-apparatus): finalize run report (reviewer participation, cost, contract
check, learnings) … The last pre-merge commit."* What that commit did not do is set the `Outcome`
header. The remaining defect is narrower than "the finalization never happened": the reviewer verdicts
stated for the head that commit created are **predictions** ("their expected verdicts are unchanged"),
not readings, which the contract's *"A claim is not an outcome"* rule (§ Rules that outrank
convenience) forbids. Read after the fact, `Sourcery review` was indeed `skipped` on that head, and
`cuioss-review-bot` did **not** re-review it (its guide comment predates that push and was never
updated).

One figure reconciles rather than refutes: the report quotes CodeRabbit's notice as *"Next review
available in: 35 minutes"* while the stored comment now reads 25 minutes. That comment carries a later
`updated_at` than the report's finalize commit, so the bot revised its own notice; the report's quote
is consistent with the earlier revision and is not treated as a misquote.

## Correctness review

1. **`gitlab_ops.cmd_pr_merge_queue` reads no queue/train state** (`gitlab_ops.py:681-720`). The
   sibling probe `_probe_merge_train_state()` exists at line 567 and is called by
   `_refuse_on_required_merge_train` (line 633), `cmd_repo_merge_queue_probe` (line 751),
   `cmd_repo_merge_queue_enable` (line 776) and `cmd_pr_auto_merge` (line 2118) — but not here. The
   verb's refusal is delegated to the provider's HTTP status, by a rationale documented at
   `pr-operations.md:55` and `gitlab-impl.md:120-127`. CONFIRMED; the residual exposure is the
   `returncode == 0` → `enqueued: true` success path (`gitlab_ops.py:722-738`), not the refusal path.

2. **The `[gitlab:merge-queue]` off-routing test cannot fail for the reason it claims.** Its refusal
   is manufactured by the stub (`test_merge_shaped_offrouting_refusal.py:158-171, 234`) and its
   assertion (`status == 'error'`, line 325) is satisfied by every `make_error` return in the handler.
   MEASURED: with the ineligible branch deleted the whole file still reports 18 passed. This is the
   "test that would pass both before and after the fix" shape.

3. **The derivation's verb vocabulary is a hand-list** (`_merge_shaped_roster.py:43`). The module
   docstring is honest about it (*"This is the VOCABULARY the derivation filters against — not a
   membership claim"*), but the consequence, measured by the `queue-merge` injection above, is that
   "population-complete" means complete over four pre-named verbs on both population guards at once.

4. **No defect found in the F3 message change itself.** `gitlab_ops.py:708-720` appends the remedy to
   the shared hint at the call site only, leaving `_MERGE_TRAIN_INELIGIBLE_HINT` and its second
   consumer (`cmd_repo_merge_queue_enable`, line 813) untouched — which is what the report says it
   did, and is correct: `repo merge-queue enable` is not a merge dispatch and `safe-merge` is not its
   alternative. CONFIRMED.

5. **The GitLab merge-train preflight FAILS OPEN on an unresolvable project scope**, contrary to its
   own docstring. `_refuse_on_required_merge_train` (`gitlab_ops.py:622-646`) claims at lines 624-626:
   *"Fails closed: a probe error (auth scope, transient API failure, malformed project response)
   refuses the merge rather than merging blind, exactly as its GitHub sibling does."* Those three
   cases do fail closed — the probe returns a non-`None` third element and the preflight converts it
   to an error. A **fourth** case is not among them: `_probe_merge_train_state` at `gitlab_ops.py:583`
   returns `(MERGE_QUEUE_INELIGIBLE, 'could not determine project path', None)` when
   `get_project_path()` is empty. `None` means "no error", `ineligible` means "the feature is absent",
   so the preflight falls through to `return None` and **permits the immediate merge** — a scope
   *resolution* failure folded into a feature *availability* verdict.

   MEASURED, with `get_project_path` stubbed empty and `run_api` stubbed to raise if reached:

   ```text
   probe on unresolvable project path -> ('ineligible', 'could not determine project path', None)
   preflight verdict -> None
   cmd_pr_merge -> {'status': 'success', 'operation': 'pr_merge', 'merged': True}
   CLI issued -> [['mr', 'merge', '42']]
   ```

   The GitHub sibling does **not** behave this way: `_resolve_base_queue_state`
   (`_github_pr.py:1211-1265`) fails closed on exactly this class — `if not owner or not repo:` returns
   `make_error(operation, 'Could not determine repository owner/name for the merge-queue preflight')`
   at lines 1253-1259 — so the docstring's *"exactly as its GitHub sibling does"* is the part that is
   wrong. Nor is GitLab internally consistent: `cmd_pr_merge_queue` at `gitlab_ops.py:699-701` **does**
   refuse an unresolvable project path (`return make_error('pr_merge_queue', 'Could not determine
   project path')`), so within one file the enqueue verb refuses the scope failure that the
   immediate-merge preflight waves through. The exposure reaches `gitlab:merge` and
   `gitlab:safe-merge`, two members of the plan's own derived population. Practical reachability is
   low (an empty project path normally means the caller is not in a GitLab repository at all) and the
   downstream `glab mr merge` behaviour against a train-enabled project is unmeasured, so the
   consequence is PLAUSIBLE rather than confirmed — but the fail-open branch itself is CONFIRMED and
   MEASURED.

6. **No idempotence or None-handling defect found** elsewhere in the guard paths this plan touched.
   `_merge_shaped_roster._handler_map_body` raises `AssertionError` rather than returning an empty
   body on a registry-regex miss (lines 67-73) — the correct choice for a population source.
   `_corroborate_merge` is established before the branch-delete follow-up on both providers
   (`_github_pr.py:1480`, `gitlab_ops.py` post-merge re-read), as the handler docstrings claim.

7. **The prose-bearing string literals in production code are checked and are not a gap here.**
   `ci_base.py:959` and `:971` describe `pr merge` / `pr auto-merge` as plain peers of the routed pair
   (*"Merge a pull request"*, *"Enable auto-merge on a PR"*), and the argument-shape table at
   `persona-plan-marshall-agent/standards/argument-naming.md:166` restates `ci pr merge`'s full flag
   surface the same way — none of the three hints that `branch-cleanup.md:1264-1265` declares both
   verbs unreachable from the routed step. Adding such a hint is nonetheless **out of scope by the
   plan's own exclusion** ("Strengthening the prose … a caller-side rule that already exists and was
   already bypassed cannot be fixed by writing it more emphatically"), so all three are recorded here
   as current state and not filed as actionable work. The remaining merge-shaped `help=` strings
   (`safe-merge` at `:986`, `merge-queue` at `:1030`) do describe their verb's own mechanism.

## Completeness review

1. **Four doc consumers of the changed refusal were not updated.** The GitHub sibling's remedy is
   spelled out in prose; the GitLab one is not, even though the code now carries it:
   - `pr-operations.md:55` (the corroboration table): *"**GitLab**: **no probe** … its HTTP 403/404 is
     the refusal"* — no routed alternative.
   - `pr-operations.md:351-352` § "The enqueue is corroborated", GitHub bullet: *"On any other
     eligibility value it returns `status: error` naming both remedies — run `/marshall-steward` →
     Configuration → Merge Queue to provision the queue, or disable the plan's `use_merge_queue` step
     param to merge immediately via `ci pr safe-merge`."* The GitLab bullet directly beneath it says
     only *"a failure surfaces as the actionable ineligible error"*.
   - `pr-operations.md:378`: *"the invocation returns `status: error, operation: pr_merge_queue` with
     the actionable ineligible message"* — no mention of the routed alternative.
   - `gitlab-impl.md:120-127`: *"its 403/404 is the refusal … The actionable-ineligible contract
     itself is cross-provider"* — no mention of the routed alternative.

   CONFIRMED by reading all four, found via
   `grep -rn "pr safe-merge|pr merge-queue|pr auto-merge|ci pr merge" marketplace/bundles/ --include=*.md -l`.

2. **The lock on the new message covers one of the two entry conditions, and the uncovered one is the
   load-bearing one.** The `safe-merge` assertion was added to `test_cmd_pr_merge_queue_ineligible_on_403`
   only (`test_gitlab_merge_queue.py:66-85`); `test_cmd_pr_merge_queue_ineligible_on_404` (lines 88-97)
   asserts only `status` and `operation`. MEASURED: under the mutation that deletes the ineligible
   branch, the 403 test goes red and the **404 test stays green** — and the 404 condition is the one
   the plan's own scenario model uses as the off-routing signature.

3. **The shared helper has exactly one consumer.** `grep -rn "_merge_shaped_roster"` over `*.py` and
   `*.md` finds `test_merge_shaped_offrouting_refusal.py:71` and prose references only. The
   first-instance guard still carries `_registry_keys` / `_registry_handler_names` /
   `_merge_shaped_registry_keys` (`test_branch_cleanup_merge_queue_routing.py:476, 496, 511`). The
   "single-source" discipline the helper's docstring names is not yet realised anywhere.

4. **`ci_base.dispatch` is uninstrumented** (`ci_base.py:1978-2032`, read in full). The plan named
   `ci.py` / `ci_base.py` as the router in its Expected surface; D2's record-a-departure obligation
   could have been discharged there for every verb at once and was not.

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
| GitLab `merge-queue` off-routing falsifiability is argued, not mutation-measured | **Still open, and the argument is refuted by measurement.** See report-claim 5: under the named mutation the off-routing arm stays green, because the fallback `make_error` keeps `status: error` |

## Adversarial review

This document and `gaps.md` have been re-derived against the tree by **two** independent adversarial
passes, neither of which took the preceding analysis on trust. Every finding below is stated in the
form the tree currently supports; nothing rests on an earlier reviewer's assertion.

**What was re-derived from source, independently, in each pass:** both `handlers: HandlerMap` registry
literals and the 8-member population; all eight handler bodies and their guard chains;
`_resolve_base_queue_state`, `_refuse_on_required_merge_queue`, `_probe_merge_queue_state`,
`_probe_merge_train_state`, `_refuse_on_required_merge_train`, `ci_base.make_error`,
`ci_base.dispatch`; every `**Observability (mandatory)**` block and the pairing arithmetic its lock
performs, at HEAD **and** at `ff11803b`; the caller enumeration across the whole bundle plus the
Python and project-local surfaces; the four doc consumers; the two new test files, the shared roster
helper, and both provider suites. Every `path:line` citation in this document and in `gaps.md` was
re-resolved against the file it names, by `grep` rather than by counting lines from an offset read.

**What was executed:** the three suites in scope (18 / 23 / 16 passed); a dispatch probe over all 8
members × both modes recording each result envelope and the CLI calls each handler issued; a
scope-failure probe of the GitLab merge-train preflight; and source mutations — delete the GitLab
ineligible branch, inject `('pr','queue-merge')` into the GitHub registry — each applied from a byte
snapshot under `$TMPDIR/` and restored from that snapshot, never with `git checkout`, with
`git status --porcelain` re-checked clean after each.

**What was read from GitHub** (not settleable from a clone): PR #1182's reviews, conversation
comments, check runs and commit list.

Standing outcome:

- **Upheld, on independent re-derivation:** the D0 derivation and its null result; the missing state
  read in `gitlab:merge-queue`; the wrong caller enumeration; the unfinalized `Outcome`; the
  contradictory build-gate footprint; the dangling landing record; the non-discriminating
  `[gitlab:merge-queue]` test arm; the absent population size in a green run; the hand-listed
  vocabulary; the single-consumer helper; the uninstrumented router; the four doc consumers; every
  report claim marked ACCURATE, spot-checked at its citation.
- **Established by measurement** rather than by argument: the refuted falsifiability claim (the mutant
  leaves the suite at 18 passed); the vocabulary blind spot (the injected `queue-merge` leaves 41
  passed); the 404/403 coverage asymmetry (the mutant reddens only the 403 arm); the side-effect
  ordering (`gitlab:merge-queue` alone issues its POST before refusing); and the GitLab preflight's
  fail-open on an unresolvable project scope (§ Correctness review item 5).
- **Downgraded from blocking, and the reasoning holds on re-examination:** `gitlab:merge-queue`'s
  delegation to the provider status is a **documented** provider-shaped design (`pr-operations.md:55`,
  `gitlab-impl.md:120-127`) rather than an omission, and its false-green consequence is unmeasured;
  the `[gitlab:merge-queue]` test arm's blind spot is real and measured, but the mutation it misses is
  caught by `test_gitlab_merge_queue.py`, so the tree is not blind to it. Both are **major**. A
  blocker here would require a demonstrated false green, and none has been produced. There are **no
  blocker-severity findings**.
- **Refuted:** the assertion that the promised finalization commit "never happened" — the PR's commit
  list ends with `0a77146e`, whose subject is exactly that finalization; what it omitted was the
  `Outcome` field. Refuted as *evidence*: `git log … returns ff11803b alone` proves nothing about
  branch history, because `git rev-list --parents -n 1 ff11803b` shows the PR was squashed. Refuted as
  *arithmetic*: an earlier reading of the dispatch probe reported "the seven guarded members refuse
  with no CLI call at all" — the probe shows **six** members refuse, five of them with no CLI call,
  and the two `auto-merge` members do not refuse at all (§ D1).
- **Could not verify:** the `./pw verify` totals and the four mutation payloads recorded in the report
  (no surviving artifact); whether GitLab's merge-train endpoint answers 2xx on a project with
  `merge_trains_enabled=false`, and whether `glab mr merge` succeeds against a train-enabled project
  with an unresolvable path (nobody in this repository has measured either, so both false-green
  consequences stay PLAUSIBLE).
- **Findings the report did not contain and neither deliverable review had recorded:** the GitLab
  merge-train preflight's fail-open on an unresolvable project scope (measured; the guard's own
  docstring claims the opposite and claims parity with a GitHub sibling that does fail closed); the
  absence of any scope identity in either GitLab refusal, against D2's "the expected branch" clause;
  the misattributed `sourcery-ai` verdict and the third GitHub surface (PR-level reviews) the report's
  two-surface read never opened; the false capability claim about
  `test_every_derived_member_has_an_offrouting_scenario`; the `pr-operations.md:55` fourth doc
  consumer; the measured 404-vs-403 lock asymmetry; the side-effect-before-refusal fact and the
  `returncode == 0` → `enqueued: true` success path as the concrete residual exposure; a fourth D0
  null-result candidate — the pre-merge rebase route, the one route in the tree that pairs a
  destructive member with a documented two-branch selection — checked and rejected on its guarded,
  siblingless callee; and the prose-bearing string literals (`ci_base.py:959`, `:971`,
  `argument-naming.md:166`) recorded as out-of-scope rather than actionable.
- **Corrected against the tree:** the landed `gitlab_ops.py` footprint (`+11/−1`, from
  `git show ff11803b --numstat`); the doc-consumer count (three → four); the caller-enumeration search,
  which needs two greps because a single contiguous pattern misses `branch-cleanup.md`'s own two
  dispatch lines; the source-guard row-regex citation (223 → 222); and the D0 near-miss / post-merge
  route line spans.

## Summary

**Counts by severity:** 0 blockers, 8 major (G1–G8), 6 minor (G9–G14) — fourteen actionable entries,
see `gaps.md`. Four of the fourteen are confirmed false report claims (G4, G5, G6, G7); a fifth false
claim, the capability attributed to `test_every_derived_member_has_an_offrouting_scenario`, is folded
into G3's evidence because its remedy is the same test change. The report-claim audit above carries
nineteen rows: 8 FALSE, 3 OVERSTATED, 6 ACCURATE, 2 UNVERIFIABLE.

Bottom line: the plan's substance largely landed and is real — D0's 8-member derivation is
reproducible from the tree, seven of the eight members consult a genuine callee-side state read, the
two new test files exist and run green, and the cold-read message fix is correct and locked. What
falls short is narrower than a failed deliverable and wider than bookkeeping. `gitlab:merge-queue`
alone delegates its off-routing verdict to the provider's HTTP status *after* issuing the POST, on a
documented rationale whose premise nobody has measured; the test arm that was supposed to cover that
member cannot fail for the reason it claims, and the report's structural argument that it could is
demonstrably wrong under mutation. The GitLab preflight the other two GitLab members share fails
**open** on an unresolvable project scope while its docstring claims it fails closed "exactly as its
GitHub sibling does" — a sibling that does fail closed on the same class, and a file whose own enqueue
verb refuses the same scope failure two hundred lines away. The population guard is blind to a
merge-shaped verb registered under a new name — the exact defect class D0 was forbidden to reproduce —
while the report claims the opposite. The published caller enumeration misnames the marshall-steward
landing cycle's verb, the very caller that unconditionally dispatches a merge-shaped verb outside any
route. And `report-01.md` was never given a contract-legal `Outcome`, asserts "No production source
was changed by this plan" in direct contradiction of the diff it shipped with, and records a reviewer
as silent when that reviewer published a rate-limit refusal on a surface the run never opened.
