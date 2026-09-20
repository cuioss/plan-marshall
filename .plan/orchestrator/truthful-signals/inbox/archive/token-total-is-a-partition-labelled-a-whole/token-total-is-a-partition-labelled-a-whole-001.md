envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=landing
created=2026-08-03T12:31:38Z

## What landed

**PLAN-TRUTH-035 — "token total is a partition labelled as a whole"** shipped as **PR #1083**, squashed to `3a20814b1` on `main` (parent `e1ae38142`).

The plan removed a mislabel at the top of the metrics surface: `total_tokens` on a phase row was rendered as if it were one homogeneous measurement when it is in fact a partition over two disjoint populations — main-context (inline) tokens and dispatched-subagent tokens. A Total row that summed across both presented a cross-population figure under a single-population label.

Shipped mechanics:

- A `total_tokens_population` discriminator (`inline` / `mixed` / `dispatched`) stamped on every phase row by `manage-metrics enrich`, plus a separate `inline_main_context_tokens` field so the inline part is a field of its own population rather than an addend.
- Render-side labelling in `cmd_generate`: the `Tokens` column header reads `dispatched unless marked`, inline cells carry their marker, and a Total that spans populations carries `(spans populations)`.
- Partiality markers `(n=k/6)` on Total cells whose contributing subset is smaller than the canonical six-phase baseline.
- A key-space + population guard for the `plan-efficiency.md` calibration-anchors table (`test_plan_efficiency_anchors.py`), which had rotted in both directions at once — 8 dead rows and 31 live `(scope_estimate, change_type)` pairs with no row at all.
- Cascading doc corrections across `manage-metrics/SKILL.md`, `manage-metrics/standards/data-format.md`, `phase-6-finalize/standards/record-metrics.md`, `plan-retrospective/references/plan-efficiency.md`, and the `audit-archived-plan-retrospectives` checks.
- A new standing rule in `persona-plan-marshall-agent/standards/agent-behavior-rules.md`: *never assert closure over an enumeration without re-checking it against its declaring source.*

13/13 tasks, 7 commits on the feature branch before squash.

## Operator decisions that superseded the spec

Three decisions were taken during execution and are the authority over the written spec:

1. **Relabel, do not delete.** The inline figure stays rendered and is labelled, rather than being dropped from the Total.
2. **`dispatched unless marked`** is the column-header form (not a per-cell `dispatched` suffix on every row).
3. **Label-only anchors** — the calibration-anchor guard asserts key-space completeness, it does not assert anchor VALUES.

## Residue the epic should track

- **The plan's own fix reproduced the plan's own target defect.** `cmd_enrich` was not idempotent: a second run read its own prior inline fold as a dispatched total and re-stamped the row `mixed`, at which point `cmd_generate` stopped collecting it into `inline_population_phases` and the Total silently lost its `(spans populations)` marker. Fixed on-branch by TASK-14, but it was caught by two review bots, not by the plan. Filed as a `candidate-lesson`.
- **`baseline-reconcile` misclassified twice in this one run**, on a gate that can trigger an unattended `git merge`. Filed as a `candidate-lesson` with a code-verified root cause that is wider than the symptom.
- **A four-site doc cascade took four passes to close**, each of the first three asserting a closure it had not verified — against the very rule this plan added. Filed as a `candidate-lesson`.
- **CodeRabbit's GitHub check read `SUCCESS` over a commit range it never reviewed.** Routed to the `review-apparatus` epic, not here.
- **The plugin registry-pin inversion fired again mid-finalize**, inside this finalize's own dispatch envelope. Filed as a `candidate-lesson`.

## Signals at finalize

- Q-Gate findings: 5 total (4 in `6-finalize`, 1 in `5-execute`), **0 pending** — all resolved in-run.
- Automated review: 7 `pr-comment` findings, 6 `fixed`, 1 `rejected`. Reviewers that actually participated: **coderabbit** (4 inline + 1 review body) and **pr-agent** (`cuioss-review-bot`, 1 issue comment). **Sourcery: SKIPPED.**
- Script-failure clusters: 0.
