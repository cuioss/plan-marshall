envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=landing
created=2026-07-28T21:04:27Z

## What landed

**PLAN-92 — One Coherent Automated-Review Contract** — PR #1041, merged from
`feature/one-coherent-automated-review-contract`, HEAD `b9692bebe`.

Single-sourced, fail-closed, recoverable automated-review contract across the three review bots
(CodeRabbit, Sourcery, PR-Agent), replacing five verified defects:

- **D2** — the rate-limit discriminator is now registry-driven and per-bot (each bot declares
  awaitable-window vs hard-quota) instead of hardcoded to CodeRabbit alone; the stale
  `## Rate limit exceeded` comment is fixed.
- **D3** — `enabled_bots` is replaced (breaking, no shim) by `required_bots` / `optional_bots`.
  Both default to EMPTY on a fresh project and are asked at `marshall-steward`, so
  never-asked is distinguishable from answered-none. A bot in neither list warns but is still
  ingested. This repo migrated explicitly to `required=coderabbit,pr-agent` /
  `optional=sourcery` via a `migrate-bot-lists` sub-step under `reconcile-config`.
  The contract (required/optional semantics, `ask` posture, and the five-member failure taxonomy:
  absent / in-progress / refused-awaitable / refused-hard / participated-but-empty) is authored
  as a standard in `automatic-review/standards/`, separate from per-bot registry data.
- **D4** — `review_timeout` recovery is event GENERATION, not waiting: sleep the parsed ETA,
  then rebase-and-push (the new-commits event); the registry trigger comment is a fallback only
  when main is unchanged and only after the window elapsed. Cross-plan coordination through
  `manage-locks` rate windows, main-anchored, with a recursion cap.
- **D5** — every thread-bearing comment gets its disposition replied in its own thread; only
  threadless findings render in the batched PR comment; undeliverable in-thread replies land in
  `untransmitted[]` with `status: partial` and are never silently re-routed to the batch.
- **D6** — bot participation is evidence-based per each bot's actual publish shape (CodeRabbit:
  posted review body / inline comments; PR-Agent: the Guide `issue_comment` tracked via presence
  plus `updated_at` movement, never inline-comment count or check state; Sourcery: posted review
  body). Quorum over `required_bots` proves participation only, never review quality.

## Residue the epic should track

1. **This PR merged with partial required-bot coverage, by explicit operator decision.**
   `required_bots = coderabbit,pr-agent`. Only pr-agent actually reviewed. CodeRabbit — a
   REQUIRED bot — never reviewed: it posted only a rate-limit refusal ("next review available in
   51 minutes") and was still refusing roughly 30 minutes PAST its own stated ETA. Sourcery
   hard-refused because the diff exceeded its 150 000-character limit. The finalize step recorded
   this truthfully (`automatic-review` display_detail: "pr-agent reviewed 1 finding fixed,
   coderabbit rate-limited, sourcery over size limit"; review-retrospective: "1/3 bots reviewed").
   The contract behaved as designed — it did NOT launder the gap — but the shipped surface has
   therefore only been reviewed by one of the two required bots.

2. **The plan's own D4 recovery design has a live counter-example from its own PR.** D4 sleeps the
   parsed ETA and then generates a new-commits event. On #1041 the parsed ETA was not honoured by
   the vendor: CodeRabbit's adaptive rate limit stretched under sustained volume and it was still
   refusing well past the stated window. See the accompanying candidate-lesson.

3. **One slipped-then-caught defect in this plan's own delivered surface**, raised and fixed
   in-run by pr-agent (finding `1a69d5`): `_run_rate_window_check`'s `record is None` branch
   omitted `expires_at` / `seconds_remaining` / `expired` while the claimed branch returned all
   three, contradicting the unconditional field list documented in `manage-locks/SKILL.md`.
   Fixed in `b9692bebe` with a field-set-parity regression. This is another instance of the
   recurring doc-contract-divergence archetype.

4. **Sourcery is now structurally unreachable for large plans.** Its refusal is keyed on diff
   SIZE, not time, so no awaitable-window recovery strategy can ever retry it. Every plan whose
   PR exceeds ~150 000 diff characters silently loses that reviewer. It is classified `optional`
   here, so the gate did not block — but the epic should decide whether large-diff plans owe a
   split or an explicit accepted-coverage-gap record.

## Signals at finalize

- `signal_qgate_pending_count`: 0
- `signal_automated_review_count`: 1 (one pr-comment finding raised AND fixed within the run)
- `signal_script_failure_clusters_count`: 0
