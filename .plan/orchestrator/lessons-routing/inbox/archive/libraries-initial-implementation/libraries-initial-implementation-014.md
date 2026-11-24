envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:08Z

component=plan-marshall:execution-context
category=anti-pattern
title=Dispatched leaves without Grep fall back to Bash grep and python file rewrites
source_lesson=2026-11-18-13-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Dispatched leaves without Grep fall back to Bash grep and python file rewrites

# Candidate lesson: dispatched leaves without Grep fall back to Bash grep and python edits

- Source signal: plan-retrospective, plan git-core-import (inbox git-core-import-008).

## What happened

Two dispatched leaves ran without `Grep`/`Glob`. The finalize unified-triage leaf did its read-only lookups with Bash `ls` and `grep` and did not consult the architecture inventory. The execute envelope-4 leaf renamed an identifier in three places of one Java file with a Bash python one-liner instead of the Edit tool. Both said so in their hand-back; a later triage leaf did it right (`architecture search --content`, then Read).

## Root cause

The envelope states the fallback, but nothing stops a leaf at the moment it reaches for Bash; the rule is only read as prose. No permission prompt fired, so nothing else surfaced the bypass.

## Candidate rule

Make the fallback mechanical: have the Bash pre-tool hook reject `grep`/`ls`/`find` and inline `python -c` file rewrites inside dispatched leaves with a message naming `architecture search --content` / `architecture find` and Edit. Let the retrospective flag any hand-back that admits such a fallback.
