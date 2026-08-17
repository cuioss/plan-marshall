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

# Close the harness and rule gaps every reduction plan is forbidden to fix

**Epic:** test-quality
**Branch prefix:** fix — the deliverables change production behaviour that today blocks its own consumers

> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10**, the concurrency
> contract, and the `plugin-doctor` invocation this plan measures with. The landed skills are the
> authority where they and the README disagree.
>
> **This plan has no blocking dependency on `030`–`080`,** and it is the only plan in the epic that
> may edit `marketplace/bundles/**`. It **shares** `test/conftest.py` with plan `110` — the two own
> different parts of that file and must not run concurrently against it; see § "The three surfaces
> this plan shares". It should land **before** `070` and `080` start, because three of its
> deliverables are what unblocks their **B6** and **B7** work.

## Problem

Every reduction plan in this epic carries the same two exclusions, for a good reason: *"a reduction
plan never edits `test/conftest.py` or `test/_shared/**`"* and *"a reduction plan never edits a
`marketplace/bundles/**` file … If it finds a production defect, it records it; it does not fix it."*
Those boundaries kept six concurrently-running plans from colliding, and they worked.

What they did not do is give the recorded defects an owner. Four executed reduction runs each hit a
blocker that lives in exactly the excluded surface, recorded it as instructed, and moved on. The
records are in the landed reports; the defects are all still open, and two of them sit directly in
front of the two largest deliverables the epic has left.

**The blocking mechanism, named.** `test/conftest.py`'s `parse_ns` builds a namespace from a script's
own parser through one of two seams — a published builder, or interception at `main()`'s
`parse_args`. A script that publishes neither raises `ParserSeamNotFound`, which is the correct
failure but leaves the call site unconvertible. Plan `060` probed every such site in its slice and
recorded 27 blocked on production modules that expose no seam at all — **15** in `script-shared`'s
build CLI (`_build_cli.py`, `_build_execute_factory.py`) and **12** in `manage-providers`'
module-level entry points (`_list_providers.py`, `_cred_*.py`) — with its own report stating that a
published `build_parser()` would unblock all 15 of the first group. (That report's finding row says
"14"; the same report records the subtotal corrected to 15 in a later commit, so the corrected figure
is the one carried here.) **B6** is not a preference: `test/conftest.py`'s own
`parse_ns` docstring explains that a hand-built namespace *"carries only the attributes its author
remembered"*, which is the defect the rule exists to remove.

**The second mechanism.** `conftest.load_script_module` resolves exactly
`{bundle}/skills/{skill}/scripts/{file}`. A bundle skill's **root-level `extension.py`** is not under
`scripts/`, and `get_scripts_dir` raises for a skill with no `scripts/` tree at all. Plan `060`'s
third run found two `test-module-preamble-boilerplate` findings that are **unfixable by the remedy
the rule's own message names** — the rule tells the author to call a helper that cannot address the
file. Plan `020` recorded the same gap from the other side, counting the skill-root `extension.py`
files the loader cannot reach.

**The third.** `load_script_module` registers the module it builds in `sys.modules` under the script
stem. A test that loads a module *by file* therefore displaces the object other directories import
*by name*, and the displaced holder fails on `importlib.reload` depending on collection order. Plan
`060` found this as a live reverse-order failure and fixed it; converted six registrations its own
preamble sweep had introduced back to plain imports; fixed two further pre-existing collisions with
real blast radius (`extension_discovery`, plain-imported by 15 other modules, and `_providers_core` by
3); and left **three** latent, with **no guard of any kind**. Those three are safe only because no
test imports their names plainly today, which is a property of the tree rather than an invariant.

**And the rules the epic measures itself with have gaps of their own.** The
`test-docstring-historical-prose` matchers require `deliverable D<n>` and `PR #<n>`, so the live
spellings `Deliverable 2` and a bare `#849` — both present in this repository's own test prose — are
invisible; the sibling `no-lesson-id-in-skill-prose` rule still carries the citation-versus-datum
confusion that `050`'s second run fixed in rule 7 and did not generalise; `identifier-validator-corpus`
has an empty registry and is a permanent no-op over this tree; and the `broken-relative-link` rule
validates a link's **file** half and not its **fragment**, so a dead anchor is invisible to the gate
that exists to catch dead links.

## Goal

The surface the reduction plans may not touch no longer blocks them. Every `parse_ns` call site that
is blocked on a missing parser seam is unblocked by publishing that seam; the shared loader can
address a skill file wherever it lives and cannot silently displace a shared registration; the
citation rules match the spellings that actually occur in this tree; and the severity ladder's
position is a measured, reported fact rather than an assumption.

## Deliverables

**Six code deliverables and a report, with a declared cut.** That is more than the two-to-three a
cloud run completes — the epic README § "How much one run does" carries the measurement — so the
ordering is not decorative. **D1–D3 are the blocking half**: they are what `070` and `080` are waiting
on, and a run that finishes them and reports D4–D6 as not done has delivered what the epic needs
first. D4–D6 are independent of each other and of the blocking half; a second run takes them. **Report
what was not reached rather than thinning what was.**

1. **D1 — Publish a parser seam on every production module that blocks a `parse_ns` conversion.**
   Add a module-level `build_parser()` (the name `test/conftest.py`'s `PARSER_BUILDER_NAMES` already
   resolves — **read that constant and use a name it lists**, do not invent one) to each production
   module a blocked call site names, and have the module's existing `main()` call it rather than
   constructing its parser inline. The known groups are `script-shared`'s build CLI and
   `manage-providers`' module-level entry points; plan `060`'s second run recorded 27 blocked sites
   across them. **That figure is a lead** — re-derive the blocked set by running `parse_ns` against
   every script the epic's test tree constructs a namespace for and collecting the
   `ParserSeamNotFound` failures, then publish a seam for each module the collection names.
   *Done when:* every module named by a `ParserSeamNotFound` in the re-derived collection exposes a
   builder `parse_ns` resolves, the collection re-run reports zero `ParserSeamNotFound` for those
   modules, no production behaviour changed (each `main()` produces the same parser it did before),
   and the report lists the modules changed with the call-site count each unblocks.

2. **D2 — Let the shared loader address a skill file outside `scripts/`.** Widen
   `conftest.load_script_module` / `get_scripts_dir` so a bundle skill's root-level `extension.py` is
   addressable, **or** — if widening the loader is the wrong shape — exempt that file shape from
   `test-module-preamble-boilerplate` in the analyzer, so the rule stops prescribing a remedy that
   cannot be applied. Take exactly one of the two and state in the report which, and why the other
   was rejected. Both halves are inside this plan's surface, so this is a decision the run makes from
   evidence rather than a proposal it records.
   **There are three instances, not two.** Plan `060`'s third run identified two in its own slice;
   `test/pm-code-intelligence/` carries a third of the same shape, which is why that directory's
   assignment to plan `080` explicitly routes its one open finding here. Re-derive the set rather than
   taking any of these three counts on trust.
   *Done when:* every `test-module-preamble-boilerplate` finding whose file loads a skill-root
   `extension.py` — the two in plan `060`'s slice **and** the one in `test/pm-code-intelligence/` — is
   either fixable by the documented remedy or no longer reported, the whole-tree count for that rule
   is re-derived before and after, and no finding that was a true positive stopped being reported.

3. **D3 — Make a shared-registration collision impossible to introduce silently.** Give
   `load_script_module` a way not to publish into `sys.modules` (or to publish under a caller-chosen
   name that cannot collide), and add a guard test that fails when a module loaded by file registers
   a name another test module imports plainly. Plan `060` fixed every collision it could reach by hand
   — the live reverse-order failure, six its own preamble sweep had introduced, and two pre-existing
   ones with real blast radius — and left **three** latent, safe only because no test imports those
   names plainly today, which is a property of the tree rather than an invariant.
   *Done when:* the guard exists, it **fails** when one of the three latent registrations is given a
   plain importer (demonstrate this by adding the importer, watching it go red, and removing it), and
   the reverse-directory-order arm of the suite still passes.

4. **D4 — Match the citation spellings that actually occur.** Widen
   `_PLAN_DELIVERABLE_ID_RE` and `_PR_REFERENCE_RE` in
   `pm-plugin-development:plugin-doctor:_analyze_test_conventions.py` to the spellings this
   repository's own test prose uses — `Deliverable 2` beside `deliverable D2`, a bare `#849` beside
   `PR #849` — and decide, from a measured false-positive rate rather than from taste, whether the
   `this plan` phrasing plan `040` counted is matchable without firing on legitimate prose.
   **Measure before widening:** run the widened matcher over the whole test tree, read a sample of
   the new findings, and report the false-positive rate. A widening whose false-positive rate is not
   measured is the defect that produced rule 7's original citation-versus-datum gap.
   *Done when:* the new spellings are matched, the before/after whole-tree count is reported, the
   sampled false-positive rate is stated with the sample size, and any spelling deliberately left
   unmatched is named with the reason.

5. **D5 — Generalise the citation-versus-datum fix to the sibling rule.** `050`'s second run taught
   `test-docstring-historical-prose` to exempt a match inside a backtick span or a quoted string,
   because a lesson id can be the test's *data* rather than a citation of history. The sibling
   `no-lesson-id-in-skill-prose` rule, which runs over `marketplace/bundles/**`, still matches on
   shape alone. `050` explicitly declined to widen it without a measured false-positive rate over
   bundle prose, which is the measurement this deliverable takes.
   *Done when:* the false-positive rate over `marketplace/bundles/**` is measured and reported with
   its sample size, and the rule is either given the same literal-span exemption or left unchanged
   with the measurement as the stated reason.

6. **D6 — Stop `test/conftest.py` naming a helper by a path that is about to move.** The
   `_routing_namespaces` docstring names `test/plan-marshall/build_test_helpers.py` **by path**, as
   part of its explanation of why the daemon-routing fixture patches closure `__globals__`. Plan
   `070` renames that file and may not edit `conftest.py`, so the docstring goes stale the moment
   `070` lands. Rewrite the docstring to identify the helper by its **role** rather than its path, so
   the rename cannot invalidate it, and keep both facts the docstring exists to record: that loading
   `_build_execute_factory` through `load_script_module` re-registers it in `sys.modules`, and that
   patching a module object would therefore be silently partial.
   *Done when:* no path under `test/plan-marshall/` is named in that docstring, both recorded facts
   survive verbatim in substance, and `grep -rn 'build_test_helpers' test/conftest.py` returns
   nothing.

7. **D7 — Report the measured deltas, and where the severity ladder stands.** Per-rule whole-tree
   `test-conventions` counts before and after; the re-derived `ParserSeamNotFound` module list with
   the call-site count each entry unblocks; the D4 and D5 false-positive samples with their sizes;
   and the collected test count before and after.

   **Plus the severity ladder, which is a measurement here and not a flip.** Plan `010` shipped four
   `test-conventions` rules at `severity: warning` and proposed flipping each to `error`
   independently once its own whole-tree count reached zero.
   **`test-helper-module-misnamed` has already been flipped** — it ships at `severity: error` today,
   landed by PR #1250, and `_analyze_test_conventions.py`'s own module docstring records why. So this
   deliverable **reports** the ladder rather than acting on it: re-derive each of the four counts, set
   them beside `010`'s baseline, and state which rules have reached zero. **If — and only if — a rule
   other than the already-flipped one is at zero, flip it too**, and say so; on the counts measured at
   authoring time none is, and the campaign that changes that is plan `100`.
   *Done when:* the report carries every figure with the command that produced it, and the four-rule
   ladder table states each rule's current severity, its current count, and `010`'s baseline.

## Out of scope

* **Converting any test call site to `parse_ns`.** Excluded because this plan *unblocks* the
  conversion and the conversion belongs to the slice that owns the tests — `070` and `080` for the
  two remaining slices, and the landed slices' own residue. A plan that both opens the seam and
  spends its run converting call sites would collide with two concurrent siblings on files it does
  not own.
* **`identifier-validator-corpus`'s empty registry.** Excluded because populating it means choosing
  which identifier validators the corpus should cover, which is a coverage decision about production
  code rather than a rule gap, and it needs the whole-tree candidate derivation plan `010` produced
  as its input. Recorded in the epic README's residue table with plan `010`'s finding as its source.
* **The `broken-relative-link` fragment gap.** Excluded because fixing it means anchor-resolving
  every Markdown heading in the marketplace, which is a new analyzer capability rather than a
  widening of an existing matcher, and it would double this plan's review surface. Recorded in the
  epic README's residue table.
* **Splitting any module over the 400-line budget.** Excluded because plan `100` owns the whole
  budget campaign across all six slices; a split done here would collide with it.
* **Adding `hypothesis` or any other third-party dependency.** Excluded because it is a
  user-approval step and this run has no operator. Plan `010` § D6 carries the standing proposal.

## Expected surface

Exactly these, and nothing else:

- `test/conftest.py` — D2, D3, D6 (and the guard test D3 adds, placed per the tree's convention for
  a root-level meta-test, alongside `test_conftest_discipline.py`)
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py`
  — D2 (if the exemption half is chosen), D4
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/` — the
  `no-lesson-id-in-skill-prose` analyzer, D5
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md`
  and the rule-catalog / rule-provenance documents the four rules' provenance contract binds — D4
  and D5
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` — D1, the build-CLI modules a
  blocked call site names
- `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/` — D1, the module-level entry
  points a blocked call site names
- `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` and their fixture
  directories — the tests for the rule changes D4 and D5 make. ⚠️ **Owned by plan `010`**; see the
  carve-out below
- `test/plan-marshall/script-shared/`, `test/plan-marshall/manage-providers/` — only where a D1
  production change requires its own test. ⚠️ **Owned by plan `060`'s slice**, which plan `100`
  re-enters; see the carve-out below

### The three surfaces this plan shares, and the carve-out that governs them

This plan's production changes need tests, and the tests for them live in directories other plans own.
That is a declared overlap, not an oversight, and it is bounded:

| Shared path | Owner | What this plan may do |
|---|---|---|
| `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` + fixtures | plan `010` | **Add or amend only the cases that exercise the rule changes D4 and D5 make.** `010` has landed and is not running, so the risk is a later re-entry, not a concurrent one |
| `test/plan-marshall/script-shared/`, `test/plan-marshall/manage-providers/` | plan `060`'s slice — landed; plan `100` re-enters it as campaign run 3 | **Add only a test that a D1 production change requires.** Do not refactor, reduce, or split anything there |
| `test/conftest.py` | shared with plan `110`, which adds a session preflight (its D2) and a skip guard (its D5) | **This plan owns the loader mechanics** — `load_script_module`, `get_scripts_dir`, the registration behaviour, the `_routing_namespaces` docstring. `110` owns the preflight and the skip guard. The two must **not** run concurrently against this file |

⛔ **Check before starting, and halt on a live collision.** These are ownership overlaps that are safe
only while the other plan is not in flight. Confirm no open PR or in-flight branch exists for `100`
campaign run 3, or for `110`, before touching the second or third row. If one does, **halt and report
it** rather than editing a file two plans own — the epic's partition exists precisely because a
concurrent edit to a shared file is the collision nobody notices until both land.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `parse_ns` resolves a published builder by a name in `PARSER_BUILDER_NAMES`, and raises `ParserSeamNotFound` when no seam resolves | OBSERVED | `test/conftest.py` — `PARSER_BUILDER_NAMES`, `parse_ns`, and its docstring's "Two seams, in order" section |
| 27 `parse_ns` call sites in the `060` slice are blocked on production modules exposing no seam — 15 in `script-shared`'s build CLI, 12 in `manage-providers` | HYPOTHESIS — **gating for D1; it decides the deliverable's size** | `doc/plans/test-quality/060-runtime-and-script-substrate-test-reduction/report-02.md` § "The `parse_ns` exception list". **Re-derive it** by collecting `ParserSeamNotFound` across the tree — the figure was measured over one slice and the two remaining slices carry far more hand-built namespaces |
| `load_script_module` resolves only `{bundle}/skills/{skill}/scripts/{file}`, so a skill-root `extension.py` is unreachable and `get_scripts_dir` raises for a skill with no `scripts/` tree | OBSERVED | `test/conftest.py` — `load_script_module`, `get_scripts_dir`; `doc/plans/test-quality/060-…/report-03.md` § "D3 preambles — 17 → 2" |
| `load_script_module` registers under the script stem, and three registrations remain that would displace a shared object if any test imported them plainly | OBSERVED (the mechanism) / HYPOTHESIS (the count) | `test/conftest.py`'s `load_script_module`; `doc/plans/test-quality/060-…/report-03.md` § F11/H4. Re-derive the collision set before building the guard |
| `_PLAN_DELIVERABLE_ID_RE` requires `deliverable D<n>` and `_PR_REFERENCE_RE` requires `PR #<n>`, so `Deliverable 2` and a bare `#849` are unmatched | OBSERVED | `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — the two regexes and `_HISTORICAL_PROSE_PATTERNS` |
| Both unmatched spellings occur in this repository's own test prose | OBSERVED | `doc/plans/test-quality/050-…/report-02.md` § Residue, "Rule 7's matchers miss two live spellings" |
| `test-helper-module-misnamed` already ships at `severity: error`, so its flip is done rather than owed | OBSERVED | `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — its `RuleDescriptor` for that rule, and the module docstring recording the transition. An earlier draft of this plan wrote the flip as an outstanding action; the tree refutes that |
| None of the other three rules is at zero, so none is flippable yet | HYPOTHESIS — **gating for D7's ladder** | Re-run the `test-conventions` sweep from `doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" over `test/` and read each rule's finding count. **A rule at zero is flipped and said so; a rule above zero is reported, not flipped** |
| `test/conftest.py`'s `_routing_namespaces` docstring names `test/plan-marshall/build_test_helpers.py` by path | OBSERVED | `test/conftest.py` — `_routing_namespaces`; surfaced by `grep -rln 'build_test_helpers' test` |
| No plan in `030`–`080` claims any file under `marketplace/bundles/**` — the surface this plan's production deliverables change | HYPOTHESIS — **asserted absence; it is this plan's entire justification** | Read the **Out of scope** section of each of `030`–`080` and confirm every one excludes `marketplace/bundles/**`. If any plan claims a file there, this plan's production surface overlaps a sibling's: **halt and report it** |
| This plan's **test** surface overlaps three paths other plans own, and each overlap is declared rather than asserted away | OBSERVED | § "The three surfaces this plan shares" above, cross-checked against `010`'s and `060`'s Expected surfaces and `110`'s. **This is not an absence claim** — an earlier draft wrote it as one and was refuted by the tree, which would have halted the run on a defect the plan itself created |
| No run is in flight against `100` campaign run 3 (plan `060`'s slice) or against plan `110` | HYPOTHESIS — **gating and halting; check before touching the shared test paths** | An open PR or an in-flight branch for either. Unresolvable → treat as a collision and halt |

## Verification

**Three conditions, all of which must hold.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count whole-tree
   before the first commit and again before the PR. Record both. This plan adds tests; it removes
   none.
2. **Coverage does not decrease** for the bundle paths the changed production modules sit under.
   Record before/after and the command.
3. **No rule stops reporting a true positive.** For every rule this plan touches, capture the
   whole-tree finding **set** (not just the count) before and after, and account for every finding
   that disappeared: it was either fixed by this plan or it was a false positive this plan
   deliberately exempted. A finding that vanished for neither reason is a regression in the gate.

**A fourth check, and it is the one that matters most for D1: a published seam must not change what
the CLI does.** For each production module D1 touches, capture the parser's own accept-set before and
after — the flags, their defaults, their action kinds — and confirm they are identical. Extracting a
parser into a builder is a refactor whose entire risk is that the extracted parser is subtly not the
one `main()` used to build. `plan-marshall:script-shared:argparse_surface.py` derives a script's
accept-set by running `--help`, which is a before/after-comparable artifact; use it, or state why it
could not serve and what was used instead.

**By reading — cold read, required for D4 and D5.** A citation rule's whole value is what a later
author does when it fires. Dispatch the lane's pre-PR verification sub-agent with the **widened
matchers' findings and no other context** — not this plan, not the diff — and ask, for ten findings
chosen across the new spellings: "is this a citation of history that should be removed, or is it the
test's own data?" A rate of wrong answers is the false-positive rate D4 and D5 must report, measured
by a reader rather than asserted by the author.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the whole-tree
`plugin-doctor test-conventions` sweep before and after, and the sibling `quality-gate` **rule-firing**
sweep — both through the invocation in `doc/plans/test-quality/README.md` § "Running the plugin-doctor
test-conventions scope", which supplies the five scripts directories the script needs on `PYTHONPATH`
because it has no `sys.path` bootstrap of its own. If either command cannot be made to run, report the
affected measurement **unavailable** rather than substituting a weaker check — and record what the
check that would have established the unavailability actually returned.

## Notes

* **Sequencing.** This plan should land **before** `070` and `080` start: D1 unblocks their **B6**
  conversions and D2 unblocks the preamble shapes their **B7** work will otherwise hit. It has no
  blocking dependency of its own — `010` and `020` have landed, and nothing here consumes a `030`–`060`
  deliverable.
* **This is the epic's only plan that may edit production code**, and the reason is stated in the
  Problem: the reduction plans' exclusion of `marketplace/bundles/**` is correct and stays, which
  leaves the recorded defects with no owner. This plan is that owner. It does **not** relax the
  exclusion for anyone else.
* **Where the evidence for each deliverable lives.** Every claim above cites a landed run report
  under `doc/plans/test-quality/`, all of which are git-tracked and readable from your clone. No
  `.plan/` path is a source for this plan; the epic is standalone and has no orchestrator ledger, so
  **do not go looking for one.**
* **D7's ladder is a gate decision, so treat its blast radius seriously.** A rule at `error` fails
  the build for every subsequent plan in this repository. A flip is licensed only by a re-derived
  zero, and on the counts measured at authoring time no rule other than the already-flipped
  `test-helper-module-misnamed` qualifies. Plan `100` is the campaign that changes that for
  `test-module-line-budget`.
