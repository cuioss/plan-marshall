envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T20:57:06Z

component=pm-plugin-development:plugin-doctor
category=bug
title=Help-surface cache keyed on the entry script sha256 misses argparse living in imported modules
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087

# Help-surface cache keyed on the entry script sha256 misses argparse living in imported modules

## Context

`plugin-doctor`'s `manage-invocation-invalid` rule validates documented invocations against each script's **live `--help` surface**. Because probing `--help` costs a subprocess per parser node, the derived surface is cached to disk. `_analyze_manage_invocation.py` documents the key:

> "an on-disk cache entry keyed by `sha256(script_source)`. A cache entry is regenerated only when the script's content hash changes (i.e. the surface could actually have drifted)."

The parenthetical is the bug: a content change to the entry script is NOT the only way the surface can drift.

## Root cause

```python
def _content_hash(script_path: Path) -> str | None:
    data = script_path.read_bytes()
    return hashlib.sha256(data).hexdigest()
```

`script_path` is a **single file** — the entry-point script from `_ScriptDescriptor`, and the discovery loop explicitly skips `_`-prefixed modules. The cache filename is `{notation}.v{_CACHE_VERSION}.{content_hash}.json`.

But the argparse surface is frequently built **elsewhere**. The canonical case is the one this plan hit: notation `plan-marshall:tools-integration-ci:ci` → `ci.py`, which contains no parser at all. It does `from ci_base import (...)` and the entire `build_parser` surface lives in `ci_base.py`.

This plan added `--pr-number` to `pr view` in **`ci_base.py` lines 842-847**. `sha256(ci.py)` did not change. The cached surface for `ci` therefore still described the pre-change parser, and was never invalidated.

The consequence is symmetric and that is what makes it dangerous:
- **False RED** — docs updated to the new flag are validated against the stale surface and flagged as inventing `--pr-number`. This plan hit exactly one such false red.
- **False GREEN** — a doc that still uses a REMOVED flag validates clean against a stale surface that still declares it. Nothing in the plan would surface this, and `project:finalize-step-plugin-doctor` reported "plugin-doctor clean: 4 skills gated" on this very run.

The `_CACHE_VERSION` token guards against *derivation-logic* drift, not against *dependency* drift, so it does not cover this.

## Proposed action

Key the cache on the transitive import closure rather than the entry file. Cheapest correct fix: hash the sorted `(relpath, sha256)` pairs of every `.py` in the script's own `scripts/` directory — that captures `ci_base.py`, `_github_pr.py` and every sibling helper without an import graph walk, and is still a single cheap stat+read pass. A precise fix walks the module's imports resolved within the bundle.

## Evidence

- `_analyze_manage_invocation.py` — `_content_hash` (single `script_path.read_bytes()`), `_cache_path` folding only that one hash, and the module docstring's "keyed by `sha256(script_source)`" claim.
- `ci.py` lines 42-48 — `from ci_base import ...`; no parser construction in `ci.py`.
- This plan's `ci_base.py` edit at lines 842-847 adding `--pr-number` to `pr view`.

## Dedup context for the orchestrator

Adjacent to the standing `stale-cache-as-evidence` archetype, and a concrete new instance of it in a **quality gate** rather than in a status read. Gate 1 dedup NOT run (`orchestrated: true`).
