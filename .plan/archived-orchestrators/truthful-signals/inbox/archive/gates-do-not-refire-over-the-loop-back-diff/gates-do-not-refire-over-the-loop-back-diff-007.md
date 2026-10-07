envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:30Z

component=plan-marshall:phase-6-finalize
category=bug

# create-pr.md Step 3.6 reads `enabled_bots`, a manifest key that no longer exists — its empty-set branch is unreachable

## Observation

`create-pr.md` **Step 3.6** reads an **`enabled_bots`** key from the execution manifest. The manifest no longer emits that key — it now emits **`required_bots`** and **`optional_bots`**.

Because the key is always absent, the read yields an empty/undefined value on every run, and the branch that handles the empty set is **unreachable in the sense that matters**: it fires unconditionally rather than conditionally, so the guard it implements has no discriminating power. The step cannot distinguish "no bots configured" from "bots configured but the key was renamed".

## Why this belongs to `truthful-signals`

Two layered untruths:

1. **Producer/consumer drift with no failure signal.** The rename of `enabled_bots` → `required_bots`/`optional_bots` left a consumer reading the retired name. Nothing errors; the consumer just silently sees nothing.
2. **A vacuous guard.** The empty-set branch is now the only reachable branch, so a check that reads as "we verified no bots are required" actually means "we could not see the bots at all". This is the **vacuous-guard archetype** (recorded 4× in this corpus, once introduced by a fix for it) crossed with the **enabled-bots-vs-operative drift** archetype — a combination that has bitten this project before.

The consequence is directly visible in this very plan: PR #1073 merged with **no bot having read the diff** (see the separate `PROCEED UNREVIEWED` finding), and the bot-configuration read path could not have flagged it.

## Suggested shape of the fix

Update Step 3.6 to consume `required_bots` / `optional_bots`. Then add the guard that actually matters: **an unknown/absent manifest key must fail loud**, not resolve to an empty set. A consumer that cannot find its key has learned nothing and must not report a verdict.

Worth a population-derived sweep for other consumers of the retired `enabled_bots` name — a single named call site is a **sample**, not an enumeration.

## Not actioned

Out of PLAN-TRUTH-001's scope. Handed to the epic.
