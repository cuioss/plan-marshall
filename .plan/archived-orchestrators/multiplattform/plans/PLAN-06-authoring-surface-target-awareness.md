# PLAN-06: The pm-plugin-development authoring surface is target-aware and rule-pack-declared

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Ingested from `archive/original-staged-specs/060-authoring-surface-target-awareness.md` and
> re-grounded against HEAD `2cd1a19c`.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

The `pm-plugin-development` bundle authors, validates, and fixes components — and much of that
surface is Claude-only or undeclared: the creator's generator emits Claude frontmatter with no target
resolution while the doctor's fixer is target-aware; validators and fix payloads carry Claude
schema/tool/model enums outside the declared rule-pack; the flagship frontmatter standard states
Claude parser rules, mounts, and settings paths as THE authoring standard; layout and settings
literals bypass the layout helpers; permission grammar is rendered in doc bodies; and an
outline-classification predicate table is written as Claude paths and keys. Make an author on any
registered target get correct frontmatter generation, validation, and fixes, with every
Claude-specific rule either target-resolved or declared in the rule-pack.

## Deliverables

1. **D1 — Target-aware generation and validation.** `cmd_generate.py` resolves the target as `_cmd_apply.py` does; `cmd_validate.py`'s format/field/tool enums become per-target (or rule-pack-declared) and its skill-field enum is reconciled with `frontmatter-standards.md` and `fix-templates.json` (one schema, three surfaces agreeing); `fix-templates.json` drops its dead entries and its live payloads become target-keyed; `apply_array_syntax_fix` gates on the resolved target.
   *Done when:* generation/validation/fix tests pass per target (red-first for the new behaviour); the dead template entries are gone; the three-surface schema disagreement is gone.
2. **D2 — `frontmatter-standards.md` split.** The target-agnostic field semantics stay; the Claude parser rules, tool set, model aliases, color enum, mount paths, and settings-permission sections move to (or are marked as) Claude target material, with the doctor's `_analyze_skill_mode.py` pointer still resolving.
   *Done when:* the document separates agnostic semantics from per-target format, and the doctor passes.
3. **D3 — Rule-pack declaration closed.** `rule-provenance.md` names the undeclared members (`tool-coverage.md`'s tool vocabulary — single-sourced with `_KNOWN_TOOLS` as data — `askuserquestion-reachability`, `agent-glob-resolver-workaround`, the bash-chain / shell-substitution / tmp-redirect rules); `_BUILD_OUTPUT_PREFIXES` reads the prefix from the target's own mapping data instead of a core-owned table; `doctor-agents.md` stops stating the `target/claude/` literal; `resolve_runtime_target`'s fallback consumes the single default PLAN-01 established.
   *Done when:* the rule-pack row covers every rule keyed on Claude tools/runtime facts (re-derive by sweeping analyzers for tool names), and no core-owned per-target prefix table remains.
4. **D4 — Layout and store literals routed.** `_dep_index.py` project scope through `get_project_skill_roots()` (duplicate helper deleted; the orphan `--scope global` flag fixed or removed; `plugin-cache` CLI vocabulary renamed target-neutrally with an alias); `extension.py` Axis-D prefix supplied by layout resolution; `plugin-doctor` SKILL/commands-guide discovery prose names the layout op; `_plugin_pin_trap.py` consumes normalized store observations from a runtime query while its oracle stays put; the `lspServers` placeholder section is declared Claude-target material.
   *Done when:* no `.claude` literal or segment-wise construction remains in the bundle outside declared Claude-target material, verified by sweep.
5. **D5 — Settings/permission prose normalized.** The `ext-outline-workflow` human-gated classification keeps its intent but takes its predicate table from a per-target runtime query (change-types restatement folded); `plugin-task-plan`'s hook-semantics rationale reworded to the observable constraint; the permission-grammar doc twins (the §M4 list) state intent or are declared Claude examples; `harness` terminology replaced per principles §7.
   *Done when:* the §M4-listed sites are reworded/routed and a `harness` sweep of the bundle is clean.

⚠️ **Split guard fired and was resolved as proceed-unsplit.** Five deliverables is at the scope-bloat
threshold. The rationale, recorded as an epic decision: D1–D5 share one authoring toolchain and one
`frontmatter-standards.md` ↔ `cmd_validate.py` ↔ `fix-templates.json` three-surface schema; splitting
them would leave the three surfaces disagreeing across two PRs, which is the exact defect D1 exists to
close. If the run finds D4/D5 separable in practice, report it rather than absorbing the growth.

## Out of Scope

- **`askuserquestion-patterns.md` scoping** — a §D target-specific-component candidate blocked on the file-level `targets:` extension. **PLAN-11 builds that prerequisite**; do not invent a second scoping mechanism here.
- **The doctor's frontmatter validation of `targets:`** — PLAN-02 D4 owns it (landed).
- **plan-marshall-bundle surfaces** — PLAN-07's surface.
- **`ext-triage-plugin/standards/pr-comment-disposition.md`** — carved out of this surface and owned by PLAN-05, so its byte-identical escalation-block set stays whole.

## Claim Labels

- OBSERVED: `cmd_generate.py` has no target resolution while `_cmd_apply.py` is target-aware — re-derived at HEAD `2cd1a19c`: `cmd_generate.py` emits raw `model:` passthrough and comma-joined `tools` with **zero** calls to `resolve_runtime_target`; `_cmd_apply.py` has **3** hits, branching on `resolve_runtime_target() == 'opencode'` to emit `mode: subagent` / `model: anthropic/...`.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb and the asymmetry is exact: cmd_generate.py carries ZERO target-resolution references while _cmd_apply.py carries THREE. The claim's shape holds unchanged.
- OBSERVED: `fix-templates.json`'s `missing-frontmatter` / `array-syntax-tools` entries are ignored by their consumer — read at `_cmd_apply.py::apply_missing_frontmatter` and `::apply_array_syntax_fix`: both take a `templates: dict` parameter and **never reference it**, hardcoding a Claude-only inline frontmatter builder and a hardcoded regex instead. Verify the ignore before deleting.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: The FILE MOVED and the declaration pointed at a path that no longer exists; corrected in the same act. fix-templates.json is now at plugin-doctor/ASSETS/, not plugin-doctor/scripts/. The claim's substance is intact - _cmd_apply.py still carries the two named entries - but the Expected Surface entry was a PHANTOM, so the disjointness gate has been comparing a path with nothing behind it. ⛔ This is the THIRD instance of that class this cleanup found (after PLAN-12's doubled manage-metrics segment and cmd_validate.py below), which is what makes the surface parser's missing filesystem check a pattern rather than an anecdote.
- OBSERVED: the three-surface skill-field enum disagreement is real — `cmd_validate.py::validate_frontmatter_skill` permits only `name`, `description`, `user-invocable` and explicitly forbids `allowed-tools` via `prohibited_fields`, while `fix-templates.json`'s `missing-frontmatter.skill` template **emits** `allowed-tools: Read, Glob, Grep`. The fixer would produce output the validator flags as an error.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: The FILE MOVED SKILLS and the declaration pointed at a path that no longer exists; corrected in the same act. cmd_validate.py is now at plugin-create/scripts/, NOT plugin-doctor/scripts/. ⭐ That relocation is materially good news for D1: cmd_validate.py now sits in the SAME SKILL as cmd_generate.py, so D1's two halves - make generation target-aware, make validation target-aware - are co-located instead of split across skills. ⚠️ The three-surface enum claim itself was NOT re-derived, because its subject file was unreadable at the declared path until this correction; the plan must re-read validate_frontmatter_skill at the new location before trusting the permitted-field list.
- OBSERVED: `_BUILD_OUTPUT_PREFIXES` is a core-owned per-target table with a Claude fallback — read at `_analyze_markdown.py`: a hardcoded `{'claude': 'target/claude/', 'opencode': 'target/opencode/'}` dict defined inline in the doctor engine, not sourced from any target's `mapping.json`, with `_build_output_prefix()` falling back to `'target/claude/'` for an unrecognized target. Precisely the principles §6 anti-pattern.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb: _analyze_markdown.py:318 defines _BUILD_OUTPUT_PREFIXES and :329 reads it as _BUILD_OUTPUT_PREFIXES.get(resolve_runtime_target(), 'target/claude/') - a per-target table with a hardcoded Claude fallback, exactly the shape claimed.
- OBSERVED, **narrowed at ingestion**: the rule-pack declaration gap is real but **smaller than the original spec implies**. `rule-provenance.md` § "Engine / Claude rule-pack split" already exists and is reasonably mature; its declared Members row lists `_KNOWN_TOOLS`-based tool validation, comma-vs-array `tools:` syntax, `agent-task-tool-prohibited`, `agent-skill-tool-visibility`, `hardcoded-model-on-canonical`, and the build-output-directory exemption. `askuserquestion-reachability` and `agent-glob-resolver-workaround` are **absent** from that set. D3's actual remaining work is adding the missing rows, not inventing the split.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Not re-derived this pass and stated rather than assumed. The claim was NARROWED at ingestion against rule-provenance.md, and that file changed FOUR times across the epic (the last re-grounding at 6884e932 confirmed the narrowed reading held then). I did not re-read it at 1c4e6febb. ⛔ Do not read the other nine PLAN-06 re-groundings in this pass as covering this one - they addressed different files. The narrowed reading is the one to start from, and it needs a fresh read of rule-provenance.md's own declaration section before D-work relies on it.
- OBSERVED: `_dep_index.py` still bypasses the layout op — read at `_dep_index.py:33,673`: `CLAUDE_DIR='.claude'` and `get_base_path('project')` building `Path.cwd()/CLAUDE_DIR` directly, while the sibling scope two lines above uses `get_bundle_cache_roots()`.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Substance holds at 1c4e6febb, LINE EVIDENCE stale. _dep_index.py still bypasses the layout op: CLAUDE_DIR = '.claude' and a segment-wise Path.cwd() / CLAUDE_DIR construction are both present. ⚠️ The claim cites :33 and :673; the real positions are :34 (CLAUDE_DIR), :760 (get_base_path) and :803 (the project construction). Locate by SYMBOL - this file has drifted since staging.
- OBSERVED: the plugin-doctor analyzers still carry segment-wise `.claude/skills` anchors — read at `_analyze_self_declared_rule_compliance.py:308-327`, where `_claude_skills_root` composes `marketplace_root.parent.parent / '.claude' / 'skills'` instead of calling `get_project_skill_roots()`. ⚠️ D4's bundle-wide done-condition is what reaches these files; they are **not** enumerated in D4's deliverable text. Confirm the sweep actually reaches all seven anchors, and report if it does not.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb: _analyze_self_declared_rule_compliance.py:315 still builds marketplace_root.parent.parent / '.claude' / 'skills' segment-wise. The claim cites 308-3xx and the real line is :315 - a small drift, same construction. The anchors are still there.
- HYPOTHESIS: the seven analyzer anchors are the complete segment-wise `.claude` set in the bundle — confirm/refute by a segment-wise probe over both quote styles across `pm-plugin-development/**` (verify-at-outline). **Not re-derived at ingestion**; the audit's own zero-finding footer claims completeness, which is a lead, not a settlement.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Not settled, and the probe I ran shows why it needs the plan's own. The claim asserts SEVEN analyzer anchors are the complete segment-wise .claude set in the bundle. A file-level probe over plugin-doctor/scripts/ alone returns EIGHT files carrying the literal - but a FILE count is not an ANCHOR count (one file can hold several, and a literal is not necessarily a segment-wise construction), so 8-vs-7 neither confirms nor refutes. ⛔ The discriminating probe is segment-wise construction across the WHOLE bundle, which is the claim's own stated test and is D-work. Recording the divergence so the plan starts from a real signal rather than from seven.
- HYPOTHESIS: `--scope global` crashes in `_dep_index.get_base_path` — confirm/refute by running it; a red-first test pins the fix (verify-at-outline). **Not reproduced at ingestion** — the script was not executed.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: The PREMISE is corroborated and the CRASH is not, and the two are kept apart deliberately. _dep_index.get_base_path's own docstring at :760 declares its accepted set as 'auto', 'marketplace', 'plugin-cache', 'project' - 'global' is NOT among them, so the claim's premise that the scope is unsupported holds by reading. But the claim's stated test is 'confirm/refute by RUNNING it', and I did not run it: whether an unsupported scope crashes, returns a wrong path, or raises the documented FileNotFoundError is a behavioural question a read cannot settle, and the difference decides what the red-first test asserts. ⛔ Do not upgrade this to corroborated on the docstring alone.
- HYPOTHESIS: the runtime queries D4/D5 need fit existing operations — confirm/refute at `platform-runtime/standards/contract.md` (verify-at-outline). A needed addition is **recorded and made minimally**, never silent.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Whether the runtime queries D4/D5 need FIT existing operations is a design question no read of contract.md settles - the contract says which operations exist, not whether these queries express within them. ⚠️ And the operation set has MOVED substantially since this claim was written: PLAN-08 added seven permission_* operations and PLAN-09 added the decline vocabulary and single-sourced registration, so D4/D5 would now be measured against a materially larger contract than at staging. That makes the fit MORE likely, not less - but likelihood is not a verdict. Verify-at-outline work.

## Expected Surface

The named anchors below are the sites this plan's deliverables already identify; the trailing glob
bullets carry the breadth the sweeps reach. Re-derive the full set at outline.

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-create/scripts/cmd_generate.py` — D1
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-create/scripts/cmd_validate.py` — D1. ⚠️ **MOVED SINCE STAGING**: this file used to live under `plugin-doctor/scripts/` and the declaration pointed there until the 2026-09-06 re-grounding. It is now in a DIFFERENT SKILL (`plugin-create`), which also owns `cmd_generate.py` — so D1's two halves are now co-located.
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_cmd_apply.py` — D1
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/assets/fix-templates.json` — D1. ⚠️ **MOVED SINCE STAGING**: `scripts/` → `assets/`; the declaration pointed at the old path until the 2026-09-06 re-grounding.
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md` — D2
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — D3
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_markdown.py` — D3
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py` — D4
- OBSERVED: `marketplace/bundles/pm-plugin-development/**` — the rest of the §M3/§M4-named skills and scripts, with one carve-out stated under Dependencies below
- OBSERVED: `test/pm-plugin-development/**`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/**` — only if D4/D5's runtime queries need a schema addition; recorded, made minimally (verify-at-outline)

## Dependencies and Sequencing

⛔ **The one carve-out inside this plan's own tree.**
`marketplace/bundles/pm-plugin-development/skills/ext-triage-plugin/standards/pr-comment-disposition.md`
belongs to **PLAN-05**, not to this plan, so PLAN-05's byte-identical escalation-block set across all
seven ext-triage skills stays whole. Everything else under `pm-plugin-development/**` is this plan's.
Widening across that boundary is a partition defect: halt and report.

- Depends on: PLAN-01 (landed) — D3's default-target fallback consumes the single source it established.
- Overlaps with: **PLAN-07** — both conditionally touch `platform-runtime/standards/contract.md`. ⛔ Not concurrent, either order.
- Overlaps with: **PLAN-02** (landed, plugin-doctor) and **PLAN-03** (landed, `scan-marketplace-inventory.py` sits beside `_dep_index.py`). Both already landed, so no live collision.
- Overlaps with: **PLAN-11** — PLAN-11 builds the file-level `targets:` extension this plan's Out of Scope depends on. PLAN-11 does not need to land first; this plan simply must not build a second mechanism.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-05 (the one shared file is carved out), PLAN-13 (fully disjoint).

## Verification

- The full verify gate; red-first tests for D1 and the `--scope global` fix.
- The bundle-wide `.claude` / `harness` sweeps from D4/D5, re-run at verification time.
- A pre-PR verification pass **cold-reads** the split `frontmatter-standards.md` and reports whether a third-target author can tell which sections bind them — the split failed if not.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-06-authoring-surface-target-awareness.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. In particular it does **not** edit
`../reference/coupling-inventory.md`: coupling rows are retired by the orchestrator from the
landing, per the epic decision recorded in `epic.md`.
