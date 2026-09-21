envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T17:02:52Z

component=project:sync-plugin-cache
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=script_failure_analysis

# A staleness guard names the wrong cause and prescribes the wrong remedy

## Context

The `sync-plugin-cache` finalize step invokes `sync.py` as bare `python3`. On this machine that hard-failed with:

```
staleness_guard: cannot import source_fingerprint helper
```

and directed the operator to re-run the generator. That remedy is wrong: `target/claude` had been freshly emitted by `deploy-target` moments earlier, so the artifact the operator was told to rebuild was already current. Re-running it changes nothing and the step fails again.

The real cause is an import path. `sync.py` reaches the helper through the full package path `marketplace.targets.claude.source_fingerprint`, which executes `marketplace/targets/__init__.py`, which registers every target (`opencode`, `pr_agent`) and transitively requires PyYAML. `source_fingerprint.py` itself imports only stdlib — `hashlib`, `shutil`, `subprocess`, `pathlib`. So a stdlib-only helper is unreachable on any interpreter lacking PyYAML, purely because of how it is addressed.

Confirmed by differential execution on this run: bare `python3` failed; `.venv/bin/python` succeeded and synced 11 bundles. Nothing about the source tree differed between the two invocations.

## Root cause

Two failures stacked, and the second is the one that costs time.

**The import drags in a registry the helper does not need.** Addressing a leaf module through its package forces every side effect in the package `__init__` to run first. The helper's own dependency footprint is stdlib; its *addressed* footprint is the whole target registry.

**The guard reports its own failure as the condition it guards against.** `cannot import source_fingerprint helper` is an infrastructure failure of the guard, but it is emitted in the vocabulary of a staleness verdict, so the operator reads it as "the artifact is stale" and is pointed at the generator. A guard that cannot run has not detected anything — and this one is indistinguishable from a guard that ran and found a problem, which is the same could-not-look-reports-a-verdict shape the epic exists to close, landing this time on an error path rather than a zero.

**Residue worth noting separately.** This is filed as plan finding `5721cb` and it is the *only* finding still `pending` in the plan's per-plan store at the end of finalize (16 total, 1 pending). Nothing carries a pending plan-scoped finding forward once the plan directory is retired, and the Signal Gate that decides whether lessons get captured counts Q-Gate findings, not per-plan ones — so a diagnosed, unfixed defect with a known remedy exits the lifecycle silently. This message is the only carrier it has.

## Proposed action

- Import `source_fingerprint` by file location (`importlib.util.spec_from_file_location`) rather than through the `marketplace.targets` package, so a stdlib-only helper does not depend on the target registry or on PyYAML being present.
- Separate the guard's two outcomes in its output vocabulary: `staleness_guard: stale` (it ran and found the artifact stale) versus `staleness_guard: could_not_run` with the underlying exception. Only the first should suggest re-running the generator.
- Audit the other bare-`python3` call sites in the project-local `.claude/skills/` step scripts for the same package-vs-file import shape; this failure mode is invisible on any machine whose `python3` happens to carry PyYAML, so its absence elsewhere has not been demonstrated by these steps passing.
- Give a pending per-plan finding a forward carrier at plan retirement, or fold per-plan pending findings into the finalize Signal Gate's population — as it stands, `pending` at plan end is indistinguishable from resolved once the directory is gone.

## Evidence

- `manage-findings list --resolution pending` → `filtered_count: 1`, `5721cb`, `resolution: pending`, `component: project:sync-plugin-cache`, `file_path: .claude/skills/sync-plugin-cache/scripts/sync.py`
- `manage-findings list` (unfiltered) → `total_count: 16`
- finding detail — bare `python3` failed with `staleness_guard: cannot import source_fingerprint helper`; `.venv/bin/python` succeeded and synced 11 bundles on the same tree
- `source_fingerprint.py` imports only `hashlib`, `shutil`, `subprocess`, `pathlib`; `marketplace/targets/__init__.py` registers `opencode` and `pr_agent`, which require PyYAML
