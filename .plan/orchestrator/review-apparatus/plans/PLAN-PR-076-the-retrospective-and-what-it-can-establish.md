# PLAN-PR-076: The review retrospective, and what its numbers can establish

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `superseded`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. `superseded` is terminal; re-staging needs an explicit operator decision.

epic: review-apparatus
workstream: WS-03

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `.claude/skills/finalize-step-review-retrospective/` — `review_retrospective.py` and its SKILL.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Make the retrospective compute over the populations it names, follow a split PR to its successors, and state what each metric can and cannot establish.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D0 | Make the `comparison` grade compute over the populations it names | `PLAN-PR-026` § D2 | `PLAN-PR-061` D2 |
| D1 | Make the metric state what it can and cannot establish | `PLAN-PR-037` § D2 | `PLAN-PR-063` D8 |
| D2 | Make the actionable classifier reviewer-aware for `issue_comment` | `PLAN-PR-037` § D4 | `PLAN-PR-063` D10 |
| D3 | Follow the split — findings and participation records reach the successor PRs | `PLAN-PR-052` § D4 | `PLAN-PR-057` D11 |
| D5 | The kind-based CodeRabbit actionable-count metric under-counts overflow findings nested as prose | (below) | lesson `2026-09-20-08-001` |

**D5 — The kind-based actionable-count metric under-reports overflow findings nested as prose (lesson
`2026-09-20-08-001`, drained 2026-09-22 via `lessons-handling-26-09-22-01`).** GitHub's inline-comment
posting cap makes CodeRabbit fold overflow findings into the meta status body as prose (`"Outside diff
range comments (N)"`) instead of posting them as separate inline comments with their own `hash_id` —
and `review_retrospective.py`'s kind-based counting reads only the inline-comment population, so it
silently drops every folded finding. Observed on `PLAN-TRUTH-143`/#1539: measured `actionable_count: 7`,
true yield `9`. *Done when:* the metric parses the meta-body overflow section and adds its count to the
population it names, and a test with a review exceeding the inline-comment cap fails on the current code
and passes after. ⚠ This is a LEAD carried from another epic's lessons drain; re-derive the overflow
population and the cap threshold at HEAD before fixing it.

**D4 — Measure the EXTERNAL review loop's self-seeded share (inbox `truthful-signals-059.md`, drained
2026-09-18).** The in-house loop is being asked to publish its self-seeded share; the same measurement
has never been taken on the bot loop, where it costs far more — a CodeRabbit round is one per hour, and
the observed run spent one of ten unattended waits (~96 min) on a quota refusal. Measured on PR #1501
(rounds at `0f4ea46`, `36188c8`, `b7a6c23`): **2 of 3 rounds re-found residue of the immediately
preceding remediation** — round 2's `manage-api.md:15-16` sibling site the previous fix did not sweep,
and round 3's vacuity inside the guard round 2 had just added — both attributed in the run's own
resolution details, unprompted. *Done when:* the retrospective publishes, per round, the share of
actionable findings attributable to the previous round's fix, over a named population, and a round whose
share cannot be computed says so rather than reporting zero. ⚠ The per-round table above is the sending
plan's own measurement and is a LEAD: re-derive it before reporting it as this epic's figure.

*(Carried from inbox message `truthful-signals-059.md`, forwarded by `truthful-signals` 2026-09-17 from
plan `truth-166-architecture-refresh-migration-churn`, PR #1501.)*


6 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: four pointer deliverables plus D4 and D5 inline, both explicitly labelled LEADS carried from another epic drain and both instructing re-derivation before use.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: DISJOINTNESS HOLDS over the DECLARED surface - review_retrospective.py, finalize-step-review-retrospective SKILL.md and its test dir appear on no other staged spec declared paths - AND the whole declared surface is UNDISTURBED: zero of the three appear in git diff --name-only 7a028157e..HEAD. The declaration nonetheless under-states reality: this spec own Dependencies says finalize-step-review-retrospective SKILL.md is also edited by PLAN-PR-071 D4 and PLAN-PR-073 D3, and that file is on neither of their Expected Surfaces - a declaration gap, not a surface collision the gate can see.


## Dependencies and Sequencing

- ⭐ **D4 consumes the same per-round model `PLAN-PR-071` D6 builds** (the reviewed tree per ROUND, not
  once per PR): without it there is no round boundary to attribute against. 071 first.
- ⛔ **Runs AFTER `PLAN-PR-071`**: D0 grades over the populations the handoff publishes.
- ⛔ **D1 runs AFTER `PLAN-PR-072` D4**: the administrative-versus-refuted split it reports needs the
  disposition vocabulary that plan adds.
- ⚠ `finalize-step-review-retrospective/SKILL.md` is also edited by `PLAN-PR-071` D4 and
  `PLAN-PR-073` D3. One file, three plans — sequence, never pair, as all three sources already state.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-076-the-retrospective-and-what-it-can-establish.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
