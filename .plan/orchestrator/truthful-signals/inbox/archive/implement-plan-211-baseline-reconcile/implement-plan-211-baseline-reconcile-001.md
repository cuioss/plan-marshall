envelope_version=1
sender_type=plan
sender_id=implement-plan-211-baseline-reconcile
epic=truthful-signals
kind=finding
created=2026-10-01T12:50:21Z

## PLAN-211 baseline-reconcile implemented for D1/D4/D6/D7

Implements the PM-MCP narrowed scope only. D2/D3/D5/D8 were not touched per
the narrowing banner.

What changed:
- `git_provider.run_git` pins `LC_ALL/LANG/LANGUAGE=C` for deterministic git
  output.
- `_cmd_baseline_reconcile._detect_merge_conflicts` passes `--no-messages`,
  falls back without the flag on older git, and collects only the path block
  up to the first blank separator. Informational lines in any locale are never
  filed as paths.
- New `test_baseline_reconcile_localized.py` covers German and English message
  sections, the flag, the fallback, and locale pinning.

Verification:
- `module-tests plan-marshall --no-parallel --filter test_baseline_reconcile`:
  37 tests green.
- `compile plan-marshall`: green.
- `quality-gate plan-marshall`: green after formatting churn.

Branch: `feature/implement-plan-211-baseline-reconcile` with two commits.
PR still to be opened via the CI abstraction; this message is the inbox
outcome record per the plan Write-Boundary.
