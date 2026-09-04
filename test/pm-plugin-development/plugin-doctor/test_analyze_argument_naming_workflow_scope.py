#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Regression tests for the workflow/*.md scope extension of ``_analyze_argument_naming``.

The argument-naming analyzer previously scanned only ``SKILL.md``,
``agents/*.md``, ``commands/*.md``, and the ``standards/``, ``references/``,
``recipes/`` skill subdirectories. Workflow bodies (``skills/*/workflow/*.md``)
are in scope too. A workflow body is executed prose: an invocation naming a
subcommand or flag the script's parser does not declare is one argparse rejects
at run time, so a doc left unscanned prescribes a command that fails when an
agent follows it.

These tests pin the extended scope: an invented subcommand inside a
``workflow/*.md`` file MUST surface as an ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``
finding, an invented flag MUST surface as an ``ARGUMENT_NAMING_FLAG_UNKNOWN``
finding, and a canonical invocation in the same scope MUST NOT.
"""

from __future__ import annotations

from pathlib import Path

from _plugin_doctor_dispatching_executor import write_dispatching_executor
from conftest import load_script_module

# ---------------------------------------------------------------------------
# Module loader — spec-load the analyzer directly from the marketplace tree.
# Underscore-prefixed analyzers are not importable through the executor.
# ---------------------------------------------------------------------------


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aan = _load_module('_analyze_argument_naming', '_analyze_argument_naming.py')
analyze_argument_naming = _aan.analyze_argument_naming


# ---------------------------------------------------------------------------
# Fixture helpers. The dispatching executor is the SHARED definition in
# ``_plugin_doctor_dispatching_executor``; the markdown/script writers below
# are local because their shapes are specific to the workflow-scope cases.
# ---------------------------------------------------------------------------

def _write_fake_script(
    marketplace_root: Path,
    notation: str,
    *,
    subcommands: dict[str, list[str]],
) -> Path:
    """Write a synthetic argparse script at the canonical marketplace path."""
    bundle, skill, script_name = notation.split(':', 2)
    scripts_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / f'{script_name}.py'
    parts: list[str] = [
        '#!/usr/bin/env python3',
        '"""Synthetic fixture script for argument-naming workflow-scope tests."""',
        'import argparse',
        '',
        'parser = argparse.ArgumentParser()',
        'subparsers = parser.add_subparsers(dest="command")',
    ]
    for sub, flags in subcommands.items():
        handle_var = f'p_{sub.replace("-", "_")}'
        parts.append(f'{handle_var} = subparsers.add_parser("{sub}")')
        for flag in flags:
            parts.append(f'{handle_var}.add_argument("--{flag}")')
    parts.append('')
    parts.append('if __name__ == "__main__":')
    parts.append('    parser.parse_args()')
    script_path.write_text('\n'.join(parts) + '\n', encoding='utf-8')
    return script_path


def _write_workflow_md(
    marketplace_root: Path,
    bundle: str,
    skill: str,
    filename: str,
    body: str,
) -> Path:
    """Write a workflow/*.md fixture under the canonical marketplace path."""
    workflow_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'workflow'
    workflow_dir.mkdir(parents=True, exist_ok=True)
    md_path = workflow_dir / filename
    md_path.write_text(body, encoding='utf-8')
    return md_path


def _findings_by_rule(findings: list[dict], rule_id: str) -> list[dict]:
    return [f for f in findings if f.get('rule_id') == rule_id]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_workflow_md_invented_subcommand_emits_subcommand_unknown(tmp_path):
    """Invented subcommand inside skills/*/workflow/*.md surfaces SUBCOMMAND_UNKNOWN.

    Workflow bodies are inside the analyzer's markdown scope. ``manage_status
    get`` names a subcommand the script does not register, so argparse rejects
    it with ``invalid choice`` when an agent runs what the workflow prescribes;
    the finding is what stops that reaching a reader. The
    extended scope MUST flag the bad subcommand at the exact line.
    """
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', ['plan-marshall:manage-status:manage_status'])
    _write_fake_script(
        marketplace_root,
        'plan-marshall:manage-status:manage_status',
        subcommands={'read': ['plan-id'], 'transition': ['plan-id', 'completed']},
    )
    workflow_md = _write_workflow_md(
        marketplace_root,
        'plan-marshall',
        'plan-marshall',
        'triage.md',
        '# Triage workflow\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get --plan-id foo\n'
        '```\n',
    )

    findings = analyze_argument_naming(marketplace_root)
    subcmd_findings = _findings_by_rule(findings, 'ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN')
    matching = [f for f in subcmd_findings if f['file'] == str(workflow_md)]
    assert len(matching) == 1, (
        f'Expected one SUBCOMMAND_UNKNOWN finding for the workflow body, got {findings!r}'
    )
    finding = matching[0]
    assert finding['details']['notation'] == 'plan-marshall:manage-status:manage_status'
    assert finding['details']['subcommand'] == 'get'
    assert sorted(finding['details']['known_subcommands']) == ['read', 'transition']
    assert finding['severity'] == 'error'


def test_workflow_md_canonical_subcommand_no_finding(tmp_path):
    """Canonical subcommand inside a workflow/*.md file yields no finding."""
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', ['plan-marshall:manage-status:manage_status'])
    _write_fake_script(
        marketplace_root,
        'plan-marshall:manage-status:manage_status',
        subcommands={'read': ['plan-id']},
    )
    workflow_md = _write_workflow_md(
        marketplace_root,
        'plan-marshall',
        'plan-marshall',
        'triage.md',
        '# Triage workflow\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read --plan-id foo\n'
        '```\n',
    )

    findings = analyze_argument_naming(marketplace_root)
    matching = [
        f
        for f in _findings_by_rule(findings, 'ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN')
        if f['file'] == str(workflow_md)
    ]
    assert matching == [], (
        f'Canonical subcommand in workflow body should yield no findings, got {matching!r}'
    )


def test_workflow_md_invented_flag_emits_flag_unknown(tmp_path):
    """Invented flag inside skills/*/workflow/*.md surfaces FLAG_UNKNOWN.

    Complements the SUBCOMMAND_UNKNOWN workflow-scope test: a flag absent
    from the resolved subparser's argparse declarations MUST surface as an
    ``ARGUMENT_NAMING_FLAG_UNKNOWN`` finding when it appears inside a
    ``workflow/*.md`` body. A flag the parser never declares is rejected as an
    unrecognized argument, so the documented command fails when run — which is
    why these findings carry ``severity='error'`` rather than a warning.
    """
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', ['plan-marshall:manage-findings:manage-findings'])
    _write_fake_script(
        marketplace_root,
        'plan-marshall:manage-findings:manage-findings',
        subcommands={'add': ['plan-id', 'type', 'title', 'detail']},
    )
    workflow_md = _write_workflow_md(
        marketplace_root,
        'plan-marshall',
        'plan-marshall',
        'verification-feedback.md',
        '# Verification feedback workflow\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add '
        '--plan-id foo --type triage --title bar --detail baz --finding-type triage\n'
        '```\n',
    )

    findings = analyze_argument_naming(marketplace_root)
    flag_findings = _findings_by_rule(findings, 'ARGUMENT_NAMING_FLAG_UNKNOWN')
    matching = [f for f in flag_findings if f['file'] == str(workflow_md)]
    assert len(matching) == 1, (
        f'Expected one FLAG_UNKNOWN finding for the workflow body, got {findings!r}'
    )
    finding = matching[0]
    assert finding['details']['notation'] == 'plan-marshall:manage-findings:manage-findings'
    assert finding['details']['subcommand'] == 'add'
    assert finding['details']['flag'] == 'finding-type'
    # The reported accept-set is a SUPERSET of the script's own declarations: it
    # carries the executor/router universals, which no ``--help`` renders. Assert
    # containment of the declared four plus absence of the offending flag rather
    # than an exact list, so the assertion pins THIS rule's contract instead of
    # re-pinning the membership of ``argparse_surface.UNIVERSAL_FLAGS``.
    known_flags = set(finding['details']['known_flags'])
    assert {'detail', 'plan-id', 'title', 'type'} <= known_flags, known_flags
    assert 'finding-type' not in known_flags, known_flags
    assert finding['severity'] == 'error'


def test_workflow_md_canonical_flag_no_finding(tmp_path):
    """Canonical flags inside a workflow/*.md file yield no FLAG_UNKNOWN finding."""
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', ['plan-marshall:manage-findings:manage-findings'])
    _write_fake_script(
        marketplace_root,
        'plan-marshall:manage-findings:manage-findings',
        subcommands={'add': ['plan-id', 'type', 'title', 'detail']},
    )
    workflow_md = _write_workflow_md(
        marketplace_root,
        'plan-marshall',
        'plan-marshall',
        'verification-feedback.md',
        '# Verification feedback workflow\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add '
        '--plan-id foo --type triage --title bar --detail baz\n'
        '```\n',
    )

    findings = analyze_argument_naming(marketplace_root)
    matching = [
        f
        for f in _findings_by_rule(findings, 'ARGUMENT_NAMING_FLAG_UNKNOWN')
        if f['file'] == str(workflow_md)
    ]
    assert matching == [], (
        f'Canonical flags in workflow body should yield no findings, got {matching!r}'
    )
