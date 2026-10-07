> ⛔⛔⛔ **EMIT RETRACTED 2026-08-08, SAME SESSION — MY DISJOINTNESS CLAIM WAS WRONG.**
>
> I emitted this plan saying *"D0 and D1 are disjoint from `PLAN-TRUTH-049`; only D2 collides."*
> **That was a FUNCTION-level reading, and disjointness is a FILE-level test.** `PLAN-TRUTH-049`'s
> Expected Surface, read at retraction:
>
> ```
> script-shared/scripts/marketplace_bundles.py
> tools-script-executor/scripts/generate_executor.py
> marshall-steward/scripts/cache_retention.py
> manage-config/standards/data-model.md, tools-script-executor/SKILL.md
> ```
>
> **That is THREE of this plan's four files, identically** — and 049 is at phase 5-execute, actively
> editing them. D1 (runtime path resolution) lives in `generate_executor.py`; 049's marker work lives in
> `generate_executor.py`. Different functions, **same file, concurrent edits** — a rebase conflict does
> not care which function.
>
> ⇒ **This plan waits for `PLAN-TRUTH-049` IN FULL, not just at D2.** Status returned to `staged`.
>
> ⭐ **The lesson, recorded against myself**: *"same component, different function"* is not a
> disjointness argument. I checked the two plans' **subjects** (path-baking vs marker encoding) and
> called them disjoint without reading 049's **file list** — the one artifact that settles it. **Read the
> surface, not the title.** This is the standing rule *"surface a risk rather than assert a disjointness
> you cannot support"* firing against the exact person who wrote it into the ledger.

> ⛔⛔ **READ FIRST — EMITTED 2026-08-08 ON OPERATOR INSTRUCTION WHILE `PLAN-TRUTH-049` IS RUNNING.**
>
> The operator was told of the collision and chose to start now. **The collision is real but NARROW, and
> it is confined to ONE deliverable.** Verified at emit: `PLAN-TRUTH-049` is at **phase 5-execute** in
> worktree `two-producers-one-marker-field-two-encodings`, branch at `263f216d9` with **no commits of
> its own yet** — i.e. actively implementing.
>
> | Deliverable | Collides with 049? |
> |---|---|
> | **D0** (derive the chain) | ❌ read-only — start here |
> | **D1** (runtime path resolution) | ❌ different surface — `generate_executor` path-baking, not the marker |
> | **D2** (stop writing `.orphaned_at`) | ⛔⛔ **YES — DIRECT.** 049 owns the marker's ENCODING; this deletes the field |
> | D3 / D4 / D5 / D6 | ⚠ D4's retirement sweep may reach marker code — re-check after D2 is settled |
>
> **THE RULE FOR THIS RUN: start on D0 and D1 immediately; DO NOT LAND D2 until `PLAN-TRUTH-049` has
> landed or been re-scoped.** Landing D2 first would delete the field 049 is mid-way through fixing the
> encoding of; landing 049 first costs nothing — an encoding fix on a field that later disappears is
> wasted work, not broken work, and that is the cheaper failure direction.
>
> ⛔ **Do not resolve this by guessing at 049's scope.** If D1 finishes and D2 is blocked, **say so and
> stop** rather than working around it — *two plans, one field, opposite directions* is the `-006`/`-054`
> collision this ledger has already paid for once, and it was invisible from inside either spec.
>
> ⭐ **Corroborate 049's state yourself before touching D2** — this note is a snapshot taken at emit, and
> a plan state is a snapshot, never a status.

# PLAN-TRUTH-069: Collapse the version-selection machinery — most of it exists to serve a baked absolute path

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-08 from an operator question: *"all this orphaned / pin marker stuff seems overly
> complicated — can't we simplify?"* **The answer is yes, and the chain below is read from the code.**

## Objective

Four of the seven links in the plugin-cache staleness chain are **ours**, and they exist only to manage
a problem two earlier links create. Nothing in the layout forces this: the cache is versioned because
Claude Code's layout is versioned, but the *selector*, the *pollution detector*, the `.orphaned_at`
*marker* and the *retention pins* are all our own machinery, each added to contain the previous one.
This plan removes the reason they exist rather than adding an eighth link to guard the seventh.

## The chain, and who owns each link — OBSERVED, read at HEAD

| # | Link | Owner |
|---|------|-------|
| 1 | Plugin cache is laid out `{base}/{bundle}/{version}/skills/` | **Claude Code** — inherited, not changeable |
| 2 | Each sync creates a NEW version dir and **never deletes** | **ours** |
| 3 | `generate_executor` **bakes absolute, version-pinned paths** into `.plan/execute-script.py` | **ours** |
| 4 | `_detect_multi_version_pollution` — needed because 2 + 3 put several versions on `PYTHONPATH` | **ours** |
| 5 | `.orphaned_at` marker — exists to **silence 4** on the next preflight | **ours** |
| 6 | `_retention_pinned_versions` — exists to stop **5 saturating** | **ours** |
| 7 | Claude Code's GC **also reads `.orphaned_at`**, in epoch-ms, while we write ISO-8601 | **shared field, two producers** |

⇒ **Links 4–6 are pure containment for 2 + 3.** Link 7 is us writing a field a third party parses with
different semantics — that is `PLAN-TRUTH-049`, and it exists only because we chose someone else's
filename.

## ⛔⛔ The invariant that was supposed to make this safe is REFUTED BY OBSERVATION

`_retention_pinned_versions`'s docstring states, twice, that pinning makes marker saturation
**"structurally impossible"** — *"the dir the resolver selects is pinned unconditionally, so at least
one live version dir always survives per bundle."*

**Measured first-party 2026-08-08 after PR #1122's sync: `unmarked == []`.** All 11 version dirs
orphan-marked, including the registry pin and the executor's own version.

⭐ **The reason the guarantee fails is circular and visible in the code**: the disk arm of the pin is
`select_live_version_dir(...)`, which selects **among live (unmarked) dirs**. Once saturation is
reached by any route, that arm returns nothing and **cannot recover** — the guard against reaching the
state depends on not already being in it. The two remaining arms are `marshal.json`'s
`provisioned_version` (recorded in this ledger as **lagging the executor by three versions**) and the
installed manifest version, neither of which tracks the dir the resolver actually wants.

⚠ **The system survives it**: `marketplace_bundles.find_bundles` has a documented **degraded
all-orphaned fallback** that returns the newest dir on disk and warns. ⇒ We are running in the degraded
path, by design, with a warning nobody is reading. **That is the honest status — not "broken", and not
"fine".**

## Deliverables

1. **D0 — GATE (mutates nothing): confirm the chain and the ownership column above by symbol**, and
   derive every consumer of a baked executor path and of `.orphaned_at`. ⛔ **Both directions**: what
   reads the marker, and what would break if it stopped existing.
2. **D1 — LEVER A (the structural one): stop baking absolute version paths into the executor.**
   Resolve bundle script dirs **at executor runtime** from a single selector, instead of freezing them
   at generation time. ⭐ **This is the root fix**: an executor that resolves at run time cannot be
   pinned to a collected directory, so the executor-vs-pin split becomes unrepresentable rather than
   detectable. ⚠ Measure the startup cost this adds — if it is material, that is the trade to state,
   and it is the reason the paths were baked in the first place (confirm that reason at D0).
3. **D2 — LEVER C (the cheap one, independent of D1): stop writing `.orphaned_at`.** It is Claude
   Code's field. If a marker is still needed after D1, use a namespaced one we own (e.g.
   `.pm-superseded`). ⛔ **This retires `PLAN-TRUTH-049`'s entire two-producers-one-field defect by
   not sharing the field** — a rename is a smaller change than reconciling two encodings forever.
4. **D3 — LEVER B (evaluate, do not assume): keep ONE version dir.** Delete-on-sync rather than
   accumulate-and-mark. ⚠ **This is the risky lever and the reason deletion was deferred to markers in
   the first place** — a superseded dir may still be on a running process's `PYTHONPATH`. **Evaluate
   against D1's outcome**: if the executor resolves at runtime, the exposure changes. **Recording the
   decision either way is the deliverable; adopting it is not required.**
5. **D4 — retire what the levers make dead.** Whichever of `_detect_multi_version_pollution`,
   `_mark_superseded_version_dirs`, `_retention_pinned_versions` and the degraded fallback are no
   longer reachable get **deleted, not left as dormant code**. ⭐ *Where a copy exists, delete the copy*
   — the standing rule applies to superseded machinery too.
6. **D5 — the saturation claim is corrected wherever it is stated.** The "structurally impossible"
   docstrings are wrong and were wrong when written. ⛔ **A refuted guarantee in a docstring is worse
   than no guarantee**, because the next reader trusts it — this epic's own thesis.
7. **D6 — tests, each verified to FAIL pre-fix.** (a) An executor generated against version X still
   resolves after X is deleted. (b) A saturated cache (`unmarked == []`) resolves without the degraded
   fallback. (c) A matched negative control: a genuinely broken cache still fails loudly. (d) No
   `.orphaned_at` write remains under our tree.

Seven deliverables — under the raised cap of 12.

## Claim Labels

- **OBSERVED** — the seven-link chain and its ownership column, read at
  `generate_executor.py` (`_mark_superseded_version_dirs`, `_retention_pinned_versions`,
  `_detect_multi_version_pollution`), `script-shared/scripts/marketplace_bundles.py` (the ONE place the
  marker is read; the degraded fallback), and `.plan/execute-script.py` itself (absolute
  version-pinned paths, `MARSHALL_VERSION`).
- **OBSERVED** — `unmarked == []` measured first-party 2026-08-08 after #1122's sync, against a
  docstring asserting saturation is structurally impossible.
- **OBSERVED** — the pin's disk arm is `select_live_version_dir`, which filters to live dirs, making
  the anti-saturation guarantee self-referential.
- **HYPOTHESIS** — the paths were baked for startup cost or determinism. **Confirm at D0**; the reason
  decides whether D1 is a straight win or a trade.
- **HYPOTHESIS** — D1 + D2 make `PLAN-TRUTH-049` and most of `PLAN-TRUTH-059` unnecessary rather than
  merely easier. ⛔ **Do NOT retire either on this spec's say-so** — 049 is RUNNING and owns the
  encoding question; see Sequencing.
- **Verify-first clause**: re-derive the ownership column at D0. If any of links 4–6 turns out to be
  required by Claude Code rather than by us, the plan re-scopes to the links that are genuinely ours.

## Expected Surface

- **OBSERVED**: `tools-script-executor/scripts/generate_executor.py` — the three functions above, and
  the path-baking site
- **OBSERVED**: `script-shared/scripts/marketplace_bundles.py` — the sole marker read + fallback
- **OBSERVED**: `marshall-steward/scripts/cache_retention.py` — the sweep's keep-union
- **HYPOTHESIS**: `plugin-doctor/scripts/_doctor_shared.py` — one marker reference (verify-at-outline)
- ⛔ **NEVER** `~/.claude/plugins/installed_plugins.json` — the plugin manager's file. Read only.

## Dependencies and Sequencing

- ⛔⛔ **`PLAN-TRUTH-049` IS RUNNING and owns the marker ENCODING.** This plan proposes removing the
  shared field entirely, which would make that question moot. **Do not emit this plan while 049 is in
  flight** — tell 049 first, and let it settle whether the encoding must be fixed for the field's
  remaining lifetime. **Two plans, one field, opposite directions is the `-006`/`-054` collision
  shape**, and this ledger has already paid for that once.
- ⚠ **`PLAN-TRUTH-059`** owns the *detector*. If D1 lands, much of what 059 detects becomes
  unrepresentable. ⛔ **059 is NOT superseded by this** — a detector for a state that can no longer
  occur is dead code, but the four-conjunct oracle also covers **pin-vs-source content staleness**,
  which D1 does not address. **Re-scope 059 after this lands; do not pre-emptively retire it.**
- **Adjacent**: `PLAN-TRUTH-005` (marshalld self-reload) reads the same cache tree.

---

## ✅ UNBLOCKED 2026-08-09 — PLAN-TRUTH-049 SHIPPED AS #1125. RE-GROUND BEFORE OUTLINE.

The sequencing block above is **discharged**: 049 landed as `cf70cf787`, and it settled the encoding
question in the direction that *helps* this plan — **outcome (i), our ISO markers age out normally, so
the inverted "write epoch-ms to match the owning consumer" remedy is REFUTED, not deferred.** There is
no longer a live proposal to fix the encoding, so removing the field is no longer an opposite-direction
collision.

⛔ **BUT RE-GROUND FIRST — 049 REWROTE TWO OF THIS PLAN'S FOUR FILES.** `cf70cf787` touches
`marketplace_bundles.py` (+42) and `generate_executor.py` (+54), and it did something that changes this
plan's D-lever C materially: **the existence-only invariant is now STATED AND TEST-ENFORCED**
(`test_orphan_marker_existence_only.py`, +1027, population-derived). Lever C ("stop writing
`.orphaned_at`, a field we don't own") must now reckon with a live enforcement test rather than an
undocumented convention — **removing the write may require retiring or re-scoping that test, and doing
so silently would be exactly the "delete the guard to make the change pass" move this epic files
against.** Name it as a deliverable or state why it is untouched.

## ⭐⭐ NEW EVIDENCE FOR LEVER A, OBSERVED LIVE AT THE 049 LANDING — THE FIELD HAS A THIRD-PARTY WRITER **AND** DELETER

The spec's re-grounding once flagged a "marked → re-marked → **UNMARKED**" third state the aging model
does not contain, and asked for it to be settled. **It is now settled, with a timestamp.** Measured
first-party, double-sampled:

- `0.1.1331` marked at **08-09 09:39:03.967** with **`1786261143967`** — raw epoch-ms, the foreign
  encoding.
- `0.1.1327`'s marker **DELETED** at **08-09 09:39:03.901** — 66 ms earlier, same operation.

⇒ **The foreign producer re-anchors the entire marker set on the registry `installPath` on its own
schedule, adding and removing markers as it goes.**

**This is the strongest argument yet for lever A (resolve at executor RUNTIME).** The case no longer
rests on "the split is untidy":

1. **We do not own the field's lifecycle, only its writes.** A value we write can be deleted by a third
   party at an instant we neither choose nor observe. Any containment built on it is built on a
   variable someone else assigns.
2. **The marker set is not an independent signal.** It is a lagging function of the registry — so the
   "sole unmarked dir" oracle counts the registry as two witnesses. Lever A makes the whole question
   unrepresentable; no oracle is needed for a state that cannot occur.
3. **It also bounds 049's own conclusion.** D-1's matched control ("no differential within the
   observable window") is confounded a second way the run did not name: **the window is truncated by
   marker RESETS, not only by our sweep's pruning.** 049's verdict stands — but the fact that its
   central measurement is degraded by a third party's writes is itself the argument for not depending
   on the field.

⚠ **Label discipline**: items 1–3 are **OBSERVED** (the two timestamps, the encodings, the registry
agreement). The claim that lever A *eliminates* the class is **HYPOTHESIS** — confirm/refute against
`tools-script-executor/scripts/generate_executor.py`, symbol `_mark_superseded_version_dirs`, and the
executor template's path-resolution site; a runtime resolver that still consults the marker set has
moved the problem, not removed it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-069-collapse-the-version-selection-machinery.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. ⛔ It writes NOTHING
under `~/.claude/plugins/` — the registry is the plugin manager's file.
