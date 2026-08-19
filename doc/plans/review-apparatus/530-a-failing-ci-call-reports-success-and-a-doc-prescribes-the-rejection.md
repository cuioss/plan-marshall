> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A failing `ci` call stops being readable as success, and the envelope contract stops prescribing an argparse rejection

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

The CI abstraction (`plan-marshall:tools-integration-ci:ci`, and the two provider front-ends behind
it) is the single channel through which every finalize step, every review barrier, and every
dispatched leaf talks to GitHub and GitLab. Three defects in that channel are live at HEAD. They are
independent in code and compounding in effect: the first makes a leaf compose an invocation the
parser rejects, the second makes a rejected or failed call indistinguishable from a successful one,
and the third makes a merge proceed without ever establishing the state it claims to have checked.

**One — the envelope contract prescribes an invocation ten `ci` subcommands reject.** The
`plan_id` row of the prompt-body contract in
`marketplace/bundles/plan-marshall/agents/execution-context.md` (the `| `plan_id` | Yes | …` table
row, near the top of § "Input — Prompt-Body Contract") tells every dispatched leaf that `ci`
"declares `--plan-id` as a **top-level/router flag consumed before the subcommand verb** (the `ci`
router reads it before `pr`/`checks`, so `--plan-id` goes **before** the verb — placing it after the
verb is an argparse rejection)". That is false for a large minority of `ci`'s verbs.
`ci_base.extract_routing_args` (in
`marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`) consumes and
strips a **pre-verb** `--plan-id` and passes a **post-verb** one through untouched, precisely so that
body-consumer subcommands can declare their own; `ci_base.add_body_consumer_args` declares
`--plan-id` with `required=True`, and `input_validation.add_plan_id_arg` (in
`tools-input-validation/scripts/input_validation.py`) does the same. Every subcommand built with
either helper therefore **requires** `--plan-id` after its verb, and a leaf that obeys the envelope
contract and moves the flag left of the verb gets exit 2. **Re-derive the affected subcommand set
from `ci_base.build_parser` and `ci_base.add_pr_create_args` — do not trust the figure ten below** —
but at authoring time the set was `pr create`, `pr edit`, `pr reply`, `pr thread-reply`,
`pr prepare-body`, `pr prepare-comment`, `issue create`, `issue comment`, `issue prepare-body`,
`issue prepare-comment`.

**Two — `ci` reports failure as `status: error` while exiting 0, and a finalize step marks itself
`done` from that.** `ci_base.output_error` prints `status: error` and returns `EXIT_SUCCESS`; its own
comment states the model outright ("Three-tier model: Exit 0 for expected errors (status:error in
TOON output)"). Both provider front-ends close `main()` with `result = dispatch(...)` /
`print(serialize_toon(result))` / `return 0` — no branch on `result['status']` —
in `workflow-integration-github/scripts/github_ops.py` and
`workflow-integration-gitlab/scripts/gitlab_ops.py`. Meanwhile the exit-code convention that governs
the finalize review-and-merge path keys on the exit code alone: its `exit_code == 0` clause says
"parse the returned TOON and use the value as the step describes". A failed `ci pr create` therefore
satisfies that clause. `phase-6-finalize/workflow/create-pr.md` § "Step 4: Create PR via CI
abstraction" states no positive shape requirement, reads `pr_number` off the return, logs
`Created PR #{pr_number}`, and records `mark-step-done --outcome done --display-detail "#{pr_number}"`
— with an absent `pr_number` that is a step marked `done` for a PR that does not exist, after which
finalize proceeds to review and merge against it.

**Three — GitLab's merge-train preflight fails open on an unresolvable project scope while its
docstring claims it fails closed like its GitHub sibling, which actually does.**
`gitlab_ops._probe_merge_train_state` returns
`(MERGE_QUEUE_INELIGIBLE, 'could not determine project path', None)` when `get_project_path()` is
empty. A `None` third element means "no error", so `gitlab_ops._refuse_on_required_merge_train` falls
through to `return None` and permits the immediate merge — a scope **resolution** failure folded into
a feature **availability** verdict. That preflight's docstring says "Fails closed: a probe error
(auth scope, transient API failure, malformed project response) refuses the merge rather than merging
blind, exactly as its GitHub sibling does." The sibling,
`workflow-integration-github/scripts/_github_pr.py::_resolve_base_queue_state`, returns
`make_error(operation, 'Could not determine repository owner/name for the merge-queue preflight')` on
exactly this class. GitLab is not even internally consistent: `gitlab_ops.cmd_pr_merge_queue` **does**
refuse an unresolvable project path. Separately, `cmd_pr_merge_queue` is the one merge-shaped verb
whose off-routing refusal arrives only *after* a side-effecting POST, because it never calls the
probe its four siblings call.

Around those three sit a set of smaller defects with the same shape: guards whose population is
hand-listed rather than derived, refusals that name no scope, tests that assert an outcome they
cannot fail on, and documented surfaces that contradict the parser or the registry they describe.

## Goal

Every `ci` invocation a dispatched leaf composes from the envelope contract parses against the real
parser; a `ci` return that is not `status: success` cannot be read as a usable value anywhere in the
finalize review-and-merge path; every merge-shaped verb on both providers establishes the queue/train
state before it acts and refuses with a message naming its scope and the routed alternative; and the
guards that assert those properties derive their population from the tree, fail for the reason they
name, and publish what they examined.

## Deliverables

Each deliverable is independently verifiable. Each names the gap ids it discharges — the detailed
evidence for every id, including the file:line and the reproduction, lives in the git-tracked
`gaps.md` files named under § Notes, which are on `main` and may be opened; this plan nonetheless
states everything the run needs without them.

0. **D0 — Derive the merge-shaped population by behaviour, or HALT** *(discharges 060-G10)* —
   `test/_shared/_merge_shaped_roster.py` derives **membership** from each provider's
   `handlers: HandlerMap` registry literal, but filters that membership against a **hand-listed
   vocabulary**, the module-level `MERGE_SHAPED_VERBS` frozenset (`{'merge', 'auto-merge',
   'safe-merge', 'merge-queue'}` at authoring time — **re-derive it, do not trust that literal**). A
   merge-shaped handler registered under any other verb name is filtered out of the population before
   any guard sees it, so "population-complete" means complete over four pre-named verbs. The previous
   plan's own failure was exactly a hand-maintained vocabulary; a hand-maintained fallback here would
   reproduce the defect inside the fix.

   Add a **secondary, behaviour-based derivation**: flag any `('pr', verb)` registry key whose handler
   body reaches the platform queue/train symbol vocabulary but whose verb is outside
   `MERGE_SHAPED_VERBS` — "merge-shaped by behaviour, not by name". The predicate already exists as
   `_first_queue_symbol` in
   `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py`; reuse it rather
   than writing a second one.

   ⛔ **This is a stop-condition deliverable.** If the behaviour-based population cannot be derived
   from the tree — the registry literal is unmatchable, the handler bodies are not resolvable to
   source text, or the queue-symbol predicate cannot be reused or reconstructed from what is in git —
   **HALT the plan, report exactly what could not be derived, and ship nothing that depends on it**
   (D3 and D4 both do). **Do not** author a hand-maintained verb list as a fallback: that is the
   defect this deliverable closes.
   *Done when:* registering a queue-guarded `('pr', 'queue-merge')` handler in either provider's
   registry literal fails a test that **names the verb**, instead of being silently filtered out of
   the population; and the derived population size is asserted from the derivation rather than from a
   transcribed literal.

1. **D1 — Make the envelope contract's `--plan-id` cell true for every `ci` subcommand**
   *(discharges 030-G1, the blocker)* — rewrite the parenthetical in the `plan_id` row of
   `marketplace/bundles/plan-marshall/agents/execution-context.md` § "Input — Prompt-Body Contract" so
   `ci` is presented as what it is: a router that consumes `--plan-id` **before** the verb only for
   the verbs that do not declare it themselves (the read verbs — `checks …`, `pr view`, `pr list`,
   `pr wait-for-comments`), while the body-consumer and prepare verbs declare a **required**
   `--plan-id` **after** the verb. Either name a different script as the pure before-the-verb
   exemplar, or state the split explicitly. Do not leave a blanket "placing it after the verb is an
   argparse rejection" attached to `ci`.

   Note for the run: the three doc sites that currently place `--plan-id` pre-verb
   (`tools-integration-ci/SKILL.md`, `ref-workflow-architecture/standards/dispatch-walkthrough.md`,
   `phase-6-finalize/workflow/sonar-roundtrip.md`) all name verbs that declare no `--plan-id` of their
   own, so no *authored* invocation is broken — **verify this before relying on it**. The exposure is
   the *runtime-composed* invocation a leaf builds from the contract.
   *Done when:* the cell contains no statement that is false for any `ci` subcommand; a cold read of
   it against `ci pr create` yields a **post-verb** `--plan-id` and a cold read against
   `ci checks pull-request-runs` yields a **pre-verb** one (see § Verification); and a test **derives**
   from `ci_base`'s own parser tree the set of subcommands declaring `--plan-id` and asserts the
   contract text does not contradict them — the derivation, never a transcribed list.

2. **D2 — Close the exit-0 hole in the exit-code convention, and give the finalize calls that depend
   on it a positive shape requirement** *(discharges 030-G3, 030-G2, 030-G4, 030-G6)* — four parts,
   one mechanism:

   - **The convention.** Add a third clause to each widened "Exit-code convention for every script
     call" section — at authoring time these were `automatic-review/SKILL.md`,
     `phase-6-finalize/SKILL.md`, and `phase-6-finalize/standards/branch-cleanup.md`; **re-derive the
     set by searching for the widened heading, do not trust the count three** — stating that an
     `exit_code == 0` return whose `status` is anything other than `success` is **not** a usable value
     and takes the `exit_code != 0` disposition. The three-tier model this covers is stated in
     `ci_base.output_error`'s own docstring.
   - **The live consequence.** Give `phase-6-finalize/workflow/create-pr.md` § "Step 4" the positive
     shape requirement the barrier already uses: the call is usable when and only when the return
     carries `status: success` **and** a non-empty `pr_number`; every other shape STOPS the step with
     an error TOON and never reaches `mark-step-done`. Do the same for the `pr prepare-body` /
     `pr edit` pair in `phase-6-finalize/standards/architecture-refresh.md`, and state the positive
     shape requirement at the `checks status` snapshot in `branch-cleanup.md` (a `status: error`
     return carries no `overall_status` at all, so it currently matches no branch).
   - **The missing doc.** `phase-6-finalize/standards/branch-cleanup-rereview.md` invokes
     `github_re_review re-review` and `github_pr fetch_findings` and carries **no** exit-code
     convention section at all (verify: it has one `## ` heading). Add the widened section, and add
     the doc to both `_INVOCATION_DOCS` and `_CONVENTION_DOCS` in
     `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py`.
   - **The rest of the phase.** Widen the heading in every `phase-6-finalize` doc whose derived
     invocation set contains a non-`manage-*` notation. The obligation is already derivable by that
     test's existing `_invoked_notations` / `_is_manage_star` helpers, so derive the list rather than
     transcribing one. **Re-derive the population** — at authoring time roughly twenty
     `manage-*`-scoped headings sat under `phase-6-finalize` against two widened ones, but the
     relevant subset is only those docs that actually invoke a non-`manage-*` script.

   ⛔ **No mid-run decision.** The alternative remedy — making both providers' `main()` return non-zero
   on `status: error` — is **out of scope** (see § Out of scope) and is **not** for this run to
   choose. Instead, **record it as a proposal** in the run report: what it would change, which call
   sites it would affect, and why it needs its own plan.
   *Done when:* each widened convention states a disposition for an exit-0 non-`success` return; no
   `--outcome done` branch in `create-pr.md` is reachable with an absent `pr_number`;
   `test_convention_is_widened_wherever_a_non_manage_star_script_is_invoked` runs and passes a case
   for `branch-cleanup-rereview.md`; the widening sweep over `phase-6-finalize` returns no doc that
   invokes a non-`manage-*` script under a narrow or absent convention (or the surviving exceptions
   are enumerated in the test with a per-doc reason, and the test fails when a new such doc appears);
   and a test derives the `ci`-verb invocations in `create-pr.md` and asserts each is followed by a
   `status`-branching disposition.

3. **D3 — Make GitLab's merge-shaped guards fail closed, probe before the side effect, and name their
   scope** *(discharges 060-G2, 060-G1, 060-G13, 060-G14, 060-G9)* —

   - **Fail closed on an unresolvable scope (060-G2).** Split the two verdicts
     `gitlab_ops._probe_merge_train_state` conflates: return an actionable error (a non-`None` third
     element) for the unresolvable-project-path case so `_refuse_on_required_merge_train` refuses,
     leaving `ineligible` with `error=None` for the genuine feature-absence verdicts (the missing
     `merge_trains_enabled` field and the two eligible outcomes). Correct the
     `_refuse_on_required_merge_train` docstring to enumerate what it actually refuses on, and drop or
     repair its "exactly as its GitHub sibling does" claim so it matches the branches that exist. Two
     members depend on this preflight — `pr merge` and `pr safe-merge`.
   - **Probe before the POST (060-G1).** Call `_probe_merge_train_state()` at the top of
     `gitlab_ops.cmd_pr_merge_queue`, before the merge-train POST. Refuse with `make_error(...)` when
     the discriminator is not `MERGE_QUEUE_ELIGIBLE_CONFIGURED`, mirroring the GitHub refusal's shape
     and naming both remedies (provision trains via `/marshall-steward` → Configuration → Merge Queue,
     or disable the plan's `use_merge_queue` step param and merge via `ci pr safe-merge`). Keep the
     existing 403/404 handling as the residual transport-level arm. The probe is read-only, so a
     refusal costs no side effect — that is the same ordering rationale already documented for the
     GitHub sibling.
   - **Name the scope (060-G13).** Pass the resolved project path into both GitLab refusal messages
     (or into their `detail`), in the shape the GitHub siblings use for the base branch. Do **not**
     invent a branch scope: a GitLab merge train is project-scoped, and a base-branch-scoped GitLab
     probe is explicitly rejected in `gitlab_ops.py`'s own § "Merge-shaped verb guards" comment block.
   - **Lock the 404 arm (060-G14).** `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py`
     asserts the routed-verb remedy on the 403 arm but not on the 404 arm, although both drive the
     same branch. Add the "merge train" and "safe-merge" message assertions to the 404 test.
   - **Move the contract docs with the code (060-G9).** Four passages state a no-probe posture and
     omit the routed-verb remedy: the corroboration table row and the two GitLab bullets in
     `tools-integration-ci/standards/pr-operations.md`, and the merge-train paragraph in
     `tools-integration-ci/standards/gitlab-impl.md`. Once the probe lands, the "**no probe**"
     statements are false and must be rewritten in the same change, and each passage must state that
     the GitLab ineligible refusal names `ci pr safe-merge` as the alternative routed verb — the shape
     the GitHub bullet directly above already uses.

   *Done when:* `_refuse_on_required_merge_train` returns an error dict when `get_project_path()` is
   empty, locked by a test that stubs it empty and asserts `cmd_pr_merge` returns `status: error` and
   issued no `mr merge` call; `cmd_pr_merge_queue` returns `status: error` on an off-routing dispatch
   **without** issuing the merge-train POST, proven by a test that stubs `_probe_merge_train_state` to
   `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED`, stubs `run_glab` to succeed, and asserts both the error and
   that `run_glab` captured no `api -X POST` call; both GitLab refusals name the project they apply
   to; both ineligible tests assert the message names the merge train and `safe-merge`; and no passage
   in the two standards docs describes a probe posture the code no longer has.

4. **D4 — Make the routing guards falsifiable, observable, and single-sourced**
   *(discharges 060-G3, 060-G8, 060-G11, 060-G12, 030-G9)* — four guards that pass for reasons they
   do not name:

   - **Discriminate a guard from a transport failure (060-G3).** In
     `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`, the
     `[gitlab:merge-queue]` off-routing arm **manufactures its own refusal**: the `run_glab` stub
     returns `HTTP 404` and the monkeypatched `_probe_merge_train_state` is never read by the handler.
     `ci_base.make_error` sets `status: 'error'` on every branch, so the handler's generic fallback
     satisfies the assertion just as well as the ineligible branch. Strengthen the arm: for the
     immediate-merge and enqueue members assert the refusal message names the correct alternative
     routed verb (`merge-queue` for the immediate verbs, `safe-merge` for the enqueue verb) rather
     than only `status: error`; and, after D3's probe lands, drive `[gitlab:merge-queue]` off-routing
     through the probe discriminator like every other member and assert **no POST was issued** — the
     `_captured` list is already returned by the test's `_dispatch` helper and currently discarded.
     That also removes the mirror tautology in `test_compliant_route_succeeds[gitlab:merge-queue]`,
     where the compliant run issues the identical POST.
   - **Record the sanctioned departure (060-G8).** An off-routing `ci pr auto-merge` — a verb
     `branch-cleanup.md` marks never reachable from the routed step — returns `status: success` with
     `disposition: enqueued` and no mention of any route; `ci_base.dispatch` logs nothing about the key
     it routed on. Have **both** `cmd_pr_auto_merge` handlers add an advisory field naming the routed
     alternative when the probe reports a configured queue/train — a `routing_note` stating that
     `ci pr merge-queue` is the routed verb for a queued base. **Do not turn the sanctioned exception
     into a refusal**: the compliant enqueue-via-auto-merge path must keep succeeding. The wider
     alternative — one structured record emitted in `ci_base.dispatch` for every merge-shaped key — is
     **out of scope**; record it as a proposal in the run report rather than choosing it mid-run.
   - **Single-source the source guard (060-G11).** `test_branch_cleanup_merge_queue_routing.py` still
     defines its own `_MERGE_SHAPED_VERBS`, `_HANDLER_MAP_RE`, `_HANDLER_ROW_RE` and registry-key
     helpers, character-for-character identical to `test/_shared/_merge_shaped_roster.py`'s, which
     calls itself "the designated single source" and has one importer. Replace the private copies with
     imports from the helper, keeping the source guard's own path resolution at the call site (it
     reads handler-source files; the helper takes text).
   - **Publish the populations (060-G12, 030-G9).** Three population guards carry their size only
     inside an assertion failure message, so a green run cannot be told from an empty one:
     `test_merge_shaped_offrouting_refusal.py`, `test_branch_cleanup_merge_queue_routing.py`
     (`test_registry_populations_are_published_and_plausible`), and
     `test_review_merge_invocation_contract.py` (`test_the_population_size_is_published`). Emit the
     size on a **passing** run, applied consistently to all three — a `pytest_report_header` entry in
     `test/conftest.py`, or a `print` an `-s` run surfaces; pick whichever the repository's existing
     test conventions already use and say which in the report. In the same pass, harden
     `test_review_merge_invocation_contract.py`'s derivation: make its floor derived rather than the
     literal `4` (or raise it to the true population), narrow the `if '[' in block: continue` skip so
     it excludes only the advertised `## Canonical invocations` forms rather than any block containing
     a `[`, and either assert one command per matched block or iterate every match in a block instead
     of only the first.

   *Done when:* neutralising `gitlab_ops.cmd_pr_merge_queue`'s off-routing refusal turns
   `test_offrouting_dispatch_is_refused_at_the_callee[gitlab:merge-queue]` **red** — measured by an
   actual mutation run whose result is recorded in the run report, not argued; an off-routing
   `pr auto-merge` on both providers emits a field naming the routed verb it departed from, locked by
   a test asserting that field's presence on the queued-base path and its absence (or its `enabled`
   form) on the unqueued one; `test_branch_cleanup_merge_queue_routing.py` imports its registry
   derivation from `_merge_shaped_roster` and defines no `handlers:\s*HandlerMap` regex of its own,
   with both suites green; each of the three population sizes is observable in a green run's output;
   and dropping one invocation from either merge-and-review population doc fails the size test rather
   than passing it.

5. **D5 — Reconcile every documented surface that contradicts the `ci` parser, registry, or dispatch
   sites** *(discharges 020-G13, 020-G12, 030-G7, 030-G10, 060-G4)* — five stale surfaces, one
   mechanism (a text asserting something the tree falsifies):

   - **Document `pr landing-state` (020-G13).** Three surfaces omit it. Add it to the
     `Sub-verbs:` enumeration under `### pr` in `tools-integration-ci/SKILL.md` § Canonical
     invocations, with a fenced canonical invocation; add a `pr landing-state` row to the PR
     Operations response-field table in `tools-integration-ci/standards/api-contract.md` naming its
     required/optional args and its response fields (which must match the dict
     `cmd_pr_landing_state` actually returns in `workflow-integration-github/scripts/_github_pr.py`);
     and add a `scripts/foreign_pr_gate.py` row to the Scripts inventory table in
     `phase-6-finalize/SKILL.md` — **re-derive the script count against a listing of
     `phase-6-finalize/scripts/`**, which at authoring time held one more script than the table held
     rows. Two surfaces are already correct and need no work:
     `tools-integration-ci/standards/leaf-command-reference.md` and
     `workflow-integration-github/SKILL.md` — confirm that before editing them. The § Canonical
     invocations preamble in `phase-6-finalize/SKILL.md` also omits the script, but it omits others
     too, so extending it is a separate whole-skill cleanup and is **out of scope** here.
   - **Extend the doc-parity test to `pr` verbs (020-G12).** `test/plan-marshall/tools-integration-ci/test_ci_base.py`
     derives the documented `checks` verb population from a table-row regex against
     `leaf-command-reference.md` and asserts parity with the registry; there is no equivalent for
     `pr`, so any future `pr` verb can be added with no documentation and no test failure. Mirror the
     `checks` parity check for `pr`: derive the registered sub-verbs from the provider handler map and
     assert each has a row in `leaf-command-reference.md` and in `api-contract.md`. `api-contract.md`
     splits `pr` verbs across two tables (read verbs and state transitions), so the assertion must
     accept either. Include a documented exemption list only if one is genuinely needed, and state the
     reason per entry.
   - **State the token FORM where a pair-form bot flag is rendered (030-G7).** Three sites render
     pair-form flags without saying which flags take pairs: the barrier's `review_completeness check`
     invocation and its surrounding prose in `phase-6-finalize/standards/branch-cleanup.md`, and the
     `review_completeness — check` and `— deficit` blocks in `automatic-review/SKILL.md` § Canonical
     invocations (which say only that all the list flags take an optional value). Add one sentence at
     the barrier invocation naming the pair-form flags and the bare-form remainder, mirroring the
     wording already used in the FIND step of `automatic-review/SKILL.md`, and add a form column or a
     one-line note to both canonical blocks. **Re-derive which flags are pair-form** from
     `review_completeness.py`'s parse routing — at authoring time four of nine were pair-form
     (`--participated-bots`, `--stale-participation-bots`, `--refused-causes`, `--refusal-size-caps`),
     but the module's own prose disagrees with its parser, and correcting that prose is **out of
     scope** here (see § Out of scope). Document the flags as the parser behaves, not as the module
     docstring describes them.
   - **Correct the now-false `--enabled-bots` claim (030-G10).** The module docstring and the class
     docstring in `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py`
     describe `--enabled-bots` as "a flag no script declares" / "a flag no parser declares".
     `automatic-review/scripts/review_gate_delta.py` now declares it on the `assess` subcommand, as
     the coverage denominator. Reword both passages to name the real invariant — a flag prescribed on
     a parser that does not declare it (`--enabled-bots` on `github_pr fetch_findings`) — and mention
     that `review_gate_delta assess` legitimately declares it.
   - **Re-derive the merge-shaped caller enumeration, and settle the steward path in text (060-G4).**
     `marshall-steward/references/landing-cycle.md` Step 5(c) dispatches
     `ci pr merge-queue --head {branch}` **unconditionally** — no `use_merge_queue` read, no routing
     branch, no fallback — so on a repository with no configured merge queue the callee refuses it and
     the landing cycle documents no remedy. Re-derive the enumeration of every documented dispatcher
     of a merge-shaped `ci pr` verb across the whole bundle, not only the finalize lifecycle.
     ⚠ **A single contiguous search is not sufficient**: the two dispatch lines in
     `phase-6-finalize/standards/branch-cleanup.md` interpose `--project-dir {worktree_path}` between
     the script notation and the noun, so a search for `tools-integration-ci:ci pr merge-queue` misses
     them. Union that search with a search for the bare notation `tools-integration-ci` over
     `branch-cleanup.md`, plus a `*.py` sweep of `marketplace/` and `.claude/`.
     ⛔ **No mid-run decision.** Do **not** change the steward's routing. Do the deterministic half:
     state the precondition in `landing-cycle.md` (the step requires a provisioned merge queue) and
     name what the operator does when the refusal fires. **Record as a proposal** in the run report
     the alternative — routing the steward path on the same `use_merge_queue` signal the finalize step
     uses — with what it would touch.

   *Done when:* the three `landing-state` surfaces name the verb/script and the response-field row
   matches the dict the handler returns; the new `pr` parity test fails if a `pr` sub-verb is
   registered without a documentation row and passes on the tree; each of the three bot-flag sites
   states in its own text which list flags take `bot_kind:value` pairs and which take bare tokens;
   neither `test_review_merge_invocation_contract.py` docstring passage asserts anything falsifiable
   by searching the tree for `--enabled-bots`; and every documented dispatcher of a merge-shaped
   `ci pr` verb is listed in the run report with the verb it actually issues, verified against the
   dispatch line in each file, with `landing-cycle.md` stating its precondition and the remedy for the
   refusal.

## Out of scope

Each exclusion states why, because with no operator watching the run, this written boundary is the
only thing that stops mid-run drift.

- **Making the provider front-ends' `main()` return non-zero on `status: error`.** This is the wider,
  arguably better remedy for defect two, but its blast radius is every `ci` caller in the tree —
  including the several sites that legitimately read a non-`success` return as a signal (a `pr view`
  that reports no PR exists, `manage-files exists` style probes). Changing it inside this plan would
  make an unbounded set of steps start STOPping where they currently proceed. D2 records it as a
  proposal instead.
- **`review_completeness.py`'s own flag-parsing behaviour and its module prose** (the silent drop of a
  non-registry-admissible `--stale-participation-bots` pair, and the two-FORM docstring that is false
  for two of its nine list flags). These are defects in that module's parser and its own reference
  text, a different mechanism from the CI abstraction's dispatch and exit-code contract. Only the
  *documentation of the flag forms at the invocation sites* is in scope, in D5. Fixing the module's
  prose while leaving its parser unchanged would put a third description of the same split into the
  tree.
- **The pre-archive foreign-PR landing gate itself** — its fail-open on an unclassified population,
  the missing `--branch`, the `unpushed` disposition, the read-intent population question, its
  subprocess timeouts and seam coverage. The gate is a *consumer* of `ci pr landing-state`; this plan
  touches only the *documentation* of that verb and of the gate script (D5). Pulling the gate's own
  logic in would double the plan's surface and mix two review cycles.
- **Implementing `pr landing-state` on the GitLab provider.** The verb is GitHub-only by
  registration; adding it means a new GitLab API surface and its own corroboration design, which is a
  provider-parity plan rather than a documentation reconciliation.
- **Widening the exit-code convention outside `phase-6-finalize` and `automatic-review`.** The narrow
  `manage-*`-scoped heading appears on the order of forty times across the bundle tree — **re-derive
  that figure if it matters** — and most of those documents are other phases and steps. A tree-wide
  sweep is a mechanical but large change that would swamp the review of the defects above. D2's
  boundary is the finalize review-and-merge path, which is where the swallowed failures were observed.
- **Emitting a structured routing record for every merge-shaped key in `ci_base.dispatch`.** This is
  the broader alternative to D4's per-handler `routing_note`; it changes the return shape of every
  dispatched `ci` call and therefore needs its own compatibility review. D4 records it as a proposal.
- **Run-report corrections for the already-landed `review-apparatus` plans** (outcome fields, build-gate
  footprints, reviewer-verdict and falsifiability claims, test-count labelling). Those are records of
  past executions, not defects in the CI abstraction; correcting them belongs to a record-hygiene plan
  that can touch several plan directories at once without entangling a code change.
- **Extending the `## Canonical invocations` preamble in `phase-6-finalize/SKILL.md`.** It omits
  several scripts, not just the one D5 adds a table row for, so completing it is a whole-skill cleanup
  with its own population to derive.

## Expected surface

- `marketplace/bundles/plan-marshall/agents/execution-context.md` — D1: the `plan_id` row of the
  prompt-body contract.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` — D3:
  `_probe_merge_train_state`, `_refuse_on_required_merge_train`, `cmd_pr_merge_queue`,
  `cmd_pr_auto_merge` (D4's `routing_note`).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — D4:
  `cmd_pr_auto_merge`'s `routing_note`. Read-only for D3 (the fail-closed sibling) and D5 (the
  `cmd_pr_landing_state` return shape).
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md`,
  `standards/api-contract.md`, `standards/pr-operations.md`, `standards/gitlab-impl.md` — D3 and D5:
  the provider-contract passages and the `pr` sub-verb surface.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`,
  `workflow/create-pr.md`, `standards/branch-cleanup.md`, `standards/branch-cleanup-rereview.md`,
  `standards/architecture-refresh.md`, and the other `phase-6-finalize` docs whose derived invocation
  set contains a non-`manage-*` notation — D2 and D5.
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — D2 (the widened convention)
  and D5 (the two canonical blocks).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md` — D5: the
  Step 5(c) precondition and remedy.
- `test/_shared/_merge_shaped_roster.py` — D0: the behaviour-based secondary derivation.
- `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`,
  `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py`,
  `test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py`,
  `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py`,
  `test/plan-marshall/tools-integration-ci/test_ci_base.py`, and possibly `test/conftest.py` — D0,
  D2, D3, D4, D5.

`marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` and both provider
`main()` functions are **read** (D1's derivation, D2's evidence) and deliberately **not** edited —
see § Out of scope.

## Claim labels

Every premise below was settled by reading the named file at the commit this plan was authored
against. **Re-derive each one before building on it**: the clone the run executes in is not guaranteed
to match the tree the author read, and a fixed defect that this plan still describes must be **dropped
and its absence reported**, not implemented around.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The envelope contract's `plan_id` row states that placing `--plan-id` after a `ci` verb is an argparse rejection | OBSERVED | `marketplace/bundles/plan-marshall/agents/execution-context.md`, the `\| `plan_id` \| Yes \|` table row |
| `ci_base.add_body_consumer_args` and `input_validation.add_plan_id_arg` declare `--plan-id` with `required=True`, and `ci_base.build_parser` applies one of them to ten `pr`/`issue` subcommands | OBSERVED | `tools-integration-ci/scripts/ci_base.py` (`add_body_consumer_args`, `build_parser`, `add_pr_create_args`); `tools-input-validation/scripts/input_validation.py` (`add_plan_id_arg`) — **re-derive the set; ten is a lead** |
| `extract_routing_args` consumes a pre-verb `--plan-id` and passes a post-verb one through | OBSERVED | `ci_base.extract_routing_args` docstring and body |
| `ci_base.output_error` prints `status: error` and returns `EXIT_SUCCESS` | OBSERVED | `ci_base.output_error` |
| Both provider front-ends `return 0` after `dispatch(...)` with no branch on `result['status']` | OBSERVED | `github_ops.main`, `gitlab_ops.main` (final three statements of each) |
| The three widened exit-code conventions key on `exit_code` alone and state no disposition for an exit-0 non-`success` return | OBSERVED | `automatic-review/SKILL.md`, `phase-6-finalize/SKILL.md`, `phase-6-finalize/standards/branch-cleanup.md` — § "Exit-code convention for every script call" in each. **Re-derive the set of widened docs** |
| `create-pr.md` § Step 4 states no positive shape requirement and reaches `mark-step-done --outcome done` with `pr_number` interpolated | OBSERVED | `phase-6-finalize/workflow/create-pr.md` § Step 4 and § Mark Step Complete, Branch A |
| `branch-cleanup-rereview.md` carries no exit-code convention while invoking two non-`manage-*` scripts | OBSERVED | The doc's single `## ` heading, and its `github_re_review re-review` / `github_pr fetch_findings` invocations |
| `_probe_merge_train_state` returns `error=None` on an unresolvable project path, and `_refuse_on_required_merge_train` therefore permits the merge | OBSERVED | `gitlab_ops.py` — the two function bodies, read end to end |
| The GitHub sibling fails closed on the same class | OBSERVED | `_github_pr._resolve_base_queue_state` — the `if not owner or not repo:` arm returning `make_error` |
| `cmd_pr_merge_queue` issues the merge-train POST with no prior state read | OBSERVED | `gitlab_ops.cmd_pr_merge_queue` — no `_probe_merge_train_state` call between `_resolve_mr_iid` and `run_glab(['api', '-X', 'POST', …])` |
| A project with `merge_trains_enabled: false` whose merge-train endpoint answers 2xx would yield `enqueued: true` for an MR that joined no train | HYPOTHESIS | Nobody in this repository has produced this false green. Confirm/refute by reading `cmd_pr_merge_queue`'s post-POST block: `enqueued: true` is derived from `returncode == 0` alone and the car read-back swallows a `json.JSONDecodeError`. The plan does not depend on this being reproducible — D3 closes the guard regardless |
| `MERGE_SHAPED_VERBS` is a hand-listed frozenset the derivation filters against | OBSERVED | `test/_shared/_merge_shaped_roster.py`, module-level constant and `merge_shaped_keys` |
| The `[gitlab:merge-queue]` off-routing arm manufactures its refusal via the `run_glab` stub and asserts only `status == 'error'` | OBSERVED | `test_merge_shaped_offrouting_refusal.py` — `_gl_run_stub`, the `mt_post_ok` expression in `_dispatch`, and the `else` branch of `test_offrouting_dispatch_is_refused_at_the_callee` |
| Neutralising `cmd_pr_merge_queue`'s ineligible branch leaves that suite green | HYPOTHESIS | Previously measured, not re-measured for this plan. Confirm/refute by the mutation run D4's *Done when* requires; if it turns out already red, drop that half of D4 and report it |
| `ci_base.dispatch` records nothing about the key it routed on | OBSERVED | `ci_base.dispatch`, read in full |
| `test_branch_cleanup_merge_queue_routing.py` carries private copies of the roster helper's regexes and derivation | OBSERVED | `_MERGE_SHAPED_VERBS`, `_HANDLER_MAP_RE`, `_HANDLER_ROW_RE` in that file versus `test/_shared/_merge_shaped_roster.py` |
| None of the three population guards emits its size on a passing run | OBSERVED | No `print` / `record_property` / `pytest_report_header` / `pytest_terminal_summary` in the three test files or in `test/conftest.py` (its only prints are executor-bootstrap warnings) |
| `landing-cycle.md` Step 5(c) dispatches `ci pr merge-queue` unconditionally | OBSERVED | `marshall-steward/references/landing-cycle.md` § Step 5(c) |
| `pr landing-state` is absent from `tools-integration-ci/SKILL.md`'s `pr` sub-verb list and from `api-contract.md`, and `foreign_pr_gate.py` is absent from the `phase-6-finalize` Scripts table | OBSERVED **(asserted absence — verify it exactly as a presence)** | The `Sub-verbs:` line under `### pr`; a search for `landing-state` in `api-contract.md`; a listing of `phase-6-finalize/scripts/` against the Scripts table rows |
| No test asserts documentation parity for `pr` sub-verbs | OBSERVED **(asserted absence)** | `test_ci_base.py` defines `_CHECKS_ROW` / `_documented_checks_verbs` and no `pr` equivalent — re-derive by searching the whole `test/` tree, not just that file |
| `review_gate_delta.py` declares `--enabled-bots` on its `assess` subcommand | OBSERVED | `automatic-review/scripts/review_gate_delta.py`, the `assess` subparser |
| No site in `branch-cleanup.md`'s barrier prose or `automatic-review/SKILL.md`'s canonical blocks states which list flags are pair-form | OBSERVED **(asserted absence)** | The barrier's `review_completeness check` fenced block and the prose beneath it; § Canonical invocations → `review_completeness — check` / `— deficit` |

## Verification

Beyond each deliverable's *Done when*:

1. **Cold read of the envelope-contract cell (D1) — required, and the check that matters most.** The
   `plan_id` cell's entire value is what it makes a *later* dispatched leaf do; "implemented as
   specified" cannot verify it, because the text can be present, well-formed, and still read the wrong
   way. Dispatch an independent reader (the lane contract's pre-PR verification sub-agent is the
   vehicle — see `cloud-plan-lane` § the verification step) that has **not** seen this plan or the
   diff, give it only the rewritten cell, and ask it to write out the exact command line it would
   compose for **(a)** `ci pr create` with a plan id, and **(b)** `ci checks pull-request-runs` with a
   plan id. Record both answers verbatim in the run report. The check passes only if (a) places
   `--plan-id` **after** `create` and (b) places it **before** `checks`. If either reading is wrong,
   the wording failed however complete it looks — rewrite and re-read cold. Do not paraphrase the
   reader's answer; quote it.
2. **Parse every rewritten invocation against the real parser.** Every fenced `ci` invocation this
   plan adds or edits must be run through `ci_base.build_parser` with its placeholders substituted,
   and must not exit 2. The existing invocation-contract suite already does this for its population;
   the newly added `branch-cleanup-rereview.md` and `create-pr.md` invocations must be inside that
   population by the end of the run.
3. **Full build.** `./pw verify` (the standalone lane's build gate — see `cloud-plan-lane` for when it
   is required). Record the green figure and the commit it belongs to; one figure per commit
   described, each labelled.
4. **Mutation evidence, not argument (D4).** The `[gitlab:merge-queue]` falsifiability claim is
   settled by an actual mutation run whose output is recorded. A structural argument is not a
   substitute — the previous plan made one, and it was wrong.
5. **Re-derive every count before stating it.** Each figure this plan mentions — the ten
   `--plan-id`-declaring subcommands, the widened-convention set, the `phase-6-finalize` doc
   populations, the merge-shaped member count, the `phase-6-finalize/scripts/` inventory — is a
   **lead**, not a fact. Re-derive it at the moment of the claim and report the derived value, noting
   any that differs from this plan.
6. **Report every dropped gap.** If a defect described here no longer reproduces at the run's HEAD,
   drop the corresponding work, and state in the run report which gap id was dropped and what was
   found instead. Do not implement around a defect that is already fixed.
7. **Proposals, not decisions.** Three items are authored as proposals the run **records** and does
   **not** decide: the provider `main()` exit-code change (D2), the `ci_base.dispatch` routing record
   (D4), and the steward-path routing signal (D5). The run report must carry all three, each naming
   what it would change and why it needs its own plan. Per `cloud-plan-lane`, a change to the contract
   that governs the run is never self-approved.

## Notes

- **Detailed evidence.** Every defect above is recorded, with its file:line, its reproduction and its
  original *done when*, in three git-tracked files on `main`, which the run **may** open:
  `doc/plans/review-apparatus/030-a-workflow-doc-prescribes-a-flag-no-script-declares/gaps.md`
  (entries G1, G2, G3, G4, G6, G7, G9, G10),
  `doc/plans/review-apparatus/060-a-prose-routing-table-is-not-an-enforcement-boundary/gaps.md`
  (G1, G2, G3, G4, G8, G9, G10, G11, G12, G13, G14), and
  `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/gaps.md`
  (G12, G13). The `verification.md` beside each carries the supporting analysis. This plan is written
  to stand on its own without them; they are corroboration, not required reading.
- **`.plan/` is all but invisible to this run.** The orchestrator ledger, the plan specs and the
  landing records live under `.plan/local/orchestrator/…`, which is git-ignored and therefore absent
  from the clone. **Do not go looking for any of them.** `.plan/` does carry two tracked exceptions
  (`.plan/marshal.json` and `.plan/project-architecture/`, per `.gitignore:45-47`) — re-derive that
  from `.gitignore` rather than trusting this sentence — but no deliverable here reads either, and
  none may be made to.
- **Gap ids not carried here.** The three source `gaps.md` files contain further entries that are
  deliberately **not** in this plan's scope: `030` G5, G8, G11; `060` G5, G6, G7; and `020` G1–G11 and
  G14–G19. Each is excluded for a reason stated in § Out of scope (bot-flag parsing, run-report
  hygiene, the foreign-PR landing gate, provider parity). They are not forgotten and must not be
  pulled in mid-run.
- **Ordering.** D0 gates D3 and D4 — both build on the derived merge-shaped population. D1, D2 and D5
  are independent of D0 and of each other and may proceed in any order. Within D3, the probe (060-G1)
  must land before D4's off-routing arm can be driven through the discriminator, and before the
  "no probe" passages in the two standards docs can be rewritten truthfully; the plan therefore
  requires both halves in the same change rather than leaving the docs behind the code.
- **Two normative surfaces currently disagree head-on** on `--plan-id` placement: the envelope
  contract on one side, and the canonical forms in `tools-integration-ci/standards/pr-operations.md`,
  `persona-plan-marshall-agent/standards/tool-usage-patterns.md` and
  `phase-6-finalize/workflow/create-pr.md` on the other. The canonical forms are the ones that match
  the parser. A reader with only the contract has no way to adjudicate — which is what makes D1 the
  blocker rather than a documentation tidy-up.
- **This plan edits `marketplace/bundles/`.** Per the standalone-lane carve-out in the repository's
  `CLAUDE.md`, a lane run neither performs a plugin-cache sync nor records one as owed: the merged
  bundle source is authoritative, and a local developer's cache is a local concern.
