# Gaps — 390-ci-and-supply-chain-hardening

**Source:** verification.md (same directory)   **Open items:** 5

D1, D3, D6 and D7 are clean passes and carry no gap: each was opened at HEAD, each done-when condition
holds, the D1 fix was re-executed against a metacharacter-bearing ref (twice — by the original reviewer
and independently during adversarial review), and the D6/D7 claims were swept tree-wide. D2's own
done-when ("declares read-only content access") holds at HEAD; what does not hold is that the D9 guard
asserts it (G5). D4 and D8 are decisions the plan explicitly permitted to be recorded rather than
actioned, and both were recorded; their open points are operator-owned residue, not gaps in the run.
D5's defective mechanism was already reverted by PR #1246 and is therefore superseded rather than
open — what remains open is the missing guard for the invariant that revert had to restore (G1).

## G1 — Guard the python-verify concurrency group against re-sharing push and pull_request

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `.github/workflows/python-verify.yml:34` — the `concurrency.group` expression (line 35 is
  `cancel-in-progress`; lines 12–33 are its explanatory comment). The guard belongs in
  `test/default/test_workflow_lint.py` or a sibling under `test/plan-marshall/manage-config/` beside
  `test_branch_prefix_allowlist.py`.
- **What is wrong:** This plan's D5 keyed the group as
  `${{ github.workflow }}-${{ github.event.pull_request.head.ref || github.ref_name }}` (re-derived from
  `git show 86d5298a:.github/workflows/python-verify.yml`, line 27), putting the push run and the
  `pull_request` run for one branch in the same group with `cancel-in-progress` true for
  `pull_request`. PR #1246 (`24271bca`, one day later) reverted it after the `pull_request` run
  cancelled the push run's `gate` job 4 seconds into a 7-second decision on PR #1234; the
  always-reporting `conclusion` job then hard-failed and planted a red **required**
  `verify / conclusion` check, returning `405 Repository rule violations found` on merge. Incidence
  was 2 of the last 30 push runs (figure quoted from `24271bca`'s commit message, not re-derived
  here). HEAD carries the fix — the key now includes `${{ github.event_name }}` — but nothing asserts
  it. The only guards over this file (`test_branch_prefix_allowlist.py`, `test_merge_group_trigger.py`,
  both re-run and passing: 4 passed) cover the `on:` block, not `concurrency:`; a `grep` of the whole
  `test/` tree for `python-verify` and `concurrency` finds no assertion over the `concurrency:` block.
  `test_workflow_lint.py` covers only the D1 and D2 dimensions. A future editor tidying the
  "redundant" `github.event_name` out of the key reintroduces an intermittent red required check with
  no underlying failure.
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

## G2 — The D9 run-block linter misses any `run:` whose step dash is wider than two characters

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/default/test_workflow_lint.py:36` — the `_RUN_LINE` regex, consumed by
  `_run_block_context_violations` (`:40-89`).
- **What is wrong:** `_RUN_LINE`'s `(?P<dash>- )?` group matches only the exact two-character `- `, so
  a step written with a wider dash matches no branch of the regex at all and its `run:` body is never
  scanned. Executed, not read — the module was loaded via `importlib` and
  `_run_block_context_violations` called on synthetic workflows:
  - `-   run: echo "${{ github.ref_name }}"` → `[]`
  - `-   run: |` / newline / `      echo "${{ github.ref_name }}"` → `[]`

  Both parse under `yaml.safe_load` to a step whose `run` value is exactly
  `echo "${{ github.ref_name }}"` — i.e. a live injection that ships with a green lint. The mainstream
  two-space-dash form is caught, so the guard is not vacuous: run against the **real pre-fix bytes**
  (`git show 86d5298a^:.github/workflows/claude-distribute.yml`) it returns 3 violations, and 0 against
  the post-fix file. But it is narrower than its docstring's claim to assert that "no GitHub Actions
  context expression may appear inside a `run:` block".
- **Why it matters:** D9 exists specifically so the D1 fix — the plan's highest-severity finding —
  cannot silently regress. An injection re-introduced in this shape ships green through the only
  automated control over it.
- **Fix:** In `test/default/test_workflow_lint.py`, broaden `_RUN_LINE` to
  `^(?P<lead>\s*)(?P<dash>-\s+)?run:(?P<after>.*)$` and compute `key_col` from the actual matched dash
  width (`len(match.group('dash'))`) instead of the hard-coded `2`. Add one regression test per shape
  (inline and block-scalar under a wide dash) asserting a non-empty violation list.
- **Done when:** `_run_block_context_violations` returns a non-empty list for both wide-dash shapes
  above, the existing 8 tests still pass, and `test_workflows_have_no_context_expression_in_run_blocks`
  still passes on the unmodified `.github/workflows/` (7 files). *(The fix was prototyped in a scratch
  copy during adversarial review: with the broadened regex and dash-width `key_col`, all three
  blind-spot shapes are flagged, all 7 real workflows stay clean, and the legitimate `env:`-passing
  form is not flagged.)*
- **Module/topic:** `test/default/test_workflow_lint.py` (D9 workflow-lint guard).

## G3 — Codify "never interpolate a context into a shell" in the security standard

- **Kind:** omission
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md:104-108`
  — the CI/CD pipeline-hardening bullet list (five bullets, `104`–`108`).
- **What is wrong:** `plan.md` D1 states the fix's rule in bold as general
  ("⛔ **Never interpolate a context into a shell.** This is the rule, not just this instance's fix"),
  and the run loaded this very standard for its CI/CD hardening guidance. The standard's CI/CD list
  covers SHA-pinning third-party actions, default-`permissions: {}` least privilege, OIDC over static
  credentials, ephemeral runners, and separation of duties — but says nothing about template injection
  through `${{ }}` in a `run:` block. Two sweeps confirm the absence: grepping the whole
  `persona-security-expert/` skill for `template injection|script injection|interpolat` returns one
  hit, an unrelated general sentence about SQL string interpolation in `adversarial-refute.md:20`; and
  a broader sweep of that skill for `run:|\$\{\{|github\.ref_name|GitHub Actions context|workflow_run|pull_request_target`
  returns **zero** hits. Widening to the whole `marketplace/` tree finds only generic
  `subprocess`/`shell=True` guidance (`pm-plugin-development:plugin-security`, `pm-dev-python:python-security`),
  never the GitHub Actions shape. The rule is therefore enforced only by this repository's own
  `test_workflow_lint.py`, and travels to no consumer project.
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

## G4 — The D9 run-block linter never scans a multi-line plain-scalar `run:` body

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/default/test_workflow_lint.py:83-88` — the non-block branch of
  `_run_block_context_violations`.
- **What is wrong:** A separate defect from G2, with a separate fix. When the text after `run:` is
  non-empty and does not begin with `|` or `>`, `_run_block_context_violations` inspects **only that
  one line** (`if _CONTEXT_EXPR.search(after)`) and advances by one; it never walks the following,
  more-deeply-indented lines. A YAML multi-line plain scalar therefore escapes entirely. Executed via
  `importlib`, not read:

  ```yaml
  - run: echo
      "${{ github.ref_name }}"
  ```

  → `_run_block_context_violations(...)` returns `[]`, while `yaml.safe_load` folds the same text to
  `run: echo "${{ github.ref_name }}"` — a live injection with a green lint. This holds regardless of
  dash width, so fixing G2's regex alone does not close it.
- **Why it matters:** Same reason as G2 — this is the only automated control standing between a future
  edit and a re-opened template-injection surface, and it reports clean on a valid instance of exactly
  the defect its docstring names.
- **Fix:** In `test/default/test_workflow_lint.py`, give the non-block branch the same body walk the
  block branch already performs: after matching `run:`, collect every following line that is blank or
  indented more deeply than `key_col`, stopping at the first line that dedents to or past `key_col`,
  and report a violation when `${{` appears in the `after` text **or** anywhere in that body. Advance
  `i` past the walked body only for the block-scalar case (the plain-scalar case must keep the existing
  `i += 1` so a sibling `run:` is not skipped). Add a regression test
  `test_linter_flags_plain_scalar_continuation` asserting a non-empty violation list for the shape
  above, and a negative test asserting that a step with `run: echo hi` followed by a sibling
  `env:`/`with:` mapping carrying `${{ … }}` at the SAME indent as `run:` is **not** flagged.
- **Done when:** `_run_block_context_violations` returns a non-empty list for the plain-scalar
  continuation shape, returns `[]` for the sibling-`env:` negative case, the existing 8 tests still
  pass, and `test_workflows_have_no_context_expression_in_run_blocks` still passes on the unmodified
  `.github/workflows/` (7 files). *(Prototyped during adversarial review in a scratch copy: the walk
  flags the continuation shape, leaves all 7 real workflows clean, and does not flag the sibling-`env:`
  form.)*
- **Module/topic:** `test/default/test_workflow_lint.py` (D9 workflow-lint guard).

## G5 — The D9 permissions guard asserts a block exists, not that it is read-only

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `test/default/test_workflow_lint.py:92-94` — `_has_top_level_permissions`, consumed by
  `test_workflows_declare_top_level_permissions` (`:120-132`).
- **What is wrong:** D2's done-when is "it declares **read-only** content access", but the guard is
  `any(line.startswith('permissions:') for line in text.splitlines())` — presence only. Executed
  against the real `opencode-generate-check.yml` bytes with the scope swapped in memory (the repo file
  was never mutated; `git diff --quiet` confirmed clean before and after):
  `_has_top_level_permissions` returns `True` for the file as-is, `True` with
  `permissions:\n  contents: write`, and `True` with `permissions: write-all`. So the half of D2 that
  is actually load-bearing — least privilege — is unguarded, and a future edit widening the generator
  check's token to write ships green. (The guard *does* catch D2's original defect, a workflow with no
  block at all, and the docstring claims no more than that; the gap is against D2's done-when, not
  against the docstring.) All 7 workflows are read-only-by-default at HEAD except `pr-agent.yml`,
  which legitimately declares `pull-requests: write`, `issues: write`, `id-token: write`.
- **Why it matters:** D9's stated purpose is that D1 and D2 "cannot silently regress". Half of D2 can.
- **Fix:** In `test/default/test_workflow_lint.py`, add a guard that parses each workflow's top-level
  `permissions:` block and asserts every scope is `read` or `none`, with an explicit allowlist keyed by
  workflow filename for the deliberate exceptions (today: `pr-agent.yml` → `pull-requests: write`,
  `issues: write`, `id-token: write`). Put the justification for each allowlisted scope in the
  allowlist entry's comment so widening a scope requires editing the allowlist, not just the workflow.
- **Done when:** Changing `.github/workflows/opencode-generate-check.yml`'s top-level block to
  `contents: write` makes a named test fail; the test passes on the unmodified tree (7 files), and
  `pr-agent.yml`'s declared write scopes pass via the allowlist rather than by the check being skipped.
- **Module/topic:** `test/default/test_workflow_lint.py` (D9 workflow-lint guard).

## Refuted during adversarial review

**None.** Every gap carried in this document at review time (G1, G2, G3) was re-checked against the
tree and upheld on substance; G2 was re-severitied and split (its plain-scalar half became G4), and
G1/G2/G3 all had file:line references corrected. The evidence for each is in the gap body above and in
verification.md § Adversarial review. Nothing was dropped.
