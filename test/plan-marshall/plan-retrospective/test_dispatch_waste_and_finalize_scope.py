# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for plan 070 — dispatch spend on dispatches that produced nothing.

Two deliverables are pinned here, both against
``plan-retrospective/scripts/analyze-logs.py``'s dispatch-boundary reader:

* **D1 (second half) — the audit rule reads the finalize boundary file.** The
  ``DISPATCH_TERMINATION_CAUSE`` rule was scoped to the execute boundary file
  only; the finalize file (where a review-shaped dispatch's
  ``returned_with_findings`` and ``error`` rows land, and which carries the
  majority of the finalize dispatch spend) was read by no rule. The fact
  extractor now surfaces every dispatching phase, and the productive-loop-back
  population is counted so it is distinguishable from genuinely-wasted spend.

* **D4 / D5 — genuinely-wasted vs retryable dispatch spend, reported distinctly.**
  ``error_total_tokens`` (a dispatch that raised a fatal error and returned
  nothing — the genuinely-wasted spend, a reported figure rather than a
  derivable one) is summed and reported DISTINCTLY from ``retryable_total_tokens``
  (``blocked_session_restart`` + ``harness_cancellation`` — infrastructure a
  re-run recovers), because the two need different remedies and conflating them
  produces a fix for the wrong half.

Every assertion pins the concrete counter value, not merely a terminal pass, so
a reader can tell a measured figure from an unexamined one.
"""

from __future__ import annotations

import json
from pathlib import Path

from _plan_retrospective_fixtures import ANALYZE_LOGS

from conftest import MARKETPLACE_ROOT, load_script_module, run_script

analyze_logs = load_script_module(
    'plan-marshall', 'plan-retrospective', 'analyze-logs.py', 'analyze_logs_waste'
)

# A finalize boundary file exercising every class the split cares about: two
# productive loop-backs, two genuine terminal errors, one session-restart block
# and one harness cancellation (the two retryable causes), plus a clean step
# completion that is neither wasted nor retryable.
_FINALIZE_BOUNDARY = (
    'plan_id: waste-scope\n'
    'phase: 6-finalize\n'
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
    '2026-06-01T10:00:00Z,returned_with_findings,50000,20,120000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:05:00Z,returned_with_findings,40000,15,90000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:10:00Z,error,7000,3,20000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:15:00Z,error,3000,1,8000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:20:00Z,blocked_session_restart,11000,4,30000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:25:00Z,harness_cancellation,5000,2,12000,unmeasured,unmeasured,unmeasured,unmeasured\n'
    '2026-06-01T10:30:00Z,step_complete,9000,6,25000,unmeasured,unmeasured,unmeasured,unmeasured\n'
)

# Expected sums derived from the fixture above.
_EXPECTED_ERROR_TOTAL = 7000 + 3000
_EXPECTED_RETRYABLE_TOTAL = 11000 + 5000
_EXPECTED_RETURNED_WITH_FINDINGS = 2


def _write_finalize_boundary(work_dir: Path) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / 'metrics-dispatch-boundaries-6-finalize.toon'
    path.write_text(_FINALIZE_BOUNDARY, encoding='utf-8')
    return path


# =============================================================================
# D4 / D5 — the per-class sums, at the reader
# =============================================================================


def test_error_total_tokens_sums_only_terminal_error_rows(tmp_path):
    """The genuinely-wasted figure sums total_tokens over `error` rows alone.

    RED before D5 — the reader emitted no such field, so a reader had to
    reconstruct the waste from the raw rows.
    """
    path = _write_finalize_boundary(tmp_path / 'work')

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert parsed['error_total_tokens'] == _EXPECTED_ERROR_TOTAL, (
        'error_total_tokens must sum total_tokens over the genuine terminal-error '
        f'rows only ({_EXPECTED_ERROR_TOTAL}); got {parsed["error_total_tokens"]!r}'
    )


def test_retryable_total_tokens_reported_distinctly_from_error(tmp_path):
    """Retryable/infrastructure spend is a separate figure, never folded into error.

    RED before D4 — nothing distinguished a session-restart block (infrastructure
    a re-run recovers) from a fatal error (which may be deterministic). The two
    need different remedies, so they must never share one "failure" figure.
    """
    path = _write_finalize_boundary(tmp_path / 'work')

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert parsed['retryable_total_tokens'] == _EXPECTED_RETRYABLE_TOTAL, (
        'retryable_total_tokens must sum blocked_session_restart + '
        f'harness_cancellation ({_EXPECTED_RETRYABLE_TOTAL}); got '
        f'{parsed["retryable_total_tokens"]!r}'
    )
    # The two classes are genuinely distinct on this fixture, so a reader that
    # conflated them would have to report one wrong.
    assert parsed['error_total_tokens'] != parsed['retryable_total_tokens']


def test_returned_with_findings_counted_as_the_productive_population(tmp_path):
    """The productive-loop-back population is counted, apart from the waste.

    A returned_with_findings dispatch is the OPPOSITE of this plan's target: it
    found defects and looped back. Counting it keeps it from being mistaken for
    wasted spend. RED before D1 (no such counter, and the cause was unrecognised).
    """
    path = _write_finalize_boundary(tmp_path / 'work')

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert parsed['returned_with_findings_count'] == _EXPECTED_RETURNED_WITH_FINDINGS
    # A productive dispatch's spend is not counted as waste.
    assert parsed['error_total_tokens'] == _EXPECTED_ERROR_TOTAL


def test_absent_file_reports_zero_for_every_new_figure(tmp_path):
    """An absent boundary file is a clean no-op across the new figures too.

    The keys are always present so a consumer never has to guess whether a zero
    means "measured zero" or "key missing".
    """
    parsed = analyze_logs._parse_dispatch_boundary_file(
        tmp_path / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon'
    )

    assert parsed['present'] is False
    assert parsed['error_total_tokens'] == 0
    assert parsed['retryable_total_tokens'] == 0
    assert parsed['returned_with_findings_count'] == 0


# =============================================================================
# D1 (second half) — the audit rule reads the FINALIZE boundary file
# =============================================================================


def test_analyze_logs_surfaces_the_finalize_boundary_file(tmp_path, monkeypatch):
    """cmd_run surfaces the finalize dispatch-boundary file, not the execute file alone.

    Stages a plan whose ONLY dispatch-boundary artifact is the finalize file and
    asserts analyze-logs reads it — the D1 done-when for the audit-rule half.
    The productive-loop-back count and the wasted/retryable split are surfaced
    for the finalize phase so the rule can act on it.
    """
    plan_id = 'waste-scope-e2e'
    base = tmp_path / 'base'
    plan_dir = base / 'plans' / plan_id
    _write_finalize_boundary(plan_dir / 'work')
    (plan_dir / 'logs').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'logs' / 'work.log').write_text('', encoding='utf-8')
    (plan_dir / 'logs' / 'decision.log').write_text('', encoding='utf-8')
    (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': []}), encoding='utf-8'
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))

    result = run_script(ANALYZE_LOGS, 'run', '--plan-id', plan_id, '--mode', 'live')
    assert result.success, result.stderr
    data = result.toon()

    # The finalize file is present in the per-phase dict — the whole point of the
    # widened scope. A reader scoped to 5-execute alone would find nothing here.
    assert '6-finalize' in data['dispatch_boundaries'], (
        'the finalize dispatch-boundary file must be surfaced by the reader; '
        f'got phases {sorted(data["dispatch_boundaries"].keys())!r}'
    )
    finalize = data['dispatch_boundaries']['6-finalize']
    assert str(finalize['present']).lower() == 'true'
    assert int(finalize['returned_with_findings_count']) == _EXPECTED_RETURNED_WITH_FINDINGS
    assert int(finalize['error_total_tokens']) == _EXPECTED_ERROR_TOTAL
    assert int(finalize['retryable_total_tokens']) == _EXPECTED_RETRYABLE_TOTAL


_LOGGING_GAP_ANALYSIS_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'references'
    / 'logging-gap-analysis.md'
)


def test_logging_gap_analysis_rule_scope_names_the_finalize_boundary_file():
    """The DISPATCH_TERMINATION_CAUSE rule doc no longer scopes to execute alone.

    RED before D1 — the rule's Inputs and precondition named only
    ``metrics-dispatch-boundaries-5-execute.toon``, so the finalize file was
    documented as read by no rule. The widened doc names the per-phase glob and
    ``6-finalize`` explicitly.
    """
    content = _LOGGING_GAP_ANALYSIS_MD.read_text(encoding='utf-8')

    assert 'metrics-dispatch-boundaries-{phase}.toon' in content, (
        'the rule doc must name the per-phase boundary artifact, not the '
        'execute file alone'
    )
    assert '6-finalize' in content, (
        'the rule doc must name the finalize phase as an audited dispatching phase'
    )
