# Run report — 390-ci-and-supply-chain-hardening (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/ci-supply-chain-hardening-9xmggr`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (working contract; loaded first, before reading the plan).
- `plan-marshall:ref-code-quality` (always).
- `pm-plugin-development:plugin-script-architecture` (always).
- `plan-marshall:persona-security-expert` — security-relevant change (template injection, token
  least-privilege, supply-chain wrapper). Loaded its `standards/secure-design-principles.md` (least
  privilege, secure-by-default) and `standards/dependency-supply-chain.md` (CI/CD pipeline hardening:
  default read-only `permissions`, minimum scope per job).

All loaded by reading the bundle path (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`); the
`plan-marshall` plugin route was not needed. No skill was un-obtainable.

## Deliverables

One component, one PR. All code changes committed on the branch and pushed.

| # | Deliverable | Done | Commit | Verification |
|---|---|---|---|---|
| D1 | Close template-injection surface in `claude-distribute.yml` | ✅ | `close template-injection surface…` | No `${{ … }}` in any `run:` block (grep-confirmed: remaining `${{ }}` are only in `name:`, `env:`, `with:`, `concurrency:`). `github.ref_name` now referenced as `"${REF_NAME}"`. |
| D2 | Least-privilege `permissions:` on `opencode-generate-check.yml` | ✅ | `add least-privilege permissions block…` | Workflow-level `permissions: contents: read` added. |
| D3 | Narrow `claude-distribute.yml` write scope | ✅ | `close template-injection surface…` | Workflow-level default `contents: write` → `contents: read`. All writes use the separate cui-release-bot app token; no step needs default-token write, so no per-step grant added. |
| D4 | GATE — settle ruleset question, then decide 3 items | ⚠ proposals | (no code change) | Ruleset unreachable + operator deferred → proposals recorded below. **No blind change made.** |
| D5 | Stop duplicate CI runs | ✅ | `dedupe push+PR verify runs…` | `concurrency:` group keyed on branch identity, `cancel-in-progress` scoped to `pull_request` only. Triggers unchanged (invariant tests still hold). |
| D6 | Fix vendored wrapper install fallback | ✅ | `repair the vendored wrapper's…` | Removed stray `irm` PowerShell token from the non-Windows curl line. Hand-patched (upstream is unfixed — see Findings). |
| D7 | Reconcile three private-contact channels | ✅ | `reconcile the private-contact channels` | LICENSE.md + README → private Tally form (matching `config.yml`); cross-references added SECURITY.md ↔ LICENSE.md. No `issues/new/choose` licensing pointer remains. |
| D8 | Decide on a PR template | ✅ decided | (no artifact) | Operator decision: **no PR template.** Recorded below. |
| D9 | Workflow-lint control | ✅ | `add workflow-lint guard…` | `test/default/test_workflow_lint.py` asserts D1 (no context in `run:`) and D2 (top-level `permissions:`) over the real tree, plus unit tests showing the linter fails a re-introduced interpolation and passes the env-passing form. |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **`pw`** (D6) and **`test/default/test_workflow_lint.py`** (D9). Python footprint present → build required.

Ran full `./pw verify` (quality-gate + test-compile + module-tests), `UV_HTTP_TIMEOUT=600`, from repo root. Result read from streamed output, not the exit code:

- quality-gate: `ruff … All checks passed!`, `mypy … Success: no issues found in 399 source files`, `SPDX-header check passed`, plugin-doctor ran.
- test-compile: `mypy … Success: no issues found in 734 source files`.
- module-tests: `19624 passed, 14 skipped in 405.71s` — 0 failed, 0 errors. D9's new tests are among the passes.

No `uv.lock` / generated-file churn resulted (verified `git status --porcelain` after the build: only `pw` and the new test file). Session interpreter is Python 3.11 (below the 3.12 floor) but no lockfile rewrite occurred this run.

## D4 — ruleset gate: decisions/proposals

The branch-protection ruleset is not visible from inside the repository, and the ruleset-config API is
unreachable on the cloud MCP path (403). The operator was asked (AskUserQuestion) and deferred all three
items ("Not sure — record a proposal"). Per the plan (⚠ "If the answer cannot be obtained in this run,
RECORD A PROPOSAL … do not change the permissions blind"), **no ruleset-dependent code change was made.**
Each item, with options and consequences:

### D4.1 — Would a code-owners file enforce anything?

- **Fact:** no `CODEOWNERS` file exists (verified via `git ls-files`).
- **Inference (strong):** the repo actively merges PRs through a merge queue with no CODEOWNERS present.
  If the ruleset *required* code-owner review, no PR could ever satisfy it (no owners defined → no
  possible code-owner approval), making the repo permanently unmergeable. Since PRs do merge, the ruleset
  almost certainly does **not** require code-owner review.
- **Option A (recommended, matches the inference):** ruleset does not require code-owner review → adding
  a CODEOWNERS file today enforces nothing. Add none. Enabling enforcement later needs BOTH a CODEOWNERS
  file AND a ruleset rule ("Require review from Code Owners"); the file alone is inert.
- **Option B:** if the ruleset *does* require code-owner review, the absent CODEOWNERS is a latent gap
  (no PR can get code-owner approval). Remediation: add a CODEOWNERS mapping the tree to the maintainer(s).
- **This run:** no CODEOWNERS added.

### D4.2 — Should the path-filtered generator check be required?

- **Fact:** `opencode-generate-check.yml` is path-filtered (`pull_request.paths` = `marketplace/bundles/**`,
  `marketplace/targets/**`). It only produces a check on PRs touching those paths.
- **Consequence if made required:** a PR not touching those paths never produces the check → the required
  context is permanently absent → the PR is blocked forever. (This plan's ⛔ warning.)
- **Empirical signal from this PR:** this PR does **not** touch those paths, so the generator check will
  not run on it. If this PR reaches a mergeable state without that check, that is direct evidence the
  check is not currently required. (Observed mergeStateStatus recorded in the review cycle below.)
- **Option A (recommended):** keep it NON-required. A path-filtered check must not be required.
- **Option B:** to make it required, first convert it to report on ALL PRs (drop the path filter, or add
  an always-reporting conclusion job that reports green when the paths are untouched — mirroring
  python-verify's `skip-on-docs-only` conclusion). Making it required while keeping the path filter is the
  wedge and must not be done.
- **This run:** no change (ruleset config not settable from here; must not guess).

### D4.3 — Do the verify workflow's read-only grants degrade the reusable workflow?

- **Fact:** `python-verify.yml` grants `contents: read` + `pull-requests: read`, calling
  `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml@v0.19.0`.
- **Unknown:** whether that reusable workflow posts PR coverage comments or check annotations needing
  `pull-requests: write` / `checks: write`. The reusable workflow is in `cuioss/cuioss-organization`,
  **out of scope** for this session.
- **Option A (recommended, and the plan's out-of-scope constraint):** leave grants unchanged. Least
  privilege; if no coverage/annotations are expected, `read` + `read` is correct. Changing the verify
  workflow on a guess is the highest-blast-radius action in the plan.
- **Option B:** if coverage/annotations are intended and currently silently degraded, grant the minimal
  extra scope — but only after confirming against the reusable workflow what it needs.
- **This run:** verify permissions unchanged.

## D8 — PR template decision

Operator decision (AskUserQuestion): **do not add a PR template.** The question is now closed. No
`.github/pull_request_template.md` / `PULL_REQUEST_TEMPLATE` was added. Context: the CONTRIBUTING guide
references "issue templates if available" (not a PR template); the tooling (CLAUDE.md, cloud-plan-lane)
checks for a PR template and proceeds gracefully when none exists, so the absence is fully handled.

## Out-of-scope re-verification

- **Lock-file finding** (claim label: "re-verify before relying on the exclusion"): `uv.lock` is present
  (83 KB) and locks real dependencies — it is not the empty/zero-dependency file the original finding
  reported. The exclusion is valid; no action.
- **Security mailbox monitored** (D7 ⛔): confirming `contact@cuioss.de` is actually monitored is an
  OPERATOR action, outside this run's reach. **Recorded as OWED — not reported as done.**

## Findings

_The verification sub-agent (Step 6), CI, and PR review are pending; findings and dispositions are
recorded below as they arrive._

- **D1 (injection), self-verified against a metacharacter-bearing ref (plan's required check):** a local
  reproduction confirmed the value cannot escape the variable. With the malicious ref
  `v1.0"; touch <marker>; echo "pwned` passed via `env:` and referenced as `"${REF_NAME}"` (the D1 form),
  the injected `touch` did **not** fire and `dist_tag` held the full literal string. With the old spliced
  form (`dist_tag="<value>"` — the value substituted into the script source), the injected `touch` **did**
  fire. The env-passing fix closes the surface; verified beyond reading the YAML, per the plan.
- **D6 (supply chain), self-verified:** the identical `irm`-splice bug is present in pyprojectx **upstream
  main** (verified via WebFetch of the upstream `pw.py`). There is therefore no fixed upstream release to
  regenerate from, so the plan's "prefer regenerating over hand-patching" resolves to a minimal hand-patch
  — recorded per the plan's D6 ⛔. (An upstream report is optional operator follow-up, not part of this run.)

## Reviewer participation

_Recorded in the review cycle (Step 7), from the stored comment bodies._

## Cost

- **Tokens:** not available to the agent in this session (the harness does not surface a token count to
  the run).
- **Wall-clock:** single interactive cloud session; the dominant measured cost was the `./pw verify` build
  at 405.71 s (0:06:45) for module-tests plus toolchain bootstrap.
- **Population:** this single Claude Code cloud session's usage. NOT comparable to a plan-marshall
  `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under a different per-task
  billing boundary this session does not share).

## Contract check (Step 9)

_Written as the last pre-merge commit (Step 8 condition 3)._

## What have we learned (Step 9)

_Written as the last pre-merge commit (Step 8 condition 3)._

## Residue

- D4 is left as three recorded proposals (ruleset unreachable + operator deferred). If the operator later
  supplies the ruleset facts, the recommended options above can be actioned in a follow-up.
- D7: security-mailbox monitoring confirmation is owed to the operator.
