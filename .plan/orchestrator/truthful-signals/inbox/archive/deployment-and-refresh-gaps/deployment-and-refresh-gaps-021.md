envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-04T07:17:21Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `plan-09-local-gate-truthfulness` (PR #699, merged `6c1bd849`), original inbox message `plan-09-local-gate-truthfulness-004.md`, promoted locally as lesson `2026-09-04-07-004`. The body below is that message's payload **verbatim**; the relaying orchestrator added only this provenance line.

# Candidate lesson: `reconcile` heals the manifest step LIST but not step PARAMS, so a plan that fixes a config value still runs against the frozen defective one

**Proposed component**: `plan-marshall:manage-execution-manifest`
**Proposed category**: `bug`
**Evidence**: decision log, plan `plan-09-local-gate-truthfulness`, phase `6-finalize` — "Manifest step-param override applied: automatic-review.required_bots 'coderabbit,cuioss-review-bot' -> 'coderabbit,pr-agent'"

## What happened

This plan's deliverable 3 corrected `required_bots` in `.plan/marshal.json` — the whole point of that deliverable was
that the value named an **author_login** where it should have named a **bot_kind**.

The plan-local execution manifest is a **compose-time snapshot**, taken at outline, *before* deliverable 3 landed the
correction. At finalize, the `automatic-review` step therefore read the frozen, defective `required_bots` value from
its own step params rather than the corrected value in `marshal.json`. `reconcile` did not heal it, because
**`reconcile` heals the step LIST, not step PARAMS**.

The run caught this and applied an explicit step-param override at the dispatch site
(`coderabbit,cuioss-review-bot` → `coderabbit,pr-agent`), with the reasoning recorded in the decision log.

## The durable content

**A plan that corrects a configuration value during its own run will execute the rest of that run against the
pre-correction value, unless the param is overridden explicitly at the dispatch site.** The manifest's snapshot
semantics are correct in general — they are what makes a run reproducible — but they create a specific blind spot for
exactly the class of plan whose deliverable *is* a config correction.

This plan came within one override of reproducing the very defect it was fixing: had the override not been applied,
`automatic-review` would have gated on `cuioss-review-bot` (an author_login that names no bot_kind), which is the
misconfiguration deliverable 3 existed to remove.

## Why this would change a future run's behaviour

Two candidate responses, for the orchestrator to weigh:

1. **Cheap and local**: a plan whose declared surface includes a `marshal.json` key that feeds a finalize step's
   params should be required to re-check that step's params against the corrected value before dispatch. This is what
   this run did by hand.
2. **Structural**: extend `reconcile` (or add a companion verb) to re-derive step PARAMS from the live config for
   steps whose param source is `marshal.json`, so the healing surface matches the drift surface. The asymmetry
   between "heals the list" and "does not heal the params" is not documented at the point of use, which is why the
   gap had to be discovered by inspection rather than reported.

The generalisable form is broader than manifests: **any compose-time snapshot of a value the run is authorised to
change needs either a re-derivation path or an explicit statement of what it does not heal.**
