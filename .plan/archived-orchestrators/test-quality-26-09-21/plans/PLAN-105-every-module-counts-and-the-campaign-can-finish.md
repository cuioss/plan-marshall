# PLAN-105: Every Module Counts, and the Campaign Can Finish

epic: test-quality
workstream: WS-04

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

> **Ingested from the standalone cloud lane.** The original brief is preserved verbatim at
> [`archive/105-every-module-counts-and-the-campaign-can-finish.md`](../archive/105-every-module-counts-and-the-campaign-can-finish.md)
> and carries the full reasoning behind every deliverable below. This spec supersedes it; the
> `cloud-plan-lane` first-instruction block no longer applies, and `.plan/` is available.

## Objective

The module-budget campaign's first run landed and left five things behind that no other plan owns, and
each recurs on every one of runs 2–7 if it is not closed now. The rule's count has three permanent
residents nobody intends to act on; the rule cannot see the ~94 non-collected helper modules that hold
about 20,000 lines — including the ~66 that run 1 itself created; the campaign's five instruments died
with the VM and are rebuilt from prose at the start of every run; and the tree carries roughly 691 lint
suppressions that suppress nothing. Close all five so the campaign's metric measures the property it
names and its safety net is a committed script rather than a prose recipe.

## Deliverables

1. **D1 — Re-derive the leftovers, and halt if they are not what this spec describes.** ⛔ **Gating.**
   Derive from the tree in your clone, never from this document: the whole-tree
   `test-module-line-budget` count; the over-budget modules inside slice `050`'s ten directories and,
   for each, whether its largest class exceeds the budget **alone**; the non-collected modules over
   budget; and the `RUF100` population split into its three kinds. Record each with its command.
   ⚠️ **Use `--extend-select RUF100`, never `--select`** — `--select` **replaces** the configured rule
   set, makes every directive look non-enabled, and inflates the count by ~60%. That error was made
   while authoring the original and is recorded so the run does not repeat it.
   D2 rests on a **shape**, not a count: an over-budget module whose whole content is one class that is
   itself under the 500-line ceiling. A module over budget for any other reason is an ordinary split
   that PLAN-140 already permits — report it, do not widen the exemption to cover it. **If no module
   has D2's shape, halt and report**: the exemption would then be a rule change with no instance.
   *Done when:* every figure marked **re-derive** in `## Claim Labels` is recomputed and recorded with
   its command, and any shape mismatch has halted the run with the module named.

2. **D2 — Stop the campaign chasing a shape it has decided to keep.** Three modules remain over budget,
   each a single class under 500 lines. The campaign's subject was **excessively large files** — the
   slice it split held an 8,705-line module — and a 466-line module holding one 424-line class is not
   that. ⚠️ **The decision is to keep them, and the deliverable is to make the rule say so.** Add a
   **bounded, documented exemption**: a collected module whose content is a single class, where that
   class is under a stated ceiling, is not flagged. State the ceiling and the reasoning in the standard
   the rule cites.
   ⛔ **The ceiling is 500 lines, measured on the CLASS, not on the module, and all three are kept.**
   Measuring the module would exclude the first at 541 lines, which is **not** the intent — it exceeds
   its class only by header, imports and a banner, none of which a split could redistribute.
   ⛔ **The exemption must be narrow, and the narrowness is the whole safety property.** A 900-line
   module holding two 450-line classes is an ordinary split and must stay flagged.
   *Done when:* all three modules are unchanged on disk and none is flagged; a module of two
   under-ceiling classes and a module of one over-ceiling class are both still flagged, each pinned by
   a test; and the standard states the ceiling, that it is measured on the class, and the reasoning.

3. **D3 — Make the budget rule see every module in the tree it governs.**
   `analyze_test_module_line_budget` filters on `_is_collected_module`, so a helper is never reported.
   Widen it, and make the finding's message say **which kind** it is — a collected module's remedy is
   "split by behaviour cluster", which is **not** a fixtures module's remedy, and a message naming an
   inapplicable remedy is the defect shape PLAN-090 exists to remove. Widening will report modules never
   reported before, including `test/conftest.py` at ~2,300 lines; **that is the point, and the newly
   reported set is reported, not fixed.**
   ⛔ **This edits `marketplace/bundles/**`, WS-03's exclusive tree.** It is taken here because the gap
   is in the campaign's own metric and a metric that cannot see where the lines went makes every
   remaining campaign run unfalsifiable. Confirm no open PR or in-flight branch touches that file before
   editing, and **halt rather than collide**.
   *Done when:* the rule reports over-budget non-collected modules; each message names a remedy
   appropriate to its kind; the whole-tree count before and after is recorded with the newly reported
   modules enumerated; and a test pins both kinds.

4. **D4 — Commit the campaign's instruments, each deriving both ends itself.** Three checks run 1 built
   and never committed, as scripts a later run invokes: a **fidelity differ** (comments, code lines and
   `Class::test` identities as multisets between two refs), a **duplication detector** (module-level
   definitions identical by name and normalised body across a directory set), and a **banner attribution
   checker** (a construct sitting under a heading that introduces a different section).
   ⛔ **Each takes two refs and computes both sides itself** — never one side from an argument and the
   other from the tree, never a figure passed in. That constraint is the deliverable's reason for
   existing: it is the structural fix for lesson 4, and a script accepting a pre-computed baseline
   reintroduces exactly the defect it prevents. Each must also **state its own definition in its
   output** — what it counted, which paths it covered — because two of run 1's four false figures came
   from two instruments silently using two definitions.
   *Done when:* each script runs against two refs and prints both sides with its definition; each is
   exercised by a test that plants a known loss, a known duplicate and a known misattribution and
   confirms detection; and run 1's own headline comparisons reproduce when re-derived through them.

5. **D5 — Bring slice `050`'s duplication to its floor, measured by D4's detector.** Run 1 reported
   duplication against a definition that changed between the two ends, so **the honest figure is
   unknown** and D1 does not attempt it. Re-derive at the pre-split ref and at HEAD **with one
   instrument**, then remove what remains that has a home.
   ⛔ Two constraints run 1 paid for: only the **dominant body** may move when a name carries more than
   one, because two bodies under one name are two behaviours; and a definition that **binds a loaded
   script module** must never be hoisted — `load_script_module` registers under the script stem, and a
   shared binding hands consumers a different module object. That mistake cost run 1 seven failing tests
   and, on an earlier plan, 173 order-dependent ones.
   *Done when:* duplication is reported at both refs by D4's detector with its definition printed; each
   remaining duplicate is removed or recorded with why it cannot move; and the whole affected suite
   passes in **both** directory orders.

6. ⛔ **D6 — RETIRED at cleanup. Its population no longer exists; do not attempt it.**
   D6 swept for *live instructions* naming a deleted test module — a staged, unexecuted plan citing one
   in a *Done when:* clause or an Expected-surface entry. Both halves of that population are gone:

   * The `doc/plans/` half — six references across four staged plans in other epics — went with the
     tree, removed entirely at commit `3bc01075` once both standalone epics were ingested.
   * The `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` specimens are **worked
     examples in a naming-convention table** (`test/.../test_findings_store.py`, elision included), not
     references to real modules. Six of the eight module names cited there do not resolve, and **that is
     correct** — they are the deliberate-citation class D6's own classification rule says to leave alone.

   ⚠ **Recorded rather than deleted**, so a reader who finds D6 named in the archived original
   (`.plan/orchestrator/test-quality/archive/105-every-module-counts-and-the-campaign-can-finish.md`) learns why it is absent rather
   than assuming it was dropped. **No sweep is owed.**

7. **D7 — Remove the suppressions by removing their causes, not by deleting the comments.** The tree
   carries ~1,130 `noqa` directives; stripping them and re-running `ruff` yields ~1,024 violations in
   exactly **four** codes falling into **two groups needing opposite treatment**.
   **`F401` (191) and `F811` (362) are pytest's semantics, and no code change reaches them** — a fixture
   is resolved by name, so the import that makes it visible looks unused and the test's parameter shadows
   it by design. Add a `per-file-ignores` entry for the test tree and **state the reason in the config**.
   ⚠️ **Say what this costs**: `F401` also catches genuinely dead imports, and this turns that off across
   `test/**`. Record it as an accepted cost with the number it covers.
   **`E402` (237) and `I001` (232) are a real smell with a fix that already exists.**
   `conftest.load_script_module` resolves any module inside a skill's `scripts/` directory, helpers
   included; **132 test modules still hand-roll it**. Migrate them and 469 suppressions lose their cause
   with both rules left **enabled**, which is strictly better than configuring them away.
   ⛔ **`load_script_module` registers in `sys.modules`, and a registration collision is the failure that
   cost PLAN-030 173 order-dependent tests.** Read that function's docstring before migrating a single
   file — it documents `module_name=` and `register=False`, and an existing guard test fails when a
   loaded name is also imported plainly. Run affected directories in **reverse** order after each batch.
   **Then make it impossible to regrow:** add `RUF100` to `select`.
   ⛔ **`RUF100` cannot be enabled until the two steps above have landed**, or it turns ~691 findings red
   at once. Order is: **configure → migrate → sweep → enable.**
   What is left is the ~108 naming rules this project does not run (`S603`, `BLE001`, `PLC0415`, `ANN*`,
   `D*`). These suppress nothing today, so `ruff --fix` deletes every one and takes the author's
   judgement with it. Convert each to a plain-language comment stating the intent; where the intent
   cannot be recovered from the code, **leave it and record it** rather than guess.
   *Done when:* `ruff check --extend-select RUF100` is clean; `RUF100` is in `select` and the build is
   green with it; no test module manipulates `sys.path` where the loader could have; the whole tree
   passes in default **and** reverse order; every non-enabled directive is converted or recorded; and the
   report gives before/after **by code**, not one number.

## Claim Labels

- OBSERVED — **re-derive; it is D2's whole premise and D1 halts on a shape mismatch**: three modules in
  slice `050` are over budget, each with one class over budget alone —
  `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` (541 lines / 495-line
  class), `manage-lessons/test_list_stalled.py` (466 / 424), `manage-lessons/test_restore_from_plan.py`
  (465 / 422)
  - verdict: corroborated | checked_at: 09f92b5e | by: test-quality/cleanup | rescoped: n/a | evidence: re-measured directly at HEAD 09f92b5e: the three slice-050 modules are still unsplit at 552, 466 and 465 lines - identical to the prior check at 00b92fca. Measured by reading the files, not inferred from the diff, because the 270-file window makes an absence argument unavailable. D2's premise and D1's shape gate both stand
- OBSERVED: `analyze_test_module_line_budget` filters on `_is_collected_module`, so no helper module is
  ever measured — read at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py`
  § `analyze_test_module_line_budget` and `_is_collected_module` immediately above it
- HYPOTHESIS — **re-derive; it sizes D3**: ~94 non-collected modules hold ~20,000 lines, ~8 of them over
  budget and none reported — confirm/refute at a walk of `test/**/*.py` partitioned by
  `_is_collected_module`'s own predicate (verify-at-outline). Run 1 landed 66 new helpers and the number
  moves with every slice
- OBSERVED — **an asserted absence; verify it**: run 1's instruments were never committed. If a fidelity
  differ or duplication detector already exists under `test/`, D4 **extends** it rather than creating a
  second one — an unverified absence here means building something twice
- OBSERVED: the slice's duplication figure is currently **unknown**, because run 1's two ends used two
  definitions — read at `.plan/orchestrator/test-quality/archive/100-module-budget-campaign/report-01.md` § Findings, M45. This is why D1
  does not ask for a duplication number and D5 waits on D4
- OBSERVED — **and the first derivation of it was wrong by 63%**: the `RUF100` population is ~691 across
  ~391 files in three kinds (~364 shadowed, ~219 stale, ~108 non-enabled). The figure first recorded was
  **1,127**, from `--select RUF100`. Same tool, same tree, two instruments, a 436-diagnostic gap —
  lesson 4's fifth instance, found while authoring the plan that cites lesson 4
- OBSERVED for the mechanism, **a DECISION for the disposition**: PLAN-140 § D2 forbids splitting a
  class, so a follow-up under it cannot close the three. That they should be **kept** rather than split
  is **not derivable from any artifact** — it is an operator decision, recorded so a reviewer can reject
  it. If rejected, D2 inverts to a split and D1's gate is unchanged
- OBSERVED — **and the opposite was asserted while authoring, then refuted by reading the code**:
  `load_script_module` can address ANY module in a skill's `scripts/` directory, helpers included, so the
  132 hand-rolled `sys.path` modules are migratable. An earlier draft claimed the loader reached only
  top-level scripts and that the migration needed a loader change first. That was wrong, and it is
  recorded because the wrong version would have sent the run to build something that already exists

## Expected Surface

- OBSERVED: `test/plan-marshall/plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` — D2
- OBSERVED: `test/plan-marshall/manage-lessons/test_list_stalled.py` — D2
- OBSERVED: `test/plan-marshall/manage-lessons/test_restore_from_plan.py` — D2
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — D3
  ⛔ **WS-03's surface; see D3 for why it is taken here and what to check first**
- OBSERVED: `test/pm-plugin-development/plugin-doctor/` — D3's tests, beside the existing rule tests
- HYPOTHESIS: `test/_shared/` or a sibling the tree's conventions indicate — D4's three instruments and
  their tests (verify-at-outline). ⚠️ **PLAN-020's surface, and shared with PLAN-110**, which writes its
  session preflight there
- OBSERVED: slice `050`'s ten directories under `test/plan-marshall/` — D5, and D2's fidelity check
- OBSERVED: `pyproject.toml` — D7's `per-file-ignores` entry and the `RUF100` addition. Small, but the
  highest-leverage file in the plan: two entries retire 553 directives
- HYPOTHESIS: **~132 test modules** — D7's migration off `sys.path` onto `load_script_module`
  (verify-at-outline). ⛔ **This is the risky part of D7, not the sweep**
- HYPOTHESIS: **~391 files across `test/` and `marketplace/bundles/`** — D7's final sweep
  (verify-at-outline). ⛔ **The widest surface in the plan, and it reaches into WS-03's tree.** Take the
  sweep **last** and re-check the collision immediately before it, so a collision costs one commit
  rather than the run

## Dependencies and Sequencing

- Depends on: PLAN-010, PLAN-020, PLAN-090, PLAN-100 run 1 — all landed. Nothing blocks it.
- ⛔ **Run it BEFORE PLAN-140's first campaign run.** D3 and D4 change what a campaign run measures and
  what it must otherwise rebuild by hand.
- Overlaps with: **PLAN-145 / PLAN-160** (`marketplace/bundles/**`, WS-03's tree — D3 at one file, D7
  across ~250); **PLAN-140** (slice `050`'s ten directories — D5 rewrites duplicated definitions there);
  **PLAN-110** (`test/_shared/**` — D4's instruments beside PLAN-110's preflight; this plan does **not**
  edit `conftest.py`'s loader mechanics, so the overlap is narrower than PLAN-135's).
- Adjacent to: `test/conftest.py`'s loader mechanics — read, never edited.

## Out of Scope

- **Fixing the modules D3 newly reports.** Widening a metric and reducing what it measures are two
  changes; bundling them makes it impossible to tell which moved the count.
- **Flipping `test-module-line-budget` to `severity: error`.** A policy decision with a named owner.
- **Adding any third-party dependency**, including `pytest-randomly`. Reverse directory order is what
  run 1 used to establish order-independence and needs no plugin.
- **Widening the exemption beyond one-class modules, or raising the 400-line budget.** D2's exemption is
  deliberately the narrowest shape covering the observed cases.
- **Editing any archived run report.** Those are dated records of what was true when a run executed.

## Split-Guard Note

⚠️ **Six LIVE deliverables — D6 is retired above, so the spec now sits AT the epic's ~6 presumptive split
threshold rather than above it.** Proceeding unsplit remains a recorded decision (see the epic's
`## Decisions`), and the argument below is unchanged and now cheaper to accept. Every one is a leftover of PLAN-100 run 1 that no
other plan owns, and D2, D4 and D5 are **mutually dependent**: D2's fidelity proof needs D4's differ, and
D5's figure is meaningless without it. Splitting would build the instrument in one plan and first use it
in another, with nothing exercising it in between.
⛔ **If a run finds D7 too large to finish, stop after the migration and report** — configure-and-migrate
is a coherent landing point; sweep-without-gate is not.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-105-every-module-counts-and-the-campaign-can-finish.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
