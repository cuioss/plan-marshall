envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T21:31:38Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=Invented flag drift on architecture search subcommand

# Invented flag drift on architecture search subcommand

## Context

During antigravity-execution-fidelity, four calls to
`plan-marshall:manage-architecture:architecture search` were rejected with exit
code 2 for an invented flag (first at 2026-10-13T18:43:18Z). The callers
guessed a flag the subcommand never declared.

## Root cause

Workflow prose names a plausible flag that does not match the script's argparse
surface, and callers quote the prose instead of `--help` or the canonical
invocation block.

## Proposed action

Align the calling workflow prose with the canonical invocation block for the
`search` subcommand, or add the missing flag if the prose describes intended
behavior.

## Evidence

- aspect: script-failure-analysis — invented_flag on architecture search, 4 occurrences
- confidence: medium; source plan: antigravity-execution-fidelity
