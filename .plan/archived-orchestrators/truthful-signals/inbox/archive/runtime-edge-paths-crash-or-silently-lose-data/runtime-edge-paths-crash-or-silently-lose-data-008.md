envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:26:59Z

component=pm-plugin-development:plan-marshall-plugin
category=improvement
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=wrapper_tangle,llm_to_script_opportunities

# wrapper-tangle-scan should publish the population it scanned

## Context

The domain-contributed `wrapper-tangle` aspect returned:

```
counts:
  total: 0
  by_surface:
    wrapper_tangle: 0
findings[0]:
```

The fragment carries no field stating how many files were examined. Establishing whether that
zero was earned required reading the script's source during the retrospective.

## Root cause

`_iter_python_files(roots, project_root)` walks three hard-coded wrapper directories relative
to `project_root`, and silently absorbs both ways the walk can come back empty:

```python
scan_dir = project_root / rel
if not scan_dir.exists():
    continue
try:
    files.extend(sorted(p for p in scan_dir.rglob('*.py') if p.is_file()))
except OSError:
    pass
```

A `project_root` that resolves anywhere other than the repository root — a worktree that has
been removed, a cwd that moved, a test override — yields three non-existent directories, zero
files scanned, and `total: 0`, which is byte-identical to a genuine clean scan of the real
wrapper sources.

In this run the zero is almost certainly genuine: cwd was the main checkout and all three
directories exist. The defect is that the output does not let a reader establish that.

## Proposed action

Emit `files_scanned` and `dirs_resolved` / `dirs_missing` on the fragment, and treat
`files_scanned == 0` as a distinct outcome from `findings == 0` — the former is
`not_scanned`, the latter is `clean`. This is the project's own standing rule for
set-guarding detectors: a check that can return 0 from an empty population MUST publish the
population size.

## Evidence

- aspect: wrapper_tangle — `counts.total: 0`, no population field
- source: `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/wrapper-tangle-scan.py`, `_iter_python_files` and `_WRAPPER_DIRS`
- the same shape is filed separately against `direct-gh-glab-usage` Surface B in this plan's inbox message 002; the two share a root cause and could be fixed with one shared coverage-field convention across every scan-shaped retrospective fragment
