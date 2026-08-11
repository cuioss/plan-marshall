# Run report — 120-rename-marshall-orchestrator-to-plan-orchestrator (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/rename-marshall-plan-orchestrator-sz8x37 (harness-assigned)    **PR:** [#1162](https://github.com/cuioss/plan-marshall/pull/1162)    **Outcome:** completed (rename implemented + verified; required checks green; auto-merge armed as the final action right after this report lands and `verify` re-confirms on the new head, landing then delegated to the merge queue)

## Skills loaded

Read directly by bundle path (the plugin notation was not attempted; direct read is the always-works route in a fresh clone):

- `plan-marshall:ref-code-quality` — always-load work identity.
- `pm-plugin-development:plugin-script-architecture` — always-load (script/notation surface).
- `pm-plugin-development:plugin-architecture` — bundle/skill-directory structure surface.
- `pm-documents:ref-asciidoc` — `.adoc` concept-doc surface.

No skill was unreachable by both routes.

## Deliverables

**D0 — GATE: re-derive the surface at HEAD (mutates nothing).**
- Derivation population: `Grep` over the whole working tree (ripgrep, which honours `.gitignore`, so `.plan/` is excluded — consistent with D6).
- Hyphen token `marshall-orchestrator`: **265 matching lines across 74 files**. Underscore form `marshall_orchestrator`: **0** (no Python identifier uses it). Other-cased variants found in the initial sweep: the single uppercase identifier `_MARSHALL_ORCHESTRATOR_SKILL` (3 uses, one test file). ⚠ **The initial variant sweep was incomplete** — it did not cover the **space-separated title-case display form** `Marshall Orchestrator`, which survived in two `SKILL.md` H1 headings and was caught by the verification sub-agent (findings #1/#2 below, fixed). A later exhaustive `Marshall.Orchestrator` sweep confirmed exactly those two and no others.
- **Subset relation confirmed** (claim-label check): `persona-marshall-orchestrator` is a strict substring of `marshall-orchestrator`, so a single exact-token replace transforms BOTH skills and the 3-part notation; the file count is the union (74), not a sum.
- **Classification**: rename-target = all `marketplace/**`, `test/**`, `plugin.json`, `README.md`, live docs (`doc/concepts/**`, `doc/user/**`, `doc/adr/016`), the living orientation doc `doc/plans/README.md`, and governance docs `CLAUDE.md` + `.claude/skills/cloud-plan-lane/SKILL.md` (each carried a now-stale `/marshall-orchestrator` command reference). Must-not-touch = records/other-plan specs under `doc/plans/**` (6 other pending specs + the 090 report + this plan's own `plan.md`/`report-01.md`) and the exclusion set.
- **Exclusion set derived, not assumed** — each confirmed to exist by name via `git ls-files`: `marshall-steward/`, `marshalld.py`/`_marshalld_*.py`, `marshal.json`, `plan-marshall` bundle. None contains the substring `marshall-orchestrator`.

**D1 — Rename the three directories** (commit `bd1f1cf`). `git mv` with history preserved; git detected all renames at 81–99 % similarity.

**D2 — Update every in-tree reference incl. 3-part notation** (commits `bd1f1cf`, `faaec17`). Exact-token substitution over `git ls-files`, excluding `doc/plans/**` except `README.md`: 65 files, 270 occurrences. New notation `plan-marshall:plan-orchestrator:orchestrator` verified (47 occurrences / 16 files); third segment `orchestrator` unchanged. Uppercase `_MARSHALL_ORCHESTRATOR_SKILL` → `_PLAN_ORCHESTRATOR_SKILL` (3×). Two title-case H1 headings fixed in `faaec17`.

**D3 — Cross-referencing skills + concept docs** (commit `bd1f1cf`). `platform-runtime`, `manage-logging`, `manage-status`, `manage-terminal-title`, `manage-config`, `extension-api`, `phase-6-finalize`, `manage-lessons`, `plan-retrospective`, `plan-marshall`; `plugin.json` + bundle `README.md`; concept docs `orchestration.adoc`, `personas.adoc`, `README.adoc`, `planning-workflow.adoc`, `doc/user/configuration.adoc`, `doc/adr/016`. Sub-agent confirmed all `link:`/`xref:` targets resolve to the renamed dirs; plugin-doctor `broken-relative-link: 0`.

**D4 — Regenerate the executor.** Not performable in this cloud clone (executor lives under git-ignored `.plan/`). The SOURCE — skill dir names + every documented notation string — is updated, so a local regeneration resolves the new notation. Recorded as a local step owed (Residue).

**D5 — Acceptance, each check verified.**
- **Zero remaining** `marshall-orchestrator` (any casing) in rename-target scope: `marketplace/` → 0, `test/` → 0; every surviving occurrence (9 files) is under `doc/plans/` (records + this plan's own docs).
- **Matched positive control** (the plan's single most important check): planted an occurrence in `marketplace/_positive_control_tmp.txt`; the sweep found it (and only it); removed it; scope returned to 0. Non-vacuous, correct tree.
- **Plugin-doctor gate clean**: `status: pass, total_issues: 0` (35 rules) — twice (`./pw verify`, then `./pw quality-gate` after the heading fixes).
- **Full test suite green**: `./pw verify` → 18957 passed / 14 skipped, `verify: SUCCESS`, no failure markers.
- **Exclusion set genuinely untouched, by name**: no `marshall-steward`/`marshalld`/`marshal.json` file in the diff; `plan-marshall` bundle name preserved. No double-replacement artifact.

**D6 — `.plan/` ledger explicitly NOT rewritten.** Non-goal asserted: `.plan/` is git-ignored and absent; its historical orchestrator references are untouched and unreachable. In-tree records under `doc/plans/**` (other specs + the 090 report) likewise left as records.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py`, so the gate took its full path: `./pw verify` → **SUCCESS, 18957 passed / 14 skipped**, plugin-doctor `total_issues: 0`. No `uv.lock`/generated-file churn. CI `verify / conclusion` on the PR head: **success**.

## Findings

Recorded per instance; source, description, disposition.

**Pre-PR verification sub-agent (2 rounds)** — verified against D0–D6; independently reproduced the zero-in-scope sweep, exclusion-set integrity, and the "purely cosmetic" guarantee (`ORCHESTRATOR_STORE = 'orchestrator'` unchanged). Findings:

1. **[MEDIUM → FIXED]** `plan-orchestrator/SKILL.md:8` H1 was `# Marshall Orchestrator Skill` (title-case form the exact-token replace missed). Fixed → `# Plan Orchestrator Skill`.
2. **[MEDIUM → FIXED]** `persona-plan-orchestrator/SKILL.md:10` H1 was `# Persona: Marshall Orchestrator`. Fixed → `# Persona: Plan Orchestrator`. Post-fix exhaustive `Marshall.Orchestrator` sweep = zero outside `doc/plans/`; round-2 sub-agent independently confirmed complete.
3. **[LOW → FIXED]** Report's D0 completeness claim understated variant coverage. Corrected in §D0.
4. **[LOW/informational → DEFERRED, deliberate]** `plugin.json` skill arrays: the two renamed entries kept their old positions, so they no longer sit in local alphabetical order. Ungated (plugin-doctor clean) and the array is not strictly alphabetical to begin with (`ref-code-quality` sits among `build-*`). Left un-re-sorted per the plan's minimal-collateral / "report-not-fix" posture; recorded transparently.

**False positives ruled out (not findings):** `plan-marshall orchestrator` (bundle name + generic "orchestrator") in `manage-metrics/SKILL.md`, `extension-api/marshal-json-reference.md`, `doc/concepts/token-management.adoc`, four `doc/resources/diagrams/*.svg` — pre-existing prose, correctly untouched (round-2 sub-agent confirmed via `-o` span extraction).

**Scope decision (recorded, not a defect):** `doc/plans/**` records/other-plan specs left untouched (29 occurrences across 8 tracked files + this run's own docs), on the plan's "records are not source" (D6) / "report-not-fix" / "re-grounds exactly one spec" principles. `doc/plans/README.md` (living doc) and governance docs updated. Sub-agent verdict: "defensible, with one honest caveat — D5's literal 'zero under doc/' is not met." The D5-vs-D6 tension was resolved in favor of D6 and recorded, not asserted as literal D5 compliance.

**CI / automated review:** `verify / conclusion`, `verify / verify`, `verify / gate`, `review / review`, `dependency-review`, `generate-check` — all **success**. No inline review-thread comments (0 threads). No actionable findings from any reviewer.

## Reviewer participation

Expected population derived from configuration — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | **reviewed** | Posted "PR Reviewer Guide 🔍 — PR contains tests, No security concerns identified, No major issues detected" — a review artifact over the diff with an explicit nothing-to-report. |
| `coderabbitai` | **rate-limited** | Posted only "Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in 40 minutes." A quota notice, not a review. |
| `sourcery-ai` | **rate-limited** | Review body: "your pull request is larger than the review limit of 150000 diff characters." A refusal (diff-size), not a review. |

**Coverage: 1 of 3.** Step 8 shortfall disclosure fired: "Review coverage: 1 of 3 — `cuioss-review-bot` reviewed (no major issues); `coderabbitai` rate-limited (window reopens ~40 min); `sourcery-ai` rate-limited (diff exceeds 150 000-char cap)." Per the contract this is a disclosure, not a merge block — rate limits are routine and outside our control.

**Non-required pending status disclosed (not a blocker):** `license/cla` is pending ("CLA not signed yet"). `mergeable_state: unstable` confirms it is NOT a required context (all required contexts passed); it is disclosed to the operator, who as author can sign/recheck via the cla-assistant link, but it does not gate the merge.

## Cost

- **Tokens:** main interactive Claude Code cloud session — not exposed to the agent in this session, stated plainly. Verification sub-agent output tokens (reported by the harness): run 1 ≈ 97,001, run 2 ≈ 109,904 (≈ 206,905 total across 33 tool uses).
- **Wall-clock:** ≈ run start 14:2x → auto-merge arm ~15:0x UTC (roughly 30–40 min), dominated by two `./pw verify`/`quality-gate` runs (~7–14 min each) and two sub-agent passes.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary a single interactive cloud session does not share.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | DONE — 4 skills, named above, all via bundle path. |
| 2 Branch | DONE — harness-assigned `claude/rename-marshall-plan-orchestrator-sz8x37`, published on `origin` (was absent; pushed as first action). |
| 3 Plan directory | DONE — `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/plan.md`, opens with the first-instruction block (present, not repaired). |
| 4 Implement | DONE — commits carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | DONE — the `*.py`-touching commit `bd1f1cf` was preceded by `./pw verify` (total_issues 0); the docs-only fix commit needed none, but `./pw quality-gate` was run anyway (clean). |
| 4 Pushed | DONE — every commit pushed; no unpushed commit remains. |
| 5 Build gate | DONE — Python changed → full `./pw verify`, green. |
| 6 Verification sub-agent | DONE — 2 rounds; 2 findings fixed, 1 report-claim fixed, 1 deferred-with-reason; all in Findings. |
| 7 PR cycle | DONE — PR #1162; every comment dispositioned; both comment surfaces read (conversation + inline threads=0). No `skip-bot-review` (diff touches skills/bundles/`*.py`). |
| 8 Merge gate | Conditions 1–3 met (required `verify/conclusion` green; comments handled; report finalized+pushed as the last pre-merge commit). Shortfall (1-of-3) and non-required `license/cla` disclosed. Auto-merge armed (SQUASH) as the final action immediately after this report commit lands and `verify` re-confirms on the new head; landing then delegated to the merge queue — the session cannot self-wake to watch it (arm-and-hand-off completion, not partial). |
| 8 Bridge | No status/bookkeeping write under `doc/plans/` outside this plan's own directory. `doc/plans/README.md` was edited as a declared rename-target deliverable (living doc), not a record. |
| 9 This check | DONE (this table). |
| 9 What have we learned | Recorded below. |

GitHub access path used: **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/*` (kept as-is). A `/sync-plugin-cache` is **not owed** by this cloud run (machine-local step).

## What have we learned (Step 9)

**No contract change proposed.** The cloud-plan-lane contract functioned as designed this run: the one substantive defect (two stale title-case headings the implementer's exact-token substitution missed) was caught precisely by the contract's Step 6 beyond-diff verification sub-agent — which is exactly the gate that step exists to be — and the two-surface comment read, the `mergeStateStatus`-based required-ness read (`unstable` ⇒ CLA non-required), and the arm-and-hand-off completion all behaved as written. One minor observation, not rising to a proposal: the content substitution used a purpose-built Python script (explicit file allowlist, per-file counts) rather than N Edit calls, which sits at the edge of the "no shell file operations" rule; it was treated as a proper tool (not one of the enumerated read/search shell utilities) and its correctness was underwritten by the exact-token safe-token property + the positive control. The operator may wish to clarify the rule's stance on programmatic bulk edits, but this run produced no failure attributable to it.

## Residue

- **Local regeneration owed (not a debt this cloud run pays):** after this lands, the orchestrator command path is `plan-marshall:plan-orchestrator:orchestrator`; the old path stops resolving. A local machine must regenerate the executor and sync the plugin cache (`/marshall-steward`, `/sync-plugin-cache`) before local tooling works again.
- **Other-plan specs under `doc/plans/`** still name `marshall-orchestrator` in their expected-surface sections; each carries its own D0 gate and re-grounds against the settled surface when it runs — not this plan's to rewrite.
- **`license/cla`** pending — the author (`cuioss-oliver`) may sign/recheck via the cla-assistant link if a green CLA status is wanted; non-required, so it does not block the merge.
