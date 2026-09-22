# PLAN-PR-051: The participation gate rejects its own callers, five times, inside its own plan's finalize

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-058` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1, D2, D3 and D1a are carried there as D6–D9, and D0 folds into that plan's
> merged D0 gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of
> every deliverable body, and `PLAN-PR-058` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-09-05 from inbox `-002` and `-009` (both `candidate-lesson`), filed by
> `required-reviewer-returns-empty-list` during its own finalize and observed live on PR #1410.
> ⭐ **`-009` SUPERSEDES `-002` on the causal question** and the two are staged together for that
> reason: `-002` reported the exit-1 cause as needing reproduction, `-009` establishes it. The spec
> carries `-009`'s settled cause, not `-002`'s open one.

## Objective

Make `review_completeness check` — the gate that decides whether required reviewers participated —
invokable by its own callers without a rejection, and make its refusals cost one call instead of two.

## Problem

**`plan-marshall:automatic-review:review_completeness check` failed FIVE times during the finalize of
the very plan whose subject is that component**: 3 argparse rejections and 2 exit-1 internal errors.

⭐⭐ **The exit-1 cause is ESTABLISHED, not pending.** Both occurrences are **deliberate
`malformed_bot_flag` refusals**, and the two malformed tokens are known verbatim:

| Passed | Required | Defect |
|---|---|---|
| `--participated-bots cuioss-review-bot` | a `bot_kind:evidence_kind` **pair** | a bare token where a pair is required |
| `--refused-causes sourcery=quota` | `sourcery:quota` | `=` used where `:` is the separator |

Both fired at 15:19Z, **16 seconds after the merge lock went `lock-owned`** — i.e. on the hot path,
at the moment the gate matters most.

⛔ **Two separators, one script, no signal which applies where.** `--participated-bots` and
`--refused-causes` both take `{key}{sep}{value}` pairs and both use `:`, but nothing at the call site
distinguishes them from the `=`-shaped flags elsewhere in the same surface, and a bare token is
accepted at neither. The refusal is *correct*; the surface is what invites the mistake.

⛔ **A refusal that costs two calls is a refusal that did not fully specify itself.** This is the same
consumption-side shape this epic already forwarded to `truthful-signals` — an argparse rejection is a
*complete specification*, not a hint — but here the producer half is ours: a `malformed_bot_flag`
refusal that names the offending token and the expected separator **inline** costs one call, not two.

## Deliverables

**D0 — GATE, mutates nothing.** Re-ground both malformed-token claims against HEAD
(`4972615257305e5ccb79f1a1c19a72517a2c15c3`, after #1410). Confirm the `:`-pair grammar for
`--participated-bots` and `--refused-causes` is still current and that `malformed_bot_flag` is still
the refusal code. **HALT and report if #1410 already changed either grammar** — this plan must not
harden a surface its own subject plan has just moved.

**D1 — A `malformed_bot_flag` refusal names the token, the expected shape, and a corrected example.**
Not the accept-set alone: the offending token verbatim, the separator that was expected, and one
literal corrected form (`cuioss-review-bot:comment`, `sourcery:quota`). *Done when:* a refusal's
message is sufficient to compose the corrected call **without a second read of the help text**, and a
test pins that all three parts are present.

**D2 — Make the pair-shaped flags self-describing at the call site.** The two pair-shaped flags share
one grammar and it is invisible at the point of use. *Done when:* the help string for each pair-shaped
flag states its separator and shows a literal example, and the check that no pair-shaped flag in this
script advertises a bare-token form is **population-derived** — it publishes how many pair-shaped
flags it evaluated, so a zero is a measured zero.

**D3 — Prove the gate against its own documented invocations.** Every `review_completeness check`
invocation form that appears in a marketplace doc or workflow is executed as a test. *Done when:* the
test enumerates the invocation forms it found and publishes that population, so a green run states how
many forms it proved rather than asserting completeness.

**D1a — A documented empty-string default that the executor makes UNREACHABLE.** ⭐ **Folded from
`one-format-…-004` on 2026-09-08**, observed at the **pre-merge review barrier** — the worst place for
this gate to reject its caller.

```text
review_completeness.py check: error: argument --measured-diff-size: expected one argument
```

The call passed `--measured-diff-size ""` — **exactly as `branch-cleanup.md` § "Predicate 2"
prescribes**: *"The two lists default to the empty list and the scalar to the empty string when the
producer emitted none … the empty fallback, never a hard failure."*

⛔ **The doc prescribes a call the executor cannot accept.** This is the same class as D1/D2 — a
refusal invited by the surface — but sharper, because here the *documentation is the caller*: anyone
following the contract produces the rejection.

*Done when:* the empty fallback the contract promises is reachable through the executor, **or** the
contract is corrected to the form that works — and whichever arm is taken, a test executes the
invocation `branch-cleanup.md` prescribes, so doc and script cannot drift apart again. ⛔ Fixing only
one side leaves the other stating a falsehood.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — D1a: § "Predicate 2", the empty-string default the executor rejects
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — D1a: the test that executes the invocation the contract prescribes

## Claim Labels

- OBSERVED: `review_completeness check` failed 5 times during PLAN-PR-042's finalize — 3 argparse
  rejections, 2 exit-1 — first-party to that run.
- OBSERVED: Both exit-1 occurrences are `malformed_bot_flag` refusals of
  `--participated-bots cuioss-review-bot` and `--refused-causes sourcery=quota`, fired at 15:19Z,
  16 s after the merge lock went `lock-owned`.
- ⛔ **RETRACTED, do not re-derive**: candidate-lesson `-002`'s claim that the exit-1 cause required
  reproduction. `-009` established it from the same run's logs. **Reproducing it is not a deliverable.**
- HYPOTHESIS: the `malformed_bot_flag` refusal message names neither the offending token nor the
  expected separator — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
  § the `malformed_bot_flag` raise site (verify-at-outline).
- HYPOTHESIS: no test executes `review_completeness check` against the invocation forms its own docs
  advertise — confirm/refute at
  `test/plan-marshall/automatic-review/test_review_completeness.py` § its test function list
  (verify-at-outline). ⛔ This is an **absence** claim and is verified as such; an unverified absence
  would have D3 build a second copy of an existing test.

## Dependencies and Sequencing

- Depends on: none. **PLAN-PR-042 has SHIPPED (#1410)**, so its hold on `review_completeness.py` is
  released.
- ⚠ **Overlaps heavily on `review_completeness.py`** with `PLAN-PR-026`, `-031`, `-043`, `-045`,
  `-046`, `-047`, `-048`. **Sequence, never pair** with any of them. This plan is the smallest of the
  set and touches only the invocation surface, so it is cheap to land first.
- Adjacent to: the argparse-population work forwarded to `truthful-signals` as
  `review-apparatus-032.md`. That side owns the **consumption** half (a rejection is a complete
  specification); this plan owns the **producer** half. ⛔ Neither subsumes the other.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-051-the-participation-gate-rejects-its-own-callers.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
