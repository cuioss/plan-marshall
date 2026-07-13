# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the Claude-target content-drift CLI wrapper.

``content_drift_cli.main`` is a thin argparse front end over
``content_drift.run_content_drift_check``: it resolves the two directory
arguments, calls the engine, serializes the ``ContentDriftResult`` to TOON,
and returns a gate exit code (``0`` passed, ``1`` drift-or-not-generated).
These tests reuse the synthetic-marketplace + real-emit fixture pattern from
the sibling ``test_content_drift.py`` and drive ``main([...])`` with
constructed argv, capturing stdout to assert the TOON report shape.

The shared TOON parser lives in the ref-toon-format skill's scripts dir,
which is not on ``PYTHONPATH`` during pytest collection; the canonical
``sys.path.insert`` prologue (see
``pm-plugin-development:plugin-script-architecture`` test-scaffolding.md)
puts it on the path so the report is parsed with ``toon_parser`` rather than
hand-rolled parsing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# test/marketplace/targets/claude/ -> repo root is four parents up.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOON_SCRIPTS = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
if str(_TOON_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_TOON_SCRIPTS))

from marketplace.targets.claude.content_drift_cli import main  # noqa: E402
from marketplace.targets.claude.target import ClaudeTarget  # noqa: E402
from toon_parser import parse_toon  # noqa: E402

_DOCUMENTED_KEYS = {
    'status',
    'passed',
    'drifted_count',
    'missing_count',
    'orphan_count',
    'drifted_files',
    'missing_in_target',
    'orphan_in_target',
    'summary',
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _build_source_marketplace(tmp_path: Path) -> Path:
    """Build a synthetic single-bundle marketplace and return its bundles dir.

    Mirrors ``test_content_drift._build_source_marketplace`` — the emitter
    needs a bundle ``plugin.json``, some content ``.md`` files, and a source
    ``marketplace.json`` whose ``plugins[].source`` starts with ``./bundles/``.
    """
    bundles = tmp_path / 'bundles'
    bundle = bundles / 'demo'

    plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': [],
        'commands': [],
        'skills': ['./skills/demo-skill'],
    }
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps(plugin_doc, indent=2) + '\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: demo\n---\n# demo skill body\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'standards' / 'rule.md',
        '# rule\n\nsome standard content\n',
    )
    _write(bundle / 'README.md', '# demo bundle\n')

    source_manifest = {
        'name': 'demo-marketplace',
        'plugins': [
            {'name': 'demo', 'description': 'demo', 'source': './bundles/demo'},
        ],
    }
    _write(
        tmp_path / '.claude-plugin' / 'marketplace.json',
        json.dumps(source_manifest, indent=2) + '\n',
    )
    return bundles


@pytest.fixture()
def synced_target(tmp_path: Path) -> tuple[Path, Path]:
    """Synthetic marketplace + a freshly emitted, in-sync target tree.

    Returns ``(target_dir, marketplace_dir)`` — a clean emit over which the
    drift check passes.
    """
    marketplace_dir = _build_source_marketplace(tmp_path)
    target_dir = tmp_path / 'target' / 'claude'
    ClaudeTarget().generate(marketplace_dir, target_dir, None)
    return target_dir, marketplace_dir


def _run_cli(target_dir: Path, marketplace_dir: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    """Drive ``main`` with constructed argv and return ``(exit_code, parsed_toon)``."""
    exit_code = main(['--target-dir', str(target_dir), '--marketplace-dir', str(marketplace_dir)])
    captured = capsys.readouterr()
    parsed = parse_toon(captured.out)
    return exit_code, parsed


def test_clean_emit_exits_zero_and_reports_passed(
    synced_target: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
):
    """A freshly emitted target is in sync — the CLI exits 0 and the TOON
    report carries ``passed: true`` with all drift counts zero.
    """
    target_dir, marketplace_dir = synced_target

    exit_code, parsed = _run_cli(target_dir, marketplace_dir, capsys)

    assert exit_code == 0
    assert parsed['status'] == 'success'
    assert parsed['passed'] is True
    assert parsed['drifted_count'] == 0
    assert parsed['missing_count'] == 0
    assert parsed['orphan_count'] == 0
    assert parsed['drifted_files'] == []
    assert parsed['missing_in_target'] == []
    assert parsed['orphan_in_target'] == []
    assert 'passed' in parsed['summary']


def test_toon_report_carries_documented_keys(
    synced_target: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
):
    """The serialized TOON report carries exactly the documented key set so
    downstream consumers (the ``upgrade`` verb Stage 3) can rely on the shape.
    """
    target_dir, marketplace_dir = synced_target

    _exit_code, parsed = _run_cli(target_dir, marketplace_dir, capsys)

    assert _DOCUMENTED_KEYS.issubset(parsed.keys())


def test_on_disk_md_mutation_exits_one_and_names_drifted_file(
    synced_target: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
):
    """An emitted ``.md`` mutated directly under the target surfaces as a
    ``drifted_files`` entry, the CLI exits 1, and the drifted path is named in
    both the list and the summary.
    """
    target_dir, marketplace_dir = synced_target
    drifted = target_dir / 'demo' / 'skills' / 'demo-skill' / 'SKILL.md'
    drifted.write_text(
        '---\nname: demo-skill\ndescription: demo\n---\n# MUTATED body\n',
        encoding='utf-8',
    )

    exit_code, parsed = _run_cli(target_dir, marketplace_dir, capsys)

    rel = 'demo/skills/demo-skill/SKILL.md'
    assert exit_code == 1
    assert parsed['status'] == 'error'
    assert parsed['passed'] is False
    assert parsed['drifted_count'] == 1
    assert rel in parsed['drifted_files']
    assert rel in parsed['summary']


def test_missing_target_dir_exits_one_with_not_generated_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """When the target dir is absent, the CLI exits 1 and the TOON summary
    carries the "not generated" diagnostic rather than crashing.
    """
    marketplace_dir = _build_source_marketplace(tmp_path)
    nowhere = tmp_path / 'target' / 'does-not-exist'

    exit_code, parsed = _run_cli(nowhere, marketplace_dir, capsys)

    assert exit_code == 1
    assert parsed['passed'] is False
    assert 'not generated' in parsed['summary']
