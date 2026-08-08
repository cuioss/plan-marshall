---
name: plan-marshall-tools-file-ops
description: Base module providing reusable file operations patterns, parameterized store-root resolution (plans, orchestrator), and the single plan-context resolver that turns a plan_id (or the NO_PLAN sentinel) into a plan directory and working-tree root for workflow scripts
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# File Operations Base Skill

**Role**: Shared Python module providing atomic file operations, metadata parsing, TOON output helpers, and base directory configuration for workflow scripts.

## Enforcement

**Execution mode**: Library module; import functions as documented in usage examples.

**Prohibited actions:**
- Do not access `.plan/` files directly; use `base_path()` or the parameterized `get_store_dir(store, entry_id)` resolver for path construction, and `resolve_plan_context(plan_id)` whenever the input is a plan identifier
- Do not invoke `manage-status get-worktree-path` from any other module; resolve the worktree face through `resolve_plan_context` (or `resolve_project_dir`, which delegates to it)
- Do not bypass atomic write; always use `atomic_write_file()` for writes
- Do not construct cross-domain paths manually; use ID-based access pattern

**Constraints:**
- All path construction goes through `base_path()`, `get_base_dir()`, or the sanctioned `get_store_dir(store, entry_id)` store-root resolver (`store='plans'` routes through `base_path`; `store='orchestrator'` routes main-anchored via `resolve_main_anchored_path`); plan-identifier inputs go through `resolve_plan_context(plan_id)`, which is layered on `get_store_dir`
- File writes use atomic temp-file-plus-rename pattern
- Cross-domain access uses IDs, not paths

## What This Skill Provides

- Workflow base directory configuration (`.plan/` by default)
- Path construction helpers for workflow files
- Plan-context resolution — the single `plan_id` → (plan directory, working-tree root) entry point, including the `NO_PLAN` plan-less sentinel
- Atomic file write (temp file + rename pattern)
- Directory creation (mkdir -p equivalent)
- JSON success/error output helpers
- Markdown key=value metadata parsing
- Markdown metadata generation

## When to Use

Import `file_ops` module in Python scripts that write to `.plan/` directories:
- Lessons learned scripts
- Plan file scripts
- Memory management scripts
- Any script requiring atomic writes to workflow directories

## Module: file_ops.py

**Location**: `scripts/file_ops.py`

### Functions

**Base Directory Functions**

**1. get_base_dir()**
- **Purpose**: Get the base directory for workflow files
- **Input**: None
- **Output**: `Path` - base directory (default: `.plan`)

**2. set_base_dir(path)**
- **Purpose**: Override the base directory for workflow files
- **Input**: `path` (str/Path) - new base directory
- **Output**: None
- **Note**: Primarily for testing; production uses `.plan` default

**3. base_path(*parts)**
- **Purpose**: Construct a path within the workflow base directory
- **Input**: `*parts` - path components to join
- **Output**: `Path` - full path including workflow base directory
- **Example**: `base_path('plans', 'my-task', 'plan.md')` → `.plan/local/plans/my-task/plan.md`

**4. get_store_dir(store, entry_id)**
- **Purpose**: Resolve the root directory for an entry of a named runtime-state store — the ONE parameterized store-root mechanism
- **Input**: `store` (str) - `'plans'` or `'orchestrator'`; `entry_id` (str) - plan id or epic id
- **Output**: `Path` - store entry root. `'plans'` routes through `base_path('plans', entry_id)` (cwd-relative, ADR-002 unchanged); `'orchestrator'` routes through `resolve_main_anchored_path(f'orchestrator/{entry_id}')` (main-anchored shared state)
- **Raises**: `ValueError` on unknown store values
- **Note**: this is the underlying store-root mechanism `resolve_plan_context` builds on. Plan-id consumers do NOT call it directly — they resolve through `resolve_plan_context` (below), and `get_plan_dir(plan_id)` is itself a thin delegate to `resolve_plan_context(plan_id, ensure=False).plan_dir`

**File Operations**

**5. atomic_write_file(path, content)**
- **Purpose**: Write file atomically using temp file + rename
- **Input**: `path` (str/Path), `content` (str)
- **Output**: None (raises on error)
- **Pattern**: Creates temp file, writes, renames to target

**6. ensure_directory(path)**
- **Purpose**: Create directory and parents if needed
- **Input**: `path` (str/Path) - file or directory path
- **Output**: None
- **Note**: If path looks like file, creates parent directory

**TOON Output Helpers**

**7. output_success(operation, **kwargs)**
- **Purpose**: Print TOON success output to stdout
- **Input**: `operation` (str), additional kwargs
- **Output**: Prints TOON to stdout

**8. output_error(operation, error)**
- **Purpose**: Print TOON error output to stderr
- **Input**: `operation` (str), `error` (str)
- **Output**: Prints TOON to stderr

**Script Entry Point**

**9. safe_main(main_fn)**
- **Purpose**: Decorator for script entry points; catches unhandled exceptions and outputs TOON error
- **Input**: `main_fn` - the main function (must return int or None)
- **Output**: Wrapped function that calls `sys.exit()` internally
- **Usage**: `safe_main(main)()` or `@safe_main` decorator

**Metadata Functions**

**10. parse_markdown_metadata(content)**
- **Purpose**: Parse key=value metadata from markdown
- **Input**: `content` (str) - full file content
- **Output**: `dict` - metadata key-value pairs
- **Format**: Supports `key=value` and `key.subkey=value` (dot notation)

**11. generate_markdown_metadata(data)**
- **Purpose**: Generate key=value metadata block
- **Input**: `data` (dict) - metadata to serialize
- **Output**: `str` - formatted metadata block

**12. update_markdown_metadata(content, updates)**
- **Purpose**: Update specific metadata fields in markdown content
- **Input**: `content` (str), `updates` (dict)
- **Output**: `str` - updated content

**13. get_metadata_content_split(content)**
- **Purpose**: Split markdown content into metadata and body
- **Input**: `content` (str)
- **Output**: `tuple[str, str]` - (metadata_block, body_content)

**Plan-Context Resolution**

**14. resolve_plan_context(plan_id, \*, ensure=True)**
- **Purpose**: THE entry point every plan-id consumer resolves against — the single place a `plan_id` becomes a plan directory and a working-tree root
- **Input**: `plan_id` (str) — a plan identifier or the `NO_PLAN` sentinel; `ensure` (bool, keyword-only) — `True` (default) requires the plan to resolve, `False` makes the call a pure path computation with no existence check and no side effects
- **Output**: `PlanContext`
- **Raises**: `PlanNotFoundError` under `ensure=True` when `plan_id` is a real identifier that does not resolve. Its `.envelope` property carries the canonical `plan_not_found` TOON payload including the sentinel `hint` and its `hint_caveat`
- **Note**: this function owns the ONLY `manage-status get-worktree-path` invocation in the codebase (reached lazily through `PlanContext`). Consumers that need a working tree from a `plan_id` — including `resolve_project_dir` — delegate here rather than shelling out themselves

**15. PlanContext (dataclass)**
- **Purpose**: The resolved plan context returned by `resolve_plan_context`
- **Fields**: `plan_id` (str), `plan_dir` (`Path`, computed eagerly — a pure path join), `is_sentinel` (bool)
- **Lazy properties**: `worktree_path` (str — the working-tree root; the persisted worktree path when `use_worktree` is true, else the main checkout), `has_worktree` (bool — whether a DEDICATED worktree was materialized; ask this, never infer "no worktree" from a path indistinguishable from a legitimate main-checkout binding), `worktree_branch` (str — the persisted feature branch, `''` when none is recorded)
- **Note**: the three worktree faces are resolved on FIRST ACCESS, not at construction. The laziness is load-bearing: `get_plan_dir` delegates to this struct at every call site, so an eager worktree face would put a subprocess behind every plan-path computation — including inside `manage-status`, the producer of that very command
- **Raises**: `WorktreeResolutionError` when a worktree face cannot be resolved for a real plan id (the `get-worktree-path` payload was non-success, or the executor could not be located)

**16. cwd_checkout_root()**
- **Purpose**: Return the checkout root as an absolute path string, resolved cwd-relatively per the uniform cwd rule (ADR-002) — the nearest ancestor of cwd containing `.plan/local`
- **Input**: None
- **Output**: `str` — falls back to cwd when the caller operates outside any resolvable plan root
- **Note**: deliberately NOT named `main_checkout_root`. `marketplace_paths.main_checkout_root` uses a DIFFERENT rule (git `--git-common-dir`, which is always MAIN even from a linked worktree) and returns a `Path`; this one resolves to the WORKTREE during phase-5+. The names are kept distinct because the two modules are routinely imported together

### The `NO_PLAN` sentinel

`resolve_plan_context` accepts one non-plan value: the plan-less sentinel `NO_PLAN` (`NO_PLAN_SENTINEL`, defined in `script-shared`'s `marketplace_paths` and re-exported by `input_validation`). Its behaviour in this module:

- It resolves to `{base_dir}/plans/NO_PLAN`.
- Under `ensure=True` it is materialized on demand — the directory **and** a `status.json`. Both halves are required: `require_plan_exists` treats a directory without `status.json` as not-found, so a mkdir-only sentinel would leave every `prepare_body` caller failing with `plan_not_found`. The write is idempotent; an existing `status.json` is never overwritten.
- Its worktree face is ALWAYS the main checkout — a plan-less caller has no worktree, so `worktree_path` yields `cwd_checkout_root()`, `has_worktree` is `False`, and `worktree_branch` is `''`.
- Under `ensure=False` it is a pure path computation, exactly like a real plan id — nothing is created.

`file_ops` imports the sentinel from `marketplace_paths`, NOT from `input_validation`: this module must import cleanly on the bootstrap path, where only `script-shared`, `ref-toon-format` and `tools-file-ops` are on `sys.path`. The identifier-grammar carve-out that makes the sentinel an acceptable `plan_id` at the CLI boundary belongs to `validate_plan_id` — see [`tools-input-validation/SKILL.md`](../tools-input-validation/SKILL.md) § "The `NO_PLAN` sentinel (plan_id carve-out)"; it is not restated here.

---

## Usage Example

```python
#!/usr/bin/env python3
from file_ops import (
    atomic_write_file,
    base_path,
    output_success,
    output_error,
    generate_markdown_metadata
)

def main():
    try:
        # Construct path within .plan directory
        filepath = base_path('lessons-learned', '2025-11-28-001.md')

        # Generate metadata
        metadata = generate_markdown_metadata({
            'id': '2025-11-28-001',
            'component.type': 'command',
            'applied': 'false'
        })

        # Write atomically (creates directories automatically)
        content = f"{metadata}\n# Lesson Title\n\nContent here..."
        atomic_write_file(filepath, content)

        output_success('write-lesson', file=str(filepath))
    except Exception as e:
        output_error('write-lesson', str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `file_ops.py` | Core file operations module (importable) |
| `constants.py` | Shared constants: status values, phase names, filenames, certainty values, directory names |

---

## Python Usage

```python
from file_ops import base_path, get_store_dir, atomic_write_file, output_success, output_error
from constants import STATUS_SUCCESS, FILE_STATUS, PHASES, DIR_PLANS

# Resolve store-entry root paths (the ONE parameterized store-root mechanism)
plan_dir = get_store_dir('plans', plan_id)  # Returns Path to .plan/local/plans/{plan_id}
epic_dir = get_store_dir('orchestrator', epic_id)  # Main-anchored: <main>/.plan/local/orchestrator/{epic_id}
artifacts = base_path('plans', plan_id, 'artifacts')

# Atomic file writes (temp file + rename for crash safety)
atomic_write_file(plan_dir / 'status.json', json.dumps(data, indent=2))

# Structured TOON output
output_success({'plan_id': plan_id, 'action': 'created'})
output_error('file_not_found', f'Plan {plan_id} not found')
```

## Integration

The executor manages PYTHONPATH automatically, so scripts can import `file_ops` directly:

```python
from file_ops import atomic_write_file, base_path, output_success, output_error
```

## Directory Structure

Files are stored in `.plan/` directory:

```text
.plan/                         # Workflow artifacts
├── run-configuration.json     # Command execution tracking
├── lessons-learned/           # Knowledge capture
│   └── *.md
├── memory/                    # Session state
│   ├── context/*.json
│   └── handoffs/*.json
└── plans/                     # Task plans
    └── {task-name}/
        ├── plan.md
        └── references.json
```

---

## Cross-Domain Access Pattern

When scripts in one domain (e.g., `plan-marshall:plan-files`) need to access resources in another domain (e.g., `plan-marshall:manage-lessons`), follow the **ID-based access pattern**.

### Principle

**Scripts take IDs, not paths, for cross-domain resources.** The script resolves the ID to a path internally using `base_path()`.

### Why This Matters

- **Encapsulation**: Each domain owns its file structure; other domains should not construct paths
- **Maintainability**: Path format changes only require updating the owning domain's script
- **Testability**: ID-based APIs are easier to mock and test
- **Error clarity**: Scripts can provide domain-specific error messages for invalid IDs

### Correct Pattern

```python
# Script in planning domain needs to access lesson from lessons-learned domain
# CORRECT: Accept ID, resolve path internally

def copy_lesson_to_plan(lesson_id: str, plan_dir: Path) -> dict:
    # Resolve ID to path internally
    lesson_file = base_path("lessons-learned", f"{lesson_id}.md")

    if not lesson_file.exists():
        return {"success": False, "error": f"Lesson not found: {lesson_id}"}

    # Proceed with copy...
```

### Incorrect Pattern (Anti-Pattern)

```python
# WRONG: Orchestrator constructs path and passes it to script

# In orchestrator (phase-management SKILL.md):
python3 {script} --lesson-file {lesson.file}  # BAD: orchestrator builds path

# In script:
def copy_lesson_to_plan(lesson_file: Path, plan_dir: Path):  # BAD: accepts path
    pass
```

### When to Use ID-Based Access

| Scenario | Use ID-Based | Reason |
|----------|--------------|--------|
| Cross-domain resource access | Yes | Scripts own their domain's paths |
| Same-domain resource access | Optional | Same skill owns both paths |
| User-specified file | No | User explicitly provides path |
| Configuration files | No | Paths defined in config are explicit |

### Implementation Rules

When creating scripts that access cross-domain resources:

1. [ ] Accept resource ID (e.g., `--lesson-id`) not path
2. [ ] Import `base_path` from file_ops
3. [ ] Resolve path internally: `base_path("domain-dir", f"{id}.md")`
4. [ ] Return clear error if resource not found
5. [ ] Document the expected ID format in help text

