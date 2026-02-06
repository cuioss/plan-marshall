---
name: build-fix-commit
description: Run full build, fix ALL issues iteratively, commit when clean
allowed-tools:
  - Bash
  - Bash(git:*)
  - Read
  - Edit
  - Glob
  - Grep
---

# Build-Fix-Commit Command

Runs full project verification, fixes ALL issues iteratively until clean, then commits all changes.

## PARAMETERS

**message** - Optional custom commit message prefix (default: "fix(build): resolve verification errors")

## WORKFLOW

### Step 1: Initialize

Set up tracking variables:
- `iteration = 0`
- `max_iterations = 5`
- `type_errors_fixed = 0`
- `lint_errors_fixed = 0`
- `test_failures_fixed = 0`
- `total_edits = 0`

### Step 2: Run Build Verification

Execute the Python build script with 10-minute timeout:

```bash
python3 .plan/execute-script.py pm-dev-python:plan-marshall-plugin:python_build run --command-args "verify" --format toon --timeout 600
```

**Parse TOON output:**
- If `status	success` → Go to Step 5 (Commit)
- If `status	error` → Parse the `errors[N]{file,line,message,category}:` section
- If `status	timeout` → Report timeout and abort

### Step 3: Fix All Issues

For each error in the parsed output, fix based on category:

**A. Type Errors (category: type_error)**

These are mypy errors. For each:
1. Read the file at the specified line using Read tool
2. Analyze the error message (e.g., "Incompatible types", "Missing return type", "has no attribute")
3. Apply the appropriate fix using Edit tool
4. Increment `type_errors_fixed`

**B. Lint Errors (category: lint_error)**

These are ruff violations. Strategy:
1. First, try auto-fix on all affected files:
   ```bash
   ruff check --fix <list-of-files>
   ```
2. Re-run build to check if issues resolved
3. For remaining lint errors, read file and apply manual fix
4. Increment `lint_errors_fixed` for each fixed

**C. Test Failures (category: test_failure)**

These are pytest failures. For each:
1. Read the log file path from build output for detailed failure info
2. Read the failing test file
3. Analyze whether the issue is in:
   - Test code (fix the test)
   - Production code (fix the production code)
4. Apply fix using Edit tool
5. Increment `test_failures_fixed`

### Step 4: Iterate

```
iteration++

if iteration >= max_iterations:
    Display remaining unfixed issues
    Report: "Max iterations reached. {N} issues remain unfixed."
    Abort workflow

Go to Step 2 (re-run build)
```

### Step 5: Commit All Changes

When build passes (`status	success`):

**A. Check for changes:**
```bash
git status --porcelain
```

If no changes, report "Build passed but no changes to commit" and exit.

**B. Stage all changes:**
```bash
git add -A
```

**C. Create commit with conventional format:**
```bash
git commit -m "$(cat <<'EOF'
fix(build): resolve verification errors

- Fixed type annotations (mypy)
- Applied linting fixes (ruff)
- Resolved test failures

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 6: Display Summary

```
============================================================
          Build-Fix-Commit Complete
============================================================

Build Status: SUCCESS
Iterations: {iteration}

Issues Fixed:
- Type errors (mypy): {type_errors_fixed}
- Lint errors (ruff): {lint_errors_fixed}
- Test failures (pytest): {test_failures_fixed}

Total file edits: {total_edits}

Commit: {commit_hash}
```

## CRITICAL RULES

1. **Build Command**: Always use:
   ```bash
   python3 .plan/execute-script.py pm-dev-python:plan-marshall-plugin:python_build run --command-args "verify" --format toon --timeout 600
   ```

2. **10-Minute Timeout**: The build command MUST use `--timeout 600`

3. **Fix ALL Issues**: Do NOT stop after fixing some issues. Continue iterating until `status	success`

4. **Max 5 Iterations**: Prevent infinite loops by stopping after 5 attempts

5. **Commit Only On Success**: Only create a commit when the build passes completely

6. **Conventional Commit Format**: Use `fix(build):` prefix with Co-Authored-By footer

7. **Parse TOON Output**: The build script returns TOON format with:
   - Core fields: `status`, `exit_code`, `duration_seconds`, `log_file`, `command`
   - Error section: `errors[N]{file,line,message,category}:`
   - Each error line: `file\tline\tmessage\tcategory`

8. **Error Categories**:
   - `type_error` = mypy type checking error
   - `lint_error` = ruff linting violation
   - `test_failure` = pytest test failure

## ERROR HANDLING

**Build Timeout:**
- Report: "Build timed out after 10 minutes"
- Abort workflow

**Max Iterations Reached:**
- Report remaining unfixed issues with file locations
- Ask user for guidance on unfixable issues

**Unfixable Issue:**
- If an issue cannot be fixed after analysis, report it clearly
- Ask user: "[S]kip this issue / [A]bort workflow"

**No Changes After Fix:**
- If build still fails but git shows no changes, there may be an environmental issue
- Report and abort

## USAGE EXAMPLES

**Basic usage (fix and commit):**
```
/build-fix-commit
```

**With custom commit message:**
```
/build-fix-commit message="refactor(scripts): clean up type annotations"
```

## RELATED

- `pm-dev-python:plan-marshall-plugin` - Python build script
- `pm-workflow:workflow-integration-git` - Git commit standards
