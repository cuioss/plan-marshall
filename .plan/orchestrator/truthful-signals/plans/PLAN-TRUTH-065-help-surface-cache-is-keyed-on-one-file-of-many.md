# PLAN-TRUTH-065: The plugin-doctor help-surface cache is keyed on one file of many

epic: truthful-signals
workstream: WS-01

> Staged plan spec — ready for `/plan-marshall` hand-off. Delegated in by `review-apparatus`
> (`review-apparatus-018` § 3) under the three-way routing rule: a quality-gate correctness
> defect, not a PR/review one.

## Objective

`_analyze_manage_invocation.py` derives each script's `--help` surface once and caches it
under `sha256(entry_script_bytes)`. For any script whose argparse surface lives in a sibling
module, that key cannot change when the surface changes. The canonical case is
`plan-marshall:tools-integration-ci:ci`, whose entry point declares no parser at all. The
gate therefore validates documentation against a surface that may be arbitrarily out of date,
in **both** directions — and the false-green direction is silent. This plan keys the cache on
the whole script directory so the gate's verdict tracks the surface it claims to check.

## Deliverables

1. Key the cached surface on the sorted `(relpath, sha256)` pairs of every `.py` in the
   script's own `scripts/` directory, so a sibling-module change invalidates the entry.
2. Add a matched control pair to the tests: a surface change in a **sibling** module must
   invalidate (today it does not), and an unrelated change outside the directory must not.
3. Make the gate's report name the cache state it acted on (hit/miss and the key inputs), so a
   `clean` verdict is distinguishable from a verdict computed off a stale entry.

Three deliverables — well under the split guard.

## Claim Labels

- OBSERVED: the key is a single file's bytes — read at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py`
  § `_content_hash` (`script_path.read_bytes()` → one `sha256`) and § `_cache_path`
  (`f'{safe}.v{_CACHE_VERSION}.{content_hash}.json'`).
- OBSERVED: `_CACHE_VERSION = 2` guards derivation-logic drift only, not dependency drift —
  same file, § `_CACHE_VERSION`. It cannot substitute for the fix.
- OBSERVED: the canonical broken case is real — `tools-integration-ci/scripts/ci.py` contains
  **zero** `add_argument` / `build_parser` occurrences and only `from ci_base import (…)`;
  the entire parser surface is in `ci_base.py`. Verified by symbol at this drain.
- OBSERVED (second-hand, from `review-apparatus-018`, NOT re-derived here): PR #1087 added
  `--pr-number` in `ci_base.py`, `sha256(ci.py)` did not change, and the run produced exactly
  one **false RED** while `finalize-step-plugin-doctor` reported `clean: 4 skills gated`.
  Re-derive before pinning a test to that specific PR.
- HYPOTHESIS: the false-GREEN direction (a doc using a **removed** flag validating clean) is
  reachable on the same mechanism and has never been observed — confirm/refute by constructing
  it in the D2 control pair (verify-at-outline). **It is the half nobody would notice**, so an
  unreproduced false-green is not evidence of its absence.
- Verify-first clause: re-read `_content_hash` / `_cache_path` against HEAD before scoping — if
  the key already folds in sibling modules, the premise is refuted and the plan re-scopes to
  D3 alone.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py`
  — `_content_hash`, `_cache_path`, `_read_cache`, `_write_cache`, `_derive_tree_uncached`
- HYPOTHESIS: the plugin-doctor test module covering invocation analysis (verify-at-outline)
- ⛔ NOT `tools-integration-ci/**` — `ci.py` / `ci_base.py` are the *evidence*, not the fix site.

## FOLDED IN — `merge-queue-enqueue-does-not-take-004`

Same gate, adjacent failure mode, folded here rather than staged separately: the
`direct-gh-glab-usage` rule **scores 100% false positives on the CI abstraction layer it
audits** — it flags the very module that exists to be the sanctioned `gh`/`glab` chokepoint.
⭐ Both defects make plugin-doctor report a problem that is not one; D3's cache-state
disclosure and this rule's self-exemption are the same obligation — *a gate must be able to
say what it examined and why a hit is a hit*. Re-derive the false-positive count at outline;
the `100%` is the filer's figure and carries its own population.

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none running. Adjacent to `PLAN-TRUTH-012` (canonical block vs argparse
  choices) — **same gate, opposite direction**: -012 is about the doc diverging from the
  parser, this is about the gate's *view* of the parser being stale. Whichever lands second
  cites the first rather than re-deriving.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-065-help-surface-cache-is-keyed-on-one-file-of-many.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.


---

## ⭐ FOLDED FROM THE 2026-08-09 (EVENING) DRAIN + ⛔ RE-GROUND REQUIRED

**`runtime-008` (candidate-lesson).** *`wrapper-tangle-scan` should **publish the population it
scanned**.* ⇒ Same component, same standing rule this epic applies everywhere: **a check that can return
0 from an empty population MUST publish the population size.** Folds here.

⛔⛔ **AND THIS SPEC MUST RE-GROUND BEFORE IT IS EMITTED.** Its OBSERVED fix site is
`_analyze_manage_invocation.py`, and **#1127 (`415dcf139`) rewrote that file by −831 lines.** The
`_content_hash` / `_cache_path` / `_read_cache` / `_write_cache` / `_derive_tree_uncached` cache defect
this spec targets **may no longer exist**. ⭐ D0 must confirm the defect is still present at HEAD before
scoping anything — and **"it is gone" is a legitimate outcome that supersedes this spec**, not a
failure.


---

## ⛔⛔ SUPERSEDED 2026-08-09 — ALL THREE OF THIS SPEC'S SURFACES ARE GONE OR WERE NEVER HERE

Verified first-party at the full-corpus review, by symbol, and **not** concluded from a single scoped
grep (a scoped zero is a *could not look*):

| Surface | Result |
|---|---|
| the cache mechanism — `_content_hash`, `_cache_path`, `_read_cache`, `_write_cache`, `_derive_tree_uncached` | **ZERO hits** in `_analyze_manage_invocation.py`. The file still exists; **#1127 (`415dcf139`) rewrote it by −831 lines and removed the caching entirely.** ⇒ the defect this spec targets **no longer exists** |
| the folded `merge-queue-…-004` item — `direct-gh-glab-usage` false positives | **not a plugin-doctor rule at all.** It lives in `plan-retrospective` (`scripts/direct-gh-glab-usage.py`, `references/direct-gh-glab-usage.md`) |
| the folded `runtime-008` item — `wrapper-tangle-scan` population | likewise **`plan-retrospective`**, not plugin-doctor |

⇒ **Nothing remains that belongs to this spec.** Superseded into `PLAN-TRUTH-045`, which owns
`plan-retrospective`.

⚠ **AND THE SECOND ROW IS A CORRECTION AGAINST MYSELF.** I folded `runtime-008` into THIS spec earlier
tonight on a component guess — *"wrapper-tangle-scan … same component"* — without checking where the
scan lives. **It was the wrong receiver for four hours.** ⭐ The fold survived the drain's own dedup
discipline because dedup checks whether a *target already holds the signal*, never whether the *target
is the right one*. **A fold needs its receiver verified, not just deduped** — recorded for
`PLAN-TRUTH-074`'s D4.
