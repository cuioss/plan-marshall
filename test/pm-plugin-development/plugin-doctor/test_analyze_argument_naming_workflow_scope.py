#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Regression tests for the workflow/*.md scope extension of ``_analyze_argument_naming``.

The argument-naming analyzer previously scanned only ``SKILL.md``,
``agents/*.md``, ``commands/*.md``, and the ``standards/``, ``references/``,
``recipes/`` skill subdirectories. Workflow bodies (``skills/*/workflow/*.md``)
were silently outside scope, which let invented subcommands such as
``manage_status get`` slip through review (lesson 2026-05-14-00-001).

These tests pin the extended scope: an invented subcommand inside a
``workflow/*.md`` file MUST surface as an ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``
finding, and a canonical invocation in the same scope MUST NOT.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Module loader — spec-load the analyzer directly from the marketplace tree.
# Underscore-prefixed analyzers are not importable through the executor.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_aan = _load_module('_analyze_argument_naming', '_analyze_argument_naming.py')
analyze_argument_naming = _aan.analyze_argument_naming


# ---------------------------------------------------------------------------
# Fixture helpers (self-contained — mirrors the layout used by
# ``test_analyze.py``'s argument-naming cluster but does not import the
# private helpers from that module).
# ---------------------------------------------------------------------------


def _write_fake_executor(plan_dir: Path, notations: list[str]) -> Path:
    """Write a minimal ``execute-script.py`` stub containing a SCRIPTS dict."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    lines = ['#!/usr/bin/env python3', 'SCRIPTS = {']
    for notation in notations:
        lines.append(f'    "{notation}": "fake/path",')
    lines.append('}')
    executor.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return executor


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

    Regression guard for lesson 2026-05-14-00-001: workflow bodies were
    previously outside the analyzer's markdown scope, so invocations such
    as ``manage_status get`` (no such subcommand) escaped detection. The
    extended scope MUST flag the bad subcommand at the exact line.
    """
    marketplace_root = tmp_path / 'marketplace'
    _write_fake_executor(tmp_path / '.plan', ['plan-marshall:manage-status:manage_status'])
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
    _write_fake_executor(tmp_path / '.plan', ['plan-marshall:manage-status:manage_status'])
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
