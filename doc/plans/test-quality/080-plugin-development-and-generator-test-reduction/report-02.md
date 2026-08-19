# Run report — 080-plugin-development-and-generator-test-reduction (run 02)

**Date (UTC):** 2026-08-19    **Branch:** `chore/plugin-dev-generator-tests-run-02`    **PR:** _pending_    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

A **re-entry** of a landed plan, as the epic README sanctions: a new report ordinal in the same
directory, the plan's deliverables unchanged. Run 01 (PR #1302, merge commit `6427016`) recorded its
unfinished work in `report-01.md` § Residue; this run closes the reachable part of it.

## Skills loaded

`cloud-plan-lane`, from `.claude/skills/cloud-plan-lane/SKILL.md`. The surface is `test/**` only, so the
one domain skill the work touches is `pm-dev-python:pytest-testing`, whose house rules reach this run
through `doc/plans/test-quality/README.md` § House style (**B1**–**B10**).

**Branch form: run-created**, not harness-assigned. The session's original `claude/*` branch was
consumed by run 01 and locked at enqueue, so this run cut a new one under the closed prefix set —
`chore/` for maintenance and refactoring, per `CLAUDE.md` § Branch Naming.

## Deliverables

Run 01 completed D1, D2, D4 and D5 and left D3 partial. This run addresses D3's two open halves.

| # | Deliverable | Run 01 | Run 02 |
|---|---|---|---|
| D3 **B6** — namespaces from the real parser | 184 of 211 | **211 of 211 — complete, 0 remaining** |
| D3 **B7** — one import preamble | 59 → 9 findings | **9 → 2** |
| D1 — scaffold conversion | 51 of 57 modules | **unchanged, and deliberately** — see below |
| D2, D4, D5 | Done in run 01 | not re-opened |

### D3 § B6 — complete

| Measure | Before | After |
|---|---:|---:|
| Hand-built `argparse.Namespace` in the slice | **27** | **0** |
| `parse_ns` template calls | 25 | **39** |

⚠️ **The population needs restating, because the plan's own re-derivation command over-counts.**
`grep -c 'Namespace('` also matches `types.SimpleNamespace(` — 11 in this slice, never a B6 target — and
the after-count additionally contains the `_ns` overlay helper's own body, one per converted module. The
figure above is hand-built `argparse.Namespace` **only**, which is what B6 is about.

**`profiles.py` is the concrete case for why B6 matters.** Its real parser yields a **`plan_id`**
attribute that none of the five hand-built namespaces in that module carried at all — so those tests
were passing against a namespace the CLI cannot produce, which is precisely the defect B6 exists to
remove. It was found by doing the conversion, not by arguing for it.

**Ambiguous shapes are keyed on the handler, never on the kwarg set.** `profiles.py`'s `unmatched` and
`suggest` both take only `--project-dir`; each site uses the template for the handler it actually feeds.
The verification round confirmed this independently and by a stronger method than test outcome — the
parsed namespaces carry the parser's own `func` binding, so `_REVIEW_NS.func is cmd_review` and its
siblings settle the pairing directly. `profiles.py` has no `func`; its `handlers` dict was read instead.

**Every one of the 39 `parse_ns` calls is at module scope** (column 0), so none re-executes its script
module per test — the hazard the plan names explicitly.

### D3 § B7 — 9 → 2, and the third survivor was mine, not the tree's

Skill-root `extension.py` loads now route through `conftest.load_skill_module`. Five path constants left
dead behind them were removed — **ruff does not flag an unused module-level constant**, so they would
have survived the lint that cleaned up the `importlib` imports beside them.

⛔ **The first commit of this run kept a third survivor on a false rationale, and the verification round
caught it.** That commit reported that `test/marketplace/test_extension_profiles.py` could not be
converted, because routing it through `load_skill_module` pushed the loader-collision guard to 91
unresolved call sites against a bound of 90, and the guard's own comment forbids growing that bound.
Both halves are true. **The conclusion was not.**

The walker skips any call that opts out of registration
(`test/plan-marshall/script-shared/_loader_contract_fixtures.py:220`), and the rule's own message names
the escape verbatim: *"pass a distinct `module_name` — **or `register=False`** — or they displace each
other."* Passing `register=False` converts the module, leaves the unresolved count at exactly **90**, and
is **behaviour-identical** to the preamble it replaces, which never touched `sys.modules`.

The rule this run now applies, stated once so it is reusable:

> A **literal** `module_name` where the guard can read it; **`register=False`** where the name is
> computed and the guard cannot.

**The two remaining survivors are genuinely unreachable, and the reason is structural rather than
budgetary.** `test/marketplace/targets/test_dist_manifest.py` loads `marketplace/targets/generate.py`
and `test/marketplace/test_spdx_enforcement.py` loads the repository-root `build.py`. `MARKETPLACE_ROOT`
is `marketplace/bundles`, so neither `load_skill_module` nor `get_skill_dir` can address either file.
This is not a residue a later run can close by spending more budget.

### D1 — not re-opened, and that is the finding

The dispatch brief named "the unconverted D1 modules" as run 02 scope, and the verification round
correctly flagged that no `test_analyze_*.py` appears in this diff: 51 of 57 import
`assert_analyzer_findings` at both `main` and HEAD. **That is the right outcome, not an omission.**
Run 01 characterised all six individually — a two-argument analyzer, a subset assertion the scaffold's
full-multiset comparison would change, a results-not-findings return, two modules with no analyzer call
at all, and a verifier-echo test. None became convertible between runs. The brief overstated the scope;
the deliverable did not understate it.

## Build gate

**Python-change verdict.** `git diff --name-only origin/main...HEAD -- '*.py'` returns 12 files, so the
gate applies.

**The gate that was actually run is the full one**, which is the correction run 01 owed: its C1 finding
was that `./pw quality-gate` plus targeted `pytest` had been substituted for `./pw verify`, so
`test-compile` never ran and CI rejected the branch. This run ran `./pw verify` **four times** — after
the B6 conversion, after the B7 conversion, after the revert, and after the verification fixes.

```text
21070 passed, 14 skipped
=== verify: SUCCESS ===
```

Read from the tool output rather than the exit code: `ruff … All checks passed!`,
`mypy … Success: no issues found in 415 source files` (production), `Success: no issues found in 778
source files` (test-compile), `SPDX-header check passed`, and a pytest summary with 0 failed / 0 errors.

⭐ **The full gate earned its cost twice in this run.** The B7 conversion initially failed
`test_conftest_loader_contract.py` — a failure `quality-gate` alone cannot see, because it is a test, not
a lint. And three blank-line defects the diff introduced were invisible to the gate for the opposite
reason: the project runs ruff with **preview off**, so `E301`–`E306` never fire. They were found by
running `ruff --preview` over the changed files and diffing against `origin/main` (3 on HEAD, 0 at
baseline), and fixed.

**Stale-base re-verification (§ Step 8 condition 2).** `git rev-list --count HEAD..origin/main` = **0**
at the gate — the base is current, so no merge was needed and no throwaway-branch shape was used.
Recorded as the measurement it is; the count is re-derived immediately before arming.

## Findings

Every finding is from the pre-PR verification round unless marked otherwise. Recorded per instance.

| # | Finding | Disposition |
|---|---|---|
| V1 | `test_python_derivation_resolver.py` docstring said the module is loaded "by explicit file path … via `spec_from_file_location`"; the body now resolves by identity | **Fixed** |
| V2 | Same shape at `test_documentation_extension.py` and `test_path_attribution.py` — both said "by explicit path" | **Fixed** (2 instances) |
| V3 | **The run's own commit message asserted a false rationale** for keeping the third B7 survivor — `register=False` clears the finding and leaves the guard's count at 90 | **Fixed**: the module is converted, B7 is 9 → 2, and the correction is stated in the commit that made it and again above. The original commit message is immutable on a pushed branch, so condition A is discharged by stating the correction here |
| V4 | Six new `sys.modules` registrations where the replaced preambles registered nothing — a real behavioural delta whose bound held but was written nowhere | **Bound recorded** — see below |
| V5 | Three blank-line defects (`E305` ×2, `E302`) introduced by the template insertion and the constant removal, invisible to the gate because ruff runs with preview off | **Fixed**; verified 3 → 0 against an `origin/main` baseline of 0 |
| V6 | D1 residue untouched against the brief's stated scope | **Not a defect** — see § D1 above. Recorded so the discrepancy is explicit rather than silent |
| V7 | `report-02.md` owed; the line delta is **positive**; an already-over-budget module grew | **This report**; figures below |
| V8 | Four pre-existing items outside this run's surface | **Recorded below with owners** |

### V4 — the one behavioural delta, characterised under B(a)

Six `load_skill_module` calls take the default `register=True`, where the `spec_from_file_location`
preambles they replace never touched `sys.modules`. The new registrations are
`extension_pm_dev_frontend_cui`, `extension_pm_dev_python_resolver`, `pm_documents_extension`,
`plugin_dev_extension`, `pm_plugin_dev_extension`, `pm_plugin_development_extension_wt`.

**It cannot change what the deliverable does**, and the proof is executed rather than argued: all six
names are distinct from each other and from every other loader-registered name tree-wide; none is
imported plainly anywhere, which the loader-contract guard asserts and which is green; and the slice was
run in default **and reverse** directory order with identical results. The seventh conversion takes
`register=False` precisely because its name is computed, so it adds no registration at all.

### V8 — outside this run's surface, with owners

| # | Finding | Owner |
|---|---|---|
| R1 | `doc/plans/test-quality/README.md` § "What the executed half left open" still says "`030`–`060` have landed" and carries no `080` row. It **restates current state** — the section exists so a follow-up can be commissioned without reading six reports — so unlike a run report it is not a record and is now false | **`120`**, or the next edit to that README |
| R2 | `plugin-script-architecture/standards/testing-standards.md:356-369` still teaches the hand-rolled `spec_from_file_location` preamble as house style, contradicting the doctor rule and `conftest`'s loaders | **`090`** — `marketplace/bundles/**` is its exclusive surface |
| R3 | `plan-marshall/skills/phase-3-outline/standards/consumer-sweep.md:109,135,150,157` names `test/pm-dev-java/manage-maven-profiles/test_profiles.py`; the real path is `.../maven-profile-management/...` | **`090`** |
| R4 | Two pre-existing duplicate loader module names inside this slice — `extension_pm_dev_java` and `extension_pm_dev_python`, each pair loading the identical file. Harmless today, but the collision guard detects only load-vs-plain-import, not load-vs-load | **`090`** (loader mechanics), recorded as a guard-coverage gap rather than a live defect |

### Stop record (§ Step 6, "When the loop stops")

* **Exit: `verifier-clear`.** Budget five; the plan sets none. **One** round ran, no extension needed.
* **The verifier's own last answer**, quoted: *"**Yes — three things remain that A or B forbids leaving
  open**"* — A violated by V1/V2 (false mechanism docstrings) and by V3's rationale, B violated by V3's
  mis-characterised survivor and mildly by V4's unrecorded bound. **All five are now fixed or recorded**,
  which is what A requires: A is discharged by the repair, not by another round of verification.
* **The evidence is stronger than a read.** The round simulated the loader-collision walker on the exact
  candidate call shape (`counted_unresolved` False with `register=False`, True without), ran the doctor
  on a converted copy against an unconverted control (`1` → `0`), dumped `vars(parse_ns(...))` for all
  14 templates and compared every overlaid key per site, resolved handler pairing through the parser's
  own `func` binding, and ran the slice in both directory orders — each returning a verdict that could
  have come back otherwise.
* **Were the findings narrower?** Only one round ran, so no trend is claimed. Its composition is worth
  stating: of eight findings, **one was a false rationale in the run's own commit message**, three were
  false statements in prose the run had just written, and none was a weakened assertion or a lost test.
* **Residue to assume remains.** Read the deliverables as still carrying defects of the kind this round
  found — **prose describing a mechanism the code no longer has, and rationales asserted rather than
  executed**. A second round would most profitably re-read every sentence this run wrote about *why*.
* **No survivors.** Nothing is left open under B; V4 is characterised under (a) above.

## Reviewer participation

_Pending — recorded before the merge gate._

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** not separately instrumented; four full `./pw verify` runs (~6–7 min each) dominate.
* **Population:** this single Claude Code cloud session. ⛔ **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a per-task billing
  boundary this session does not share.

## Measured deltas (D5, for this run)

| Measure | Before (`origin/main`) | After | Delta |
|---|---:|---:|---:|
| Slice lines | 61,818 | 61,892 | **+74** |
| Collected tests (slice) | 3,357 | 3,357 | **0** |
| Hand-built `argparse.Namespace` | 27 | **0** | −27 |
| `parse_ns` template calls | 25 | **39** | +14 |
| `test-module-preamble-boilerplate` | 9 | **2** | −7 |
| `test-module-line-budget` (slice) | 43 | 43 | 0 |

⚠️ **The line delta is POSITIVE, and that is expected rather than a failure.** A B6 conversion is
line-positive by construction — it replaces a one-line hand-built namespace with a module-scope template
plus an overlay call — and plan `100` independently records the same property for its own cluster
("line-neutral to slightly positive"). The epic's § "Why there is no line floor" governs: the delta is
**reported, not targeted**, and no assertion, rationale or comment was deleted to move it.

**One already-over-budget module grew**: `test/pm-dev-java/maven-profile-management/test_profiles.py`,
**537 → 563** lines (+26), the largest single growth in the diff. **No module newly crossed the 400-line
budget** — the slice's over-budget count is unchanged at 43 (42 this plan's, 1 plan `010`'s). Splitting
it is plan `100`'s row 6, whose stated prerequisite (`080` landed) is now met.

**Coverage (Verification condition 2) was NOT measured this run**, and is stated as unmeasured rather
than assumed: the diff changes no production code and no test count (3,357 both sides), so coverage
cannot fall, but that is an argument, not a measurement.

## Contract check (Step 9)

_Pending — completed before the merge gate._

## What have we learned (Step 9)

_Pending._

## Residue

**Closed by this run:** B6 entirely (0 remaining); B7 down to its structural floor.

**Genuinely unreachable, not budget:** the 2 remaining preamble findings —
`marketplace/targets/generate.py` and the repository-root `build.py` are outside `marketplace/bundles`,
so the skill-root loader cannot address them. A future fix would need a new conftest accessor, which is
`090`'s surface.

**Left by design:** the 6 unconverted `test_analyze_*.py` modules (each characterised in `report-01.md`
§ D1); the 42 over-budget modules (**plan `100` row 6**, now unblocked).

**Handed on:** R1–R4 above.
