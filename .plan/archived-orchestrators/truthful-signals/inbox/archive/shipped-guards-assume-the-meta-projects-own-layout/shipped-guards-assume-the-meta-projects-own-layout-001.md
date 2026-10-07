envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=finding
created=2026-09-04T14:12:31Z

# plugin-doctor `scan_manage_invocation` emits false positives under a worktree marketplace root

## The signal

`doctor-marketplace quality-gate` reports **173 `manage-invocation-invalid` errors**
against a worktree marketplace root and **0** against the main checkout, on
**identical source**. Every finding names a flag that demonstrably exists.

The tell is in the finding text itself: the `registered` set it reports is always
the small router/common set rather than the subcommand's own flags.

```text
`plan-marshall:manage-metrics:manage-metrics` invocation uses unregistered flag
`--total-tokens` (registered: ['audit-plan-id', 'help', 'plan-id', 'project-dir'])
```

Live, the real parser declares them:

```text
manage-metrics.py accumulate-agent-usage [-h] --plan-id PLAN_ID --phase {...}
    [--total-tokens ...] [--tool-uses ...] [--duration-ms ...]
    [--retrospective-tokens ...]
```

Same shape for `github_pr fetch_findings --required-bots/--optional-bots`,
`github_pr bot_completion --bot-kind`, `sonar fetch_findings --types`,
`manage-lessons set-title --title`. Every one of these flags was invoked
successfully dozens of times during the run that filed this.

## Why it is a false positive, established rather than asserted

| Evidence | Result |
|---|---|
| `quality-gate --marketplace-root <main>/marketplace` | `status: pass`, `total_issues: 0` |
| `quality-gate --marketplace-root <worktree>/marketplace` | `status: fail`, `total_issues: 173` |
| `git log origin/main..HEAD -- <every flagged file>` | empty — the branch touches none of them |
| Live `--help` on each flagged notation | the flag is declared |
| Same gate, same worktree, earlier in the same session | green three times |

The 173 are **entirely** one rule (`scan_manage_invocation`); the other 36 rules
report 0. `analyze_argument_naming` blind spots also rise 308 → 518 between the
two roots, so the degradation is broader than the rule that happens to fail the
build.

## What triggered it

The gate was green three times against this same worktree earlier in the session.
It turned red only after two events, neither of which is a source change:

1. the `project:finalize-step-plugin-doctor` dispatch regenerated the worktree
   executor, and
2. `run_config cleanup --target temp` swept 73543 files / 721 MB.

## Repairs that do NOT work — do not retry these

- `generate_executor generate`
- `generate_executor generate --force`
- `generate_executor generate --force` with `PM_SURFACE_BUDGET_SECONDS=1200`

All three report **identically**:

```text
surface-stats: scripts_registered=162 surfaces_derived=0 surfaces_reused=117 surfaces_not_derivable=45
```

`surfaces_derived: 0` on every one, including `--force`: surfaces are reused by
**script digest** from the previous executor's `SCRIPT_SURFACES` literal, so
unchanged scripts are never re-derived and `--force` does not reach them. A
degraded generation is therefore **sticky** — which is the more general defect
here, independent of whatever degraded it first.

## Two hypotheses already eliminated

- **Executor artifact content.** Both executors were read directly; **both**
  contain the flags in `SCRIPT_SURFACES` (`required-bots` ×3, `retrospective-tokens`
  ×6 in each). Content is not the differentiator.
- **Symlink layout.** Neither `.plan` nor `.plan/execute-script.py` is a symlink
  in either tree.

## Residual hypothesis

The analyzer's per-notation script resolution falls back to a **router surface**
when invoked against a worktree marketplace root, and the reported `registered`
list is that fallback rather than a derived accept-set. Unverified.

## Why this matters beyond one run

`manage-invocation-invalid` is an **error-severity, build-failing** rule, and this
is the failure mode it is least able to survive: a *degraded derivation* is
reported in exactly the same shape as a *real* invalid invocation. A reader
cannot tell "this flag does not exist" from "I could not derive what exists", so
the rule's red means two different things and only one of them is actionable. The
`registered` list is already in the payload — publishing whether that list was
*derived* or *fallen back to* would separate them.

That is the same confident-signal-hides-a-caveat shape this epic exists for.

## Disposition on the originating run

Operator-accepted so finalize could proceed. The originating plan's own
`pre-push-quality-gate` step records the whole-tree `quality-gate` arm as
**DEGRADED** rather than green, so the un-gated dimension is named in the step
record rather than laundered into a pass. Impact is confined to local derived
state: CI checks out source and has no worktree executor, so the false findings
cannot reach the PR.

Plan-local finding id: `cb3735`.
