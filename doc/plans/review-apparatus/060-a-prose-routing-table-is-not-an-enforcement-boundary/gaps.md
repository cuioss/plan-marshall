# Gaps — 060-a-prose-routing-table-is-not-an-enforcement-boundary

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Give GitLab `pr merge-queue` a callee-side merge-train preflight

- **Severity:** blocker
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:681-720`
  (`cmd_pr_merge_queue`). The unused sibling probe is at the same file, line 567
  (`_probe_merge_train_state`), already called from lines 633, 751, 776 and 2118.
- **Evidence:** the handler goes from `_resolve_mr_iid` / `get_project_path` straight to
  `run_glab(['api', '-X', 'POST', endpoint])` with no state read. Its GitHub sibling
  (`_github_pr.py:1894`) refuses first: `if discriminator != MERGE_QUEUE_ELIGIBLE_CONFIGURED:`.
  Confirmed by reading both handler bodies end to end and by
  `grep -n "_probe_merge_train_state()" gitlab_ops.py`, which lists every call site and does not
  include this one.
- **Impact:** this is the single member of the plan's own derived 8-member population with no
  callee-side off-routing check — the plan's part-(c) "asymmetric checking across the siblings"
  surviving inside the population it was written to close. The refusal depends entirely on the
  provider answering HTTP 403/404. On a project where `merge_trains_enabled` is `false` but the
  endpoint answers 2xx, the verb returns `enqueued: true` for an MR that joined no train — the exact
  false-green signature the epic exists to eliminate. `report-01.md` § D1 nevertheless states "every
  D0 member refuses an off-routing dispatch".
- **Task:** call `_probe_merge_train_state()` at the top of `cmd_pr_merge_queue`, before the POST.
  Refuse with `make_error('pr_merge_queue', …)` when the discriminator is not
  `MERGE_QUEUE_ELIGIBLE_CONFIGURED`, mirroring the GitHub refusal's shape and naming both remedies
  (provision trains via `/marshall-steward` → Configuration → Merge Queue, or disable the plan's
  `use_merge_queue` step param and merge via `ci pr safe-merge`). Keep the existing 403/404 handling
  as the residual transport-level arm. Preserve the pre-call ordering rationale already documented
  for the GitHub sibling: the probe is read-only, so a refusal costs no side effect.
- **Done when:** `cmd_pr_merge_queue` returns `status: error` on an off-routing dispatch **without**
  issuing the merge-train POST, proven by a test that stubs `_probe_merge_train_state` to
  `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED`, stubs `run_glab` to succeed, and asserts both the error and
  that `run_glab` captured no `api -X POST` call.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards

## G2 — Make the `[gitlab:merge-queue]` off-routing arm discriminate a guard from a transport failure

- **Severity:** blocker
- **Kind:** missing-test
- **Where:** `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py:158-171`
  (`_gl_run_stub`), `:234` (`mt_post_ok = not (verb == 'merge-queue' and mode == 'off_routing')`),
  `:324-328` (the `else` branch asserting only `result.get('status') == 'error'`).
- **Evidence:** the arm manufactures its own refusal — the stub returns `(1, '', 'HTTP 404: not found')`
  — and the monkeypatched `_probe_merge_train_state` is never read by the handler under test.
  `ci_base.make_error` (`ci_base.py:783`) sets `status: 'error'` on every branch, so the generic
  fallback at `gitlab_ops.py:720` satisfies the assertion just as well as the ineligible branch at
  line 713. `report-01.md` § Residue claims "dropping the 404/403-as-refusal handling flips
  `gitlab:merge-queue`'s off-routing test" — it does not.
- **Impact:** one of the eight members of a guard advertised as "population-complete" is covered by an
  assertion that cannot fail for the reason it names. A future deletion of the ineligible branch — or,
  after G1, of the preflight — leaves the suite green.
- **Task:** strengthen the arm so it identifies *which* refusal fired. For the immediate-merge and
  enqueue members assert the refusal message names the correct alternative routed verb (`merge-queue`
  for the immediate verbs, `safe-merge` for the enqueue verb) rather than only `status: error`. After
  G1 lands, drive `[gitlab:merge-queue]` off-routing through the probe discriminator like every other
  member and assert no POST was issued (`_captured` is already returned by `_dispatch` and currently
  discarded at lines 311 and 346).
- **Done when:** neutralising `gitlab_ops.cmd_pr_merge_queue`'s off-routing refusal turns
  `test_offrouting_dispatch_is_refused_at_the_callee[gitlab:merge-queue]` red, measured by an actual
  mutation run recorded in the follow-up plan's report — closing the second residue item, which was
  argued rather than measured and argued wrongly.
- **Suggested grouping:** tools-integration-ci / off-routing behavioural guard

## G3 — Correct the caller enumeration: the marshall-steward landing cycle dispatches `pr merge-queue`

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/060-.../report-01.md` § D1 ("the marshall-steward landing
  cycle uses `safe-merge`") versus
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md:152-154`.
- **Evidence:** the landing cycle's Step 5(c) reads *"**(c) Merge via the platform merge queue** —
  WITHOUT `--delete-branch`"* and dispatches
  `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue --head {branch}`
  unconditionally — no `use_merge_queue` read, no routing branch, no fallback.
  `git log --oneline -S'ci pr merge-queue' -- <that file>` returns only `27be6350`, an ancestor of
  `ff11803b`, so this was already true when the plan ran.
- **Impact:** D1's *Done when* required the caller enumeration to be published, and the plan's
  UNKNOWN claim ("some legitimate caller depends on reaching a D0 member outside its route") was
  resolved "in the negative" on an enumeration that misnames this caller's verb. The steward path is
  a sanctioned caller that dispatches a merge-shaped verb against a base whose queue state it never
  checks; on a repository with no configured merge queue the callee refuses it (`_github_pr.py:1894`)
  and the landing cycle documents no remedy.
- **Task:** re-derive the caller enumeration across the whole bundle (not only the finalize
  lifecycle), correct it in a follow-up record, and decide the steward path explicitly: either route
  it on the same `use_merge_queue` signal the finalize step uses, or document that the steward
  requires a provisioned queue and state what the operator does when the refusal fires.
- **Done when:** every documented dispatcher of a merge-shaped `ci pr` verb is listed with the verb it
  actually issues, verified against the dispatch line in each file; and `landing-cycle.md` either
  routes or states its precondition and the remedy for the refusal.
- **Suggested grouping:** marshall-steward / landing cycle

## G4 — Finalize `report-01.md`: the outcome, the build-gate footprint, and the landing record

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `report-01.md` header (`**Outcome:** _in progress_`), § Build gate ("No production source
  was changed by this plan" and the footprint stated as "two test files"), § Contract check Step 8
  ("Landing recorded to the operator (see below)").
- **Evidence:** `git show ff11803b --name-status` lists
  `M marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`
  (+12/−1) and `M test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py` (+4)
  alongside the two new test files — four Python paths, one of them production, and the report's own
  F3 describes making that production change. `git log --oneline -- <plan dir>` returns `ff11803b`
  alone, so the report was never amended; the promised finalization commit and the promised landing
  record do not exist. The lane contract in force at the time
  (`git show ff11803b:.claude/skills/cloud-plan-lane/SKILL.md:844`) admits only
  `completed | partial | blocked` for `Outcome`.
- **Impact:** an unfinalized report reads as an abandoned run, and its Build-gate section states the
  opposite of the diff it shipped with. The reviewer verdicts stated for the final head are
  predictions ("their expected verdicts are unchanged"), which the contract's "A claim is not an
  outcome" rule forbids.
- **Task:** amend `report-01.md`: set `Outcome`, correct § Build gate to name all four changed Python
  paths and to state that one production file (`gitlab_ops.py`, the F3 refusal-parity fix) was changed,
  replace the dangling "see below" with the actual landing record, and replace the predicted reviewer
  verdicts with what the surfaces actually held at merge (or state plainly that they were not re-read).
- **Done when:** `report-01.md` carries a contract-legal `Outcome`, no statement in it contradicts
  `git show ff11803b --name-status`, and no forward-looking prediction is presented as an observation.
- **Suggested grouping:** review-apparatus / run-report hygiene

## G5 — Correct the refuted falsifiability argument in the report's residue

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `report-01.md` § D3 (the "Cross-provider / cross-verb reach" bullet for
  `refuse_unconfigured`) and § Residue (second item).
- **Evidence:** the claim is *"dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s
  off-routing test"*. Deleting the `if _is_auth_scope_error(stderr_text) or 'http 404' in stderr_text.lower():`
  block at `gitlab_ops.py:713` leaves `return make_error('pr_merge_queue', f'Failed to enqueue MR {iid} onto the merge train', stderr_text)`
  at line 720; `make_error` (`ci_base.py:783`) always sets `status: 'error'`; the off-routing arm
  asserts only `status == 'error'` (`test_merge_shaped_offrouting_refusal.py:325`). The arm stays
  green. The pre-existing `test_cmd_pr_merge_queue_generic_error_is_not_ineligible`
  (`test_gitlab_merge_queue.py:100`) demonstrates the same fallback path returning `status: error`.
- **Impact:** the one member whose falsifiability was argued rather than measured has an argument that
  is wrong, so the suite's discrimination on that member is unestablished in both directions.
- **Task:** correct the two passages to state that the arm is not falsifiable as written, and fold the
  remedy into G2. Do not restate the structural argument.
- **Done when:** neither passage asserts a mutation that would not flip the named test.
- **Suggested grouping:** review-apparatus / run-report hygiene

## G6 — Record a departure record for the sanctioned exception, or at the router

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:1592-1645`
  (`cmd_pr_auto_merge`), `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py:2080-2137`
  (`cmd_pr_auto_merge`), and `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:1978`
  (`dispatch`).
- **Evidence:** D2's *Done when* is "a departure from a documented route emits a record naming the
  route, the expected branch, and the verb actually dispatched". An off-routing `ci pr auto-merge` —
  a verb `branch-cleanup.md` § "The dispatch set is CLOSED" marks **never** reachable — returns
  `status: success` with `disposition: enqueued` and no mention of any route. `ci_base.dispatch`
  contains no logging of the key it routed on (read in full at lines 1978-2020).
- **Impact:** the plan's sanctioned exception is the one member whose off-routing dispatch is both
  permitted and unrecorded, so the next departure through it is as unexplainable as the incident that
  produced the plan — which is exactly what D2 exists to prevent.
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

## G7 — Carry the new GitLab refusal remedy into its three doc consumers

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md`
  § "The enqueue is corroborated" (the GitLab bullet, immediately after the GitHub one) and line 378;
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/gitlab-impl.md:120-127`.
- **Evidence:** the GitHub bullet spells the remedy out — *"it returns `status: error` naming both
  remedies — run `/marshall-steward` → Configuration → Merge Queue to provision the queue, or disable
  the plan's `use_merge_queue` step param to merge immediately via `ci pr safe-merge`"* — while the
  GitLab bullet beneath it says only *"a failure surfaces as the actionable ineligible error"*, and
  line 378 only *"with the actionable ineligible message"*. `gitlab-impl.md` says *"its 403/404 is the
  refusal"* and names no alternative verb. The shipped GitLab message now names `ci pr safe-merge`
  (`gitlab_ops.py:713-720`). Found via
  `grep -rn "pr safe-merge|pr merge-queue|pr auto-merge|ci pr merge" marketplace/bundles/ --include=*.md -l`,
  then reading every hit.
- **Impact:** the boundary-not-wall property the F3 fix established is invisible to a reader of the
  contract docs, and a future edit could remove it from the code without any doc disagreeing.
- **Task:** add the routed-verb remedy to the GitLab bullet and to line 378 in `pr-operations.md`, and
  to the merge-train paragraph in `gitlab-impl.md`, in the same shape as the GitHub bullet.
- **Done when:** all three passages state that the GitLab ineligible refusal names `ci pr safe-merge`
  as the alternative routed verb.
- **Suggested grouping:** tools-integration-ci / provider contract docs

## G8 — Make the derived population independent of a hand-listed verb vocabulary

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `test/_shared/_merge_shaped_roster.py:43` (`MERGE_SHAPED_VERBS`) and its twin
  `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:153`
  (`_MERGE_SHAPED_VERBS`) — the two frozensets are identical.
- **Evidence:** `merge_shaped_keys` (`_merge_shaped_roster.py:97-107`) filters registry keys by
  `key[1] in MERGE_SHAPED_VERBS`, so a merge-shaped verb registered under any other name is not in
  the derived population at all. The size assertion at
  `test_merge_shaped_offrouting_refusal.py:270` (`verbs_by_provider.get(provider) == set(MERGE_SHAPED_VERBS)`)
  detects a member disappearing, never a new one appearing under a new name.
- **Impact:** the plan forbade hand-listing the verb sets ("a hand-maintained list of the sites that
  need guarding is the same defect in a new place"); the derivation is registry-driven for
  *membership* but hand-listed for *vocabulary*, so "population-complete" means complete over four
  pre-named verbs. Inherited from the reference implementation, so this is a residual rather than a
  regression.
- **Task:** add a secondary derivation that flags any `('pr', verb)` registry key whose handler body
  reaches the platform queue/train symbol vocabulary (the predicate
  `test_branch_cleanup_merge_queue_routing.py:_first_queue_symbol` already implements) but whose verb
  is outside `MERGE_SHAPED_VERBS` — a "merge-shaped by behaviour, not by name" detector that fails
  loudly and names the verb.
- **Done when:** registering a queue-guarded `('pr','queue-merge')` handler in either provider fails a
  test naming it, rather than being silently filtered out of the population.
- **Suggested grouping:** tools-integration-ci / population derivation

## G9 — Consolidate the first-instance source guard onto the shared roster helper

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:219, 223,
  476, 496, 511` versus `test/_shared/_merge_shaped_roster.py:54, 57, 76, 84, 97`.
- **Evidence:** the source guard still defines `_HANDLER_MAP_RE`, `_HANDLER_ROW_RE`, `_registry_keys`,
  `_registry_handler_names` and `_merge_shaped_registry_keys` itself; the regexes are character-for-character
  identical to the helper's. `grep -rn "_merge_shaped_roster"` across `*.py` finds exactly one importer
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

## G10 — Publish the population size in a passing run's output, or drop the claim

- **Severity:** minor
- **Kind:** omission
- **Where:** `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py:246-274`;
  the same shape at `test_branch_cleanup_merge_queue_routing.py:642`
  (`test_registry_populations_are_published_and_plausible`).
- **Evidence:** the size reaches only the `assert … , (f'…{size}…')` failure messages.
  `grep -rn "print("` over both new files returns nothing and `test/conftest.py` defines no
  `pytest_terminal_summary` / `pytest_report_header` hook, so the observed output of a green run is
  `..................  [100%]` / `18 passed`. The plan's D3 *Done when* is "the population size appears
  in the test's own output"; `report-01.md` § D3 asserts it does.
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

## G11 — Assert the routed-verb remedy on the 404 arm as well as the 403 arm

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py:66-85`
  (`test_cmd_pr_merge_queue_ineligible_on_403`, which carries the `safe-merge` assertion) versus
  `:88-97` (`test_cmd_pr_merge_queue_ineligible_on_404`, which asserts only `status` and `operation`).
- **Evidence:** both stubs drive the same branch at `gitlab_ops.py:713`, but only the 403 test locks
  the message content. Read both test bodies in full.
- **Impact:** the 404 condition is the one the plan's own scenario model treats as the off-routing
  signature, and it is the arm with no message lock. Low practical risk while both conditions share a
  branch; it becomes real the moment they diverge.
- **Task:** add the `'merge train' in message` and `'safe-merge' in message` assertions to the 404
  test, matching its 403 sibling.
- **Done when:** both ineligible tests assert the message names the merge train and `safe-merge`.
- **Suggested grouping:** workflow-integration-gitlab / merge-shaped verb guards
