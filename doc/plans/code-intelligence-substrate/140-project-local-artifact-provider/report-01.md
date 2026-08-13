# Run report — 140-project-local-artifact-provider (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/project-local-artifact-provider-3ajym0` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

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
| One `.claude/` subtree resolves to a module, its sibling resolves to null | **Confirmed** | `plan-marshall`'s `claim_paths()` returns `('.claude/skills', 'plan-marshall')`; `.claude/commands` and `.claude/settings.json` are claimed by no attributor and are dotfile trees the crawl never inventories, so they resolve to `null`. Pinned by `test_which_module_plan_claim.py::test_both_shipped_claims_arrive_through_the_same_seam`. |
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

_Pending verification sub-agent + CI + review._

## Reviewer participation

_Pending._

## Cost

_Filled at close._

## Contract check (Step 9)

_Filled at close._

## What have we learned (Step 9)

_Filled at close._

## Residue

_Filled at close._
