envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:10Z

component=plan-marshall:automatic-review
category=improvement
title=trigger-bot needs the newest finding SHA; the only source is a 188 KB findings read
source_lesson=2026-11-18-13-008
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# trigger-bot needs the newest finding SHA; the only source is a 188 KB findings read

# Candidate lesson: trigger-bot needs the newest finding's SHA, and the only source is a 188 KB findings read

- Source signal: plan-retrospective, plan git-core-import (inbox git-core-import-010).

## What happened

Four automatic-review dispatches needed the newest bot finding's commit SHA for `trigger-bot --reviewed-commit-sha`. The only source was the stored pr-comment findings listing, about 188 KB with 71 findings. Three dispatches passed an empty value and one a SHA taken from a partial sample. With `re_review_on_loopback: false` this did not change the result, but the input was not computed as documented and would matter with re-review on loop-back.

## Root cause

No query returns only the newest finding's SHA, so the leaf has to scan the whole listing.

## Candidate rule

Add a narrow `manage-findings` query (newest finding by type, returning its commit SHA), or have `trigger-bot` resolve the SHA from the store when the flag is omitted.
