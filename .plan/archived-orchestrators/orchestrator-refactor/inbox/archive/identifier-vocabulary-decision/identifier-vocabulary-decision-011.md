envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:32:10Z

component=plan-marshall:manage-locks
category=bug
bundle=plan-marshall

# merge_lock budget-reclaim declares --hold-start as a float while every caller holds an ISO-8601 instant

Source signal: script-failure cluster 2 of 3 on plan `identifier-vocabulary-decision`
(epic `orchestrator-refactor`). Work-log marker, `2026-09-20T07:39:16Z`:

```text
[ERROR] (plan-marshall:execute-script:2) script_failure
notation=plan-marshall:manage-locks:merge_lock exit_code=2
failure_kind=argparse_rejection
detail=merge_lock.py budget-reclaim: error: argument --hold-start:
       invalid float value: '2026-09-20T07:09:31Z'
```

argparse's own rejection is the proof: `budget-reclaim --hold-start` is declared
`type=float` (epoch seconds), and the value the caller had to hand was the ISO-8601
UTC instant that every other timestamp surface in this system speaks — `created`,
`consumed_at`, `amended`, `last_seen`, the work-log `timestamp` column, and the lock's
own `set_at` payload (`'set_at': '2026-09-20T07:09:31Z'`, visible in the adjacent
title-token log lines and almost certainly where this value was read from).

## Why it is a bug and not a caller error

The value passed was not wrong, it was in the **house format**. A single surface that
demands epoch-float while its own sibling state is serialized as ISO-8601 makes the
correct call require a conversion the caller has no reason to expect — so the failure
mode is not "caller was careless", it is "one surface disagrees with the system's
timestamp vocabulary".

Note the resonance with what this plan actually landed: ADR-023 closed the vocabulary
for entity-identifying *argument names*. This is the same disease one axis over — an
argument **value type** that departs from the system-wide convention. Whether the epic
wants to own that axis is a scope decision for the orchestrator, not for this plan.

## Where it bit

Inside the overnight merge-queue landing path, between the lock being taken at
`2026-09-19T21:00:56Z` and released at `2026-09-20T07:09:24Z`, then re-taken at
`07:45:56Z`. `budget-reclaim` is the path that reclaims a lock whose hold budget has
expired. ⛔ A reclaim path that cannot be invoked is a path that leaves a stale merge
lock held — and a stale merge lock blocks every other plan's landing, not just this
one. The run did land (PR #1543 merged at `08:00:32Z`), so the failure was recovered
from, but the blast radius of this particular script failing is cross-plan.

## Unverified — for the orchestrator to check, not to assume

I did **not** verify what the documentation advertises. `--hold-start` appears in
`manage-locks/SKILL.md` (2 hits) and in
`phase-6-finalize/standards/branch-cleanup.md` (1 hit) — the caller-side doc. If
either of those shows a timestamp-shaped example value, this is a
**doc-contract-divergence** (the doc tells you to pass what the parser refuses) and is
strictly worse than a plain type choice. If both show an epoch float, it is a
convention-inconsistency only. `Grep` was unavailable in this envelope and the
content-search verb returns no line context, so the distinction is genuinely open
rather than checked-and-clean.
