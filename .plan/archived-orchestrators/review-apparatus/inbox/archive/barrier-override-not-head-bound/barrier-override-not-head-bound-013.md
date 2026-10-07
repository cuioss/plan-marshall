envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:44Z

# Aspect table display names do not match the collect-fragments registry keys

component: plan-marshall:plan-retrospective
category: improvement
confidence: high

## Context

SKILL.md Step 3's aspect table names aspects in prose form — "Invariant outcomes", "Script failure
analysis", "Direct gh/glab usage (Surfaces A+B: plan logs + plan diff)" — and the per-aspect capture
pattern instructs `collect-fragments add --aspect {name}`. But `collect-fragments` validates `--aspect`
against a closed canonical registry whose keys are `invariant-summary`, `script-failure-analysis`,
`direct-gh-glab-usage`.

Three of the five deterministic registrations in this run were rejected on first attempt for exactly this
mismatch.

## Root cause

The table's "Aspect" column serves two audiences — it is prose documentation and it is also the only
in-document source for the registration argument — and it satisfies only the first. The canonical keys
appear nowhere in SKILL.md.

## Proposed action

Add a `registry key` column to the Step 3 aspect table carrying the canonical key per row, so the
document that instructs the registration also supplies the exact argument. Alternatively, have
`collect-fragments add` accept the display names as aliases.

**Note the guard worked.** `collect-fragments add` rejected every wrong key with the full valid set and
an explicit explanation that `compile-report` would otherwise silently drop the section. This is a
fail-loud design doing its job — the proposal is to remove the need for it, not to weaken it.

## Evidence

- Three `Unregistered aspect key` rejections during this retrospective run (`invariants`, `script-failures`, `direct-gh-glab`)
- aspect: llm_to_script_opportunities — candidate 2, repetition_count 4
- SKILL.md Step 3 table vs `collect-fragments` `valid_aspects[17]`
