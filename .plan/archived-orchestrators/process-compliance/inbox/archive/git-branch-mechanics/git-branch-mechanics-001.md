envelope_version=1
sender_type=plan
sender_id=git-branch-mechanics
epic=process-compliance
kind=finding
created=2026-09-17T20:47:54Z

# Process issues observed executing PLAN-04 (git-branch-mechanics, PR #1509)

Sender: plan `git-branch-mechanics` (archived 2026-09-17 after merge as
`f8b0fa40`). The plan itself shipped clean; what follows are
process-framework gaps this run exposed, offered as candidate input to the
process-compliance epic. Two were already filed to the finalize-machinery
epic (noted below); the rest are new.

## 1. Stale main-checkout executor runs pre-fix code post-merge (new, highest value)

After the queue merge + `switch-and-pull`, the post-merge
`prune-local-and-remote-ref` ran the OLD abort path verbatim — even though
the merged tree on disk carried the new tolerated-delete code. Cause: the
executor embeds script mappings at generation time, and main's
`.plan/execute-script.py` predated the plan's own fix. The failure message
was byte-identical to the pre-fix shape, which is also why it initially
read as "our fix doesn't work" rather than "stale runner". I regenerated
(`generate_executor generate`) and the retry took the tolerated path.
Suggestion: a staleness guard before post-merge verbs run from main
(`generate_executor drift`/`verify`, or auto-regen after `switch-and-pull`),
so a merged fix can never be executed by its own pre-image.

## 2. Session-identity hard-block on a session-less runtime (already filed as finalize-machinery finding 002)

`execution.md`'s finalize resolver aborts when no session identity exists.
On OpenCode no identity exists by construction (`session bind` →
`no_session_id`), while the sole consumer (`enrich`) already degrades to
no-op there. A telemetry-only input gates the shipping pipeline. Suggest
target-aware degrade-to-unenriched with a logged waiver instead of abort.

## 3. Orchestrator-side phase-5 move-in skipped (already filed as finalize-machinery finding 001)

I dispatched the execute envelope with `WORKTREE: .` on a
`not_yet_materialized` plan, delegating move-in entirely to the leaf's
Step 2.5 while staying on main. Result: a `references.json` stub
recreated on main alongside the worktree copy. `execution.md`'s
orchestrator cwd-pinning (`prepare_execute` + pin before dispatch) exists
precisely to prevent this; I bypassed it. Possible structural fix: make
the pre-dispatch `get-worktree-path` state (`pending` vs materialized) a
hard precondition for the execute dispatch.

## 4. Self-review verifier fixed-point has no contract exit

Two consecutive rounds on a deterministic surface with unchanged HEAD
returned identical accepted-clean verdicts, and the verifier twice
answered `may_close: no` on incurable grounds (files the surfacer never
produces candidates for; the published structural limit). The contract's
only exits are another identical round or burning `max_iterations`.
I escalated to the operator, who closed it by waiver. Suggest: a
same-surface detector (identical candidate digest + unchanged HEAD seal
the prior acceptance), or a documented operator-override path so the
waiver does not have to masquerade as a verifier `yes`.

## 5. Operator override overwrites the fact it overrides

Related to (4): closing the review required recording `may_close=yes`
although both verifiers answered `no`. The `previous_*` fields preserve
the history, but any consumer reading the fact reads the override as the
verdict. Suggest a distinct override marker (e.g. `may_close=waived` with
a reason reference) rather than overwriting the measured value.

## 6. Post-pack fix tasks carry `envelope_id: null`

Triage-created fix tasks (TASK-4 through TASK-8) arrive with no envelope,
so the envelope-filtered executor cannot see them. I hand-stamped them
`envelope_id: 1` via `manage-tasks update`. Suggest: re-run the
bin-packer over added tasks at loop-back entry, or define the
null-envelope execution rule explicitly instead of leaving an operator
edit as the only path.

## 7. `plan-retrospective` leaf skipped its terminal record

The retrospective dispatch returned `status: success` with a report path
but recorded no `mark-step-done`, tripping `assert-step-recorded`. I
backfilled the record from its return TOON. Suggest: dispatcher-side
completion guard for this roster entry (as exists for other dispatched
steps), or a leaf-side fix — a silent success with no record is the exact
gap `record-before-return` exists to close.

## 8. Observation only: simplify removed a just-added regression test

The re-fired simplify pass deleted one of the plan's own new regression
tests as duplicative (twin kept, suite green). Correct outcome here, but
the sweep's changeset scope includes the plan's newest coverage with no
"do not cut green tests added this run" guard beyond reviewer judgment.
No action proposed; recorded so a future bad cut has a prior to cite.

## What worked (for balance)

The freshness gate (`pre-commit-verify-freshness`) caught two genuinely
stale trees and directed the exact remedy; the review→triage→loop-back
machinery converted 8 bot comments into 5 landed fixes plus 1 sound
decline; the participation barrier caught a stale bot review and the
re-review trigger verified against the new HEAD.
