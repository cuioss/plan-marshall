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

# The multi-target generator's edge paths — an unguarded rmtree, a non-pruning emitter, and a fence parser that stops early

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`marketplace/targets/` emits the distribution output for every assistant target. Six defects survive in
its error and edge paths — **one component, one PR**:

- **An unguarded destructive wipe.** One emitter does `if dest_root.exists(): shutil.rmtree(dest_root)`
  with **no check that the destination is inside the resolved output directory** — while the sibling
  emitter has exactly such a helper. ⇒ **A mistyped output path pointing at a tree containing the bundle
  source destroys real source.**
  ⚠ Its docstring argues the wipe is safe because the intended destination is gitignored — **true for
  the intended destination, and irrelevant to a mistyped one.** ⭐ ***A safety argument that assumes the
  input is correct is not a guard.***
- **An emitter that never prunes.** The other emitter only creates directories and rewrites in place, so
  **a skill removed from source leaves its emitted directory behind and output drifts past source.**
- **A frontmatter parser that ends a block on the first `---` substring.** It finds the closing fence by
  raw substring, so **a value containing three hyphens ends the block early and later fields are
  silently dropped.** A sibling emitter already anchors on a newline-delimited fence — **match it.**
- **An unguarded JSON read** that crashes the equality CLI instead of returning the documented "re-run
  emit" diagnostic — while the adjacent read path is already guarded.
- **A path-keyed cache blind to content change.** A memoised loader keys purely on the path, so a
  modified mapping at the same path is **not re-read**. ⭐ **This is the stale-cache-as-evidence
  archetype.**
- **A diff layer that can double-count one root cause**, producing overlapping entries and **an inflated
  failure count**. ⭐ **On-theme: a count that overstates the number of distinct problems is a
  truthfulness defect, not a cosmetic one.**

## ⛔⛔ One deliverable this plan inherited is ALREADY CLOSED — do not restate it

An earlier scoping carried a deliverable to retire a path-prefix-stripping idiom. **That shipped
elsewhere**, marketplace-wide, **with a population-derived guard that fails the build on
re-introduction.** A repo-wide sweep returns **zero occurrences**.

⇒ ⛔ **Delete it at D0 rather than restating it. Do not "verify" it again by inspection — the guard IS
the verification, and re-adding a check duplicates it.**

⭐⭐ **And the population that plan inherited was wrong in the same way its own spec was**: the spec
asserted certain sites were already clean; **the population-derived sweep found three times as many
sites across more files than claimed.** ⛔ **Do not re-count this plan's remaining deliverables from its
own prose** — re-derive against the tree.

## Goal

The generator's error and edge paths behave as their own documentation claims: a destructive operation
is contained, emitted output cannot drift past source, a parser cannot silently truncate, a corrupt
input produces a diagnostic rather than a crash, a cache notices content changes, and a failure count
counts distinct failures.

## Deliverables

1. **D0 — GATE: confirm every finding at HEAD by symbol, and re-count.** Mutates nothing.
   *Done when:* each finding is confirmed or refuted **by symbol**, and the surviving deliverable set is
   stated.
   ⛔ **The already-closed deliverable is DELETED here, not restated.**
   ⛔ **If the remainder is EMPTY, say so and recommend superseding this plan** rather than shipping a
   no-op. ⭐ **A plan kept alive for a shipped deliverable is a duplicate with a slower fuse.**
   ⚠ **Assume more may have been fixed since.** A prior pass over the same source review found **eight of
   its findings already fixed** — this is a review whose findings decay.
   ⛔ **Sweep both directions.** These were found by comparing one emitter against the other; **sweep for
   the reverse asymmetry too** — the emitter with the guard may lack something the other has.
2. **D1 — Guard the destructive wipe.** Refuse a destination that is not inside the resolved output
   directory. **Reuse or share the sibling emitter's existing helper** rather than writing a second one.
   *Done when:* an output path inside the source tree is refused.
   ⛔ **Also correct the docstring's safety argument** — leaving it in place preserves the reasoning that
   produced the gap.
3. **D2 — Make the non-pruning emitter prune.** Clear the relevant subtrees **guarded**, or track written
   paths and prune leftovers.
   *Done when:* a skill removed from source leaves no emitted directory behind.
   ⚠ **If pruning by wipe, it needs D1's guard too** — do not solve one emitter's drift by giving it the
   other's hazard.
4. **D3 — Anchor the frontmatter closing fence.** Match the sibling's newline-delimited anchor.
   *Done when:* a value containing three hyphens no longer truncates the block.
5. **D4 — Guard the JSON read.** A corrupt emitted file returns the **documented diagnostic**, not a
   traceback.
   *Done when:* the documented behaviour is what actually happens.
6. **D5 — Key the cache on content, not path.** Key on path plus modification time, or clear the cache
   at each generation entry point.
   *Done when:* a modified file at the same path is re-read.
   ⭐ **Same archetype as a path-keyed cache elsewhere in this project — cite it rather than re-deriving
   the rule.**
7. **D6 — De-duplicate the overlapping diff layers.**
   *Done when:* one root cause produces one entry.
   ⚠ **First confirm the double-count is REACHABLE in practice.** It was reasoned from the code, not
   observed. ⛔ **If unreachable, DROP this deliverable rather than "fixing" a path that cannot occur** —
   that would be a vacuous fix, which is this epic's own archetype.
8. **D7 — Tests, each verified to FAIL pre-fix**, including ⛔ **a matched negative control for the wipe
   guard**: an output path inside the tree is **refused**, and a legitimate one **still wipes**.
   *Done when:* all pass, each seen red first, with both halves of the control present.

Eight deliverables, under the raised cap — **minus whatever D0 deletes.**

## Out of scope

- ⛔ **`marketplace/bundles/**` — the source of truth.** This plan changes the **emitters**, never what
  they read. An emitter bug fixed by editing source is not a fix.
- **The already-closed prefix-strip idiom.** See above. ⛔ **Restating it would either no-op or re-do
  settled work, and any attempt to "fix" the class again now trips a guard.**
- **Adding a second containment helper.** ⭐ One exists in a sibling emitter. **Reuse or share it** —
  two implementations of one safety check is how they drift apart.

## Expected surface

- `marketplace/targets/claude/emitter.py` — the unguarded wipe.
- `marketplace/targets/claude/equality_check.py` — the unguarded JSON read.
- `marketplace/targets/claude/variant_emitter.py` — the correct fence anchor to match.
- `marketplace/targets/opencode/emitter.py` — the non-pruning emitter and the existing containment
  helper.
- `marketplace/targets/opencode/frontmatter.py` — the substring fence.
- The mapping loader's cache and the diff layer.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| One emitter calls `rmtree` with no containment check, while the other has a safe helper | HYPOTHESIS | both emitters, **by symbol** — ⛔ **the highest-severity finding, and fully checkable from this clone** |
| The other emitter has no prune path at all | HYPOTHESIS | that emitter, **by symbol** — an asserted **absence**, verified as a presence |
| The frontmatter parser finds its closing fence by raw substring | HYPOTHESIS | that parser, **by symbol**, and the sibling that anchors correctly |
| The JSON read is unguarded while the adjacent one is guarded | HYPOTHESIS | both read paths — ⭐ **the asymmetry is the evidence** |
| The mapping loader is memoised on path alone | HYPOTHESIS | that loader, **by symbol** |
| The diff double-count is REACHABLE in practice | HYPOTHESIS | ⛔ **reasoned from the code, NOT observed. Confirm by constructing the out-of-sync state** — and **drop the deliverable if it cannot occur** |
| The prefix-strip idiom returns zero occurrences and is guarded | HYPOTHESIS | a repo-wide sweep, plus the guard test — ⭐ **confirm once at D0 to justify deleting the deliverable, then stop** |
| No other asymmetry exists between the two emitters | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — **D0's reverse sweep owns it** |

⚠ **Every line number this plan might have inherited is weeks stale — verify by SYMBOL, never by line.**
An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D7's matched control for the wipe guard is the most important test here.** A guard that refuses
  everything would satisfy the negative half and break every legitimate generation. **Both halves, or the
  guard is unverified.**
- ⛔ **D6 must be dropped rather than implemented if the state is unreachable**, and the report must say
  which happened. Fixing an unreachable path is indistinguishable from fixing nothing, except that it
  adds code.
- **D0's refutations belong in the report with their evidence.** A finding that has since been fixed is a
  successful outcome; silently omitting it makes the next reader re-file it.
- **D5's fix must be verified by modifying a file in place** and confirming the re-read — not by
  inspecting the cache key.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐ **The source review these findings came from is weeks old and decays fast** — a prior pass found
  eight of its findings already fixed. **That is why D0 is a gate and not a formality**, and why every
  location is expressed as a symbol.
- ⛔ **Do not go looking for the orchestrator spec, the retired review document, or any landing record.**
  The first and last live under `.plan/`; the review is being retired and its surviving findings are
  transcribed in full above. Everything needed is in this file.
