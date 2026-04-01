# Artifact Cleanup

Pre-commit artifact detection and cleanup. Run before staging to prevent build artifacts from being committed.

## Artifact Detection

Use Glob to detect artifacts:

```
Glob pattern="**/*.class"
Glob pattern="**/*.temp"
Glob pattern="**/*.pyc"
Glob pattern="**/__pycache__/**"
Glob pattern="**/.DS_Store"
```

Artifact patterns to clean:
- `*.class` files in `src/` directories
- `*.temp`, `*.backup`, `*.backup*`, `*.orig` temporary files
- `*.pyc` and `__pycache__/` Python bytecode
- `.DS_Store` macOS metadata
- Files in `target/`, `build/`, or `node_modules/` accidentally staged
- Files in `.plan/temp/` (transient working files)

## Cleanup Rules

### Safe Deletions (automatic)

Delete without asking:
- `*.class` in `src/main/java` or `src/test/java`
- `*.temp`, `*.backup`, `*.backup*`, `*.orig` anywhere
- `*.pyc` and `__pycache__/` anywhere
- `.DS_Store` anywhere
- Delete using `rm <file>` (or `rm -rf <dir>` for directories)

### Uncertain Cases (ask user)

Use `AskUserQuestion` before deleting:
- Files >1MB
- Files outside safe list
- Files in `target/` that are tracked
