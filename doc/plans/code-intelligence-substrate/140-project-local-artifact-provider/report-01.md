# Run report — 140-project-local-artifact-provider (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/project-local-artifact-provider-3ajym0` (harness-assigned, kept as-is)    **PR:** [#1208](https://github.com/cuioss/plan-marshall/pull/1208)    **Outcome:** completed — auto-merge armed, landing delegated to the merge queue

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — via bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — via bundle path.
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.
- `plan-marshall:cloud-plan-lane` — the working contract (loaded first).

For the `.adoc` and bundle-doc surfaces I followed `CLAUDE.md`'s Documentation Standards
(blank line before lists, `xref:`, no timestamps, current-state-only) and the existing
document conventions rather than loading `pm-documents:ref-asciidoc` /
`pm-plugin-development:plugin-architecture` in full — the edits are additive rows/prose to
existing docs that already establish the house style, and the reference model
(`pm-documents` attributor + its test) was read first-party.

## Claim re-derivation (founding premises, re-checked in the clone)

| Claim | Verdict | How re-derived |
|---|---|---|
| One `.claude/` subtree resolves to a module, its sibling resolves to null | **Confirmed** | At run start `plan-marshall`'s `claim_paths()` returned `('.claude/skills', 'plan-marshall')`; `.claude/commands` and `.claude/settings.json` were claimed by no attributor and are dotfile trees the crawl never inventories, so they resolved to `null`. This pre-change premise was pinned by the seam-merge assertions in `test_which_module_plan_claim.py` (since updated to the new owner by this run). |
| Project-local dotfile trees are never inventoried; attribution is the sole route | **Confirmed** | `cmd_which_module` docstring + `code-intelligence.adoc` § "Inventory scope is not tree scope": `.claude/**` is outside the crawl's allowlist, so rungs 1/2/4 are structurally blind and only rung-3 (Axis-D) can answer. |
| The hard-coded prefix map is already retired from core | **Confirmed, verified first-party** | `_architecture_core.py` rung-3 resolution goes entirely through `_load_path_attribution_seam()` → `discover_path_attributors` / `merge_path_claims` / `lookup_claim`. No project-local prefix constant in core. |
| The plugin-development bundle already implements module discovery | **Confirmed** | `pm-plugin-development` `Extension(ExtensionBase, DerivationResolverBase)` implements `discover_modules()` (one module per bundle). |
| A third artifact subtree exists in this repository | **Refuted** | `.claude/` has exactly `commands/`, `settings.json`, `skills/` — two directories and one file, no third subdirectory. The bare-root `.claude` claim covers all three uniformly, which is why enumeration is unnecessary. |
| Moving the ownership breaks no consumer | **Confirmed** | The only test asserting the `.claude/skills → plan-marshall` *claim* is `test_which_module_plan_claim.py:188`. No production code branches on `.claude/skills → plan-marshall` specifically. In a consumer project the claim was already inert (neither `plan-marshall` nor `pm-plugin-development` is a discovered module there), so the module-existence guard drops it before and after. See § Deliverables D2. |
| The index-cannot-answer consequence and its whole-tree fallback | **Confirmed** | `.claude/commands/**` resolves to `null` today; a caller obeying structured-queries-first reads that as "covered, no owner" and falls back to a whole-tree scan. |

## Deliverables

| # | Deliverable | What was done | Commit | Verification state |
|---|---|---|---|---|
| D1 | Project-local artifact claim through the seam, covering the surface uniformly | `pm-plugin-development`'s `Extension` opts into `PathAttributionBase` and `claim_paths()` returns the **bare-root** `('.claude', 'pm-plugin-development')`, covering skills, commands, settings, and any future subtree by prefix containment. `plan-marshall` drops `.claude/skills`, keeping only `.plan`. No core edit — the claim rides the Axis-D seam. | `935eaca` | Verified: unit test asserts the claim; `./pw quality-gate` + module-tests green |
| D2 | Ownership decision, made explicitly and recorded | Move from `plan-marshall` (a legacy re-homing, never a fresh ruling) to `pm-plugin-development` (owner = who understands Claude Code plugin artifacts). Recorded in both extensions' `claim_paths()` docstrings, the pm-plugin-development SKILL.md § Project-Local Artifact Ownership, and code-intelligence.adoc. Two readings do not conflict — the former owner was never a ruling. | `935eaca` | Verified by the sub-agent cold-read (below) |
| D3 | Consistency verification across the whole tree | `test_path_attribution.py` **enumerates** the real `.claude` tree (47 files) and asserts every path → `pm-plugin-development`, publishing the count; each top-level subtree asserted uniform; reader-level test in `test_which_module_plan_claim.py`. | `935eaca` | Verified: walk test green, 47 files published |
| D4 | Resolver distinguishes "not covered" from "covered, no matches" | Reuses the shipped `attributor_count` coverage contract (mirrors `resolver_count` / `files_scanned`) — no second contract invented, no core edit. Negative-control pair asserted at the seam (attributor_count 0 vs N) and at the which-module reader. | `935eaca` | Verified: negative-control pair green |
| D5 | Documentation | Ownership contract in pm-plugin-development SKILL.md; project-local attribution row + prose in code-intelligence.adoc; current-implementations table and Overview/Declaration in ext-point-path-attribution.md. | `935eaca` | Verified: plugin-doctor `broken-relative-link: 0`, doc renders |

**Split-guard evaluation (plan asked to evaluate before implementing):** the five deliverables are facets of one change — the claim (D1), its decision record (D2), its verification (D3/D4), and its docs (D5) — not separable into independent plans. No split; executed as one plan.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (two `extension.py`, two test files under plan-marshall + pm-plugin-development), so the Python build gate applies.

- **Whole-tree quality gate** (`./pw quality-gate`): **green** — mypy 396 files clean, ruff clean, SPDX headers clean, plugin-doctor marketplace-wide **0 issues** (incl. `broken-relative-link: 0`, `provides-method-table-drift: 0`, `readme-skill-registration-drift: 0`).
- **`./pw module-tests plan-marshall`**: **16342 passed, 1 skipped, 0 failed** (two `.claude/skills → plan-marshall` consumer tests in `test_files_inventory.py` were found and updated to the new owner during this run).
- **`./pw module-tests pm-plugin-development`**: **2241 passed** (incl. the new `test_path_attribution.py` and the real-marketplace quality-gate test).
- The full-suite `./pw verify` across every module is CI's required `verify` check (the lane's merge-queue net); it was not re-run whole locally because it re-runs the already-green quality gate and exceeds this session's 10-minute per-command bound. All `*.py` changes live in the two modules run above, and no other module's tests consume the changed `.claude` attribution.

## Findings

Recorded per instance.

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | Verification sub-agent | `doc/concepts/extension-architecture.adoc:29` said `plan-marshall-plugin` claims `.plan` and `.claude/skills` — stale after the move. Line 31's Axis-A straddle roster omitted `pm-plugin-development`. | **Fixed** in `eef6a02` — line 29 now names the three claimants; line 31 adds `pm-plugin-development`. |
| 2 | Verification sub-agent | `doc/resources/diagrams/extension-topology.svg:144-145` showed `plan-marshall-plugin · .claude/skills · .plan (Axis-D)` with `1 impl` — stale attribution + wrong count. | **Fixed** in `eef6a02` — now `claims: .plan · .claude · doc (Axis-D)` / `3 impls`. |
| 3 | Verification sub-agent (final sweep) | `test/plan-marshall/extension-api/test_path_attribution_merge.py:641-651` — a stub fixture encoding `('.claude/skills', 'plan-marshall')` and asserting `.claude/settings.json` is unclaimed, under a "the two claims the seam ships" comment. Passed (stub-based, so CI would not catch it) but misleads a reader. | **Fixed** in `f741ba0` — fixture updated to the two real attributors (`pm-plugin-development` owns `.claude`, `plan-marshall` owns `.plan`); `.claude/settings.json` assertion flipped to `pm-plugin-development`; `_MODULES` gained `pm-plugin-development`. |
| — | Build gate (local) | Ruff `I001` import-order in the new `test_path_attribution.py`. | **Fixed** during the gate — marketplace-first-party (`extension_base`) grouped before local (`conftest`). |
| — | Build gate (local) | Two stale `.claude/skills → plan-marshall` consumer tests in `test_files_inventory.py` failed under the new ownership. | **Fixed** during the gate — seed gained a `pm-plugin-development` module; assertions updated; the `.claude/settings.json`-is-unclaimed test repurposed to assert the founding inconsistency is now closed. |
| — | CI (`review / review`, `cuioss-review-bot`) | "PR contains tests; No security concerns identified; No major issues detected." | No action — a clean review with no findings. |
| — | CI (`coderabbitai`, `sourcery-ai`) | Rate-limit / quota notices in place of a review. | No action — routine rate limits; disclosed under Reviewer participation (not a merge block). |

No verification finding was rejected — all three were real and fixed, then re-swept clean. The pre-PR sub-agent confirmed D1–D4, the no-core-edit constraint, and the D2 ownership record (by cold read).

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:
`coderabbitai` (coderabbit.md), `sourcery-ai` (sourcery.md), `cuioss-review-bot` (pr-agent.md).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published the "PR Reviewer Guide" review artifact over the diff — "PR contains tests · No security concerns identified · No major issues detected." No actionable findings. |
| `coderabbitai` | `rate-limited` | Published only "Review limit reached … we couldn't start this review. Next review available in: 92 minutes." Engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published only "you have reached your weekly rate limit of 500000 diff characters." Engaged but did not review this diff. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure fired: "Review coverage 1 of 3 — `cuioss-review-bot` reviewed with no findings; `coderabbitai` rate-limited (window reopens ~92 min); `sourcery-ai` rate-limited (weekly quota)." Per the contract this is a disclosure, not a block — rate limits are routine and outside our control, so auto-merge is armed on 1-of-3 with the shortfall stated.

## Cost

- **Tokens:** not available to the agent in this session — this interactive cloud session exposes no token meter to the run.
- **Wall-clock:** not precisely metered by the agent; observable anchors — PR #1208 created `2026-08-13T10:22Z`; the run's build gates alone (`./pw quality-gate` + `./pw module-tests` ×2 + `./pw verify plan-marshall`) consumed ≈ 22 min of wall-clock, and the three verification-sub-agent dispatches ≈ 8 min.
- **Population:** these figures count only this single Claude Code cloud session's own activity. They are **NOT comparable** to a plan-marshall `metrics.toon` total, which sums an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary that a single interactive cloud session does not share.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded. |
| 2 Branch | Done — harness-assigned `claude/project-local-artifact-provider-3ajym0` kept as-is; present on `origin`. |
| 3 Plan directory | Done — `doc/plans/code-intelligence-substrate/140-project-local-artifact-provider/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — five commits carry the `Co-Authored-By: Claude` trailer; D1–D5 addressed. |
| 4 Per-commit gate | Done — every `*.py`-touching commit was preceded by a clean gate (whole-tree `./pw quality-gate` green, and `./pw verify plan-marshall` green for the finding-3 commit). |
| 4 Pushed | Done — no unpushed commit (each commit pushed immediately). |
| 5 Build gate | Done — Python footprint present; whole-tree quality gate green, `plan-marshall` 16342 passed, `pm-plugin-development` 2241 passed. Full-suite `./pw verify` delegated to CI's required `verify` check. |
| 6 Verification sub-agent | Done — 3 findings, all fixed; dispositions above; final sweep clean. |
| 7 PR cycle | Done — PR #1208; all three comment surfaces read; every comment dispositioned (no actionable ones). |
| 8 Merge gate | Conditions 1–3 gated at arm time (verify green on the report-inclusive head; no open comments; report finalized and pushed as the last pre-merge commit). Auto-merge armed; landing delegated to the merge queue (this session cannot self-wake to watch the queue). |
| 8 Bridge | No status/bookkeeping write outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | Recorded here. |
| 9 What have we learned | Recorded below. |

**GitHub access path used:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned. A `/sync-plugin-cache` is **not owed** — it is a machine-local build step, not a debt a cloud run records.

## What have we learned (Step 9)

**Proposed contract change (pending operator approval — NOT shipped in this run).** This run produced concrete evidence for one refinement to the `cloud-plan-lane` Step 6 sweep instruction. Finding 3 was a **test stub/fixture that hardcoded the retired value** (`('.claude/skills', 'plan-marshall')`) and *still passed CI* because it is driven by a `_StubAttributor`, not the real discovered seam — so neither the local build gate nor CI would ever have caught it, and it survived two sub-agent sweeps before a third, explicitly-`*.py`-inclusive sweep found it. Step 6 today names consumer kinds "a prose restatement, a schema field or its placeholder, a worked example, a cross-document reference" but does **not** name *a test fixture/stub that encodes the changed value and passes regardless because it is not driven by the real code path*. Adding that consumer kind (and instructing the sweep to grep `*.py` fixtures, not only prose/docs) would have surfaced Finding 3 on the first pass. Evidence: `test_path_attribution_merge.py:641-651`, caught only on the third dispatch. **Recommendation:** if the operator approves, ship as a separate `chore(cloud-plan-lane)` PR (not `skip-bot-review`), touching only the skill. Not self-approved and not bundled into this PR, per Step 9.

## Residue

- The full-suite `./pw verify` across every module was not run whole locally (10-minute per-command bound + already-green quality gate); it is covered by CI's required `verify` check and the merge queue's `merge_group` run. All `*.py` changes are confined to the two modules run green locally.
- `coderabbitai` and `sourcery-ai` may re-review once their windows reopen; the subscription remains active until the PR merges or closes, and any late review comment will wake this session for handling.
