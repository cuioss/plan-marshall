# Artifact Cleanup

Pre-commit artifact detection and cleanup. Run before staging to prevent build artifacts from being committed.

## Relationship with .gitignore

Most repos already have a `.gitignore` that covers common artifact patterns (`*.class`, `target/`, `build/`, `node_modules/`). The `detect-artifacts` command **respects .gitignore by default** — gitignored files are excluded from results since they cannot be accidentally committed. This means on well-configured repos, the command typically returns empty results.

Use `--no-gitignore` to audit all artifact patterns regardless of .gitignore coverage.

## Artifact Detection

The `detect-artifacts` command in `git_workflow.py` is the **source of truth** for artifact detection. Pattern definitions are in `standards/artifact-patterns.json`.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow detect-artifacts [--root <repo-root>]
```

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists.

## Cleanup Rules

- **Safe deletions** (automatic): Patterns in `artifact-patterns.json` → `safe_patterns` — delete without asking
- **Uncertain cases** (ask user): Patterns in `artifact-patterns.json` → `uncertain_patterns` — use `AskUserQuestion` before deleting

To add or update artifact detection patterns, edit `standards/artifact-patterns.json` instead of the script.
