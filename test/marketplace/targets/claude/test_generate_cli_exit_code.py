"""End-to-end regression: emit-mode CLI propagates equality failure as exit 2.

Locks the silent-failure path that PR #353 review surfaced: in emit mode
``ClaudeTarget.generate`` used to record ``equality.passed=False`` on
``_last_run`` but return success, masking drift. The fix raises so the
``generate.py`` ``except Exception`` clause maps the failure to
``EXIT_ERROR=2``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def fake_marketplace(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal marketplace + (deliberately stale) target/claude pair."""
    marketplace = tmp_path / 'bundles'
    target = tmp_path / 'target' / 'claude'

    bundle = marketplace / 'demo'
    plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'demo',
        'agents': [],
        'commands': [],
        'skills': ['./skills/alpha'],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(plugin_doc, indent=2) + '\n')
    _write(bundle / 'skills' / 'alpha' / 'SKILL.md', '---\nname: alpha\ndescription: a\n---\n')

    # The Claude target's emit step also generates a top-level marketplace.json
    # from the source marketplace manifest; provide a minimal one so emit mode
    # succeeds.
    marketplace_manifest = {
        'name': 'fake-marketplace',
        'plugins': [
            {'name': 'demo', 'description': 'demo', 'source': './bundles/demo'},
        ],
    }
    _write(
        tmp_path / '.claude-plugin' / 'marketplace.json',
        json.dumps(marketplace_manifest, indent=2) + '\n',
    )
    return marketplace, target


def _run_generate(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / 'marketplace' / 'targets' / 'generate.py'),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_validate_mode_exits_2_when_target_missing(fake_marketplace: tuple[Path, Path]):
    """``--target claude`` without --output exits 2 when target/claude is absent."""
    marketplace, target = fake_marketplace
    # target/claude does not exist yet → diagnostic + exit 2
    assert not target.exists()
    result = _run_generate(['--target', 'claude', '--marketplace-dir', str(marketplace)])
    assert result.returncode == 2, result.stderr
    assert 'not generated' in result.stderr or 'target/claude' in result.stderr


def test_emit_mode_exit_0_when_clean(fake_marketplace: tuple[Path, Path]):
    """Emit mode exits 0 when source ↔ target/claude agree post-emit."""
    marketplace, target = fake_marketplace
    result = _run_generate(
        ['--target', 'claude', '--output', str(target), '--marketplace-dir', str(marketplace)]
    )
    assert result.returncode == 0, result.stderr
    assert (target / 'demo' / '.claude-plugin' / 'plugin.json').exists()


def test_emit_mode_exits_2_after_corrupting_target(fake_marketplace: tuple[Path, Path]):
    """After a clean emit, mutating target's plugin.json forces exit 2 on re-validate."""
    marketplace, target = fake_marketplace
    # Fresh emit
    emit = _run_generate(
        ['--target', 'claude', '--output', str(target), '--marketplace-dir', str(marketplace)]
    )
    assert emit.returncode == 0

    # Corrupt the emitted plugin.json so source vs target disagree
    emitted = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_doc = json.loads(emitted.read_text(encoding='utf-8'))
    plugin_doc['skills'].append('./skills/ghost-skill')
    plugin_doc['skills'].sort()
    emitted.write_text(json.dumps(plugin_doc, indent=2) + '\n', encoding='utf-8')

    # Re-validate: drift surfaces as exit 2
    revalidate = _run_generate(['--target', 'claude', '--marketplace-dir', str(marketplace)])
    assert revalidate.returncode == 2, revalidate.stderr
    assert 'failed' in revalidate.stderr or 'demo' in revalidate.stderr
