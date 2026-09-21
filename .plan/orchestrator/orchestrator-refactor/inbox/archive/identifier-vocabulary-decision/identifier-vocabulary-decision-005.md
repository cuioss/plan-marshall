envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:24:57Z

component=plan-marshall:plan-retrospective
category=bug
title=Give affected_files_exact_match a consuming rule or stop deferring it

# Give affected_files_exact_match a consuming rule or stop deferring it

## Context

`check-artifact-consistency` emitted `affected_files_exact_match` with `status: warn`, `references_only: [uv.lock]`, `manifest_present: true` and `forwarded_to_manifest: true`, and its single finding reads "Set mismatch — deferred to manifest aspect (see check-manifest-consistency)".

`check-manifest-consistency` then ran and emitted five checks: `manifest_version_recognized`, `docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`. None of them is a declared-vs-referenced set-mismatch rule. It reported `findings: 0` and `summary.failed: 0`.

So the deferral has no consumer. The only aspect that noticed the footprint discrepancy handed it to an aspect that has no rule for it, and the retrospective as a whole reported a clean result on a genuine over-claim — the same over-claim independently confirmed against the merge commit.

## Root cause

Aspect 1 forwards a finding to aspect 12 by name, but aspect 12's rule set was never extended to receive it. The handoff is asserted in prose and in a `forwarded_to_manifest` boolean, and nothing checks that the receiving side acts on it.

## Proposed action

Either add a rule to `check-manifest-consistency` that consumes the forwarded set mismatch and emits a finding on it, or stop downgrading `affected_files_exact_match` to `info` in `check-artifact-consistency` and let it report the mismatch itself. A forwarding flag that no consumer reads is a silent finding sink, and this run demonstrates it swallowing a true positive.

## Evidence

- aspect: artifact_consistency — `affected_files_exact_match.status: warn`, `forwarded_to_manifest: true`, finding severity downgraded to `info`
- aspect: manifest_decisions — 5 checks emitted, none matching the forwarded concern; `findings: 0`
- aspect: request_result_alignment — the same discrepancy confirmed against merge commit `4804b6976`
