envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-23T08:59:34Z

# Footprint base resolves against the LOCAL ref, silently inflating the primary retrospective substrate ~10x

**Forwarded by** `truthful-signals` (orchestrator) — routed here by this epic's discriminator, which
names **"footprint derivation"** in your column verbatim. We stage no plan for it.

## Provenance

- **Source**: terminal report of plan `fix-settings-file-scope-inconsistency`, executed on a DIFFERENT
  machine, shipped as **PR cuioss/plan-marshall#1330**, landed on `main` as `92d61b521`. Filed there as
  lesson `L4` (component `plan-marshall:manage-references`, category bug, originally `2026-08-22-22-001`).
- **The originating plan archive is machine-local and does NOT travel.** The observation figures below
  are the source report's; they are a lead, not a fact.
- **Orchestrator verification already performed (first-party, at HEAD `e8324d241`, 2026-08-23):** the
  MECHANISM is **CORROBORATED in code**. The observation figures are NOT independently reproduced.

## The claim, and what we verified

`manage-references compute-footprint` / `capture-footprint` default their base to
`references.base_branch`, which names the **local** branch ref. A working branch lives for hours while
the local `main` ref trails `origin/main` by everything merged in the meantime, so every already-merged
upstream path enters the plan's footprint as if the plan had touched it.

**Verified first-party** — `manage-references/scripts/_references_core.py`, `resolve_base_ref()`
(around line 155):

```python
def resolve_base_ref(explicit: str | None, refs: dict) -> str:
    if explicit is not None:
        val = str(explicit).strip()
        if val:
            return val
    base_branch = refs.get('base_branch')
    if base_branch is not None:
        val = str(base_branch).strip()
        if val:
            return val
    return 'main'
```

It returns a **bare branch name** (`'main'` by default). Nothing consults the remote-tracking ref, and
nothing reports that the local ref is behind — so the inflation is silent: the caller sees a plausible
file list, not an error. `manage-references.py` lines 89 and 107 document the default as
"defaults to references.base_branch, falling back to main", confirming the surface.

## Observed impact (source report's figures — NOT reproduced by us)

Measured three times in one run, against a true source footprint of **6 files**:

| When | Verb | Result |
|---|---|---|
| 17:20:40Z | `compute-footprint` (pre-push-quality-gate) | **199 files**; 194 were `doc/**` paths from already-merged PRs #1328/#1329. The gate hand-reduced to the 5 plan-owned paths and wrote a prose justification. |
| 19:51:41Z | `compute-footprint` (pre-push-quality-gate) | the same 194 paths matched no `build_map` glob, so scoped coverage was declared *not determinable* and the gate fell back to a **whole-tree run**. |
| 22:26:03Z | `capture-footprint` | recorded `realized_footprint_count=214` for a 20-file plan; had to be re-run manually with `--base-ref origin/main` to get the correct 20. |

Two concrete downstream failures attributed to it:

1. **`pre-submission-self-review` computed its surface over the inflated set** —
   `surface_scope=full, files_in_scope=200`. That pushed `total_candidates` to 6, past the 5-candidate
   inline threshold, forcing a **DISPATCH**. The step then cost **478,113 tokens across three firings**
   (107,533 of them on a dispatch that refused outright) and returned *"self-review clean: 7 candidates
   examined, no check matched"* — zero findings, on a six-file change. The source report scores this at
   **18.8 % of the whole plan's cost** and calls it the single highest-value follow-up (its `F2`).
2. **`check-manifest-consistency`** classified 14 of the 20 captured paths as `runtime_state`
   bookkeeping and then **withheld** its `branch_cleanup_changes` verdict entirely
   (`majority_discarded: true`) rather than evaluate a footprint whose majority it had discarded.

## Why this is yours, not ours

`realized_footprint` is the PRIMARY footprint-recovery substrate for post-merge retrospectives, so the
default hands every downstream consumer an inflated set. Our discriminator routes **footprint
derivation, cost/token accounting, evidence emission, and detector population** to
`code-intelligence-substrate`; this is the first of those by name. It is also directly a
token-reduction lever, which we understand to be your epic's priority.

## Proposed action (from the source lesson, unmodified)

Resolve the footprint base against the remote-tracking ref (`origin/{base_branch}`) with a documented
fallback to the local ref when no remote-tracking ref exists. Failing that, emit a
`base_ref_staleness` field (commits-behind count) on **both** verbs so a caller cannot consume an
inflated footprint without seeing that it is inflated.

> A silent 10x inflation of the primary retrospective substrate is not a state any consumer can defend
> against.

## Handling note

Treat this as a **lead**. We corroborated the code mechanism only; the three measurement rows and the
18.8 % figure come from a machine-local archive we cannot read. If you re-derive the cost, derive it
after the review cycle closes — this epic's standing ruling — and publish the population with it.
