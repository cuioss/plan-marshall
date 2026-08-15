# Run report — 390-ci-and-supply-chain-hardening (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/ci-supply-chain-hardening-9xmggr`    **PR:** [#1230](https://github.com/cuioss/plan-marshall/pull/1230)    **Outcome:** completed — auto-merge armed, landing delegated to the merge queue

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
unreachable on the cloud MCP path (403). The operator was asked twice (AskUserQuestion): first deferring
("Not sure — record a proposal"), then, when the concrete options were presented, explicitly instructing
**"do not decide now — report as open point"** for all three items. Per the plan (⚠ "If the answer cannot
be obtained in this run, RECORD A PROPOSAL … do not change the permissions blind") and the operator's
instruction, **no ruleset-dependent code change was made; all three remain OPEN POINTS for a later
operator decision.** Each item, with options and consequences:

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

### Pre-PR verification sub-agent (Step 6)

An independent `general-purpose` sub-agent verified the branch against the plan (read the actual files,
ran the D9 tests via importlib, swept the whole tree for stale claims). Verdict: **D1, D2, D3, D6, D7,
D9 fully VERIFIED; D4 and D8 verified as decisions with no blind code artifacts; D5 verified as a sound
static design.** Its beyond-diff stale-claim sweep was otherwise clean (no doc restates claude-distribute's
old `contents: write`, no fixture hardcodes the old `pw` line / old licensing URL / old permissions).

Per-instance findings and dispositions:

1. **D5 verification method — runtime single-run not observable from the diff** (sub-agent, verification
   caveat, not a defect). Confirming "one push → one verify run" needs a live run; the diff cannot show it.
   *Disposition:* accepted as a known limitation. The static design is verified safe (below); the runtime
   observation is deferred to a real `feature/`/`fix/`/`chore/` PR.
2. **D5 own-PR fixture is degenerate** (sub-agent, verification caveat). This branch is
   `claude/ci-supply-chain-hardening-9xmggr`; `claude/*` is not in the push allowlist, so only the
   `pull_request` trigger ever fires for it — a single verify run regardless of the concurrency block. The
   plan's "verify D5 on this plan's own PR" fixture therefore cannot exercise the dedup (which only occurs
   for `feature/*`/`fix/*`/`chore/*`). *Disposition:* accepted and disclosed; the report does not claim to
   have observed the dedup. The dedup is verified by static design analysis instead (group keyed per-branch;
   `cancel-in-progress` true only for `pull_request`, so a push run never cancels a PR run and the required
   `verify / conclusion` check is never lost).
3. **Stale illustrative sketch in `doc/refactor/02-verification-protocol.md`** (sub-agent, low severity).
   An illustrative YAML sketch of `opencode-generate-check.yml` (L330–352) omitted a `permissions:` block —
   accurate before D2, now divergent from the real file. *Disposition:* **FIXED** — added
   `permissions: contents: read` to the sketch to match the D2 change (this epic is about not leaving
   misleading signals). The sketch's *other* pre-existing divergences (unpinned `actions/checkout@v4` /
   `setup-python@v5` vs the real pinned SHAs) were deliberately **left unchanged** — action-pinning is a
   separate concern outside this plan's scope; re-pinning an illustrative sketch would be scope creep.
4. **D1 runtime metacharacter execution — CANNOT-VERIFY-FROM-DIFF** (sub-agent). The mechanism is provably
   safe by inspection (env-var delivery, quoted expansion). *Disposition:* covered by the local injection
   reproduction recorded above (safe form does not fire; old spliced form does).

No sub-agent finding required a re-dispatch: the only actionable item (#3) was a doc consistency touch,
not a defect in a deliverable.

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

Expected population derived from the registry (`author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`): `coderabbitai`,
`cuioss-review-bot`, `sourcery-ai`. Verdicts from the stored comment/review bodies (all three surfaces
read: `get_comments`, `get_reviews`, `get_review_comments`):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "PR Reviewer Guide 🔍 — No security concerns identified, No major issues detected, PR contains tests"; the `review / review` check concluded `success`. No findings to action. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in: 16 minutes." No review of the diff. |
| `sourcery-ai` | `rate-limited` | Posted only a review body "you have reached your weekly rate limit of 500000 diff characters"; `Sourcery review` check `skipped`. No review of the diff. |

**Coverage: 1 of 3.** Inline review threads: none (`get_review_comments` totalCount 0). No actionable review
comment exists (one clean review + two rate-limit notices), so nothing needed a fix or a thread reply.

**Step 8 condition-4 shortfall disclosure fired** (to the operator, and here): "Review coverage: 1 of 3 —
`cuioss-review-bot` reviewed (no issues); `coderabbitai` rate-limited (window reopens ~16 min); `sourcery-ai`
rate-limited (weekly quota)." Per the contract this is disclosed, not blocked on — rate limits are routine
and outside our control.

## Cost

- **Tokens:** not available to the agent in this session (the harness does not surface a token count to
  the run).
- **Wall-clock:** single interactive cloud session; the dominant measured cost was the `./pw verify` build
  at 405.71 s (0:06:45) for module-tests plus toolchain bootstrap.
- **Population:** this single Claude Code cloud session's usage. NOT comparable to a plan-marshall
  `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under a different per-task
  billing boundary this session does not share).

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named above (core two + persona-security-expert; two standards). |
| 2 Branch | Done — harness-assigned `claude/ci-supply-chain-hardening-9xmggr`, pushed to `origin` before any edit. **Branch form: harness-assigned** (kept as-is per the lane). |
| 3 Plan directory | Done — `plan.md` exists under the plan dir and opens with the first-instruction block (present in the handed file; no repair needed). |
| 4 Implement | Done — 11 commits, each carrying the `Co-Authored-By: Claude` trailer; every deliverable addressed. |
| 4 Per-commit gate | Done — the only `*.py`-touching commits (D6 `pw`, D9 test) were preceded by the full `./pw verify` (a superset of the quality gate), read clean before commit. Non-`*.py` commits correctly ran no gate. |
| 4 Pushed | Done — every commit pushed; no unpushed commit before arming. |
| 5 Build gate | Done — `git diff --name-only origin/main...HEAD -- '*.py'` = `pw`, `test/default/test_workflow_lint.py` → Python footprint present → `./pw verify` run, green (19624 passed / 0 failed). |
| 6 Verification sub-agent | Done — one independent `general-purpose` agent; findings + dispositions recorded (one low-severity doc-sketch item FIXED). |
| 7 PR cycle | Done — PR #1230; all three comment surfaces read; every comment dispositioned (none actionable). |
| 8 Merge gate | Conditions 2 (comments handled) and 3 (report finalized as last pre-merge commit) met; condition 1 (`verify`) `in_progress` at the gate → **armed anyway per the no-self-wake exception** (`subscribe_pr_activity` is approval-gated here), the merge queue is the enforcer. Condition-4 shortfall disclosed (1 of 3). |
| 8 Bridge | No status/bookkeeping write under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome for the orchestrator's collect. The `doc/refactor/` edit is a declared deliverable-adjacent consistency fix, not a bridge/status write. |
| 9 This check | Appended here. |
| 9 What have we learned | Recorded below. |

**GitHub access path:** the GitHub MCP server (cloud). **`/sync-plugin-cache`:** not owed (cloud run; and this
run edited no `marketplace/bundles/` behavioural surface beyond the automatic-review registry read — no bundle
edit was made at all).

## What have we learned (Step 9)

**None proposed.** Every contract step's artifact was producible as written, and every command worked in the
actual cloud environment. Two frictions arose, and both were already handled *by the contract as written*:

1. **`subscribe_pr_activity` is approval-gated** in this session — exactly the case the contract's Cloud-session
   affordances anticipate. The run drove the review cycle by the (ungated) read surface and completed via
   arm-and-hand-off, as the contract prescribes. No gap.
2. **The plan's "verify D5 on this plan's own PR" fixture is degenerate on a `claude/*` branch** (not in the
   push allowlist → only `pull_request` fires → a single run regardless of the concurrency block). This is a
   *plan-authoring* matter, not a lane-contract one, and the contract already handles it correctly via its
   disclose-don't-fake rule: the run disclosed the limitation rather than fabricating the observation. Worth
   a note for `author-cloud-plan` (a push-trigger-dependent verification cannot be self-observed on a cloud
   run's `claude/*` PR), but it is **not** a change to `cloud-plan-lane`.

The quiet-window caution the plan named was live this run (sibling plan 380 / PR #1229 was mid-flight and
landed at 15:32); the run checked the window before arming and confirmed it clear. That the plan carried the
caution and the run acted on it is the plan+contract working as intended, not a contract gap.

## Residue

- **D4 — three open points** (ruleset unreachable + operator instructed "do not decide now — report as open
  point"). If the operator later supplies the ruleset facts, the recommended options in §D4 can be actioned in
  a follow-up (CODEOWNERS only enforces with a paired ruleset rule; the generator check must be made
  always-reporting before it can be required; verify's grants need the reusable workflow's actual needs).
- **D7 — owed:** confirming `contact@cuioss.de` is monitored is an operator action, outside this run.
- **D5 — runtime single-run observation** is deferred: it cannot be exercised on this `claude/*` PR; the next
  `feature/`/`fix/`/`chore/` PR after this lands will show one verify run per push.
- **D6 — optional:** an upstream bug report to pyprojectx (the `irm` splice is in upstream `main`) is available
  operator follow-up, not part of this run.
