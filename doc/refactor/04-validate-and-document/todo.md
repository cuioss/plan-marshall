# 04 — Validate and Document — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (whenever a CI job or test fixture is added), **documentation** (whenever a published doc changes — this cluster is documentation-heavy).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-04-validate-document`
- [ ] Confirm clusters 00, 01, 02, and 03 have been merged to `main` and pulled locally

## Tasks

### 1. Drift detection CI gate
- [ ] Implementation: GitHub Actions workflow that runs `./pw generate -- --target claude --output target/claude` on every PR; exits non-zero on drift
- [ ] Testing: PR fixture introduces deliberate orphan `plugin.json` entry — CI must fail; remove orphan — CI must pass
- [ ] Documentation: workflow README + entry in `doc/multi-target-marketplace.adoc`

### 2. OpenCode generation CI gate
- [ ] Implementation: GitHub Actions workflow that runs `./pw generate -- --target opencode --output target/opencode` on every PR; exits non-zero on generation failure (unmapped tool, invalid frontmatter, missing description)
- [ ] Testing: PR fixture introduces an unmapped tool in an agent — CI must fail
- [ ] Documentation: workflow README

### 3. Unit-test suite per cluster 04 "Test Plan — Unit Tests"
- [ ] Implementation: for every row in `plan.md` "Unit Tests" table, write the corresponding test under `test/plan-marshall/`. Includes router dispatch, ClaudeRuntime ops, OpenCodeRuntime ops + no-ops, SessionStart hook, session capture, metrics capture, TOON output, no-op handling, error handling, dual-emit, both body transforms, both executor resolvers
- [ ] Testing: `./pw verify` runs all tests cleanly; coverage report includes platform-runtime modules

### 4. Integration-test suite per cluster 04 "Test Plan — Integration Tests"
- [ ] Implementation: implement every row of the table — fresh-init (Claude + OpenCode variants), session capture, permission configure, permission analyze, permission fix normalize, permission ensure wildcards, permission ensure steps, permission web analyze, the three executor permission ops on OpenCode, bundle sync (Claude + OpenCode), drift detection, OpenCode generation
- [ ] Testing: integration suite runs cleanly under `./pw verify`

### 5. End-to-end test
- [ ] Implementation: scripted E2E covering the 5 steps in `plan.md` "End-to-End Test" — fresh clone, `./pw verify`, generate Claude (zero drift), generate OpenCode (success), generate all
- [ ] Testing: E2E runs cleanly in CI on every PR

### 6. `platform-runtime health-check` script
- [ ] Implementation: implement `health-check --checks {all,permissions,display,mcp-diagnostics}` per cluster 01 spec. Both targets covered.
- [ ] Testing: per-target health-check tests; failure paths documented

### 7. Port refactor plans into canonical docs
- [ ] Implementation: per the porting table in `plan.md`, port:
  - `doc/refactor/README.md` → `doc/multi-target-marketplace.adoc` (umbrella)
  - `doc/refactor/principles.md` → `doc/principles.md`
  - `doc/refactor/01-design-platform-api/plan.md` → `doc/platform-runtime-api.md`
  - `doc/refactor/02-build-system/plan.md` → `doc/build-system.md`
  - `doc/refactor/03-refactor-for-portability/plan.md` → `doc/migration-guide.md`
  - `doc/refactor/05-distribution/plan.md` → `doc/distribution.md`
  - `doc/refactor/06-developer-workflow/plan.md` → `doc/developer-workflow.md`
- [ ] Documentation: follow the "Rules for porting" — present-tense; no plan language; technical specs preserved; cross-references between docs

### 8. Delete `doc/refactor/`
- [ ] Implementation: after porting verified, delete `doc/refactor/` directory entirely
- [ ] Testing: `git grep "doc/refactor"` returns no live references; canonical docs render correctly

### 9. Documentation cross-link audit
- [ ] Implementation: confirm `doc/multi-target-marketplace.adoc` is the umbrella; per-topic docs cross-reference rather than duplicate; no document repeats specifications that live elsewhere
- [ ] Documentation: this is the "documentation matches implemented code" global acceptance criterion

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` (Bash timeout ≥ 600000 ms). Inspect TOON.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` (Bash timeout ≥ 600000 ms).
- [ ] Both `status: success` before "Ship".

## Ship

- [ ] Commit all changes
- [ ] Push the feature branch
- [ ] Create the PR via the CI integration script
- [ ] **Wait 5 minutes** for review automation
- [ ] Handle review comments (apply sensible fixes; ask before skipping)
- [ ] **Wait for user review**

## Close

- [ ] User approval
- [ ] Merge via the CI integration script
- [ ] `git switch main && git pull origin main`
- [ ] Mark this TODO as **completed**
