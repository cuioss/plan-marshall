# Gaps — surface-every-knob-in-marshal-json

**Source:** verification.md (same directory)   **Open items:** 3 (re-derived during adversarial review: 3 upheld, 0 refuted, 0 added)

## G1 — Materialise the two orchestrator knobs in the repo's own committed `.plan/marshal.json`

- **Kind:** incomplete-sweep
- **Severity:** high
- **Where:** `.plan/marshal.json` — the `orchestrator` block (tracked: `.gitignore:46` re-includes it with `!.plan/marshal.json`); the false premise is in `doc/plans/truthful-signals/090-surface-every-knob-in-marshal-json/report-01.md` § "D2 config-surface enumeration".
- **What is wrong:** At HEAD the committed config still reads `"orchestrator": {"auto_emit": false}` (`git show HEAD:.plan/marshal.json`), and `git log -S 'parallelization_scope' -- .plan/marshal.json` returns no commit — the key has never been written there. The run skipped this surface because the report states it is "git-ignored and absent from this clone"; it is neither. Walking `get_default_config()` against the committed file reports exactly three missing keys: `orchestrator.effort`, `orchestrator.parallelization_scope`, and `plan.phase-6-finalize.steps.default:emit-landing` (the last owed by a different plan). `config-design-principles.md:123-126` (Rule 4, surface 2 — "The self-hosting repo's own `.plan/marshal.json`") names this surface explicitly and requires migrating it "in the same change"; the rule's closing paragraph (`:137-138`) calls the meta-project's own `marshal.json` one of "the two most-forgotten surfaces". Recipe Aspect 1 (`.claude/skills/recipe-marshal-json-config-audit/SKILL.md:76`) frames the whole rule as materialisation "in `.plan/marshal.json`" — the file, not the seed dict. Re-derived independently during adversarial review by executing `get_default_config()` and walking it against the committed file: the same three keys, no more and no fewer. The third (`plan.phase-6-finalize.steps.default:emit-landing`) is confirmed to belong to a different plan — it is seeded dynamically by `_seed_finalize_steps()`, and plan 302 (`302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains`, report-01 § deliverables) introduced the step.
- **Why it matters:** The plan's goal is that an operator reading their own `marshal.json` can discover every knob. Every developer of this repo reads *this* file, and it still hides both knobs — the exact defect the plan set out to remove, left standing at the surface Rule 4 calls the most-forgotten. It also means the epic shipped a truthful-signals fix whose own dogfooding surface still carries the untruthful shape.
- **Fix:** Add `"effort": {}` and `"parallelization_scope": 1` to the `orchestrator` block of `.plan/marshal.json`, preserving the existing `auto_emit`. This is the scoped route and the one to take. Running `manage-config sync-defaults` in this repo instead is **not** equivalent and should not be substituted blind: `_cmd_sync_defaults.py:462-478` re-stamps `system.provisioned_version` and `system.config_seed_fingerprint` unconditionally, and the deep-merge also back-fills `plan.phase-6-finalize.steps.default:emit-landing` — three further committed-file changes that belong to other plans. Then add a regression guard to `test/plan-marshall/manage-config/test_config_defaults.py` — e.g. `test_committed_marshal_json_surfaces_every_orchestrator_knob`, asserting `set(committed['orchestrator']) == set(ORCHESTRATOR_KNOWN_KEYS)` using the existing `_COMMITTED_MARSHAL_PATH` (`test_config_defaults.py:1865`) — so the tracked file cannot silently fall behind the seed again. Note the two existing committed-file tests (`test_config_defaults.py:1995`, `:2016`) assert **top-level key order only**; neither reads inside a block, so neither is a content guard and adding inner keys cannot disturb them.
- **Done when:** `git show HEAD:.plan/marshal.json` shows the three-key orchestrator block; a test asserts the committed file carries every key in `ORCHESTRATOR_KNOWN_KEYS`; and that test fails if the block is reverted to `{"auto_emit": false}`.
- **Module/topic:** `plan-marshall:manage-config` — `_config_defaults.py` seed / committed `.plan/marshal.json` / `test/plan-marshall/manage-config/test_config_defaults.py`.

## G2 — Update the extension-api `marshal.json` reference to the surfaced orchestrator shape

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md:121`, `:145`, `:149` — § "Orchestrator Configuration".
- **What is wrong:** This is the canonical extension-API reference for `marshal.json`, and it still describes the block as though nothing were seeded: line 121 characterises it only as "An **empty `{}` block is legal** and behaviourally inert", line 145 says `parallelization_scope` "when unset … keeps today's hard-coded `1` default" without mentioning that `init` now seeds `1`, and the table row at line 149 labels the seeded block "`orchestrator` (empty `{}` legal)". The sibling documents in the same bundle (`manage-config/standards/api-reference.md:157`, `data-model.md:222`, `SKILL.md:1066`) were all corrected in the landed change; this one was missed because the closure grep was scoped to the `manage-config` skill while the report describes it as bundle-wide.
- **Why it matters:** An extension author consulting the canonical reference concludes the two knobs do not appear in a seeded file and writes code or docs on that basis — the same undiscoverability the plan removed elsewhere, preserved in the document extension authors are pointed at. It also makes the report's "zero surviving stale claims" closure statement narrower than it reads.
- **Fix:** In § "Orchestrator Configuration", state that `init` seeds the block with every knob at its effective default (`auto_emit: false`, `effort: {}`, `parallelization_scope: 1`), that each seeded default resolves exactly as the unset key did, and that a legacy block carrying only `auto_emit` stays valid and is back-filled by `sync-defaults`. Update the `orchestrator` table row so its parenthetical reflects the seeded shape rather than "empty `{}` legal", and rephrase the `orchestrator.parallelization_scope` paragraph so the seeded `1` is the stated default with the unset case as the legacy note.
- **Done when:** `marshal-json-reference.md` § "Orchestrator Configuration" names the three seeded keys (`auto_emit`, `effort`, `parallelization_scope`) and their effective defaults (`false`, `{}`, `1`); and `grep -rniE 'empty .\{\}. block is legal|empty .\{\}. legal|when unset the ask keeps' marketplace/bundles/plan-marshall/` returns no hit that presents the seeded orchestrator block as empty or the seeded `parallelization_scope` as absent.
- **Module/topic:** `plan-marshall:extension-api` — `standards/marshal-json-reference.md`.

## G3 — Retire the stale "PLAN-48 reserves `auto_emit`" statements

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md:123` and `:155`; `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md:88`; `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py:596`.
- **What is wrong:** All four sites describe `orchestrator.auto_emit` as a *future*, *reserved* knob that "PLAN-48 adds" to the whitelist. `auto_emit` has been implemented, validated, whitelisted and seeded since `1fad0868` (#996) — it is in `ORCHESTRATOR_SCALAR_FIELDS`, in `ORCHESTRATOR_KNOWN_KEYS`, and in `DEFAULT_ORCHESTRATOR`. **Not caused by this plan** (the drift predates it); recorded here because it sits in the same block's documentation and was inside the sweep D4/D3 walked past.
- **Why it matters:** A reader of the extension-API reference or the effort-roles registry is told a shipped knob does not exist yet, and may re-implement or avoid it. It is the same "documentation that makes the tree look other than it is" archetype this epic targets.
- **Fix:** Delete the two "Reserved extension slot (PLAN-48)" blocks and rewrite the `marshal-json-reference.md:123` sentence to describe `auto_emit` as a shipped scalar knob on the same verb; update `effort-roles.md:88` to name both scalar knobs as present; change the `manage-config.py:596` comment to "the provisioning scalars (`parallelization_scope`, `auto_emit`)".
- **Done when:** `grep -rn "PLAN-48" marketplace/` returns no hit that describes `auto_emit` as reserved or future.
- **Module/topic:** `plan-marshall:extension-api` / `plan-marshall:plan-marshall` (effort-roles) / `plan-marshall:manage-config` — orchestrator-block documentation.

## Refuted during adversarial review

**None.** All three gaps were re-checked against the tree by an independent agent and stand. What was
tested and how is recorded in `verification.md` § "Adversarial review"; the corrections applied above
are citation-precision and fix-actionability fixes, not reversals. G1's `high` severity was
re-examined against the severity rubric (`high` requires wrong behaviour, a shipped false signal, or a
guard that passes against the defect it names) and **upheld**: no behaviour is wrong, but the run
shipped a false factual premise (".plan/marshal.json is git-ignored and absent from this clone") and
no guard covers the committed file's block contents. G3's `low` severity was re-examined and
**upheld** — the four PLAN-48 sites are genuinely stale, but `auto_emit` is a key this plan did not
newly materialise, so the drift sits outside the plan's declared documentation scope and is recorded
as adjacent evidence rather than as a debt this plan owes.
