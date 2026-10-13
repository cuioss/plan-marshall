envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:28:25Z

component=plan-marshall:manage-references
category=improvement
bundle=plan-marshall

# Prune paths dropped from the outline in sync-affected-files

## Context

In plan lb-28-java-consumer-repos the first outline listed two extension-api standards docs; the outline revision dropped them because the request excludes extension-api edits. `sync-affected-files` only ever adds paths, so `references.affected_files` kept both stale entries (35 stored vs 33 declared) and `read_intent_files` kept a dropped `test_maven_run.py`. Three separate agents (outline revise, 3-outline Q-Gate, 4-plan Q-Gate) each noticed and worked around the stale entries, and the retrospective's outline-vs-shipped aspect reports the two docs as include_unrealised.

## Root cause

`cmd_sync_affected_files` in `manage-references/scripts/_references_crud.py` computes a set union with the outline's declared files, so a path removed from the outline can never leave the stored list; no workflow step removes it either.

## Proposed action

Make `sync-affected-files` replace the outline-derived portion of `affected_files` (or report and remove paths no longer declared by any deliverable), keeping a separate record of paths added for other reasons. Alternatively give phase-3-outline's revise path an explicit prune step. Either way, downstream scope readers then see the declared surface, not its history.

## Evidence

- aspect: outline_vs_shipped — include_unrealised 2 of 19 (build-api-reference.md, module-discovery.md)
- aspect: chat_history_analysis — "sync-affected-files only ever adds paths ... the stored total is 35, against 33 declared"
- aspect: artifact_consistency — declared-vs-stored mismatch forwarded to the manifest aspect
