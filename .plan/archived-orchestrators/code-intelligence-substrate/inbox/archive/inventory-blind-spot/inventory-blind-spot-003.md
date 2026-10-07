envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T15:49:46Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# The kinds a request names are a SAMPLE — measure the population, then write a name-free rule

## Observation

The `inventory-blind-spot` request named **3** invisible skill sub-directory kinds
(`workflow/`, `references/`, `examples/`). Measured live against `marketplace/bundles/`, the real
population was:

- **6 distinct sub-directory kinds** (excluding `standards/`, `templates/`, `scripts/`)
- **138 markdown files**
- **+4 non-markdown files** (2 `.json`, 1 `.toon`, 1 `.yml`)

An allowlist of the 3 named kinds would have left **8 files still invisible** and would have re-broken
on the **seventh** kind — reproducing the exact defect the plan existed to fix, in the same idiom.

## The second, subtler axis

The first outline correctly reasoned its way out of a *directory-name* allowlist ("a name allowlist
re-breaks the moment a seventh kind appears") — and then specified the residual rule as
**"any remaining `.md` under `skills/<skill>/**`"**. That rule is name-free over **directories** but
**enumerated over extensions**. The blind spot survived on the other axis. Worse, the plan's own
population-derived regression test was specified to "collect every `.md` … and assert zero classify as
`None`" — its population was narrowed to `.md`, so the test **structurally could not detect the
extension gap it existed to prevent**. That is the vacuous-guard shape.

## Solution

1. **Measure the population before writing the rule.** Never take the requester's enumeration as the
   set — it is a sample drawn from whatever they happened to notice.
2. **Make the rule free on every axis the defect can travel.** Here: name-free over directories AND
   extension-free over formats — "any remaining **file** under `skills/<skill>/**`". Precedent already
   existed in the very function being edited: the `templates/**/*` rule had no extension test.
3. **Derive the guard test's population from the same unfiltered walk as the rule.** If the test's
   collection step carries a filter the rule does not, the test is vacuous over exactly the gap the
   rule was widened to close.
4. When a narrower scope IS the deliberate choice (the generic non-marketplace classifier stayed
   extension-driven, because path position carries no role guarantee in an arbitrary project),
   **pin the boundary with an assertion** — assert the in-set extensions classify, and that a known
   out-of-set extension still returns `None` — so the narrowness is asserted rather than silent.

## Impact

This is the population-derived-detector rule applied to *rule authoring*, not just to detectors:
a fix written against a named sample inherits the sample's blind spot. The recurrence signature to
watch for in an outline: a rationale paragraph that correctly rejects an allowlist on one axis,
immediately followed by a rule that is an allowlist on a different axis.
