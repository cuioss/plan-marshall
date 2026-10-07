# WS-05: Standards and Design

epic: token-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Fold the bot-caught consumer-domain patterns into the standard docs (cui-http, cui-testing, cui-logging, asciidoc) and settle the survivor-sweep invariant design-first (ADR on the git-native fingerprint substrate — the invariant PR #723 failed to ship four times). Closes when P5 and SS have shipped.

## Scope

- In scope: pm-dev-java-cui / pm-documents standards documents; the survivor-sweep ADR and any code it authorizes.
- Out of scope: the already-shipped whole-tree drift gate (ADR-006 territory, #911).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-p5-consumer-domain-standards | launched | Pure docs surface — the source ledger's best parallel candidate |
| PLAN-10-ss-survivor-sweep | launched | Design-first: ADR before code; re-derive on the fingerprint substrate |

## Sequencing and Surface Notes

- Both plans are independent of each other and of every other launched plan (docs vs design doc).
