# PLAN-LB-107: The merge gate accepts what the finalize dispatcher accepted, and the push gate reads a build's real scope

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-107-finalize-gate-waiver-and-step-truth.md` and is queued as one row file, `queue/PLAN-LB-107.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's instruction of 2026-11-02 ("stage the corresponding plans, aggregate where sensible") from three
> consumer-repo findings that asked for residual checks:
> - lessons-routing-060 (TokenSheriff and API-Sheriff);
> - lessons-routing-068 (API-Sheriff);
> - lessons-routing-058 items 2 and 4 (API-Sheriff).
>
> Each was checked against `main` at 0fb6a79b1. What is still open is staged here. What is already fixed is recorded under Claim
> Labels and is not staged.

## Objective

Before it merges, `pre_merge_gate merge` refuses with `merge_candidate_not_gated` whenever a finalize step record carries a
`head_at_completion` that differs from the merge candidate. The gate decides which steps count by a different rule from the
finalize dispatcher, and it ignores the operator's re-fire waiver that the dispatcher honours. So a waiver that `loop-back close`
accepted, and that the dispatcher acted on, is refused again at merge, and the reviews it waived run again hours later.

This plan makes the merge gate accept exactly the records the dispatcher's re-entry table accepts. It also publishes the
barrier's override option labels, so the operator prompt is built from the labels the grant verb accepts.

Two more fixes ship with it:
- The pre-push freshness check counts a build row as whole-tree only when the row's recorded scope really is whole-tree.
- A cheap guard keeps the producer names in `ci-verify.md` inside the set that `verification-feedback` accepts.

## Deliverables

1. **The merge gate honours the operator's re-fire waiver at the candidate head.**
   - In `_head_binding_refusal`, a record whose `refire_waiver.head` equals the merge candidate is not counted as an offending
     step. The comparison is full-SHA equality, the same one the dispatcher's waiver row uses. A waiver that is absent,
     malformed or at any other SHA is void, and the record is checked as it is today.
   - The dispatched payload names each step that passed on a waiver, with its waiver head and `basis`, so that `record-merge`
     and the reader can tell a waived step from one that was validated.
   - `branch-cleanup.md`, in the `merge_candidate_not_gated` disposition, states that the gate honours a waiver only at the
     waiver's own head. The existing sentence stays: a merge authorization does not cover a tree the gates did not see.

   *Done when:* tests in `test_lb55_merge_head_binding.py` cover four cases:
   - (a) A record at head A with `refire_waiver.head` equal to candidate B dispatches, and the payload names the waived step and
     its basis. Red at HEAD.
   - (b) A matched control, the same record with `refire_waiver.head = C != B`, refuses and names the step.
   - (c) A malformed waiver refuses: no `head`, an abbreviated SHA, or a value that is not a dict.
   - (d) A waiver on one step does not admit a second stale step that has no waiver.

2. **The gate takes head-dependence from the same source as the dispatcher's skip rule.**
   - Today the two decide head-dependence differently:
     - The dispatcher decides that a step is head-dependent from its declared `head_dependent: true` frontmatter
       (`phase-6-finalize/SKILL.md` L605).
     - The gate decides it from whether `head_at_completion` is present on the record (`pre_merge_gate.py` L280-285).

     The gate moves to the declared fact. It reads it through the same discovery path that `mark-step-done` uses
     (`_derive_head_dependence`), so no second frontmatter parser is added.
   - A step that declares no head-dependence but carries a SHA on its record is never refused. It is listed in a payload field
     that does not refuse (for example `unconsulted_stamps`). The dispatcher never re-fires such a step, so the remedy "re-run
     those steps" could never clear it. That is the shape of the PLAN-02 `finalize-step-sync-baseline` case.
   - When the declaration cannot be derived, the gate falls back to field presence (fail-closed) and says so in the payload. A
     declaration that cannot be derived never widens what is admitted.
   - For a declared step whose head differs and which has no waiver for this head, the gate asks the same verdict-currency
     classifier the dispatcher asks (`verdict_currency classify`). `preserved` is accepted; `invalidated` and every uncertain
     answer refuse. The offending set then equals the set of steps the dispatcher would re-fire, so the remedy text of the
     refusal is true.

   *Done when:*
   - (a) A record of an undeclared step with a stale SHA, and no stale declared step, dispatches and lists the undeclared
     stamp. Red at HEAD.
   - (b) A matched control, a declared step with the same stale SHA, refuses.
   - (c) When discovery fails, a stale SHA is refused and the payload names the fallback.
   - (d) A classifier stub that answers `preserved` admits the record and one that answers `invalidated` refuses it. The
     classifier is reached through the same executor seam the module already uses for every other verb.

3. **The operator prompt is built from the labels the grant accepts.**
   - The `merge_participation_unproven` refusal from `pre_merge_gate merge` carries the override option labels for the gap it
     reports (for example in an `override_options` field). The labels come from the one constant that
     `merge-authorization grant` validates against (`BARRIER_OVERRIDE_LABELS`), never from a copy of it.
   - `branch-cleanup.md` § Pre-Merge Review-Completeness Barrier (the ask arm and the structural prompt) tells the agent to take
     the `AskUserQuestion` option labels verbatim from that field and never to paraphrase them. The grant's refusal of anything
     but an exact label is unchanged.

   *Done when:*
   - (a) A test in `test_pre_merge_gate.py` shows the participation refusal carrying both labels, read from the constant. Red
     at HEAD.
   - (b) A doc-sync test asserts that every override label named in the branch-cleanup barrier text and in the item-7a hook of
     phase-6-finalize is a member of the constant. The test reads `phase-6-finalize/SKILL.md` and does not edit it. A label that
     has drifted fails the test.

4. **A build row counts as whole-tree only when its recorded scope is whole-tree.**
   - `parse_row_scope` (`_freshness_crosscheck.py` L568-576) stops collecting scope at the first flag after the canonical
     command. A narrowing expressed as a flag inside `--command-args` is therefore read as no scope, which means whole-tree.
   - A known scope-bearing flag is read as scope. At minimum this is Maven's `-pl` / `--projects` value. The outline enumerates
     the flags that each build skill's resolved executables actually carry.
   - Any other flag after the canonical command makes the row's scope unreadable, through `args_carry_no_command_args` or a new
     sibling token. Such a row contributes no coverage, and it is never reported or credited as whole-tree.
   - Wherever the gate's `row_scopes` evidence labels a row's scope, it says whole-tree only for a row with no scope tokens and
     no trailing flag.

   *Done when:* tests in `test_freshness_notation_crosscheck.py` cover three cases:
   - (a) `--command-args module-tests -pl mod-a` parses to scope `mod-a` and is too narrow for a change that needs the whole
     tree. Red at HEAD.
   - (b) `--command-args module-tests -k foo` (an unknown flag) contributes no coverage and is not labelled whole-tree. Red at
     HEAD.
   - (c) A matched control, `--command-args module-tests`, is still whole-tree and adequate.

   The PR also records the resolved Maven `module-tests` executable for one module of a Maven fixture, showing where its scope
   sits in `--command-args`.

5. **Guard: every producer that `ci-verify.md` names is one that `verification-feedback` accepts.**
   - A doc-side guard next to the existing code-side sweep. It parses the producer values named in
     `phase-6-finalize/standards/ci-verify.md` and asserts that each is in the single accept-set parsed from
     `verification-feedback.md`.
   - The sweep must find at least one producer name, so the guard cannot pass vacuously.

   *Done when:* the guard is green at HEAD, where the doc names only accepted producers, and a mutated copy that names
   `ci-verify-policy` turns it red.

Split guard: five deliverables on one theme, that a finalize gate's verdict agrees with the record it reads. D1-D3 are the merge
path, D4 is the push path, and D5 is a guard test only.

## Standing Constraints

- **Do not loosen `merge_candidate_not_gated` beyond the dispatcher's own SKIP rows.** A waiver counts only at its exact head. A
  merge authorization of any `merge_authorizations` kind still never admits a tree the gates did not see.
- **Leave the waiver and the re-entry table alone.** Do not change the waiver's write shape (`{head, basis}`), `loop-back close`,
  or the dispatcher's re-entry table in `phase-6-finalize/SKILL.md`. The gate adopts the table; it does not restate or edit it.
- **Do not relax the exact-label check in `merge-authorization grant`** (PLAN-LB-55 D4). Operator answers get no fuzzy matching:
  the fix is to publish the labels, not to accept paraphrases.
- **Keep the freshness module's split fail-direction.** A refutation fails closed; an inability passes, with the inability
  recorded. Do not add `command` as a scope fallback, which the module docstring L175-183 refuses. Do not change
  `required_coverage`.
- **Keep the gate's new reads inside the existing seams.** Head-dependence discovery and the classifier go through the module's
  existing seams and stay bounded by `_VERB_TIMEOUT_SECONDS`, because they run while the merge mutex is held.
- **Every new test states what it protects**, carries a matched control, and is shown red at HEAD where the deliverable says so.
- **Builds go through the resolved executor** and route through the build server by default, as the runbook lane requires.
- **Sonar is not enabled for this project and is ignored:** collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: the merge gate decides which steps count by whether `head_at_completion` is present, compares with strict SHA
  equality, and never reads `refire_waiver`. Read at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` L271-332 § `_head_binding_refusal`
  (membership L280-285, loop L305-315, message L326-331). `architecture search --content --pattern refire_waiver` returns only
  `manage-status` (`_cmd_loop_back.py`, `_cmd_mark_step.py`, `manage-status.py`, SKILL.md), `phase-6-finalize/SKILL.md` and two
  `manage-status` tests (files_scanned 3686, truncated false, unreadable 0).
- OBSERVED: the dispatcher decides head-dependence from the declared frontmatter fact. It skips a record whose SHA differs when
  there is a waiver at the live HEAD, or when the classifier's verdict is `preserved`, and in both cases it keeps the original
  SHA. Read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` L605 (declaration), L607-615 (table),
  L619-632 (waiver: "record stays done at its original head_at_completion") and L643-644 (`preserved` → SKIP, do not re-stamp).
- OBSERVED: `loop-back close` stamps the waiver at the closing HEAD and requires a full SHA, and `mark-step-done` never writes the
  waiver. Read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` L45-55, L95-98 and
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` L131-136, L188-190 § `REFIRE_WAIVER_KEY`.
- OBSERVED: `mark-step-done` already derives `head_dependent` through the registry's discovery path. Read at `_cmd_mark_step.py`
  L56-64 and L193 § `_derive_head_dependence`.
- OBSERVED: the shipped head-binding tests have no waiver case and no undeclared-step case. Read at
  `test/plan-marshall/phase-6-finalize/test_lb55_merge_head_binding.py` L23-120.
- OBSERVED: `finalize-step-sync-baseline` declares no `head_dependent` fact and passes no `--head-at-completion` on any of its
  terminal calls at HEAD. Read at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md` L1-24 (frontmatter) and
  L272-301 (all three `mark-step-done` calls). The stale PLAN-02 stamp the consumer saw therefore did not come from the step doc
  at HEAD. What remains is the two-source mismatch that D2 removes.
- OBSERVED: the grant validates against one label constant and lists `accepted_options` only in its own refusal, after the fact.
  Nothing on the barrier side or the gate side publishes those labels. Read at
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_merge_authorization.py` L93-99 § `BARRIER_OVERRIDE_LABELS`
  and L155-172. `architecture search --content --pattern "accepted_options|BARRIER_OVERRIDE_LABELS|override_options"` finds only
  that file. The labels in `branch-cleanup.md` L133 are prose.
- OBSERVED: refusing the paraphrase "Accept gap and merge" is designed behaviour (PLAN-LB-55 D4), not a defect. Read at
  `test/plan-marshall/automatic-review/test_lb55_grant_and_review_policy.py` L57-82.
- OBSERVED: the freshness check reads scope only from the row's `args`. Empty scope tokens mean whole-tree, scope collection stops
  at the first flag token, and the test count is used only to refute a measured zero. Read at
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` L528-576 § `parse_row_scope` (the
  truncation at L568-573), L579-599 § `_measured_zero_tests`, L629-635 § `_row_refusal` and L651-652 § `_scope_adequate`.
- OBSERVED: PLAN-LB-58 (#1866) did not touch the freshness module. `git log -- _freshness_crosscheck.py` shows the last change at
  c8adaf178 (#1768).
- HYPOTHESIS: Maven executables scoped to a module carry `-pl {module}` inside `--command-args`, after the canonical command, so a
  narrow Maven row is read as whole-tree. This would match the API-Sheriff (Maven) sighting of 5 tests labelled whole-tree.
  Confirm or refute at `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` (the only script
  that matches `-pl \{`) and at the resolved `module-tests --module X` executable of one Maven fixture (verify-at-outline).
- HYPOTHESIS: the "whole-tree" label the consumer read is rendered from the empty scope tokens that `parse_row_scope` returns, in
  the gate's `row_scopes` evidence. Confirm at
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` (verify-at-outline).
- HYPOTHESIS: no shipped finalize step declares `verdict_inputs`, so today the `preserved` leg in D2 can be reached only by a test.
  `architecture search --content --pattern "verdict_inputs:"` finds only `verdict_currency.py` and one test. `.claude/**` is
  outside the inventory, and of it only `.claude/skills/finalize-step-plugin-doctor/SKILL.md` was read (no `verdict_inputs`).
  Confirm the frontmatter of the remaining `.claude/skills/finalize-step-*` (verify-at-outline).
- HYPOTHESIS: `pre_merge_gate.py` can reach `_derive_head_dependence` and `verdict_currency classify` through its existing
  executor and import seams, without a new coupling across skills. Confirm at `pre_merge_gate.py` L99-101 (imports) and
  § `_run_verb` (verify-at-outline).
- HYPOTHESIS: `manage-status/SKILL.md` § "Re-fire waiver" names only the dispatcher as the waiver's reader, and needs one sentence
  naming the merge gate. Confirm at `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` (verify-at-outline).
- OBSERVED (already fixed, not staged): lessons-routing-058 item 2. No document names `ci-verify-policy` or `ci-verify-cancelled`;
  `architecture search --content` finds them only in `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py`. The code-side
  producer sweep exists at `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py` L80-108 (PLAN-LB-44,
  #1848). D5 adds only the doc-side direction.
- OBSERVED (already fixed, not staged): lessons-routing-058 item 4.
  - `pre-submission-self-review` and the self-review surfacer apparatus were retired by 47d21e1bf (#1758), and no source names the
    step any more.
  - `branch-cleanup.md` matches no `./pw | pyprojectx | uv run` pattern.
  - `pre-push-quality-gate.md` L122-129 states that `./pw verify` is this repository's implementation, and that every arm obtains
    its invocation from `architecture resolve`.
- Verify-first clause (D1/D2): before editing, reproduce the API-Sheriff shape against the real gate with stubbed seams: a waiver
  at the candidate head on `functional-review` and on `finalize-step-simplify`, and no other stale step. If it dispatches at HEAD,
  the waiver is already honoured somewhere this spec missed; loop back and re-scope.
- Verify-first clause (D4): settle the Maven HYPOTHESIS first. If Maven scope is positional rather than a flag, the trigger is
  elsewhere; read the `args` shape of the consumer's row before writing the D4 parser change.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `_head_binding_refusal` (D1, D2), participation refusal payload (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — not-gated disposition wording (D1), barrier prompt labels (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_merge_authorization.py` — the label constant's single home (D3; read, edited only if the constant must move to a shared module)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — one sentence naming the merge gate as a waiver reader (D1; verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb55_merge_head_binding.py` — waiver and declaration cases (D1, D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` — published labels and doc-sync (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `parse_row_scope` (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — the row-scope label (D4; verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` — flag-scope cases (D4)
- OBSERVED: `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py` — doc-side producer guard (D5)

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-55 (#1856), PLAN-LB-100 (#1883) and PLAN-LB-101 (#1890) have shipped. This plan extends LB-55's
  head binding and LB-55 D4's grant, and reopens neither.
- **Overlaps with:**
  - PLAN-LB-46 (parked) declares `phase-6-finalize/standards/branch-cleanup.md` and `manage-status/SKILL.md`, both on this
    surface.
  - PLAN-LB-75 (parked) declares the directory `test/plan-marshall/phase-6-finalize/`, which contains
    `test_lb55_merge_head_binding.py` and `test_pre_merge_gate.py`.
  - If either parked plan is unparked before this plan runs, sequence this plan after it. No other parked plan (LB-41, 51, 57,
    69, 83, 84, 87, 89) declares a path on this surface.
  - Of the plans staged on 2026-11-02, PLAN-LB-105 also declares the directory `test/plan-marshall/phase-6-finalize/`, and
    PLAN-LB-109 declares `phase-6-finalize/SKILL.md`, which this plan reads but does not edit. The disjointness gate decides each
    pairing.
- **Adjacent to:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`: the dispatcher table the gate adopts. The D3 doc-sync
    test reads it, and it is not edited. Parked LB-41 and LB-87 declare it.
  - `_cmd_loop_back.py` and `_cmd_mark_step.py`: the waiver writer and the discovery path, both untouched.
  - `verdict_currency.py`: consulted, not changed.
  - The open question of whether a finalize step with no implementor records `done` rather than `skipped`. The step that raised
    it is retired (#1758), and `phase-6-finalize/SKILL.md` L632 records that `skipped` on a required step counts as incomplete.
    That is an epic watch, not this plan's deliverable.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-107-finalize-gate-waiver-and-step-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
