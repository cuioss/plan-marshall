# Run report — 135-remove-lsp-query-facade (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/lsp-shaped-query-api-6p2esn (harness-assigned, kept as-is)    **PR:** [#1214](https://github.com/cuioss/plan-marshall/pull/1214)    **Outcome:** completed (auto-merge armed; landing delegated to the merge queue — this session's self-wake tools are approval-gated, so it cannot block-to-confirm)

## Skills loaded

- `cloud-plan-lane` (first action, the working contract)
- `plan-marshall:ref-code-quality` (always; read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (always; read from bundle path)
- `plan-marshall:persona-implementer` (production-code work identity)
- `pm-plugin-development:plugin-architecture` (SKILL.md surgical edit)
- `pm-documents:ref-asciidoc` (`.adoc` doc edits)
- **Not loaded, and why:** `pm-dev-python:python-core` / `pytest-testing` — this change *removes* code and *deletes* a test rather than authoring new logic or tests, and the removal surface was fully specified up front; their standards would have been context cost with no use.

## Deliverables

- **D0 — GATE (zero consumers):** DONE (a gate, no commit). Re-derived the removal surface in-clone and swept the whole tree for `cmd_lsp_` / `architecture lsp` / the four verb names; every hit was the plan's own records or the historical `130-*` records. Consumer set empty → proceeded.
- **D1 — code + test removed:** DONE, commit `cfc4aad`. Removed the `lsp` argparse group, the four `cmd_lsp_*` pass-through handlers, and their imports/dispatch/re-exports (`architecture.py`, `_cmd_client_handlers.py`, `_cmd_client.py`); deleted `test_lsp_facade.py`. Wrapped verbs (`module`/`impact`/`find`/`resolve`) unchanged. Verified: `architecture … lsp hover` is now an argparse invalid-choice; a grep of the scripts dir for `lsp` returns nothing.
- **D2 — docs removed (surgical + hazard):** DONE, commit `cfc4aad`. Deleted `lsp-query-facade.adoc`; excised the facade row/section from `client-api.md`, `SKILL.md`, `code-intelligence.adoc`, `code-search.adoc`, and the developer-README index; pruned every dangling `xref`. **Hazard handled:** the search-verb paragraphs misfiled under `### lsp` in `SKILL.md` (`re.MULTILINE` anchors, payload boundary, inventory-scope, zero-result semantics) were **relocated** under `### search`, not lost — confirmed by the plugin-doctor pass and the conformance sub-agent.
- **D3 — single-vocabulary invariant:** DONE. Full `./pw verify` green; whole-tree orphan sweep clean (see Build gate + Findings).
- **Operator-requested addition — reasoning record:** DONE, commit `2192f3f`. [`rationale.md`](rationale.md) captures the design discussion behind the removal — the pre-1.0 no-shims/no-duplication principle, the analysis that the core query API is not (and cannot cheaply be) LSP-conformant, the feasibility verdict on full conformance, and where real LSP substance lives (plans `200`/`240`). Referenced from the PR and this report.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (`architecture.py`, `_cmd_client.py`, `_cmd_client_handlers.py`, and the deleted `test_lsp_facade.py`). Python changed → full **`./pw verify` ran → SUCCESS: 19497 passed, 14 skipped**; coverage COMPLETE (mypy production [396] + test [726], ruff, SPDX headers, plugin-doctor marketplace-wide, whole-tree pytest). Clean tree re-asserted before committing; **no `uv.lock` churn** (deliverable paths staged explicitly, never `git add -A`).

## Findings

- **Pre-PR verification sub-agent #1 (deliverable conformance):** **CLEAN — no findings.** Independently re-ran the orphan sweep three ways (`git grep`, the Grep tool, and `rg --no-ignore --hidden` over `target/` / `.claude/` / `marketplace/targets/`), confirmed D0–D2, verified the SKILL.md hazard (all five search paragraphs preserved and relocated under `### search`; exactly one `### capabilities`; `### lsp` gone), confirmed the wrapped verbs unchanged, and cleared the beyond-diff sweep. Stated limitation: it did not run `./pw verify` — covered by the Build gate above.
- **Pre-PR verification sub-agent #2 (cold read, unprimed):** Confirmed the removal — the query surface reads as **one coherent vocabulary, no aliases, no dangling references, search content complete**. It also surfaced **pre-existing** issues *not caused by this removal*; each is recorded per instance and **DEFERRED** as out of scope for a facade removal:
  1. `client-api.md` H2/H3 hierarchy: seven verb sections (`files`/`which-module`/`find`/`search`/`diff-modules`/`descriptor-regression-check`/`capabilities`) render under `## Error Handling` because the doc was never re-closed after verbs were appended past `resolve`. Pre-existing; the facade-section removal is neutral to it. Disposition: DEFERRED (see Residue).
  2. Verb-set drift: `siblings` / `profiles` are real subcommands with an invocation block only in `SKILL.md` (no contract, absent from `client-api.md`); `descriptor-regression-check` is contracted in `client-api.md` but absent from both `SKILL.md` surfaces. Pre-existing; unrelated to the facade. Disposition: DEFERRED.
  3. `doc/concepts/code-intelligence.adoc:34` names `info` as an adjacency/edge surface, which `client-api.md`'s `info` output does not carry. Pre-existing; the line was untouched by this change. Disposition: DEFERRED.
  4. Minor intra-doc duplication in `client-api.md § search` (the `--ignore-case`/`--literal` composition and `count` vs `file_count` each stated twice — contract then edge-case recap). Pre-existing; cosmetic. Disposition: DEFERRED.
- **CI (PR #1214):** `verify / gate`, `dependency-review`, `generate-check` green; `verify / verify` in progress at report time (auto-merge holds on it; the queue re-verifies on `merge_group`). `Sourcery review` and `auto-merge` checks report `skipped`.
- **PR review — `cuioss-review-bot`:** REVIEWED, **no findings** — "No major issues detected", "No security concerns identified". No action.
- **PR review — `coderabbitai` / `sourcery-ai`:** rate-limit notices only, no review of this diff. No action.

## Reviewer participation

Population from configuration — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc: `coderabbitai`, `sourcery-ai`, `cuioss-review-bot`.

| Reviewer (`author_login`) | Verdict | Body evidence |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide" review body: **"No major issues detected"**, "No security concerns identified" — a clean review over the diff. |
| `coderabbitai` | `rate-limited` | Published only "Review limit reached — next review available in 107 minutes." |
| `sourcery-ai` | `rate-limited` | Published only "reached your weekly rate limit of 500000 diff characters." |

**Coverage: 1 of 3 reviewed** — and the reviewer that ran found no issues. The § Step 8 shortfall disclosure fired: *"Review coverage 1 of 3 — cuioss-review-bot reviewed (clean); coderabbitai rate-limited (window reopens ~107 min); sourcery-ai rate-limited (weekly quota)."* Routine external quota exhaustion — disclosed, not blocked.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness exposes no per-session token counter). The dispatched sub-agents self-reported `subagent_tokens` (footprint ~81k, consumer-audit ~66k, verb-census ~147k, conformance-verify ~86k, cold-read ~104k); the main-loop total is not surfaced.
- **Wall-clock:** a single interactive session on 2026-08-13; the full `./pw verify` took 351s.
- **Population:** this single Claude Code cloud session's activity. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does not share. Not presented as such.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | DONE — § Skills loaded (read via bundle path; plugin not required). |
| 2 Branch | DONE — harness-assigned `claude/lsp-shaped-query-api-6p2esn`, present on `origin`, kept as-is. |
| 3 Plan directory | DONE — `135-remove-lsp-query-facade/plan.md` exists (prefix preserved) and opens with the first-instruction block. |
| 4 Implement | DONE — every commit carries the `Co-Authored-By: Claude` trailer; D0–D3 + the rationale addressed. |
| 4 Per-commit gate | DONE — the one `*.py`-touching commit (`cfc4aad`) was preceded by a clean full `./pw verify` (a superset of `quality-gate`); the docs-only commits (dir move, rationale, this report) need no gate. |
| 4 Pushed | DONE — every commit pushed; no unpushed commit remains. |
| 5 Build gate | DONE — Python changed → full `./pw verify` = SUCCESS (19497 passed). |
| 6 Verification sub-agent | DONE — two independent agents: conformance (CLEAN) and unprimed cold read (confirmed the removal; surfaced pre-existing out-of-scope findings). Dispositions in § Findings. |
| 7 PR cycle | DONE — PR #1214; every comment dispositioned (1 clean review, 2 rate-limited). All three comment surfaces read. |
| 8 Merge gate | DONE — conditions 1–3 met, shortfall disclosed, auto-merge armed (SQUASH). Landing delegated to the merge queue: the session's self-wake tools (`subscribe_pr_activity`, `send_later`) are approval-gated, so it cannot block-to-confirm `MERGED`; recorded as completed-with-landing-delegated, not partial. |
| 8 Bridge | DONE — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | DONE — this section. |
| 9 What have we learned | DONE — see below. |

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned**. No `/sync-plugin-cache` owed (a cloud run never performs or records it).

## What have we learned (Step 9)

**No contract change proposed.** The run exercised the lane end to end — the D0 gate, the conditional build gate, the two-agent verification (conformance + cold read), the three-surface comment read, and the merge gate — and every step's artifact was producible exactly as written. The only friction was cosmetic and outside the contract: the initial PR body's markdown link to `rationale.md` was mangled by backtick escaping, fixed by editing the PR body (a `update_pull_request`, no push). That is a tooling artifact, not a gap in the contract, so it is not an evidence-backed amendment. Nothing in this execution showed an ambiguous step, an unproducible artifact, or a command that failed as written.

## Residue

- **Landing confirmation.** Auto-merge is armed on #1214; the merge queue holds until the final head's `verify` greens, then squashes. This session's self-wake tools are approval-gated, so the `state: MERGED` read is delegated to the orchestrator's collect (which reads the PR merge event). If a human is watching, the PR page shows the queue state directly.
- **Pre-existing doc-hygiene findings (recommend a separate plan).** The cold read surfaced three unrelated, pre-existing defects worth their own doc-hygiene plan: the `client-api.md` H2/H3 hierarchy break (verb sections rendering under `## Error Handling`); the `SKILL.md` ↔ `client-api.md` verb-set drift (`siblings`/`profiles` under-documented, `descriptor-regression-check` missing from `SKILL.md`); and the `info`-adjacency overstatement in `code-intelligence.adoc`. All are out of scope for a facade removal and were left untouched.
- **Rationale's permanent home.** `rationale.md` lives in the plan directory and is removed at collect (git history retains it). If the "why the query API is domain-native, not LSP" reasoning should survive as a standing guard against re-proposing the facade, promote it to a `doc/adr/` ADR or a short concepts-page note — a follow-up, not this plan.
- **No orchestrator parent.** This plan was operator-authored from a direct request, not derived from a `.plan/local/orchestrator/` spec, so the collect step has no orchestrator plan to transition to `shipped`; treat it as a standalone correction of the merged `130` plan (PR #1207).
