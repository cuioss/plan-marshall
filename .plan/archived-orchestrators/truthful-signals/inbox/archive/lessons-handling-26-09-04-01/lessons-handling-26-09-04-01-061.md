envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:52Z

component=pm-documents:ref-asciidoc
category=bug

# The ref-asciidoc header rule and the manage-adr template disagree, so every template-generated ADR fails validation

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15), inbox message
`lessons-handling-epic-residual-cleanup-008.md`. That plan's deliverable 3 was to decide whether
the validator or the ADR files were wrong **before** editing 13 files. It decided the validator
is wrong and made zero edits under `doc/adr/`.

## Observation (confirmed against source, not just the plan log)

- `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_validate.py:17-20` requires
  `:toclevels: 3`, `:toc-title: Table of Contents` and `:source-highlighter: highlight.js`, and
  reports `missing_header` (severity `error`, line 92) when they are absent.
- `marketplace/bundles/plan-marshall/skills/manage-adr/templates/adr-template.adoc:3-4` emits
  `:toclevels: 2` and `:sectnums:`, with no `:toc-title:` and no `:source-highlighter:`.
- Token-Sheriff `doc/adr/`: `asciidoc validate --path doc/adr` gives 14 files, 12 non-compliant
  (0003–0014), all `missing_header`. ADR-0001 carries the validator's header set. ADR-0012 carries
  the template's set exactly. 0003 is an older outlier missing all five (plan decision.log `5b9dc6`, `0b48ba`).

Read at plan-marshall HEAD `7a028157e`.

## Why it matters

Two marketplace components give opposite verdicts on the same document. Every consumer repo that
uses `manage-adr` gets an ADR set that validates as broken by construction. The obvious fix of
editing the ADRs to satisfy the validator is exactly the edit that would bring the files out of
line with their own template.

## Candidate direction

Pick one source of truth. Either the `ref-asciidoc` header rule recognizes the `manage-adr`
header set for ADR documents, or the `manage-adr` template emits the validator's required
attributes. After the change, a freshly generated ADR must validate clean. That round-trip is the
regression test this pair lacks.
