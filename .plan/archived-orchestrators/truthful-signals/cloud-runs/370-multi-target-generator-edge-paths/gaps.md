# Gaps — 370-multi-target-generator-edge-paths

**Source:** verification.md (same directory)   **Open items:** 7

All six shipped deliverables (D1–D5, D7) are implemented and non-vacuously tested; D6 was dropped
under the plan's own explicit authorisation, with the drop rationale independently re-confirmed by
constructing all four states and counting `check_bundle` entries (C1=2, C2=1, C3=1, C4=1). Nothing
below reverses a deliverable, but **two items narrow a deliverable's done-when**: G6 shows D4's
"documented behaviour is what actually happens" holds only for one of the two corrupt-input classes,
and G7 shows the reverse of D2's defect survives untouched in the sibling emitter. Three items are
medium; four are low.

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
  `unusable_target_bundles`) updating its two construction sites (`:250`, `:283`), its declaration
  (`:87`) and the three test assertions in
  `test/marketplace/targets/claude/test_equality_check.py:250,263,281`, or add a separate
  `corrupt_target_bundles` field and stop folding corrupt names into the missing list.
  Sort the combined list once (`sorted(missing + corrupt)`) if the fold is kept.
- **Done when:** the docstring names the corrupt case, the returned field's name matches what it
  contains, and a test asserts the corrupt bundle is reported under a corrupt-or-neutral name rather
  than as "missing".
- **Module/topic:** `marketplace/targets/claude/equality_check.py` (multi-target generator, Claude
  target equality gate)

## G2 — Anchor the remaining partially-anchored frontmatter fence in `body_transform_engine`

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/targets/body_transform_engine.py` — `_frontmatter_field` (`def` at `:347`,
  opening fence at `:355`, closing fence at `:357`)
- **What is wrong:** D3 brought `opencode/frontmatter.py::parse_frontmatter:122` to the sibling's
  `content.find('\n---\n', 4)` anchor (`claude/variant_emitter.py:103`). A third frontmatter reader
  inside the same component still uses `content.find('\n---', 3)` — anchored at the start of a line
  but not at the end of one, so it closes the block at any line beginning with `---` (`---`, `----`,
  `--- note`) rather than only at a whole `---` line. It also opens on `content.startswith('---')`
  rather than `'---\n'`. Confirmed by execution:
  `_frontmatter_field('---\nname: demo\ndescription: x\n--- note\nuser-invocable: true\n---\n\nbody',
  'user-invocable')` returns `''`, while the same content with the `--- note` line removed returns
  `'true'`.
- **Why it matters:** `_frontmatter_field` feeds `build_user_invocable_lookup`
  (`body_transform_engine.py:373`), whose result is the `{name}` substitution table for the
  **Transform 2 slash-command body rewrite** (`marketplace/targets/opencode/target.py:53` →
  `make_body_transformer`). A skill dropped from that lookup keeps its emitted command wrapper — that
  decision is taken separately by `opencode/emitter.py::_is_user_invocable` off the D3-fixed
  `parse_frontmatter` — but every `/skill-name` reference to it in other emitted bodies is then left
  un-rewritten, so the OpenCode output ships an invocation string that does not resolve. Same
  silent-drop class D3 fixed, one layer further out. Re-derived against the real corpus: running
  `_frontmatter_field` and `opencode.frontmatter.parse_frontmatter` over all 11 bundles'
  `SKILL.md` files yields **0 disagreements** on `user-invocable`, so this is latent, not live.
- **Fix:** change `_frontmatter_field` to open on `content.startswith('---\n')` and close on
  `content.find('\n---\n', 4)`, with the same end-of-file tolerance the two sibling parsers carry;
  add a test in `test/marketplace/targets/` asserting a field that follows a `---`-leading value line
  is still read.
- **Done when:** all three frontmatter *readers* under `marketplace/targets/`
  (`claude/variant_emitter.py::parse_frontmatter`, `opencode/frontmatter.py::parse_frontmatter`,
  `body_transform_engine.py::_frontmatter_field`) use the newline-delimited `\n---\n` anchor, and a
  test pins the behaviour for `_frontmatter_field`. (`opencode/variant_emitter.py::_inject_effort` is
  not a fourth reader — it walks a block the emitter itself just generated, matching
  `line.strip() == '---'` per line, and is already line-anchored.)
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
- **Why it matters:** a reader scanning to the end of the report — or any heading-keyed extraction
  that takes the last occurrence of a heading — sees "(Recorded at close.)" and concludes the run
  never recorded its cost, contract check, learnings or residue, the opposite of what happened. The
  four headings are the tail of the `cloud-plan-lane` report template
  (`.claude/skills/cloud-plan-lane/SKILL.md:1536-1560`), so the duplication is an unresolved template
  tail rather than an intentional second pass. It is specific to this report: a sweep for
  `(Recorded at close.)` under `doc/` and `.claude/` matches only this file (and this gaps document,
  which quotes it).
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
  seven other modules — re-derived by listing the package: top-level `body_transform_engine.py`;
  `claude/content_drift.py`, `claude/content_drift_cli.py`, `claude/source_fingerprint.py`; and
  `opencode/emitter.py`, `opencode/frontmatter.py`, `opencode/variant_emitter.py` (the `opencode/`
  block lists only `target.py` and the two JSON config files). So this extends existing drift rather
  than starting it.
- **Why it matters:** the module exists specifically to be found and reused instead of re-implemented;
  a shared-safety helper that is invisible in the component's own map is the condition under which a
  second copy gets written.
- **Fix:** add `├── fs_safety.py                  # Shared rmtree containment (is_within/safe_rmtree)`
  to the top-level block of the README tree, and while there add the other missing modules so the
  tree is exhaustive.
- **Done when:** every non-`__init__` `.py` module under `marketplace/targets/`,
  `marketplace/targets/claude/`, `marketplace/targets/opencode/` and `marketplace/targets/pr_agent/`
  appears in the README's architecture tree — the eight currently missing being `fs_safety.py`,
  `body_transform_engine.py`, `claude/content_drift.py`, `claude/content_drift_cli.py`,
  `claude/source_fingerprint.py`, `opencode/emitter.py`, `opencode/frontmatter.py` and
  `opencode/variant_emitter.py`.
- **Module/topic:** `marketplace/targets/README.md` (multi-target generator documentation)

## G6 — D4's JSON guard misses the valid-JSON-but-not-an-object case, which still crashes

- **Kind:** incomplete-guard
- **Severity:** medium
- **Where:** `marketplace/targets/claude/equality_check.py:130-134` —
  `_read_emitted_plugin_json`; contrast `:109-114` — `_check_marketplace_json`
- **What is wrong:** D4 wrapped the emitted-`plugin.json` read in
  `except json.JSONDecodeError` and nothing else, so it returns the documented diagnostic only when
  the file fails to *parse*. A file that parses to something other than a JSON object still escapes:
  `check_bundle:191-198` immediately calls `committed.get(field_name, [])` on the parsed value.
  Executed against a synthetic target tree — `run_equality_check(target_dir, [bundle_dir])` with the
  emitted `plugin.json` set to each payload in turn:

  | Emitted `plugin.json` | Result |
  |---|---|
  | `{ not json` | `passed=False`, summary `"… not valid JSON for: demo — run 'python3 marketplace/targets/generate.py …' first"` |
  | `[]` | **raises** `AttributeError: 'list' object has no attribute 'get'` |
  | `"hello"` | **raises** `AttributeError: 'str' object has no attribute 'get'` |
  | `null` | **raises** `AttributeError: 'NoneType' object has no attribute 'get'` |

  The adjacent read that the plan cited as the evidence of asymmetry — `_check_marketplace_json` —
  guards *both* halves: `except json.JSONDecodeError` at `:111` **and**
  `if not isinstance(committed, dict)` at `:113`. D4 copied only the first half, so the asymmetry the
  deliverable was written to remove survives in narrowed form.
- **Why it matters:** D4's done-when is "the documented behaviour is what actually happens", and for
  this input class it is not. `generate.py:439`'s blanket `except Exception` converts the escape into
  `error: target 'claude' failed: 'list' object has no attribute 'get'` (reproduced) — an internal
  type error in place of the documented "re-run emit" remedy, on the same gitignored build artifact
  and the same hand-corruption population D4 was accepted for. `check_bundle` is also public and is
  called directly by tests, where the traceback is unmediated.
- **Fix:** in `_read_emitted_plugin_json`, after the successful `json.loads`, add
  `if not isinstance(parsed, dict): raise CorruptEmittedPluginJsonError(...)` mirroring
  `_check_marketplace_json:113`. `CorruptEmittedPluginJsonError.__init__` currently requires a
  `json.JSONDecodeError` third argument — widen its signature to take a reason string (or make the
  exception optional and build the message from a supplied reason) so the non-object case can raise
  it. Add a test in `test/marketplace/targets/claude/test_equality_check.py` parametrised over
  `'[]'`, `'"x"'`, `'null'`, `'3'`, asserting `run_equality_check` returns
  `passed is False` and a summary containing `not valid JSON for`.
- **Done when:** `run_equality_check` returns the documented re-run-emit diagnostic — not an
  exception — for an emitted `plugin.json` whose content is `[]`, `"x"`, `null` or `3`, and the
  parametrised test passes.
- **Module/topic:** `marketplace/targets/claude/equality_check.py` (multi-target generator, Claude
  target equality gate)

## G7 — The Claude emitter never prunes a bundle removed from source (the reverse of D2)

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/targets/claude/target.py:141-160` — `ClaudeTarget.generate` (emit mode);
  contrast `marketplace/targets/opencode/emitter.py:505-506` — `emit_bundles` calling
  `_prune_stale_outputs`
- **What is wrong:** D2 gave the OpenCode emitter a top-level prune, so a component **or a whole
  bundle** removed from source leaves no emitted artifact behind. The Claude emitter has no
  equivalent: `generate` does `output_dir.mkdir(parents=True, exist_ok=True)` and then iterates
  **source** bundles, wiping and rewriting each one's own `output_dir/{bundle}/`. A bundle directory
  in `output_dir` with no surviving source bundle is never visited and never removed. Reproduced
  against the real 11-bundle corpus: `generate.py --target claude --output <tmp>` → 1165 entries;
  injecting `<tmp>/zz-removed-bundle/.claude-plugin/plugin.json` plus
  `<tmp>/zz-removed-bundle/agents/gone.md` and re-running → **both survive**, the run reports
  success, and the post-emit stamp line reads `stamped version 0.1.513 into 12 bundle plugin.json`
  against an 11-bundle source, because `generate.py:462`'s `_override_bundle_plugin_versions` walks
  the *output* tree. The phantom is also carried into `.emit-marker.json`'s `file_hashes`. D0's
  reverse sweep ("the emitter with the guard may lack something the other has") reported "no *other*
  asymmetry survives" — it missed this one, which D2 created.
- **Why it matters:** this is the plan's own Goal ("emitted output cannot drift past source") left
  half-met, and the inflated `12 bundle plugin.json` is a count that overstates reality in the
  generator's own output — the exact archetype the plan names for D6. Nothing surfaces the drift:
  the emitted `marketplace.json` is regenerated from source so it omits the phantom, and
  `run_equality_check` iterates the source bundle list so it never inspects an undeclared target
  directory. Bounded, and the bound is worth stating: the `claude-distribute` workflow builds from a
  fresh `actions/checkout`, so no published distribution can carry a phantom. The exposure is any
  machine with a persistent `target/claude/` — where the stale bundle is re-stamped with the current
  version on every build and is what `/sync-plugin-cache` mirrors.
- **Fix:** in `ClaudeTarget.generate` (emit mode), after the per-bundle loop and before the
  equality check, remove every immediate child directory of `output_dir` that is not
  `.claude-plugin` and not the name of a bundle in `bundle_dirs`, going through
  `fs_safety.safe_rmtree(child, output_dir)` so the containment invariant D1 established is not
  bypassed. Gate it on `bundles is None` exactly as `opencode/emitter.py:505` does, since a scoped
  `--bundles` emit legitimately leaves other bundles' directories in place. Add a test in
  `test/marketplace/targets/claude/test_emitter.py` (or `test_target.py`) that emits, injects
  `output_dir/zz-removed/.claude-plugin/plugin.json`, re-emits with `bundles=None`, and asserts the
  directory is gone — plus the matched control that a scoped `bundles=['demo']` emit leaves a second
  bundle's directory untouched.
- **Done when:** a full `generate.py --target claude --output <dir>` run over an unchanged source
  tree removes any `<dir>/{name}/` whose `{name}` is not a source bundle, the post-emit stamp line
  reports the source bundle count, and both halves of the scoped/unscoped control pass.
- **Module/topic:** `marketplace/targets/claude/target.py` (multi-target generator, Claude target)

## Refuted during adversarial review

No gap was refuted in full — all five original findings reproduce at HEAD. One **clause** was
refuted and rewritten in place rather than deleted:

- **G2, original "Why it matters":** *"`_frontmatter_field` feeds `build_user_invocable_lookup`,
  which decides which skills get an OpenCode command wrapper. A SKILL.md whose frontmatter carries a
  line starting with `---` before `user-invocable:` would silently lose the dual-emit wrapper."*
  **Refuted.** `build_user_invocable_lookup` has exactly one production consumer,
  `marketplace/targets/opencode/target.py:53`, which passes its result to `make_body_transformer` as
  the `{name}` table for the Transform 2 slash-command **body rewrite**
  (`body_transform_engine.py:22-27`). The dual-emit wrapper decision is taken elsewhere and by a
  different parser: `opencode/emitter.py:215` calls `_is_user_invocable(fm)` on the frontmatter
  returned by `opencode/frontmatter.py::parse_frontmatter` — the reader D3 fixed. A skill missed by
  `_frontmatter_field` therefore still gets its wrapper; what it loses is the rewrite of every
  `/skill-name` reference to it in other emitted bodies. The gap survives with the corrected
  consequence; the severity stays `low`.
