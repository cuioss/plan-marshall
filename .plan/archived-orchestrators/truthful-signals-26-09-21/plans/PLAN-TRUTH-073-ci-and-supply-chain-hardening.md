# PLAN-TRUTH-073: CI and supply-chain hardening — a template-injection surface and an unscoped token

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from `doc/review-26-07-04.md`, which is being retired. Re-verified at HEAD.

## Objective

Ten `.github/` and packaging findings survive re-verification. Two are security-relevant and lead the
plan: a template-injection surface in a `contents: write` workflow, and a workflow with no
`permissions:` block at all. The rest are least-privilege, trigger-topology and packaging hygiene.
**One component (`.github/` plus the vendored wrapper), one PR.**

## Deliverables

1. **[B1] Close the template-injection surface — *Medium, security*.** The *"Create dist tag"* step
   interpolates `${{ github.ref_name }}` **directly into a bash `run:` block** that runs
   `git fetch`/`git tag` in a `contents: write` context. ✅ **Re-verified at HEAD: 2 interpolation
   sites.** Ref names can carry shell metacharacters — a classic injection shape. **Pass via `env:` and
   reference `"$REF_NAME"`; never interpolate a context into a shell.**
2. **[B2] Add a `permissions:` block to `opencode-generate-check.yml` — *Medium, security*.**
   ✅ **Re-verified: still no `permissions:` block**, so `GITHUB_TOKEN` inherits the repo/org default
   (potentially read-write) for a job that only runs a generator. Add `permissions: contents: read`.
3. **[B5] Narrow `claude-distribute`'s workflow-wide `contents: write` — *Low*.** ✅ Re-verified
   present. Pushes use a GitHub App / personal token, so the default token's write scope is
   unnecessary breadth on checkout and generate steps. Default to `read`; grant `write` per step.
4. **[B3] Decide `CODEOWNERS` — *Medium*.** ✅ **Re-verified: `.github/CODEOWNERS` does not exist.**
   ⛔ **This is a DECISION, not a fix**: if the branch-protection ruleset enables *"Require review from
   Code Owners"*, the rule matches no owners and enforces nothing. **Confirm what the ruleset actually
   requires before adding the file** — the ruleset is not visible in-repo.
5. **[B6] / [B7] Settle the required-check topology — *Low*.** `opencode-generate-check` is
   path-filtered: **if it is ever made a required check, PRs not touching those paths wait forever.**
   And `python-verify` grants only `contents: read` + `pull-requests: read`, so if the reusable verify
   workflow posts coverage or annotations it **silently degrades**. ⛔ Both depend on the same
   invisible ruleset as B3 — **answer the ruleset question once, then act on all three.**
6. **[B8] Stop the duplicate CI runs — *Low*.** For a `feature/*`/`fix/*`/`chore/*` branch with an open
   PR to `main`, **both `push` and `pull_request` fire**, running the full verify suite twice per push.
   Add a concurrency group, or drop the `push` trigger for those prefixes. ⭐ Straight compute saving
   with no behaviour change.
7. **[B9] Fix the vendored `pw` uv-install fallback — *Low*.** ✅ **Re-verified: the stray `irm` is
   still present.** The non-Windows fallback splices PowerShell's `Invoke-RestMethod` into a `curl`
   line, breaking that path. ⚠ **This is upstream pyprojectx wrapper code** — prefer regenerating via
   `pw --upgrade` to a fixed release over hand-patching a vendored file, and **record which was done**.
8. **[B10] Reconcile the three private-contact channels — *Low*.** `SECURITY.md` routes vulnerability
   email to `contact@cuioss.de`, commercial licensing goes to a form, `LICENSE.md` points at issues.
   Cross-reference them consistently. ⛔ **And confirm the security mailbox is actually monitored** —
   that half is an operator action, not a code change, and the plan must not report it as done.
9. **[B11] Add a PR template — *Low, optional*.** ✅ Re-verified absent. `CONTRIBUTING.md` assumes one
   may exist. **Optional — drop it if a template is not wanted**, and record the decision either way.
10. **D10 — tests/controls where testable.** B1's `env:` form and B2's permissions block are
    assertable by a workflow-lint check; add one rather than relying on review.

Ten deliverables — under the raised cap of 12.

## Claim Labels

- **OBSERVED, re-verified at HEAD 2026-08-09**: B1 (2 `ref_name` interpolations), B2 (no
  `permissions:`), B3 (no `CODEOWNERS`), B5 (`contents: write` present), B9 (stray `irm`), B11 (no PR
  template).
- ✅ **[B4] IS FIXED and is NOT in this plan.** The review found `uv.lock` locking **zero**
  dependencies while `build.py` invoked `uv run`. ✅ **Re-verified: `uv.lock` now carries 47 package
  entries.** ⭐ It was refreshed during PR #1122 as an operator decision — **an unrelated plan closed a
  review finding nobody had connected to it.** Recorded so it is not re-filed.
- ⛔ **NOT ESTABLISHED — the branch-protection ruleset.** B3, B6 and B7 all turn on what the ruleset
  requires, and **it is not visible in the repository.** The review flagged this as a maintainer
  decision and it still is. **D4/D5 must ASK, not assume** — changing workflow permissions against a
  guessed ruleset is how a required check wedges.
- ⚠ B10's mailbox check cannot be settled from the repo at all.

## Expected Surface

- **OBSERVED**: `.github/workflows/claude-distribute.yml`,
  `.github/workflows/opencode-generate-check.yml`, `.github/workflows/python-verify.yml`,
  `.github/` (new `CODEOWNERS` / PR template), `SECURITY.md`, `LICENSE.md`, `pw`
- ⛔ **`python-verify.yml` is the file every plan's CI depends on** — a mistake here breaks the merge
  gate for every other plan in flight. Treat B6/B7/B8 as the highest-blast-radius items in the plan.

## Dependencies and Sequencing

- Depends on: none. **Disjoint from every currently-running plan.**
- ⛔ **Do not run concurrently with a plan that is mid-merge**: B8's trigger change and B6/B7's
  permission changes alter the checks a PR produces, and a plan in its merge window could see its
  required check disappear or duplicate. **Land it in a quiet window.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-073-ci-and-supply-chain-hardening.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
