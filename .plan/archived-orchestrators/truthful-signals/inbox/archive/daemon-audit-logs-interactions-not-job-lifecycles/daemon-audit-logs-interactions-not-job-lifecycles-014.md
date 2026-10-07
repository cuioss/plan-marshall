envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:36Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Document architecture-refresh's Tier-0-only zero-dispatch path the way ci-verify's is documented

## What was observed

The execution-context dispatch audit flagged one `dispatch_coverage_violation`:

```
phase_steps[6-finalize][architecture-refresh]: outcome=done,
  display_detail="no module structure changed"
→ no matching [DISPATCH] emission in work.log
```

`standards/dispatch-inline-split.md` classifies `default:architecture-refresh` as
DISPATCHED, with this rationale:

> hybrid, classified dispatched: its Tier 0 discover + diff is deterministic inline script
> work, and its Tier 1 re-enrichment fans out under `phase-6-finalize` per affected module
> — the only per-iteration parallel dispatch in the contract.

So when no module structure changed, Tier 1 never fires and the step legitimately emits
zero `[DISPATCH]` lines. **This run's flag is a false positive.**

## Why it is still worth fixing

The same document handles the identical situation for a sibling step *explicitly*:

> `default:ci-verify` deserves a note: its green pass-through (`final_status == success`
> AND no failing checks) marks the step done with ZERO dispatch, and only genuinely-red CI
> files one taxonomy finding ... This green-early-return / no-dispatch bypass is documented
> BEFORE the red-CI triage dispatch it bypasses.

`architecture-refresh` has an equivalent zero-dispatch path and no equivalent note. The
consequence is that the audit's `dispatch_coverage_violation` check — whose whole purpose
is to catch "ran inline where dispatch was required" — cannot mechanically distinguish
`architecture-refresh`'s benign no-op from a genuine violation. Every clean run produces
one `severity: error` finding that a reader must hand-adjudicate.

An error-severity finding that fires on healthy runs trains readers to skip the category.
That is how a real violation gets waved through later.

## Proposed action

Add a roster note for `default:architecture-refresh` mirroring the `ci-verify` note: state
that a Tier-0-only run (no module structure changed) marks the step done with zero
dispatch, and that this is the expected path rather than a coverage violation.

Then make the audit's check consume the carve-out rather than prose: the two documented
zero-dispatch paths (`ci-verify` green pass-through, `architecture-refresh` Tier-0-only)
should be a machine-readable exemption the `dispatch_coverage_violation` check reads, so
the exemption set cannot drift from the roster.

## Evidence

- `work/fragment-execution-context-dispatch-audit.toon` (this run) — 1 finding,
  0 envelope_violation, 0 generic_subagent_violation, 21 canonical `[DISPATCH]` lines
- `phase-6-finalize/standards/dispatch-inline-split.md` §§ "Dispatched steps",
  "Inline steps" (the ci-verify note)
- `logs/work.log:240-241` — step entry followed directly by the next step, no `[DISPATCH]`
