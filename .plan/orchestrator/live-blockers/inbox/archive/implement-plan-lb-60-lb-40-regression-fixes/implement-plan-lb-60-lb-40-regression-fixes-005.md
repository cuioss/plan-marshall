envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:37:44Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=Invented flag drift in the architecture search call

# Invented flag drift in the architecture search call

## Context

During plan `implement-plan-lb-60-lb-40-regression-fixes` the
`plan-marshall:manage-architecture:architecture search` verb was invoked three
times with a flag the script does not declare. Each call exited 2 at the
argparse boundary and was never executed, so the caller silently lost the
architecture lookup it was making.

## Root cause

The caller paraphrased the flag from surrounding workflow prose instead of
quoting the verb's declared argparse surface. This is the known
`argparse_rejection` recurrence class (verb-scoped / invented-flag drift) that
the `ARGUMENT_NAMING_*` plugin-doctor cluster guards against at edit time.

## Proposed action

Quote the `architecture search` flag set verbatim from the script's own
`--help` / the `manage-architecture` Canonical invocations block, and add the
exact call shape used by the retrospective's own search sites to that block so
future callers copy rather than retype.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-architecture:architecture` subcommand `search`, `exit_code: 2`, subtype `invented_flag`, first at `2026-10-15T18:35:33Z`, occurrence_count 3
