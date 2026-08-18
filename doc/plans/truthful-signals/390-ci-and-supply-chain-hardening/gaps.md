# Gaps — 390-ci-and-supply-chain-hardening

**Source:** verification.md (same directory)   **Open items:** 3

D1, D2, D3, D6 and D7 are clean passes and carry no gap: each was opened at HEAD, each done-when
condition holds, the D1 fix was re-executed against a metacharacter-bearing ref, and the D6/D7 claims
were swept tree-wide. D4 and D8 are decisions the plan explicitly permitted to be recorded rather than
actioned, and both were recorded; their open points are operator-owned residue, not gaps in the run.
D5's defective mechanism was already reverted by PR #1246 and is therefore superseded rather than
open — what remains open is the missing guard for the invariant that revert had to restore (G1).

## G1 — Guard the python-verify concurrency group against re-sharing push and pull_request

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `.github/workflows/python-verify.yml:33` — the `concurrency.group` expression; guard
  belongs in `test/default/test_workflow_lint.py` or a sibling under
  `test/plan-marshall/manage-config/` beside `test_branch_prefix_allowlist.py`.
- **What is wrong:** This plan's D5 keyed the group as
  `${{ github.workflow }}-${{ github.event.pull_request.head.ref || github.ref_name }}`, putting the
  push run and the `pull_request` run for one branch in the same group with
  `cancel-in-progress` true for `pull_request`. PR #1246 (`24271bca`, one day later) reverted it after
  the `pull_request` run cancelled the push run's `gate` job 4 seconds into a 7-second decision on PR
  #1234; the always-reporting `conclusion` job then hard-failed and planted a red **required**
  `verify / conclusion` check, returning `405 Repository rule violations found` on merge. Incidence
  was 2 of the last 30 push runs. HEAD carries the fix — the key now includes
  `${{ github.event_name }}` — but nothing asserts it. The only guards over this file
  (`test_branch_prefix_allowlist.py`, `test_merge_group_trigger.py`, both re-run and passing) cover
  the `on:` block, not `concurrency:`; `test_workflow_lint.py` covers only the D1 and D2 dimensions.
  A future editor tidying the "redundant" `github.event_name` out of the key reintroduces an
  intermittent red required check with no underlying failure.
- **Why it matters:** The failure is a false-red on the one check every plan's merge gate depends on,
  it is intermittent (so it reads as flake, not as a regression), and it blocks merges repository-wide
  — the precise blast radius `plan.md` flagged in bold for this file.
- **Fix:** Add a test that reads `.github/workflows/python-verify.yml` and asserts the
  `concurrency.group` value contains `github.event_name` (and, positively, that the resolved group
  differs between a `push` and a `pull_request` event for the same branch). Give the assertion message
  the reason — pointing at PR #1246 and the cancelled-gate failure mode — so the next editor reads
  *why* before deleting it. Assert alongside it that `cancel-in-progress` remains scoped to
  `pull_request` only.
- **Done when:** Deleting `-${{ github.event_name }}` from `python-verify.yml`'s `concurrency.group`
  makes a named test fail with a message that explains the cancelled-gate failure mode; the test
  passes on the unmodified file.
- **Module/topic:** `.github/workflows/python-verify.yml` + `test/default/` workflow guards (CI
  topology).

## G2 — Close two false-negative shapes in the D9 run-block interpolation linter

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `test/default/test_workflow_lint.py:36-38` — `_RUN_LINE` regex and
  `_run_block_context_violations`.
- **What is wrong:** The linter recognises exactly two `run:` shapes: an inline `run: cmd` and a block
  scalar `run: |` / `run: >`. Probed directly (module loaded via `importlib`,
  `_run_block_context_violations` called on synthetic workflows), two valid YAML shapes carrying a
  live injection return `[]`: (a) a multi-line plain scalar —
  `run: echo` / newline / `  "${{ github.ref_name }}"` — because the continuation lines are never
  scanned once `after` is non-empty and does not begin with `|` or `>`; (b) a wider step dash —
  `-   run: echo "${{ github.ref_name }}"` — because `_RUN_LINE`'s `(?P<dash>- )?` group matches only
  the exact two-character `- `, so the line matches no branch at all. The mainstream block-scalar
  form is caught (mutation-verified: re-introducing `echo "${{ github.ref_name }}"` into
  `opencode-generate-check.yml`'s `run:` block turns the guard RED), so the guard is not vacuous —
  but it is narrower than its docstring's claim to assert that "no GitHub Actions context expression
  may appear inside a `run:` block".
- **Why it matters:** D9 exists specifically so the D1 fix cannot silently regress. An injection
  re-introduced in either shape ships with a green lint.
- **Fix:** Broaden `_RUN_LINE` to `^(?P<lead>\s*)(?P<dash>-\s+)?run:(?P<after>.*)$` and compute
  `key_col` from the actual matched dash width. For the non-block branch, also scan following lines
  indented deeper than `key_col` (the plain-scalar continuation), stopping at the first line that
  dedents to or past it — the same walk the block branch already performs. Add one regression test per
  shape asserting a non-empty violation list.
- **Done when:** `_run_block_context_violations` returns a non-empty list for both probed shapes, the
  existing 8 tests still pass, and the whole-tree guard still passes on the unmodified
  `.github/workflows/` (7 files).
- **Module/topic:** `test/default/test_workflow_lint.py` (D9 workflow-lint guard).

## G3 — Codify "never interpolate a context into a shell" in the security standard

- **Kind:** omission
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md:104-105`
  — the CI/CD pipeline-hardening bullet list.
- **What is wrong:** `plan.md` D1 states the fix's rule in bold as general
  ("⛔ **Never interpolate a context into a shell.** This is the rule, not just this instance's fix"),
  and the run loaded this very standard for its CI/CD hardening guidance. The standard's CI/CD list
  covers SHA-pinning third-party actions and default-`permissions: {}` least privilege, but says
  nothing about template injection through `${{ }}` in a `run:` block. Grepping the whole
  `persona-security-expert/` skill for `template injection|script injection|interpolat` returns one
  hit, an unrelated general sentence about SQL string interpolation in `adversarial-refute.md:20`.
  The rule is therefore enforced only by this repository's own `test_workflow_lint.py`, and travels to
  no consumer project.
- **Why it matters:** The plan's highest-severity finding produced a repo-local fix and a repo-local
  guard, but no reusable guidance — so the identical surface in any consumer project reviewed under
  this persona goes unflagged.
- **Fix:** Add one bullet to the CI/CD pipeline-hardening list in `dependency-supply-chain.md`: never
  interpolate a GitHub Actions context expression into a `run:` block; pass the value through `env:`
  and reference it as a quoted shell variable, because context values such as `github.ref_name`,
  `github.event.issue.title`, and `github.event.pull_request.head.ref` are attacker-influenceable and
  can carry shell metacharacters. Name the safe form explicitly so a reviewer can pattern-match it.
- **Done when:** The bullet is present in `dependency-supply-chain.md`'s CI/CD list and names both the
  unsafe shape (`${{ … }}` inside `run:`) and the safe one (`env:` + quoted `"${VAR}"`).
- **Module/topic:** `plan-marshall:persona-security-expert` (standards).
