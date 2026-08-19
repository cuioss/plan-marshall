# Gaps — 060-a-prose-routing-table-is-not-an-enforcement-boundary

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

**Fourteen entries: 0 blockers, 8 major (G1–G8), 6 minor (G9–G14).** Every severity, citation and
count here agrees with `verification.md`; where the two would disagree, the tree decides and both are
corrected together.

## G1 — Give GitLab `pr merge-queue` a callee-side merge-train preflight

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:681-720`
  (`cmd_pr_merge_queue`). The unused sibling probe is at the same file, line 567
  (`_probe_merge_train_state`), already called from lines 633, 751, 776 and 2118.
- **Evidence:** the handler goes from `_resolve_mr_iid` / `get_project_path` straight to
  `run_glab(['api', '-X', 'POST', endpoint])` at line 705, with no state read. Its GitHub sibling
  (`_github_pr.py:1894`) refuses first: `if discriminator != MERGE_QUEUE_ELIGIBLE_CONFIGURED:`.
  Confirmed by reading both handler bodies end to end and by
  `grep -n "_probe_merge_train_state" gitlab_ops.py`, which lists every call site (567, 633, 751, 776,
  2118) and does not include this one. MEASURED by a dispatch probe over all 8 members × both modes:
  `gitlab:merge-queue` issues
  `['api', '-X', 'POST', 'projects/octo%2Frepo/merge_trains/merge_requests/42']` in **both** the
  off-routing and the compliant run — the two differ only in what the stub returns — while the five
  other refusing members reach `status: error` with no CLI call at all.
- **Impact:** this is the single member of the plan's own derived 8-member population whose
  off-routing verdict is not established at the callee, and the only one whose refusal lands *after* a
  side-effecting call. The refusal depends entirely on the provider answering HTTP 403/404. On a
  project where `merge_trains_enabled` is `false` but the endpoint answers 2xx, `gitlab_ops.py:722-738`
  derives `enqueued: true` from `returncode == 0` alone and swallows a `json.JSONDecodeError` on the
  car read-back, yielding `enqueued: true` with an empty `merge_train_car_id` for an MR that joined no
  train — the false-green signature the epic exists to eliminate. Its GitHub sibling publishes
  `enqueue_corroboration` from a probe verdict instead. `report-01.md` § D1 nevertheless states "every
  D0 member refuses an off-routing dispatch".
- **Not a blocker, and why:** the delegation is documented as deliberate and provider-shaped
  (`pr-operations.md:55`: *"**GitLab**: **no probe** — the POST to the dedicated merge-train endpoint
  is itself the corroboration … and its HTTP 403/404 is the refusal"*; `gitlab-impl.md:120-127` gives
  the same rationale), and the 2xx-on-unconfigured case is PLAUSIBLE, not measured — nobody in this
  repository has produced the false green. What makes it still worth closing is that the documented
  basis is an unverified assumption about provider behaviour, which is the exact assumption class the
  plan exists to remove.
- **Task:** call `_probe_merge_train_state()` at the top of `cmd_pr_merge_queue`, before the POST.
  Refuse with `make_error('pr_merge_queue', …)` when the discriminator is not
  `MERGE_QUEUE_ELIGIBLE_CONFIGURED`, mirroring the GitHub refusal's shape and naming both remedies
  (provision trains via `/marshall-steward` → Configuration → Merge Queue, or disable the plan's
  `use_merge_queue` step param and merge via `ci pr safe-merge`). Keep the existing 403/404 handling
  as the residual transport-level arm. Preserve the pre-call ordering rationale already documented
  for the GitHub sibling: the probe is read-only, so a refusal costs no side effect. Update the two
  doc passages that state the no-probe design (G9) in the same change, so code and contract move
  together.
- **Done when:** `cmd_pr_merge_queue` returns `status: error` on an off-routing dispatch **without**
  issuing the merge-train POST, proven by a test that stubs `_probe_merge_train_state` to
  `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED`, stubs `run_glab` to succeed, and asserts both the error and
  that `run_glab` captured no `api -X POST` call.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards

## G2 — Close the GitLab merge-train preflight's fail-open on an unresolvable project scope

- **Severity:** major
- **Kind:** defect
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:583`
  (`_probe_merge_train_state`'s unresolvable-path return) and `:622-646`
  (`_refuse_on_required_merge_train`, whose docstring at lines 624-626 claims the opposite behaviour).
  The affected members are `gitlab:merge` (preflight called at `:1955`) and `gitlab:safe-merge`
  (`:2202`).
- **Evidence:** `_probe_merge_train_state` returns
  `(MERGE_QUEUE_INELIGIBLE, 'could not determine project path', None)` when `get_project_path()` is
  empty. A `None` third element means "no error" and `ineligible` means "the feature is absent", so
  `_refuse_on_required_merge_train` falls through to `return None` and permits the immediate merge — a
  scope *resolution* failure folded into a feature *availability* verdict. MEASURED with
  `get_project_path` stubbed empty and `run_api` stubbed to raise if reached:

  ```text
  probe on unresolvable project path -> ('ineligible', 'could not determine project path', None)
  preflight verdict -> None
  cmd_pr_merge -> {'status': 'success', 'operation': 'pr_merge', 'merged': True}
  CLI issued -> [['mr', 'merge', '42']]
  ```

  The docstring at `:624-626` states *"Fails closed: a probe error (auth scope, transient API failure,
  malformed project response) refuses the merge rather than merging blind, exactly as its GitHub
  sibling does."* Those three cases do fail closed; this fourth one is not among them, and the
  sibling comparison is wrong — `_github_pr.py:1253-1259` returns
  `make_error(operation, 'Could not determine repository owner/name for the merge-queue preflight')`
  on exactly this class. GitLab is not internally consistent either:
  `cmd_pr_merge_queue` at `gitlab_ops.py:699-701` **does** refuse an unresolvable project path.
- **Impact:** two members of the plan's derived population can perform an immediate merge without the
  train state ever being established — a fail-open in the guard the plan generalises, in the file the
  plan edited, with the guard's own docstring asserting the opposite. Practical reachability is low
  (an empty project path normally means the caller is not in a GitLab repository at all) and the
  downstream `glab mr merge` behaviour against a train-enabled project is unmeasured, so the
  false-green consequence is PLAUSIBLE rather than confirmed; the fail-open branch itself is measured.
- **Task:** split the two verdicts `_probe_merge_train_state` currently conflates. Return an
  actionable error (a non-`None` third element) for the unresolvable-project-path case so the
  preflight refuses, leaving `ineligible`/`error=None` for the genuine feature-absence verdicts (the
  missing `merge_trains_enabled` field and the two eligible outcomes). Correct the
  `_refuse_on_required_merge_train` docstring to enumerate what it actually refuses on, and align the
  message with `cmd_pr_merge_queue`'s existing wording so the two agree.
- **Done when:** `_refuse_on_required_merge_train` returns an error dict when `get_project_path()` is
  empty, locked by a test that stubs it empty and asserts `cmd_pr_merge` returns `status: error` and
  issued no `mr merge` call; and the docstring's fail-closed claim matches the branches that exist.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards

## G3 — Make the `[gitlab:merge-queue]` off-routing arm discriminate a guard from a transport failure

- **Severity:** major
- **Kind:** missing-test
- **Where:** `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py:158-171`
  (`_gl_run_stub`), `:234` (`mt_post_ok = not (verb == 'merge-queue' and mode == 'off_routing')`,
  inside `_dispatch` at `:206`), `:324-328` (the `else` branch asserting only
  `result.get('status') == 'error'`), and `:277-292`
  (`test_every_derived_member_has_an_offrouting_scenario`).
- **Evidence:** the arm manufactures its own refusal — the stub returns `(1, '', 'HTTP 404: not found')`
  — and the monkeypatched `_probe_merge_train_state` is never read by the handler under test.
  `ci_base.make_error` (def at `ci_base.py:777`, `status: 'error'` assigned at `:783`) sets that
  status on every branch, so the generic fallback at `gitlab_ops.py:720` satisfies the assertion just
  as well as the ineligible branch at `:708`. MEASURED: deleting the ineligible branch leaves the file
  at **18 passed**. The same file's second population claim is also false — `report-01.md` § D3 says a
  merge-shaped verb added to a registry without an off-routing scenario "fails
  `test_every_derived_member_has_an_offrouting_scenario` rather than being silently skipped"; MEASURED,
  injecting `('pr','queue-merge'): cmd_pr_merge_queue` into `github_ops.py`'s registry literal leaves
  **both** population guards green (41 passed), because `merge_shaped_keys`
  (`_merge_shaped_roster.py:97-107`) filters the verb out before either test sees it.
- **Impact:** one of the eight members of a guard advertised as "population-complete" is covered by an
  assertion that cannot fail for the reason it names, and the scenario-coverage arm cannot detect the
  addition it claims to. A future deletion of the ineligible branch — or, after G1, of the preflight —
  leaves the suite green. Not a blocker: the specific mutation this arm misses is caught by
  `test_gitlab_merge_queue.py::test_cmd_pr_merge_queue_ineligible_on_403`, so the tree is not blind to
  it; the guard that advertises population-completeness is.
- **Task:** strengthen the arm so it identifies *which* refusal fired. For the immediate-merge and
  enqueue members assert the refusal message names the correct alternative routed verb (`merge-queue`
  for the immediate verbs, `safe-merge` for the enqueue verb) rather than only `status: error`. After
  G1 lands, drive `[gitlab:merge-queue]` off-routing through the probe discriminator like every other
  member and assert no POST was issued (`_captured` is already returned by `_dispatch` and currently
  discarded at lines 311 and 346), which also removes the mirror tautology in
  `test_compliant_route_succeeds[gitlab:merge-queue]`, where the compliant run issues the identical
  POST. Correct the report's capability claim about the scenario arm at the same time; the actual
  remedy for that claim is G10.
- **Done when:** neutralising `gitlab_ops.cmd_pr_merge_queue`'s off-routing refusal turns
  `test_offrouting_dispatch_is_refused_at_the_callee[gitlab:merge-queue]` red, measured by an actual
  mutation run recorded in the follow-up plan's report — closing the second residue item, which was
  argued rather than measured and argued wrongly.
- **Suggested grouping:** tools-integration-ci / off-routing behavioural guard

## G4 — Correct the caller enumeration: the marshall-steward landing cycle dispatches `pr merge-queue`

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/060-.../report-01.md` § D1 ("the marshall-steward landing
  cycle uses `safe-merge`") versus
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md:152-154`.
- **Evidence:** the landing cycle's Step 5(c) reads *"**(c) Merge via the platform merge queue** —
  WITHOUT `--delete-branch`"* and dispatches
  `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue --head {branch}`
  unconditionally — no `use_merge_queue` read, no routing branch, no fallback.
  `git log --oneline -S'ci pr merge-queue' -- <that file>` returns only `27be6350`, which
  `git merge-base --is-ancestor 27be6350 ff11803b` confirms is an ancestor, so this was already true
  when the plan ran.
- **Impact:** D1's *Done when* required the caller enumeration to be published, and the plan's
  UNKNOWN claim ("some legitimate caller depends on reaching a D0 member outside its route") was
  resolved "in the negative" on an enumeration that misnames this caller's verb. The steward path is
  a sanctioned caller that dispatches a merge-shaped verb against a base whose queue state it never
  checks; on a repository with no configured merge queue the callee refuses it (`_github_pr.py:1894`)
  and the landing cycle documents no remedy.
- **Method note the re-derivation must carry:** a single contiguous grep is not sufficient. The two
  dispatch lines in `branch-cleanup.md` (`:1299` `pr merge-queue`, `:1321` `pr safe-merge`) interpose
  `--project-dir {worktree_path}` between the script token and the noun, so
  `grep -rn "tools-integration-ci:ci pr merge-queue\|…"` misses them; the enumeration closes only when
  that search is unioned with `grep -n "execute-script.py plan-marshall:tools-integration-ci"` over
  `branch-cleanup.md` and a `--include=*.py` sweep of `marketplace/` and `.claude/`.
- **Task:** re-derive the caller enumeration across the whole bundle (not only the finalize
  lifecycle) using both searches, correct it in a follow-up record, and decide the steward path
  explicitly: either route it on the same `use_merge_queue` signal the finalize step uses, or document
  that the steward requires a provisioned queue and state what the operator does when the refusal
  fires.
- **Done when:** every documented dispatcher of a merge-shaped `ci pr` verb is listed with the verb it
  actually issues, verified against the dispatch line in each file; and `landing-cycle.md` either
  routes or states its precondition and the remedy for the refusal.
- **Suggested grouping:** marshall-steward / landing cycle

## G5 — Finalize `report-01.md`: the outcome, the build-gate footprint, and the landing record

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `report-01.md` header (`**Outcome:** _in progress_`), § Build gate ("No production source
  was changed by this plan" and the footprint stated as "two test files"), § Contract check Step 8
  ("Landing recorded to the operator (see below)").
- **Evidence:** `git show ff11803b --name-status` lists
  `M marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` and
  `M test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py` alongside the two new
  test files; `--numstat` gives them as `+11/−1` and `+4` — four Python paths, one of them production,
  and the report's own F3 describes making that production change. No landing record appears anywhere
  below the Step 8 row: the sections after it are the GitHub-access/branch-form note, "What have we
  learned" and "Residue". The lane contract in force at the time
  (`git show ff11803b:.claude/skills/cloud-plan-lane/SKILL.md:844`) admits only
  `completed | partial | blocked` for `Outcome`.
- **Impact:** an unfinalized report reads as an abandoned run, and its Build-gate section states the
  opposite of the diff it shipped with. The reviewer verdicts stated for the final head are
  predictions ("their expected verdicts are unchanged"), which the contract's "A claim is not an
  outcome" rule forbids — and one of them is wrong (G6).
- **Not owed, so do not add them:** the `> **Verification loop exit:**` line and the stale-base
  re-verification figure post-date this run — `git log -S` over the lane skill dates them to
  `7d61d671` (#1297) and `2cbcb1f3` (#1299), neither an ancestor of `ff11803b`.
- **Task:** amend `report-01.md`: set `Outcome`, correct § Build gate to name all four changed Python
  paths and to state that one production file (`gitlab_ops.py`, the F3 refusal-parity fix, `+11/−1`)
  was changed, replace the dangling "see below" with the actual landing record, and replace the
  predicted reviewer verdicts with what the surfaces actually held at merge.
- **Done when:** `report-01.md` carries a contract-legal `Outcome`, no statement in it contradicts
  `git show ff11803b --name-status`, and no forward-looking prediction is presented as an observation.
- **Suggested grouping:** review-apparatus / run-report hygiene

## G6 — Correct the `sourcery-ai` verdict, and add the PR-level reviews surface to the read

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `report-01.md` § Reviewer participation (`sourcery-ai` = *"`silent` … no review artifact
  and no notice was published"*) and § Contract check Step 8 (the disclosure text *"`sourcery-ai`
  skipped/silent"*). The method statement it follows from is § PR cycle: *"both comment surfaces
  read"*.
- **Evidence:** PR #1182's **reviews** surface carries a `sourcery-ai[bot]` review (id 4915308445,
  `state: COMMENTED`, on commit `1d3ce632`) whose entire body is *"Sorry @cuioss-oliver, you have
  reached your weekly rate limit of 500000 diff characters."* The check-run half of the report's claim
  is accurate — `Sourcery review` concluded `skipped`, on the final head `0a77146e` as well — but the
  bot was rate-limited and said so, not silent. Read through the GitHub MCP server (`get_reviews`,
  `get_check_runs`, `get_commits`), which a clone cannot settle.
- **Impact:** the 1-of-3 coverage figure is unaffected — a refusal is not a review — but the cause
  stated to the operator is wrong in the direction that matters: a rate limit reopens, a skip does
  not, so the disclosure understates what a short wait would have bought. The root cause is a method
  gap, not a transcription slip: the run read the conversation and inline-review-thread surfaces; the
  PR-level reviews surface is a **third**, and it is where this bot published.
- **Task:** correct both passages in `report-01.md` to state the observed cause (rate-limited, notice
  published on the reviews surface, check run skipped). Then close the method gap where it belongs: if
  the lane contract's reviewer read enumerates surfaces, add the PR-level reviews surface to it, so a
  bot that publishes only there is not recorded as silent.
- **Done when:** no passage in `report-01.md` describes `sourcery-ai` as silent, and the reviewer-read
  step names all three surfaces a bot can publish on.
- **Suggested grouping:** review-apparatus / run-report hygiene

## G7 — Correct the refuted falsifiability argument in the report's residue

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `report-01.md` § D3 (the "Cross-provider / cross-verb reach" bullet for
  `refuse_unconfigured`) and § Residue (second item).
- **Evidence:** the claim is *"dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s
  off-routing test"*. Deleting the `if _is_auth_scope_error(stderr_text) or 'http 404' in stderr_text.lower():`
  block at `gitlab_ops.py:708` leaves
  `return make_error('pr_merge_queue', f'Failed to enqueue MR {iid} onto the merge train', stderr_text)`
  at `:720`; `make_error` (`ci_base.py:783`) always sets `status: 'error'`; the off-routing arm asserts
  only `status == 'error'` (`test_merge_shaped_offrouting_refusal.py:325`). MEASURED: under that mutant
  the file reports **18 passed**. The pre-existing `test_cmd_pr_merge_queue_generic_error_is_not_ineligible`
  (`test_gitlab_merge_queue.py:100`) demonstrates the same fallback path returning `status: error`.
- **Impact:** the one member whose falsifiability was argued rather than measured has an argument that
  is wrong, so the suite's discrimination on that member is unestablished in both directions. The
  report presents the argument as a substitute for the measurement it did not run.
- **Task:** correct the two passages to state that the arm is not falsifiable as written, and fold the
  remedy into G3. Do not restate the structural argument.
- **Done when:** neither passage asserts a mutation that would not flip the named test.
- **Suggested grouping:** review-apparatus / run-report hygiene

## G8 — Record a departure record for the sanctioned exception, or at the router

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:1592-1645`
  (`cmd_pr_auto_merge`), `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:2080-2137`
  (`cmd_pr_auto_merge`), and `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:1978-2032`
  (`dispatch`).
- **Evidence:** D2's *Done when* is "a departure from a documented route emits a record naming the
  route, the expected branch, and the verb actually dispatched". An off-routing `ci pr auto-merge` — a
  verb `branch-cleanup.md:1265` marks **never** reachable from the routed step — returns
  `status: success` with `disposition: enqueued` and no mention of any route; MEASURED by the dispatch
  probe, which shows both providers' `auto-merge` issuing their scheduling call and reporting
  `disposition: enqueued` on a queued base. `ci_base.dispatch` carries no logging of the key it routed
  on (read in full, lines 1978-2032).
- **Impact:** the plan's sanctioned exception is the one member whose off-routing dispatch is both
  permitted and unrecorded, so the next departure through it is as unexplainable as the incident that
  produced the plan — which is exactly what D2 exists to prevent. The plan named `ci.py` / `ci_base.py`
  as "the router that performs the dispatch" in its Expected surface; the obligation could have been
  discharged there for every verb at once.
- **Task:** either (a) have both `cmd_pr_auto_merge` handlers add an advisory field naming the routed
  alternative when the probe reports a configured queue/train — e.g. a `routing_note` stating that
  `ci pr merge-queue` is the routed verb for a queued base — or (b) emit one structured record in
  `ci_base.dispatch` naming the dispatched `(noun, verb)` for every merge-shaped key. Do not turn the
  sanctioned exception into a refusal: the report's preservation argument for the
  enqueue-via-auto-merge path is sound and the compliant route must keep succeeding.
- **Done when:** an off-routing `pr auto-merge` on both providers emits a record naming the routed
  verb it departed from, locked by a test asserting that field's presence on the queued-base path and
  its absence (or its `enabled` form) on the unqueued one.
- **Suggested grouping:** tools-integration-ci / routing observability

## G9 — Carry the new GitLab refusal remedy into its four doc consumers

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md:55`
  (the corroboration table), `:352` (the GitLab bullet under § "The enqueue is corroborated"), `:378`;
  and `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/gitlab-impl.md:120-127`.
- **Evidence:** the GitHub bullet at `pr-operations.md:351` spells the remedy out — *"it returns
  `status: error` naming both remedies — run `/marshall-steward` → Configuration → Merge Queue to
  provision the queue, or disable the plan's `use_merge_queue` step param to merge immediately via
  `ci pr safe-merge`"* — while the GitLab bullet directly beneath it at `:352` says only *"a failure
  surfaces as the actionable ineligible error"*. `:55` says *"**GitLab**: **no probe** … its HTTP
  403/404 is the refusal"* and `:378` only *"with the actionable ineligible message"*; `gitlab-impl.md`
  says *"its 403/404 is the refusal"* and names no alternative verb. The shipped GitLab message now
  names `ci pr safe-merge` (`gitlab_ops.py:713-719`). Found via
  `grep -rn "pr safe-merge\|pr merge-queue\|pr auto-merge\|ci pr merge" marketplace/bundles/ --include=*.md -l`,
  then reading every hit.
- **Impact:** the boundary-not-wall property the F3 fix established is invisible to a reader of the
  contract docs, and a future edit could remove it from the code without any doc disagreeing.
- **Task:** add the routed-verb remedy to `pr-operations.md:55`, `:352` and `:378`, and to the
  merge-train paragraph in `gitlab-impl.md`, in the same shape as the GitHub bullet. If G1 lands, the
  *"**no probe**"* statements at `pr-operations.md:55` and `gitlab-impl.md:120-127` also stop being
  true and must be rewritten in the same change rather than left behind it.
- **Done when:** all four passages state that the GitLab ineligible refusal names `ci pr safe-merge`
  as the alternative routed verb, and no passage describes a probe posture the code no longer has.
- **Suggested grouping:** tools-integration-ci / provider contract docs

## G10 — Make the derived population independent of a hand-listed verb vocabulary

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `test/_shared/_merge_shaped_roster.py:43` (`MERGE_SHAPED_VERBS`) and its twin
  `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:153`
  (`_MERGE_SHAPED_VERBS`) — the two frozensets are identical.
- **Evidence:** `merge_shaped_keys` (`_merge_shaped_roster.py:97-107`) filters registry keys by
  `key[1] in MERGE_SHAPED_VERBS`, so a merge-shaped verb registered under any other name is not in
  the derived population at all. The size assertion at
  `test_merge_shaped_offrouting_refusal.py:270` (`verbs_by_provider.get(provider) == set(MERGE_SHAPED_VERBS)`)
  detects a member disappearing, never a new one appearing under a new name. MEASURED: injecting
  `('pr','queue-merge'): cmd_pr_merge_queue` into `github_ops.py`'s registry literal leaves both
  population guards green (41 passed).
- **Impact:** the plan forbade hand-listing the verb sets ("a hand-maintained list of the sites that
  need guarding is the same defect in a new place"); the derivation is registry-driven for
  *membership* but hand-listed for *vocabulary*, so "population-complete" means complete over four
  pre-named verbs. The module docstring is honest about this (*"This is the VOCABULARY the derivation
  filters against — not a membership claim"*), and the frozenset is inherited byte-for-byte from the
  reference implementation, so the hand-list is a residual rather than a regression; `report-01.md`
  § D3's claim that the scenario arm catches such an addition is the regression.
- **Task:** add a secondary derivation that flags any `('pr', verb)` registry key whose handler body
  reaches the platform queue/train symbol vocabulary (the predicate
  `test_branch_cleanup_merge_queue_routing.py:568` `_first_queue_symbol` already implements) but whose
  verb is outside `MERGE_SHAPED_VERBS` — a "merge-shaped by behaviour, not by name" detector that
  fails loudly and names the verb.
- **Done when:** registering a queue-guarded `('pr','queue-merge')` handler in either provider fails a
  test naming it, rather than being silently filtered out of the population.
- **Suggested grouping:** tools-integration-ci / population derivation

## G11 — Consolidate the first-instance source guard onto the shared roster helper

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:219, 222,
  476, 496, 511` versus `test/_shared/_merge_shaped_roster.py:54, 57, 76, 84, 97`.
- **Evidence:** the source guard still defines `_HANDLER_MAP_RE`, `_HANDLER_ROW_RE`, `_registry_keys`,
  `_registry_handler_names` and `_merge_shaped_registry_keys` itself; the regexes are
  character-for-character identical to the helper's, with the same `re.DOTALL`.
  `grep -rn "_merge_shaped_roster"` across `*.py` finds exactly one importer
  (`test_merge_shaped_offrouting_refusal.py:71`). This is residue item 1 from `report-01.md`, still
  open — `git log --oneline -- test/_shared/_merge_shaped_roster.py` shows no commit after `ff11803b`.
- **Impact:** the helper's own docstring calls itself "the designated single source"; with one consumer
  and a byte-identical private copy next door, the single-source discipline is documented but not
  realised, and the two can drift.
- **Task:** in a `chore/` change, replace the source guard's five private symbols with imports from
  `_merge_shaped_roster`, keeping its path resolution (it reads two GitHub handler-source files, the
  helper takes text) at the call site.
- **Done when:** `test_branch_cleanup_merge_queue_routing.py` imports its registry derivation from
  `_merge_shaped_roster` and defines no `handlers:\s*HandlerMap` regex of its own, with both suites
  still green.
- **Suggested grouping:** tools-integration-ci / population derivation

## G12 — Publish the population size in a passing run's output, or drop the claim

- **Severity:** minor
- **Kind:** omission
- **Where:** `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py:246-274`;
  the same shape at `test_branch_cleanup_merge_queue_routing.py:642`
  (`test_registry_populations_are_published_and_plausible`).
- **Evidence:** the size reaches only the `assert … , (f'…{size}…')` failure messages.
  `grep -rn "print("` over both new files returns nothing and
  `grep -rn "pytest_terminal_summary\|pytest_report_header" test/` returns nothing, so no conftest
  supplies one; the observed output of a green run is `..................  [100%]` / `18 passed`. The
  plan's D3 *Done when* is "the population size appears in the test's own output"; `report-01.md` § D3
  asserts it does.
- **Impact:** the distinguishing signal the plan asked for — a passing run being visibly different from
  an empty-population run — is carried by the `== 8` assertion rather than by any output, so the
  stated obligation is met in substance but not as written, and the report's claim about it is
  overstated.
- **Task:** either emit the size on a passing run (a `pytest_report_header` entry in
  `test/conftest.py`, or a `print` the `-s` run surfaces) applied consistently to both population
  guards, or amend the two reports' wording to say the size is published in the failure message and
  the members in the parametrization ids.
- **Done when:** the size is observable in a green run's output, or no document claims that it is.
- **Suggested grouping:** tools-integration-ci / population derivation

## G13 — Name the scope in the GitLab refusals, as the GitHub siblings name the base branch

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:639-641`
  (`_refuse_on_required_merge_train`'s message) and `:715-717` (`cmd_pr_merge_queue`'s ineligible
  message, which inherits `_MERGE_TRAIN_INELIGIBLE_HINT` at `:554-558`).
- **Evidence:** D2's *Done when* requires the departure record to name "the route, the expected
  branch, and the verb actually dispatched". The GitHub refusals name the base branch
  (`_github_pr.py:1281`, `:1897`: *"PR {identifier} targets base branch {base_branch!r} …"*). Neither
  GitLab refusal names any scope: `:639` says *"This project has merge trains enabled"* with no project
  identity, its `detail` argument is the probe's `'merge_trains_enabled=true'` (`:598`) which carries
  none either, and `_MERGE_TRAIN_INELIGIBLE_HINT`'s *"This project is not eligible"* is likewise
  anonymous. Only the un-routed fallback at `:720` names the MR. Confirmed by reading all four
  messages and the probe's return values.
- **Impact:** that a GitLab merge train is project-scoped rather than branch-scoped is real and
  documented (`gitlab_ops.py:610-616`), so "the expected branch" has no GitLab analogue — but the
  project path is resolved on both paths (`get_project_path()`) and is simply not put in the record.
  A reader of a GitLab refusal cannot tell which project it is about, which is the same
  reconstruct-it-afterwards posture D2 exists to remove. Low risk, because the operator usually knows
  their own project; it becomes real in a multi-project or worktree context.
- **Task:** pass the resolved project path into both refusal messages (or into their `detail`), in the
  same shape the GitHub siblings use for the base branch. Do not invent a branch scope — inventing a
  base-branch-scoped GitLab probe is explicitly rejected at `gitlab_ops.py:610-616`.
- **Done when:** both GitLab refusals name the project they apply to, locked by an assertion in
  `test_gitlab_merge_queue.py` and in the merge-train preflight's test.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards

## G14 — Assert the routed-verb remedy on the 404 arm as well as the 403 arm

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py:66-85`
  (`test_cmd_pr_merge_queue_ineligible_on_403`, which carries the `safe-merge` assertion) versus
  `:88-97` (`test_cmd_pr_merge_queue_ineligible_on_404`, which asserts only `status` and `operation`).
- **Evidence:** both stubs drive the same branch at `gitlab_ops.py:708`, but only the 403 test locks
  the message content. MEASURED: under the mutation that deletes the ineligible branch, the 403 test
  goes red on its `'safe-merge' in message` assertion and the **404 test stays green**.
- **Impact:** the 404 condition is the one the plan's own scenario model treats as the off-routing
  signature, and it is the arm with no message lock. Low practical risk while both conditions share a
  branch; it becomes real the moment they diverge.
- **Task:** add the `'merge train' in message` and `'safe-merge' in message` assertions to the 404
  test, matching its 403 sibling.
- **Done when:** both ineligible tests assert the message names the merge train and `safe-merge`.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards
