# Run report — 310-main-sha-records-the-pinned-cwd (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/main-sha-pinned-cwd-0p9af9` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Every skill was obtained by reading its bundle `SKILL.md` path — the route that always works in a
fresh clone. The `Skill: {bundle}:{skill}` plugin notation was not attempted. No skill was
unobtainable by either route.

- `plan-marshall:ref-code-quality` (always).
- `pm-plugin-development:plugin-script-architecture` (always).
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

`pm-documents:ref-asciidoc` was **not** loaded: the two documentation surfaces the change touches are
Markdown references inside bundles, not `.adoc`. The one `.adoc` file that mentions these columns
(`doc/concepts/branches-and-worktrees.adoc`) was read during the beyond-diff sweep and needed no edit.

## Deliverables

### D1 — GATE: the two populations, derived from source

**Population A — fields that claim to describe main: 3, out of a 15-entry registry.**

The registry is `_invariants.INVARIANTS` — the single field registry; there is no second one. Each
field's actual tree was read from its `capture_fn`, not from its name.

| Field | `capture_fn` | Tree read **pre-fix** | Tree read **post-fix** |
|---|---|---|---|
| `main_sha` | `_capture_main_sha` | `_repo_root()` → cwd-derived → **the worktree** at phase-5+ | `_main_repo_root()` → main |
| `main_dirty` | `_capture_main_dirty` | same | same |
| `main_dirty_files` | `_capture_main_dirty_files` | same | same |

**The asserted absence, verified rather than assumed** — the other 12 entries, and why none is
mis-resolved:

- `worktree_sha`, `worktree_dirty` — read from `metadata['worktree_path']`. Correct, and the names
  claim the worktree, not main.
- `references_valid`, `task_state_hash`, `qgate_open_count`, `config_hash`,
  `unfinished_tasks_count`, `phase_steps_complete`, `task_graph_valid`, `pending_findings_by_type`,
  `pending_findings_blocking_count`, `pr_title_present` — plan-state captures. Cwd-relative **by
  ADR-002 design** (the plan state is moved into the worktree at phase-5 start, so cwd-relative is
  the correct resolution), and none claims main.

`config_hash` deserves a named verdict because the predecessor plan
(`truthful-signals/290-…`) explicitly deferred its "whole-checkout stability" here. **Verdict: not a
member of this population.** Its name makes no main claim, and its cwd-relative `marshal.json` read
is the ADR-002 rule rather than a mislabel. Redirecting it to main would be a behaviour change this
plan neither scopes nor justifies. Left unchanged, recorded here so the hand-off is not silently
dropped.

**A second `main_sha` namespace exists and is NOT affected.** `status.metadata.main_sha` /
`worktree_sha`, written by phase-5-execute's zero-overlap self-absorption branch
(`phase-5-execute/SKILL.md`, `standards/sync-with-main.md`), are metadata keys, not handshake
columns. They are read by an explicit `git -C {worktree_path} rev-parse origin/{base_branch}` and
mean "the upstream tip being absorbed" — a different quantity, correctly resolved. Enumerated here
because a name-based sweep finds them and a reader could mistake them for members.

**Population B — callers of the root-resolution helper: 4, all in `_invariants.py`.**

| Caller | Contract it needs | Inherits the mis-resolution? |
|---|---|---|
| `_capture_main_sha` | the MAIN checkout | **yes** |
| `_capture_main_dirty` | the MAIN checkout | **yes** |
| `_capture_main_dirty_files` | the MAIN checkout | **yes** |
| `_run_script` | the CURRENT checkout | **no** |

⛔ **The plan's HYPOTHESIS "every consumer of that resolver inherits the mis-resolution" is REFUTED:
3 of 4 do.** `_run_script` resolves `{root}/.plan/execute-script.py` and sets the subprocess cwd, and
it must reach the **worktree-resident** executor and plan state moved in at phase-5 start — the
contract `file_ops.get_executor_path` documents. It has 10 call sites of its own, feeding 7 registry
captures. **Redirecting the shared resolver to main would therefore have broken those 7 captures**,
which is precisely why D1 exists as a gate rather than going straight to a one-line change. The fix
splits the resolver by contract instead of redirecting it.

**Sibling-pattern sweep.** The defect's shape — infer the root from the base directory's parent
chain, fall back to `Path.cwd()` — occurs **exactly once** across `marketplace/`, at the resolver
under repair. No second copy to fix.

*Done: both populations enumerated from source and published with their counts.*

### D2 — the resolution is fixed, not the call site

Commit `ad47a67`.

- `_repo_root` → **`_current_repo_root`**, semantics unchanged, docstring rewritten to state that
  following the pinned worktree is its *purpose* and that a `main_*` column must not use it. The
  rename is the point: one name serving two contracts is what produced the bug.
- **`_main_repo_root`** (new) resolves main-anchored: base-dir override first (so every
  `PLAN_BASE_DIR` consumer test keeps its meaning), then `git rev-parse --git-common-dir`, which
  names main's `.git` even from a linked worktree. Mirrors
  `marketplace_paths.resolve_main_anchored_path`, the single sanctioned main-anchored exception.
- Returns **`None`**, never a cwd fallback, when main is unresolvable — the column is left empty
  under the registry's existing "not applicable" contract. A cwd fallback is the mis-resolution being
  removed; reinstating it as an error path would have shipped the defect under a different name.
- `marketplace_paths.base_dir_override_active()` (new public predicate) replaces the
  `os.environ.get('PLAN_BASE_DIR') or _override_is_set()` disjunction at its two existing sites, so
  the new resolver asks the one sanctioned question instead of adding a third private-attribute copy
  of it.

*Done when: asserted **directly on the resolver** —
`test_main_repo_root_resolves_to_main_from_pinned_worktree_cwd` builds a real repo and a real linked
worktree, pins cwd into the worktree, and asserts the resolver returns main.
`test_current_repo_root_still_follows_pinned_worktree_cwd` asserts the other half, so the split is
pinned in both directions.*

### D3 — the impossible state is refused at capture time

`WorktreeShaEqualsMainSha`, raised by `capture_all` via `_assert_main_differs_from_worktree` and
surfaced by `cmd_capture` as `error: worktree_sha_equals_main_sha` **without writing a row**.

- **Fires** when both `main_sha` and `worktree_sha` were captured and are equal. Both present is
  exactly "worktree-backed with a resolvable worktree", since `worktree_sha` is gated on
  `_worktree_in_use`.
- **One-sided by construction.** A plan genuinely on main captures no `worktree_sha`, so the refusal
  is unreachable there and cannot block an on-main run.
- **`same_tree`** carries the diagnosis, derived from the two *resolved paths* rather than from the
  equal values: `true` = the main-scoped resolution regressed to the worktree (the capture bug);
  `false` = two distinct trees genuinely hold one commit.
- Also handled in `cmd_verify`. Without that handler the exception would escape a live re-capture as
  an unhandled traceback — `cmd_verify` catches only two of the three pre-existing capture
  exceptions, so the gap was real. Added to `VERIFY_REFUSAL_ERRORS` and to `phase_handshake`'s
  strict non-zero exit list, so a boundary re-capture that reproduces it refuses and is never
  auto-resolved by the loop-back marker.

*Done when: verified in both directions —
`test_capture_all_refuses_equal_shas_on_a_worktree_backed_plan` and
`test_capture_all_permits_equal_shas_for_a_plan_running_on_main`, plus one test per `same_tree`
value and one asserting no row is persisted.*

### D4 — the already-written rows are quarantined, and the count is BLOCKED

**Two separate numbers, as the plan requires:**

| Number | Value |
|---|---|
| Handshake corpora **examined** | **0** |
| Records **affected** | **BLOCKED — not measurable from this clone** |

**Reachability, established empirically rather than assumed.** `.plan/` in this clone holds only
`marshal.json` and `project-architecture` — no `local/`, so no plan directories. A tree-wide search
for `handshakes.toon` returns **zero** files; the only `.toon` fixtures present are synthetic
retrospective test fixtures, not real records. The corpus is machine-local and git-ignored exactly as
the plan predicted, so no search for it was mounted beyond confirming its absence. No corpus rewrite
was in scope either way.

**The documented rule shipped** in `plan-retrospective/references/invariant-check-summary.md`, beside
the existing `main_sha`-drift severity rule that is the interpretation site. It states that a
`main_sha` drift entry whose `to_phase` is `5-execute` is a **known capture artifact** on a pre-fix
worktree-backed plan, never evidence that main moved and never a finding — and that drift at any
*other* boundary of the same plan is unaffected, because the planning rows ran with cwd on main.

Two properties make the rule usable without the corpus:

- **Self-identifying.** An affected row is recognisable from the row alone: `main_sha == worktree_sha`
  means the two columns describe one tree, which is only possible under the pre-fix resolution. No
  fix date, no plan metadata, no archived reference is needed.
- **Not open-ended.** A post-fix row cannot carry the artifact, because such a row is now refused at
  capture time (D3). A drift entry at that boundary on a post-fix row is a real signal.

Interpretive only — stored rows are not rewritten.

### D5 — tests, each verified to fail against the defect it names

Two new modules (split at 400 lines by behaviour cluster per the pytest module budget):
`test/plan-marshall/plan-marshall/test_invariants_main_resolution.py` (9 tests) and
`test_invariants_worktree_sha_refusal.py` (6 tests). 15 total.

⛔ **A guard is not a guard until it has been seen to fail.** Each was mutation-tested against the
specific defect it names, not against a plausible neighbour:

| Mutation applied to shipped code | Red | Green |
|---|---|---|
| `_main_repo_root` → `return _current_repo_root()` (the exact defect reinstated) | **5** | 10 |
| `_assert_main_differs_from_worktree` call removed from `capture_all` | **4** | 2 |
| refusal's worktree gate dropped (made two-sided) | **1** | 5 |
| `worktree_sha_equals_main_sha` removed from `VERIFY_REFUSAL_ERRORS` | **1** | 5 |

Every one of the 15 is covered by at least one mutation above, so none is a second copy of the
implementation wearing a test's name. The four mutations were applied to the *shipped* code and
reverted; the tree at HEAD carries none of them.

The plan's three named cases:

- **(a)** `test_capture_main_sha_records_main_head_not_the_pinned_worktree_head` — real repo + real
  linked worktree carrying its own commit, cwd pinned to the worktree: `main_sha` equals main's HEAD,
  `worktree_sha` equals the worktree's, and the two differ. Red under mutation 1.
  `test_capture_main_dirty_reads_main_not_the_pinned_worktree` dirties **only** the worktree, so a
  non-zero `main_dirty` could only mean the wrong tree was read — settling the plan's
  companion-dirty-flag hypothesis by execution.
- **(b)** the four refusal-direction tests above.
- **(c)** `test_summariser_sees_no_main_sha_drift_across_the_execute_boundary` — the rows are built
  by the **real capture** at both boundaries (cwd on main for the `4-plan` row, pinned to the
  worktree for the `5-execute` row) and then fed to the summariser's `detect_drift`. Hand-feeding
  rows would have passed pre- and post-fix alike; deriving them makes the test discriminating. Under
  mutation 1 it reproduces the reported symptom verbatim:
  `main_sha, 4-plan → 5-execute, 0250cddd… -> fccd486f…`.

**This is also how the plan's un-reachable OBSERVED claims were settled.** The records are
machine-local, and the plan directed that the resolver's behaviour under a pinned directory be
reproduced instead. It was: mutation 1 produces the false drift entry in-clone, from a real
worktree, with no reference to any archived corpus.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **7 Python files** (5 production, 2 test),
so the gate applies.

`UV_HTTP_TIMEOUT=600 ./pw verify` — **clean**: `20661 passed, 14 skipped in 344.86s`, and every gate
dimension reported complete (mypy production 412 files, ruff, SPDX, plugin-doctor marketplace-wide,
mypy test 768 files, whole-tree pytest). Read from the streamed tool output, not the exit code: the
`./pw` path emits no structured log. `=== verify: SUCCESS ===`.

No lockfile churn reached the commit — `git status` was checked for stray generated files before
staging, and the deliverable paths were staged by name rather than with `git add -A`.

## Findings

_(Verification rounds recorded below as they run.)_

## Reviewer participation

_(Recorded after the PR is opened.)_

## Cost

_(Recorded at close.)_

## Contract check (Step 9)

_(Recorded at close.)_

## What have we learned (Step 9)

_(Recorded at close.)_

## Residue

_(Recorded at close.)_
