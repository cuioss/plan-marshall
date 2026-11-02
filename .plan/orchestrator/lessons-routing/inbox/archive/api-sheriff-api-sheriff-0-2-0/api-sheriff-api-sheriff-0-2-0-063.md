envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-25T22:12:13Z

# Candidate lesson: a re-filed blocking Q-Gate finding folds into its resolved record and `--reopen` does not surface it (plan-marshall:manage-findings qgate dedup, loop-back close)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-002.

What happened: a round re-filed a blocking finding identical to one already resolved with `qgate resolve-by-rule --resolution taken_into_account`. It had the same content discriminator, so it folded into the resolved record (`status: kept`) and showed no pending row. `qgate add --reopen` did not reopen it (the orchestrator observed this directly; the plan logs do not record it). `loop-back close --accept` reads only pending findings, so a round's whole blocking set was invisible to it. Evidence in the plan records: the resolved rows carry `reobserved_count` 3-4 while staying `accepted` or `taken_into_account`.

Suggested direction:
- A re-filed blocking finding whose prior record is resolved should reopen as pending by default, or at least be named in the `qgate add` result (for example `reobserved_on_resolved`).
- `--reopen` should reopen a resolved record, or fail loudly.
- `loop-back close --accept` should count blocking re-observations made in the current round, not only pending rows.

Related: -062 (the weakened_test rows that produced the re-observations).
