# PLAN-07: plan-marshall states runtime facts through the runtime, and single sources stay single

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Ingested from `archive/original-staged-specs/070-runtime-fact-prose-and-single-sources.md` and
> re-grounded against HEAD `2cd1a19c`.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim; the hit list is the work list.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

The plan-marshall bundle carries Claude runtime facts, layout literals, and duplicated single-source
tables far beyond the inventory's registered sites: hook events, Bash-tool ceilings, the `<usage>`
envelope, and `.claude` layout appear as universal facts in general standards and scripts; the effort
level→model table is restated on several bundle surfaces against its build-target single source;
`/marshall-steward` is emitted as a remediation string from over a dozen general scripts (and
persisted into `.gitignore`); `CLAUDE.md` is a whole steward sub-operation's only write target; and
several live code sites construct Claude layout outside the layout helpers. Source runtime facts from
`platform-runtime` or state them as per-target notes; give the effort table, command forms, and
agent-instructions filename exactly one source each.

## Deliverables

1. **D1 — Layout code routed.** `configurable_contract.py::resolve_step_doc_path` through `get_project_skill_roots()`; the executor template's `_newest_cache_scripts_dir` recovery root through the runtime-resolved cache roots; `marketplace_paths.get_base_path`'s `global`/`project` scopes runtime-routed.
   *Done when:* the segment-wise/literal constructions are gone from the three sites, pinned by tests including a non-default-root case.
2. **D2 — `manage-terminal-title` split.** The channel-delivery/hook-event content (architecture standard sections, SKILL mapping table, script comments) moves to `platform-runtime` documentation; the composer skill keeps only the target-neutral contract its frontmatter claims.
   *Done when:* the skill's body no longer contradicts its self-description (no hook-event or channel vocabulary outside platform-runtime), and the displaced content is reachable from the runtime's docs.
3. **D3 — Hook/session/ceiling facts sourced.** The §M5/§M6 prose sites (manage-status build-busy contract, orchestration-model channel claim, manage-architecture search justification, session-id mechanism mentions, `_invariants.py`, worktree-handling rationale, Bash-ceiling and call-shape statements, `<usage>` mentions, phase-3 harness-config routing rule, q-gate validators, extension-api/manifest/config contract prose, coverage/wizard `.claude` prose, docstring target enumerations) state intent, cite the runtime op or single constant, or carry an explicit per-target conditional.
   *Done when:* a bundle sweep for hook-event names, `.claude` literals, and hard-coded ceiling values outside platform-runtime and declared Claude-target material is clean.
4. **D4 — Effort table single-sourced.** The §M7 surfaces reference the build-target source instead of restating it; `CLAUDE_CODE_SUBAGENT_MODEL` prose becomes a Claude-target note; the `LEVEL_TABLE`/`model_map` cross-target import direction is recorded as a proposal (the fix is `marketplace/targets` work outside this plan's surface).
   *Done when:* no bundle file carries the level→model rows; each cites the single source.
5. **D5 — Command form and agent-instructions file.** The `/marshall-steward` (and `/sync-plugin-cache`) emission sites consume one command-form lookup; `gitignore_setup.py` persists a neutral comment; `architecture-setup.md`'s write target and `determine_mode.py`'s rule-file lists resolve the agent-instructions filename per target (fixing the `['CLAUDE.md']`-only asymmetry); "CLAUDE.md § …" authority citations name the rule's owner; the steward `--settings` literals route through the permission skills' own semantic ops.
   **FOLDED IN (PLAN-19 landing, F1 root cause) — the generator command form in the agent-instructions files.** `AGENTS.md:74` and `CLAUDE.md:115` both instruct the bare `uv run python marketplace/targets/generate.py --target {name} --output {dir}`. That form fails whenever `uv` is not globally installed — the normal state here, because pyprojectx provisions it into `.pyprojectx/` (`[tool.pyprojectx.main] requirements = ["uv"]`) rather than onto `$PATH`. The working invocation is the wrapper alias (`./pw generate`, `generate-claude`, `generate-opencode`, defined at `pyproject.toml:103-106`). ⚠️ **This is not hypothetical: an agent followed the documented form literally, concluded the generator was unrunnable, and skipped a required verification item** (PLAN-19's F1, since retracted). Same defect class as the rest of D5 — a command form stated in prose that diverges from the one that works — and the same remedy: one source, and it is the wrapper.
   *Done when:* the emission sites share one lookup; the asymmetry has a red-first test; the steward surfaces contain no settings-path literal; **and neither `AGENTS.md` nor `CLAUDE.md` instructs a generator invocation that fails on a host without a global `uv`.**

⚠️ **Split guard fired and was resolved as proceed-unsplit.** Five deliverables. Rationale, recorded as
an epic decision: D1–D5 are all "one bundle, one sweep" work whose done-conditions are bundle-wide
sweeps (D3, D4, D5 each end in a sweep over the same tree). Splitting would run the same sweep three
times against a moving surface and leave the intermediate states half-clean. If the run finds D1
separable from D2–D5 in practice, report it rather than absorbing growth.

## Out of Scope

- **The steward terminal-title and enforcement-hook wizard splits** — §D/§M6 target-specific candidates. **PLAN-11 owns the split**; this plan fixes their `--settings` literals only.
- **Renaming the persisted `harness_cancellation` enum** — a data-migration cost for a terminology gain; recorded as a deliberate non-migration.
- **`trusted-domains` seed policy** — whether `code.claude.com` stays a full-trust default is an operator policy question; this plan records the proposal, never decides it.
- **pm-plugin-development and cross-bundle prose** — PLAN-06's and PLAN-12's surfaces.
- **`platform-runtime/SKILL.md`'s 24-operation no-op table** — PLAN-09's surface (WS-01), not this plan's, even though it is the same coupling class.

## Claim Labels

- ⚙️ **RE-SCOPED at the 2026-09-05 re-grounding — this site is CLOSED and the claim's original assertion is REFUTED.** It previously read that `configurable_contract.py::resolve_step_doc_path` *still constructs* the segment-wise `.claude/skills` path. Re-derived at `565d4ade7`: the literal is **gone from the file**. `resolve_step_doc_path` now resolves through the target's declared project-local skill roots, and the only surviving mention is a docstring line (:113) whose own words are *"which is why that spelling is no longer written here"*. ⛔ **Do not re-open this as a D1 target** — somebody closed it between ingestion and now. What remains for D1 is the REST of the M5 site set, not this file.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e and the 2026-09-05 re-scope HOLDS unchanged: configurable_contract.py carries exactly ONE .claude mention and it is the docstring at :113 whose own words are 'which is why that spelling is no longer written here'. The segment-wise construction is still gone and the site is still CLOSED. ⛔ Do not re-open this as a D1 target. ⚠️ RE-STAMP CORRECTION: an earlier call in this same cleanup pass wrote terminal-title evidence onto this index by mis-mapping the claim ordinals; this verdict replaces that misplaced text with the correct re-derivation for THIS claim.
- OBSERVED, **softened at ingestion**: `manage-terminal-title` does carry Claude hook-event names (`Stop`, `Notification`, `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, `PostToolUse:Bash`) in a skill whose line 52 states "The composer knows **no** hook-event vocabulary" — so the self-contradiction is real. **But each mention is explicitly attributed** to `claude_runtime._claude_event_to_process_state(...)` as "the CALLER's half, deliberately not owned here." The original spec's "resident Claude channel specification" framing overstates it. Scope D2 to the attributed-but-resident content, not to an unattributed specification. `standards/terminal-title-architecture.md` was **not** independently read at ingestion — read it before scoping D2, since it carries 8 `claude_runtime` hits and may or may not be the fuller specification the original framing describes.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e and the claim holds EXACTLY, including its line citation. manage-terminal-title/SKILL.md line 52 still reads 'The composer knows **no** hook-event vocabulary' - the same line the claim cites - while standards/terminal-title-architecture.md still carries 10 hits of the Claude hook-event names (Stop, Notification, PreToolUse:AskUserQuestion, PreToolUse:Bash, PostToolUse:Bash). ⚠️ Notable because terminal-title-architecture.md is the ONE named file in this spec that moved since 1c4e6febb (PLAN-11 edited it): the file changed and the self-contradiction survived the edit. Checked, not assumed.
- ⚙️ **RE-SCOPED at the 2026-09-05 re-grounding — the figure "three" is REFUTED and the set has MOVED.** Re-derived at `565d4ade7` by the segment-wise probe the claim itself prescribes. `configurable_contract.py` has **dropped out** of the set entirely (see the first claim). The live segment-wise CONSTRUCTION sites outside the helpers and outside already-owned inventory rows are: `marshall-steward/scripts/bootstrap_plugin.py` (**two** sites — `:163` `Path.home() / '.claude' / 'plugins' / 'cache'` and `:205` `str(home / '.claude' / 'skills')`) and `pm-plugin-development/skills/plan-marshall-plugin/extension.py:368` (`[('.claude', 'pm-plugin-development')]`). ⛔ **Sites deliberately EXCLUDED, each for a stated reason, so the next reader does not re-add them**: `marketplace_paths.py` is the helper itself; `generate_executor.py` and `_dep_index.py` carry their own coupling-inventory rows; `permission_doctor.py` is declared rule-pack material as of PLAN-14; the plugin-doctor analyzers mention the literal as analyzer subject matter. The hit list above is the work list.
  - verdict: contradicted | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: yes | evidence: THE SET HAS MOVED AGAIN, and this time one of its own epic siblings closed a member. The 2026-09-05 re-scope refuted the figure three and named the live segment-wise construction sites as bootstrap_plugin.py :163 and :205 plus plan-marshall-plugin/extension.py:368. Re-derived at 8fc353b6e: bootstrap_plugin.py still carries BOTH sites at the SAME line numbers (:163 Path.home()/'.claude'/'plugins'/'cache', :205 str(home/'.claude'/'skills')), but extension.py:368 is GONE - PLAN-06 (#1456) touched that file and the [('.claude','pm-plugin-development')] construction no longer exists. What remains in extension.py are prose and docstring mentions at :19 :157 :309 :317 :319 declaring the Axis-D ownership boundary, which is a DECLARATION rather than a construction site and is not a D1 target. ⛔ The live set is now TWO, both in bootstrap_plugin.py. Re-derive again before D-work: this set has moved at every single re-grounding, and it now shrinks as sibling plans land.
- OBSERVED, set is a lead: the effort table is restated on five bundle surfaces — **not independently re-derived at ingestion**. Re-derive by searching for the level rows; treat five as a figure to confirm, not a fact.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: The figure FIVE cannot be reproduced because the claim does not state the pattern that produced it - the same defect-in-claim-form the PLAN-12 metrics claim carries, now observed twice in this corpus. The claim says the effort table is restated on five bundle surfaces and instructs re-derivation 'by searching for the level rows', but 'the level rows' is not a searchable expression. ⛔ Do not treat five as the work list. The plan STATES its own pattern and derives its own set at outline. This records that the number was never checkable, not that it is wrong; an unverifiable verdict does not block emission.
- OBSERVED, set is a lead: the `/marshall-steward` emission set spans the §M8-listed scripts — **not independently re-derived at ingestion**. Re-derive by literal search; the hit list is the work list.
  - verdict: corroborated | checked_at: a83389fdb | by: multiplattform/analyze | rescoped: n/a | evidence: CORRECTION OF THIS PASS'S OWN EARLIER VERDICT, recorded at the PLAN-07 landing. The cleanup stamp hours earlier read 'contradicted, rescoped: yes - 152 hits across 87 FILES, D5 must be scoped against 87 files, weigh the scope-bloat guard'. That figure was WRONG IN ITS UNIT: the probe was a literal content search for /marshall-steward, which counts every textual MENTION - prose, standards, skill bodies - not the EMISSION SITES D5 targets. The landed plan scoped against 29 emission sites and single-sourced them through the new script-shared/scripts/command_forms.py; measured at a83389fdb, command_forms resolves to 30 hits across 15 files while the raw literal still returns 130 across 76, because the majority were always prose and prose was never D5's target. ⛔ The scope-bloat warning that verdict produced was a FALSE ALARM; splitting PLAN-07 on it would have been a split made on a phantom. The claim's own instruction ('re-derive by literal search; the hit list is the work list') is what misled the probe, and cleanup inherited the imprecision rather than catching it. The claim is CORROBORATED as shipped: the emission set was real, bounded, and single-sourced.
- HYPOTHESIS: the §M5–§M9 prose sites are complete — confirm/refute by running the audit registry's named sweep patterns (verify-at-outline). Extra hits are folded in and reported.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: OPEN BY DESIGN and left open. The claim asserts the section M5-M9 prose sites are complete and marks itself verify-at-outline against the audit registry's named sweep patterns. Settling it is the LAUNCHED plan's job per the verify-first contract - blocking on an unchecked verify-at-outline clause would make the verifying phase unreachable and the spec permanently unemittable. Re-stamped at 8fc353b6e for currency; the substance is unchanged from the 1c4e6febb reading. Does not block emission.
- OBSERVED, **line evidence refreshed at the 2026-09-05 re-grounding**: `marketplace_paths.py`'s `get_base_path` `global`/`project` scopes are D1's target, and are **distinct** from the same file's fallback-composer constants (`CLAUDE_DIR`, `PLUGIN_CACHE_SUBPATH`, `_DEFAULT_SKILL_ROOTS`, `_DEFAULT_BUNDLE_CACHE_ROOTS`), which are **PLAN-10's**. ⛔ Same file, two owners: touch only the scopes, and report rather than fix if the two turn out inseparable. ⚠️ **Locate by SYMBOL, never by the line numbers this claim used to carry** — they were `812-816` and `105, 110, 125, 136`, and at `565d4ade7` the real positions are `get_base_path` at **:735** and the constants at **:105, :110, :134, :145**. PLAN-09 moved this file and will not be the last to.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e: marketplace_paths.py is UNCHANGED since 1c4e6febb and still carries get_base_path with its global/project scopes. The claim's distinction between those scopes and the same file's fallback-composer constants stands unaltered. ⭐ Two landings have since made that distinction concrete rather than theoretical: PLAN-10's D1 examined the fallback constants and reported single-sourcing structurally impossible (import cycle), which confirms the two halves are genuinely separate targets - exactly what this claim asserts.

## Expected Surface

The named anchors below are the sites this plan's deliverables already identify; the trailing glob
bullets carry the breadth the sweeps reach. Re-derive the full set at outline.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/configurable_contract.py` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` — D1, **`get_base_path` scopes only** (see Dependencies)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-terminal-title/SKILL.md` — D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-terminal-title/standards/terminal-title-architecture.md` — D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py` — D5
- OBSERVED: `marketplace/bundles/plan-marshall/**` — the rest of the §M5–§M9-named skills, standards, and scripts
- OBSERVED: `test/plan-marshall/**` for every touched script
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/**` **docs only** (D2's displaced content); any op-schema need is recorded and made minimally
- OBSERVED (added by the PLAN-19-landing fold): `AGENTS.md`, `CLAUDE.md` — D5, the generator command form only. ✅ Verified with `corpus surfaces` at executor 0.1.1573: both resolve as `file` entries and this spec reads `declarative` with `claimed_count: 10`, so they DO contribute rows to the disjointness matcher. (An earlier note here claimed the extractor could not resolve slash-less repo-root paths; that was true of the retired parser only.)

## Dependencies and Sequencing

⛔ **One file, three owners — the sharpest boundary in this epic.**
`marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` carries three
separately-owned symbol sets: **this plan** owns `get_base_path`'s `global`/`project` scopes (§M5);
**PLAN-10** owns the fallback-composer constants (`CLAUDE_DIR`, `PLUGIN_CACHE_SUBPATH`,
`_DEFAULT_BUNDLE_CACHE_ROOTS`, `_DEFAULT_SKILL_ROOTS`); **PLAN-09** owns `_DEFAULT_RUNTIME_TARGET`.
Touch only the scopes. If they turn out inseparable from the constants, report rather than fix.

- Depends on: PLAN-01 and PLAN-03 (both landed) — shares the platform-runtime and permission surfaces with them.
- Overlaps with: **PLAN-06** — both conditionally touch `platform-runtime/standards/contract.md`. ⛔ Not concurrent, either order.
- Overlaps with: **PLAN-10** on `marketplace_paths.py` (different symbols in the same file). ⛔ Sequence PLAN-07 first; PLAN-10 then closes the remainder and re-derives rather than assuming.
- Overlaps with: **PLAN-09** on `platform-runtime` docs. Sequence, do not pair.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-05 (disjoint bundles), PLAN-13 (fully disjoint).

## Verification

- The full verify gate; red-first tests for D1's routing and D5's rule-file asymmetry.
- The D3 sweep re-run at verification time over the changed tree.
- A pre-PR verification pass **cold-reads** the reworded manage-status build-busy contract and reports whether an implementer on a hook-less target can tell what to do — the wording failed if not.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-07-runtime-fact-prose-and-single-sources.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. In particular it does **not** edit
`../reference/coupling-inventory.md`: coupling rows are retired by the orchestrator from the
landing, per the epic decision recorded in `epic.md`.
