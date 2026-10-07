envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:57Z

# A retried finalize step cannot record its success without `--force`

## Observed

`phase-6-finalize/SKILL.md` Step 3 item 1 (resumable re-entry): "IF outcome == `failed`: RETRY (proceed to
dispatch as fresh run)". `finalize-step-sync-baseline` recorded `--outcome failed` (rebase refused on a dirty
worktree), the cause was cleared, and the retry rebased cleanly. Its documented terminal call —
`mark-step-done --step finalize-step-sync-baseline --outcome done ...` — was then refused:

```text
status: error
error: conflict
existing_outcome: failed
requested_outcome: done
message: Step 'finalize-step-sync-baseline' in phase '6-finalize' already marked as 'failed'; use --force to overwrite with 'done'
```

None of the step docs' terminal `mark-step-done` calls carry `--force`, and the dispatcher's retry contract does
not mention it. So the documented `failed -> retry` path cannot complete by following the documents: every
retried step's success record is refused, and the step stays `failed` — which the next re-entry retries again,
forever. The orchestrator added `--force`, an undocumented override, to record an honest success.

## Recurrence in the same run

`default:push` hit it again: the freshness gate refused (`build_scope_narrow`), push recorded `failed` as its doc
requires, a whole-tree `verify` cleared the refusal, the push succeeded — and `mark-step-done --outcome done` was
refused with the identical `conflict`. Recorded with `--force` again. A third instance followed: `plan-marshall:automatic-review` (failed record from its first attempt → retries → the successful fifth dispatch's `mark-step-done --outcome done` refused with `conflict`, re-issued with `--force`). That makes three of the steps so far in this
finalize whose documented failed → retry → done path could not be completed as written.

## Suggested fix

Have `mark-step-done` treat `failed -> done|skipped|loop_back` as a legal transition (a retry is exactly that),
keeping the refusal only for overwriting a terminal `done`; or have the dispatcher clear the `failed` record
before re-dispatching a retry. Add a test that walks failed -> retry -> done through the documented calls.
