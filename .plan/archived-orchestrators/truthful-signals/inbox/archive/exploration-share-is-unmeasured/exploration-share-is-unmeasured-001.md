envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=landing
created=2026-07-29T04:49:53Z

## What landed

Plan `exploration-share-is-unmeasured` — PR #1043, merged from `feature/exploration-share-is-unmeasured`, CI green at `0739dac8`.

Theme fit: this plan attacks the epic's own theme (a confident signal hides a caveat) by making exploration share a *measured* quantity instead of an asserted one.

### Deliverables (5)

- **D1 — gate / empirical confirmation.** H1 confirmed: `tool_use.name` is present on 100% of ~575k items across 9,779 transcripts. Settled the classification (41 raw tool names → 5 buckets, fail-open `unclassified`) and the denominator: **payload-byte share is PRIMARY**, turn share SECONDARY, **token share REJECTED** — `message.usage` is per-message, so a tool_result's cost lands in a *later* message and no per-tool token attribution exists without re-tokenizing. Baseline: **76.84% payload-byte share, 16.90% turn share**.
- **D2 — emission.** Ten per-phase counters emitted from the transcript engine through `cmd_enrich` into `metrics.toon` + `generate`, across **all five** read paths of the shared per-phase bucket. Absent-vs-zero enforced by a **presence** test, deliberately diverging from the neighbouring truthiness guard.
- **D3 — auditor check.** New `exploration-share` cross-plan auditor check (the 23rd), corpus-relative thresholds, degenerate-corpus guard, registered at every count site.
- **D4 — standard.** Citations-only return shape lifted into a new standard, with a **population-derived** conformance detector.
- **D5 — outcome: NOT-YET-MEASURABLE** (finding `c0d568`). All 17 archived plans predate D2, so all 17 are excluded and `plans_in_corpus=0`. This is the *designed third outcome*, recorded as such rather than dressed up as a pass.

### Residue the epic should track

1. **Measurability is deferred, not achieved.** D5 is a real, honest null result: the check cannot report until enough post-D2 plans have archived. The epic should re-run the `exploration-share` auditor check once the corpus contains post-D2 plans, and treat "still `plans_in_corpus=0`" as a signal in its own right if it persists.
2. **Production residue from TASK-11 (open).** `audit.py`'s `write_persisted_report` derives its output path from `Path.cwd()` and never consults `--plan-dir`. TASK-11 fixed only the *test* side (`monkeypatch.chdir`). The production path-resolution defect is still live. Filed separately as a candidate-lesson.
3. **Review coverage was 1-of-3.** CodeRabbit and Sourcery both rate-limited; CodeRabbit reported `completed: true` over a refusal comment. Operator-accepted. Filed separately as a candidate-lesson because it is a direct instance of the epic theme.
4. **Router under-scoped this plan at init.** `scope_estimate` was derived from ONE detected path because the spec wrote its paths in backticks, routing the plan to the `light` lane / `minimal` posture. The operator escalated to `deep`/`auto`. Filed separately as a candidate-lesson — also a direct instance of the epic theme.

### Defects caught during the run (all in this plan's own new code/tests)

| # | Where | Defect |
|---|-------|--------|
| 1 | TASK-9 | Over-strict exact-list-equals assertion on orthogonal flags |
| 2 | TASK-10 | Leftover restatement sentence — caught by the plan's own new D4 conformance detector |
| 3 | pre-submission-self-review | Doc-contract divergence: `manage-metrics` SKILL.md's enrich field enumeration omitted the ten new counters while `data-format.md` had them |
| 4 | TASK-11 (CI) | Pollution-guard leak — see residue item 2; under `-n auto` the leak also blamed 3 unrelated tests as collateral |

Notable: the plan's own D4 detector caught a defect in the plan's own D4 work (#2), and the D3 test-authoring produced the pollution leak (#4). Both are self-referential quality signals worth the epic's attention.
