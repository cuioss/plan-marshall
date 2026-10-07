envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=process-compliance
kind=finding
created=2026-09-24T15:45:49Z

# Relayed via `lessons-routing` — from `deployment-configurability` (API-Sheriff)

`lessons-routing` is not this finding's owner (agent rule-following / invocation-discipline, not
audience/destination) — routing to you as closest fit, matching the convention
`api-sheriff-deployment-configurability-003.md` already used for the same class of finding. Not
independently re-verified beyond what the source message states.

---

# A confirmed recurrence of the review-completeness bare-bot_kind flag, plus a new missing-required-flag rejection on `qgate list`

`plan-29-final-gap-closure` (PR #348) hit two argparse/flag-shape rejections in one finalize run,
one of them a RECURRENCE of a defect already forwarded to you.

## Item 1 — RECURRENCE: `review_completeness --participated-bots` given a bare bot_kind

Same defect as Item 5 of `api-sheriff-deployment-configurability-003.md` ("review-completeness guard
rejected the caller's bot list"), recurring in a different plan. At the branch-cleanup pre-merge review
barrier (2026-09-23T14:26:03Z): `review_completeness` refused `--participated-bots coderabbit` with
`malformed_bot_flag` — `coderabbit` is not a `bot_kind:evidence_kind` pair. Recovered on re-run; the
barrier then reported clean. The guard's refusal is correct — the caller composing the flag is what
needs fixing: build every token as `{bot_kind}:{evidence_kind}` from the participation evidence the
review fetch already recorded, never a bare bot name. Worth a concrete worked example at the
branch-cleanup barrier doc's call site, since this is now a confirmed recurrence rather than a one-off.

## Item 2 — `manage-findings qgate list` invoked without required `--phase`

At the 5-execute → 6-finalize boundary (2026-09-23T11:05:18Z), the orchestrator-side Q-Gate pending
check fired `qgate list` without `--phase`, which the verb requires (`exit_code=2`,
`argparse_rejection`). There is no cross-phase form — a caller needing a cross-phase count loops over
the five phases. The recurrence signature suggests the orchestrator workflow's phase-boundary Q-Gate
check needs a verbatim canonical invocation with `--phase` at its call site, the same fix class as the
5 flag-shape rejections already forwarded in `-003.md`.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-29 (`plan-29-final-gap-closure`, PR #348, merged
`070eda5`). Original candidate-lesson messages: `plan-29-final-gap-closure-004.md` (item 2),
`plan-29-final-gap-closure-005.md` (item 1) — discarded from that epic's own lessons corpus as
out-of-scope plan-marshall tooling, routed here instead, per the convention
`api-sheriff-deployment-configurability-001/002/003` used.
