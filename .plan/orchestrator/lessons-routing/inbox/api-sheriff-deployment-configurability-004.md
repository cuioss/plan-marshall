envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=lessons-routing
kind=finding
created=2026-09-23T15:34:25Z

# Forward from `deployment-configurability` (API-Sheriff) — PLAN-29 (PR #348): a recurrence of an already-forwarded finding, plus two new tooling gaps

Follow-up to `api-sheriff-deployment-configurability-001/002/003` (2026-09-23, R19 confirms these were
forwarded to `post-run-quality`, `truthful-signals`, and `process-compliance` respectively). PLAN-29's
own finalize run (2026-09-23) hit one recurrence of an already-forwarded issue plus two new ones.

## Item 1 — RECURRENCE of the `process-compliance` forward: `review_completeness --participated-bots` given a bare bot_kind

Same defect as Item 5 of the finding already forwarded to `process-compliance`
(`api-sheriff-deployment-configurability-003.md`'s "review-completeness guard rejected the caller's
bot list" item), recurring in a different plan. At the branch-cleanup pre-merge review barrier
(2026-09-23T14:26:03Z): `review_completeness` refused `--participated-bots coderabbit` with
`malformed_bot_flag` — `coderabbit` is not a `bot_kind:evidence_kind` pair. Recovered on re-run; the
barrier then reported clean ("zero pending pr-comment findings, required-bot participation
complete"). The guard's refusal is correct (fail-loud on under-determined input); the caller
composing the flag is what needs fixing — build every token as `{bot_kind}:{evidence_kind}` from the
participation evidence the review fetch already recorded, never a bare bot name. Worth a concrete
worked example at the branch-cleanup barrier doc's call site, since this is now a confirmed recurrence
rather than a one-off.

## Item 2 — `manage-findings qgate list` invoked without required `--phase`

At the 5-execute → 6-finalize boundary (2026-09-23T11:05:18Z), the orchestrator-side Q-Gate pending
check fired `qgate list` without `--phase`, which the verb requires (`exit_code=2`,
`argparse_rejection`). There is no cross-phase form — a caller needing a cross-phase count loops over
the five phases. The recurrence signature suggests the orchestrator workflow's phase-boundary Q-Gate
check needs a verbatim canonical invocation with `--phase` at its call site, the same fix class as the
5 flag-shape rejections already forwarded.

## Item 3 — `ci_wait`'s adaptive timeout budget doesn't fit this repo's known-slow CI jobs

Within one PLAN-29 finalize run, 5 `ci_timeout`-classified triage findings (ci-verify's wait deadline
exceeded while a check was still `IN_PROGRESS`) were all resolved `accepted` with the identical
rationale — ci-verify taxonomy row (h): retry, not a failure; a re-poll at the same HEAD later observed
a real conclusion. This recurred well above `preference_min_recurrence` (5 vs 2). API-Sheriff's CI
shape (Maven `sonar-build` ~850s, `integration-tests` ~1600s) routinely exceeds `ci_wait`'s default
wait window, so the `ci_timeout` → accept-and-retry cycle fired on every finalize pass in this plan (3
separate loop-back iterations) — pure wasted iteration budget on a disposition that is never anything
but "retry" in practice here. Consider either seeding `ci_wait`'s adaptive budget with a longer
ceiling for this project's known-slow jobs, or having `ci_timeout` re-poll once automatically before
filing a Q-Gate finding, since the disposition is deterministic.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-29 (`plan-29-final-gap-closure`, PR #348, merged
`070eda5`). Original candidate-lesson messages: `plan-29-final-gap-closure-004.md` (item 2),
`plan-29-final-gap-closure-005.md` (item 1), `plan-29-final-gap-closure-006.md` (item 3) — all
discarded from that epic's own lessons corpus as out-of-scope plan-marshall tooling, routed here
instead, per the same convention `api-sheriff-deployment-configurability-001/002/003` used.
