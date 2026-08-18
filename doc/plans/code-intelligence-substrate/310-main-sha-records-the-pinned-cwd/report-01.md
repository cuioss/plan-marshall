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

`MainCaptureReadTheWorktree`, raised by `capture_all` via `_assert_main_capture_read_main` and
surfaced by both `cmd_capture` and `cmd_verify` as `error: main_capture_read_the_worktree`
**without writing a row**.

⚠ **The trigger is narrower than the plan's literal wording, and the narrowing is the plan's own
verification clause applied.** The plan says to assert that a worktree-backed plan's main commit
*differs* from its worktree commit, and its ⭐ argues such a row "is definitionally wrong unless the
plan runs on main". **That is false for one reachable state**, found by round-1 verification and
reproduced against a real `git worktree add`: a worktree-backed plan whose feature branch carries no
commit of its own has both HEADs on the commit it branched from. `phase-5-execute` Step 2.5
materializes the worktree **unconditionally, before the `early_terminate` short-circuit**, so an
analysis-only plan reaches its phase-5 boundary in exactly that state. Refusing it hard-blocks the
boundary with no override escape and writes no `5-execute` row — which `invariant-check-summary.md`
then reads as "the phase did not complete its handshake". The plan's own Verification section forbids
precisely this failure shape ("A one-directional assertion would break legitimate on-main runs"), so
the refusal is keyed on the **cause** rather than the symptom:

- **Refuses** when `main_sha == worktree_sha` **and** `_main_repo_root()` resolves to the same
  directory as `worktree_path`. One tree under two names — the capture bug this plan is about.
- **Permits** an equal pair across two *distinct* trees. That row is correct: its `main_sha` genuinely
  is main's HEAD.
- **Never reached** for a plan with no persisted `worktree_path`, because `worktree_sha` is gated on
  `_worktree_in_use` and there is then nothing to compare.

⛔ **The gate is the persisted path, not `use_worktree`.** `_worktree_in_use` delegates to
`_worktree_materialized(metadata, None)`, which reads `worktree_path` and **never** reads
`use_worktree` — so `{'use_worktree': False, 'worktree_path': …}` *is* worktree-backed for this
family, and the refusal agrees with the predicate the sibling columns already use. The first draft of
this work described the refusal as "one-sided by construction: a plan genuinely running on main
captures no `worktree_sha`", which is a different and false claim; it is now stated as the predicate
actually is, and pinned by `test_the_gate_is_the_persisted_path_not_the_use_worktree_flag`.

The payload carries the two resolved paths (`main_root`, `worktree_path`) — the actionable diagnostic
— rather than the `same_tree` flag the first draft returned, which under the narrowed trigger is
always `true` and therefore carries no information.

**`cmd_verify` returns the same payload from a shared builder.** The first draft placed a handler
*after* the `capture_all` call, which round-1 verification proved was unreachable dead code:
`capture_all` runs the cross-field check itself, so the exception surfaced at that call and escaped
the verb entirely, rendering as `internal_error` through `file_ops.safe_main` — the opposite of what
the handler's own comment claimed, and with every verify-time behaviour the docs promised
undelivered. The catch now sits on the `capture_all` call. Added to `VERIFY_REFUSAL_ERRORS` and to
`phase_handshake`'s strict non-zero exit list, so such a boundary refuses and is never auto-resolved
by the loop-back marker.

*Done when: verified in both directions and at both verbs —
`test_refuses_when_both_columns_resolved_to_the_same_tree`,
`test_permits_equal_shas_when_the_two_trees_are_distinct`,
`test_permits_equal_shas_for_a_plan_with_no_worktree_path`,
`test_a_commit_less_feature_branch_is_captured_not_refused` (real repo, real worktree, no stub),
`test_cmd_capture_returns_structured_refusal_and_writes_no_row`,
`test_cmd_verify_returns_the_same_refusal_rather_than_raising`, and the strict-exit pair with its
negative control.*

### D4 — the already-written rows are quarantined, and the count is BLOCKED

**Two separate numbers, as the plan requires:**

| Number | Value |
|---|---|
| Plans **examined** | **0** |
| Records **affected** | **BLOCKED — not measurable from this clone** |

**Reachability, established empirically rather than assumed.** `.plan/local/` in this clone carries
no `plans/` directory, so there are no plan directories and no handshake rows to read. The corpus is
machine-local and git-ignored exactly as the plan predicted, so no search was mounted beyond
confirming its absence. No corpus rewrite was in scope either way.

⚠ **The "zero `handshakes.toon` in the tree" claim this report first made was withdrawn**, because it
was a tree claim that the run's own build gate invalidated: `./pw verify` writes hundreds of synthetic
`handshakes.toon` fixtures under `.plan/temp/pytest-basetemp/`. The claim was true when written and
false minutes later. The load-bearing fact is narrower and stable — **`.plan/local/` has no
`plans/`** — and that is what the BLOCKED verdict rests on. Recorded as an instance of the hazard,
not tidied away.

**The documented rule shipped** in `plan-retrospective/references/invariant-check-summary.md`, beside
the existing `main_sha`-drift severity rule that is the interpretation site. It took **four
corrections**, each from a verification round, and each reversed part of the last:

| Round | What it found | What changed |
|---|---|---|
| 1 (F10) | The rule asserted the artifact always appears at `4-plan → 5-execute` and that other boundaries are correct. `workflow/execution.md` re-anchors cwd and *then* **upserts** the `4-plan` row, so a cross-session re-entry moves it back a boundary. | Stopped keying on the boundary; keyed on the row |
| 2 (F13) | The row-level rule claimed the benign commit-less-branch case "emits no drift entry", so a drift entry beside the fingerprint proved the artifact. **Both halves false** — `main_sha` is main's HEAD *at each boundary*, and main moves when a sibling merges. | Added **branch containment** as the discriminator |
| 3 (F20) | Containment returns the **inverted** verdict at the moment the rule is read: this summary is a `post_run_review` step (`order: 995`) running after the merge gate, and the default PR merge strategy is a **merge commit**, which makes feature commits ancestors of main. | **Withdrew** containment; verdict became `unverifiable` |
| 4 (F31, F34, F37) | `unverifiable` was itself too weak — `captured_at` **is** a stored column, so the era is determinate. And the rule was **unactionable by its declared reader**: `summarize-invariants.py` emits invariant *names*, never per-row values, and strips `captured_at`. § Inputs also named two `status.metadata` keys that exist nowhere in the tree. | Rewrote as a two-step check against `handshakes.toon`, and corrected § Inputs |

**The shipped rule is now a procedure, not a verdict.** Step 1 reads the fingerprint (`main_sha ==
worktree_sha` on a row carrying both); Step 2 reads `captured_at` and compares it against when this
fix landed. `captured_at` is the discriminator that works, and it works *because* `capture` upserts —
the row is re-stamped when re-written, so the timestamp dates the write whose resolution semantics
produced the value, which is exactly the question. The rule names the three discriminators that fail
(the boundary, the fingerprint alone, containment) with the reason for each, and — because the check
needs two column values the summary output does not carry — instructs the reader to open
`handshakes.toon` directly.

⚠ **A code-level alternative was available and not taken:** `summarize-invariants.py` could surface
the fingerprint and `captured_at` in its own output, making the quarantine self-executing rather than
an instruction. It was not, because D4 asks for a documented rule and the plan's Out-of-scope list
bounds this work to assessing and documenting; changing the summariser's output contract is a
different deliverable. The choice is recorded here rather than left implicit.

⚠ **When the refusal actually fires, stated plainly because two earlier drafts got it wrong in opposite
directions.** In the **default** configuration it does not: `_main_repo_root()` resolves via
`git rev-parse --git-common-dir` while `worktree_path` is `<main>/.plan/local/worktrees/{plan}`
(`file_ops.get_worktree_root`), and no code calls `set_base_dir()` outside its own definition — so the
two cannot compare equal, and the refusal is reached only under a D2 regression or corrupt
`worktree_path` metadata. **But `PLAN_BASE_DIR` is a documented *user* override** (`file_ops.py`
"tests, user override"; `bootstrap_plugin` help text; the `manage-logging` env table), and with one
active the resolver follows the working directory and the refusal genuinely fires. So it is a live
guard for a real if unusual configuration, not dead code awaiting a regression — round 3 corrected the
previous draft's "unreachable in production" on exactly that point.

⛔ **And under that same override the refusal can MISS.** With an override active and the cwd in a
**subdirectory** of the worktree, `_main_repo_root()` returns that subdirectory, which is not equal to
`worktree_path` — so a mislabelled row persists un-refused. Round 3 demonstrated it by execution. This
is why the shipped D4 rule no longer says a post-fix row needs no check: it says a post-fix row is
sound *unless an override was in play*. The earlier draft's "a post-fix row cannot carry the artifact,
because such a row is now refused at capture time" was wrong twice over — such a row is permitted when
the trees are distinct, and can be mislabelled-and-permitted under an override.

### D5 — tests, each verified to fail against the defect it names

Two new modules (split at 400 lines by behaviour cluster per the pytest module budget):
`test/plan-marshall/plan-marshall/test_invariants_main_resolution.py` (**10** tests) and
`test_invariants_main_capture_refusal.py` (**9** tests). **19** total. (The first draft said 9 + 6 =
15 and named the refusal module by its pre-rename filename; both were left behind when round 1 added
tests and renamed the module.)

⛔ **A guard is not a guard until it has been seen to fail.** Every test was mutation-tested against
the specific defect it names, not against a plausible neighbour. **Population: all 19 tests in the two
modules, for every row** — the earlier draft of this table mixed populations between rows, so three of
its four "green" figures counted only one module:

| Mutation applied to shipped code | Red | Green |
|---|---|---|
| `M1` — main-scoped resolution follows cwd (the original defect) | **6** | 13 |
| `M2` — cross-field refusal not invoked | **4** | 15 |
| `M3` — refusal keyed on equality alone (same-tree gate dropped) | **2** | 17 |
| `M4` — error code absent from VERIFY_REFUSAL_ERRORS | **1** | 18 |
| `M5` — current-checkout resolver made main-anchored | **2** | 17 |
| `M6` — override branch dropped from the main resolver | **1** | 18 |
| `M7` — main_sha None-guard removed | **1** | 18 |
| `M8` — main_dirty_files None-guard removed | **1** | 18 |
| `M9` — error code absent from the strict exit list | **1** | 18 |
| `M10` — strict verify exits 1 unconditionally | **1** | 18 |
| `M11` — refusal ignores the worktree gate entirely | **1** | 18 |

**Union of the red sets: 19 of 19.** Derived by set union over the recorded per-mutation red lists,
not asserted — an earlier draft claimed full coverage when the union was 11, and the two tests that
survived every mutation then were both **negative controls**, which is exactly the class a red-set
union is needed to notice. `M10` and `M11` were added to reach them, each inverting the guard
its control exists to hold.

⚠ **The previous draft carried a twelfth row whose figures were wrong (6 red), and round 2 caught
it.** That run's mutation *also* rewrote the exception payload, so two refusal tests reddened on their
payload assertions rather than on the two-sidedness the row's label named — the figures described a
different mutation from the one written down. Re-measured as the **pure** same-tree-gate removal it
turned out to be `M3` exactly, so the duplicate row is gone; `M11` was added because neither variant
reaches the no-worktree-path control. Every other row was independently re-measured by round 2 and
matched to the figure.

All mutations were applied to the *shipped* code and reverted; `git status` is clean.

⚠ **One process finding worth recording.** The first mutation harness restored each file with
`git checkout -- <path>`, which restores from the **index** — so it silently reverted the run's own
uncommitted fixes to `_invariants.py` rather than just the mutation. It was caught immediately (the
next mutation's anchor did not match) and the fixes were reapplied and verified, but the lesson is
general: a mutation harness must restore from a snapshot it took itself, never from git, and
uncommitted work should be committed before any such sweep.

The plan's three named cases:

- **(a)** `test_capture_main_sha_records_main_head_not_the_pinned_worktree_head` — real repo + real
  linked worktree carrying its own commit, cwd pinned to the worktree: `main_sha` equals main's HEAD,
  `worktree_sha` equals the worktree's, and the two differ. Red under `M1`.
  `test_capture_main_dirty_reads_main_not_the_pinned_worktree` dirties **only** the worktree, so a
  non-zero `main_dirty` could only mean the wrong tree was read — settling the plan's
  companion-dirty-flag hypothesis by execution.
- **(b)** the refusal module's nine tests: five direction/verb tests
  (`test_refuses_when_both_columns_resolved_to_the_same_tree`,
  `test_permits_equal_shas_when_the_two_trees_are_distinct`,
  `test_permits_equal_shas_for_a_plan_with_no_worktree_path`,
  `test_cmd_capture_returns_structured_refusal_and_writes_no_row`,
  `test_cmd_verify_returns_the_same_refusal_rather_than_raising`), the gate-predicate test
  (`test_the_gate_is_the_persisted_path_not_the_use_worktree_flag`), the `VERIFY_REFUSAL_ERRORS`
  membership test, and the strict-exit pair (positive plus negative control). D3's fourth listed test,
  `test_a_commit_less_feature_branch_is_captured_not_refused`, lives in the **resolution** module
  because it needs that module's real-repo fixtures — so it is counted there, not here.
- **(c)** `test_summariser_sees_no_main_sha_drift_across_the_execute_boundary` — the rows are built
  by the **real capture** at both boundaries (cwd on main for the `4-plan` row, pinned to the
  worktree for the `5-execute` row) and then fed to the summariser's `detect_drift`. Hand-feeding
  rows would have passed pre- and post-fix alike; deriving them makes the test discriminating. Under
  `M1` it reproduces the reported symptom verbatim:
  `main_sha, 4-plan → 5-execute, 0250cddd… -> fccd486f…`.

**This is also how the plan's un-reachable OBSERVED claims were settled.** The records are
machine-local, and the plan directed that the resolver's behaviour under a pinned directory be
reproduced instead. It was: `M1` produces the false drift entry in-clone, from a real worktree, with
no reference to any archived corpus.

**Declared collateral: the layer-D comparison at `verify --phase 4-plan` is corrected, not newly
armed.** `_check_main_dirty_drift` fires only at the planning-phase boundaries, and
`workflow/execution.md` re-anchors cwd into the worktree in its Step 0 preflight *before* issuing
`verify --phase 4-plan --strict`. Pre-fix that compared a main-captured baseline against the
**worktree's** live dirty set — two different trees, so it could both fire spuriously and pass
spuriously. Post-fix both sides are main's set, which is the signal the guard was written for. Stated
here because it is a behaviour change the deliverables do not name.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **11 Python files** (6 production, 5 test),
so the gate applies. (The first draft of this report said 7 (5 production, 2 test): the command had
been run against the working tree before the two new test modules were tracked, so untracked files
were invisible to it, and round-1 fixes later widened the set. Re-derived at the moment of this
claim.)

`UV_HTTP_TIMEOUT=600 ./pw verify` — **clean**: `20665 passed, 14 skipped`, and every gate
dimension reported complete (mypy production 412 files, ruff, SPDX, plugin-doctor marketplace-wide,
mypy test 768 files, whole-tree pytest). Read from the streamed tool output, not the exit code: the
`./pw` path emits no structured log. `=== verify: SUCCESS ===`.

No lockfile churn reached the commit — `git status` was checked for stray generated files before
staging, and the deliverable paths were staged by name rather than with `git add -A`.

## Findings

**Round budget: 4, declared before the first dispatch.** Verification is dispatched as an independent
`general-purpose` sub-agent that reports and never fixes.

### Round 1 — 12 findings, all fixed

The round executed rather than read: it reproduced three of the four mutations the report claimed, ran
the whole suite, probed the path comparison at 15 boundaries, ran `_worktree_in_use` over 7 metadata
shapes, drove the real `cmd_verify`, and built a real repo + real linked worktree with a commit-less
branch. One finding is recorded per instance.

| # | Source / site | Finding | Disposition |
|---|---|---|---|
| F1 | `_handshake_commands.py` `cmd_verify` | The new refusal handler was **unreachable dead code** — `capture_all` runs the cross-field check itself, so the exception escaped at the `capture_all` call and rendered as `internal_error` via `safe_main`. Its own comment claimed the opposite. Everything D3 documented for verify time was undelivered. | **Fixed** — catch moved onto the `capture_all` call; shared payload builder; covered by a test driving the real `cmd_verify` |
| F2 | `_invariants.py` `_main_repo_root`, ×2 sites in `phase-handshake.md` | "cwd-independent" / "never falls back to cwd" / "mirrors `resolve_main_anchored_path`" are **false in the override branch**: a flat override delegates to `_current_repo_root`, which returns `Path.cwd()`. Proven by execution — the same override returned two different roots from two cwds. | **Fixed** — restated as **worktree-invariance**, with the precision note that neither branch is cwd-*independent* and the ⛔ no-fallback rule scoped to the git branch where the defect lives |
| F3 | `_invariants.py` exception + helper docstrings, `phase-handshake.md` | "One-sided by construction: a plan genuinely running on main captures no `worktree_sha`" — refuted by running `_worktree_in_use` over 7 shapes: it keys on `worktree_path` and **never reads `use_worktree`**. | **Fixed** — restated as the predicate actually is, and pinned by a new test asserting `{'use_worktree': False, 'worktree_path': …}` is treated as worktree-backed |
| F4 | `_cmd_lifecycle.py:137`, `:388` | The file whose constant gained a member still described `VERIFY_REFUSAL_ERRORS` as three categories and counted "**the three**" members. Pre-existing (already wrong at four), moved to wrong-by-two. | **Fixed** — category list extended; the ordinal replaced with "enumerated by", per prefer-naming-to-counting |
| F5 | `test_invariants_main_capture_refusal.py` helper docstring | "the **ten** plan-state captures that would shell out through `_run_script`" — the true figure is **7**, which this report already stated correctly elsewhere. | **Fixed** — corrected to 7 |
| F6 | `marketplace_paths.py` `base_dir_override_active`; `_lessons_io.py:91`; `test_lesson_store_resolution_fail_open.py:79` | The new docstring claimed **every** main-anchored resolver calls it, while one hand-maintained copy of the disjunction remained in `_lessons_io` — whose own docstring documented that mirror as an unguarded hazard, and whose test asserted the two sites are "textually identical COPIES". | **Fixed** — `_lessons_io` converted to the shared predicate (removing the documented hazard), both docstrings and the test's rewritten; the predicate's docstring now **names** its readers instead of asserting a universal |
| F7 | `report-01.md` build gate | "7 Python files (5 production, 2 test)" — actual **11 (6 production, 5 test)**. The command had been run before the new test modules were tracked. | **Fixed** — re-derived at the moment of the claim, with the cause recorded |
| F8 | `report-01.md` mutation table | "Every one of the 15 is covered by at least one mutation" — the union was **11 of 15**, and the two structurally-uncoverable survivors were **negative controls**. The table also silently changed population between rows. | **Fixed** — two further mutations added to reach the controls, the matrix re-run in full (11 mutations, union **19 of 19**), populations labelled |
| F9 | `report-01.md` D4 | "A tree-wide search for `handshakes.toon` returns zero files" self-contradicted its own next clause, and was invalidated by the run's own build gate, which writes hundreds under `.plan/temp/pytest-basetemp/`. | **Fixed** — claim withdrawn and the hazard recorded; the BLOCKED verdict now rests on the narrower stable fact (`.plan/local/` has no `plans/`). Unit label corrected from "corpora" to "plans" per the plan's wording |
| F10 | `invariant-check-summary.md` | The shipped D4 rule asserted **two universals** the tree contradicts: "exactly one" false drift entry per plan, and "other boundaries are correct". `workflow/execution.md` Step 0 re-anchors cwd into the worktree and *then* upserts the `4-plan` row, so a cross-session re-entry moves the false entry back a boundary. The plan labels this a **HYPOTHESIS**; it shipped as an assertion. | **Fixed** — rewritten to identify the artifact **from the row**, with the re-entry upsert mechanism named and the boundary-level claims dropped |
| F11 | `phase-handshake.md:315` | Documented a verify-time refusal that did not exist (same root cause as F1) — the operator-facing surface. | **Fixed** by F1's code change, which makes the documented behaviour real |
| F12 | `_invariants.py` `_assert_main_capture_read_main` (behavioural) | **A legitimate state was refused**: a worktree-backed plan whose feature branch carries no commit. Reproduced against a real `git worktree add`. Condition **B** was not satisfied — no proof and no bound was offered. | **Fixed, not characterised** — the refusal is re-keyed on the same-tree resolution. Re-probed against a real commit-less worktree post-fix: permitted, main correctly resolved. Guarded by a real-repo test that deliberately uses no stub |

**Lower-severity observations from the same round, all acted on:** `capture_all` gained the `Raises:`
section its five raising paths never had; `phase_handshake`'s `--strict` docstring no longer claims
drift is the only non-zero exit; the refusal helper now filters the **live** registry instead of
substituting a hard-coded two-entry list; the `cmd_capture` test's incidental route to its assertion
was replaced with a fixture that arranges the defect deliberately; the strict-exit guard was rewritten
from a source-text grep into a test that drives `main()` and reads `SystemExit.code`, with a negative
control. One observation was a **verified negative and is recorded as such**: adding a second
main-anchored resolver does **not** violate `cwd-policy.md`'s single-sanctioned-resolver assertion,
which is scoped to `.plan/`-path resolution for plan-scoped state.

### Round 2 — 7 findings, all fixed. No behavioural defect in the shipped code survived

The round re-ran all eleven mutations from its own snapshots, rebuilt the real-repo probes, drove
`_assert_main_capture_read_main` over 12 path shapes, ran `detect_drift` on capture-derived rows, and
took an AST closure over `capture_all`'s raise set. **Every finding is a false statement (condition
A); none is behavioural.** Two are instances of round-1 findings marked "Fixed" that had been fixed at
fewer sites than the claim spanned — the n−1-of-n pattern.

| # | Source / site | Finding | Disposition |
|---|---|---|---|
| F13 | `invariant-check-summary.md` (the D4 deliverable) | The rule's load-bearing premise — the commit-less-branch case "writes the same value at every boundary and therefore emits **no** drift entry" — is **false**. `main_sha` is main's HEAD at each boundary, and main moves when a sibling merges. Executed counter-example: a commit-less-branch plan emitting a genuine `4-plan → 5-execute` drift entry **with the fingerprint present**, reproduced on both sides of the fix. The rule therefore instructed retrospectives to discard a true "main moved mid-plan" signal. | **Fixed** — rewritten around **branch containment** as the only evidence that separates the two cases; the fingerprint now marks a row *ambiguous* rather than convicting it |
| F14 | `_invariants.py` `_capture_main_sha`, `_capture_main_dirty` | Both still opened with "**cwd-independent**" — the exact claim round 1's F2 refuted and fixed in `_main_repo_root`, whose docstring three functions above now says outright "It is NOT cwd-independent in general". The file contradicted itself. Refuted again by execution under a flat override. | **Fixed** at both sites — restated as **worktree-invariant**, with the caveat named rather than cross-referenced away. Recorded as an n−1-of-n miss: F2 was fixed at 1 of 3 sites |
| F15 | `report-01.md` D4 section, 3 claims | Still described the **pre-round-1** rule ("`to_phase` is `5-execute`", "other boundaries unaffected") and the **pre-narrowing** refusal ("only possible under the pre-fix resolution", "such a row is now refused at capture time"). The last is refuted by execution — such a row is *permitted*. | **Fixed** — section rewritten to record both corrections and what each reversed, plus the candour gap below |
| — | (same section) | The report never said the refusal is **unreachable in production** except under a D2 regression, while "Not open-ended" implied the opposite. | **Fixed** — stated plainly, with the reason (`git-common-dir` vs `<main>/.plan/local/worktrees/…` can never compare equal, and no production site sets an override) |
| F16 | `report-01.md` D5 header | "`test_invariants_main_resolution.py` (9 tests) and `test_invariants_worktree_sha_refusal.py` (6 tests). 15 total." — the module name was retired in round 1 and the counts are **10 / 9 / 19**; the next paragraph already said 19. | **Fixed** — re-derived by collection |
| F17 | `report-01.md` mutation matrix | The `M10` row's figures (6 red) described a **different mutation** than its label: that run's variant also rewrote the exception payload, so two refusal tests reddened on payload assertions rather than on two-sidedness. Round 2 re-measured every row from its own snapshots; the other ten matched exactly. | **Fixed** — re-measured as the pure same-tree-gate removal, which turned out to be `M3` exactly, so the duplicate row is gone. A genuinely new mutation (`M11`) was added because neither variant reaches the no-worktree-path control. Union still **19 of 19**, now over 11 distinct mutations |
| F18 | `test_invariants_main_resolution.py` module docstring | Named the deleted module `test_invariants_worktree_sha_refusal.py` **and** described the retired equality-only trigger — the last surviving tree reference to either. An enumeration lead-in ("three levels") also stood over two bullets. | **Fixed** — module renamed in the reference, trigger restated, the count replaced by naming the two levels |
| F19 | `test_invariants_main_resolution.py` `test_main_repo_root_returns_none_outside_a_git_repository` | The test's stated premise was false under the project's own harness: `build.py` pins `--basetemp` inside the repo, so a `tmp_path` subdirectory is **inside** this git worktree and the `chdir` was inert — only the stub produced the `None`. `conftest.py` ships an `outside_repo_dir` fixture whose docstring warns of exactly this trap. | **Fixed** — switched to `outside_repo_dir` and the stub **dropped**, so the real resolver is now exercised against a genuinely repo-less cwd |

**Lower-value observations, dispositioned:** `marketplace_paths.py` cited `merge_lock._override_is_set`,
which no longer exists — **fixed** (pre-existing, but false, and in a file this change touches).
`TestOverridePredicateMirroring` was misnamed once its two sites came to share one predicate —
**renamed** to `TestOverridePredicateAgreement`, with the `_lessons_io` reference updated. The report's
D5(b) accounted for 8 tests where the refusal module holds 9 — **fixed**. One observation is
**accepted, not fixed**: `_main_repo_root()` now shells out to git and is called 4× per `capture_all`
(three captures plus the assertion) where the old resolver was pure. That is four `git rev-parse`
invocations at a phase boundary whose captures already fan out ~10 subprocesses through `_run_script`;
memoising would add cross-call state to a module that has none. Recorded as a declared characteristic.

**Round 2 confirmed by execution, and these are recorded so the negatives are distinguishable from
unchecked items:** the F12 fix (real commit-less worktree → captured, not refused); the refusal still
firing for the real defect; the narrowing having **no hole** for symlinked, trailing-slash, `..`-bearing
or `.plan/local/worktrees/`-shaped paths (`Path.resolve()` normalises all of them), with the single
miss being a *relative* path in the false-negative direction the docstring already claims; both
mechanism claims in the `_main_repo_root` docstring; the "both early returns unreachable by
construction" claim; the `phase-5-execute` Step 2.5 ordering; all four named readers of
`base_dir_override_active` and the absence of a fifth hand-spelled disjunction; the `capture_all`
`Raises:` set being exactly the five reachable exceptions (AST closure); the shared-envelope claim;
that `--override` provides **no** escape hatch, identically to the four sibling capture-time refusals;
that `findings-check` is unaffected; and that `VERIFY_REFUSAL_ERRORS` is enumerated in exactly two
places, both updated.

### Round 3 — 9 findings, all fixed. Exit-evidence campaigns all clean on the shipped Python

The round ran four campaigns of the kind that can come back different: exhaustive branch enumeration
under branch-coverage over all 570 tests in the owning directory, a differential run of `origin/main`'s
`_invariants.py` against HEAD's across five conditions, a 4000-pair fuzz sweep over the path
comparison, and a targeted mutation. **All four came back clean on the code.** Every one of the nine
findings is a false statement (condition A); none is behavioural.

| # | Source / site | Finding | Disposition |
|---|---|---|---|
| F20 | `invariant-check-summary.md` (the D4 deliverable) | ⛔ **Round 2's branch-containment discriminator returns the INVERTED verdict at the moment the rule is read.** `plan-retrospective` is a `post_run_review` step (`order: 995`) that runs **after the merge gate**, and the default PR merge strategy is a **merge commit** (`ci_base.py`, `--strategy` default `merge`) — which makes every feature-branch commit an ancestor of main. So a mislabelled `main_sha` reads as "on main" and containment reports *sound* for exactly the rows it was meant to convict. Executed both cases before and after a real `merge --no-ff`. Rebase/fast-forward merges break it too; only squash preserves the distinction, and that is not the default. | **Fixed** — the discriminator is **withdrawn**. The rule now reports such an entry as **unverifiable**, names all three failed discriminators (boundary, stored columns, containment) with the reason each fails, and states plainly that what would settle it — the row's capture era relative to the fix — is not in the corpus |
| F21 | same file | "A post-fix row needs no containment check … main's HEAD **whatever the working directory**" is false. Executed: with a base-dir override active and cwd in a worktree **subdirectory**, `_main_repo_root()` returns that subdirectory, so it is unequal to `worktree_path`, the refusal does **not** fire, and a mislabelled row persists with the fingerprint. | **Fixed** — the universal is replaced by "sound *unless an override was in play*", with the subdirectory mechanism named |
| F22 | `test_phase_handshake_validators.py` (docstring **this plan rewrote**) | "`cwd=tmp_path` (a non-git, isolated dir) leaves the git probes with **no repository to read**" — both halves false: `build.py` pins `--basetemp` inside the repo, so the probes read this worktree and `main_sha` captured the real HEAD. **Third instance of the trap** F19 named; round 2 fixed the sibling module and left this one. | **Fixed** — the note now says only the executor fan-out is isolated, not the git reads, and why that suffices for a parse-time test |
| F23 | `test_invariants_main_resolution.py` | Round 2's own F19 fix dropped the `main_checkout_root` stub and left the docstring saying the resolver is "exercised **alongside the stub**". | **Fixed** — the docstring now describes the real `git rev-parse` failure path, which is what produces the `None` |
| F24 | `report-01.md` D5(b) | The decomposition named the wrong six tests: one of D3's six lives in the *resolution* module, and the refusal module's gate-predicate test was unaccounted for. The total reached 9 only because the mis-attribution and the omission cancelled. Round 2 fixed this row's count without fixing its claim. | **Fixed** — every test named explicitly, with the cross-module one attributed to where it lives and why |
| F25 | `report-01.md` | "No production site sets `PLAN_BASE_DIR` … the refusal is **unreachable** in production except under a D2 regression" — over-strong. `PLAN_BASE_DIR` is a documented **user** override, and under one the refusal genuinely fires. | **Fixed** — restated: not reachable in the *default* configuration, a live guard under an override. The `set_base_dir()` and `worktree_path` conjuncts were verified and hold |
| F26 | `phase-handshake.md` | "the row disproves itself **with no external reference**" — pre-narrowing wording. The check consults `_main_repo_root()` (a live git probe) and `metadata.worktree_path`, neither a row column. It also contradicted the D4 rule two files away, which says the stored rows carry nothing that distinguishes the cases. | **Fixed** — now states that the refusal is available at capture time and **not** to a later reader of the row, with the xref to the retrospective rule |
| F27 | `invariant-check-summary.md` | The severity line's parenthetical "(the worktree should isolate the plan from main)" contradicted the bullet added directly below it, and `phase-handshake.md` § Blocking classification. | **Fixed** — replaced with what `main_sha` drift actually means (the integration target moved), plus the xref |
| F28 | `_invariants.py` ×3 | "raises `TaskGraphInvalid` so **`cmd_capture` refuses**" — there is no handler and no `task_graph_invalid` error code, so it escapes as `internal_error`. The same defect shape as F1, on the fifth member of the `Raises:` set this plan added. Pre-existing (confirmed absent at `origin/main` too). | **Fixed at all three sites** — the *outcome* claim was true (no row persisted, boundary blocked) and is kept; the *mechanism* is corrected, and the lost structured diagnosis is named. The missing handler is carried as declared residue, with its bound |

**Exit-evidence campaigns, with verdicts:**

- **Branch enumeration.** `_main_repo_root`: 3 return paths, **all reached by a named test**, no missing
  branches. `_assert_main_capture_read_main`: 8 paths, 6 reached; the two misses are the guards the
  docstring already calls unreachable-by-construction, and the round independently confirmed both by
  argument. The one unclaimed miss (`except OSError`) was probed — 5000-char and 2000-segment paths
  resolve fine, and the input that does raise (`\x00`) raises `ValueError` in `git_head` *earlier* in
  the registry loop, so no new crash path exists.
- **Differential run vs the merge base**, five conditions: **exactly one behaviour changed** — cwd in a
  linked worktree, where all three `main_*` columns now read main instead of the worktree. That is D2's
  fix, and it lands on all three columns rather than `main_sha` alone. Every other condition (cwd on
  main, flat override on main, flat override in a worktree, outside any repo) is byte-identical to the
  base. `capture_all` cross-field: base persists an equal pair from the worktree, HEAD persists a
  differing one.
- **Fuzz sweep**: 14 deterministic same-tree shapes (trailing `/`, `//`, `/.`, `..`-bearing, symlink
  alias, `subdir/..`) all refuse; 8 different-tree shapes give no false positive; **4000 random path
  pairs, 0 mismatches** against `Path.resolve()`-equality.
- **Mutation**: making the resolver's `except RuntimeError` fall back to `_current_repo_root()` reddens
  **exactly** the one test round 2 rewrote — so dropping its stub left it non-vacuous. It is also
  fail-loud rather than fail-silent: forcing `TMPDIR` inside the repo produces an explicit
  `AssertionError` rather than a pass.

**Are the late rounds' findings narrower? Partly, and the report says so rather than claiming
convergence.** They have moved from code to prose — round 3 found no behavioural defect in the shipped
Python, and its four campaigns are the strongest evidence this run has produced. But the D4 deliverable
*is* prose, and F20 inverted its verdict at the only moment it is read; that is not a narrow finding.
The recurring shape across rounds 2 and 3 is **n−1-of-n**: a claim corrected where the finding pointed
and left standing elsewhere (F14, F22, F24, F26, F27 are all instances). Round 3's verifier judged that
pattern to be relocating rather than converging, and that judgement is recorded here as it was given.

### Round 4 — the final budgeted round. 9 findings, all fixed

| # | Source / site | Finding | Disposition |
|---|---|---|---|
| F29 | `report-01.md` D4 narrative | ⛔ The report's own account of what D4 ships stated the **withdrawn** rule: containment as "the discriminator", and "a post-fix row needs no check at all" — the two things rounds 3's F20 and F21 had just reversed. It contradicted itself 17 lines below. Round 3 fixed the shipped file and its findings table, and not the narrative of the same rule. | **Fixed** — replaced by a four-row correction history stating what each round reversed, and what the rule now is |
| F30 | `_invariants.py` `MainCaptureReadTheWorktree` docstring | (a) "the row disproves itself **with no external reference**" — the sibling site of F26, fixed in `phase-handshake.md` and left standing here. (b) "a `main_sha` that **provably never reached main**" — refuted by execution: under an override, a commit-less-branch plan trips the refusal on a value that **is** main's HEAD. | **Fixed** — both: the evidence is named as the resolved paths (live probe + metadata, not row columns), and the refused value is no longer claimed to be off-main |
| F31 | `invariant-check-summary.md` | "**What would settle it is not in the corpus**" — false. `handshakes.toon` rows carry **`captured_at`** (`HANDSHAKE_FIELDS[1]`, stamped on every write). The era *is* recorded; only the cutoff is external. And because `capture` upserts, `captured_at` dates the write whose resolution semantics produced the value — the property that defeats the boundary discriminator is what makes this one work. | **Fixed** — the rule's verdict moves from `unverifiable` to a determinate two-step check; `captured_at` is now the named discriminator |
| F32 | same file | "a rebase or fast-forward merge does the same … only squash preserves the distinction" — false. Executed across six merge shapes: rebase **rewrites** the SHAs whenever main moved, so it preserves the distinction. Only the default merge-commit strategy inverts. The rule's *conclusion* survives; the enumeration was wrong. | **Fixed** — corrected to name squash and rebase as both preserving it, with the default as the case that does not |
| F33 | `test_phase_handshake_validators.py` `test_list_subcommand_canonical_plan_id` | **Fourth** instance of the `tmp_path`-is-outside-the-repo premise — 30 lines from the sibling docstring round 3 had just rewritten, and cross-referencing it. | **Fixed** — states that only the executor lookup is isolated, with the pointer to the corrected sibling note |
| F34 | `invariant-check-summary.md` § Inputs **and** `plan-retrospective/SKILL.md` | Both said the summariser reads `status.metadata.phase_handshake` / `.invariants`. **Neither key exists anywhere in the tree**; the script reads `{plan_dir}/handshakes.toon`, as its own module docstring says. Pre-existing, but in the D4 deliverable's own file, load-bearing for what the reader's fact source is, and the direct cause of F37. | **Fixed at both sites** |
| F35 | `report-01.md` D5(b) | "D3's **sixth** listed test" — it is the fourth. Introduced by round 3's own F24 fix to this sentence. | **Fixed** |
| F36 | `phase-handshake.md` | "self-contradictory-row refusals" — last surviving use of the retired framing in bundle prose. | **Fixed** |
| F37 | `invariant-check-summary.md` (**behavioural**) | ⛔ **The rule was unactionable by its declared reader, so D4 shipped as a no-op.** The aspect declares its facts come from `summarize-invariants.py`, which emits invariant **names** per phase and strips `captured_at` — so an LLM given those facts cannot evaluate the fingerprint at all. | **Fixed, not characterised** — condition B offers neither a proof nor a bound for a finding that stops the deliverable working. The rule now instructs the reader to open `handshakes.toon` and names both fields to read; § Inputs states what the summary output does and does not carry |

**Verified clean by round 4, recorded so the negatives are distinguishable:** D1's populations
re-derived at HEAD (registry 15, main-named 3, `_run_script` 10 call sites → 7 registry captures — all
report figures correct); round 3's commit proved **docstring-only** by AST comparison, so its four
campaigns remain valid; 570/570 tests pass in the owning directory; every report enumeration
independently counted, including the D5(b) list now naming exactly the right nine tests; the plan's
**Out of scope** holds (no second explicit-tree argument at the capture site, no corpus rewrite); the
subdirectory refusal-miss reproduced; both new xrefs open onto sections that say what the citations
imply; and **no consumer of the `main_*` columns is unexamined** — `summarize-invariants.py` is the
only one, `execution-recovery.md`'s `main_sha` is the `status.metadata` namespace D1 excluded, and the
archived-plan audit skill does not read handshake rows.

**One plan claim-label disposition was missing and is now recorded.** *"A commit recorded in the
main-named field provably never reached main — OBSERVED, verified by branch containment."* **This run
does not carry that claim forward.** It was settleable only against the machine-local corpus, which is
unreachable here; and round 3 showed branch containment is not sound evidence for it after a
merge-commit merge, while round 4 showed the converse — a refused `main_sha` can be main's own HEAD.
The plan's own note that "the mechanism above supersedes the need for it" is what this run relied on:
the defect was reproduced from the resolver's behaviour under a pinned directory, which needs no
containment argument.

### The stop record

⛔ **The loop ended on exit (ii): the round budget was exhausted.** It did **not** end on a verifier
answering that nothing remains. Round 4 answered the stop question **"yes — findings remain that
condition A forbids leaving open"**, and judged that the recurring n−1-of-n pattern *"produced findings
in this round and has not stopped."* That answer is recorded as given.

- **Budget: 4 rounds, declared before the first dispatch.** The plan named none, so the run declared
  it — up front, not at the moment of wanting to stop.
- **The round that ended it: round 4**, by exhaustion.
- **Everything condition A forbids was fixed regardless**, as the budget exit requires: all 9 of round
  4's findings are fixed in commit `190910a`, including the two HIGH ones and F37, which had made D4 a
  no-op for its own reader. Running out of rounds bounds how often the run *verifies*; it never bounds
  what it *fixes*.

**Findings per round: 12, 7, 9, 9 — 37 in total, every one fixed, none deferred.** The count did not
fall. What changed is *what* the rounds found:

| Round | Behavioural findings in shipped code | Condition-A false statements |
|---|---|---|
| 1 | 2 (a legitimate state refused; an unreachable handler) | 10 |
| 2 | 0 | 7 |
| 3 | 0 | 9 |
| 4 | 1 (D4 unactionable by its reader) | 8 |

**Are the late findings narrower? Partly — and the honest answer is not a clean yes.** Rounds 2 and 3
found no behavioural defect in the shipped Python at all, and round 3's four campaigns (branch
enumeration, a differential run against the merge base, a 4000-pair fuzz sweep, a targeted mutation)
came back clean. But the D4 deliverable *is* prose, so "only prose findings" does not mean "only
cosmetic findings": round 3's F20 inverted D4's verdict, and round 4's F37 showed D4 could not be
applied at all. Those are deliverable-level, not narrow.

**Condition-B survivors: one, and it is pre-existing.**

| Survivor | Bound (b), and the promise it stays outside of |
|---|---|
| `TaskGraphInvalid` has no handler in `cmd_capture` **or** `cmd_verify`, so a broken task graph surfaces as `error: internal_error` rather than a structured `cycle` / `dangling` payload | **Reaches only** a plan whose task graph carries a cycle or a dangling `depends_on` at a phase boundary — the state the `task_graph_valid` invariant exists to block. **Fails closed at both verbs**: the raise precedes `_row_for_capture`/`upsert_row`, so no row is persisted, and `safe_main` exits 1. The promise it stays outside of is the plan's own goal — *"a self-contradictory record is refused at capture time rather than persisted"* — which it does not weaken: the record is still refused, and the boundary still blocks. The loss is confined to diagnostic shape. Confirmed absent at `origin/main`, so this run neither introduced nor widened it. Re-put to round 4, which ran the whole path and judged the bound "accurate and sufficient", recommending only that it be widened from `cmd_capture` to both verbs — done, in the code docstrings and here |

**Residue a reader should assume remains.** The deliverables should be read as still carrying defects
of the kind round 4 was finding, because the loop stopped on its budget rather than on exhaustion:

- **Prose describing the deliverable, at sites the previous finding did not point at.** This is the
  n−1-of-n pattern, and it produced findings in every round after the first — 2 of 7 in round 2, 5 of
  9 in round 3, 3 of 9 in round 4. Round 4's instances were the report's own narrative of a rule it had
  just fixed, a sibling docstring, and a *fourth* instance of a test premise two earlier rounds had
  named. **Round 4's own fixes are unreviewed**, and are the most likely place for the next instance.
- **Rule-versus-consumer mismatches that no round examined until late.** F31, F34 and F37 were all of
  this kind — a documented rule whose stated inputs, available evidence, or reader did not match
  reality. Three rounds passed over them.
- **The code is the best-evidenced part of this change** and should not be read as carrying the same
  residue: round 3's campaigns were clean, its commit is provably docstring-only by AST comparison,
  round 4 re-derived D1's populations at HEAD, and `./pw verify` is green at every commit.

One further independent pass is still owed and will happen outside this loop: the PR's automated
reviewers see this diff (§ Reviewer participation).

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
