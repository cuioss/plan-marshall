envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:46Z

component=plan-marshall:phase-3-outline
category=bug

# Candidate lesson: phase-3 domain-narrow emptied references.domains; clearing call needs --values=

- Suggested component: plan-marshall:phase-3-outline (domain-narrow) and plan-marshall:manage-references (set-list)
- Suggested category: bug
- Signal source: outline-phase decision log
- Evidence: decision log c5ba22, "domain-narrow: 4 domain(s) -> 0 retained; dropped documentation, general-dev, java, java-cui". Decision log b8259e, "domains restored to [documentation] after domain-narrow emptied them". The `set-list --values ""` exit-2 behaviour was observed by the orchestrator and is not in the plan log.

## What happened

1. Every deliverable declared `domain: documentation`, but phase-3 domain-narrow dropped all four detected domains, including documentation, and left `references.domains` as `[]`. The operator had to restore `[documentation]` by hand.
2. The documented way to clear a list, `manage-references set-list --values ""`, exits 2 because the executor strips the empty argument. `--values=` works.

## Why it matters

An empty domain list removes domain-skill resolution for every later phase. The documented clearing form does not work, so the recovery path fails as well.

## Suggested fix

- domain-narrow should keep every domain that a deliverable declares. It should never narrow to an empty set while deliverables still carry a domain.
- Either keep empty argument values in the executor, or change the documented clearing form to `--values=`.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-002.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
