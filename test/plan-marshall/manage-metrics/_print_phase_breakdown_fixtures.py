#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py `print-phase-breakdown` subcommand.

Covers:
- Successful extraction of the `## Phase Breakdown` section from metrics.md.
- Error when metrics.md is missing.
- Error when metrics.md exists but lacks the Phase Breakdown heading.
- Section bounded correctly when followed by another `##` heading.
- Direct cmd_* call (Tier 2 import) and CLI plumbing (subprocess).
"""


# ruff: noqa: I001
import importlib.util








from conftest import get_script_path




from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)


SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')


# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics', SCRIPT_PATH)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


_extract_phase_breakdown_section = manage_metrics._extract_phase_breakdown_section


cmd_end_phase = manage_metrics.cmd_end_phase


cmd_generate = manage_metrics.cmd_generate


cmd_print_phase_breakdown = manage_metrics.cmd_print_phase_breakdown


cmd_start_phase = manage_metrics.cmd_start_phase


write_metrics = manage_metrics.write_metrics


# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================
#
# TASK-1 added a require_plan_exists guard to every plan-scoped writer in
# manage-metrics.py (start-phase, end-phase, generate, phase-boundary,
# accumulate-agent-usage, enrich). The guard returns ``error: plan_not_found``
# unless the plan directory carries a ``status.json`` sentinel. The
# ``plan_context`` fixture creates plan dirs without that sentinel, so every
# positive test would otherwise trip the guard.
#
# The autouse fixture below patches ``manage_metrics.require_plan_exists`` so
# that, during these tests, it auto-materialises the ``status.json`` sentinel for
# any plan whose dir exists but is not explicitly registered as "unseeded". This
# is the real guard chokepoint — it fires regardless of whether a test resolves
# its plan dir before or after calling the writer. Guard-negative tests register
# their plan_id via ``_register_unseeded`` so the patched guard lets the genuine
# ``plan_not_found`` branch run.

_UNSEEDED_PLAN_IDS: set[str] = set()


def _register_unseeded(plan_id: str) -> str:
    """Mark ``plan_id`` so the autouse guard-seeder leaves it un-sentinelled.

    Returns the plan_id for inline use. Negative guard tests call this so the
    patched ``require_plan_exists`` runs its genuine ``plan_not_found`` branch.
    """
    _UNSEEDED_PLAN_IDS.add(plan_id)
    return plan_id


def _seed_metrics_md(plan_id: str) -> None:
    """Seed metrics.md by recording a couple of phases and calling generate."""
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init', total_tokens=25_000))
    cmd_start_phase(ns_start_phase(plan_id, '2-refine'))
    cmd_end_phase(ns_end_phase(plan_id, '2-refine', total_tokens=10_000))
    result = cmd_generate(ns_generate(plan_id))
    assert result['status'] == 'success'


def _seed_phases(plan_id: str, phases: dict) -> None:
    """Write a metrics.toon file with the given phases dict, bypassing start/end."""
    write_metrics(plan_id, {'phases': phases})


def _render_breakdown(plan_id: str) -> list[str]:
    """Call cmd_generate and return the Phase Breakdown table lines from metrics.md.

    Returns the list of lines starting with the header row and ending with the
    Total row (whitespace stripped).
    """
    result = cmd_generate(ns_generate(plan_id))
    assert result['status'] == 'success', result
    from file_ops import get_plan_dir

    md_path = get_plan_dir(plan_id) / 'metrics.md'
    content = md_path.read_text(encoding='utf-8')
    section = _extract_phase_breakdown_section(content)
    assert section is not None
    # Strip down to table rows.
    table_lines = [ln for ln in section.splitlines() if ln.startswith('|')]
    return table_lines
