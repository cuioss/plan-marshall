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

# Bring the test corpus under the module budget, one slice per run

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10**, the concurrency
> contract, and the `plugin-doctor` invocation this plan measures with. The landed skills are the
> authority where they and the README disagree.
>
> **Blocking dependency.** Plans `010` and `020` must have landed — confirm with
> `grep -n 'def parse_ns' test/conftest.py` and by reading the module-budget section of
> `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> For the `070` and `080` slices specifically, that plan must also have landed first, because its own
> fixture-consolidation deliverable changes which of its modules are over budget. The other four
> slices have no such dependency: their reduction plans have landed and their residue is unowned.

## Problem

**B1** — a test module is budgeted at 400 lines — is the epic's one structural rule with an enforced
detector behind it. Plan `010` landed `test-module-line-budget` at `severity: warning` over a tree
carrying **315** violations, and proposed flipping it to `error` once the count reached zero.

Four reduction plans then ran, and the count is **313**. That figure is a lead like any other and must
be re-derived, but the shape it describes is not in doubt: across the epic's entire executed half, the
budget moved by two modules. The two other rules those plans touched moved a great deal —
`test-module-preamble-boilerplate` roughly halved and `test-docstring-historical-prose` fell by about
two thirds — so this is not a story about runs that achieved nothing. It is a story about **one
deliverable that was never reached**, four times, for the same structural reason.

**The mechanism is the ordering.** Each of `030`–`060` placed its split deliverable last and said why:
splitting after the other deliverables is correct, because fixture hoisting and scaffold conversion
shrink modules and change which ones are over budget. That reasoning is sound and this plan does not
contradict it. What it did not account for is that a cloud run completes roughly two to three
deliverables, so a deliverable placed fifth is a deliverable that does not happen. The landed reports
say so in their own words — `030` *"D2 — not started"*, `040` *"D4 … was not started"*, `050`
*"**NOT DONE** … the deliverable that would have produced most of the line reduction"*, `060`
*"**53 modules remain over the 400-line budget. Nothing was split.**"*

**And the split was measured against the wrong thing.** Every reduction plan carried a percentage
line floor, and each one missed it by more than an order of magnitude. Splitting a module by behaviour
cluster is **line-neutral to slightly positive** — it moves lines between files and adds a preamble
per new file. A deliverable that cannot help the headline number, sequenced behind deliverables that
can, is a deliverable with nothing pulling it forward.

## Goal

Every `test_*.py` in the tree is within the 400-line budget, so `test-module-line-budget` reports zero
and the rule can be flipped to `error` — turning the epic's one structural rule from advisory into
enforced. The work is owned by one plan with one measurement, taken slice by slice, and no run
measures a split against a line target.

## Deliverables

The campaign is **one slice per run**. A run takes the next slice in the order below, completes it,
and reports; the following run takes the next. This is deliberate: the evidence says a run completes
two to three deliverables, and one slice is one deliverable.

1. **D1 — Derive the current over-budget set, and halt if the partition does not hold.** Before any
   split, run the whole-tree `test-conventions` sweep and group its `test-module-line-budget` findings
   by slice, then confirm every finding's module falls in exactly one slice of the epic's partition
   **or in this plan's row 7**. **This is the gating, halting derivation** the epic README § "The
   plans, and what may run at the same time" specifies; a module claimed by neither is a partition
   defect and this run neither claims nor skips it unilaterally.
   ⚠️ **Row 7 is why the halt is phrased that way.** Its one module is claimed by no reduction slice —
   `080` excludes the `rule*` glob and the epic README assigns it to plan `010` — so a derivation
   admitting only the six slices halts on this plan's own table. That is not a defect to report; it is
   why row 7 exists.
   **The per-slice counts stated below are leads and one of them will differ**: they move whenever a
   module crosses the budget. **Report the disagreement rather than absorbing it** — a grouping that
   silently differs from this plan's own table is the shape D1 exists to surface.
   *Done when:* the per-slice over-budget counts are recorded, every finding is attributed to exactly
   one slice **or to row 7**, the per-slice counts **plus row 7** sum to the whole-tree total with no
   residual bucket beyond row 7 itself, any module attributed to neither has halted the run with the
   defect reported, and any disagreement with the table in § Expected surface is stated explicitly.
   ⚠️ Row 7 is **not** a residual bucket: it is a declared campaign item with an owner, which is the
   whole reason it exists. A done-when that admits only the six slices makes the six-slice sum 312
   against a whole-tree 313 and halts on this plan's own table — two earlier drafts did exactly that.

2. **D2 — Split this run's slice by behaviour cluster.** **Derive the file set from the plan's own
   Expected surface, never from a convenient tree walk** — plan `060`'s third run ran a sweep whose
   glob reached 37 modules outside its plan's surface and caught it only by checking the changed set
   against that surface before committing. Check the changed set after every edit, and report the
   check. For each over-budget module in the slice,
   split into `test_{unit}_{cluster}.py` using the module's **existing test classes** as the cluster
   boundaries where it has them. Never split in arbitrary halves and never by line count alone.
   Module-level helpers, constants and loaders that more than one resulting module needs move into a
   `_{domain}_fixtures.py` per **B10** — never a `test_*.py` (pytest collects it), never a nested
   `conftest.py`, never a bare `_fixtures.py`.
   **A class larger than the budget is a stated exception, not a licence to split a class.** Plan
   `060`'s third run measured its slice and found exactly one such class, so class-boundary splitting
   reached 52 of its 53 modules. Where a class exceeds the budget alone, leave it, and name it in the
   report with its line count.
   *Done when:* every module in the slice is within the budget or is named in the report as a
   single-class exception with its line count, and each new module's name states its cluster.

3. **D3 — Preserve every shared registration through the move.** `conftest.load_script_module`
   registers the module it builds in `sys.modules` under the script stem, so a split that changes a
   registration name makes previously-isolated modules share state. Plan `030` paid **173
   order-dependent failures** for exactly this: the marketplace config modules carry mutable
   module-level default dicts, and collapsing distinct registrations onto a shared one leaked one
   test's mutation into another's read. Every converted or relocated load in this campaign keeps its
   original registration name unless the module it loads is demonstrably free of module-level mutable
   state — and "demonstrably" means read, not assumed.
   *Done when:* the slice passes in default order **and** in reverse directory order, and the report
   names every registration whose name this run changed together with the evidence that the loaded
   module carries no mutable module-level state.

4. **D4 — Prove the split moved text, not meaning.** A split is a pure move, and the failure mode is
   specific: **an AST-faithful move is not a text-faithful move.** Plan `050` sliced 92 classes
   between `node.lineno` and `node.end_lineno` — exact for every construct the AST models — and
   silently dropped **162 column-0 comments**, eight of which carried fixture invariants that survived
   nowhere else. Every check that run made was green, because the AST does not contain a comment.
   So: diff **comments and prose as their own dimension**, not only the AST, and count them before and
   after.
   *Done when:* the comment count before and after is reported as a measurement rather than an
   assertion, every difference is accounted for, the collected item count for the slice is identical,
   and the node-id sets match.

5. **D5 — Report the measured deltas.** Per-slice `test-module-line-budget` count before and after;
   the whole-tree count before and after; module count before and after; collected item count before
   and after; comment count before and after; the single-class exceptions with their line counts; and
   the slice's line total before and after **stated as an observation, not as a target** (see
   Verification).
   *Done when:* the report carries every figure with the command that produced it.

## Out of scope

* **Any line-reduction target.** Excluded because splitting is line-neutral to slightly positive, and
  measuring it against a line floor is what kept this deliverable sequenced behind work that could
  move the number. The slice's line delta is **reported**, never targeted. A run that deletes an
  assertion, a docstring, or a comment to make the delta look better has failed this plan, not
  satisfied it.
* **Parametrizing, hoisting fixtures, converting namespaces, or stripping prose.** Excluded because
  each belongs to the slice's own reduction plan — `070` and `080` for the two remaining slices, and
  the landed slices' recorded residue. A campaign run that also does house-style work stops being one
  reviewable deliverable, and the reason the split never happened is that it shared a run with work
  like this.
* **Any file under `marketplace/bundles/**` or `test/conftest.py`.** Excluded because test refactoring
  that changes production code is not test refactoring, and because plan `090` owns the shared harness.
  A production or harness defect found while splitting is **recorded**, not fixed.
* **`EXEMPT_RULE_IDS` in `test/pm-plugin-development/plugin-doctor/_fixtures.py`.** Excluded
  explicitly because it is the single most available wrong move when splitting that directory: the
  suite-coverage meta-test asserts
  `registered_rule_ids − fired_rule_ids − EXEMPT_RULE_IDS == ∅`, and a split that separates the
  recording test from the meta-test's import path shrinks `fired_rule_ids()`. Growing the exempt set
  converts a real coverage loss into a passing build. **A grown exempt set is a failed deliverable.**
* **Moving a module into or out of `test/plan-marshall/build-server/`.** Excluded because that
  directory is carved out of `test/conftest.py`'s autouse `_neutralize_daemon_routing` fixture **by
  location**: the carve-out is resolved from the collected node's own path, so a relocation silently
  changes whether the fixture engages, and a module that loses the carve-out keeps passing while its
  assertions become tautologies.

## Expected surface

`test/**` only, one slice per run, and within that slice only `test_*.py` modules the D1 derivation
names as over budget, plus the `_{domain}_fixtures.py` files D2 creates or extends.

**Slice order, and why.** Take the four landed slices first — their reduction plans have landed and
their split residue is unowned, so nothing is concurrent with them — then the two whose reduction plan
must land first, and finally the one module that belongs to a landed plan no reduction slice covers:

| Run | Slice | Over-budget modules (lead — re-derive) | Depends on |
|---|---|---:|---|
| 1 | `050`'s — plan state and records | 60 | nothing; `050` landed |
| 2 | `040`'s — delivery pipeline | 55 | nothing; `040` landed |
| 3 | `060`'s — runtime and script substrate | 53 | `060` landed; **halts if `090` is in flight** — see § Notes |
| 4 | `030`'s — config and manifest | 39 | nothing; `030` landed |
| 5 | `070`'s — architecture and orchestration | 63 | plan `070` landed |
| 6 | `080`'s — plugin development and generator | 42 | plan `080` landed |
| 7 | plan `010`'s rule-test modules — `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` | 1 | `010` landed; **halts if `090` is in flight** — see § Notes |

Each slice's exact directory list is the **Expected surface** of the reduction plan that owns it,
read from that plan's own file — not restated here, because a restated list is a second thing to
drift. **That includes the root-level `test/plan-marshall/*.py` modules**: four of them are over
budget, and each is named by filename in the Expected surface of `040` or `050`, so each belongs to
that slice. The counts above include them, and they are called out because a root-level file is
exactly the category a slice boundary is most likely to mis-assign — an earlier draft of this plan
held them out as a separate bucket, which made its own totals disagree with the plans it cites.

**Row 7 exists because the six slices do not cover the tree.** Plan `080`'s Expected surface excludes
every module matched by `plugin-doctor/test_test_conventions_rule*.py`, which the epic README assigns
to plan `010` — and one of those modules is over budget. No reduction plan would ever take it, because
`080`'s surface is the only one reaching that directory and it excludes the glob; and `010` has
landed, so `010` will not take it either — and the campaign's own goal, the rule reaching zero, is
unreachable without it. An earlier draft of this plan counted it into `080` and asserted a distribution that did not reconcile;
D1's halting derivation is what surfaces that class of error, and it would have halted on this plan's
own table.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `test-module-line-budget` fires on a `test_*.py` over 400 lines, and the budget is stated at `persona-module-tester/standards/testing-methodology.md` § "Module Budget: 400 lines" | OBSERVED | that standards file; `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` |
| The whole-tree count is 313, distributed 39 / 55 / 60 / 53 / 63 / 42 across `030` / `040` / `050` / `060` / `070` / `080`, plus **1** in plan `010`'s rule-test modules, summing exactly to 313 with no residual bucket | HYPOTHESIS — **gating for D1; it sizes every run** | Re-run the sweep from `doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" over `test/` and group the findings by slice, attributing each root-level `test/plan-marshall/*.py` module to the plan whose Expected surface names it. **If your grouping does not sum to the whole-tree total with every module attributed, the grouping is wrong — say so rather than reporting a residual bucket.** An earlier draft of this plan carried a distribution that did not reconcile |
| Plan `010` landed the rule over a tree carrying 315 violations and proposed flipping it to `error` at zero | OBSERVED | `doc/plans/test-quality/010-test-authoring-standards-and-enforcement/report-01.md` § "Proposal 2 — Flipping the four D5 rules to `error`" |
| None of `030`–`060` reached its split deliverable | OBSERVED | the four landed reports' own Deliverables tables and § Residue |
| Splitting is line-neutral to slightly positive | HYPOTHESIS — **it is this plan's reason for refusing a line target** | Measure the slice's line total before and after in D5. If a run finds a materially negative delta, say so: the claim is refuted and the report is where that lands |
| Exactly one class in the `060` slice exceeds the budget on its own, at 663 lines | OBSERVED for that slice, HYPOTHESIS for every other | `doc/plans/test-quality/060-…/report-03.md` § "D2 — still open, with a new finding". Re-derive per slice: the count of budget-exceeding classes is what bounds how many modules class-boundary splitting can reach |
| A line-range or AST-node move silently drops comments preceding a definition | OBSERVED | `doc/plans/test-quality/050-…/report-01.md` § "What have we learned" — 162 column-0 comments lost from a commit whose message called it a pure move |
| `conftest.load_script_module` registers under the script stem, and collapsing registrations leaks module-level mutable state between tests | OBSERVED | `test/conftest.py` — `load_script_module`; `doc/plans/test-quality/030-…/report-01.md` § Findings row 1 (173 order-dependent failures) |
| Every module in this run's slice is claimed by exactly one of the epic's six slices, **or by this plan's row 7** | HYPOTHESIS — **gating and halting; run it before D2** | The six reduction plans' Expected-surface sections, read from their own files, plus row 7's entry in § Expected surface. A module in two lists, or in neither the six nor row 7, is a partition defect: **halt and report it**. Row 7's module is claimed by no reduction slice **by design** — do not report it as the defect |

## Verification

**Three conditions, all of which must hold. There is deliberately no line-count condition.**

1. **Collected test count does not decrease** — measured for the slice before the first commit and
   again before the PR, as pytest's own collected-item count. A split must be exactly neutral here;
   anything else means a test was lost or a module stopped being collected. Plan `050` caught a stale
   generated module this way when its count went **up** unexpectedly (542 → 566), which is the same
   check working in the other direction.
2. **Coverage does not decrease** for the bundle paths the slice exercises. Record before/after and
   the command.
3. **The slice is order-independent.** Run it in default order and again with the directories in
   **reverse order**; both must pass. This is not optional hygiene — it is the check that catches D3's
   failure mode, and plan `060` found a live order-dependent failure with it that three same-order
   runs had reported as passing.

**A fourth check, and it outranks everything above for the `080` slice: the suite-coverage meta-test
must still pass with `EXEMPT_RULE_IDS` unchanged.** Report the before/after sizes of
`registered_rule_ids`, `fired_rule_ids` and `EXEMPT_RULE_IDS`. A grown exempt set is a failed
deliverable, not a passing one.

**A fifth check, epic-wide: the suite must not slow down and must not skip more.** Record the
whole-tree pytest wall-clock and the skipped count before and after, per
`doc/plans/test-quality/README.md` § "What a reduction run must hold". A split adds modules, and each
new module re-runs its own import preamble at collection, which is the mechanism most likely to make
this campaign the one that regresses either figure.

**By reading — cold read, required for D4.** Take three split modules and their `_{domain}_fixtures.py`
and dispatch the lane's pre-PR verification sub-agent with **those files and no other context** — not
this plan, not the originals — asking for each of ten named tests: "what contract does this test pin,
and why does it matter?" A test whose answer is unrecoverable lost a rationale in the move; restore
it beside the symbol it explains and re-read. Record the answers verbatim.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over the slice, before and after, with the per-rule counts
recorded — through the invocation in `doc/plans/test-quality/README.md`, which supplies the five
scripts directories the script needs on `PYTHONPATH` because it has no `sys.path` bootstrap. If it
cannot be made to run, report the affected measurement **unavailable** rather than substituting a
weaker check, and record what the check that would have established the unavailability returned.

## Notes

* **The worked example is already in the tree.** Plan `050` decomposed
  `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_checks.py` (8,705 lines, 92
  classes) into **49** check-named modules and `test_audit.py` into **15**, with the shared builders in
  `_audit_fixtures.py`. Read that directory before starting: it is what a finished slice looks like,
  including the part that went wrong — the 162 lost comments D4 exists to prevent.
* **One slice per run, and the run says which slice it took.** The campaign's state is the tree: a
  slice is done when its `test-module-line-budget` count is zero. There is no ledger, no status file,
  and nothing to update outside this plan's own directory.
* **Sequencing against the rest of the epic.** Rows 1–4 have no dependency and may start
  immediately. `070` and `080` must land before this campaign takes their slices — rows 5 and 6 of
  the table above.
  ⛔ **Two of the seven runs collide with plan `090`, and the check is halting for both.** `090`'s
  carve-out claims three test paths besides its production surface, and two of them are this
  campaign's:
  * **Row 3** — `090`'s carve-out claims `test/plan-marshall/script-shared/` and
    `test/plan-marshall/manage-providers/`, both inside plan `060`'s slice, which row 3 re-enters.
  * **Row 7** — `090`'s carve-out claims the `test_test_conventions_rule*.py` glob, which row 7 splits.

  **Before starting row 3 or row 7, confirm no open PR and no in-flight branch exists for `090`; if
  one does, halt and report it** rather than editing files two plans own. `090` carries the mirror of
  this check and names the same two runs. **Rows 1, 2, 4, 5 and 6 are independent of `090`** and may
  run alongside it.
* **When every slice is done, one thing follows.** `test-module-line-budget` reaches zero and its
  flip to `severity: error` becomes available. That flip belongs to plan `090` § D7's ladder, not
  here — this plan produces the condition, it does not take the gate decision.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked.
