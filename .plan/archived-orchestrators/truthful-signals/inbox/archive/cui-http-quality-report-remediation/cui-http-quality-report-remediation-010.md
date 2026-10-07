envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:06Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# Loop-back fix rewrote one doc section and left a contradicting line elsewhere in the same file

## Source

- Plan: plan-12-javadoc-samples-and-api-prose (PR #260)
- Signal: Q-Gate finding 4d1a3f (phase 6-finalize, defect class `same_document_contradiction`), fixed by commit c2e67d1
- File: cui-http-core/src/main/java/de/cuioss/http/client/adapter/package-info.java

## What happened

A loop-back fix (in response to the CodeRabbit review comment e29d95) rewrote the "Request Body
Validation" section to say: validate individual user-supplied values, not the serialized
document. The "Security Checklist" in the same file still said "All request bodies validated with
URLParameterValidationPipeline". The self-review re-fire caught the contradiction. It did not slip
into the merge, but it cost an extra loop-back round.

## Why it matters

A fix scoped to the line a reviewer pointed at leaves the file's other statements of the same
rule (checklists, summaries, "see also" lines) unchanged. Those statements then contradict the fix.
This is most likely in long Javadoc package-info files, which restate one rule in several places.

## Suggested correction

When a loop-back fix changes a normative statement, search the same file (and its sibling
summaries) for every other statement of that rule before committing. For example, search for the
pipeline or API name the fix stopped recommending, and update each hit in the same commit.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-12 (cuioss/cui-http #260), inbox message `plan-12-javadoc-samples-and-api-prose-003.md`. Routed by the cui-http orchestrator on 2026-10-05.
