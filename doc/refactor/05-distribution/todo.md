# 05 — Distribution — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (whenever a CI workflow or release artifact is added), **documentation** (whenever installation paths or update strategy change).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Briefing

Read these documents in full **before touching anything**. Do not start the tasks below until you have done so.

- [ ] Read [`plan.md`](plan.md) — this cluster's distribution architecture: Claude Code plugin discovery (manifest at repo root, `pluginRoot`), OpenCode install paths, CI/CD pipeline, versioning strategy, hosting comparison, update strategy
- [ ] Read [`../02-build-system/plan.md`](../02-build-system/plan.md) — distribution wraps the generator; you must know what the generator produces (singular layout, dual-emit, body transforms)
- [ ] Read [`../principles.md`](../principles.md) — cross-cutting rules
- [ ] Read [`../README.md`](../README.md) — refactor overview, terminology, dependency graph
- [ ] Confirm to yourself you have understood the marketplace.json relocation, the singular-vs-plural directory tension, and which install paths are CI-tested vs documented-only
- [ ] If **any** part is unclear or contradictory, **stop and ask the user** before continuing — do not guess

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-05-distribution`
- [ ] Confirm cluster 02 (build system) has been merged to `main` and pulled locally — distribution depends on the generator existing
- [ ] If using cluster 04 CI gates, ensure they are merged too so the distribution workflow can layer on top

## Tasks

### 1. Move `marketplace.json` to repo root
- [ ] Implementation: move `marketplace/.claude-plugin/marketplace.json` → `.claude-plugin/marketplace.json` at repo root. Update `metadata.pluginRoot` to `./marketplace/bundles` and adjust `source` paths so each entry resolves correctly. Confirm Claude Code's `/plugin marketplace add owner/repo` discovers it.
- [ ] Testing: locally clone the repo and run `/plugin marketplace add ./` (or the documented add-from-path form); assert all 10 bundles register
- [ ] Documentation: README at repo root reflects the new manifest location and install path

### 2. CI workflow — Build job
- [ ] Implementation: GitHub Actions job that runs on `push: branches:[main]`, `tags: ['v*']`, `pull_request: branches:[main]`, and `workflow_dispatch`. Sets up Python 3.12, installs deps, runs `./pw generate -- --target opencode --output dist/opencode/` and (when implemented) other targets. Tars artifacts as `plan-marshall-opencode-${GITHUB_SHA}.tar.gz`. Uploads via `actions/upload-artifact@v4`.
- [ ] Testing: PR triggers the build; artifact appears in the run output

### 3. CI workflow — Drift Check job
- [ ] Implementation: separate job that runs `./pw generate -- --target claude --output target/claude`. Exits non-zero on drift. Print TOON diff to the workflow summary.
- [ ] Testing: PR with deliberate `plugin.json` orphan triggers a failed drift-check; PR with consistent state passes

### 4. CI workflow — GitHub Pages publish (on push to main)
- [ ] Implementation: `publish-pages` job that depends on `build` + `drift-check`. Downloads artifacts, prepares `_site/opencode/latest/` from the OpenCode tarball, copies install docs to `_site/index.md`, uploads + deploys via `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4`. Confirm `https://{org}.github.io/{repo}/opencode/latest/` becomes the canonical install URL.
- [ ] Testing: merge to main triggers Pages deploy; URL serves the expected layout
- [ ] Documentation: include the canonical Pages URL in `doc/distribution.md`

### 5. CI workflow — GitHub Releases (on tag)
- [ ] Implementation: `release` job that runs on `refs/tags/v*`. Uses `softprops/action-gh-release@v1` to attach `dist/*.tar.gz`. Body includes installation snippets per cluster 05 "Job 4: Publish GitHub Release (on tag)".
- [ ] Testing: tag a `v0.x.x` release on a fork or scratch repo; assert tarballs attach and body renders

### 6. Versioning and tag conventions
- [ ] Documentation: write the versioning section into `doc/distribution.md` per cluster 05 "Versioning Strategy" (schema, tag format, cadence, what gets versioned). Add a `RELEASE.md` or extend `CONTRIBUTING.md` with the tag command sequence.

### 7. Installation documentation — Claude Code primary path
- [ ] Documentation: in `doc/distribution.md`, document `/plugin marketplace add {org}/plan-marshall` + `/plugin install plan-marshall` (and `/plugin install pm-dev-java`, etc.). Document `/plugin marketplace update {org}/plan-marshall`.
- [ ] Testing: end-to-end validation on a fresh clone — install, verify all 10 bundles loadable

### 8. Installation documentation — OpenCode primary path
- [ ] Documentation: in `doc/distribution.md`, document `opencode-marketplace install {pages-url}/opencode/latest/` and the GitHub-Releases tarball alternative. Note the `opencode-marketplace` directory shape (singular `skill/`/`agent/`/`command/`) matches the emitter output.
- [ ] Testing: install the artifact via `opencode-marketplace` against the published Pages URL; verify skills appear in OpenCode

### 9. Update strategy documentation
- [ ] Documentation: write the "Update Strategy" section into `doc/distribution.md` covering Claude Code (`/plugin marketplace update`) and OpenCode (`opencode-marketplace update`) primary paths plus alternatives

### 10. Hosting comparison + risk register
- [ ] Documentation: include the hosting comparison table and the risk register from cluster 05 in `doc/distribution.md`

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"` (Bash timeout ≥ 600000 ms). Inspect TOON.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"` (Bash timeout ≥ 600000 ms).
- [ ] Both `status: success` before "Ship".

## Ship

Use `PLAN_ID=refactor-05-distribution` in the commands below. Capture the PR number into `PR=<n>` after `ci pr create`.

- [ ] Commit all changes (conventional commits)
- [ ] Push the feature branch:
      `git push -u origin feature/refactor-05-distribution`
- [ ] Allocate a body file:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id refactor-05-distribution`
      (write PR body to the returned path)
- [ ] Create the PR:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title "feat(dist): repo-root marketplace.json, CI build/release pipeline, install docs" --plan-id refactor-05-distribution --base main`
- [ ] Wait 5 minutes for review automation:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number $PR --timeout 300`
- [ ] Fetch unresolved comments and reviews:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments --pr-number $PR --unresolved-only`
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews  --pr-number $PR`
- [ ] For each unresolved comment (use `thread_id` from `ci pr comments` output):
      - **Real issue + sensible fix** → apply, commit, push; reply to the inline thread:
        `... pr prepare-comment --plan-id refactor-05-distribution --for thread-reply --slot reply-<n>` (write text), then
        `... pr thread-reply --pr-number $PR --thread-id <THREAD_ID> --plan-id refactor-05-distribution --slot reply-<n>`,
        then `... pr resolve-thread --thread-id <THREAD_ID>` once the fix has landed.
        For PR-level (non-inline) comments use `pr prepare-comment --for reply` + `pr reply --pr-number $PR ...` instead.
      - **Wrong / out of scope** → ask the user before skipping.
- [ ] After comment handling, **wait for the user to review** the PR.

## Close

- [ ] User has approved the PR
- [ ] Merge with squash + delete branch:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge --pr-number $PR --strategy squash --delete-branch`
- [ ] `git switch main && git pull origin main`
- [ ] Mark this TODO as **completed**
