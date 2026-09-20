# PLAN-PRQ-11: Spend and diagnostic aspects count the wrong population too

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-19 from `prq-06-a-lane-override-that-cannot-take-effect-is-007.md`, `-008.md`, `-023.md`
(one signal, filed as three messages by the same run — see D1's Claim Labels) and `-010.md`, all filed
first-party by `PLAN-PRQ-06`'s own retrospective (PR #1541, `a1dd4901f`) and delivered to this epic's
inbox by hand after `emit-landing` failed open. Split out of `PLAN-PRQ-09` rather than folded into it —
same THEME ("reads an available population and counts the wrong thing in it") but a different tier
(spend/diagnostic aspects, not recall/coverage aspects); folding both in would have pushed PRQ-09 to 8
deliverables, past the Scope-Bloat Split Guard's ~6 presumption.

## Objective

**Two retrospective diagnostics read a population that IS available and misclassify it** — one collapses
a correct action and a stall into one "waste" figure, the other collapses an executor guard firing
correctly and a genuine product bug into one "internal error" count. Both are `PLAN-PRQ-09`'s exact shape
(a population that is READ, not missed — counted wrong) applied to the spend/diagnostic tier rather than
the recall/coverage tier.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the script-failure and wait-time populations across the archived corpus.** (a) Per
archived plan, `script-failure-analysis`'s per-failure classification (`bug` / `script_internal_error` /
other) joined against whether the underlying call was a genuine product defect or an executor-guard
firing (invalid notation, invented flag, malformed argv). (b) Per archived plan, `script_cost_rollup`'s
wait-classed call population (`build_server`, `ci`, `ci_complete_precondition`) joined against whether
each wait resolved with useful signal (a real CI/build outcome) or was itself the diagnosable delay. ⛔
One plan's 26 script failures / 2,051 wait calls is an instance; publish both corpus figures before
choosing a fix shape.

**D1 — `script-failure-analysis` states which failures are call-construction drift, not product bugs.**
On `PLAN-PRQ-06`, 22 of 26 script failures were three clusters, none a product defect: 8
`architecture search` invented-flag rejections (no path-scoping flag exists — an agent-usage gap, not a
tool bug), 4 notation underscore/hyphen internal errors, and 10 further invalid-notation executor
rejections. `script-failure-analysis` currently files the executor-guard-firing-correctly rows as `bug` /
`script_internal_error`, inflating the plan's internal-error count. Add an `invalid_notation` subtype
distinct from `script_internal_error`, and publish a partition (`product_defect` vs.
`call_construction_drift`) that sums to the total. ⛔ Two adjacent asks are OUT of this spec's territory
and must not be folded here — see Dependencies.

**D2 — `script_cost_rollup` states which wait was deliberate and which was a stall.** `build_server`
(27.4%), `ci` (27.3%) and `ci_complete_precondition` (23.1%) — 77.8% of 14,423,580 ms over 2,051 calls on
`PLAN-PRQ-06` — are reported as one undifferentiated cost population. One of those waits was the
operator's own recorded ruling to wait out a CodeRabbit quota window, a CORRECT action under the standing
review-discipline protocol; eight `ci_complete_precondition` polls averaging 417s each were not. Add a
`wait_reason` field on the recorded call so the rollup partitions deliberate waits from poll misses. ⛔ The
early-negative CI-precondition-behaviour question and the poll-budget sizing question are OUT of this
spec's territory — see Dependencies.

**D3 — Controls.** (i) A genuine product bug still classifies as `bug` — the matched negative for D1,
pinned by a real defect in the corpus. (ii) An operator-directed wait still reports as deliberate — the
matched positive for D2. (iii) Per the epic's standing rule, both new partitions are population-derived
and publish the population they were computed over, never a bare ratio.

## Claim Labels

- OBSERVED: `-007`, `-008` and `-023` are ONE signal, split by the filing plan itself —`-023` states it
  directly: *"Signal 3 for this plan is 15 distinct failing notations over 26 total failures... The three
  clusters together (8 + 4 + 10 = 22 of 26 total failures) account for nearly all of this plan's
  script-failure surface, and none of them is a product defect."* Folded as one deliverable (D1), not
  three.
- OBSERVED: `architecture search --content --pattern P` accepts `--category`, `--literal`,
  `--ignore-case` and no path-scoping flag, confirmed live at HEAD (every invocation this epic's own
  sessions have made) — corroborates `-007`'s "no path scoping" claim.
- ⚠ HYPOTHESIS: the per-row `script-failure-analysis` classification rule itself was NOT re-verified
  against source (`PLAN-PRQ-06`'s artifacts are archived; the four rejected notations are a lead) — D0(a)
  owns re-deriving the classification rule at HEAD before D1 scopes on it (verify-at-outline).
- ⚠ HYPOTHESIS: `script_cost_rollup` carries no wait/intent discriminator today — the filing message
  asserts this; confirm/refute by reading the producer before D2 scopes (verify-at-outline).
- Verify-first clause: D0's two populations are both first-party leads from one plan's retrospective, not
  yet corpus-derived — do not scope D1/D2's fix SHAPE until D0 returns the corpus figures.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — `script-failure-analysis` and `script_cost_rollup` producers (D0, D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/` — the classification and rollup contracts (D1, D2)
- OBSERVED: `test/plan-marshall/plan-retrospective/` — D3's controls

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Split from `PLAN-PRQ-09`** — same theme, different tier; see that spec's Dependencies note. Never
  pair with `PLAN-PRQ-09` while both are in flight (shared `plan-retrospective/scripts/` and
  `plan-retrospective/references/`); at `parallelization_scope: 1` this is automatic.
- ⛔ **Two halves of the inbox signal are explicitly OUT of this spec and belong to `code-intelligence-substrate`**, whose queue should receive them via `orchestrator inbox write` rather than a fold here:
  - `-007`'s ask (give `architecture search --content` a path-scoping flag) — that epic's
    `PLAN-CIS-001-content-search-seam` is **shipped**; this is residual on a surface it owns.
  - `-008`/`-023`'s executor-diagnostics ask (a copy-pasteable `did-you-mean:` argv reconstruction; a
    structured shape for the `ci` router's flag-position note) — that epic's
    `PLAN-CIS-032-executor-rejects-invalid-invocations-before-spawn` is **shipped**, making
    executor-diagnostics its declared surface.
- ⛔ **Two halves of the wait-time signal need operator adjudication, not a fold, and are NOT staged
  anywhere yet**: `ci_complete_precondition`'s early-negative return path, and the ~600s poll-budget
  sizing (95%+ of the harness ceiling). Both are `phase-6-finalize` / CI-behaviour changes, not post-run
  measurement — outside this epic's territory, and the standing PR/CI routing rule does not cleanly
  apply. Recorded as a Watch in `epic.md` rather than routed, pending an operator call.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-11-spend-and-diagnostic-aspects-count-the-wrong-population-too.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
