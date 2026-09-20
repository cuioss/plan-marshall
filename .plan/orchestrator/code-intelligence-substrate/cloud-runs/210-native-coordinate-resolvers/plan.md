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

# Python and npm projects get a structurally empty dependency graph

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

Edge derivation joins dependencies on **Maven coordinates**. Neither the Python nor the npm build
discoverer produces them: the Python discoverer emits a project name, a version, a description and a
Python requirement, and emits dependencies as compact name-plus-scope strings; the npm discoverer
likewise extracts dependency names with no coordinate pair. **The join key can therefore never
match**, so the internal-dependency set stays empty for every Python and npm project.

⛔ **This is not a self-hosting curiosity.** Every Python and npm consumer project running this
tooling gets its graph, path, neighbours and impact verbs **structurally vacuous** — and a
feasibility guard that reasons over graph output **dead** — while every verb reports success.

## Goal

A multi-module Python project and a multi-package npm workspace both yield **non-empty** graph edges
and non-empty impact results, derived from the coordinate systems those ecosystems actually use, and
a consumer can read what dependency intelligence they get without configuring anything.

## Deliverables

1. **D0 — GATE: verify the consumer-facing claim against a real consumer project. Mutates nothing.**
   The mechanism has been read in both discoverers, but the graph verb has **not** been run against a
   real Python or npm consumer repository.
   *Done when:* the edge count from at least one real non-Maven project is recorded, **or** the run
   reports it could not reach one.
   ⛔ **Do not scope the consumer-facing claim until one real project has been measured.** If none is
   reachable, say so and scope from the mechanism alone — **do not state a consumer-wide claim the
   run could not check.**
2. **D1 — GATE: verify Gradle explicitly.** It emits group-and-artifact coordinates and **may already
   work.**
   ⛔ **If Gradle works it is a second reference implementation, not a third defect — do not "fix" a
   working path.**
   *Done when:* Gradle's dependency extraction is read and classified as working or not.
3. **D2 — a Python resolver** deriving internal edges from project names rather than Maven
   coordinates, registered against the existing resolver seam.
   *Done when:* a multi-module Python fixture yields non-empty edges through the seam.
4. **D3 — an npm resolver** deriving internal edges from package names, **including workspace
   members**.
   *Done when:* a multi-package workspace fixture yields non-empty edges.
5. **D4 — tests** proving both ecosystems yield non-empty graph edges **and** non-empty impact.
   ⛔ **Impact separately from edges**: edges present with impact still empty is a live failure mode
   and the assertion must be able to catch it.
6. **D5 — documentation.** Register the native resolvers alongside the build-system extension
   implementations in the extension-architecture concepts page.
   ⭐ **The user-facing page matters most for this plan**: this is the consumer-facing half of the
   epic, so a Python or npm consumer must be able to read what they now get **without configuring
   anything**. ⛔ Ship docs **in this plan**.

Six deliverables with two gates — at the split guard; evaluate before implementing. The natural cut
is (D0+D1+D2: Python end-to-end) then (D3+D4+D5: npm and documentation).

## Out of scope

- **Changing the Maven derivation path.** Excluded: it works, and this plan adds peers beside it
  rather than reworking it.
- **A new extension point.** Excluded — the resolver seam exists and these are implementors of it. If
  the plan finds itself extending the seam, that is a co-design signal; stop and record it.
- **Fixing Gradle.** ⛔ Excluded **unless D1 shows it is broken.** An unverified assumption that it
  patterns with Python and npm would produce a change to a working path.
- **Configuring which resolvers run.** Excluded — a sibling plan owns the binding surface.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py` —
  metadata and dependency extraction. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py` — dependency
  extraction. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_discover.py` —
  **verify-only; may need no change.** **HYPOTHESIS.**
- `doc/concepts/extension-architecture.adoc` and `doc/user/` — documentation. **OBSERVED.**
- `test/plan-marshall/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Edge derivation joins on a Maven-style coordinate pair | **OBSERVED (mechanism)** | The query module's dependency-splitting and the artifact-to-module map it joins against. **Read both in the clone** — this is the plan's founding premise. |
| The Python discoverer emits no coordinate pair, and its dependencies are name-plus-scope strings | **OBSERVED** | The Python discoverer in the clone. Read it. |
| The npm discoverer likewise emits no coordinate pair | **OBSERVED** | The npm discoverer in the clone. |
| The same failure applies to **every** Python and npm consumer project | **HYPOTHESIS (a derived claim)** | ⛔ **D0.** The mechanism was read; the graph verb was **not** run against a real consumer repository. **Measure one before asserting the consumer-wide claim.** |
| Gradle may or may not be affected | **HYPOTHESIS** | ⛔ **D1, and this is an ASSERTED ABSENCE** — "no non-Maven build system derives internal edges" carries the higher verification burden. **Verify Gradle explicitly rather than assuming it patterns with the other two.** |
| Line numbers cited for any of the above | **LEADS** | Re-derive; they move. |

## Verification

- **D2 and D3 are verified by impact, not only by edge count.** A resolver that produces edges the
  traversal cannot use has not met the goal. Assert both.
- **D1's outcome is verified either way and recorded.** "Gradle already works" is a valuable result
  and must appear in the run report; silently skipping it leaves the absence claim unverified.
- **D0's honesty**: if no real consumer project is reachable from this environment, the report says
  so and the consumer-wide claim is stated as unverified. ⛔ An unmeasured consumer claim presented as
  measured is exactly the defect class this epic exists to remove.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Dependency.** The resolver seam must exist; it has shipped. Confirm in the clone.
- **Disjointness.** This plan touches the build-system bundles and is disjoint from the
  marketplace-dependency resolver and from the configuration plan — **the epic's best natural
  pairing.** ⚠ Check whether any sibling plan is editing build-system discovery before starting.
