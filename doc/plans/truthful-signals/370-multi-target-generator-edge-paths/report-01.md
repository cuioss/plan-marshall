# Run report — 370-multi-target-generator-edge-paths (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/multi-target-generator-edge-paths-7yae0m`    **PR:** [#1228](https://github.com/cuioss/plan-marshall/pull/1228)    **Outcome:** completed — auto-merge armed, landing delegated to the merge queue (merge commit recorded to the operator, not embedded here)

## Skills loaded

Loaded by bundle path (fresh cloud clone; `plan-marshall` plugin not assumed present):

- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`)
- `pm-plugin-development:plugin-script-architecture`
- `plan-marshall:persona-implementer` (work identity for production code)
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

## D0 — GATE: confirm every finding at HEAD by symbol, and re-count

Mutates nothing. Every location verified by **symbol** (line numbers in the source review are stale and were not used). Surface confirmed to be swapped/renamed relative to some claim prose, so each was re-derived against the tree.

| Finding | Symbol (verified at HEAD) | Verdict |
|---|---|---|
| Unguarded destructive wipe | `claude/emitter.py::emit_bundle_verbatim` — `if dest_root.exists(): shutil.rmtree(dest_root)` (no containment check) | **CONFIRMED — live** |
| Sibling containment helper exists | `opencode/emitter.py::_safe_rmtree(path, output_dir)` refuses a target outside `output_dir` | **CONFIRMED** |
| Docstring's false safety argument | `emit_bundle_verbatim` docstring: "Target/claude/ is a pure build output (gitignored…), so the wipe is safe" | **CONFIRMED — live** |
| Non-pruning emitter | `opencode/emitter.py::emit_bundles` / `_emit_skill` / `_emit_agent` / `_emit_command` only `mkdir` + `write_text`; top-level `skill/`,`agent/`,`command/` output is never cleared | **CONFIRMED — live** |
| Frontmatter fence by raw substring | `opencode/frontmatter.py::parse_frontmatter` — `end = content.find('---', 3)` | **CONFIRMED — live** |
| Sibling anchors the fence on a newline | `claude/variant_emitter.py::parse_frontmatter` — `end = text.find('\n---\n', 4)` | **CONFIRMED** |
| Unguarded JSON read | `claude/equality_check.py::_read_emitted_plugin_json` — `json.loads(plugin_json.read_text(...))` with no guard | **CONFIRMED — live** |
| Adjacent read is guarded | `claude/equality_check.py::_check_marketplace_json` — `try: json.loads(...) except json.JSONDecodeError` | **CONFIRMED (asymmetry is the evidence)** |
| Path-keyed cache blind to content | `claude/variant_emitter.py::_load_mapping` — `@lru_cache` keyed on `Path` only | **CONFIRMED — live** |
| Diff double-count REACHABLE | `claude/equality_check.py::check_bundle` two layers (manifest + orphan) | **CONFIRMED in code, UNREACHABLE in practice → D6 DROPPED (see below)** |
| Prefix-strip idiom retired + guarded | repo-wide sweep + `test/marketplace/test_prefix_strip_idiom_retired.py` | **CONFIRMED — DELETED at D0 (already closed)** |

### Already-closed deliverable — DELETED, not restated

The prefix-strip idiom (`lstrip('./')` / `lstrip("./")`) returns **zero occurrences** under `marketplace/` (precise literal sweep, both spellings). The population-derived build guard `test/marketplace/test_prefix_strip_idiom_retired.py` fails the build on re-introduction. Per D0 this deliverable is **deleted** — not re-verified by inspection beyond the one confirmation the plan permits.

### Reverse sweep (both directions)

The two emitters were compared each way. The only material asymmetries are the two the plan already names: (1) `claude` has the dangerous unguarded wipe but no containment helper (D1); (2) `opencode` has the containment helper but no top-level prune (D2). No *other* asymmetry survives: `claude/iter_bundle_dirs` is traversal-safe by construction (it filters real directory entries by name membership rather than joining an arbitrary name), so it needs no `..` guard the way `opencode/iter_bundle_dirs` does. The frontmatter parsers (D3) and the JSON reads / cache (D4/D5) live in different modules, not in the emitter pair.

### D6 reachability — CONSTRUCTED and judged UNREACHABLE → DROPPED

The double-count was reasoned from code; per the plan it was **confirmed by constructing the out-of-sync state**. Four states were built and run through `check_bundle`:

| State | Setup | `check_bundle` entries |
|---|---|---|
| C1 hand-corrupted | component in **source + on disk**, absent from emitted `plugin.json` | **2** (manifest `only_in_generated` **and** `agents-orphans`) |
| C2 added-not-re-emitted | in source; absent from manifest **and** disk | 1 |
| C3 deleted-not-re-emitted (the *documented* orphan scenario) | absent from source; still in manifest **and** disk | 1 |
| C4 pure orphan | on disk; absent from source **and** manifest | 1 |

Only **C1** double-counts, and C1 requires the emitted tree to be **internally inconsistent** — a `.md` file present on disk yet absent from its own sibling `plugin.json`, while that component still exists in source. The emit pipeline (`ClaudeTarget.generate`, target.py) writes files (`emit_bundle_verbatim`, which wipes+rewrites the whole bundle dir) and regenerates `plugin.json` together, from one source and one cached `mapping.json`, in the same loop iteration — so **after any emit, on-disk always equals the manifest.** A crash between the two steps leaves *no* `plugin.json` (the wipe removed it), which hits `run_equality_check`'s `missing` path, not C1. C1 is therefore reachable only by hand-corrupting the gitignored build output in a shape the emitter never produces.

Per the plan ("If unreachable, DROP this deliverable rather than 'fixing' a path that cannot occur — that would be a vacuous fix, which is this epic's own archetype") **D6 is dropped.** No code was added for it.

### Surviving deliverable set

**D1, D2, D3, D4, D5, D7.** D6 dropped (above). The already-closed prefix-strip deliverable deleted (above). The remainder is non-empty, so the plan is not a no-op.

## Deliverables

| # | Deliverable | Status | What changed |
|---|---|---|---|
| D0 | Gate: confirm/re-count | **done** | Findings confirmed by symbol; prefix-strip deliverable deleted; D6 dropped (see D0 section above). Mutates nothing. |
| D1 | Guard the destructive wipe | **done** | New shared `marketplace/targets/fs_safety.py` (`is_within` + `safe_rmtree`) — the sibling `_safe_rmtree` extracted, not re-implemented. `opencode/emitter.py` now imports it (no duplicate). `claude/emitter.py::emit_bundle_verbatim` refuses a destination inside the source tree (`is_within(dest_root, bundle_dir.parent)`) and wraps the wipe in `safe_rmtree`. Docstring's false "gitignored ⇒ safe" argument corrected. |
| D2 | Make the non-pruning emitter prune | **done** | `opencode/emitter.py::_prune_stale_outputs` unlinks every emitted `skill/`,`agent/`,`command/` file not written this run and removes the directories left empty (deepest first) — **file granularity**, so it prunes a whole removed component AND a verbatim sub-directory removed from a *surviving* skill. No broad `rmtree`, so no containment hazard is re-introduced. Full-regeneration only (scoped `--bundles` emits share flat agent/command namespaces and cannot attribute a leftover to a bundle safely; the normal build and drift checks are full regenerations). |
| D3 | Anchor the frontmatter fence | **done** | `opencode/frontmatter.py::parse_frontmatter` now anchors the closing fence on a newline-delimited `\n---\n` (matching the sibling `variant_emitter.parse_frontmatter`), with the sibling's trailing-`---`-at-EOF tolerance. A `---`-containing value no longer truncates the block. |
| D4 | Guard the JSON read | **done** | `claude/equality_check.py`: new `CorruptEmittedPluginJsonError` raised by `_read_emitted_plugin_json` on a bad emitted file; `run_equality_check` catches it and returns the documented "re-run emit" diagnostic instead of a traceback. A corrupt *source* plugin.json still raises (a genuine, different error). |
| D5 | Key the cache on content | **done** | `claude/variant_emitter.py::_load_mapping` now keys the `lru_cache` on `(path, st_mtime_ns)` via `_load_mapping_cached`, so an in-place edit misses the cache and is re-read. Cites the same archetype as `plan-marshall:script-shared` `argparse_surface.py` (content-digest key, not path alone). |
| D6 | De-dup diff layers | **DROPPED** | Double-count confirmed in code (C1) but unreachable in practice — see D0 § D6. No code added. |
| D7 | Tests, each FAIL-first | **done** | See below. |

### D7 — tests, each verified FAIL-first

Every bug test was run against the pre-fix code (production files `git stash`-reverted to HEAD, tests kept) and seen **red**, then green with the fixes restored. The matched control for the wipe guard has both halves.

| Test | File | Pre-fix (red) evidence |
|---|---|---|
| `test_emit_bundle_verbatim_refuses_output_inside_source_tree` (D1 negative control) | `test/marketplace/targets/claude/test_emitter.py` | pre-fix: no refusal, source destroyed |
| `test_emit_bundle_verbatim_legitimate_output_still_wipes` (D1 positive control) | same | passes pre- and post-fix by design (guard must not break legit emits) |
| `test_is_within_*` / `test_safe_rmtree_*` (shared helper) | `test/marketplace/targets/test_fs_safety.py` | unit coverage incl. prefix-sibling boundary + refuse-outside negative control |
| `test_emit_bundles_prunes_removed_skill` / `_removed_agent` (D2) | `test/marketplace/targets/opencode/test_emitter.py` | pre-fix: stale emitted dir/file lingers |
| `test_value_containing_triple_dash_does_not_truncate` (D3) | `test/marketplace/targets/opencode/test_frontmatter.py` | pre-fix: `description` truncated at `---`, `tools` dropped |
| `test_corrupt_emitted_plugin_json_returns_diagnostic` (D4) | `test/marketplace/targets/claude/test_equality_check.py` | pre-fix: raises `json.JSONDecodeError` |
| `test_load_mapping_rereads_after_in_place_change` (D5) | `test/marketplace/targets/claude/test_variant_emission.py` | pre-fix: path-cached, stale, not re-read |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (five production modules + one new module + test files), so `./pw verify` takes its full path (quality-gate + test-compile + module-tests). Result recorded at close.

## Findings

### Pre-PR verification sub-agent (independent, read-only)

**Verdict: PASS** — all in-scope deliverables implemented as specified; the D6 drop was independently re-confirmed against the real pipeline (`target.py::generate` writes files + regenerates the manifest from one source, so the C1 double-count state is unreachable); the beyond-diff sweep was clean (no surviving `_safe_rmtree`, no `_load_mapping.cache_clear()`, no stale "gitignored ⇒ safe" prose, no test stub pinning old behavior); out-of-scope respected (no `marketplace/bundles/**` edits, no second containment helper, no prefix-strip restatement). The agent also empirically re-derived FAIL-first for D3 and D5 by reverting those two files.

Two **informational** observations (the agent flagged both as NOT plan violations):

| # | Observation | Disposition |
|---|---|---|
| 1 | D2 pruned at whole-skill-dir granularity, so a verbatim sub-dir (`references/`, `standards/`, …) removed from a *surviving* skill was not pruned — a residual drift finer than D2's component-granularity Done-when. | **Fixed.** `_prune_stale_outputs` reworked to file granularity (unlink non-written files + remove emptied dirs). This directly serves the plan's Goal ("emitted output cannot drift past source") and uses D2's own sanctioned "track written paths and prune leftovers" approach. New test `test_emit_bundles_prunes_removed_skill_subdir`, verified red against the prior whole-dir prune. **A focused re-verification of this change returned CLEAN** (all three prune cases correct, `opencode.json` untouched, empty-dir cleanup safe, full-regeneration-only preserved, no new hazard). |
| 2 | D5 keys on `st_mtime_ns` rather than a content hash — carries the usual two-writes-in-one-tick mtime blind spot. | **Accepted, no change.** The plan explicitly sanctions "path plus modification time, **or** clear the cache" — mtime is one of the two named options. The blind spot is irrelevant to the real single-process generation flow, and the D5 test bumps mtime explicitly (as a real edit does), so it is deterministic. |

## Reviewer participation

Expected population derived from `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` (`author_login`), cross-named by `.github/workflows/pr-agent.yml`: **`cuioss-review-bot`** (pr-agent), **`coderabbitai`** (coderabbit), **`sourcery-ai`** (sourcery). M = 3.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | **reviewed** | Filed the "PR Reviewer Guide 🔍" review-summary comment against the diff: "PR contains tests", "No security concerns identified", "No major issues detected". No findings to action. |
| `coderabbitai` | **rate-limited** | Published only a refusal notice: "Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in: 67 minutes." Engaged but did not review this diff. |
| `sourcery-ai` | **rate-limited** | Published only a refusal notice (review body): "you have reached your weekly rate limit of 500000 diff characters." Engaged but did not review this diff. |

**Coverage: 1 of 3.** All three comment surfaces were read (`get_comments`, `get_reviews`, `get_review_comments`); inline review threads = 0. The one reviewer that reviewed found nothing to fix, so there are no actionable review comments.

**Step 8 shortfall disclosure (fired):** "Review coverage: 1 of 3 — `cuioss-review-bot` reviewed (no findings); `coderabbitai` rate-limited (window reopens in ~67 min); `sourcery-ai` rate-limited (weekly diff-character quota)." Per the contract, rate limits are routine and NOT a merge block — the shortfall is disclosed, not waited on.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not surface a per-session token count to the running agent).
- **Wall-clock:** ≈ single continuous session; PR #1228 opened at 2026-08-14T14:25Z (source: PR `created_at`). Two full `./pw verify` runs dominated (~8–9 min each) plus two verification sub-agent dispatches.
- **Population:** this single Claude Code cloud session's own work. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which this single interactive cloud session does not share. No comparable figure is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named in "Skills loaded"; all obtained by bundle path. |
| 2 Branch | **done** — harness-assigned `claude/multi-target-generator-edge-paths-7yae0m`, kept as-is (cloud session), pushed to `origin` before any edit. |
| 3 Plan directory | **done** — `doc/plans/truthful-signals/370-multi-target-generator-edge-paths/plan.md` exists and opens with the first-instruction block (present, not repaired). |
| 4 Implement | **done** — commits carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | **done** — every `*.py`-touching commit was preceded by a clean gate; the full `./pw verify` ran green over the branch (executor path unavailable in the fresh clone, so the direct `./pw` path was used and its tool lines read clean). |
| 4 Pushed | **done** — no unpushed commit; pushed after each commit. |
| 5 Build gate | **done** — `git diff --name-only origin/main...HEAD -- '*.py'` non-empty; `./pw verify` = SUCCESS (19632 passed, 14 skipped) across quality-gate + test-compile + module-tests. |
| 6 Verification sub-agent | **done** — PASS with two informational observations; observation 1 fixed and re-verified CLEAN; observation 2 accepted with reason. |
| 7 PR cycle | **done** — PR #1228; all three comment surfaces read; no actionable comment (one reviewer clean, two rate-limited). |
| 8 Merge gate | conditions 1–3 assessed; auto-merge arming recorded to the operator (see close). GitHub access path: **GitHub MCP server**. Branch form: **harness-assigned**. |
| 8 Bridge | **done** — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | **done** — this table. |
| 9 What have we learned | see below. |

A cloud run owes no `/sync-plugin-cache` — it is a machine-local build step, not a debt this run records.

## What have we learned (Step 9)

**None proposed.** Every step of the contract executed as written and produced its named artifact. The one place the run met friction — the first `./pw verify` exceeding the 10-minute Bash timeout and moving to the background, and `uv` needing `UV_HTTP_TIMEOUT` raised — is already documented in the contract (§ Step 5: give ≥600000 ms and export `UV_HTTP_TIMEOUT=600`), so the contract already anticipated it and no change is warranted. The FAIL-first requirement was met without direct pytest by reverting production via `git stash` and re-running a `tempfile`-based harness against the real production functions, which the contract's Step 6/D7 wording already accommodates. No ambiguity, missing artifact, or environment mismatch surfaced that the contract does not already cover.

## Residue

- **Rate-limited reviewers** (`coderabbitai`, `sourcery-ai`) did not review this diff. Their windows reopen (coderabbit ~67 min; sourcery weekly). Not blocking; disclosed above. If a re-review is desired, push a trivial commit or comment `@coderabbitai review` after the window reopens.
- Nothing else open. D6 dropped with evidence; observation 2 (mtime vs content-hash) accepted with reason.

## Cost

(Recorded at close.)

## Contract check (Step 9)

(Recorded at close.)

## What have we learned (Step 9)

(Recorded at close.)

## Residue

(Recorded at close.)
