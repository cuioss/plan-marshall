envelope_version=1
sender_type=plan
sender_id=lb-26-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T19:09:30Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=Document architecture find canonical flags after 7 invented-flag rejects

# Document architecture find canonical flags after 7 invented-flag rejects

## Context

The lb-26-regression-fixes run hit 7 argparse rejections on plan-marshall:manage-architecture:architecture find from invented flags, plus one notation-shape error on the doubled manage-architecture segment. All 16 tasks still completed with 100 percent declared-file recall.

## Root cause

The find verb surface is discovered by guessing flag names from prose instead of the canonical invocation block, and nothing at the call site lists the accepted flags.

## Proposed action

Add the canonical flag set and one copy-paste find example to the architecture skill invocation block.

## Evidence

- aspect: script-failure-analysis — invented_flag on architecture find, occurrence_count 7
- aspect: log-analysis — 16 script errors across 1540 script entries
