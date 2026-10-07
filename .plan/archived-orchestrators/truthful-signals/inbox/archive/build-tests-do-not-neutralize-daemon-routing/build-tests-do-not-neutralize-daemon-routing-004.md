envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:02:04Z

component=plan-marshall:execution-context
category=bug

# The dispatched leaf has no search primitive — and it blocked real work in this run

`Grep` and `Glob` were **unavailable** to dispatched agents throughout this session, and the project's file-operation hard rule (with its enforcement hook) additionally blocks recursive `grep` / `find` via Bash. A dispatched leaf therefore has **no** broad content-search primitive at all: the declared-tools list advertises `Grep`/`Glob`, the runtime denies them, and the documented Bash fallback is hook-blocked.

This is exactly the defect PLAN-105 describes. **PLAN-105 was superseded WITHOUT LANDING, so the gap is live.**

It blocked real work here. The phase-5 leaf needed a population census across the build-factory test surface. With no search primitive it could have shrunk coverage to the 3 files whose *filenames* matched — a coverage deletion that a green suite would have hidden. It **correctly refused to fabricate the census** and returned the gap to the orchestrator instead, per the sanctioned "return the coverage gap rather than pass green with shrunken coverage" contract. The contract worked; the capability gap it exists to paper over is still there.

## Solution

**Re-queue PLAN-105.** The gap is live in main and it is now confirmed to block, not merely inconvenience.

The workaround this plan used is worth promoting on its own merits: instead of ad-hoc greps, write a **deterministic, re-runnable census script** that derives the population from the AST and commit it alongside the deliverable. For a population-derivation deliverable this is *better* evidence than greps would have been — it is reproducible, it is reviewable, and it re-derives the population on every future run rather than pinning a number measured once. Compare `test/_shared/_dispatch_roster.py`, the existing precedent for population-derived detectors.

Interim guidance for a leaf that hits the gap:

1. Try the structured architecture inventory first (`architecture find --pattern`, `which-module`, `files --module`).
2. `Read` inside an already-known file.
3. If neither can cover the surface, **write a census script** rather than degrading to spot-checks.
4. If even that is out of scope, return the coverage gap to the orchestrator. Never silently shrink coverage.

## Impact

Affects every dispatched leaf performing coverage-class work — sweeps, audits, population-derived detectors, refactor campaigns. The failure mode when the contract is *not* followed is the recurring `volume-read-as-coverage` archetype: a leaf reports "N candidates examined" where N is what it could reach, not what exists.
