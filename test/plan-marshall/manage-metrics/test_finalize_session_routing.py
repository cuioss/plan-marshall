#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression tests for finalize session routing.

Pins the transcript-gated routing at the ``manage-metrics enrich`` script seam:

* transcript-capable target (Claude) with absent session identity preserves the
  abort/error — the broken-hook signal survived the D1 fix.
* transcript-less target (opencode) with absent session identity proceeds
  unenriched with the population-carrying gap flag and the logged-decision
  message — the hard-block is closed there.

Fail-before / pass-after: before the D1 fix ``--session-id`` was a required
argparse argument, so both cases below failed before reaching any routing
(the parser exited instead of returning a verdict); after the fix the
transcript-capable case returns the ``missing_session_id`` error and the
transcript-less case returns the unenriched skip. No interference with the D1
co-located unit cases in ``test_manage_metrics_enrich.py`` (disjoint plan ids,
disjoint assertions).
"""

from _manage_metrics_fixtures import ns

from _manage_metrics_module_fixtures import (
    _seed_guarded_plan_dirs,
    cmd_enrich,
    manage_metrics,
)


def test_regression_claude_absent_identity_preserves_abort(plan_context, monkeypatch):
    """Claude path: absent identity still errors with the broken-hook remedy."""
    plan_id = 'finalize-routing-claude'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'claude')

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'error'
    assert result.get('error') == 'missing_session_id'
    assert 'SessionStart' in result.get('message', '')


def test_regression_transcript_less_absent_identity_proceeds_unenriched(plan_context, monkeypatch):
    """Transcript-less path: absent identity proceeds unenriched with gap flag and decision."""
    plan_id = 'finalize-routing-transcript-less'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'opencode')

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'success'
    assert result.get('enriched') is False
    assert result.get('skipped') is True
    assert result.get('gap') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_TRANSCRIPT_LESS
    assert result.get('population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED
    assert 'unenriched' in result.get('message', '')
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert str(stored.get('enrichment_skipped')).lower() == 'true'
    assert stored.get('enrichment_gap_population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED
