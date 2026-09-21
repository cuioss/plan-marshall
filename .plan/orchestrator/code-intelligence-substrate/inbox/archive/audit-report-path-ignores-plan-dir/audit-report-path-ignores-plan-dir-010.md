envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:32:46Z

component=plan-marshall:plan-retrospective
category=bug
title=check-manifest-consistency filters .claude/ as bookkeeping, contradicting build_map's production classification

# The manifest cross-check discards this project's own production tree

## Observation

`check-manifest-consistency.py:49`:

```python
# Paths whose changes are bookkeeping side-effects of phase-6-finalize, not
# implementation work. Filtered before evaluating any rule.
_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')
```

The project's own `build_map` says the opposite:

```
.claude/skills/*.py, production, compile
```

For plan `audit-report-path-ignores-plan-dir` the two disagree on 10 of 11 files. Running the aspect with the realized footprint supplied explicitly:

```
diff: files_total: 11, files_filtered: 10, files_kept: 1
```

The one survivor is `test/plan-marshall/.../test_audit_checks.py`. Everything discarded as "bookkeeping" is the plan's actual deliverable set — including `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, a **7000-line Python production module** and the entire subject of the plan.

## Consequence

Every rule downstream of the filter then evaluates against a 1-file phantom footprint:

- `docs_only_diff` (M1), `early_terminate_diff` (M2), `tests_only_diff` (M3) — all skipped.
- `branch_cleanup_changes` — `pass, branch-cleanup paired with 1 changed file(s)`.

That `pass` is vacuous. The cross-check reported `passed: 2, failed: 0, findings: 0` on a plan whose real footprint it never saw.

## Mechanism

The prefix list is a hardcoded, project-agnostic guess about what `.claude/` means. In most consumer projects `.claude/` is indeed config and cache. In **this** meta-project it is a first-class source tree — which is exactly why `build_map` declares it production. The component encodes its own classification instead of consulting the declared oracle.

## Rule

- `build_map` is THE build/no-build oracle (already the standing position, cf. the pending PLAN-35 oracle-consolidation work). A component that needs to know whether a path is implementation MUST query it, not carry a private prefix list.
- Replace `_BOOKKEEPING_PREFIXES` with a `build_map` lookup: a path whose resolved `role` is `production` or `test` is implementation; only `config`/unclassified paths are bookkeeping. `.plan/` can stay hardcoded — it is genuinely runtime state and is not in any build_map.
- Any rule whose input set was reduced by filtering must report the reduction in its verdict. `passed: 2, findings: 0` should not be emitable when 91% of the supplied footprint was discarded before evaluation — surface `files_filtered` in the verdict, or downgrade to `indeterminate`.

## Relation to the epic

Another `confident-signal-hides-a-caveat` instance, and a **source-of-truth duplication** one: two components hold contradictory classifications of the same path class, and the one that is wrong for this repository is the one that silently wins. It is also the same archetype the audited plan itself was fixing — a hardcoded list mirroring a set defined authoritatively elsewhere.
