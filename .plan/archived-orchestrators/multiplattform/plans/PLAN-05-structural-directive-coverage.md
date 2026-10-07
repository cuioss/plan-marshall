# PLAN-05: Every structural source directive is registered, and normative prose names acts, not tools

epic: multiplattform
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Ingested from `archive/original-staged-specs/050-structural-directive-coverage.md` and re-grounded
> against HEAD `2cd1a19c`.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim, act on what the tree says, and report divergence from the figure stated here.
- **Never edit another plan's surface**, even for an obvious adjacent fix — the neighbour may be running concurrently. Record the finding in the PR body and the inbox message instead.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`body_transform_engine.py`'s `STRUCTURAL_VOCABULARY` holds only the `Skill:` directive and `/slash`
commands, so the `Read: {path}` full-line load directive — the structural sibling of `Skill:`, used
across the bundles — is invisible to `assert_source_vocabulary_mapped` and emits verbatim to every
non-verbatim target. Beyond the directive, several bundle files carry **normative** Claude tool
invocations the registered idiom rewrites cannot reach. Make the build fail closed on an unmapped
`Read:` directive exactly as it does for `Skill:`, and leave no audited bundle file instructing a
Claude tool invocation outside the registered idiom carriers.

## Deliverables

1. **D1 — `read_directive` in the structural vocabulary.** Engine matcher plus per-target template (`mapping.json::directive_rewrites.read_directive`) mirroring `skill_directive`; the Claude target stays verbatim; fail-closed on a non-verbatim target without the template.
   *Done when:* generation rewrites a fixture `Read:` line per the OpenCode template, fails closed without one (red-first test), and the Claude equality check still passes.
2. **D2 — Call-schema block neutralized.** `pm-dev-java/skills/manage-maven-profiles/SKILL.md` Step 2 states the question and option set as data ("escalate to the operator with these options"), not the Claude argument schema.
   *Done when:* no `AskUserQuestion:`-keyed block with `header`/`options`/`multiSelect` remains in the file; the step's decision content is preserved.
3. **D3 — ext-triage escalation lines neutralized.** In every ext-triage `pr-comment-disposition.md` the bare ESCALATE-row and flow-branch lines name the act ("escalate to the operator"), keeping the one backticked `AskUserQuestion` as the registered-idiom carrier; the escalation blocks stay byte-identical across the files.
   *Done when:* the escalation blocks hash identically across the re-derived file set and only the backticked occurrence of the tool name remains in each.
4. **D4 — Remaining normative tool-prose sites.** The §M2-listed sites (Write-tool steps in `recipe-cui-logging-enforce` and the three pm-documents recipes, `link-verification.md` call syntax and blocks, the `testing-pytest.md` `CLAUDE.md` citation, the `pm-dev-java-cui/README.md` slash form, `content-review.md` second Claude mention) reworded to name the act or the owning rule.
   *Done when:* each named site is reworded; a sweep of the touched files finds no remaining unbackticked normative tool-invocation instruction.

## Out of Scope

- **Registering `Write`/`Edit`/`Glob`/`Grep` as rewrite idioms** — no live-runtime evidence yet that a rewrite (versus prose neutrality) is needed; `../reference/coupling-inventory.md` §C keeps that gated on WS-05's validation protocol.
- **The `persona-plan-marshall-agent` tool-usage surfaces** — registered in inventory §C with the same validation gate; a much larger rewrite with its own risk profile.
- **plugin-doctor / authoring vocabulary** — PLAN-06's surface.

## Claim Labels

- OBSERVED: `STRUCTURAL_VOCABULARY` holds only `skill_directive` and `slash_command` — read at `marketplace/targets/body_transform_engine.py:86-89`, exactly two keys, no `read_directive`. Re-read before building.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: body_transform_engine.py:86-89 holds exactly two keys - skill_directive and slash_command. No read_directive.
- OBSERVED, **count corrected at ingestion**: the `Read:` directive class spans roughly **146** occurrences across **55** distinct files, not the ~130 the original spec stated. Re-derived at HEAD `2cd1a19c` by full-line search. Per-bundle occurrence totals: plan-marshall 26, pm-dev-frontend 18, pm-dev-java-cui 11, pm-dev-java 36, pm-dev-python 1, pm-plugin-development 41, pm-documents 3, pm-requirements 6, plus 2 in `test/`. **This figure is itself a lead** — re-derive before D1; the hit list is the work list.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Phenomenon corroborated, figure corrected: re-derived 146 occurrences across 55 distinct files, not the ~130 stated. Per-bundle totals recorded in the claim.
- OBSERVED, **file counts corrected at ingestion**: the plan-marshall carrier set is **14** files, not 13 (the original count omitted `phase-3-outline/standards/outline-workflow-detail.md`); the pm-plugin-development carrier set is **13** files, not 11. The exactly-corroborated per-bundle skill counts are pm-dev-java 10, pm-dev-frontend 5, pm-dev-java-cui 5, pm-dev-python 1, pm-documents 3, pm-requirements 1.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: File counts corrected: plan-marshall 14 not 13 (omitted phase-3-outline/standards/outline-workflow-detail.md), pm-plugin-development 13 not 11. Per-bundle skill counts corroborated exactly.
- OBSERVED: the ext-triage escalation blocks are byte-identical across **seven** `pr-comment-disposition.md` files (js, java, oci, python, docs, plugin, reqs). Directly diffed the python and plugin files at HEAD: the Disposition-Outcomes ESCALATE row, the "Use `AskUserQuestion` when…" line, and the full 9-line Disposition Flow block are byte-identical. The set is a lead — re-derive and re-hash before editing.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Seven pr-comment-disposition.md files confirmed; python and plugin files directly diffed - ESCALATE row, the Use AskUserQuestion line, and the full 9-line Disposition Flow block are byte-identical
- OBSERVED: each of the seven files carries exactly **4** `AskUserQuestion` occurrences on **3** lines — the Disposition Outcomes table (2 on one line), the backticked carrier (1), and the flow branch (1). Only the backticked one is reachable by `rewrite_inline_code`.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Verified against the python file: line 11 carries 2 occurrences, line 78/88 the backticked carrier, line 105 the flow branch = 4 on 3 lines. All seven files report match_count 4.
- OBSERVED: the `AskUserQuestion:` YAML block is unreachable by every existing transform — read at `pm-dev-java/skills/manage-maven-profiles/SKILL.md` Step 2 (lines 96–108), a fenced YAML block with `question`/`header`/`options[].label/.description`/`multiSelect`. No registered-idiom rewrite touches a fenced block; only backtick-wrapped inline code is rewritten.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: manage-maven-profiles/SKILL.md Step 2 lines 96-108 is a fenced YAML block with question/header/options[].label/.description/multiSelect; no registered idiom rewrite touches a fenced block
- HYPOTHESIS: no further normative call-schema block exists in the bundles — confirm/refute by sweeping for fenced blocks keyed by a Claude tool name across every candidate file (verify-at-outline). Extra hits are reported and folded into D4. The ingestion pass did **not** settle this: an exhaustive sweep of every fenced code block was not run, so this remains genuinely open rather than silently assumed.
  - verdict: unverifiable | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Not settled at ingestion: an exhaustive sweep of every fenced code block across all candidate files was not run. Recorded as genuinely open rather than defaulted to corroborated - the plan's own D4 folds in extra hits.

## Expected Surface

- OBSERVED: `marketplace/targets/body_transform_engine.py`, `marketplace/targets/opencode/mapping.json`, `marketplace/targets/opencode/transforms.md`, `test/marketplace/targets/**` — D1
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/SKILL.md` — D2
- OBSERVED: the seven `*/skills/ext-triage-*/standards/pr-comment-disposition.md` files across pm-dev-frontend, pm-dev-java, pm-dev-oci, pm-dev-python, pm-documents, pm-requirements, **plus the single `pm-plugin-development/skills/ext-triage-plugin/standards/pr-comment-disposition.md`** — D3
- OBSERVED: the §M2-named bundle files across pm-dev-java, pm-dev-java-cui, pm-dev-python, pm-dev-oci, pm-dev-frontend, pm-documents, pm-requirements — D4

## Dependencies and Sequencing

- Depends on: none (PLAN-02 landed; the engine it extends is present).
- Overlaps with: **PLAN-16** and **PLAN-02** (landed) on `marketplace/targets/**` — not concurrent with PLAN-16. Preferred order is PLAN-16 first, so the lint gate covers the engine before this plan adds code to it.
- Overlaps with: **PLAN-12** across pm-documents, pm-dev-frontend, pm-requirements. Run PLAN-05 first; PLAN-12 re-derives afterwards.
- ✅ **The PLAN-19 overlap on `marketplace/targets/opencode/transforms.md` is DISSOLVED.** It was recorded at ingestion by `corpus cross-check`; commit `3bc01075` de-referenced that file's dangling link directly, so PLAN-19 no longer edits it and this plan's D1 has the file to itself. PLAN-19 and this plan may now run concurrently.
- Adjacent to: **PLAN-06's surface, with one deliberate carve-out.** `pm-plugin-development/skills/ext-triage-plugin/standards/pr-comment-disposition.md` belongs to THIS plan, carved out of PLAN-06's `pm-plugin-development/**`, so D3's byte-identical set stays whole. ⛔ That carve-out is load-bearing: do not widen either plan across it. Everything else under `pm-plugin-development/**` is PLAN-06's and must not be touched here.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).

## Verification

- The full verify gate (Python changes — the build gate applies); D1's fail-closed test red-first.
- `generate.py --target all` exits 0 on the edited tree.
- A pre-PR verification pass sweeps the changed values' consumers by kind, and **cold-reads** one rewritten ext-triage standard to report whether the escalation instruction still unambiguously directs an operator escalation — the wording failed if not.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-05-structural-directive-coverage.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. In particular it does **not** edit
`../reference/coupling-inventory.md`: coupling rows are retired by the orchestrator from the
landing, per the epic decision recorded in `epic.md`.
