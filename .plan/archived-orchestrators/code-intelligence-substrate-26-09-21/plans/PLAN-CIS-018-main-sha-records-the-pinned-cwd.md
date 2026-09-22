# PLAN-CIS-018: `main_sha` records the pinned cwd, so every worktree plan emits a false drift warning

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-30 from the PLAN-11 landing (#1063), inbox message
> `audit-report-path-ignores-plan-dir-008`.

## Objective

The phase-handshake invariant record captures `main_sha` by reading HEAD of the *current* tree. Under
ADR-002 the cwd is pinned to the plan's worktree from phase 5 onward, so from that boundary on the
field named `main_sha` silently holds a **feature-branch** commit. `summarize-invariants` then reports
`main_sha drift` at the 4-plan→5-execute boundary of **every worktree-backed plan**, while main did not
move. Capture `main_sha` / `main_dirty` against the main checkout explicitly, and make the
self-contradictory state fail loud instead of persisting.

## Why this is ours

This is MEASUREMENT of our own runs — a cross-phase drift *detector* whose input is mislabelled at
capture. It is not a PR/review surface (routing test 1 does not fire) and it changes how the system
counts, so routing test 2 keeps it here.

## The self-contradiction is structural, not statistical

⭐ **The row disproves itself without any external reference.** `handshakes.toon` for
`audit-report-path-ignores-plan-dir` records at the `5-execute` boundary:

```text
main_sha     = 2475cd1794a8443d3ff01c85bf908898b4d3175f
worktree_sha = 2475cd1794a8443d3ff01c85bf908898b4d3175f
main_dirty   = 0
```

A row where `main_sha == worktree_sha`, while `worktree_sha` exists as a separate column, is
definitionally wrong unless the plan runs on main — and this plan's `use_worktree` is `true`. **The
evidence needed to detect the bug is already inside the record**; nothing consumes it.

## ⛔⛔ RE-GROUNDED 2026-08-09 — THE MECHANISM IS REFUTED, THE SYMPTOM IS CONFIRMED. READ BEFORE SCOPING.

**The symptom is CONFIRMED LIVE, on a plan that ran 2026-08-09** — second independent instance, and
it is not a historical artifact. `.plan/local/archived-plans/2026-08-09-self-review-resweeps-full-surface-every-round/handshakes.toon`,
`5-execute` row:

```text
main_sha     = a6657d8b07a81d0339bb793ad186d6789c2d6542
worktree_sha = a6657d8b07a81d0339bb793ad186d6789c2d6542
```

Identical, on a worktree-backed plan — the self-contradictory row this spec describes. ⭐ And rows
1–4 are correct (`263f216d9` ×3 = PR #1122 on main, then `775399cb2` = PR #1124 on main), which
**localises the defect to the phase-5 boundary exactly as the spec predicted.**

⛔⛔ **BUT THE STATED MECHANISM IS FALSE AT HEAD, AND D2 MUST BE RE-SCOPED.** This spec's load-bearing
HYPOTHESIS was *"the capture reads HEAD of the current tree with no explicit tree argument."*
**Verified first-party — it does not:**

```python
# _invariants.py:437-438
def _capture_main_sha(_plan_id, _metadata, _phase):
    return git_head(_repo_root())          # ← EXPLICIT tree argument, already
```

⇒ **D2 as written ("read them via `git -C {main_checkout}`, never via the pinned cwd") is ALREADY
IMPLEMENTED and would be a no-op.** The defect has moved one layer down: `_repo_root()`
(`_invariants.py:253-263`) infers the main checkout from `get_base_dir()` by walking
`.plan/local → .plan → root`, **and that inference is what returns the worktree** when the cwd is
pinned there — or `PLAN_BASE_DIR` points at the worktree's own `.plan/local`.

⭐ **This is precisely the outcome this spec's own verify-first clause anticipated** — *"if capture
already takes an explicit path and resolves it wrongly, D2's remedy changes shape."* **It did, and
the clause paid for itself.** The plan gets SMALLER and MORE PRECISE:

- **D2 is re-scoped**: fix the **resolution** of `_repo_root()` / `get_base_dir()` under a pinned
  cwd, so a main-scoped capture resolves the main checkout rather than the worktree that shadows it.
  ⛔ **Do NOT add a second `git -C` argument at the capture site** — the argument is already there
  and correct; adding another would leave the real defect and ship a no-op with a green test.
- ⚠ **The blast radius is WIDER than this spec's field list, and that strengthens D1 rather than
  replacing it**: every consumer of `_repo_root()` inherits the mis-resolution, not just `main_sha`
  and `main_dirty`. **D1's population derivation must enumerate `_repo_root()`'s callers**, which is
  a mechanical and cheap query — and it is the honest form of the "a reported instance is a SAMPLE"
  rule this spec already invokes.
- ✅ **D3, D4 and D5 are unaffected** and remain exactly as written.

## Deliverables

1. **D1 — GATE (mutates nothing): derive the population of "main-scoped" captures.** Enumerate every
   field that claims to describe **main** and establish, per field, which tree it is actually read
   from. ⚠ **Population-derived, not the two fields this spec names.** `main_sha` and `main_dirty` were
   found by one run; the epic's standing rule 4 says a reported instance is a SAMPLE. The known
   sibling archetype — merge-lock staleness judged from a worktree-scoped store — is evidence the
   class has more than one member.
2. **D2 — capture main-scoped fields against the main checkout explicitly.** Read them via
   `git -C {main_checkout}`, never via the pinned cwd. The main-checkout path is resolvable
   independently of the worktree.
3. **D3 — fail loud on the impossible state.** Assert at capture time that `use_worktree == true`
   implies `main_sha != worktree_sha`. A violation is a **capture bug**, not a valid row: refuse to
   persist rather than writing a self-contradictory record.
4. **D4 — quarantine the already-written rows.** Existing `handshakes.toon` records across the
   archived corpus carry the mislabelled value, so every historical 4-plan→5-execute `main_sha` drift
   warning is a guaranteed false positive. ⚠ **Report the affected count SEPARATELY from the number of
   plans examined** — volume-read-as-coverage is a recorded recurring archetype here. No corpus
   rewrite is in scope; the deliverable is the honest assessment plus a documented rule that
   pre-fix drift warnings at that boundary are not actionable.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A worktree-backed plan's `5-execute` handshake
   records a `main_sha` that differs from its `worktree_sha`. (b) The capture-time assertion rejects a
   row where they are equal under `use_worktree: true`. (c) `summarize-invariants` emits no `main_sha`
   drift warning across a 4-plan→5-execute boundary on which main did not move.

Five deliverables — under the split guard, no split rationale owed.

## Claim Labels

- **OBSERVED** (orchestrator-verified, not message-supplied): `git branch -a --contains 2475cd179`
  returns exactly one ref, `remotes/origin/feature/audit-report-path-ignores-plan-dir`. The commit
  never reached main; PR #1063 was squash-merged as `d0da6742d`. The `main_sha` field therefore held a
  commit that provably was not on main.
- **OBSERVED** (first-party, plan artifacts): the `handshakes.toon` row above, and the
  `summarize-invariants` output `warning, main_sha, main_sha drift 4-plan -> 5-execute:
  d38b769... -> 2475cd179...`.
- **OBSERVED**: rows 1–4 of the same file are correct (`c259f5c` → `f8a3619` → `d38b769` → `d38b769`),
  which localizes the defect to the phase-5 cwd pin rather than to the capture logic in general.
- **HYPOTHESIS**: the mechanism is the ADR-002 cwd pin, i.e. the capture reads HEAD of the current tree
  with no explicit tree argument — confirm/refute at the handshake capture site, at the symbol that
  writes the `main_sha` column (verify-at-outline). **Load-bearing**: if capture already takes an
  explicit path and resolves it wrongly, D2's remedy changes shape.
- **HYPOTHESIS**: `main_dirty` is captured from the same tree as `main_sha` and is therefore also a
  worktree reading — confirm/refute at the same symbol (verify-at-outline).
- **HYPOTHESIS**: the defect fires on **every** worktree-backed plan rather than on this one —
  confirm/refute by checking the `handshakes.toon` of a second archived worktree plan
  (verify-at-outline). D4's blast-radius wording depends on it.
- **Verify-first clause**: settle the capture-site hypothesis against the *implementing source* — the
  code that writes the column — before scoping D2/D3. A standards doc describing the intended
  semantics restates the same inference and does not confirm it.

## Expected Surface

- HYPOTHESIS: the phase-handshake capture site — the writer of `handshakes.toon` `main_sha` /
  `main_dirty` (verify-at-outline; locate via `architecture find` before scoping)
- HYPOTHESIS: `summarize-invariants` — the drift-warning consumer (verify-at-outline)
- OBSERVED: the plan-artifact schema doc for `handshakes.toon`, wherever the column contract is stated

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none currently staged. ⚠ Re-check against PLAN-CIS-015
  (`outline-plan-scope-derivation-integrity`) at emit time — both may touch phase-boundary records.
- Adjacent to: PLAN-CIS-012 (`footprint-read-outside-its-window`) — the same *polarity* of defect (a
  reading taken from the wrong tree / the wrong moment) but a **different seam and a different file**;
  it stays untouched here. ⛔ Do not merge the two: PLAN-CIS-012 is already at its split guard.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-018-main-sha-records-the-pinned-cwd.md"
```

## Relation to the corpus

Same polarity as the standing rule *"never judge a merge lock stale from a worktree-scoped store —
query the MAIN checkout; an empty worktree-scoped read is UNKNOWN"*. This is that rule violated at a
different seam: not an empty read misinterpreted, but a **worktree read mislabelled as a main read**,
with a correctly-named sibling column sitting next to it proving the mislabel.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
