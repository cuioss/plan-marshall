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

# The plugin pin trap — build the detector, and give it an oracle that can actually fail

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Three stores must agree about which plugin-cache version is live: the **cache directories** (with their
orphan markers), the **plugin registry**, and the **generated executor**. They routinely do not, and the
inversion has recurred **roughly daily across more than a dozen recorded incidents**.

> ⭐⭐ **The organising claim: the cache sync updates the CACHE and the EXECUTOR, and never the
> REGISTRY.** Every sync moves the cache forward and leaves the registry behind. **That is not drift; it
> is a producer that writes two of three stores.**

The consequence is not cosmetic. A stale read produced a retired flag, a current script rejected it with
exit 2, and **the pre-merge barrier turned that into "clean, 0 findings" in 33 seconds.** ⇒ **A pin gap
manufactures FALSE GREEN AT THE MERGE BOUNDARY.**

## ⛔ Scope — the fix is not ours; the DETECTION is

The registry is **the plugin manager's file.** ⛔ **Do not write it, and do not propose writing it** — a
third-party store with a second writer is a defect this epic has already shipped a plan against.

⇒ **What is ours: (a) noticing, (b) refusing to proceed silently, (c) telling the operator what to run.**

## ⛔ A pre-launch check is necessary and demonstrably NOT sufficient

Three incidents fired **inside one plan run** — one of them **self-observed at load, from inside its own
dispatch**, announcing a persona from a version dozens behind its own envelope, **with no loader
indication**. ⇒ **The failure is not in the pin at launch; it is in what the session's loaded registry
serves when asked, hours later.**

⚠ **And the arming path is routine.** The executor-regeneration preflight that runs on ordinary
invocations re-anchors the executor at a freshly generated directory, which a later sweep can
orphan-mark. ⭐ **One run's own cache-sync finalize step re-armed the very condition its report
described — the finalize that reports the condition is the finalize that creates it.**

## ⛔⛔ The oracle: six failure shapes, and every simpler formulation has already failed

Each of these was learned by a check being **wrong in production**, in one direction or the other:

| # | Shape | Why the obvious check misses it |
|---|---|---|
| 1 | `unmarked == []` | **An empty set reads as "nothing stale"** to anyone writing the obvious check. Observed twice. |
| 2 | Pin orphan-marked while a newer dir is unmarked | The pin points at a directory **scheduled for deletion**. |
| 3 | `unmarked == [stale, pin]` | A stale unmarked dir **beside a correct pin** — the configuration that seated a session dozens of versions backward. |
| 4 | `unmarked == [pin]` **and the pin is stale against source** | ⭐⭐ **The keep-set and the registry agree WITH EACH OTHER and say nothing about the REPOSITORY.** Measured: the pinned dir matched source on 352 of 360 files and **diverged on 8**, all of which matched an *orphan-marked* dir. |
| 5 | The registry's own two fields disagree | ⛔ **"The pin" is NOT ONE VALUE.** In one measurement `installPath` and `version` disagreed in **14 of 14** of our entries — while the single third-party entry in the same file **agreed**. ⭐ **That control is what makes it a finding rather than a format quirk.** |
| 6 | Divergence **without** GC exposure | Both load-bearing dirs unmarked but disagreeing. **Materially less urgent** than shape 1 — "repair when convenient" versus "repair before the fuse burns". |

⛔⛔ **And the sharpest correction of all: the unmarked set is NOT an independent witness.** Marker
timestamps caught the transition to the millisecond — the foreign garbage collector **deletes a marker
from the registry's `installPath` directory and marks every other**. ⇒ **The unmarked set is a LAGGING
FUNCTION OF THE REGISTRY.** An oracle asserting `executor == pin == sole unmarked dir` is not three
independent measurements; it is **two, plus a derived value the foreign collector periodically forces
into agreement with the registry.** ⭐ **It counts one witness twice.**

⇒ **Gate on `executor == installPath`, name the field, and use the unmarked set only to detect the
window between a sync and the next re-anchor.**

⛔⛔ **And a survey is a READ-DURING-WRITE.** One reading reported three unmarked dirs when two of them
**were** marked — their markers landed *seconds after* the sample. That false alarm **triggered
action**: an operator was told not to launch a plan, citing a trap that did not exist. ⭐ **The false
FAIL is the more dangerous direction, because it acts.**

## The saturation mechanism, stated precisely

Our marker pass **only ADDS markers; it never CLEARS them**, and it spares exactly one directory: the
current one. When the foreign collector has **already** marked the dir our pass would spare, the union
is the whole set. ⇒ **Saturation is reachable in ONE step**, and the documented *"structurally
impossible"* anti-saturation guarantee is refuted **constructively**, not just observationally.

⚠ **Markers are also re-written**, resetting a directory's apparent age to zero. ⇒ **An age-based oracle
over these markers measures time-since-last-sweep, not time-since-orphaning** — and a directory can be
re-marked indefinitely without ever aging out.

## Goal

A detector exists that can name every failure shape above, states which field it read, distinguishes
*could not look* from both *pass* and *fail*, reports its sampling instant, and tells the operator
exactly what to run — while writing nothing it does not own.

## Deliverables

1. **D0 — GATE: derive the three stores and who writes each, by symbol.** Mutates nothing.
   *Done when:* the writer of each store is established **from source**, and the organising claim — that
   the sync writes cache and executor and **never** the registry — is confirmed **by symbol at the sync
   entry point**.
   ⛔ **It has been asserted by two independent observers and by two search methods, and it is still an
   ABSENCE claim bounded by search coverage.** ⚠ **Two ledgers asserting one unverified claim is still
   ONE SOURCE.** *A corrective is a hypothesis until the named site is read.*
2. **D1 — A detector with the RIGHT oracle.**
   *Done when:* it rejects **all six shapes**, and every one of the following holds:
   - ⛔ **It gates on `executor == installPath`** for load safety, and **NAMES the field it read.** A
     detector that says *"the pin"* without naming the field is **unfalsifiable** — it will be right or
     wrong depending on an unstated choice.
   - ⛔ **It asserts `installPath == version` as a SEPARATE conjunct.** A registry disagreeing with
     *itself* is a distinct defect from a registry disagreeing with the cache.
   - ⛔ **It states that the unmarked set is REGISTRY-DERIVED, not independent**, and uses it only for
     the post-sync window.
   - ⛔ **It compares pin content against source**, reported as **"N of M files match; K diverge"** —
     **never as a boolean.** *"352 of 360 match"* is actionable; *"stale"* is not, and *"clean"* would
     have been wrong. It **degrades honestly**: a partial scan says so.
   - ⛔ **It double-samples** — read at least twice, seconds apart, and require agreement.
   - ⛔ **`indeterminate` is its own outcome**, distinct from both pass and fail. Collapsing it
     reproduces this epic's archetype from the opposite side.
   - ⛔ **It reports the sampling instant with the verdict**, and **publishes the population size and the
     newest marker's age** — so *"the sweep saturated"* is distinguishable from *"nothing has been marked
     yet"*, which are the same observation to any check that only counts unmarked directories.
   - ⛔ **It reports divergence and GC-exposure as SEPARATE axes**, so shape 6 does not rank alongside
     shape 1.
   ⛔ **Counting executor path-versions does NOT detect this** — every recorded incident had a **clean
   executor and a stale loader**.
   ⚠ **Do not swap one cheap heuristic for another.** A later-written cache directory was built from an
   *older* source state, so **version ordinal and directory mtime contradict each other** and only
   content-versus-source is right. **Either alone yields a confident wrong answer, in opposite
   directions.**
3. **D2 — A mid-run assertion, because pre-launch is provably insufficient.** A dispatched envelope must
   be able to establish that a loaded skill body came from the pinned version.
   *Done when:* it fails closed **and says which version it got**, rather than proceeding with a body
   from dozens of versions back.
   ⭐ **The loader announces its base directory — that string is the available evidence.**
4. **D3 — The operator-facing remedy is stated, not implied.** The detector reports **what to run**.
   *Done when:* the remedy text is explicit.
   ⚠ **A session restart does NOT fix it — reconfirmed repeatedly.** ⭐ **The working in-run remedy is to
   read the pinned skill file directly; state that too.**
5. **D4 — Settle the loader's behaviour under two unmarked directories.** The standing note is *"the
   loader follows the unmarked dir"* — **singular**. With two unmarked, **which does it follow?**
   *Done when:* the answer is established **from the loader's selection code**.
   ⛔ **D1 must not assume it resolves to the pin.**
6. **D5 — The executor's own reachability defects, which arm and hide this class.** Three defects in the
   generation path, each re-verified against a later HEAD than the review that found them:
   - **The generation fallback is unreachable on its most common failure.** The generator wraps discovery
     in `except Exception` to fall back to a glob, but discovery signals *"inventory not found"* via
     `sys.exit(2)` — a `SystemExit`, which is a `BaseException`, **not** an `Exception`. ⇒ **The glob
     fallback never runs for exactly the failure it exists to cover.** ⭐ **A vacuous fallback — an error
     path that cannot be reached — this epic's archetype in the executor itself.** A sibling command does
     catch it.
   - **The glob fallback drops any script whose name contains `test`** as a bare substring, which also
     matches legitimate entrypoints. **Match `test_` / `_test` precisely.**
     ⛔ **These two must land TOGETHER** — the discovery gap exists **only** in the fallback path, so it
     is invisible until the first is fixed, and **fixing the first alone activates a path that silently
     drops scripts.**
   - **Executor validation interpolates a filesystem path into `python3 -c` source.** A checkout path
     containing a quote or backslash breaks the generated program. **Pass the path via argv or the
     environment, never into the source string.**
   *Done when:* all three are fixed, with the ordering constraint honoured.
7. **D6 — Argparse rejections must name a misplaced router flag.** A top-level router flag consumed
   before dispatch is **rejected when placed after the verb**, with an *"unrecognised argument"* message
   that sends the caller looking for a flag that is right there.
   ⭐⭐ **One design produces two opposite errors: a false NEGATIVE when you search the argparse table for
   the flag, and a false REJECTION when you use it.**
   *Done when:* a rejection says *"this flag exists but belongs before the verb"*.
   ⛔ **The remedy is NOT to document the ordering.**
8. **D7 — Tests, each verified to FAIL pre-fix.** Fixture-driven, since the live state is not
   reproducible:
   - (a) Each of the six failure shapes is detected, **and shape 6 is classified distinctly from shape 1**.
   - (b) A healthy state passes.
   - (c) A dispatched load from a non-pinned version is reported.
   - (d) Two disagreeing samples yield **`indeterminate`**, not a verdict.
   - (e) ⛔ **The negative control: a tree where two consumers agree and the third does not.** A pairwise
     formulation must **fail** this.
   - (f) Discovery raising `SystemExit` **reaches the glob fallback**, and the fallback keeps a script
     named like `latest.py`.
   *Done when:* all six pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** eight deliverables against a raised cap of twelve.
The source spec, after absorbing two siblings, was counted at **twelve — at the cap, not over it** —
with its own instruction that overlapping deliverables **COLLAPSE rather than concatenate.** That
collapse is applied. ⛔ **Internal order is load-bearing: the content-comparison conjunct must land
before any corpus-normalisation step**, or the normalisation is validated by the stamp check it
replaces. ⭐⭐ **The absorbed stamp-versus-content defect is the same defect as D1's content conjunct
reached from the other side** — one measurement found a pinned directory diverging from source on 8 of
360 files **while every stamp-based check passed. A stamp is not a hash.** Neither plan could have
stated that alone.

## Out of scope

- ⛔⛔ **Writing the registry. DO NOT DO IT, AND DO NOT PROPOSE IT.** It is the plugin manager's file, and
  a third-party store with a second writer is precisely the defect class this epic has already filed.
- **Repairing the live machine.** ⛔ **Repair is operator-only.** The deliverable is a detector and a
  remedy statement.
- **An age-based staleness heuristic over the markers.** See the reset confound — it measures
  time-since-last-sweep, not time-since-orphaning.
- **The orphan-marker ENCODING defect.** A sibling plan owns the two-producers-two-encodings problem in
  the same tree. ⛔ **Do not fold: that is the marker's encoding; this is the registry's staleness.**
  ⭐ They read the same directories, so run them together if both are in flight.

## Expected surface

- `.claude/skills/sync-plugin-cache/**` — the sync script (meta-project-only surface).
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — the
  pin/selector logic, the generation fallback, the glob discovery, and the validation interpolation.
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — the natural home for the
  detector.
- The argparse error-emission path (D6).
- Tests, with **fixture trees** standing in for the live cache and registry.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The sync writes cache and executor and **never** the registry | HYPOTHESIS | ⛔ **the sync entry point, by symbol.** Corroborated by two observers and two searches; still an **absence** claim bounded by search coverage. **Confirm at D0 rather than inheriting it** |
| The generation fallback cannot catch `SystemExit`, and a sibling command can | HYPOTHESIS | both commands, **by symbol** — ⭐ **checkable entirely from source, and the strongest self-contained claim here** |
| The glob fallback drops names containing the bare substring `test` | HYPOTHESIS | that function, **by symbol** |
| Executor validation interpolates a path into `python3 -c` source at two sites | HYPOTHESIS | that function, **by symbol** |
| The six failure shapes, and every live measurement of the registry, cache, and executor | HYPOTHESIS | ⛔⛔ **NONE of this is reachable from this clone.** A cloud clone has **no plugin cache and no registry** — they live on an operator's machine. **Every measurement above is MOTIVATION for the detector's design, and the detector is tested against FIXTURES.** ⛔ Do not attempt to read `~/.claude/plugins/`; do not report its absence as a finding |
| The unmarked set is a lagging function of the registry, re-anchored by the foreign collector | HYPOTHESIS | ⛔ marker timestamps on a live machine — **not reachable here.** ⭐ **But its CONSEQUENCE is a design constraint that needs no measurement: an oracle must not treat a derived value as independent corroboration** |
| `installPath` and `version` are normally equal | HYPOTHESIS | ⭐ **the control is the load-bearing part**: one third-party entry in the same file agreed while ours disagreed. **14 of 15 disagreeing with the 1 that isn't ours agreeing** is what makes it drift rather than schema |
| The pinned directory diverged from source on 8 of 360 files | HYPOTHESIS | ⛔ **first-party to another observer, one machine, one instant, and NOT re-derived.** ⚠ **Use the 8 filenames as the SHAPE of the defect, never as an expected set** |
| The loader follows the unmarked directory when there are two | HYPOTHESIS | ⛔ **NOT ESTABLISHED — D4 owns it** |
| The GC has ever actually deleted a pinned directory here | HYPOTHESIS | ⛔ **NOT ESTABLISHED.** ⚠ **The trap being armed is not the trap having fired — do not report it as damage taken** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **STOP CONDITION, read this first: the live state is NOT observable from this clone.** There is no
  plugin cache and no registry here. **This run builds and tests the detector against fixtures.** If a
  deliverable cannot be verified without live state, **say so in the report** rather than fabricating an
  observation.
- ⛔ **D7(e), the negative control, is the most important test in the plan.** A tree where two consumers
  agree and the third does not **must fail**. Every pairwise oracle passes that tree — and one did, in
  production, certifying a three-way disagreement.
- ⛔ **D7(d) — disagreeing samples yielding `indeterminate`** — is the test that stops the false-fail
  direction, which is the one that triggers action.
- **D1's content comparison must be verified to report a count, not a boolean.** A boolean here is the
  defect: *"clean"* would have been wrong on a tree diverging on eight files.
- **D5's two coupled fixes must be verified together.** Fixing the unreachable fallback while leaving the
  substring bug activates a path that silently drops scripts — a strictly worse state than today.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **A fourth consumer no survey covers: the session's own seating.** It is fixed at session start and
  appears in **neither** the registry, the executor, nor the marker set. ⛔ **D1 must either measure it or
  state explicitly that it does not.** Independently reported twice.
- ⚠ **The health surface and the execution surface disagree, and only the health surface is reported** —
  every health signal named the pinned version while dispatched leaves ran a superseded one. ⭐ **A green
  health line is not evidence about what any leaf actually loaded.**
- ⚠ **A version number in a finalize report is stale by the time it is read** — observed three times.
  **That is why every reading in this plan carries its sample instant.**
- ⛔ **An upgrade command has gone green over an unrepaired split, and in one case actively worsened the
  marker state.** ⭐ **A repair is not a resolution**: the arming trigger is a routine preflight, so a
  repair holds only until the next regeneration — which happens in the ordinary course of the command.
- ⛔ **Do not go looking for the orchestrator spec, the absorbed specs, the retired review document, the
  drained messages, or any landing record.** They live under `.plan/`, which is git-ignored and absent
  from this clone. Everything needed is in this file.
