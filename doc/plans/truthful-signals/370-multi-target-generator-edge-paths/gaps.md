# Gaps — 370-multi-target-generator-edge-paths

**Source:** verification.md (same directory)   **Open items:** 5

All six shipped deliverables (D1–D5, D7) are implemented, correct, and non-vacuously tested; D6 was
dropped under the plan's own explicit authorisation, with the drop rationale independently
re-confirmed. Nothing below reverses a deliverable. One item is medium (a docstring a reader would
act on plus a mis-named result field); four are low.

## G1 — Document and name the corrupt-emitted-plugin.json outcome in `run_equality_check`

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/targets/claude/equality_check.py:222` — `run_equality_check` (docstring),
  and `:283` — `missing_target_bundles=sorted(missing) + sorted(corrupt)`; field declared at `:87`
- **What is wrong:** D4 added a third failure mode (an emitted `plugin.json` that exists but is not
  valid JSON), but `run_equality_check`'s docstring still enumerates only "When `target_dir` itself,
  a per-bundle emitted plugin.json, or the top-level marketplace.json is **missing or drifts**". The
  corrupt bundles are then returned inside `EqualityResult.missing_target_bundles`, a field whose
  name asserts they are absent when they are present-but-unreadable. The concatenation
  `sorted(missing) + sorted(corrupt)` is also not globally sorted, so the list is unsorted whenever
  both buckets are non-empty (e.g. `missing=['z']`, `corrupt=['a']` → `['z','a']`).
- **Why it matters:** in an epic about truthful signals, a caller reading
  `missing_target_bundles` is told a file is missing when it is corrupt — a different diagnosis with
  a different manual remedy — and the docstring a maintainer reads to learn what the engine converts
  into a diagnostic omits the case entirely. Today only tests read the field, so no shipped consumer
  is misled yet; the next consumer would be.
- **Fix:** extend the `run_equality_check` docstring to name the corrupt-emitted-`plugin.json` case
  and state that it is treated exactly like a missing one; either rename
  `EqualityResult.missing_target_bundles` to something outcome-neutral (e.g.
  `unusable_target_bundles`) updating its three call sites and the three test assertions, or add a
  separate `corrupt_target_bundles` field and stop folding corrupt names into the missing list.
  Sort the combined list once (`sorted(missing + corrupt)`) if the fold is kept.
- **Done when:** the docstring names the corrupt case, the returned field's name matches what it
  contains, and a test asserts the corrupt bundle is reported under a corrupt-or-neutral name rather
  than as "missing".
- **Module/topic:** `marketplace/targets/claude/equality_check.py` (multi-target generator, Claude
  target equality gate)

## G2 — Anchor the remaining partially-anchored frontmatter fence in `body_transform_engine`

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/targets/body_transform_engine.py:356` — `_frontmatter_field`
- **What is wrong:** D3 brought `opencode/frontmatter.py::parse_frontmatter` to the sibling's
  `content.find('\n---\n', 4)` anchor. A third frontmatter reader inside the same component still
  uses `content.find('\n---', 3)` — anchored at the start of a line but not at the end of one, so it
  closes the block at any line beginning with `---` (`---`, `----`, `--- note`) rather than only at
  a whole `---` line. It also opens on `content.startswith('---')` rather than `'---\n'`.
- **Why it matters:** `_frontmatter_field` feeds `build_user_invocable_lookup`, which decides which
  skills get an OpenCode command wrapper. A SKILL.md whose frontmatter carries a line starting with
  `---` before `user-invocable:` would silently lose the dual-emit wrapper — the same silent-drop
  class D3 fixed. No such SKILL.md exists in the corpus today, so this is latent, not live.
- **Fix:** change `_frontmatter_field` to open on `content.startswith('---\n')` and close on
  `content.find('\n---\n', 4)`, with the same end-of-file tolerance the two sibling parsers carry;
  add a test in `test/marketplace/targets/` asserting a field that follows a `---`-leading value line
  is still read.
- **Done when:** all three frontmatter readers under `marketplace/targets/` use the newline-delimited
  `\n---\n` anchor, and a test pins the behaviour for `_frontmatter_field`.
- **Module/topic:** `marketplace/targets/body_transform_engine.py` (multi-target generator, shared
  body transform)

## G3 — Give the OpenCode emitter the same source-tree refusal the Claude emitter now has

- **Kind:** omission
- **Severity:** low
- **Where:** `marketplace/targets/opencode/emitter.py:438` — `emit_bundles`, and `:135` —
  `_prune_stale_outputs`
- **What is wrong:** D1 gave `claude/emitter.py::emit_bundle_verbatim` an explicit refusal when the
  resolved destination lies inside the source tree. `emit_bundles` has no equivalent check, and D2
  gave it a new destructive path: `_prune_stale_outputs` unlinks every file under
  `{output_dir}/skill`, `{output_dir}/agent` and `{output_dir}/command` that was not written this
  run, then `rmdir`s the emptied directories. `safe_rmtree` only constrains the target to be inside
  `output_dir`; nothing constrains `output_dir` itself. D0's reverse sweep concluded "no other
  asymmetry survives", but this one was created by D1 and D2 in the same PR.
- **Why it matters:** the plan warned explicitly against solving one emitter's drift by giving it the
  other's hazard. No reachable harm exists in this repository — the singular names `skill/`, `agent/`
  and `command/` collide with nothing in `marketplace/bundles/` (which uses the plural forms), so a
  mistyped `--output` currently creates junk rather than destroying source — but the containment
  invariant is asserted in one emitter and merely absent in the other.
- **Fix:** in `emit_bundles`, before any write, refuse when `output_dir` resolves inside
  `marketplace_dir` (reuse `fs_safety.is_within`, raising the same shape of `ValueError` as
  `emit_bundle_verbatim`); add the matched control to
  `test/marketplace/targets/opencode/test_emitter.py` — an `output_dir` inside the source tree is
  refused, and a legitimate one still emits and prunes.
- **Done when:** `emit_bundles(marketplace_dir, marketplace_dir, config_dir)` raises before writing
  or unlinking anything, and both halves of the control pass.
- **Module/topic:** `marketplace/targets/opencode/emitter.py` (multi-target generator, OpenCode
  target)

## G4 — Remove the duplicated placeholder sections at the end of report-01.md

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/370-multi-target-generator-edge-paths/report-01.md` — the
  four trailing headings "## Cost", "## Contract check (Step 9)", "## What have we learned (Step 9)"
  and "## Residue", each containing only "(Recorded at close.)"
- **What is wrong:** the report carries filled versions of all four sections earlier in the file and
  then repeats each heading at the end with an unresolved template placeholder. The document has two
  "Cost" sections, two "Contract check (Step 9)" sections, two "What have we learned" sections and
  two "Residue" sections, the second of each empty.
- **Why it matters:** a reader (or an archived-plan retrospective sweep that reads the last
  occurrence of a heading) sees "(Recorded at close.)" and concludes the run never recorded its cost,
  contract check, learnings or residue — the opposite of what happened.
- **Fix:** delete the four trailing placeholder sections, keeping the filled ones.
- **Done when:** each of the four headings occurs exactly once in `report-01.md` and carries content.
- **Module/topic:** `doc/plans/truthful-signals/370-multi-target-generator-edge-paths/` (cloud plan
  lane run record)

## G5 — List `fs_safety.py` in the targets architecture tree

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/targets/README.md:9-26` — the "## Architecture" tree
- **What is wrong:** D1 introduced `marketplace/targets/fs_safety.py` as the deliberate single home
  for the containment check ("so the two emitters cannot drift apart with two subtly-different
  copies of it"). The README's architecture tree lists the other top-level modules
  (`__init__.py`, `base.py`, `generate.py`) but not this one. The tree is already incomplete for
  other modules (`body_transform_engine.py`, `source_fingerprint.py`, `content_drift.py`,
  `opencode/emitter.py`, `opencode/frontmatter.py`, `opencode/variant_emitter.py`), so this extends
  existing drift rather than starting it.
- **Why it matters:** the module exists specifically to be found and reused instead of re-implemented;
  a shared-safety helper that is invisible in the component's own map is the condition under which a
  second copy gets written.
- **Fix:** add `├── fs_safety.py                  # Shared rmtree containment (is_within/safe_rmtree)`
  to the top-level block of the README tree, and while there add the other missing modules so the
  tree is exhaustive.
- **Done when:** every `.py` module directly under `marketplace/targets/` and under
  `marketplace/targets/opencode/` appears in the README's architecture tree.
- **Module/topic:** `marketplace/targets/README.md` (multi-target generator documentation)
