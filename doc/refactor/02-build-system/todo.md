# 02 — Build System — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (mandatory wherever a script or generator is added), **documentation** (whenever public contract changes).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-02-build-system`
- [ ] Confirm cluster 01 has been merged to `main` and pulled locally (target engine needs the platform-runtime API surface to validate against)

## Tasks

### 1. `marketplace/targets/` skeleton
- [ ] Implementation: create the directory structure in cluster 02 "Architecture" (`base.py`, `generate.py`, `opencode/`, `claude/`, `opencode/templates/`). Empty placeholders permitted; later tasks fill them.
- [ ] Documentation: README at `marketplace/targets/README.md` describing the target framework

### 2. `TargetBase` abstract class
- [ ] Implementation: implement `TargetBase` per the contract in `plan.md` (`name`, `generate`, `supports_agents`, `supports_commands`, `config_dir`)
- [ ] Testing: unit test asserts abstract methods are enforced; a stub subclass passes the contract

### 3. `generate.py` CLI
- [ ] Implementation: CLI entry point with `--target {claude,opencode,all}`, `--output <dir>`, `--bundles <list>`. Reads `TARGET_REGISTRY`. Exits with code 2 on any failure.
- [ ] Testing: smoke tests for each `--target` value; exit-code tests for the failure paths
- [ ] Documentation: `--help` text matches `plan.md` "Build Integration" snippet; pyproject.toml entries match

### 4. Claude target — drift detection
- [ ] Implementation: `claude/target.py` + `claude/drift.py`. Reads each bundle's `plugin.json` and `.claude-plugin/`. Compares to what the generator would produce. Exits 0 (no drift) or 2 (drift, with TOON diff).
- [ ] Testing: introduce a deliberate orphan `plugin.json` entry in a fixture and assert exit 2 + diff; remove orphan and assert exit 0

### 5. OpenCode target — emitter skeleton
- [ ] Implementation: `opencode/target.py` (the `OpenCodeTarget` class implementing `TargetBase`); `opencode/emitter.py` walks the source bundles and writes to `target/opencode/{skill,agent,command}/` (singular layout)
- [ ] Testing: smoke test generates a valid output tree from a fixture bundle

### 6. Frontmatter transform engine
- [ ] Implementation: `opencode/frontmatter.py` reads `mapping.json` and `frontmatter-rules.json`, rewrites Claude frontmatter into OpenCode frontmatter (tools → permissions, model → resolved id, required/optional fields validated)
- [ ] Testing: per-rule unit tests; fail-on-unmapped-tool path returns exit 2

### 7. Body transforms (`body-transforms.py` + `transforms.md`)
- [ ] Implementation: write `opencode/transforms.md` (authoritative spec; copy from `plan.md` "Body Transforms" section). Implement `body-transforms.py` doing exactly the two documented transforms — `Skill:` directive rewrite and slash-command rewrite. Build the slash-command lookup table from a marketplace scan of `user-invocable: true` skills.
- [ ] Testing: regex unit tests for each transform; happy-path + boundary cases (no-match-on-inline-backtick, no-match-on-path-substring); integration test against a fixture skill body
- [ ] Documentation: ensure `transforms.md` and `plan.md` "Body Transforms" stay in sync

### 8. `mapping.json` and `frontmatter-rules.json`
- [ ] Implementation: write the JSON files per cluster 02 "Configuration" section. `mapping.json` owns `tool_permissions` + `model_map`; `frontmatter-rules.json` owns `required_fields` + `optional_fields`. No fields duplicated across files.
- [ ] Testing: schema validation on both files; unit test asserts loader fails fast on malformed input

### 9. User-invocable wrapper template (`templates/user-invocable-command.md`)
- [ ] Implementation: write the template per cluster 02 "User-Invocable Skills (Dual Emission)" with placeholders `{{description}}`, `{{model}}`, `{{skill_id}}`. Implement the dual-emit logic in the emitter that scans for `user-invocable: true`, generates the skill *and* the wrapper command.
- [ ] Testing: dual-emit assertion — for each `user-invocable: true` source skill, both `skill/{bundle}-{skill}/SKILL.md` and `command/{bundle}-{skill}.md` are produced; wrapper substitutions match the source frontmatter; missing-`description` case exits 2

### 10. Adapter migration
- [ ] Implementation: port the working logic from `marketplace/adapters/opencode_adapter.py` into the new target engine (`opencode/frontmatter.py`, `opencode/target.py`, `generate.py`). Upgrade body-`Skill:` annotation to body rewrite per task 7. Delete `marketplace/adapters/`. Update any imports.
- [ ] Testing: existing adapter-level tests are migrated to test the new target engine; old test files are removed; `./pw verify` still passes

### 11. Build integration + gitignore
- [ ] Implementation: add `[tool.pdm.scripts]` entries to `pyproject.toml`. Update `.gitignore` to add `target/opencode/`, `target/claude/`, `.cursor-plugin/`, `.codex-plugin/`.
- [ ] Testing: `./pw generate -- --target claude --output target/claude` runs cleanly; `./pw generate -- --target opencode --output target/opencode` runs cleanly; `./pw generate -- --target all --output target` runs cleanly

## Quality Gate

After every task is done:

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` with Bash timeout ≥ 600000 ms. Inspect the result TOON.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` with Bash timeout ≥ 600000 ms.
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
