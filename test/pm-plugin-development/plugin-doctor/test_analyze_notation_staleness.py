#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Regression tests for the ``notation-staleness`` analyzer.

The ``_analyze_notation_staleness`` analyzer flags three-part executor
notations whose third segment has no matching ``{script}.py`` file under the
resolved ``bundles/{bundle}/skills/{skill}/scripts/`` directory. A renamed
entrypoint script silently changes its public notation (because
``generate_executor`` derives the third segment from the filename), so
callers that still use the old form resolve to ``Unknown notation``.

These tests pin both directions:

- **Positive** — a stale notation whose third segment has no matching file
  surfaces a ``notation-staleness`` finding; when the hyphen/underscore-
  flipped form resolves to a real file the finding carries a
  ``details.canonical_hint``.
- **Negative** — a consistent notation whose third segment matches a real
  script file produces no finding.
"""

from __future__ import annotations

from pathlib import Path

from conftest import load_script_module

# ---------------------------------------------------------------------------
# Module loader — spec-load the analyzer directly from the marketplace tree.
# Underscore-prefixed analyzers are not importable through the executor.
# ---------------------------------------------------------------------------


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ans = _load_module('_analyze_notation_staleness', '_analyze_notation_staleness.py')
analyze_notation_staleness = _ans.analyze_notation_staleness
RULE_ID = _ans.RULE_ID


# ---------------------------------------------------------------------------
# Fixture helpers — build a minimal fake marketplace tree.
# ---------------------------------------------------------------------------


def _make_skill(
    tmp_path: Path,
    *,
    bundle: str,
    skill: str,
    script_files: list[str],
) -> Path:
    """Create ``marketplace/bundles/{bundle}/skills/{skill}`` with script files.

    Also writes the bundle's ``.claude-plugin/plugin.json`` so the bundle and
    skill segments of any executor notation in the fixture resolve on disk —
    keeping the ``notation-bundle-skill-drift`` rule silent so these tests
    isolate the third-segment ``notation-staleness`` behaviour they target.

    Returns the skill directory path.
    """
    bundle_dir = tmp_path / 'marketplace' / 'bundles' / bundle
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_dir / 'plugin.json'
    if not plugin_json.exists():
        plugin_json.write_text('{}', encoding='utf-8')

    skill_dir = bundle_dir / 'skills' / skill
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True)
    for fname in script_files:
        (scripts_dir / fname).write_text('# stub\n', encoding='utf-8')
    return skill_dir


def _write_skill_md(skill_dir: Path, body: str) -> None:
    """Write a ``SKILL.md`` with the given body into the skill directory."""
    (skill_dir / 'SKILL.md').write_text(body, encoding='utf-8')


# ===========================================================================
# Positive cases — stale notation is flagged.
# ===========================================================================


def test_stale_notation_flagged(tmp_path):
    """A notation whose third segment has no matching file is flagged."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-status',
        script_files=['manage-status.py'],
    )
    _write_skill_md(
        skill_dir,
        'See command:\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read\n'
        '```\n',
    )

    findings = analyze_notation_staleness([skill_dir])

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['type'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['fixable'] is False
    assert finding['details']['notation'] == 'plan-marshall:manage-status:manage_status'
    assert finding['details']['reason'] == 'script_file_missing'


def test_canonical_hint_when_flipped_form_resolves(tmp_path):
    """When the hyphen/underscore-flipped form matches a file, hint names it."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-metrics',
        script_files=['manage-metrics.py'],
    )
    _write_skill_md(
        skill_dir,
        'python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate\n',
    )

    findings = analyze_notation_staleness([skill_dir])

    assert len(findings) == 1
    hint = findings[0]['details']['canonical_hint']
    assert 'plan-marshall:manage-metrics:manage-metrics' in hint


def test_stale_notation_in_script_file_flagged(tmp_path):
    """A stale notation in a sibling-script body is also flagged."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='workflow-integration-git',
        script_files=['git-workflow.py'],
    )
    (skill_dir / 'scripts' / 'caller.py').write_text(
        "NOTATION = 'plan-marshall:workflow-integration-git:git_workflow'\n",
        encoding='utf-8',
    )

    findings = analyze_notation_staleness([skill_dir])

    notations = {f['details']['notation'] for f in findings}
    assert 'plan-marshall:workflow-integration-git:git_workflow' in notations


# ===========================================================================
# Negative cases — consistent notation stays silent.
# ===========================================================================


def test_consistent_notation_silent(tmp_path):
    """A notation whose third segment matches a real file produces no finding."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-status',
        script_files=['manage-status.py'],
    )
    _write_skill_md(
        skill_dir,
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read\n',
    )

    findings = analyze_notation_staleness([skill_dir])

    assert findings == []


def test_unknown_bundle_skipped(tmp_path):
    """A colon-token whose target scripts/ directory does not exist is skipped."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-status',
        script_files=['manage-status.py'],
    )
    # A prose colon-token that is not an executor notation — no scripts/ dir
    # exists for some-bundle/some-skill, so it must not be flagged.
    _write_skill_md(
        skill_dir,
        'Unrelated text with some-bundle:some-skill:some-script in prose.\n',
    )

    findings = analyze_notation_staleness([skill_dir])

    assert findings == []


def test_rules_filter_deselects_rule(tmp_path):
    """When rules_filter excludes the rule, no findings are returned."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-status',
        script_files=['manage-status.py'],
    )
    _write_skill_md(
        skill_dir,
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read\n',
    )

    findings = analyze_notation_staleness([skill_dir], rules_filter={'other-rule'})

    assert findings == []


def test_file_entry_resolves_marketplace_root(tmp_path):
    """Passing an individual file resolves the marketplace root from its path."""
    skill_dir = _make_skill(
        tmp_path,
        bundle='plan-marshall',
        skill='manage-status',
        script_files=['manage-status.py'],
    )
    md_path = skill_dir / 'standards' / 'usage.md'
    md_path.parent.mkdir()
    md_path.write_text(
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read\n',
        encoding='utf-8',
    )

    findings = analyze_notation_staleness([md_path])

    assert len(findings) == 1
    assert findings[0]['details']['notation'] == (
        'plan-marshall:manage-status:manage_status'
    )
