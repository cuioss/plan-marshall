# Landing Analysis: PLAN-07 — Unit-Test Coverage & Gating Truthfulness

epic: test-suite-quality
workstream: WS-03
pr: #1012 (`ae0d8d79b`, squash-merged via merge queue)

> Landing record for one shipped plan. Lives at `landings/PLAN-07.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

5/5 shipped. Every verdict below was checked against the merged tree at `ae0d8d79b`, not
accepted from the landing narrative — and that discipline caught one material divergence
(D2, below), so the corroboration earned its cost on this landing.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 coverage-scope decision — TAKE it | shipped-as-specified, **documented not widened** | `pyproject.toml` +12 lines of rationale above `source = ["marketplace/bundles"]`; `doc/developer/testing.adoc` +16. The decision was to **keep** the restricted denominator as a deliberate product-surface scope. Bonus finding recorded in the comment: `build.py:cmd_coverage` passes `--cov={bundle_path}` on every invocation, so **changing `source` alone would have been inert** — widening needs both sites in lock-step. That is a genuine discovery the spec did not anticipate |
| D2 dead `discover_modules` tier — delete-or-revive | shipped-modified — **DELETED** (a spec-sanctioned option), and **extended well past the declared surface** | Whole `test/plan-marshall/integration/**` and `test/integration_common/` trees absent from `ae0d8d79b` (`ls-tree` returns empty). Net **−4173 / +168** across 56 files |
| D3 four weak Gradle assertions — strengthen | shipped-as-specified, genuinely strengthened | `test_gradle_discover_modules.py` +84/−13: exact values now asserted — `paths.sources == ['src/main/java']`, `stats.source_files == 2`, `paths.readme == 'README.md'`, and a full 10-command expected set with `assert_command_uses_executor` per command. **No assertion weakened**; the `shutil.which('gradle')` probe was replaced by a runtime-shape branch |
| D4 `pre-push-quality-gate` `mypy test` parity | shipped-as-specified, **best-executed item in the plan** | `pre-push-quality-gate.md` +52/−13: a third guard inserted as quality-gate → **test-compile** → module-tests, explicitly mirroring `build.py:cmd_verify`'s CI order. Frontmatter `description`, both Mark-Step-Complete branches, and both `display_detail` strings all updated in lock-step |
| D5 RU-4/M4 residue — verify then resolve | shipped-as-specified, closed as **explicit closure rationale** | `doc/developer/build.adoc` +10 — the Cobertura-vs-JaCoCo fixture-format mismatch re-verified as still accurate and moved out of a squashed commit message into discoverable docs. The real blocker filed as lesson `2026-07-26-20-001` (verified present in the live store) |

### D2 — two things worth recording

**(a) The PR body describes the opposite of what shipped.** Its D2 paragraph states the tier was
*"revived … with in-repo fixture projects … so `test_gradle_discover_modules_integration.py` and
`test_maven_discover_modules.py` are CI-runnable"*, and its Changes list describes
`test_hybrid_merge.py` / `integration_common/__init__.py` / `conftest.py` as *"shared
integration-test scaffolding **supporting the revived tier**"*. The merged tree contradicts all of
it: those files are **deleted**, and the fixture resources under `discover_modules/resources/**`
(which already existed at the parent commit) were deleted too. The most likely history is a
revive-then-reverse inside the plan, with the PR body authored at the revive stage and never
re-synced after the reversal. **The outcome is spec-compliant** — D2 offered delete outright as a
first-class option and even anticipated "delete-for-now" — so this is a *record* defect, not a
scope defect. It matters because the PR body is the durable public artifact the retrospective
corpus and future readers consult, and here it asserts the inverse of ground truth. This is the
epic's own recurring `2026-07-21-22-001` archetype (recorded claim ≠ ground truth) landing in the
plan's own PR body.

**(b) The deletion extended past the declared Expected Surface, and the extension is justified.**
The spec named only `test/plan-marshall/integration/discover_modules/**`. Also deleted:
`test/integration_common/__init__.py` (435 lines) and
`test/plan-marshall/integration/module_aggregation/test_hybrid_merge.py` (246 lines). Both were
independently verified as the same dead-tier class — `git grep "def test_"` returns **zero** in
both (sanity-checked: plain `def ` returns 15 and 3, so the grep was live), and `test/conftest.py`
shows all three files were already listed in `collect_ignore`, i.e. **never collected by any
run**. So the enlarged deletion removed code that was doubly dead: no test functions, and excluded
from collection regardless. Verdict: a correct extension, but it does mean the surface declaration
under-stated the diff by ~700 lines of deletion plus a fixture tree.

## Metrics and Anomalies

- **Tokens**: 3,006,279 total. Phase outliers: `6-finalize` 1.21 M (40 %), `3-outline` 771 K (26 %).
- **Duration**: 3 h 5 m worked against 12 h 18 m wall (9 h 13 m idle); `3-outline` alone reports
  4 h 54 m wall for 42 m worked.
- **Anomalies**:
  - **Planning-to-execute ratio 4.3 : 1** — 1.43 M tokens across phases 1–4 vs 331 K for execute,
    on a tech-debt change whose largest single act was a deletion. Driven by a `cross_cutting`
    deep-lane escalation. This is the epic's most planning-heavy landing.
  - **Phase-breakdown reports `n=5/6`** — one phase contributed no worked-time or tool-use figure,
    so the 3 h 5 m and 1028 tool-uses totals are both under-counts of unknown size.
  - **Plugin cache was stale by several merges mid-run** (retrospective finding 1): the cached
    `retro_sections.py` lacked the `chat-history-analysis` aspect from #998, and its refusal
    message blamed the caller rather than the stale cache — a misattributing error message, the
    same confident-signal-hides-a-caveat shape this campaign keeps surfacing. Re-synced at
    `0.1.1222` with the on-main executor regenerated.

## Routing and Merge Behavior

- **Review**: **thinner than configured, again.** Three bots enabled (CodeRabbit, Sourcery,
  PR-Agent); CodeRabbit and PR-Agent ran, **Sourcery SKIPPED**. Two comments fetched, both
  classified noise ⇒ **zero findings stored**, so `finalize-step-review-retrospective` had nothing
  to compare and produced no comparative verdict. This is the **third consecutive** near-zero
  automated-review yield on this epic's shape (see the standing watch) and the second recent
  instance of fewer bots running than are enabled — do not read the clean pass as corroboration.
- **CI/merge**: all checks green (run `30219129112`); rebased onto `origin/main` picking up 2
  upstream commits; merged via merge queue; branch cleaned up; worktree removed; tree clean at
  `ae0d8d79b`. **No collision** — PLAN-07 ran alone under `N = 1`, so no pairing evidence was
  generated this round.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-07 → `shipped`, pr `#1012`, landing `landings/PLAN-07.md`
- [x] epic.md queue row reconciled from status.json
- [x] Watch retired: "Coverage-scope blind spot" (D1 took the decision)
- [x] Watch retired: "RU-4/M4 and RU-7 residue" (D2/D3/D5 closed all three strands)
- [x] Watches opened: PR-body-vs-diff divergence; `test-compile` unresolvable at default scope;
      `build.py` classify_paths block; residual open dimension of `2026-07-24-13-001`
- [x] Watch reinforced: automated-review yield (3rd consecutive), now with the bots-skipped dimension
- [x] resume_anchor updated
- [x] START-HERE block regenerated

**Lesson dispositions — VERIFIED against the live store, not the plan report.** Housekeeping
reported "1 removed, 1 adapted" against two bound lessons; both dispositions check out and the
verify-still-open gate is the reason:

| Lesson | Reported | Verified in live store | Verdict |
|--------|----------|------------------------|---------|
| `2026-07-21-16-001` | retired | `not_found` — absent | **Correctly retired.** D2 + D3 fully consumed it |
| `2026-07-24-13-001` | adapted | **present, `active`**, body rewritten | **Correctly NOT retired.** The `test-compile` dimension is closed and the body says so explicitly; but a **different** missing dimension recurred on #1008 — the gate still runs only bundle-scoped `quality-gate`, so the whole-tree plugin-doctor pass stays un-gated locally. The lesson stays active on that residue |

That is the **third consecutive** WS-03 plan where the verify-still-open gate prevented a false
retirement (PLAN-09 trimmed two, PLAN-07 adapted one). The control is established — keep it bound
into every remaining spec.

## Follow-Ups

Four new items, none folded silently:

1. **`2026-07-24-13-001` residual dimension** — pre-push gate runs bundle-scoped `quality-gate`
   only, so the marketplace-wide plugin-doctor pass is un-gated locally (cost: one push→CI
   round-trip on #1008). **Natural fit for PLAN-08** (finalize machinery, same file D4 just
   edited) — recorded as a watch with that owner proposed, NOT folded unilaterally, because
   PLAN-08's spec would need re-scoping and that is an operator call.
2. **`test-compile` does not resolve at default scope** — `_pyproject_cmd_discover._build_commands`
   never emits `test-compile` for any module, so D4's guard uses a documented bypass (module-scoped
   resolve with the module argument dropped). Deliberately recorded rather than fixed, being a
   production change to build-system discovery. Watch.
3. **`build.py` is unplannable** — it matches no `_CLASSIFY_PATTERNS` entry in `build-pyproject`'s
   `classify_paths()` (though `classify_globs()` routes it), so any deliverable naming `build.py`
   resolves to the `unknown` bucket and **blocks at plan time**. Filed as lesson
   `2026-07-26-20-001` (verified present). This blocks the known-wrong `build.py:392` `verify`
   help text, which denies the very chain D4 just achieved parity with. Watch.
4. **New lesson `2026-07-26-22-005`** — `manage-change-ledger` ships a Rule-5-forbidden `query`
   verb, and no gate can see it because `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` is table-driven and
   the script has no table row. **Belongs to `truthful-signals`, not this epic** — it is the
   vacuous-guard archetype (a guard whose population is defined by the same artifact whose absence
   is the defect), which is that epic's declared theme. Recorded here as a pointer only; the
   ledger write-boundary means this epic does not stage it.
