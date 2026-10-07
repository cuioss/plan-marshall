# PLAN-TRUTH-071: The multi-target generator's edge paths — an unguarded rmtree, a non-pruning emitter, and a fence parser that stops early

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from `doc/review-26-07-04.md`, which is being retired. **Every finding below was
> re-verified at HEAD at staging time** — the review is 5 weeks old and 8 of its findings had already
> been fixed; these had not.

## Objective

`marketplace/targets/` emits the distribution output for every assistant target. Six defects in its
error and edge paths survive re-verification: a `shutil.rmtree` with no containment guard, an emitter
that never prunes so output drifts past source, a frontmatter parser that ends a block on the first
`---` substring, an unguarded `json.loads` that crashes the equality CLI, a path-keyed cache blind to
content change, and a diff layer that can double-count one root cause. **One component, one PR.**

## Deliverables

1. **D0 — GATE (mutates nothing): confirm all six at HEAD by symbol**, and derive whether the two
   emitters have any other asymmetries beyond G1/G2. ⛔ **Both directions** — the review found these by
   comparing Claude against OpenCode; sweep for the reverse asymmetry too.
2. **[G1] Guard the Claude emitter's `rmtree` — *High*.** `emit_bundle_verbatim` does
   `if dest_root.exists(): shutil.rmtree(dest_root)` with **no check that `dest_root` is inside the
   resolved `--output` dir**. ✅ Re-verified at HEAD: bare `shutil.rmtree`, **no `_safe_rmtree`** in the
   Claude emitter, while OpenCode has exactly that helper. ⇒ A mistyped `--output` pointing at (a tree
   containing) `marketplace/bundles` **destroys real source**. Reuse/share OpenCode's `_safe_rmtree`.
   ⚠ The emitter's docstring argues the wipe is safe because `target/claude/` is gitignored — **true
   for the intended destination, and irrelevant to a mistyped one.** *A safety argument that assumes
   the input is correct is not a guard.*
3. **[G2] Make the OpenCode emitter prune — *Medium*.** ✅ Re-verified: `emit_bundles` contains **no
   `rmtree` and no prune** — it only `mkdir(exist_ok=True)` and rewrites in place, so a skill removed
   from source leaves its emitted directory behind and **output drifts past source**. The Claude
   emitter wipes first (which is why it needs G1's guard). Clear the relevant subtrees guarded, or
   track written paths and prune leftovers.
4. **[G4] Anchor the frontmatter closing fence — *Medium*.** `end = content.find('---', 3)` finds the
   fence by **raw substring**, so a value containing `---` (a horizontal rule, three hyphens as an
   em-dash) ends the block early and later fields are silently dropped. ✅ Re-verified at HEAD. The
   Claude `variant_emitter` already anchors on `\n---\n` — **match it.**
5. **[G5] Guard the per-bundle `plugin.json` read — *Medium*.** `_read_emitted_plugin_json` calls
   `json.loads` with **no error handling**; in validate mode a corrupt emitted file raises
   `JSONDecodeError` and **crashes the CLI instead of returning the documented "re-run emit"
   diagnostic**. ✅ Re-verified: still unguarded, while the `marketplace.json` path already is.
6. **[G6] Key the mapping cache on content, not path — *Low*.** `@lru_cache` on `_load_mapping` keys
   purely on the `Path`, so a modified `mapping.json` at the same path is not re-read. Key on
   `(path, st_mtime_ns)` or force `cache_clear()` at each generation entry point. ⭐ **This is the
   `stale-cache-as-evidence` archetype**, same shape as `PLAN-TRUTH-065`'s help-surface cache — cite it.
7. **[G7] De-duplicate the orphan-diff layers — *Low*.** `_diff_array` flags `on_disk - declared`
   while the manifest-drift layer above reports the same root cause, producing two overlapping
   `BundleDiff` entries and **an inflated failure count**. ⭐ On-theme: a count that overstates the
   number of distinct problems is a truthfulness defect, not a cosmetic one.
8. **D8 — tests, each verified to FAIL pre-fix**, including a **matched negative control** for G1
   (an `--output` inside the tree is refused; a legitimate one still wipes).

Eight deliverables — under the raised cap of 12.

## Claim Labels

- **OBSERVED, re-verified at HEAD 2026-08-09**: G1 (bare `rmtree`, no `_safe_rmtree` in the Claude
  emitter), G2 (`emit_bundles` has no prune), G4 (`find('---', 3)`), G5 (unguarded `json.loads`),
  G6 (`lru_cache` present), G7 (`_diff_array` present).
- **HYPOTHESIS**: G7's double-count is reachable in practice — the review reasoned it from the code
  rather than observing it. **Confirm by constructing the out-of-sync state** (verify-at-outline);
  if unreachable, drop D7 rather than "fixing" a path that cannot occur.
- ⚠ **Line numbers in the source review are 5 weeks stale — verify by symbol, never by line.**
- **Verify-first clause**: re-confirm each finding at D0. Eight of the source review's findings were
  already fixed by the time this plan was staged; assume more may be by the time it runs.

## Expected Surface

- **OBSERVED**: `marketplace/targets/claude/emitter.py`, `.../claude/equality_check.py`,
  `.../claude/variant_emitter.py`, `.../opencode/emitter.py`, `.../opencode/frontmatter.py`
- ⛔ NOT `marketplace/bundles/**` — this plan changes the emitters, never the source of truth.

## Dependencies and Sequencing

- Depends on: none. **Disjoint from every currently-running plan** (`manage-logging`/`manage-providers`,
  the plugin cache tree, `manage-metrics`).
- ⚠ Adjacent to `PLAN-TRUTH-065` (plugin-doctor's path-keyed cache): **G6 is the same archetype at a
  second site.** Whichever lands second cites the first rather than re-deriving the rule.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-071-multi-target-generator-edge-paths.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.


---

## ⛔⛔ RE-SCOPE REQUIRED BEFORE EMISSION — THE `lstrip` DELIVERABLE ALREADY SHIPPED (2026-08-09)

`PLAN-TRUTH-070` landed as **#1132** (`ff4462148`) and **carried the `opencode/emitter.py` overlap
rather than handing it off.** Its D4 retired the `lstrip('./')` prefix-strip idiom **marketplace-wide**,
and its D5 added a **population-derived source-tree guard** (`test/marketplace/test_prefix_strip_idiom_retired.py`,
409 files scanned) that **fails the build if the idiom is re-introduced.**

⇒ **This plan's `lstrip` deliverable is satisfied.** Emitting it unchanged would either no-op or re-do
settled work, and any attempt to "fix" the class again now trips a guard.

⭐⭐ **And the population this plan inherited was wrong in the same way -070's spec was.** -070's spec
asserted `plugin_discover.py`'s sites *"are now gone"*; the population-derived sweep found **9 sites
across 3 files, not 3 across 2** — `_cmd_manage.py`, `plugin_discover.py` (**not** clean), and
`opencode/emitter.py`. ⛔ **Do not re-count this plan's remaining deliverables from its own prose** —
re-derive against `ff4462148` and against the D5 guard's scan, which is now the authoritative population
for this idiom.

**Before emitting, D0 must:** (a) confirm which of this plan's deliverables survive `ff4462148`;
(b) delete the satisfied ones rather than restating them; (c) if nothing survives, **say so and
supersede this spec** — a plan kept alive for a shipped deliverable is a duplicate with a slower fuse.


## ✅ VERIFIED SATISFIED 2026-08-09 — the `lstrip('./')` deliverable is CLOSED, by measurement

A repo-wide sweep for `lstrip('./')` across **all of `marketplace/`** returns **ZERO occurrences.**
#1132's D5 guard (`test/marketplace/test_prefix_strip_idiom_retired.py`, 409 files scanned) now fails
the build on re-introduction.

⇒ **Delete this deliverable at D0 rather than restating it.** ⛔ Do not "verify" it again by inspection —
the guard is the verification, and re-adding a check duplicates it.

⚠ **This spec's REMAINING deliverables are NOT closed by that** — it is the multi-target generator's
edge paths, of which the idiom was one. **Re-count at outline against `ff4462148`**, and if the
remainder is empty, **supersede this spec rather than shipping a no-op.**
