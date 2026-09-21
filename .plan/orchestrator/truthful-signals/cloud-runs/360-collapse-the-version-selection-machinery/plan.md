> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Collapse the version-selection machinery — most of it exists to serve a baked absolute path

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Four of the seven links in the plugin-cache staleness chain are **ours**, and they exist only to manage
a problem two earlier links create.

| # | Link | Owner |
|---|---|---|
| 1 | The cache is laid out `{base}/{bundle}/{version}/skills/` | **Inherited** — the plugin host's layout, not changeable |
| 2 | Each sync creates a NEW version directory and **never deletes** | **ours** |
| 3 | Executor generation **bakes absolute, version-pinned paths** into the generated script | **ours** |
| 4 | A multi-version pollution detector — needed because 2 + 3 put several versions on the import path | **ours** |
| 5 | An orphan marker — exists to **silence 4** on the next preflight | **ours** |
| 6 | Retention pins — exist to stop **5 saturating** | **ours** |
| 7 | The plugin host's own collector **also reads that marker**, in a different encoding | **shared field, two producers** |

⇒ **Links 4–6 are pure containment for 2 + 3.** Link 7 exists only because we chose someone else's
filename.

⭐ **The plan removes the reason they exist rather than adding an eighth link to guard the seventh.**

## ⛔⛔ The invariant that was supposed to make this safe is REFUTED BY OBSERVATION

The retention-pin function's docstring states, twice, that pinning makes marker saturation
**"structurally impossible"** — *"the dir the resolver selects is pinned unconditionally, so at least one
live version dir always survives per bundle."*

**Measured: every version directory orphan-marked, including the registry pin and the executor's own
version.**

⭐ **The reason the guarantee fails is circular and visible in the code**: the disk arm of the pin
selects **among live (unmarked) directories**. Once saturation is reached by any route, that arm returns
nothing and **cannot recover** — **the guard against reaching the state depends on not already being in
it.** The two remaining arms track values that lag the directory the resolver actually wants.

⚠ **The system survives it**: the bundle finder has a documented **degraded all-orphaned fallback** that
returns the newest directory and warns. ⇒ **We are running in the degraded path, by design, with a
warning nobody is reading.** That is the honest status — not "broken", and not "fine".

## ⭐⭐ The strongest argument for the structural fix: a third party writes AND DELETES the field

Marker timestamps caught a transition to the millisecond: one directory was marked in the **foreign
encoding**, and 66 ms earlier, in the same operation, **another directory's marker was DELETED**.

⇒ **The foreign producer re-anchors the entire marker set on the registry, adding and removing markers
on its own schedule.** Three consequences:

1. **We do not own the field's lifecycle, only its writes.** A value we write can be deleted by a third
   party at an instant we neither choose nor observe. **Any containment built on it is built on a
   variable someone else assigns.**
2. **The marker set is not an independent signal** — it is a **lagging function of the registry**, so a
   "sole unmarked dir" oracle **counts the registry as two witnesses.**
3. **It bounds a sibling plan's own conclusion**: that plan's control measurement is confounded a second
   way — **the observation window is truncated by marker RESETS**, not only by our own sweep.

⇒ **Resolving at executor runtime makes the whole question unrepresentable. No oracle is needed for a
state that cannot occur.**

## Goal

The executor resolves bundle paths at run time rather than freezing them at generation time; nothing we
own writes a field a third party also owns; and every containment mechanism the change makes dead is
deleted rather than left dormant.

## Deliverables

1. **D0 — GATE: confirm the chain and its ownership column by symbol.** Mutates nothing. Derive every
   consumer of a baked executor path and of the shared marker, **in both directions** — what reads it,
   and **what would break if it stopped existing**.
   *Done when:* the ownership column is confirmed from source and both consumer sets are enumerated.
   ⛔ **If any of links 4–6 turns out to be required by the plugin host rather than by us, the plan
   re-scopes to the links that are genuinely ours.**
   ⛔ **Also establish WHY the paths were baked.** Startup cost? Determinism? **The reason decides
   whether the structural fix is a straight win or a trade** — and it is the reason the paths exist.
2. **D1 — LEVER A, the structural one: stop baking absolute version paths into the executor.** Resolve
   bundle script directories **at executor runtime** from a single selector.
   *Done when:* an executor generated against one version still resolves after that version is deleted.
   ⭐ **This is the root fix**: an executor that resolves at run time **cannot be pinned to a collected
   directory**, so the split becomes **unrepresentable rather than detectable**.
   ⚠ **Measure the startup cost this adds.** If it is material, **that is the trade to state**, not to
   discover later.
   ⛔ **A runtime resolver that still consults the marker set has MOVED the problem, not removed it.**
3. **D2 — LEVER C, the cheap one, independent of D1: stop writing the shared marker.** It is the plugin
   host's field. If a marker is still needed after D1, **use a namespaced one we own.**
   *Done when:* no write to the shared field remains under our tree.
   ⭐ **This retires the entire two-producers-one-field defect by NOT SHARING THE FIELD** — a rename is a
   smaller change than reconciling two encodings forever.
   ⛔⛔ **BUT: the marker's existence-only invariant is now STATED AND TEST-ENFORCED by a
   population-derived test that landed recently.** Removing the write **may require retiring or
   re-scoping that test**, and ⛔ **doing so silently would be exactly the "delete the guard to make the
   change pass" move this epic files against.** **Name it as a deliverable, or state explicitly why it is
   untouched.**
4. **D3 — LEVER B: evaluate keeping ONE version directory. Do not assume it.** Delete-on-sync rather
   than accumulate-and-mark.
   *Done when:* **the decision is RECORDED either way.** ⛔ **Adopting it is not required.**
   ⚠ **This is the risky lever, and the reason deletion was deferred to markers in the first place** — a
   superseded directory may still be on a running process's import path. **Evaluate against D1's
   outcome**: if the executor resolves at runtime, the exposure changes.
5. **D4 — Retire what the levers make dead.** Whichever of the pollution detector, the marker sweep, the
   retention pins, and the degraded fallback are no longer reachable get **deleted, not left as dormant
   code**.
   *Done when:* no unreachable containment code remains.
   ⭐ *Where a copy exists, delete the copy* — the standing rule applies to superseded machinery too.
6. **D5 — Correct the saturation claim wherever it is stated.** The "structurally impossible" docstrings
   **are wrong and were wrong when written.**
   *Done when:* no document asserts the refuted guarantee.
   ⛔ **A refuted guarantee in a docstring is worse than no guarantee, because the next reader trusts
   it** — this epic's own thesis, in our own code.
7. **D6 — Tests, each verified to FAIL pre-fix.**
   - (a) An executor generated against a version **still resolves after that version is deleted**.
   - (b) A saturated cache resolves **without** the degraded fallback.
   - (c) ⛔ **A matched negative control: a genuinely broken cache still fails LOUDLY.**
   - (d) No write to the shared marker remains under our tree.
   *Done when:* all four pass, each seen red first.

Seven deliverables, under the raised cap.

## Out of scope

- ⛔ **Writing the plugin registry, or anything under the plugin host's own directory.** Read only.
- **Retiring the sibling detector plan.** ⛔ **It is NOT superseded by this.** A detector for a state that
  can no longer occur *is* dead code — **but its oracle also covers pin-versus-source content
  staleness, which this plan does not address.** ⛔ **Re-scope it after this lands; do not pre-emptively
  retire it.**
- **Re-opening the marker ENCODING question.** ✅ It was settled in the direction that *helps* this plan:
  our markers age out normally, so the inverted "write the foreign encoding" remedy is **REFUTED, not
  deferred.** ⇒ **There is no live proposal to fix the encoding**, so removing the field is no longer an
  opposite-direction collision.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — the
  marker sweep, the retention pins, the pollution detector, and the path-baking site.
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` — the sole
  marker read and the degraded fallback.
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py` — the sweep's
  keep-union.
- The plugin-doctor shared helper's single marker reference.
- The existence-only invariant test (D2).
- Tests.

⛔ **NEVER the plugin host's registry file.** Read only.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The seven-link chain and its ownership column | HYPOTHESIS | the four named files, **by symbol** — **D0 confirms; the column is the plan's premise** |
| Saturation was measured with every directory marked, against a docstring asserting it impossible | HYPOTHESIS | ⛔ **a live machine state, NOT reachable from this clone.** ⭐ **But the CIRCULARITY is checkable from source**: the disk arm selects among live directories, so the guard depends on not already being in the state it guards against |
| The degraded all-orphaned fallback exists and warns | HYPOTHESIS | the bundle finder, **by symbol** — checkable here |
| The foreign producer both writes and DELETES markers, re-anchoring on the registry | HYPOTHESIS | ⛔ **marker timestamps on a live machine, NOT reachable here.** ⭐ **Its consequence is a design argument that needs no measurement**: a field a third party can delete cannot carry our containment |
| The paths were baked for startup cost or determinism | HYPOTHESIS | ⛔ **D0. The reason decides whether D1 is a win or a trade** |
| The existence-only invariant is now test-enforced by a population-derived test | HYPOTHESIS | that test file — ⛔ **read it before D2 touches the write path** |
| The structural fix eliminates the class rather than moving it | HYPOTHESIS | the path-resolution site after D1 — ⛔ **a runtime resolver that still consults markers has moved the problem** |
| Nothing outside our tree depends on us writing the shared marker | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half, and **partly unknowable** — the other producer is third-party. **State the limit rather than asserting the absence** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D6(a) is the test that proves the structural fix.** An executor surviving the deletion of its
  generation-time version is the whole point; without it, D1 is a refactor with no demonstrated benefit.
- ⛔ **D6(c), the loud-failure control, is what stops D1 from becoming a silent fallback.** A resolver
  that always finds *something* is worse than one that fails, because it will find the wrong thing.
- ⛔ **D2's interaction with the enforcement test must be stated explicitly in the report** — retired,
  re-scoped, or untouched, with the reason. Silently deleting a test to make a change pass is the move
  this epic exists to catch.
- **D5's corrections must remove the claim, not soften it.** "Saturation is unlikely" is still a
  guarantee a reader will trust.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐⭐ **A lesson recorded against the author of this plan's own sequencing, and worth carrying:** an
  earlier attempt declared this plan disjoint from a sibling because their *subjects* differed —
  path-baking versus marker encoding — **without reading the sibling's FILE LIST.** Three of four files
  were identical. ⛔ **"Same component, different function" is NOT a disjointness argument. Disjointness
  is a FILE-level test. Read the surface, not the title.**
- ⚠ **That sibling has since landed and rewrote two of this plan's four files.** ⛔ **Re-ground before
  scoping** — the tree moved underneath this spec.
- ⛔ **Do not go looking for the orchestrator spec, the live cache tree, the plugin registry, or any
  landing record.** The first and last live under `.plan/`; the others live on an operator's machine.
  None is reachable from this clone. **Everything checkable from source is named above.**
