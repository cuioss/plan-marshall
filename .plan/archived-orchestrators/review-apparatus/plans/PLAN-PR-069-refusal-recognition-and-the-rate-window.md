# PLAN-PR-069: Refusal recognition, and the rate window that governs the retry

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `superseded`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. `superseded` is terminal; re-staging needs an explicit operator decision.

epic: review-apparatus
workstream: WS-01

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `automatic-review` registry and standards — `bot_registry.py`, `coderabbit.md`, `sourcery.md`, `cuioss-review-bot.md`, and the rate-window surface.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Recognise every refusal a bot actually publishes, extract its ETA under the same guard as the detection, and turn the rate window into a retry policy that names the event it waited for.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | Select the trigger-B bot from the gating set, not from comment recency | `PLAN-PR-043` § D1 | `PLAN-PR-056` D1 |
| D2 | Close the refusal-recognition gap the three arms each missed differently | `PLAN-PR-043` § D2 | `PLAN-PR-056` D2 |
| D3 | The rate window is a retry policy, not a flat timeout | `PLAN-PR-043` § D6 | `PLAN-PR-056` D7 |
| D4 | The rate window's own instruments are deaf — ⭐ **+ the measured cost of the window itself, folded 2026-09-13** | `PLAN-PR-043` § D7 | `PLAN-PR-056` D8 |
| D5 | Rate-limit notices are TRANSPORT FAILURES, classified at ingestion | `PLAN-PR-048` § D3 | `PLAN-PR-057` D5 |
| D6 | Classify the refusal by CONDITION, and make the named remedy executable | `PLAN-PR-052` § D1 | `PLAN-PR-057` D8 |
| D7 | Make `refusal_structural` reachable, or delete it | `PLAN-PR-052` § D2 | `PLAN-PR-057` D9 |
| D8 | Give a stored refusal its MODE — the two modes have different remedies | `PLAN-PR-047` § D2 | `PLAN-PR-061` D9 |
| D9 | Name the composition — neither path alone predicts the failure | `PLAN-PR-045` § D3 | `PLAN-PR-056` D11 |

⭐ **Recurrence (lesson `2026-09-19-21-002`, drained 2026-09-22 via `lessons-handling-26-09-22-01`):**
Trigger B's stale-bot selector still cannot reach a required bot that has never published a finding —
the same gap D1 (select the trigger-B bot from the gating set, not comment recency) already owns. No
new deliverable; folds as a second occurrence on D1.

**D1 amendment 2026-09-22 (re-grounding pass, cleanup A1) — the residue is narrower, not the whole
deliverable.** `#1510` (sibling epic `instrumentation-substrate`, its PLAN-03) shipped
`select_stale_bot_for_trigger(stale_bots, newest_finding_kind_bot)` in `review_completeness.py`,
undeclared here: it selects trigger B from the STALE SET rather than from comment recency, exposed as
the CLI verb `trigger-bot --plan-id --stale-bots --newest-kind`. ⇒ D1 is RE-SCOPED from *build the
selector* to *close the remaining gap*: a required bot that has never published ANY finding is not in
`stale_bots` and falls through to `newest_finding_kind_bot` or empty — that narrower case, plus whether
`automatic-review`'s workflow actually invokes the new verb, is unestablished and is what D1 now owns.
⚠ Coverage bound: the content-search tool does not walk `.claude/**` or `.github/**`.

**D0 — GATE, mutates nothing.** The merged re-grounding gate. Re-read every symbol
`PLAN-PR-043` § Claim Labels and `PLAN-PR-045` D0/D0a name, at HEAD, and publish the affected
population `PLAN-PR-045` D0 requires **before** any disposition is chosen. ⛔ Anchor on SYMBOLS, never
on line numbers — this spec's ancestors carried three line references that had all moved while the
mechanism held. **HALT and report** if a named symbol no longer resolves.

*(Carried verbatim from `PLAN-PR-056` D0 at the 2026-09-18 component re-cut.)*

10 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — ⭐ **this plan is its single owner**; `PLAN-PR-070` and `PLAN-PR-071` route contract edits here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_patterns.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_markers.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_structural_refusal_cap.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_structural_refusal_diff.py`
- OBSERVED: `test/plan-marshall/manage-locks/`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: nine pointer deliverables plus a merged D0 gate, with the 2026-09-22 recurrence explicitly folded onto D1 rather than restated. That recurrence is now the only live half of D1 - see the contradiction on PLAN-PR-043 claim 0.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping; RE-SCOPED 2026-09-22):
  this plan's declared surface is disjoint from every other live plan's in this epic **except
  `PLAN-PR-066`, which shares `automatic-review/standards/cuioss-review-bot.md`** (069 as a
  refusal-standards target, 066 as a D11 rename target) — sequence, never pair. The separate
  single-owner assertions below DO hold: `bot-participation-contract.md` is declared by no other
  STAGED spec, and `automatic-review/SKILL.md` is declared only by `PLAN-PR-070`. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus` — non-determinate at HEAD (see the claim's
  verdict).
  - verdict: contradicted | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: yes | evidence: DISJOINTNESS IS FALSE: PLAN-PR-069 and PLAN-PR-066 both declare automatic-review/standards/cuioss-review-bot.md (069 as a refusal-standards target, 066 as a D11 rename target). The resume_anchor already names this pair; the spec own claim does not. RE-SCOPE: name the 066 collision on cuioss-review-bot.md, as 066 own Dependencies section does. The spec separate single-owner assertions DO hold and were derived: bot-participation-contract.md is declared by no other STAGED spec, and automatic-review/SKILL.md is declared only by PLAN-PR-070.


## Dependencies and Sequencing

- ⛔ **D2 is the single owner of refusal RECOGNITION.** `PLAN-PR-070` acts on a refusal but never
  re-implements its recognition; the Sourcery lead formerly at `PLAN-PR-057` D6 is folded into D2
  rather than staged separately (it was labelled a LEAD, not a finding, and its body is unreachable).
- ⛔ **D3 produces the interval/ceiling surface D5 consumes** — producer before consumer, inside this
  plan, which is why they are no longer in two specs.
- ⚠ D4 carries a `manage-locks` limb (`merge_lock.py` `_run_rate_window_check` scoping) and D3 a
  `manage-config` limb. Both are declared; neither is a second component this plan owns — if either
  grows past its stated bullet, split it out rather than widening this plan.
- ⚠ D8 needs its discriminator derived at RECOGNITION time, and recognition lives in
  `_github_pr.py` — a file `PLAN-PR-067` owns. Sequence behind 067, or confine D8 to the registry side.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-069-refusal-recognition-and-the-rate-window.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
