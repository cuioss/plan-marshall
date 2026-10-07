envelope_version=1
sender_type=plan
sender_id=invocation-surfaces
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T07:44:17Z

# Candidate lesson: Name the offending flag and sibling verb in every argparse rejection

component: plan-marshall:tools-script-executor
category: improvement
confidence: high
source_plan: invocation-surfaces
source_aspects: script_failure_analysis, log_analysis

## Context

The invocation-surfaces plan retired the argparse-rejection class: nine rejections in one run across four signatures, several recurring from independent callers. Its own execution kept hitting the class it was fixing (ci pr prepare-body missing --plan-id, manage-status read --phase, manage-findings query, architecture search invented flag), which is what made the fix shippable and verifiable in one run.

## Root cause

Argparse error paths named the failure but not the fix: the message said a flag was required or a verb unknown without naming the sibling verb or spelling that would have succeeded, so every independent caller had to discover the correction separately.

## Proposed action

Keep the executor-template remedy this plan shipped (rejection messages name the offending flag and the correct sibling verb/flag spelling at exit 2) and apply the same naming discipline to every new argparse site added afterwards: verify the rejection message against the implementing argparse source before scoping, for presence and absence claims alike.

## Evidence

- aspect: script_failure_analysis — 13 failures / 10 unique across the plan run, dominated by argparse rejections
- aspect: log_analysis — work.log script_failure lines name the exact sibling verbs that now appear in the messages
