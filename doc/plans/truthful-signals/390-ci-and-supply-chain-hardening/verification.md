# Verification — 390-ci-and-supply-chain-hardening

**Verified against:** commit `c04b24e50b560da7cfc73988e46a4394b0d2bab6`   **Landed as:** PR #1230, commit `86d5298ab4610aa142912725399ed5249c863a5f`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit (`git log --oneline --all --grep '#1230'` → `86d5298a`) and read its full
  diff (`git show --stat`, then `git show 86d5298a -- <path>` for every touched path). Landed
  footprint re-derived at HEAD: **11 files, 546 insertions, 17 deletions**.
- Opened at HEAD: `.github/workflows/claude-distribute.yml`, `.github/workflows/opencode-generate-check.yml`,
  `.github/workflows/python-verify.yml`, `.github/workflows/pr-agent.yml`, `pw` (lines 195–225),
  `pw.bat`, `LICENSE.md`, `README.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/config.yml`,
  `CONTRIBUTING.md`, `test/default/test_workflow_lint.py`, `pyproject.toml` (`[tool.pytest.ini_options]`),
  `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md`.
- Tests executed: `uv run python -m pytest test/default/test_workflow_lint.py -o addopts="" -q` →
  **8 passed**; `uv run python -m pytest test/plan-marshall/manage-config/test_branch_prefix_allowlist.py
  test/plan-marshall/manage-config/test_merge_group_trigger.py -o addopts="" -q` → **4 passed**.
- **Mutation checks (2), both on `.github/workflows/opencode-generate-check.yml`.** `git diff --quiet`
  returned 0 (file clean) before each; byte-level backup taken to the scratchpad and restored by
  copy-back (never `git checkout`/`restore`/`stash`); `git diff --quiet` returned 0 again after
  restore. (a) Re-introduced `echo "${{ github.ref_name }}"` into the `run:` block →
  `test_workflows_have_no_context_expression_in_run_blocks` **FAILED** (1 failed, 7 passed).
  (b) Deleted the top-level `permissions:` block →
  `test_workflows_declare_top_level_permissions` **FAILED** (1 failed, 7 passed). Both guards are
  non-vacuous.
- **D1 runtime reproduction executed** (scratchpad, not the repo). Env-passing form
  (`REF_NAME='v1.0"; touch pwned; echo "'` + `dist_tag="claude/${REF_NAME}"`): marker file **not**
  created, `dist_tag` held the full literal `claude/v1.0"; touch pwned; echo "`. Old spliced form
  (the ref substituted into the script source): marker file `pwned` **was** created. The plan's
  required metacharacter check reproduces.
- **Linter blind-spot probe:** loaded `test_workflow_lint.py` via `importlib` and called
  `_run_block_context_violations` on three synthetic shapes (results in G2 below).
- Tree-wide sweeps (`grep -rn`, excluding `.git`/`.pyprojectx`/`target`): `issues/new/choose`,
  `tally.so`, `commercial licens*`, `contents: write`, `uv-installer.sh`, `irm`,
  `pull_request_template|CODEOWNERS` (via `git ls-files`), `claude-distribute` in docs.
- Supersession checks: `git log --oneline -- .github/workflows/python-verify.yml` and
  `git log --oneline -- doc/refactor/02-verification-protocol.md`, then read the superseding commits
  `24271bca` (#1246) and `bb858993` (#1275) in full.
- Re-derived: `uv.lock` = **83078 bytes**, **19** `[[package]]` entries; `.github/workflows/` holds
  **7** workflow files; the automatic-review registry declares **3** `author_login` values
  (`coderabbitai`, `sourcery-ai`, `cuioss-review-bot`).

Not attempted: any GitHub API call for PR #1230's check-run history, and any re-run of `./pw verify`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | Close template-injection surface | No context expression inside any `run:` block in that workflow | Yes | Yes | Yes | Yes | `.github/workflows/claude-distribute.yml:120-142` — `env:` block (`DIST_TAG_PREFIX`, `REF_NAME`, `BRANCH_NAME`, `TARGET_NAME`) + quoted `"${REF_NAME}"`. `grep -n '\${{'` on that file: 17 hits, all in `name:`/`concurrency:`/`with:`/`env:`, none in a `run:` body. Runtime reproduction: old form fires `touch pwned`, new form does not. |
| D2 | Least-privilege `permissions:` on generator-check | Declares read-only content access | Yes | Yes | Yes | Yes | `.github/workflows/opencode-generate-check.yml:9-12` — `permissions:\n  contents: read`. Mutation check (b) proves the guard catches its removal. |
| D3 | Narrow distribution write scope | Workflow-level default is read | Yes | Yes | Yes | Yes | `.github/workflows/claude-distribute.yml:14-20` — `contents: read`. Both writes use the release-bot token: `:111` `personal_token:` and `:147` `github_token:` = `steps.release-token.outputs.token`. Tag is created locally (`:141-144`) before the push step. |
| D4 | GATE — settle ruleset, decide 3 items | Ruleset requirements known and all three decided together | Partly (proposals) | Yes | Yes | Yes | Ruleset unreachable; run recorded three options-and-consequences proposals and made **no** blind change. Confirmed at HEAD: no `CODEOWNERS` (`git ls-files` → no match); `opencode-generate-check.yml:4-8` still path-filtered; `python-verify.yml:36-38` grants unchanged (`contents: read`, `pull-requests: read`). The plan's ⚠ explicitly permits the proposal path. |
| D5 | Stop duplicate CI runs | One push produces one verify run | Yes, then **superseded** | Yes for the landed text; the stated *rationale* was wrong | **No** — see below | n/a | Landed `concurrency:` at `python-verify.yml` shared one group across push and `pull_request`. **Reverted in substance by `24271bca` (#1246), one day later**, after it planted a red required `verify / conclusion` on PR #1234 and blocked its merge. HEAD group key now includes `${{ github.event_name }}`. |
| D6 | Fix vendored wrapper install fallback | The fallback works | Yes | Yes | Yes | Yes | `pw:211` — `curl --proto '=https' --tlsv1.2 -LsSf {release_base_url}/uv-installer.sh \| sh`; stray `irm` gone. `grep -n irm pw pw.bat` → one hit, the legitimate PowerShell branch at `pw:208`. Tree-wide `uv-installer.sh` sweep: the only surviving bad copy is `.pyprojectx/…/pw.py`, confirmed git-ignored (`git check-ignore -v` → `.gitignore:52`). |
| D7 | Reconcile three private-contact channels | They cross-reference each other consistently | Yes | Yes | Yes | Yes | `LICENSE.md:11-17`, `README.md:114`, `.github/ISSUE_TEMPLATE/config.yml:4` all point at `https://tally.so/r/9qalQY`; `SECURITY.md:20-22` → LICENSE.md, `LICENSE.md:15-17` → SECURITY.md. Sweeps: `issues/new/choose` survives only inside this plan's own report; `tally.so` appears in exactly the 3 intended files; `doc/developer/why-this-license.adoc:38` defers to LICENSE.md rather than routing separately. |
| D8 | Decide on a PR template | The decision is recorded either way | Yes (decision) | Mostly — one unsupported rationale clause | Yes | Yes | Decision "no PR template" recorded in report §D8. Confirmed absent at HEAD (`git ls-files \| grep -i pull_request_template` → no match). `CONTRIBUTING.md:22` says "Use issue templates if available" — the report's reading is correct. |
| D9 | Workflow-lint control | A lint check asserts D1 and D2 rather than relying on review | Yes | Yes | Yes, with two false-negative shapes | Yes for the declared scope | `test/default/test_workflow_lint.py` — 8 tests, all pass; collected by `pyproject.toml:102` (`testpaths = ["test"]`). Both real-tree guards proven to go RED under mutation. Blind spots in G2. |

### D5 — the one deliverable that is not a clean pass

`.github/workflows/python-verify.yml`, `concurrency:` block. As landed, the group key was
`${{ github.workflow }}-${{ github.event.pull_request.head.ref || github.ref_name }}` with
`cancel-in-progress: ${{ github.event_name == 'pull_request' }}` — one group shared by the push and
`pull_request` events for the same branch. The landed comment and `report-01.md` both justify this
with: "the run that produces the required `verify / conclusion` check (the pull_request run) is NEVER
cancelled by a competing push run."

That premise is false, and the tree proves it. The **push** run also reports a `verify / conclusion`
check on the same head SHA. `24271bca` (#1246, landed the next day) records the observed
consequence on PR #1234: the `pull_request` run cancelled the push run's `gate` job 4 seconds into a
7-second decision; the always-reporting `conclusion` job then hard-failed
(`gate job did not succeed (cancelled)`), planting a red required check that returned
`405 Repository rule violations found — Required status check "verify / conclusion" is failing` on a
merge attempt. Measured incidence: 2 of the last 30 push runs. This is exactly the failure mode
`plan.md` flagged in bold ("A mistake here breaks the merge gate for every other plan in flight").

The same commit also establishes that D5's premise about the *problem* was under-verified. The plan
asserted "both the push and pull-request triggers fire, running the full verify suite twice per push"
and labelled it derivable entirely from the workflow files. Both triggers do fire, but collapsing the
duplicate was **already** the reusable workflow's `gate` job's responsibility (in place since #1133,
before this plan): a push whose commit is covered by an open PR skips the heavy verify and reports
green in ~17s. #1246's verdict on the concurrency change is explicit: "The cancellation bought
nothing to begin with." Reading only the two trigger blocks — which the plan's claim-label table
authorised — could not have shown that, because the deciding behaviour lives in an out-of-repo
reusable workflow.

Net position at HEAD: D5's done-when ("one push produces one verify run") is met, but by the
pre-existing gate, not by this plan's change. What survives of the change is the narrowed benefit
#1246 kept — `cancel-in-progress` within the `pull_request` class only, so a new push cancels that
PR's own obsolete run. Per the verification method's case (b), the mechanism is **superseded** rather
than a still-open gap; the residue is that nothing guards the invariant #1246 had to restore (G1).

### D8 — one unsupported rationale clause

`report-01.md` §D8 states the decision's context as: "the tooling (CLAUDE.md, cloud-plan-lane) checks
for a PR template and proceeds gracefully when none exists". Grepping
`pull_request_template|pull request template|PR template` across `CLAUDE.md`, `.claude/` (all 15
skills, including `cloud-plan-lane`), and `marketplace/` returns **zero** hits. The decision itself is
sound and recorded; only this supporting clause is unsupported by the tree. (The instruction that
does exist is the GitHub MCP server's own tool guidance, which is not either of the two named
sources.)

## Report accuracy

Contradictions found:

1. **D5 rationale (high).** `report-01.md`'s D5 row and its Findings §2 state that the concurrency
   design is "verified safe … a push run never cancels a PR run and the required `verify / conclusion`
   check is never lost". The tree contradicts this: `24271bca`'s commit message documents the required
   check being lost precisely this way on PR #1234, and reverts the shared-group design. The report's
   pre-PR sub-agent verdict "D5 verified as a sound static design" is likewise contradicted.
2. **D5 residue (medium).** The Residue section predicts "the next `feature/`/`fix/`/`chore/` PR after
   this lands will show one verify run per push." What the next such push actually showed was an
   intermittent red required check. The prediction was not merely unobserved — it was falsified.
3. **D8 rationale (low).** "the tooling (CLAUDE.md, cloud-plan-lane) checks for a PR template" — zero
   matches across `CLAUDE.md`, `.claude/`, `marketplace/` (detail above).
4. **D4.3 citation (cosmetic).** The report writes the reusable-workflow reference as
   `…reusable-pyprojectx-verify.yml@v0.19.0`. The file has carried a pinned SHA since #1133:
   `@4c508c662620fcc7c374e0a54d35ac84416b8140 # v0.19.0`. The version is right; the form is not.

Checked and found accurate — no contradiction: the D1 grep claim (17 `${{` hits in
`claude-distribute.yml`, all outside `run:` bodies); the D1 metacharacter reproduction (independently
re-executed, same outcome both ways); the D3 token-routing claim (both writes read
`steps.release-token.outputs.token`); the D6 hand-patch and its "no fixed upstream release" framing
(the only remaining bad copy is the git-ignored `.pyprojectx/` cache); the D7 "no `issues/new/choose`
licensing pointer remains" sweep; the D4.1 and D8 asserted absences (`CODEOWNERS`,
`pull_request_template` — both re-derived via `git ls-files`); the D4.2 path-filter fact; the D4.3
grant fact (`contents: read` + `pull-requests: read`); the `uv.lock` re-verification (83078 bytes, 19
packages — "83 KB … locks real dependencies" is right); the reviewer-registry population (3
`author_login` values, matching the three named); the D9 test's existence, collection, and passing
state; the "triggers unchanged" claim (the `on:` block is byte-identical across `86d5298a` and
`24271bca`, and both invariant tests still pass); and the `doc/refactor` sketch fix (present in the
landed diff — the file was later deleted wholesale by #1275).

## Out-of-scope compliance

Clean. The landed diff touches 11 paths, every one of them inside the plan's Expected surface or its
own plan directory: the three named workflows, `pw`, `SECURITY.md`, `LICENSE.md`, the plan dir
(`plan.md` rename + `report-01.md`), plus two adjacent touches the report declares —
`README.md` (D7's third licensing route, necessary for "they cross-reference each other
consistently") and `doc/refactor/02-verification-protocol.md` (the stale D2 sketch, disclosed as
Finding #3). No undeclared collateral change. The three declared out-of-scope boundaries all held:
`uv.lock` is untouched by the diff; the verify workflow's *content* is unchanged (only `concurrency:`
was added, `on:` and `with:` are identical); and the security-mailbox confirmation was recorded as
owed rather than claimed. The run also correctly declined to add a `CODEOWNERS`, a PR template, or a
permissions change against an unknown ruleset.

## Residue carried forward

| Report residue | Status in today's tree |
|---|---|
| **D4 — three open points** (code-owners enforcement; whether the path-filtered generator check should be required; whether the reusable verify workflow needs write scope) | **Still open.** No `CODEOWNERS` (`git ls-files` → no match); `opencode-generate-check.yml:4-8` still path-filtered; `python-verify.yml:36-38` grants unchanged. Nothing in the tree records an operator answer. |
| **D7 — owed:** confirm `contact@cuioss.de` is monitored | **Still owed.** Operator action; not settleable from the repository. `SECURITY.md:14` still names the mailbox. |
| **D5 — runtime single-run observation deferred** | **Closed, adversely.** The next real push run did exercise it: #1246 measured the result and reverted the mechanism. |
| **D6 — optional upstream pyprojectx bug report** | **Unknown/still open.** `pw:211` is hand-patched locally; whether an upstream report was filed is not visible from this repository. |

## What could NOT be verified

- **The branch-protection ruleset itself.** Not visible from the tree; D4's entire premise. Unchanged
  since the run.
- **Whether the reusable workflow `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml`
  needs `pull-requests: write` / `checks: write`** (D4.3), and **whether its `gate` job in fact
  collapses the push/PR duplicate today** (the mechanism D5's done-when now rests on). Both live in
  another repository. #1246's measured re-run is the best available evidence and is second-hand here.
- **The `./pw verify` figures** in the report (`19624 passed, 14 skipped`, `mypy … 399` / `734` source
  files). Not re-run — a full verify is not a cheap check, and the tree has moved many commits since.
- **The 11-commit / per-commit-gate / `Co-Authored-By`-trailer claims.** The branch
  `claude/ci-supply-chain-hardening-9xmggr` no longer exists locally or on any remote ref in this
  clone (`git branch -a --list '*ci-supply-chain*'` → empty), and the PR was squash-merged, so
  individual commits are unrecoverable.
- **PR #1230's own check-run history** (the D5 own-PR fixture). No GitHub API call was made; the
  report's disclosure that the fixture is degenerate on a `claude/*` branch is consistent with
  `python-verify.yml:5`'s push allowlist, which does not list `claude/*`, and is accepted on that
  basis.
- **Whether `claude-distribute.yml` has run green since D3 narrowed its token.** Its triggers are
  `push: main` and `v*` tags; no run log is visible from the tree. The reasoning that no step needs
  default-token write was checked step by step and holds by inspection.
