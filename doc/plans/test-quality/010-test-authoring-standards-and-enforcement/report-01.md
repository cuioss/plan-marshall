# Run report — 010-test-authoring-standards-and-enforcement (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/test-authoring-standards-ja0nqp`    **PR:** _(pending)_    **Outcome:** completed

## Skills loaded

Loaded by reading the bundle path (the `plan-marshall` plugin is not installed in this cloud session,
so `Skill: {bundle}:{skill}` notation was not used):

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, `.claude/skills/`) — first action of the run |
| `plan-marshall:ref-code-quality` | bundle path |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `plan-marshall:persona-module-tester` | bundle path — also an edit target (D1–D3) |
| `pm-dev-python:pytest-testing` | bundle path — also an edit target (D2–D4) |
| `pm-plugin-development:plugin-doctor` | bundle path — edit target (D5) |

No skill was unobtainable by both routes.

## Deliverables

| # | Outcome | Commit | Verification state |
|---|---|---|---|
| D1 | Done | `782345b` | `~200` figure retired tree-wide; 400-line budget + cluster taxonomy stated; derivation cites the measured median |
| D2 | Done | `782345b` | Discriminator stated in both files; Forbidden-Patterns and Anti-Patterns rows qualified |
| D3 | Done | `782345b` | Rule + grounding + worked before/after in both skills |
| D4 | Done | `782345b` | Six rules with thresholds + one-layer-per-contract in both skills; Quick Reference rows added |
| D5 | Done | `5c31b15` | Four rules ship at `warning`; all four fire over the live tree; 21 new tests; full `./pw verify` green |
| D6 | Done | this report | Both proposals below, derived at report time |

### D1 — Module budget

`persona-module-tester/standards/testing-methodology.md`: § "Splitting Large Test Files" replaced by
§ "Module Budget: 400 lines" + § "Splitting by behaviour cluster". The `~200 lines` figure appears
nowhere in the file. The derivation sentence names the median as its basis and cites the number
**measured on this clone**, not the number written in the plan.

**Census re-derived** (the plan labels this HYPOTHESIS and requires re-derivation):

| Measure | Plan's lead | Measured here |
|---|---|---|
| `test_*.py` modules | ~770 | **786** |
| Total lines | ~377,000 | **384,224** |
| Median module | ~323 | **326.5** |
| Modules > 400 lines | ~309 (40%) | **315 (40.1%)** |
| Share of lines in > 400 modules | ~73% | **73.1%** (280,779) |
| Modules > 200 lines | "~three quarters" | **588 (74.8%)** |

Every lead is confirmed. The standard states "~327 lines" as the median.

### D2 — Generated-data scoping

Both files now state the discriminator: **generated data where the contract is universal** (parsers,
identifier validators, path normalisers, round-trip encoders) / **exact literals where the literal is
the contract** (seeded default, canonical step id, serialized field name, argparse flag spelling), with
the settling question — *would this test still be meaningful if the value were different?* The existing
exception list is subsumed, not contradicted: the Forbidden-Patterns bullet and the Anti-Patterns table
row are both qualified by the discriminator rather than deleted.

### D3 — Docstring content

Stated in both skills, grounded in `CLAUDE.md` § Documentation Standards applied to a tree those
standards were never scoped over, and cross-referenced to the three existing `plugin-doctor` rules that
enforce the same thing over `marketplace/bundles/**`. The worked before/after is drawn from a **real
module in this tree** —
`test/plan-marshall/manage-architecture/test_files_inventory.py::test_which_module_resolves_test_path_via_paths_tests`,
whose docstring ends "(closes lesson 2026-07-09-04-001)". The "after" keeps the invariant and adds the
present-tense reason the invariant is load-bearing.

### D4 — Arrange placement, parametrization, argv, budgets, layering

All six rules stated with their triggering thresholds in `pytest-testing` § "Test Organization", plus
one-layer-per-contract in **both** skills. The namespace rule names the defaults-bypass as its reason.
The 15-line test budget is explicitly a review trigger, not a gate, and states why no rule ships for it.
The one-layer rule names both exceptions and the name-the-replacement obligation. Quick Reference gained
a row per rule.

### D5 — Four plugin-doctor rules

All four ship at `severity: warning` and fire over the live tree.

**Absence claim verified** (the plan flags this as the higher-risk HYPOTHESIS). The registry was
enumerated by *running* it — `_rule_registry.get_registry()` — not by grepping, because most descriptors
use positional arguments and a grep-based enumeration under-reports badly (15 ids vs the real 72). Of
the **72** registered rules, none of the four new ids exists, and none has equivalent detection over
`test/`: `no-historical-prose-in-skills`, `no-incident-references` and `no-lesson-id-in-skill-prose` all
take a `marketplace_root` and never see the test tree. `test_test_conventions_rule4.py` did not exist.

**Reuse decision** (the plan's "Reuse before you write" note). For `test-docstring-historical-prose` the
detection *patterns* are reused by **importing** them — `_LESSON_ID_RE` and `_LESSON_BACKTICK_ID_RE` from
`_analyze_lesson_id_in_skill_prose`, `_PLAN_MARSHALL_REF_RE` from `_analyze_incident_reference_in_docs` —
rather than restated. Cross-analyzer imports are idiomatic here (`_analyze_allowed_tools_drift` imports
from `_analyze_coverage`; `_analyze_plugin_json` from `_analyze_declared_vs_disk`). Only two shapes those
analyzers do not carry are defined locally: `PR #NNN` / `pull request #NNN`, and plan/deliverable ids.
The *traversal* is not reused, and deliberately: the existing analyzers walk `marketplace/bundles/**` with
markdown-oriented exemptions (frontmatter, fenced blocks, `Source:` lines) that have no meaning over a
`*.py`-only test tree, and they take a `marketplace_root` this scope does not have.

**Provenance contract — all five artifacts per rule:**

| Rule | Feasibility count | Positive test fires | rule-catalog row | rule-provenance row | Source citation |
|---|---|---|---|---|---|
| `test-module-line-budget` | 315 | ✓ | ✓ | ✓ | `persona-module-tester` § "Module Budget: 400 lines" |
| `test-helper-module-misnamed` | 1 | ✓ | ✓ | ✓ | `persona-module-tester` § "Test Helper Module Organization" |
| `test-module-preamble-boilerplate` | 342 | ✓ | ✓ | ✓ | `conftest` helper contract (`load_script_module` / `get_scripts_dir`) |
| `test-docstring-historical-prose` | 283 prose hits vs 861 legitimate data occurrences | ✓ | ✓ | ✓ | `CLAUDE.md` § Documentation Standards + the three `marketplace/bundles/**` prose rules |

The citation-vs-D3 tension the plan flags is resolved as the plan directs: lesson ids remain permitted in
the doctor's own provenance table (its canonical citation home, already allowlisted by
`no-lesson-id-in-skill-prose`), and are forbidden only in *test prose*. No citation was dropped.

**Feasibility note for the prose rule.** The rule scans **docstrings and comments only**, never string
literals. That restriction is the rule's structural discriminator, not an optimisation: measured over
this tree, the citation shapes produce **283** hits in prose against **861** occurrences of the *same
shapes* as string-literal test data (a lesson id fed to the validator under test is the corpus the test
exists to check). A rule flagging both would be textually indistinguishable from a legitimate shape and
therefore infeasible under the provenance contract; scoping to prose makes it feasible.

**Zero-match invariant fed as the plan directs.** Four `FIXTURE_CORPUS` entries were added to
`test/pm-plugin-development/plugin-doctor/_fixtures.py` — not `record_fired`, which is process-local and
invisible across `pytest-xdist` workers. No `EXEMPT_RULE_IDS` entry was added.
`test_zero_match_suite_coverage.py` passes.

**Blanket severity statements corrected.** Both statements the plan names were false the moment a
`warning` rule landed beside the three `error` rules, and both are fixed in
`standards/doctor-test-conventions.md`: § Rules ("All three rules emit findings with `severity: error`")
and § Severity Summary ("All three rules ship with build-failing severity … Suppression is not
provided"). The Severity Summary table gained a row per new rule; the intro line and the plugin-doctor
`SKILL.md` Workflow 10 and rule-index were corrected in the same change.

**One behaviour change beyond the four rules, and why it was necessary.** `cmd_test_conventions`
previously derived `status` from *any* finding, so a `warning`-severity rule would have made the
subcommand exit non-zero — defeating the entire reason the plan specifies `warning`. `status` is now
derived from **error-severity findings only**, and the result carries `error_count` / `warning_count`.
The three existing `error` rules keep their build-failing behaviour unchanged. This scope is not part of
`quality-gate`, so no build gate is affected either way.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **4 files** (`_analyze_test_conventions.py`,
`doctor-marketplace.py`, `_fixtures.py`, `test_test_conventions_rule4.py`). The gate is therefore armed.

`UV_HTTP_TIMEOUT=600 ./pw verify` → **`=== verify: SUCCESS ===`**, `20066 passed, 14 skipped` in 389s.
All three sub-steps ran: quality-gate (`ruff … All checks passed!`, `mypy … Success: no issues found in
405 source files`, `SPDX-header check passed`, plugin-doctor `issues[0]`), test-compile (`mypy(test)`,
751 files), and module-tests.

Per-commit gate: the D1–D4 commit touched no `*.py` (gate not triggered); the D5 commit was preceded by a
clean `./pw quality-gate`.

**Doctor scope over the live tree**, using the epic README's verified invocation with `--test-root test/`:

```text
status: fail   total_issues: 929   error_count: 17   warning_count: 912
  unique-fixture-basenames,2
  subprocess-pythonpath,15
  identifier-validator-corpus,0
  test-module-line-budget,315
  test-helper-module-misnamed,1
  test-module-preamble-boilerplate,342
  test-docstring-historical-prose,254
```

`status: fail` is driven entirely by the 17 pre-existing `error`-severity findings, which this plan does
not fix (out of scope — the reduction plans own them). No new rule reports zero, so no detector is broken
in the sense the plan's verification section warns about. `identifier-validator-corpus` reports 0 because
its registry is empty by design, which is its documented no-op behaviour and not a new zero.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Own test (`test_one_chain_yields_one_finding`) | `_parent_chain_depth` fired once per *suffix* of a `.parent` chain, so a depth-4 chain emitted a depth-4 **and** a depth-3 finding. The docstring claimed outermost-only; the code never checked it | **Fixed** before commit — added `_nested_parent_attribute_ids` to exclude inner links. Live-tree count fell 491 → 342 |
| 2 | Self-review after the fix | The `rule-provenance.md` row still recorded the pre-fix count (491) — a stale claim in a file this run authored | **Fixed** — corrected to 342 |
| 3 | Corpus feasibility (D5) | A naive whole-file matcher for the prose rule hits 291 files / 1730 raw occurrences, most of them legitimate test *data* — textually indistinguishable from the defect and therefore infeasible per the provenance contract | **Resolved by design** — scoped the scan to docstrings and comments, which is a genuine structural discriminator (283 prose vs 861 data) |
| 4 | Observation (not fixed) | `standards/doctor-test-conventions.md` § "Rule 3 — Validator Registry" is still the empty template, so `identifier-validator-corpus` is a permanent no-op over this tree | **Deferred** — populating it is outside this plan's deliverables and touches no D1–D6 clause. Recorded for the epic |
| 5 | Observation (not fixed) | The three pre-existing test-conventions rules have no `rule-catalog.md` rows; only the four new rules do | **Deferred** — the provenance contract binds new rules, and back-filling three unrelated rows would widen this diff beyond its Expected surface |

**Cold-read verification (the plan's mandated by-reading check).** A sub-agent was given the two amended
standards files **and no other context** — not the plan, not the epic README — and asked the plan's three
questions. Its answers, verbatim:

> **Q1 — Test module line budget.** "Settled: 400 lines, and an over-budget module is split by behaviour
> cluster." Quoting: *"**A test module is budgeted at 400 lines.** A module over budget is split by
> *behaviour cluster* into `test_{unit}_{cluster}.py` — never in arbitrary halves, and never by line count
> alone."*
>
> **Q2 — `merge_queue_wait_budget_seconds: 1800`.** "Settled unambiguously: exact literal. This precise
> case is the worked example in the pytest document." Quoting: *"**Write an exact literal where the literal
> is the contract.** … Here the literal is the whole assertion. A generator would replace the one value
> that matters with an arbitrary one, so **a generator is the defect, not the fix**."*
>
> **Q3 — May a docstring name the PR?** "Settled: no." Quoting: *"A test docstring does **not** narrate the
> incident that produced the test, and does not cite: … a PR or issue number …"*
>
> Closing: *"No question was left unsettled or ambiguous by the two documents, and on all three points the
> two files agree."*

All three readings match the plan's expected readings (**400 / split by behaviour cluster**, **exact
literal**, **no**), so no re-wording was required.

## Reviewer participation

Expected population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, not a
list transcribed here:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | _(pending)_ | — |
| `coderabbitai` | _(pending)_ | — |
| `sourcery-ai` | _(pending)_ | — |

Coverage: _(pending — completed before the merge gate)_

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** ~50 minutes from session start to report finalisation. Source: run start against the
  timestamps of the commits on this branch.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ **Not
  comparable** to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch
  tree under plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session
  does not share. The figures cannot be made comparable, so no parity is implied.

## D6 — The two decisions this run may not take

### Proposal 1 — Hypothesis adoption

`hypothesis` is a third-party dependency; adding it to `[dependency-groups].dev` in `pyproject.toml` is a
user-approval step that `pm-dev-python:pytest-testing` already marks as such, and this run has no operator
authority to take it. **The proposal is to add it**, on the evidence that the technique has *zero*
adoption today (`grep -rn 'hypothesis' test --include=*.py` returns one unrelated prose match) while the
tree carries a substantial universal-contract surface.

**Candidates derived, not copied.** Derivation: module-level public functions under
`marketplace/bundles/**` and `marketplace/targets/**` whose names match the universal-contract shapes
(`parse*`, `validate*`, `normali[sz]e*`, `encode`/`decode`, `serial`/`deserial`, `canonicalize`, `slugify`,
`escape`/`unescape`, `coerce`, `to_toon`/`from_toon`), filtered to those actually exercised by a test
today. **Result: 107 functions across 53 modules.**

The three examples the plan seeds from are all confirmed present in the derivation:

| Seed example | Confirmed as |
|---|---|
| `marketplace/targets/opencode/frontmatter.py` `parse_frontmatter` | present (also `marketplace/targets/claude/variant_emitter.py::parse_frontmatter`) |
| the shared `toon_parser` | present — `parse_toon`, `parse_toon_table`, `serialize_toon`, a genuine round-trip encoder triple |
| identifier validators in `doctor-test-conventions.md` § "Rule 3 — Validator Registry" | **the registry is empty**, so this seed resolves to no call sites at all (see Finding 4) |

Highest-value subset, by contract kind:

| Kind | Call sites |
|---|---|
| Round-trip encoders | `ref-toon-format/scripts/toon_parser.py` — `parse_toon` / `serialize_toon` (the strongest candidate: an actual encode/decode pair) |
| Format parsers | `_gradle_cmd_parse.py`, `_maven_cmd_parse.py`, `_npm_parse_{errors,eslint,jest,tap,typescript}.py`, `_pyproject_cmd_parse.py` — eight `parse_log` implementations of one contract shape |
| Frontmatter parsers | `marketplace/targets/{opencode,claude}` `parse_frontmatter` |
| Identifier normalisers / canonicalisers | `_step_key_canonical.py::canonicalize_step_key`, `ci_base.py::normalize_issue_ref`, `_ci_log_filter.py::slugify_check_name`, `permission_fix.py::normalize_path_perm`, `_config_core.py::normalize_keys` |
| Argument-surface parsers | `argparse_surface.py` — `parse_choice_list`, `parse_flag_arity`, `parse_help_node`, `parse_required_flags` |

**Relationship to the later plans, stated as the plan requires.** This is the **whole-tree** list; two
later plans refine disjoint halves of it. Plan `060` § D5 derives the candidates in the runtime and
script-substrate slice; plan `080` § D5 derives them in the generator slice. Both run after this plan and
both seed from the same three examples. The operator therefore receives **one list refined twice**, not
three unrelated lists: this table is the superset, and `060`/`080` narrow it to their own surfaces. The
column set is fixed here (call site / contract kind) so the two refinements are diffable against it.

### Proposal 2 — Flipping the four D5 rules to `error`

The rules ship at `warning` because the tree violates all four at scale, and a build-failing rule landed
over a non-compliant tree fails every subsequent build until the tree complies — blocking the very plans
that would fix it.

**Per-rule violation counts, re-derived at report time** (not carried over from the plan):

| Rule | Violations now | Flip condition |
|---|---|---|
| `test-module-line-budget` | **315** | reaches 0 |
| `test-helper-module-misnamed` | **1** | reaches 0 — nearest to flippable by a wide margin; the single violation is `test/plan-marshall/manage-config/test_helpers.py` |
| `test-module-preamble-boilerplate` | **342** | reaches 0 |
| `test-docstring-historical-prose` | **254** | reaches 0 |

**The proposal:** flip each rule to `severity: error` as a follow-up, per-rule and independently, once its
own count reaches zero — not as a single all-four flip, since `test-helper-module-misnamed` is one fix away
while the other three depend on the full `030`–`080` reduction wave. Flipping it early buys enforcement at
almost no cost; coupling it to the other three defers that for no reason.

## Contract check (Step 9)

_(completed at Step 8 condition 3, before arming auto-merge)_

## What have we learned (Step 9)

_(completed at Step 8 condition 3)_

## Residue

* **Finding 4** — the Rule 3 validator registry is empty, making `identifier-validator-corpus` a
  permanent no-op. Belongs to whichever plan owns identifier-validator coverage; not this one.
* **Finding 5** — the three pre-existing test-conventions rules have no `rule-catalog.md` rows. A
  provenance-audit housekeeping item.
* **Plugin cache sync** — per `CLAUDE.md` § Standalone Plan Lane, a cloud run neither performs nor owes
  `/sync-plugin-cache`; it is a machine-local build step reading the git-ignored `target/`. Recorded here
  only because the plan's Notes ask for it. A developer refreshing a local cache after this lands does so
  as a local concern, not as a debt this run tracks.
* **Sequencing** — this plan and `020` are the epic's two blocking plans. `030`–`080` may start once both
  have landed on `main`. Plan `080` renames `test/pm-plugin-development/plugin-doctor/_fixtures.py` and
  will inherit it carrying four test-conventions entries, as its D1 anticipates.
