# Artifact Cleanup

Pre-commit artifact detection and cleanup. Run before staging to prevent build artifacts from being committed.

## Artifact Detection

Use Glob to detect artifacts:

```
Glob pattern="**/*.class"
Glob pattern="**/*.temp"
```

Artifact patterns to clean:
- `*.class` files in `src/` directories
- `*.temp` temporary files
- Files in `target/` or `build/` accidentally staged

## Cleanup Rules

### Safe Deletions (automatic)

Delete without asking:
- `*.class` in `src/main/java` or `src/test/java`
- `*.temp` anywhere
- Delete using `rm <file>`

### Uncertain Cases (ask user)

Use `AskUserQuestion` before deleting:
- Files >1MB
- Files outside safe list
- Files in `target/` that are tracked
