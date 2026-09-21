# Landing: PLAN-CIS-003 — marketplace-dependency-resolver

epic: code-intelligence-substrate
workstream: WS-02
plan: `marketplace-dependency-resolver`
PR: #1074 — merged `021305e26`

## Corroboration — the merge is REAL

⛔ **Corroborated with extra care, because THIS SENDER filed a false landing claim on its previous
message** (`marketplace-dependency-resolver-001.md`, 2026-08-01, claimed a merge while #1074 was
still open). That message is now retroactively true; the earlier refusal was correct at the time.

- `git log origin/main` — `021305e26 feat(tools-marketplace-inventory): wire resolver into arch graph (#1074)` present.
- 6/6 deliverables, 22/22 finalize steps, 3 recorded operator deviations.

**Row transitioned to `shipped`.** The plan shipped. What it *achieved* is a separate question, below.

## ⛔ THE HEADLINE CLAIM IS REFUTED AT HEAD — the founding defect is NOT closed

The report states: *"The epic's founding defect is closed. `architecture impact` now merges 3
resolvers — markdown, maven, python — spanning both extension hierarchies, **over a real non-empty
edge set**."* Deliverable 4 is recorded as *"End-to-end proof: `architecture impact` returns
non-empty [OK]"*.

**Probed live at HEAD after the merge. It does not reproduce:**

| Probe | Result |
|---|---|
| `architecture graph` | **`edge_count: 0`**, `edges[0]` |
| `architecture impact --module plan-marshall` | **`impact[0]`** — empty |
| `architecture impact --module pm-documents` | **`impact[0]`** — empty |
| `architecture neighbors --module plan-marshall` | `neighbors[1]: plan-marshall` — **itself only** |
| all 12 modules in `graph` | listed as **BOTH `roots` AND `leaves`** — the signature of a zero-edge graph |

Meanwhile the **resolvers themselves report edges**: `markdown, 24, ok` · `maven, 0, ok` ·
`python, 5, ok` · `resolver_count: 3`.

⭐ **So 29 resolver-derived edges exist and the merged graph has zero.** The resolvers are wired
and running — that half of the plan is real and verified. The edges do not survive into the graph.

### Stale data is RULED OUT — this is not a refresh being owed

`architecture derived-module --module pm-documents` shows deliverable 1 shipped and the persisted
data current:

```text
component_refs[8]{target_bundle,dep_type,resolved}:
  plan-marshall,implements,true      <- cross-bundle, RESOLVED
  plan-marshall,import,true          <- cross-bundle, RESOLVED
  plan-marshall,path,true            <- cross-bundle, RESOLVED
  plan-marshall,script,true          <- cross-bundle, RESOLVED
  pm-documents,path|script|skill     <- self-refs
  pm-plugin-development,path,true    <- cross-bundle, RESOLVED
```

**Five resolved CROSS-BUNDLE refs sit in pm-documents' own persisted module data, and
`pm-documents` is still reported as both a root and a leaf.** The inputs are present, fresh, and
resolved; the output is empty. This is a live defect in the derivation-to-merge path, not a
missing refresh and not a stale plugin cache (the three new resolvers are present and executing,
so #1074's code IS the code running).

### What this is, precisely

⛔ **The epic's own standing warning fired a second time, one tier down.** The PLAN-02 landing
recorded: *"⛔ Do not read 'F2 retired' as 'the graph has edges'."* The successor claim is
**"resolvers wired" ≠ "the graph has edges"** — and this time it was reported as closure.

⚠ **The plan's own spec named this exact risk and it appears to have gone unsettled.** Its central
HYPOTHESIS was: *"the two vocabularies can be mapped without loss — the graph family is
module-granular (12 bundle nodes) while the engine is component-granular (294 components)…*
***This is the plan's central risk**: if module-granularity is the wrong exposure, deliverable 3
becomes a design decision rather than a mapping, and the plan must loop back rather than proceed."*
The observation is consistent with that mapping dropping every edge at the merge boundary — but
⚠ **the mechanism is a HYPOTHESIS, not established.** The *observation* (29 resolver edges, 0 graph
edges, fresh resolved inputs) is solid; the *cause* needs deriving.

**Candidate mechanisms to discriminate, none yet confirmed:** the merge dropping pairs whose
endpoints are not both known module names (the documented "a resolver cannot invent a node" limit);
the 24 markdown edges collapsing to self-edges after module-granular mapping; or the graph reading
a persisted edge set that the live resolvers never write into.

⭐ **How D4's "end-to-end proof" passed while the live system returns empty is itself the finding
worth the most.** A proof that passes in-plan and fails on main is either scoped to a fixture, or
asserts the resolver-level count rather than the merged graph. **That is the test-pins-the-defect
archetype this epic already tracks** — and it means the deliverable's own evidence needs auditing,
not just the code.

## What DID land, verified

- ✅ **Three resolvers execute and report**, spanning both extension hierarchies — markdown
  (pm-plugin-development), python (pm-dev-python), maven. `resolver_count: 3`.
- ✅ **`component_refs` materialized into module discovery** with `target_bundle` / `dep_type` /
  `resolved`, cross-bundle refs correctly resolved.
- ✅ **Suppression reporting works and is informative** — `unresolved-target: 32 suppressed`,
  `self-edge: 21 suppressed`, with samples. The provenance contract is doing its job; it is what
  made this diagnosis possible at all.

## Operator decisions recorded

- Python resolver → `pm-dev-python` (operator call; the "not guaranteed active" objection was
  **verified unfounded**, not assumed).
- mypy scope defect fixed in-plan rather than deferred.
- Ship with optional bots absent — **which the barrier then overrode by finding them.**

## Review — the barrier earned its keep again, harder

**CodeRabbit found 6 actionable items on a diff pr-agent called "no major issues detected."** Four
were genuine, including a **TypeError crash path in `build.py` that contradicted its own
"fails open by design" docstring**. Two were refuted on evidence. ⛔ **Without the barrier all four
land unreviewed** — second consecutive landing where this is true.

⭐ **Three self-corrections the plan made, which are worth more than its successes:**

1. **`review-retrospective.md` had shipped a falsehood** — written at `order: 50`, *before* the
   review it claimed to measure. Rewritten from post-merge evidence rather than archived false.
   ⭐ **Same archetype as the CIS-023 retrospective-input defect: a step scheduled where its input
   does not yet exist.** Two independent sightings now — this is a pattern, not an incident.
2. **Its own triage refuted CodeRabbit finding `cd99e7` on a FALSE PREMISE**, citing a q-gate
   resolution that argues *against* the refutation. Honest score restated as **4 confirmed /
   1 refuted / 1 refuted-but-mostly-right**. Residual doc drift shipped; filed as msg 021.
   ⚠ **This is the counterweight to CIS-023's celebrated refutation** — refuting a bot finding is
   correct practice, and is itself capable of being wrong.
3. **Withdrew an earlier "CI skipped the build" warning** once two-runs-per-head became visible —
   the evidence never supported the inference.

## Cost

**4.9 M tokens · 12h50m wall / 5h19m worked. Finalize alone 2.5 M (52%)** across the barrier cycles.

⛔ **Finalize above 40% for a FOURTH consecutive landing** (3.4 M/42%, PLAN-11 48%, and now 52%).
Four points is a trend with a rising slope. → owners PLAN-CIS-008 / PLAN-CIS-014; this is no longer
a watch item awaiting data.

⚠ **Self-inflicted cost recorded by the plan itself**: it asked the operator to babysit a merge-lock
block instead of arming a Monitor that was available throughout, and three later monitor predicates
fired on non-events by gating on *absence-of-known-in-progress-markers* rather than the producer's
**terminal marker**. ⭐ Gating on absence-of-a-negative rather than presence-of-the-terminal-signal
is a reusable defect shape.

## Ledger effects

- Row: status `shipped`, pr `1074`, landing `landings/PLAN-CIS-003.md`.
- ⛔ **F2 / F5 STAY OPEN.** The founding defect is not closed. A follow-up plan is owed at
  **PLAN-CIS-027** to derive why 29 resolver edges yield 0 graph edges, and to audit D4's proof.
- ⚠ **PLAN-CIS-004** (native-coordinate-resolvers) and **PLAN-CIS-026** (LSP derivation resolver)
  both add resolvers through this same merge path. **Both are now suspect** — adding a fourth and
  fifth producer to a merge that drops its inputs adds nothing. **Sequence PLAN-CIS-027 ahead of
  both.**
- 21 inbox messages filed by this plan (1 landing, 19 candidate-lessons, 1 triage-error finding).
