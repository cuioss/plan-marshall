# PLAN-TRUTH-019: In-house build gate ↔ CI coverage parity — the gate passes what CI would fail

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-30 from the **build-gate half of the former PLAN-60**, returned by `review-apparatus`
> (message `review-apparatus-004`, operator decision). That epic kept only the *review* half as its
> `PLAN-PR-011`; everything below is build-gate work and is not review-apparatus subject matter.
> **This is a re-issue, not a rename** — PLAN-60's row stays `transferred`, because its review half
> lives on there under a different id.

## Objective

The local pre-push quality gate reports a clean pass for footprints CI would reject. Each instance is
a different hole in the same property — **the in-house gate's coverage is a subset of CI's, and it
never says so.** Close the holes and make the gate's coverage claim honest about what it did not check.

## Deliverables

### D1 — GATE: derive the parity population before fixing any instance (mutates nothing)

Enumerate where local gate coverage and CI coverage diverge, from the tool configuration on both
sides, and produce the parity table. ⛔ **Do not scope the fix to the four instances named below** —
they are the observed sample, and this epic has been burned four times by a detector built from a
sample rather than a derived population. D1's output is the population; D2–D3 fix from it.

### D2 — linter and type-check parity

- **`OBSERVED`** — the `RUF` rule family is absent from the local ruff `select=`, so CI-visible
  findings are locally invisible. Lesson `2026-06-22-13-001`.
- **`OBSERVED`** — `pre-push-quality-gate` lacks `mypy test` test-compile parity. Lesson
  `2026-07-24-13-001`.
- **`OBSERVED` — the cost is already paid, not hypothetical:** `quality-gate` excludes `test/`, and
  **three mypy errors reached `verify` on #1037** as a direct result.
- **`OBSERVED`** — a whole-tree test-compile gate sees failures that mypy over `test/` alone cannot.
  ⇒ These two together are why D2 is a *parity* fix and not a config tweak: widening the file set and
  widening the rule set are independent holes, and closing either alone still passes what CI fails.

### D3 — divergence-gate branch integrity

- **`OBSERVED`** — the module-tests divergence gate has a **zero-scoped-modules / docs-only branch**
  that resolves to a clean pass. Lesson `2026-07-21-11-003`.
- **`OBSERVED`** — non-bundle root footprint (`marketplace/targets/**`) is not escalated to the
  whole-tree gate. Lesson `2026-07-21-21-002`.

⛔ **DEDUP CONSTRAINT — read before scoping D3.** The zero-scoped-modules → docs-only → clean-pass
branch is **the same conflation** as `PLAN-TRUTH-010` D4b (`resolve-test-scope` returning
`recommended_target: null` for Python source it cannot resolve): in both, *"no module matched"* and
*"no tests needed"* are the same signal. **These are two consumers of one defect, and they must not be
fixed twice in different shapes.** Whichever plan reaches outline second re-grounds against the
other's actual fix. ⇒ **`PLAN-TRUTH-010` and this plan are a serialization pair — never run them
concurrently.** ⭐ Recorded at staging rather than discovered at outline, because the overlap was only
visible from having drained both signals in one session and would not survive a fresh context.

### D4 — the gate must report what it did NOT check

The through-line of D2 and D3: every hole above presents as a **clean pass**, never as an
incomplete one. Make the gate's own output name its coverage boundary, so a footprint it could not
fully check is distinguishable from one that genuinely passed. This is the epic's fail-closed
discipline (`PLAN-TRUTH-010` D3) applied to the gate's own verdict — cross-link, do not re-author it.

### D5 — promote the landed residues and re-bind the returned lessons

Promote the token-detector item (`2026-06-25-02-001`) and the three landed residues
(`2026-06-20-16-002`, `2026-07-17-09-002`, `2026-07-23-02-001`), then retire the carried lessons.

## Lessons Carried

Re-bound here 2026-07-30 from the PLAN-60 split. ⚠ `review-apparatus`'s `PLAN-PR-011` carries exactly
`2026-07-21-10-002` and `2026-07-17-09-001` and explicitly **not** the rest; the remainder is this
plan's to bind, which is what this section does.

- `2026-06-22-13-001` — RUF family absent from local ruff select (D2)
- `2026-07-24-13-001` — pre-push-quality-gate lacks mypy test parity (D2)
- `2026-07-21-11-003` — zero-scoped-modules / docs-only branch (D3)
- `2026-07-21-21-002` — non-bundle root footprint not escalated (D3)
- `2026-06-25-02-001` — token detector (D5)
- `2026-06-20-16-002`, `2026-07-17-09-002`, `2026-07-23-02-001` — landed residues to promote (D5)

## Expected Surface

- `HYPOTHESIS`: the local ruff / mypy configuration and the CI workflow that must match it
  (verify-at-outline; D1 names the exact files).
- `HYPOTHESIS`: `phase-6-finalize/standards/pre-push-quality-gate.md` (verify-at-outline).
- `HYPOTHESIS`: the module-tests divergence-gate implementation (verify-at-outline) — locate by
  SYMBOL, never by line number.
- `OBSERVED`: the corresponding gate tests.

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Serialization pair with `PLAN-TRUTH-010`** — see the D3 dedup constraint.
- ⚠ **Cross-epic coupling, and it needs a PR number.** If D2/D4 moves
  `phase-6-finalize/standards/pre-push-quality-gate.md`, that file is `PLAN-PR-011`'s candidate home
  for a coverage-parity standard. Per the convention both epics have now adopted, **name this plan's
  PR to `review-apparatus` when it opens** so they retire the deferral by checking rather than by
  remembering. ⛔ Re-verify this collision **at outline** against their live queue, not from this note.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-019-build-gate-coverage-parity.md"
```

## ⭐ FOLDED 2026-08-02 — a FIFTH hole, and it is the sharpest one yet

**From `review-apparatus-012` item 13** (observed on PR #1078), delegated to us:

> The local pre-push **test-compile gate passed in 2–5 seconds** across consecutive rounds. **CI on the
> same tree checked 660 files and found 2 real type errors.** Cause: a stale **mypy incremental cache**
> — the gate answered *"nothing I have cached changed"* and that was consumed as *"the tree
> type-checks."*

⇒ This is precisely this plan's subject: **the local gate passes what CI fails.** Fold it as an
additional hole in the D0 population; do not file it separately.

⛔ **Why it is sharper than the other four**: the existing holes are about **scope** (the gate does not
look at `test/`, etc.). This one is about **staleness** — the gate looks at the right scope and answers
from a cache. ⇒ **A coverage-parity fix that only widens what the gate examines does NOT close it.**
D0 must treat cache validity as a distinct dimension from scope.

⭐ **Add a duration sanity check**: an implausibly fast gate is a failure signal. This is the
`never-trust-a-routed-build's-outer-status` archetype arriving through a **cache** rather than a router
— **confident + fast + repeated, read as reassurance.**

⚠ **REPORTED, not re-derived** (bundle 0.1.1276). Confirm the mypy-incremental configuration at D0
before designing around it.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
