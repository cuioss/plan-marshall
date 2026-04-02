# Artifact Cleanup

Pre-commit artifact detection and cleanup. Run before staging to prevent build artifacts from being committed.

## Relationship with .gitignore

Most repos already have a `.gitignore` that covers common artifact patterns (`*.class`, `target/`, `build/`, `node_modules/`). The `detect-artifacts` command **respects .gitignore by default** — gitignored files are excluded from results since they cannot be accidentally committed. This means on well-configured repos, the command typically returns empty results.

Use `--no-gitignore` to audit all artifact patterns regardless of .gitignore coverage. This is useful for verifying .gitignore completeness or finding artifacts in repos with incomplete coverage.

## Artifact Detection

The `detect-artifacts` command in `git-workflow.py` is the **source of truth** for artifact patterns. Use it instead of manual Glob calls.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts [--root <repo-root>]
```

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists, respecting `.gitignore` by default.

## Cleanup Rules

### Safe Deletions (automatic)

The script classifies these patterns as safe — delete without asking:
- `*.class` — compiled Java bytecode
- `*.temp`, `*.backup`, `*.backup*`, `*.orig` — temporary files
- `*.pyc` and `__pycache__/` — Python bytecode
- `.DS_Store` — macOS metadata

Delete using `rm <file>` (or `rm -rf <dir>` for directories).

### Uncertain Cases (ask user)

The script classifies these as uncertain — use `AskUserQuestion` before deleting:
- Files in `target/`, `build/`, `node_modules/`, `.plan/temp/`
- Files >1MB
- Files outside the safe pattern list
