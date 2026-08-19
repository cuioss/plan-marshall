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
(The check-run gap was closed later by the independent adversarial pass — see § Adversarial review. The
`./pw verify` re-run was not.)

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | Close template-injection surface | No context expression inside any `run:` block in that workflow | Yes | Yes | Yes | Yes | `.github/workflows/claude-distribute.yml:120-142` — `env:` block at `:128-132` (`DIST_TAG_PREFIX`, `REF_NAME`, `BRANCH_NAME`, `TARGET_NAME`) + quoted `"${REF_NAME}"` in the `run:` body at `:133-141`. `grep -n '\${{'` on that file: **18** matching lines (**19** occurrences — `:118` carries two), all in `name:`/`concurrency:`/`with:`/`env:`, none in a `run:` body. *(Corrected during adversarial review: the original figure of 17 does not re-derive, at HEAD or at `86d5298a`. The substance — none inside a `run:` body — holds.)* Runtime reproduction: old form fires `touch pwned`, new form does not. |
| D2 | Least-privilege `permissions:` on generator-check | Declares read-only content access | Yes | Yes | Yes | Yes | `.github/workflows/opencode-generate-check.yml:12-13` — `permissions:` / `  contents: read` (`:9-11` is its explanatory comment). Mutation check (b) proves the guard catches its removal — but only its removal, not its widening (G5). |
| D3 | Narrow distribution write scope | Workflow-level default is read | Yes | Yes | Yes | Yes | `.github/workflows/claude-distribute.yml:20-21` — `permissions:` / `  contents: read` (`:14-19` is its explanatory comment). Both writes use the release-bot token: `:111` `personal_token:` and `:147` `github_token:` = `steps.release-token.outputs.token`. Tag is created locally (`git tag -a` at `:139-141`) before the push step at `:143-149`. |
| D4 | GATE — settle ruleset, decide 3 items | Ruleset requirements known and all three decided together | Partly (proposals) | Yes | Yes | Yes | Ruleset unreachable; run recorded three options-and-consequences proposals and made **no** blind change. Confirmed at HEAD: no `CODEOWNERS` (`git ls-files` → no match); `opencode-generate-check.yml:4-7` still path-filtered; `python-verify.yml:37-39` grants unchanged (`contents: read`, `pull-requests: read`). The plan's ⚠ explicitly permits the proposal path. D4.2's Option A now has direct empirical support — see § Adversarial review. |
| D5 | Stop duplicate CI runs | One push produces one verify run | Yes, then **superseded** | Yes for the landed text; the stated *rationale* was wrong | **No** — see below | n/a | Landed `concurrency:` at `python-verify.yml` shared one group across push and `pull_request`. **Reverted in substance by `24271bca` (#1246), one day later**, after it planted a red required `verify / conclusion` on PR #1234 and blocked its merge. HEAD group key now includes `${{ github.event_name }}`. |
| D6 | Fix vendored wrapper install fallback | The fallback works | Yes | Yes | Yes | Yes | `pw:211` — `curl --proto '=https' --tlsv1.2 -LsSf {release_base_url}/uv-installer.sh \| sh`; stray `irm` gone. `grep -n irm pw pw.bat` → one hit, the legitimate PowerShell branch at `pw:208`. Tree-wide `uv-installer.sh` sweep: the only surviving bad copy is `.pyprojectx/…/pw.py`, confirmed git-ignored (`git check-ignore -v` → `.gitignore:52`). |
| D7 | Reconcile three private-contact channels | They cross-reference each other consistently | Yes | Yes | Yes | Yes | `LICENSE.md:11-17`, `README.md:114`, `.github/ISSUE_TEMPLATE/config.yml:4` all point at `https://tally.so/r/9qalQY`; `SECURITY.md:20-22` → LICENSE.md, `LICENSE.md:15-17` → SECURITY.md. Sweeps: `issues/new/choose` survives only inside this plan's own report; `tally.so` appears in exactly the 3 intended files; `doc/developer/why-this-license.adoc:38` defers to LICENSE.md rather than routing separately. |
| D8 | Decide on a PR template | The decision is recorded either way | Yes (decision) | Mostly — one unsupported rationale clause | Yes | Yes | Decision "no PR template" recorded in report §D8. Confirmed absent at HEAD (`git ls-files \| grep -i pull_request_template` → no match). `CONTRIBUTING.md:22` says "Use issue templates if available" — the report's reading is correct. |
| D9 | Workflow-lint control | A lint check asserts D1 and D2 rather than relying on review | Yes | Yes | Yes, with three false-negative shapes | Yes for the declared scope | `test/default/test_workflow_lint.py` — 8 tests, all pass (re-run: `8 passed`), collected by `pyproject.toml:102` (`testpaths = ["test"]`), 8 collected under the default `addopts`. Both real-tree guards proven non-vacuous: the D1 guard returns **3** violations against the real pre-fix bytes (`git show 86d5298a^:.github/workflows/claude-distribute.yml`) and **0** post-fix. Blind spots in G2 (wide dash), G4 (plain-scalar continuation) and G5 (permissions asserted present, not read-only). |

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
| **D4 — three open points** (code-owners enforcement; whether the path-filtered generator check should be required; whether the reusable verify workflow needs write scope) | **Still open.** No `CODEOWNERS` (`git ls-files` → no match); `opencode-generate-check.yml:4-7` still path-filtered; `python-verify.yml:37-39` grants unchanged. Nothing in the tree records an operator answer. D4.2 now has empirical support for its recommended option (§ Adversarial review); D4.1 and D4.3 remain undecided. |
| **D7 — owed:** confirm `contact@cuioss.de` is monitored | **Still owed.** Operator action; not settleable from the repository. `SECURITY.md:13` still names the mailbox. |
| **D5 — runtime single-run observation deferred** | **Closed, adversely.** The next real push run did exercise it: #1246 measured the result and reverted the mechanism. |
| **D6 — optional upstream pyprojectx bug report** | **Unknown/still open.** `pw:211` is hand-patched locally; whether an upstream report was filed is not visible from this repository. |

## What could NOT be verified

- **The branch-protection ruleset itself.** Not visible from the tree; D4's entire premise. Unchanged
  since the run.
- **Whether the reusable workflow `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml`
  needs `pull-requests: write` / `checks: write`** (D4.3). Still unverified: the workflow lives in
  another repository, and a direct read was attempted during adversarial review and refused
  (`Access denied: repository "cuioss/cuioss-organization" is not configured for this session`).
  - **Superseded:** the sibling claim that **whether the `gate` job in fact collapses the push/PR
    duplicate today** could not be verified. It can be, and was, from this repository's own check-run
    history — see § Adversarial review. It is no longer second-hand.
- **The `./pw verify` figures** in the report (`19624 passed, 14 skipped`, `mypy … 399` / `734` source
  files). Not re-run — a full verify is not a cheap check, and the tree has moved many commits since.
- **The 11-commit / per-commit-gate / `Co-Authored-By`-trailer claims.** The branch
  `claude/ci-supply-chain-hardening-9xmggr` no longer exists locally or on any remote ref in this
  clone (`git branch -a --list '*ci-supply-chain*'` → empty), and the PR was squash-merged, so
  individual commits are unrecoverable.
- ~~**PR #1230's own check-run history** (the D5 own-PR fixture).~~ **Now verified** during adversarial
  review via `pull_request_read(get_check_runs)` — see § Adversarial review. The report's
  degenerate-fixture disclosure is confirmed, not merely accepted.
- **Whether `claude-distribute.yml` has run green since D3 narrowed its token.** Its triggers are
  `push: main` and `v*` tags; no run log is visible from the tree. The reasoning that no step needs
  default-token write was checked step by step and holds by inspection.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap (there were none — the highest carried severity was `medium`), every
deliverable row marked a clean pass, and every "swept the tree, clean" claim were re-derived. Concretely:

*Figures re-derived from the tree, not repeated:* landed footprint (`git show --stat 86d5298a` → **11
files, 546 insertions, 17 deletions** — upheld); `${{` count in `claude-distribute.yml` (**18** lines /
19 occurrences, **not** 17 — corrected); `.github/workflows/` file count (**7** — upheld); `uv.lock`
(**83078** bytes, **19** `[[package]]` — upheld); `author_login` registry population (**3**:
`sourcery-ai`, `coderabbitai`, `cuioss-review-bot` — upheld); `.claude/skills/` count (**15** — upheld);
test totals (`test_workflow_lint.py` → **8 passed**, 8 collected under default `addopts`;
`test_branch_prefix_allowlist.py` + `test_merge_group_trigger.py` → **4 passed** — both upheld);
supersession SHAs (`24271bca` = #1246, `bb858993` = #1275 which deleted `doc/refactor/` wholesale — both
upheld). Every file:line citation in the deliverable table and the residue table was opened and
corrected where it pointed at a comment line rather than the cited construct (D2, D3, D4, G1, G3, and
`SECURITY.md`).

*Mechanism clauses confirmed at their own file and symbol:* the landed concurrency key was read out of
`git show 86d5298a:.github/workflows/python-verify.yml` (line 27) and matches the quoted expression
exactly; `24271bca`'s full commit body was read and carries the 4s-cancel / 7s-gate / `405 Repository
rule violations found` / "2 of the last 30 push runs" narrative verbatim; the `on:` blocks of
`86d5298a` and `24271bca` were diffed and are byte-identical (the only difference inside lines 1–12 is
a comment line **inside** the `concurrency:` block).

*Functions executed, not read:* `_run_block_context_violations` and `_has_top_level_permissions` were
loaded via `importlib` and **called** — on the two shapes G2 named, on a third shape (wide dash + block
scalar), on two negative controls, on the **real pre-fix bytes** of `claude-distribute.yml`
(`git show 86d5298a^:…` → 3 violations) and on the post-fix file (0 violations), and on
`opencode-generate-check.yml` with its scope swapped to `contents: write` and to `write-all`. The
proposed remedies for G2 and G4 were prototyped in a scratch copy and run against all 7 real workflows
to confirm they introduce no false positive. The D1 runtime reproduction was **re-executed
independently**: with `REF_NAME='v1.0"; touch pwned; echo "'` the env-passing form left `dist_tag`
holding the full literal `claude/v1.0"; touch pwned; echo "` and created no marker; the old spliced
form created `pwned`. Same outcome both ways.

*Sweeps re-run with broader patterns than the originals:* the D8 clause was swept with
`pull[_ -]?request[_ -]?template|PULL_REQUEST_TEMPLATE|\bPR template` **and** a bare `template` sweep
over `CLAUDE.md` + `.claude/` — zero relevant hits either way. G3's sweep was widened from
`template injection|script injection|interpolat` to
`run:|\$\{\{|github\.ref_name|GitHub Actions context|workflow_run|pull_request_target` across the whole
persona skill (zero hits) and then to the whole `marketplace/` tree (only generic `shell=True` guidance,
never the Actions shape). `contents: write` was swept tree-wide (three hits, all legitimate:
`dependabot-auto-merge.yml`'s job-level grant and two test fixtures). `tally.so` (3 intended files),
`issues/new/choose` (only this plan's own documents), `uv-installer.sh` and `irm` (the sole surviving
bad copy is the git-ignored `.pyprojectx/` cache, `git check-ignore -v` → `.gitignore:52`) all upheld.

*New evidence gathered that this document had listed as unobtainable:* `pull_request_read(get_check_runs)`
on PR **#1230** and PR **#1234**, plus `actions_get(get_workflow_run)` on run `31864317583`. See
"Documents corrected" below.

**Not re-checked.** The branch-protection ruleset (still not exposed by any available tool). The
reusable workflow's own source — a read of `cuioss/cuioss-organization` was attempted and refused
(`Access denied: repository … is not configured for this session`), so D4.3 stays open. The `./pw
verify` figures (`19624 passed`, `mypy … 399`/`734` source files) — still not re-run. The 11-commit /
per-commit-gate / trailer claims — the branch is still absent from every ref
(`git branch -a --list '*ci-supply-chain*'` → empty). `report-01.md`'s reviewer-participation verdicts
were not re-fetched from the PR's comment surfaces. No source file was mutated on disk at any point:
`git diff --quiet` on `.github/workflows/opencode-generate-check.yml` returned 0 before and after, and
its md5 is unchanged — every guard probe was done on in-memory copies instead.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| **Verdict** | `implemented-with-gaps` | **upheld** | No deliverable is unimplemented: D1/D2/D3/D6/D7/D9 landed and hold at HEAD; D4 and D8 took the plan's own explicitly-authorised decision/proposal path; D5 landed and was then corrected by #1246. `partially-implemented` is reserved for an unimplemented deliverable and does not apply. |
| D1 | Injection surface closed; no context expression in any `run:` block | **upheld, figure corrected** | Runtime reproduction re-executed independently (marker fires on the old form, not the new). Linter run on the real pre-fix bytes: 3 offending `run:` blocks; post-fix: 0. The `${{` count is 18 lines / 19 occurrences, not 17 — corrected in the D1 row. (The plan's "two context interpolations" re-derives as the two `github.ref_name` occurrences, pre-fix `:112` and `:117`; the other offending blocks interpolated trusted `matrix.*` values and were fixed too.) |
| D2 | Declares read-only content access | **upheld, cite corrected** | `:12-13` at HEAD, not `:9-12` (`:9-11` is comment). Guard scope shortfall filed as G5. |
| D3 | Workflow-level default is read; no step needs default-token write | **upheld, cites corrected** | `permissions:`/`contents: read` at `:20-21`; tag created locally at `:139-141` (not `:141-144`); both writes read `steps.release-token.outputs.token` at `:111` and `:147`. Every step re-inspected: checkout/generate/fetch are read-only, both pushes carry the release-bot token. |
| D4 | Ruleset unreachable; proposals recorded, no blind change | **upheld, strengthened** | Absences re-derived (`git ls-files` → no `CODEOWNERS`, no PR template). D4.2's recommended option now has direct empirical support: PR #1230's check-run set contains no `opencode-generate-check` context (it touched none of the filtered paths) and the PR merged regardless — the path-filtered check is **not** currently required. D4.1 and D4.3 remain undecided; D4.3's blocker was re-confirmed by a refused cross-repo read. |
| D5 | Landed, then superseded by #1246; done-when met by the pre-existing gate | **upheld, now first-hand** | #1246's commit body read in full and matches. The gate mechanism it relies on is no longer second-hand: on PR #1234's head SHA, workflow run `31864317583` (`event: "push"`, branch `dependabot/pip/ruff-gte-0.16.2`, `run_attempt: 2`) shows `verify / gate` **success in 7s**, `verify / verify` **skipped**, `verify / conclusion` **success**, while the `pull_request` run on the same SHA ran `verify / verify` to green over ~10 minutes. That is the gate collapsing the push/PR duplicate, measured from this repository, with the 7-second gate duration #1246 named. |
| D6 | Fallback fixed; only surviving bad copy is git-ignored | **upheld** | `pw:211` carries the clean `curl … uv-installer.sh \| sh`; the sole `irm` hit is the legitimate PowerShell branch at `pw:208`; `.pyprojectx/…/pw.py:211` still splices `irm` and is ignored via `.gitignore:52`. |
| D7 | Three channels cross-reference consistently | **upheld, cite corrected** | `tally.so` in exactly `LICENSE.md:13`, `README.md:114`, `.github/ISSUE_TEMPLATE/config.yml:4`; `SECURITY.md:20-22` → LICENSE.md; `LICENSE.md:15-17` → SECURITY.md; `why-this-license.adoc:38` defers. The mailbox is named at `SECURITY.md:13`, not `:14` — corrected in the residue table. |
| D8 | Decision recorded; one unsupported rationale clause | **upheld** | Re-swept with a broader pattern and then with a bare `template` sweep over `CLAUDE.md` and all 15 `.claude/` skills: still zero. The clause is unsupported; the decision itself stands. |
| D9 | Guard asserts D1 and D2; two false-negative shapes | **upheld, widened** | 8 tests pass and collect. Non-vacuousness re-proved against real pre-fix bytes rather than a synthetic mutation. Three blind spots, not two — see G2/G4/G5. |
| G1 | Concurrency invariant unguarded, `medium` | **upheld, cite corrected** | `concurrency.group` is at `python-verify.yml:34`, not `:33`. A `grep` of the whole `test/` tree for `python-verify`/`concurrency` confirms no assertion over the `concurrency:` block; the two sibling guards touch only `on.push.branches` and `on.merge_group`. Severity `medium` is right: no wrong behaviour or false signal ships today — the key is correct at HEAD — so the `high` bar is not met. |
| G2 | Two false-negative shapes, `low` | **re-severitied and split** | Both shapes reproduced by **executing** the function, and both parse under `yaml.safe_load` to a live injection. They are two independent defects with two independent fixes (a regex width; a missing body walk), so the plain-scalar half is now **G4** and G2 keeps the dash-width half. Both raised `low` → `medium`: this is the sole automated control over the plan's highest-severity finding, and it returns clean on valid-YAML instances of exactly the defect it names. Not `high` — the real tree contains none of these shapes, so no false signal is currently shipped. Cite corrected to `:36` (regex) + `:40-89` (function). |
| G3 | Rule not codified in the security standard, `low` | **upheld, cite corrected and sweep widened** | The CI/CD list runs `:104-108` (five bullets), not `:104-105`. Two broader sweeps (whole persona skill for Actions-specific tokens; whole `marketplace/` tree) both confirm the absence. `low` is right — an omission in guidance, no wrong behaviour. |
| **G4** *(new)* | — | **added** | Split out of G2: the non-block branch of `_run_block_context_violations` (`:83-88`) never walks a multi-line plain-scalar `run:` body. Executed, returns `[]` on a live injection. `medium`. |
| **G5** *(new)* | — | **added** | `_has_top_level_permissions` (`:92-94`) is presence-only; executed, it returns `True` for `contents: write` and for `permissions: write-all`. D2's done-when names *read-only* access, and that half is unguarded. `low` — D2 currently holds, and the guard's own docstring claims no more than presence. |

**Documents corrected.**

*gaps.md* — G2 split into G2 (wide dash) + **G4** (plain-scalar continuation), both re-severitied
`low` → `medium`, both carrying a Fix that was prototyped and validated against the real 7-workflow tree
before being written down. **G5** added (D2's read-only half unguarded, `low`). File:line references
corrected in G1 (`:33` → `:34`), G2 (`:36-38` → `:36` + `:40-89`) and G3 (`:104-105` → `:104-108`).
G1's incidence figure re-attributed as a quote from `24271bca` rather than a re-derived measurement.
Evidence strengthened in G1 (whole-`test/`-tree sweep) and G3 (two broader sweeps). Preamble reworded so
D2 is no longer listed among the gap-free passes without qualification. `**Open items:**` 3 → **5**. A
`## Refuted during adversarial review` section was added recording that nothing was refuted.

*verification.md* — the `${{` count corrected 17 → 18 lines / 19 occurrences; six file:line citations
corrected (D2, D3 ×2, D4 ×2, residue `SECURITY.md`); the D9 row widened from two blind spots to three
and its non-vacuousness evidence upgraded from a synthetic mutation to the real pre-fix bytes; two
entries removed from "What could NOT be verified" (PR #1230's check-run history, and whether the `gate`
job collapses the duplicate — both now settled first-hand), while D4.3's entry was strengthened with the
refused cross-repo read. The headline verdict is unchanged.

**Residual doubt.** In priority order: (1) **D4.3** — the reusable workflow's actual permission needs
remain unread, and a silently-degraded coverage comment or check annotation would be invisible from
here; a reviewer with `cuioss/cuioss-organization` access should read
`reusable-pyprojectx-verify.yml@4c508c66` and settle it. (2) **The ruleset itself** — D4.1 is still an
inference from "PRs do merge", and no tool in this session exposes the rule set; the D4.2 conclusion
above is an observation about one PR, not a read of the configuration. (3) **The `./pw verify` figures**
in `report-01.md` (`19624 passed`, `mypy … 399`/`734`) — never re-derived by either reviewer, and the
tree has moved many commits. (4) Whether `claude-distribute.yml` has actually run green on a `v*` tag
since D3 narrowed the token — still inspection-only, and the first real release is where a missing grant
would surface.
