envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:41Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-identity-and-scope-defences` (PR #682), original message `refresh-identity-and-scope-defences-001.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a signal that could not be observed must never be recorded as an observed pass

**Category**: anti-pattern
**Suggested component**: `plan-marshall:automatic-review`, `plan-marshall:phase-5-execute` (`scope_creep_check`), `plan-marshall:phase-6-finalize`
**Source plan**: `refresh-identity-and-scope-defences` (PR #682, squash `31715f6b`)

## The rule

Three independent mechanisms in this one plan reported a *pass* for a check that had
never actually observed the thing it was supposed to check. Each was caught by a human
or by a reviewer bot, never by the mechanism itself. The unifying rule is the one
`manage-lessons`, `inbox list`, and `list-stalled` already encode for their own zeros
and which the review/guard surfaces do not: **every green must state which kind of green
it is — "looked and found nothing" or "could not look".**

## Witness 1 — a stale bot review credited as current participation (fired three times)

`automatic-review`'s currency test `_reviewed_at_merge_candidate` runs only for bots whose
registry entry declares `participation_requires_update: true`. CodeRabbit's entry declares it
`false`, so the update-currency arm is skipped entirely and *any* comment on the thread — a
re-surfaced comment set, or an inline auto-annotation whose timestamp merely post-dates the
head commit — credits the bot as `participated`.

Concrete instances from `logs/decision.log`:

- `2026-09-01T09:15:04Z` — HEAD `e7e5611a`. Ledger credited `coderabbit` as participated
  (`evidence_kind=inline`) off an "Addressed in commit e7e5611" auto-annotation. CodeRabbit's
  actual latest full review states its own range as `cf8acb80..d7e56393`; the delta review was
  rate-limited.
- `2026-09-01T13:35:12Z` — HEAD `c76016d3`. `participated_bots[]=coderabbit` was again a
  false-green; the review body states range `7ce5255e..4e73be2a`, two commits behind.
- `2026-08-31T21:42:05Z` — HEAD `82e6597d`. Review body names `379afb77..99c36992`.

**The only reliable detection was reading the review body's own stated commit range.** Every
time, the structured ledger and the bot's own prose disagreed and the prose was right.

Upstream half already filed as `truthful-signals/refresh-identity-and-scope-defences-002.md`.
The consuming-project half is: with `required_bots=coderabbit,pr-agent` and
`pre_merge_comment_barrier=fail_into_loopback` configured, this project's merge gate is
gated on a signal that can be forged by an unrelated comment. Until the registry flag is
fixed upstream, an operator directive requiring a named bot's review must be verified by
reading the review body range, not by trusting `participated_bots[]`.

## Witness 2 — a guard whose failure reads as a pass

`scope_creep_check` emits finding type `scope_creep_warning`. `manage-findings qgate` rejects
that type as invalid, so the check exits 1 with `finding_persist_failed` on **every**
invocation. Recorded at `logs/decision.log` `2026-09-01T06:07:59Z`:

> scope creep therefore went UNMEASURED on tasks 11-13, not measured-clean

The same gap had already appeared earlier in the run under a different cause
(`2026-08-31T13:05:45Z`: `could_not_look`/`no_baseline_sha` on tasks 1-5 because
`references.plan_creation_sha` was unset). So across an 18-task plan, scope creep was never
once actually measured — and nothing in the pipeline said so.

Producer/consumer type mismatch is the mechanical defect; the durable lesson is that a guard
which can only ever fail is indistinguishable from a guard that always passes unless its
failure is surfaced as a distinct non-green state.

## Witness 3 — the orchestrator bulk re-stamped head-dependent steps it had not re-run

Self-caught, `logs/work.log` `2026-09-01T09:58:28Z` (`[CRITICAL]`): five head-dependent
finalize steps were re-stamped at HEAD `7ce5255e` in one loop. Only `pre-push-quality-gate`
and `push` had actually been earned. `finalize-step-simplify`,
`finalize-step-security-audit`, and `pre-submission-self-review` were stamped without
running, and the `e7e5611a..7ce5255e` delta contained production code
(`TokenLifecycleManager` quarantine extension plus two test files).

The orchestrator's own words: *"Stamping a security audit as having validated code it never
examined is precisely the false-green this session has repeatedly refused from tooling."*
All three were re-fired for real before merge.

## Suggested remedy

1. Upstream: make the currency test unconditional, or make `participation_requires_update:
   false` fail closed rather than credit.
2. Upstream: fix `scope_creep_check`'s finding type, and make a guard's non-zero exit
   surface as a `could_not_measure` state that a phase transition refuses to read as clean.
3. Locally: when a HEAD advances past a head-dependent finalize step, re-stamping is only
   legitimate when the delta is provably inert (zero files under `src/main`) — and that
   inertness must be shown, as this run did correctly at `2026-09-01T08:32:15Z` for a 6-line
   AsciiDoc commit, not assumed for a batch.
