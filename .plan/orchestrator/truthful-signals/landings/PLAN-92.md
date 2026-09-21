# Landing Analysis: PLAN-92 — One coherent automated-review contract

epic: truthful-signals
workstream: WS-01
pr: 1041 — merged as `facb0df44`, 2026-07-28 21:11:23 +0000

> ⚠ **This landing was reconciled from PR STATE, not from the plan's inbox landing message.** That
> message (written 21:04:27Z) asserted the PR was already *"merged … HEAD `b9692bebe`"* while
> `origin/main` was still at `8b143643b` and #1041 was open — it was written **7 minutes before the
> actual merge**. The message was dispositioned `observed`, not `reconciled`, and this record was
> written only once `facb0df44` existed on `origin/main`.

## Deliverable Fidelity vs Spec

Five verified defects replaced by a single-sourced, fail-closed, recoverable contract across the
three review bots.

| Deliverable | Verdict | Evidence |
|---|---|---|
| D2 — rate-limit discriminator registry-driven and per-bot | shipped-as-specified | Each bot declares awaitable-window vs hard-quota; the stale `## Rate limit exceeded` comment fixed |
| D3 — `enabled_bots` → `required_bots` / `optional_bots` | shipped-**breaking, no shim** | Both default EMPTY on a fresh project and are asked at `marshall-steward`, so never-asked is distinguishable from answered-none. This repo migrated via a `migrate-bot-lists` sub-step to `required=coderabbit,pr-agent` / `optional=sourcery` |
| D4 — `review_timeout` recovery is event GENERATION, not waiting | shipped-as-specified | Sleep the parsed ETA, then rebase-and-push; registry trigger comment is a fallback only. Cross-plan coordination via `manage-locks` rate windows with a recursion cap |
| D5 — per-thread disposition replies | shipped-as-specified | Only threadless findings batch; undeliverable in-thread replies land in `untransmitted[]` with `status: partial`, never silently re-routed |
| D6 — evidence-based participation per publish shape | shipped-as-specified | CodeRabbit: review body / inline; PR-Agent: Guide `issue_comment` via presence + `updated_at` movement, never check state; Sourcery: review body |

The five-member failure taxonomy (absent / in-progress / refused-awaitable / refused-hard /
participated-but-empty) is authored as a **standard**, separate from per-bot registry data.

## Routing and Merge Behavior

⛔ **Merged with PARTIAL REQUIRED-BOT COVERAGE, by explicit operator decision.**
`required_bots = coderabbit,pr-agent`; **only pr-agent reviewed.**

- **CodeRabbit — a REQUIRED bot — never reviewed.** It posted only a rate-limit refusal
  (*"next review available in 51 minutes"*) and was still refusing ~30 minutes **past its own stated
  ETA**. The vendor limit is adaptive and stretches under sustained volume.
- **Sourcery hard-refused** — diff exceeded its 150 000-character limit.
- ✅ **The contract did NOT launder the gap.** `automatic-review` recorded *"pr-agent reviewed 1
  finding fixed, coderabbit rate-limited, sourcery over size limit"*; review-retrospective recorded
  *"1/3 bots reviewed"*. **This is the contract working as designed** — the shipped surface is
  simply known to have been reviewed by one of two required bots.
- **The one defect found in that surface was found by that single reviewer** (finding `1a69d5`):
  `_run_rate_window_check`'s `record is None` branch omitted `expires_at` / `seconds_remaining` /
  `expired` while the claimed branch returned all three, contradicting the unconditional field list
  in `manage-locks/SKILL.md`. Fixed in-run with a **field-set-parity** regression.

### Post-merge PR revisit — clean

Merged 21:11:23Z; latest comment 21:09:50Z. **No post-merge arrivals.** Sibling #1042 was still open
at that point and is analyzed in its own landing record.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1041; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] epic.md queue reconciled; PLAN-101's `manage-config` blocker released
- [x] the pre-merge landing-message defect recorded as the **third** confirmation (PLAN-100 owns it)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- ⭐ **PLAN-101 is UNBLOCKED by this landing** — `manage-config` is free.
- ⛔ **Operator decision still owed:** does a large-diff plan owe an explicit accepted-coverage-gap
  record? **Sourcery is now structurally unreachable for large plans** — its refusal keys on diff
  SIZE, not time, so no wait-and-retry strategy can reach it and there is **no planning-time
  signal**. Practice half filed as lesson `2026-07-28-23-002`.
- The unrecognized-refusal streak reached **five** consecutive PRs (#1024, #1032, #1034, #1040,
  #1042). D2 addresses classification; it does not make a refusing bot review.
