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

**Two retrospective diagnostics read a population that IS available and leave part of it unpublished or
insufficiently split.** `script_cost_rollup` collapses a correct action and a stall into one "waste"
figure with no discriminator (D2, unnarrowed). `script-failure-analysis` already classifies executor-guard
firings apart from genuine product bugs at HEAD (D1, NARROWED 2026-09-21 — the classification exists, it
is simply not published as a summed roll-up and its `bug` bucket needs one further split). Both remain
`PLAN-PRQ-09`'s shape (a population that is READ, not missed) applied to the spend/diagnostic tier rather
than the recall/coverage tier — D2 fully, D1 in its surviving, narrower form.

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

**D1 — `script-failure-analysis` PUBLISHES its existing partition as a roll-up, and splits
`script_internal_error` so a notation failure is distinguishable from a genuine crash.** ⛔⛔ **NARROWED
2026-09-21 (cleanup, `checked_at: e8a71650`): the premise as originally staged is REFUTED.**
`script-failure-analysis.py:47-53` already declares a two-axis vocabulary — `invented_subcommand` /
`missing_required_flag` / `invented_flag` / `argparse_other` all classify as **`anti-pattern`**, and only
`script_internal_error` classifies as **`bug`**. Re-partitioning `PLAN-PRQ-06`'s own archived
`fragment-script-failure-analysis.toon` by `(type, subtype)` gives **20 of 26** rows already filed as
`anti-pattern`, only **6** as `bug` — the `product_defect` vs. `call_construction_drift` partition this
deliverable originally proposed to ADD **already exists** as the `type` axis. What remains: (a) publish
the existing `type`/`subtype` partition as a summed roll-up so it is visible rather than latent, and (b)
split `script_internal_error`'s 6 rows further — an `invalid_notation` subtype distinct from a genuine
crash, since the "4 notation underscore/hyphen internal errors" the inbox message named are a SUBSET of
those 6, not evidence of a missing top-level partition. ⛔ Two adjacent asks are OUT of this spec's
territory and must not be folded here — see Dependencies.

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
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: All three messages present in the epic inbox archive. Every quoted fragment verified verbatim in -023.md: '15 distinct failing notations', '26 total failures', '8+4+10=22', 'none of them is a product defect'. Header confirms kind=candidate-lesson, component=plan-marshall:tools-script-executor.
- OBSERVED: `architecture search --content --pattern P` accepts `--category`, `--literal`,
  `--ignore-case` and no path-scoping flag, confirmed live at HEAD (every invocation this epic's own
  sessions have made) — corroborates `-007`'s "no path scoping" claim.
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: architecture.py search --help declares exactly: --content, --pattern, --category, --literal, --ignore-case. No path/dir/scope flag of any kind. Derived complete enumeration from the argparse declaration itself, not a sample.
- ⚠ HYPOTHESIS: the per-row `script-failure-analysis` classification rule itself was NOT re-verified
  against source (`PLAN-PRQ-06`'s artifacts are archived; the four rejected notations are a lead) — D0(a)
  owns re-deriving the classification rule at HEAD before D1 scopes on it (verify-at-outline).
  - verdict: contradicted | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: yes | evidence: Re-derivation refutes D1's premise. script-failure-analysis.py:47-53 already declares a two-axis vocabulary: invented_subcommand/missing_required_flag/invented_flag/argparse_other all classify as anti-pattern; only script_internal_error classifies as bug. Re-partitioning PRQ-06's own fragment-script-failure-analysis.toon by (type,subtype): 20 of 26 already file as anti-pattern, only 6 as bug. D1's product_defect vs call_construction_drift partition ALREADY EXISTS as the type axis. D1 shrinks to: publish the existing partition as a summed roll-up, and split script_internal_error so notation-resolution failures are distinguishable from genuine crashes.
- ⚠ HYPOTHESIS: `script_cost_rollup` carries no wait/intent discriminator today — the filing message
  asserts this; confirm/refute by reading the producer before D2 scopes (verify-at-outline).
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: log-analysis.md:54-73 contract: script_cost_rollup keys are population/ceiling_seconds/calls_at_or_over_ceiling/total_calls/total_duration_ms/distinct_scripts/ranked_count/sub_precision_calls/ranked[] -- no wait/intent/reason/deliberateness field. Content sweep for wait_reason: count 0, files_scanned 3089. Producer analyze-logs.py confirmed inside PRQ-11's declared surface.
- Verify-first clause: D0's two populations are both first-party leads from one plan's retrospective, not
  yet corpus-derived — do not scope D1/D2's fix SHAPE until D0 returns the corpus figures.
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Both figures reproduce exactly on the single source plan and nowhere else -- confirmed single-plan, not corpus. The clause is now doubly warranted: the D1 re-derivation (claim 2) shows a corpus pass would have caught D1's premise error before it was written into a deliverable.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — `script-failure-analysis` and `script_cost_rollup` producers (D0, D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/` — the classification and rollup contracts (D1, D2)
- OBSERVED: `test/plan-marshall/plan-retrospective/` — D3's controls

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Split from `PLAN-PRQ-09`** — same theme, different tier; see that spec's Dependencies note. Never
  pair with `PLAN-PRQ-09` while both are in flight (shared `plan-retrospective/scripts/` and
  `plan-retrospective/references/`); at `parallelization_scope: 1` this is automatic.
- Also shares `plan-retrospective/scripts/` with `PLAN-PRQ-01` and `PLAN-PRQ-02` (added 2026-09-21,
  `corpus cross-check`) — automatic at `parallelization_scope: 1`, recorded so a raised knob does not
  pair either.
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
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-11-spend-and-diagnostic-aspects-count-the-wrong-population-too.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
