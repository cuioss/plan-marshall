envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:33:20Z

# Align the skill description with the verb name to stop inducing extract-deliverables

component: plan-marshall:manage-solution-outline
category: anti-pattern
confidence: high

## Context

`manage-solution-outline` registers the verb `list-deliverables`. Its skill description advertises "standards, examples, validation, and deliverable extraction".

The invented verb `extract-deliverables` was issued twice during this plan's execute phase (argparse exit 2, first at 2026-09-02T18:02:37Z, `occurrence_count: 2`) and was independently reproduced a third time by this retrospective run, by a different model instance in a different phase reading different documents.

## Root cause

A content sweep over the architecture inventory (`architecture search --content --literal --pattern extract-deliverables`, 5338 files scanned, 0 unreadable, `truncated: false`, no elision) returns **zero** hits. No workflow doc, skill body or standard prescribes the verb, so this is not documentation drift that a doc fix would close.

The verb is generated, not copied. The skill's own description names the capability "deliverable **extraction**", which makes `extract-deliverables` the natural verb-paraphrase — precisely the recurrence signature 1 (verb-paraphrase) the agent-behavior rules already warn about. The description is the attractor.

Three independent occurrences across two phases and two model instances make this structural rather than incidental.

## Proposed action

Change the skill description to name the registered verb: "deliverable listing" rather than "deliverable extraction". A description that uses the verb's own word removes the paraphrase pressure at its source.

Optionally, register `extract-deliverables` as an argparse alias of `list-deliverables` — the same accepted-secondary-spelling carve-out already granted to `manage-lessons read`, `manage-tasks get` and `manage-status get`. The rejection message already names the correct verb, so the cost of the current behaviour is one wasted call per occurrence, but it recurs reliably.

## Evidence

- aspect: script_failure_analysis — `anti-pattern, argparse_other, plan-marshall:manage-solution-outline:manage-solution-outline, extract-deliverables, exit 2, occurrence_count: 2`
- This retrospective run reproduced the same rejection a third time before consulting the accepted-verb list
- `architecture search --content` over 5338 files with clean coverage: the string appears in no document, so the verb is model-generated from the description
