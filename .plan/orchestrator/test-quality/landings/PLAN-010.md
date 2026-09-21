# Landing Analysis: PLAN-010 — Test-Authoring Standards and Enforcement

epic: test-quality
workstream: WS-01
pr: not recorded in the archived report (cloud-lane run, pre-ingestion)

> Landing record for one shipped plan. Lives at `landings/PLAN-010.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Ground-truth check run at HEAD `2cd1a19c`** by a dispatched read-only `execution-context-level-3`
leaf, against the archived `plan.md` + `report-01.md`. The archived report is a **claim**; this record
is the verdict.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — retire the ~200-line figure, state the 400-line budget and the cluster-split taxonomy in `persona-module-tester` | **shipped-as-specified** | `testing-methodology.md:75` `### Module Budget: 400 lines`; a grep for `200 lines` in that file returns nothing; the derivation cites the corpus's own ~327-line median |
| D2 — state the universal-contract / literal-is-the-contract discriminator in both skills | **shipped-as-specified** | `testing-methodology.md:212` and `testing-pytest.md:212` both carry `### The discriminator`; `testing-pytest.md:207` "Write an exact literal where the literal is the contract" |
| D3 — docstring content rule (present-tense invariant; no incident, PR or lesson-id citation) in both skills | **shipped-as-specified** | `testing-methodology.md:139`; `testing-pytest.md:405-406` carry the same language, with a worked before/after at `:416-423` |
| D4 — six arrange/parametrize/argv/budget rules plus one-layer-per-contract in both skills | **shipped-as-specified** | `testing-pytest.md` § Test Organization carries all six (`:395,403,437,467,497,525`) plus `One layer per contract` (`:535`); `persona-module-tester.md:361` `## One Layer Per Contract` |
| D5 — four new `test-conventions` rules at `severity: warning`, with tests, catalog and provenance rows, and corrected severity statements | **shipped-as-specified** | `_analyze_test_conventions.py:61-64` carries a `RuleDescriptor` for all four ids; a **live doctor run at HEAD fires all four** (267 / 0 / 106 / 201 findings); `rule-catalog.md:624-627` and `rule-provenance.md:282-285` carry rows; `_plugin_doctor_fixtures.py:1047-1072` carries the `FIXTURE_CORPUS` entries; no `EXEMPT_RULE_IDS` entry for any of the four |
| D6 — record the Hypothesis-adoption and error-flip proposals without acting on them | **shipped-as-specified** | `pyproject.toml` carries no `hypothesis` string anywhere — the dependency was correctly **not** added; the archived report carries both proposals with derived counts |

**Six of six shipped as specified.** This is the epic's cleanest landing: every claimed artifact exists
where the report says it does, and the enforcement half is confirmed by running the analyzer over the
real tree rather than by reading the code that would run it.

## Metrics and Anomalies

- Tokens / duration: not recorded in the archived report in a form this analysis can re-derive.
- **Anomaly — one rule has since been promoted.** `test-helper-module-misnamed` now ships at
  `severity: error` and reports **0** violations. It is the epic's one fully-closed enforcement rule.
  The archived report anticipated exactly this flip once the count reached zero.

## Routing and Merge Behavior

- Review: not recoverable from the archived artifacts; the cloud-lane run predates this ledger.
- CI/merge: the plan landed on `main`; its rules are live in the shipped analyzer, which is the
  stronger evidence.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `landing` stamped → `landings/PLAN-010.md`
- [x] Open Defect opened — `test_test_conventions_rule6.py` regrown over budget (see below)
- [x] Watch opened — corpus-wide **B6** adoption is far thinner than a reader of the landed reports
      would assume (see below)

## Follow-Ups

- ⛔ **Open Defect — the rule this plan shipped now fires on the module this plan created.**
  `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule6.py` is the module D5's Finding
  26 split off *specifically* to keep `rule4.py` under the budget D1 was introducing. It has grown back
  to **681 lines**, 281 over budget, and the live doctor run flags it against that very rule. It is
  assigned on paper to WS-04's campaign row 7, which **has not executed**. Recorded in the epic's
  `## Open Defects`.

- **Watch — harness adoption is thin relative to the corpus.** 36 modules reference `parse_ns` against
  **2,467** remaining hand-built `Namespace(` sites tree-wide (census lead: ~2,900). This refutes
  nothing either plan claimed — neither ever claimed corpus-wide conversion — but a reader of `080`'s
  "**B6** complete at 211 of 211" could reasonably mis-read the whole corpus as converted. Recorded in
  the epic's `## Watches`.

- **Unowned residue carried forward** (each recorded in the epic's `## Open Defects`): the three
  pre-existing `test-conventions` rules with no `rule-catalog.md` rows; `pm-dev-java` still carrying the
  retired ~200-line figure and the unscoped generated-data phrasing; `uv.lock` out of sync with
  `pyproject.toml` on `main`.

- **Unowned by design, and correctly so:** populating the `identifier-validator-corpus` registry (a
  coverage decision, not a rule gap) and the `broken-relative-link` rule's fragment half (a new analyzer
  capability, not a widening). Both are stated in the archived brief and in `090` § Out of scope.

## Note on Drift

Every corpus-wide snapshot the archived report states (module count, line totals, violation counts) has
moved substantially since this plan landed, because seven further plans executed against the same corpus
afterwards. That is **expected drift, not a report defect** — each figure was internally correct against
its own clone. The re-derived figures at HEAD are recorded in the epic's `## Open Defects` where they
change a decision, and are otherwise left as leads.
