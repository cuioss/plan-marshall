envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:35Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: a bound on one side of a symmetric pair needs a stated round-trip consequence
source_lesson=2026-11-23-12-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# phase-3-outline: a bound on one side of a symmetric pair needs a stated round-trip consequence

# Candidate lesson: a bound placed on one side of a symmetric pair broke the round-trip contract

- Source signal: plan plan-23-forms-hardening (inbox plan-23-forms-hardening-001), automated review of PR #59 (CodeRabbit inline finding 908e3b on `YamlDocumentCodec.java` 106, fixed by TASK-19, commit `8ea86a1`).

## What happened

At outline the owner answered "number bounds in `YamlReader` only, in-memory numbers stated unbounded", and the plan implemented exactly that. CodeRabbit then showed the consequence: `encode` accepted a `BigDecimal("1e1001")` or `BigInteger.TEN.pow(1000)`, wrote it, and `decode` refused the bytes as MALFORMED, which breaks the documented promise that `decode(encode(v))` succeeds for every value `encode` accepts. The first triage disposition kept the reader-only decision and only documented the exception; the owner then changed TASK-19 to make `encode` refuse numbers beyond the reader bounds.

## Candidate rule

When a plan places an input bound on one side of a symmetric pair (reader/writer, decode/encode, parse/format), the outline checks the pair's round-trip contract: either the other side enforces the same bound or the contract is changed explicitly. A one-sided bound is a decision that needs a stated round-trip consequence, not just a per-side answer. Owning component: `plan-marshall:phase-3-outline` (the outline's checks for codec and reader plans).
