envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:08:38Z

# Candidate lesson: a test that stubs a resolver the code no longer calls can silently ESCAPE ITS SANDBOX and mutate tracked repository state — and the assertion failure is not what tells you so

**Source plan**: plan-truth-103 (PR #1475)
**Evidence**: first-party Q-Gate finding `52c981` (5-execute, bug, severity warning), with `720f48` as its second-order symptom.
**Dedup note**: not among the 10 findings already routed this run.

## What happened

Checking the worktree before the deliverable-5 commit, `git status` showed `.claude/settings.json` modified — a tracked file **not** in the declared deliverable footprint. The whole diff was two added allow entries, `Skill(foo:*)` and `SlashCommand(/foo:*)`, plus a stripped trailing newline. `foo` is the bundle name in the marketplace fixture used by `test_scope_project_resolves_settings_via_ops`.

## Mechanism (the part that generalizes)

The test monkeypatched `permission_common.get_project_settings_path_for_write`. But `permission_fix` **binds its resolver by name at import time**, so patching the module attribute never affected the bound reference. The test also did no `monkeypatch.chdir`. `resolve_settings_arg` therefore resolved against the **real process cwd** — the worktree root — and `ensure-wildcards` loaded and REWROTE the worktree's tracked `.claude/settings.json`, i.e. a developer's real permission configuration.

Two independent conditions had to hold, and both are common:
- a stub applied at a binding site the production code does not consult (module attribute vs import-time-bound name), so the stub is inert;
- no filesystem confinement (`chdir` / `tmp_path`), so an inert stub degrades to the real path rather than to an error.

A stub that is inert is not a no-op. It is a **silent fall-through to production state**.

## Why the signal was misleading

The visible symptom was second-order and pointed elsewhere. The first run applied the wildcards (`applied: True`); every run after that saw them already present, returned `applied: False`, and failed the assertion. That failure was triaged as `720f48` — "the test pins the pre-switch write-preference resolution", an expected consequence of the D2/TASK-003 resolver switch, which the outline had *predicted*. That reading was locally reasonable and locally wrong about the mechanism: the first-order effect was an uncommitted write to a tracked repository file, and the assertion failure was merely the second run observing its own prior mutation.

So the ordering matters: **a test whose result changes between run 1 and run 2 has mutated state outside its sandbox.** Idempotence-under-rerun is the cheap tell, and it fires before any diff inspection.

## The rule

- A test that stubs a resolver **cannot observe which resolver the code asks for** — it is structurally blind to its own subject. When the change under test IS a resolver preference, the test must drive a real tree under `monkeypatch.chdir(tmp_path)`, not a stubbed seam. This is what the TASK-005 step-4 rewrite did, and it is why the rewrite also had to split the arms: the single-file arm (only `settings.json` present) and the dual-file arm (where the preference is actually observable) must be separate tests, because keeping them apart is what makes the pair discriminate a preference from a hard-wired filename.
- Confinement is not optional even when a stub is present, because the stub may be inert for reasons invisible at the test site (import-time name binding is the canonical one in this codebase).
- Recovery: the leaked file was restored with `git checkout` only after the full diff was inspected and confirmed to carry no other uncommitted content (single path, whole diff read, per the execute-task destructive-checkout rule). That sequencing is the safe form and should not be shortened.

## Suggested corpus placement

`plan-marshall:persona-module-tester` already owns "fixture-level neutralization of state-dependent branch selection" and real-resolver E2E testing for path-resolver side effects. This is a concrete, first-party instance with a named mechanism (import-time binding defeats module-attribute patching) and a cheap detector (non-idempotent rerun), so the likely best outcome is reinforcing that skill rather than a standalone lesson.
