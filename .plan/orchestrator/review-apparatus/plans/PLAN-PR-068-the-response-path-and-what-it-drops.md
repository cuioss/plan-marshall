# PLAN-PR-068: The response path, and every answer it drops

> ⛔⛔ **PARKED — SUPERSEDED BY PM-MCP (2026-09-26, operator decision).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. Un-park only by explicit operator decision.

epic: review-apparatus
workstream: WS-03

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `workflow-integration-github` write path — `cmd_post_responses`, the reply/resolve mutations, and the three providers that share them.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Make a transmitted answer, an undelivered one and an unresolved thread three distinguishable outcomes, and make a failed marker write impossible to swallow. Every deliverable here edits the WRITE path.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | A delivered reply is stamped, counted honestly, and never re-sent | `PLAN-PR-029` § D2 | `PLAN-PR-059` D2 |
| D2 | Make "unanswered" a first-class outcome of the transmit verb | `PLAN-PR-035` § D1 | `PLAN-PR-060` D1 |
| D3 | Close the mechanism D0 implicates | `PLAN-PR-035` § D3 | `PLAN-PR-060` D3 |
| D4 | Pin the measurement | `PLAN-PR-035` § D4 | `PLAN-PR-060` D4 |


**D0 — GATE, mutates nothing.** The merged attribution-and-derivation gate, carrying BOTH populations.
From `PLAN-PR-035` D0: attribute each of the thirteen unanswered findings to a mechanism or record it
unattributable, published as a table with its population (13 of 43, four named PRs); **HALT if fewer
than nine attribute.** From `PLAN-PR-031` D0: derive the report corpus and confirm every defect still
reproduces. ⛔ `PLAN-PR-035` § Dependencies: **D0 must ATTRIBUTE BY AUTHOR before reporting any ratio**
— some of the 43 may be our own comments, which would make numerator and denominator both wrong.

*(Carried verbatim from `PLAN-PR-060` D0 at the 2026-09-18 component re-cut.)*

5 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: the four deliverables are pointers and D0 names its two source gates. No git diff bears on it.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping; RE-SCOPED 2026-09-22):
  this plan's declared surface is disjoint from every other live plan's in this epic **except
  `PLAN-PR-067`, which shares three declared files** (`github_pr.py`, `workflow-integration-github/SKILL.md`,
  `test_github_pr.py`) — the read-path/write-path split is a split of FUNCTIONS inside one file, not of
  files; sequenced ("Runs AFTER `PLAN-PR-067`" below), never paired. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus` — non-determinate at HEAD (see the claim's
  verdict).
  - verdict: contradicted | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: yes | evidence: DISJOINTNESS IS FALSE - the mirror of PLAN-PR-067 claim 1. Both specs declare github_pr.py, workflow-integration-github/SKILL.md and test_github_pr.py. RE-SCOPE: state the three shared files and the ordering (Runs AFTER PLAN-PR-067) instead of asserting disjointness. The read-path/write-path split is a split of FUNCTIONS inside one file, not of files.
- OBSERVED (corpus pass 2026-09-15): 97 of 493 plan-marshall finding units carry no posted answer, 11
  of them unresolved (6 on merged PRs); all 7 Sourcery review bodies and all 3 substantive pr-agent
  guides went unanswered. D0 attributes these, not only the original thirteen.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Corpus-pass measurement over a findings population (97 of 493 plan-marshall finding units unanswered, 11 unresolved, 6 on merged PRs; 7 Sourcery bodies and 3 pr-agent guides unanswered). The substrate is a findings store, not the git tree - no diff in this window can confirm or refute it, and it was not re-derived. D0 must re-derive, not inherit.

## Dependencies and Sequencing

- ⛔ **Runs AFTER `PLAN-PR-067`** (its pre-filter) and **AFTER `PLAN-PR-072`** (the marker lifecycle
  D1 stamps through). Both are stated dependencies of the carried bodies, not new ones.
- ⭐ D1 discharges what `PLAN-PR-060` D2 asked for separately — the four `mark_finding_responded`
  call sites are edited ONCE, here. The duplicate was deleted at the re-cut, not merged.
- ⚠ D3 is conditional by construction: if D0 attributes the majority to the resolve-failure path, it
  is DROPPED and D1 carries the fix.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-068-the-response-path-and-what-it-drops.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
