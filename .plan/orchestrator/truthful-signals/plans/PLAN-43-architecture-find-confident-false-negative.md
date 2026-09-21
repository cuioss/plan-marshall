# PLAN-43: `architecture find` Returns Confident False Negatives Past the Elision Horizon

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced 2026-07-22 by the operator with a full root-cause trace, then
> **re-verified at ground truth by the orchestrator** (`main` @ `dfc4ac15c`) before staging — the
> mechanism, the caller-side swallow, and the known-but-unsurfaced blind spot all confirmed.
> **Migrated from plan-optimization 2026-07-22** (successor epic; plan id kept).
>
> **Not staleness, not missing files.** Both `enriched.json` inventories were regenerated within
> two days. The defect is a **hard cap in the inventory builder** that the reader consumes silently.

## Objective

`architecture find --pattern P` returns `status: success, count: 0` for files that **exist and are
tracked**, whenever the matching path sorts past the elision horizon of an over-cap category. The
zero is indistinguishable from a genuine "no such file," and because **"Structured queries first" is
a hard rule**, agents trust it and stop looking. Two independent leaves in one run each concluded a
file "doesn't exist" and burned a recovery cycle. Make the primitive incapable of emitting a
confident negative it cannot stand behind.

## ⚠ Mechanism — verified at `dfc4ac15c`

1. `manage-architecture/scripts/_cmd_manage.py` — `_FILES_CATEGORY_CAP = 500` (:53),
   `_FILES_ELISION_SAMPLE_SIZE = 100` (:54). `_apply_category_cap()` (:348) replaces any
   per-category file list over 500 with `{'elided': <true count>, 'sample': paths[:100]}`.
2. `_cmd_client_handlers.py` — `_flatten_inventory()` (:503-517) yields, for an elided category,
   **only `value['sample']`** (:515-516).
3. `cmd_find()` (:654-694) `fnmatch`-matches against that flattened stream and returns
   `count/results` with **no `elided`/`truncated`/`samples_only` field** (:688-694). The
   elided/sample distinction never reaches the caller.
4. Sample is `paths[:100]` on a **byte-sorted** list, so the blind spot is **contiguous and
   alphabetical**, not distributed — the worst selection for lookup.

**Blast radius (verified):** `test/plan-marshall/` tracks **696** files vs the 500 cap; `find` over
it returns **exactly 100** rows (the sample size, not a coincidence). The horizon lands mid-`build-server`:
`build-*`/`audit-*`/`automatic-review` visible; `execute-task`, `manage-*`, `phase-*`, `extension-api`,
`script-shared`, `integration` — **71 of 80 subdirectories — invisible**. Probes:
`find --pattern "test/plan-marshall/build-pyproject/*"` → 11; `"test/plan-marshall/manage-status/*"` → 0;
`"*test_markers_search*"` → 0 while `git ls-files` shows 26 files there.

**Doc-contract-divergence:** `cmd_which_module()` (:579) already *docstrings* the blind spot ("most
`test/**` files never appear as an exact hit") — the code knows; the contract to the agent does not.

## Deliverables

### D1 — GATE: choose the truthful-negative shape (design, mutates nothing)

The invariant: **a lookup primitive backing a hard rule must never emit a confident negative it
cannot stand behind.** Two fix shapes reconcile with that; D1 picks one against named artifacts:
- **(a) self-scan** — for a `--pattern` query, when any in-scope category is elided, `find` scans
  the real module tree (git-tracked walk) instead of the sample, so the answer is complete.
- **(b) truthful truncation** — `find` returns `truncated: true` + the elided category names + true
  counts whenever a matched-or-searched category was elided, so the caller knows the negative is
  unreliable and must fall back.
  Recommendation: (a) for pattern queries (the caller wants a *complete* answer, and a
  `find`-that-lies is worse than a `find`-that-scans); (b) as the minimum for any path that cannot
  self-scan. **These are not exclusive — (a) is the fix, (b) is the floor.** Whichever D1 picks,
  `which-module` must get the same treatment (same swallow, same hard-rule dependency).

### D2 — implement the chosen shape in `find` and `which-module`

Both readers consume `_flatten_inventory`'s sample-only stream. The fix lives at the reader boundary
(`_cmd_client_handlers.py`), not the builder — the elision shape in `enriched.json` is a legitimate
size guard; the bug is that the reader treats a sample as the whole. Preserve the fast path: only
elided categories in scope trigger the self-scan / truncation flag.

### D3 — palliative, not the fix: cap + sample selection

Fold in as defense-in-depth **only after D2 makes negatives truthful** — never as the resolution:
- raise/parameterize `_FILES_CATEGORY_CAP` so this repo's `test` category (696) is not silently
  clipped by a 500 that predates it;
- if a sample is still emitted anywhere, stop making it `paths[:100]` byte-sorted (a contiguous
  alphabetical hole) — a strided/distributed sample at least fails uniformly.
  ⚠ Guard against re-introducing the confident-zero: D3 must not let a raised cap or better sample
  substitute for D2's truthful negative. A cap only moves the horizon.

### D4 — regression test: an over-cap category cannot produce a silent zero

A fixture module whose `test` category exceeds the cap; assert `find --pattern` for a path **past**
the sample horizon either returns the hit (shape a) or `truncated: true` (shape b) — never
`success/count:0`. Pins the truthful-negative invariant, not the current cap value.

## Expected surface

- `manage-architecture/scripts/_cmd_client_handlers.py` — `cmd_find`, `cmd_which_module`,
  `_flatten_inventory` (reader boundary; the fix lives here)
- `manage-architecture/scripts/_cmd_manage.py` — `_FILES_CATEGORY_CAP` / sample selection (D3 only)
- one new test under `test/plan-marshall/manage-architecture/**` (D4)

**Disjointness:** `manage-architecture` surface — does NOT touch phase-1-init (PLAN-41), finalize
steps (PLAN-44), the CI/await seam (PLAN-42), or plan-optimization's running `_markers_search.py`
(PLAN-23) / `manage-execution-manifest.py` (PLAN-35). Emittable now.

## Notes

- Archetype: **confident-signal-hides-a-caveat** / silent-degradation — same family as the
  false-green routed-build status (exit-0-on-failure) and PLAN-42's invisible synchronous fallback:
  a tool reporting `success` while suppressing the qualifier that makes the answer wrong. Distinct
  from the vacuous-guards archetype (inert predicate) — here the predicate fires and the *result* is
  truncated in transit.
- The leaves' collateral misdiagnosis (`extension_base.py`/`query-config.py` reported missing)
  was partly this bug and partly leaf error — `extension_base.py` resolves fine. Only the test-file
  gap is a real tool defect; scope D2 to that, do not chase the misdiagnosed pair.
