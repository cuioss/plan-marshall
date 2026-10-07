envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T21:40:59Z

envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T22:10:00Z

# Finding: generate_executor registers plugin-cache skills as default-bundle shadows, making shorthand resolution ambiguous and the pre-push whole-tree gate false-red on any regenerated executor

Epic: process-compliance
Plan: implement-opencode-enforcement-parity
Phase observed: phase-6-finalize, pre-push-quality-gate whole-tree arm

## Summary

The pre-push whole-tree `quality-gate` failed with 26 `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` issues (`shorthand_unresolved`) on `persona-plan-marshall-agent/standards/argument-naming.md` — a file this plan never touched, byte-identical to origin/main, and CLEAN when gated on main. Root cause is not the tree but the worktree's freshly-regenerated executor map: `generate_executor` discovers ~160 "project-local scripts" from the plugin cache (`~/.config/opencode/skills/*`) and registers each as `default-bundle:{cache-dirname}:{script}`. Cache dirnames are `{bundle}-{skill}`, so each shadow's third segment equals the real marketplace script name; `_resolve_shorthand_to_notation` (third-segment equality, ambiguity returns None) then finds 2 exact matches for every skill==script shorthand (`manage-status`, `manage-tasks`, `manage-findings`, `manage-logging`, `manage-references`, `architecture`) and resolves none of them.

## Facet A — Cache slurp in local discovery

`generate_executor generate` (default and `--marketplace` contexts alike) reports "Found 160 local scripts"; 156 dry-run mappings resolve under `/home/oliver/.config/opencode/skills/`. Main's working executor carries 165 notations (6 default-bundle); any fresh regeneration produces 319 (160 default-bundle). Main passes only because its executor predates the slurp. The next steward regeneration of main's executor will break the gate there too.

## Facet B — Ambiguity fails closed into false findings

`_resolve_shorthand_to_notation` returns None both for "no match" and "ambiguous match", and the rule reports both as `shorthand_unresolved` errors against the doc file. A shadow-induced ambiguity is a measurement defect, yet it renders as 26 file-anchored errors indistinguishable from genuine drift. Either the generator must not register shadowing entries, or the resolver must prefer the non-`default-bundle` match (or report ambiguity distinctly from absence).

## Suggested fixes

1. Stop registering plugin-cache skills into marketplace-checkout executors (or namespace them so third segments cannot collide with marketplace script names).
2. Alternatively, make `_resolve_shorthand_to_notation` prefer the marketplace-qualified match over `default-bundle:` shadows, and/or emit a distinct reason for ambiguity vs absence so the gate can tell a map defect from doc drift.
3. Until fixed, any plan whose executor regenerates (rebase refresh, plugin-doctor Step 4) inherits a false-red whole-tree gate.

## Evidence

- Worktree executor SCRIPTS block: 319 unique notations, 160 `default-bundle:`-prefixed; main executor: 165 unique, 6 prefixed.
- Dry-run on main: "Found 160 local scripts", 156 mappings under `/home/oliver/.config/opencode/skills/`, e.g. `default-bundle:plan-marshall-manage-status:manage-status -> .../skills/plan-marshall-manage-status/scripts/manage-status.py`.
- Scoped gate on identical file: main `status: pass, total_issues: 0`; worktree `status: fail, total_issues: 26` (all `shorthand_unresolved`, lines 128-160).
- Fresh `--marketplace`-context regeneration reproduces the 160 shadows; executor regeneration does not clear them.
