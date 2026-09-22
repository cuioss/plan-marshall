# PLAN-135: Sweep the Preambles the Shipped Accessors Can Now Reach

epic: test-quality
workstream: WS-02

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion**, from a defect class four independent
> ground-truth checks found and no landed plan owns. It is PLAN-130's sibling — same cause, different
> rule — and the two are **strictly sequenced**, never concurrent.

## Objective

PLAN-090 shipped `conftest.load_skill_module` **specifically** to address the one preamble shape the
reduction plans could not convert: a bundle skill's root-level `extension.py`, which `load_script_module`
cannot address. The accessor landed, PLAN-080 adopted it — and PLAN-060's own known-blocked call site was
never converted, while three more sit in a **circular ownership contradiction** where PLAN-070's report
names PLAN-090 as owner and PLAN-090's report names PLAN-070. Both plans are closed. **The fix shipped and
the tree was never swept.** Close it: convert every preamble the shipped accessors can now reach, and
resolve the `subprocess-pythonpath` findings that share the same cause.

## Deliverables

1. **D1 — Derive the live population and classify every member.** ⛔ **Gating and halting.** Run the
   doctor's `test-conventions` scope whole-tree and classify **every**
   `test-module-preamble-boilerplate` finding into exactly one of:
   * **reachable by `load_script_module`** — the target is inside a skill's `scripts/` directory; **convert**;
   * **reachable by `load_skill_module`** — the target is a skill-root `extension.py`; **convert**;
   * **structurally unreachable** — the target is outside `marketplace/bundles` (`generate.py`, the
     repository-root `build.py`); **leave it and name it**, this is the floor;
   * **not a preamble** — a secondary in-test dynamic load of a scratch fixture; **exempt**, and confirm
     the module's own preamble is already compliant.

   Do the same for the `subprocess-pythonpath` findings.
   *Done when:* every finding carries exactly one class with its evidence; the whole-tree and per-slice
   counts are recorded with their commands; the structural floor is stated as a number and a file list; and
   any member fitting no class has halted the run with the member named.

2. **D2 — Convert every reachable preamble, and resolve the circular-ownership three first.** Replace each
   convertible preamble with the appropriate accessor.
   ⛔ **Take the three contradiction sites first**, because they are the ones with evidence that nobody was
   going to do them: `test/plan-marshall/build-gradle/test_gradle_discover_modules.py`,
   `test/plan-marshall/build-npm/test_npm_discover_modules.py`,
   `test/plan-marshall/build-operations/test_extension_implementations.py`. Then
   `test/plan-marshall/extension-api/test_extension_discovery.py:458`, PLAN-060's own site, which its
   report-03 named as blocking (H6) and which the accessor unblocked.
   ⛔ **`load_script_module` registers in `sys.modules`, and a registration collision is the failure that
   cost PLAN-030 173 order-dependent tests and PLAN-060 seven.** Read that function's docstring before
   converting a single file — it documents `module_name=` and `register=False` — and note that
   `test/plan-marshall/script-shared/test_conftest_loader_contract.py` carries a guard that **fails on
   growth** past its 23-name `KNOWN_REGISTRATION_COLLISIONS` baseline. **The guard must not be relaxed to
   accommodate this work**: a conversion that would grow the baseline is a conversion that needs
   `register=False`, not a larger baseline.
   *Done when:* the rule's whole-tree count is reported before and after; the four named sites are converted
   or each is named with why it could not be; the collision baseline is **unchanged**; and the affected
   directories pass in **default and reverse** order.

3. **D3 — Resolve the `subprocess-pythonpath` findings.** The rule reports **15** tree-wide, and its one
   named instance — `marshall-steward/test_steward_determine_mode.py` — has been recorded as unowned since
   PLAN-030 run 02.
   *Done when:* the count is reported before and after; every finding is fixed or named with why it cannot
   be; and any rule false positive is **recorded for WS-03**, not worked around.

4. **D4 — Report the measured deltas.** Both rules' whole-tree counts before and after; the per-slice
   breakdown; the full classification with one row per finding; the structural floor named as a file list;
   the collision-baseline before and after; the reverse-order result; and the collected test count before
   and after.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the whole-tree `test-module-preamble-boilerplate` count is **101** and `subprocess-pythonpath`
  is **17** at HEAD `bf1b7ed6` — re-derived from the doctor's own `rules_run` tally. ⛔ **Re-scoped five
  times, 106 → 107 → 110 → 112 → 101**, and the last step is a **DECREASE of 11** across this epic's own
  521-file landing `bf1b7ed6` — the first fall this population has recorded. **Treat this
  number as a moving target and re-derive it in D1 rather than executing from it**: the count has moved in
  every window measured so far, and D1 is gating precisely because the population is live.
  ⛔ **`subprocess-pythonpath` HAS NOW MOVED, 15 → 16 → 17** — this claim previously asserted it "unmoved
  at 15 across all three measurements", and that stability assertion is REFUTED. All four of this rule
  set's populations now move, and `preamble-boilerplate` has now moved in BOTH directions; treat none of
  them as a fixed floor, and treat neither direction as evidence of remediation
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: doctor rules_run tally at bf1b7ed6: test-module-preamble-boilerplate 101, DOWN 11 from the recorded 112 and the first fall this population has shown; subprocess-pythonpath 17, up from the recorded 16. Re-scoped both, and the claim now records that the population moves in BOTH directions so neither direction is evidence of remediation
- OBSERVED — **a live circular-ownership contradiction, and the strongest evidence this plan is needed**:
  PLAN-070's report assigns three unconverted `extension.py` preambles to `090 § D2`, and PLAN-090's report
  assigns the same three to PLAN-070. Both plans are closed; ⛔ **2 of the 3** sites are still raw
  `spec_from_file_location` at `bf1b7ed6` — `build-npm/test_npm_discover_modules.py:36` and
  `build-operations/test_extension_implementations.py:67`. **`build-gradle/test_gradle_discover_modules.py`
  has since been converted** to `load_skill_module` and is no longer a site (re-scoped from 3)
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: 2 of the 3 circular-ownership sites remain raw at bf1b7ed6 (build-npm/test_npm_discover_modules.py:36 and build-operations/test_extension_implementations.py:67); build-gradle/test_gradle_discover_modules.py has been converted to load_skill_module and is no longer a site. Re-scoped from 3 to 2
- OBSERVED: `test/plan-marshall/extension-api/test_extension_discovery.py:460` (drifted +2 from `:458`)
  still uses raw `spec_from_file_location` although PLAN-090 shipped `load_skill_module` for exactly that
  shape and PLAN-080's equivalent site **was** converted — read at `test/conftest.py:488` and the two call
  sites
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: still uses raw importlib.util.spec_from_file_location at bf1b7ed6, at line 460 - a +2 drift from the cited :458, corrected in place
- OBSERVED: `test/conftest.py:372` `get_skill_dir` and `:488` `load_skill_module` both exist (both drifted
  +4) and **16** test modules already consume the latter (re-scoped from 15)
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: get_skill_dir is now at test/conftest.py:372 and load_skill_module at :488, both drifted +4; load_skill_module( resolves in 17 files including the conftest definition itself, so 16 consumers not 15. Re-scoped on both lines and count
- OBSERVED: the structural floor is **2** — `generate.py` and the repository-root `build.py`, both outside
  `marketplace/bundles` and therefore unreachable by `load_skill_module`. ⛔ **An asserted absence: verify
  it before accepting it.** If a conftest accessor could reach them, this floor is not a floor and D1 says so
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: generate.py at marketplace/targets/generate.py and build.py at the repository root both exist at bf1b7ed6 and both sit outside marketplace/bundles/, so the structural floor of 2 holds
- OBSERVED: the `sys.modules` collision guard sits at a **17**-name baseline with an
  `UNRESOLVED_CALL_SITE_BOUND` of **86** — read at
  `test/plan-marshall/script-shared/test_conftest_loader_contract.py:55` and `:69-87` (re-scoped from a
  23-name baseline and a bound of 90 at `:47` / `:61-85`). ⚠️ **Both baselines FELL** across `bf1b7ed6`,
  which also added +83 lines to this same file
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: at bf1b7ed6 test_conftest_loader_contract.py carries UNRESOLVED_CALL_SITE_BOUND 86 at :55 and a KNOWN_REGISTRATION_COLLISIONS frozenset of 17 entries at :69-87, against the recorded 90 at :47 and 23 at :61-85. BOTH baselines FELL across a landing that added +83 lines to this same file. Re-scoped

## Expected Surface

⛔ **This plan crosses the whole partition by construction**, like PLAN-130. It is surface-incompatible with
every other `test/`-editing plan and must be sequenced, not paired.

- OBSERVED: `test/` — ⛔ **the whole tree.** The rule's 110 findings do not respect slice boundaries, so
  this plan's surface is the test tree entire, and it pairs with no other `test/`-editing plan
- OBSERVED: `test/plan-marshall/build-gradle/test_gradle_discover_modules.py` — D2, contradiction site 1
- OBSERVED: `test/plan-marshall/build-npm/test_npm_discover_modules.py` — D2, contradiction site 2
- OBSERVED: `test/plan-marshall/build-operations/test_extension_implementations.py` — D2, contradiction site 3
- OBSERVED: `test/plan-marshall/extension-api/test_extension_discovery.py` — D2, PLAN-060's blocked site
- OBSERVED: `test/plan-marshall/marshall-steward/test_steward_determine_mode.py` — D3
- HYPOTHESIS: the remaining preamble and `subprocess-pythonpath` findings across `test/plan-marshall/**`,
  `test/pm-plugin-development/**` and `test/marketplace/**` — the full set is **D1's output**, not this
  spec's (verify-at-outline)
- OBSERVED: **no `marketplace/bundles/**` file**, and **no edit to `test/conftest.py`**. The accessors this
  plan consumes already exist; needing a new one is a finding **recorded for WS-03**, not built here

## Dependencies and Sequencing

- Depends on: PLAN-090 (landed — it shipped the accessors this plan consumes).
- ⛔ **Runs AFTER PLAN-130, never beside it.** Both sweep the same tree; PLAN-130's edits are contained to
  docstrings while this plan's change what a module binds at import time, so the riskier change goes second
  against a settled target.
- ⛔ **Must not run concurrently with PLAN-140** (any campaign run), **PLAN-105** (§ D5 and § D7 both touch
  loader call sites and `sys.modules` registration), or **PLAN-110**.
- ⚠️ **PLAN-105 § D7 overlaps this plan's subject directly** — its migration of ~132 modules off `sys.path`
  onto `load_script_module` is the same mechanism against a different population. If PLAN-105 lands first,
  **re-derive D1 before scoping**: much of this plan's D2 may already be done, and the honest outcome is a
  smaller plan rather than a duplicated one.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-135-sweep-the-preambles-the-shipped-accessors-can-now-reach.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
