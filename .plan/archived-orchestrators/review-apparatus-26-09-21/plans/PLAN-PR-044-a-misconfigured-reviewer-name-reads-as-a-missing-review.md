# PLAN-PR-044: A misconfigured reviewer name reads as a missing review

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-02 from an operator paste reporting a using project's experience. The
> STRUCTURAL claim below was corroborated first-party against this repository's source
> before staging; the reporting project's PROXIMATE cause was not, and D0 exists to settle
> it. ⛔ Do not conflate the two — see Claim Labels.

## Objective

`required_bots` names **bot kinds** (`pr-agent`, `coderabbit`, `sourcery`), each backed by a
registry doc. Participation is proved by a `bot_kind` **derived from the reviewer's login**
(`cuioss-review-bot` → `pr-agent`). The two sides therefore meet only if the configured token
is a member of the live registry's kind set — and **nothing checks that it is.**

A token that matches no registry kind can never appear in the derived `participated_bots` map,
so it resolves to `absent`, and `absent` is the state reserved for *"this bot did not review."*
The result is a **blocking** merge barrier reporting a true statement about the observed set and
a false steer about the cause. The reporting operator spent ~2h chasing a review that already
existed, then worked around it plan-locally — so the misconfiguration survives for every future
plan in that repository.

This is the epic's shipped `absent`-names-two-states archetype (PLAN-PR-007) recurring one layer
up, at the **configuration** boundary rather than the observation boundary.

## Deliverables

### D0 — Establish the reporting project's proximate cause before fixing anything

⛔ **The structural gap and the reported incident are two claims, and only the first is settled.**
This repository's registry DOES map `cuioss-review-bot` → `pr-agent`, so the operator's stated
pair should NOT mismatch here. At least three mechanisms produce the reported symptom and they
have different fixes:

1. the configured token was the **login** (`cuioss-review-bot`), not the kind;
2. the token was the kind but the project resolved an **older registry** (stale plugin cache) that
   did not yet carry the login→kind entry;
3. the reviewer posted under a **different login** in that org, absent from the map.

*Done when:* the reporting project's `required_bots` value and its **resolved** registry are read
first-party, and exactly one mechanism is named as observed — with the other two recorded as
rejected and why. A fix authored before this is a fix aimed at a guess.

### D1 — Validate the configured bot lists against the live registry, and give a mismatch its own state

Check every token of `required_bots ∪ optional_bots` against `bot_registry.bot_kinds()`. A token
matching no kind resolves to a NEW state — unproven and **blocking exactly as `absent` is**, so
the barrier keeps failing closed — whose meaning is *"this name matches no reviewer we know"* and
whose remedy is *fix the name*, not *chase the reviewer*.

⭐ **The shape already exists: `not_triggered` refines `absent` today.** Follow it; do not add a
parallel mechanism beside the eleven-state vocabulary.

*Done when:* a `required_bots` token that is not a registry kind renders the new state, and the
payload names the live kind set the token was checked against. **Matched negative control
required:** a correctly-named required bot that genuinely did not review still renders `absent`.
Without that control a refinement is indistinguishable from a blanket reclassification.

### D2 — Say it at configuration time, not only at the barrier

`marshall-steward` already builds its bot questions from `bot_registry.bot_kinds()`, so the
**wizard path cannot produce this mismatch** — a hand-edited, copied, or inherited `marshal.json`
can. That asymmetry is the defect's entry point, and closing it is a config-read-time check.

⛔ **Not a blanket reject.** The unknown token is REPORTED with the live kind set; the fail-closed
barrier still blocks. A config read that silently drops the token would replace a confusing block
with a silent pass, which is strictly worse.

*Done when:* reading a `marshal.json` whose bot lists name an unknown kind reports the offending
token(s) and the live kind set; matched negative control: a valid list reports clean over a stated
population.

### D3 — The blocking message names the discriminating question

The 2h was a **diagnosis** cost, not a detection cost — the barrier detected correctly and steered
wrongly. Its escalation text for the new state names the configured token, the live kind set, and
the login→kind entry for any reviewer observed on the PR whose kind is unclassified.

*Done when:* the WARNING/escalation for the new state carries all three, pinned by a test whose
pre-fix form fails; and the existing `unclassified_bots` warning is cross-referenced rather than
duplicated.

Four deliverables, comfortably inside the split guard.

## Claim Labels

- OBSERVED: nothing in the tree validates a configured `required_bots` / `optional_bots` token
  against `bot_registry.bot_kinds()`. Derivation named so it is re-runnable: two enumerations over
  `marketplace/bundles`, `.claude` and `test` — `bot_kinds()` call sites (28 hits) and all other
  `bot_kinds` textual references (20 hits) — and no hit is a validation of the config lists.
  Confirm/refute at `review_completeness.py` § `check_completeness` (its `required_bots` argument
  is consumed unvalidated) and at `manage-config`'s script set (no bot-kind check exists).
  ⛔ This is an asserted ABSENCE — re-run both enumerations at outline before building on it.
- OBSERVED: the completeness vocabulary has eleven states and none of them means *"the configured
  name matches no reviewer"*. Confirm/refute at the `STATE_*` constants in
  `automatic-review/scripts/review_completeness.py`.
- OBSERVED: participation is keyed by a `bot_kind` DERIVED from the author login, so a token
  outside the derived-kind codomain can never enter `participated_bots` and must fall to `absent`.
  Confirm/refute at `github_pr.py`'s `bot_kind_for_author` call site and `parse_participation`.
- OBSERVED: `marshall-steward` builds its bot questions from the live registry, so the wizard path
  cannot emit an unknown token. Confirm/refute at `marshall-steward/SKILL.md` § the bot questions.
- HYPOTHESIS: the reporting project's incident was caused by this gap rather than by a stale
  resolved registry or an unmapped login. Confirm/refute at the reporting project's `marshal.json`
  and its resolved `automatic-review/standards/*.md` registry — D0 settles it (verify-at-outline).
  ⛔ n=1, second-hand, and this repository's own registry contradicts the naive reading.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `test/plan-marshall/automatic-review/`

## Dependencies and Sequencing

- ⛔ **Overlaps `review_completeness.py`** — never concurrent with PLAN-PR-042, PLAN-PR-026,
  PLAN-PR-031, PLAN-PR-043.
- ⛔ **Overlaps `automatic-review/SKILL.md`** — never concurrent with PLAN-PR-029, PLAN-PR-030,
  PLAN-PR-043.
- ⛔ **Overlaps `branch-cleanup.md`** — never concurrent with PLAN-PR-026, PLAN-PR-028,
  PLAN-PR-033.
- ⚠ Re-derive the live-plan collision set before launch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-044-a-misconfigured-reviewer-name-reads-as-a-missing-review.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
