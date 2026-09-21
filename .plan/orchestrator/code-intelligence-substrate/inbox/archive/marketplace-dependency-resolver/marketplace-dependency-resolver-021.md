envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=finding
created=2026-08-01T23:29:08Z

component=plan-marshall:extension-api
category=bug
title=Residual count-prose drift shipped in PR #1074; a triage refutation cited an authority that argued against it

# Residual count-prose drift at `ext-point-derivation-resolver.md:3`, and the triage error that let it ship

## The defect that shipped

`marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md` line 3 currently reads:

```
| **Implementations**: see [§ Current implementations](#current-implementations) | **Status**: Shipped — the `extension_base.py` ABC is wired and three resolvers implement it, two opting in from Axis-A and one from Axis-B
```

The cardinality claim (`three resolvers`, `two … from Axis-A`, `one from Axis-B`) is **not adjacent to its enumeration** — the enumeration is behind a cross-reference. A fourth resolver requires a header edit that nothing forces, which is the count-prose staleness archetype this project already tracks. Two sibling sites in the same change set are fine: `doc/concepts/extension-architecture.adoc:28` and `ext-point-derivation-resolver.md:155` each carry their count beside the list it counts.

## Why it shipped — a triage error, not a missed finding

CodeRabbit **did** flag it, as finding `cd99e7` on PR #1074. The plan's unified triage **declined** it on the premise "every count already sits adjacent to its own enumeration, so the enumerate-exactly rule is satisfied." That premise is true for the two sibling sites and false for line 3, and the refutation generalized from the sites it checked to the one it did not.

The compounding error is the citation. The disposition named q-gate resolution `817899` as the authority requiring that wording. `817899`'s own recorded resolution prescribes the opposite — *"a roster-free replacement so a fourth resolver needs no header edit"*. **The cited authority argues against the refutation it was cited to support.**

Honest scoring of CodeRabbit's 6 actionable findings on PR #1074 is therefore **4 confirmed / 1 soundly refuted / 1 refuted-but-substantially-correct**, not the 4/2 the triage recorded.

## The generalizable rule

A refutation that rests on a universally-quantified premise ("*every* count is adjacent to its enumeration") must enumerate the population before asserting it. Checking two instances and generalizing is the same sampling error as a reviewer naming three call sites when fourteen exist — here it was committed *while rejecting a finding*, which is the direction that leaves no trace: a wrongly-accepted finding produces a visible no-op fix, a wrongly-refuted one produces silence.

Second rule: when a disposition cites a prior decision as authority, the citation must be **read**, not recalled. `817899` was resolved earlier in this same plan and its text was available.

## Suggested fix

Replace the line-3 `**Status**` clause with a roster-free formulation carrying no cardinality, exactly as `817899` prescribed. Verify no other cardinality claim in the document sits apart from its enumeration.
