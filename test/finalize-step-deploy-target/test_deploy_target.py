#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the project-local ``project:finalize-step-deploy-target`` skill.

The skill is a markdown executor playbook backed by the multi-target
generator at ``marketplace/targets/generate.py``. These tests pin the
contract from three angles:

1. **Frontmatter and ordering** — the skill declares ``order: 80`` so
   the dispatcher places it post-merge after ``default:branch-cleanup``
   (70) and before ``project:finalize-step-sync-plugin-cache`` (85).
2. **Project-local registration** — the skill lives at
   ``.claude/skills/finalize-step-deploy-target/SKILL.md`` (NOT in any
   marketplace bundle, NOT in ``BUILT_IN_FINALIZE_STEPS``).
3. **Generator behaviour** — when the live generator runs against a
   fixture marketplace, it returns ``status: success`` with a non-zero
   ``produced`` count; the executor's ``display_detail`` template uses
   that count.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_SKILL_MD = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'
)
_GENERATE_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'generate.py'

_MANAGE_CONFIG_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))

import _config_defaults as cd  # noqa: E402


# ---------------------------------------------------------------------------
# 1) Frontmatter and ordering
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    assert match is not None, f'frontmatter not found in {path}'
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            fm[key.strip()] = value.strip()
    return fm


def test_skill_md_exists():
    assert _SKILL_MD.is_file(), f'project-local finalize-step skill missing: {_SKILL_MD}'


def test_skill_frontmatter_has_canonical_fields():
    fm = _parse_frontmatter(_SKILL_MD)
    assert fm.get('name') == 'finalize-step-deploy-target'
    assert fm.get('description'), 'description must be non-empty'
    assert fm.get('order') == '81', (
        'deploy-target order must be 81 (post-merge: after branch-cleanup=70, '
        'before sync-plugin-cache=85; bumped 80->81 to deconflict with the '
        'consumer-shipped built-in default:finalize-step-preference-emitter at order 80)'
    )


def test_skill_body_documents_inline_only_and_no_skip_detector():
    text = _SKILL_MD.read_text(encoding='utf-8')
    flat = re.sub(r'\s+', ' ', text.lower())
    assert 'inline-only' in flat or 'inline only' in flat
    assert 'no skip detector' in flat, (
        'standard must explicitly state there is no skip detector — generator handles no-op'
    )
    # Generator command must appear verbatim
    assert 'marketplace/targets/generate.py --target claude --output target/claude' in text
    # display_detail template must reference emitted_count semantics
    assert 'files emitted to target/claude/' in text


# ---------------------------------------------------------------------------
# 2) NOT a built-in default — meta-project-only project step
# ---------------------------------------------------------------------------


def test_deploy_target_is_not_a_built_in_default():
    """Per the relocation, deploy-target is a project-local step, not a default.

    The hand-maintained BUILT_IN_FINALIZE_STEPS / *_DESCRIPTIONS constants were
    removed; membership is discovered via extension_discovery.find_implementors.
    A ``default:deploy-target`` built-in id must NOT appear among the discovered
    finalize steps, and must NOT be in the default-on seed.
    """
    from extension_discovery import find_implementors

    discovered_names = {
        rec['name'] for rec in find_implementors(cd.FINALIZE_STEP_EXT_POINT) if rec.get('name')
    }
    assert 'default:deploy-target' not in discovered_names
    # Positive contract: the project-local step IS discovered under its
    # PATH-derived ``project:{dir}`` id — confirming the step is surfaced, not
    # merely that the wrong built-in id is absent.
    assert 'project:finalize-step-deploy-target' in discovered_names
    # DEFAULT_PLAN_FINALIZE['steps'] is a lazy None placeholder; the seeded map is
    # built by _seed_finalize_steps() (the discovered default-on built-in set).
    assert 'default:deploy-target' not in cd._seed_finalize_steps()


def test_no_bundled_standards_doc_for_deploy_target():
    """No bundled phase-6-finalize/standards/deploy-target.md exists — the skill
    is project-local under .claude/, not in the plan-marshall bundle."""
    bundled = (
        MARKETPLACE_ROOT
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / 'standards'
        / 'deploy-target.md'
    )
    assert not bundled.exists(), (
        f'Unexpected bundled standards doc: {bundled}. The deploy-target step '
        f'is project-local only; no marketplace bundle should ship it.'
    )


# ---------------------------------------------------------------------------
# 3) Generator behaviour smoke test (integration)
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def fixture_marketplace(tmp_path: Path) -> Path:
    """Tiny single-bundle marketplace for smoke testing the generator."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'demo bundle',
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write(bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n',
    )
    # The Claude target's emit step regenerates a top-level marketplace.json
    # from the source manifest; provide a minimal one so emit mode succeeds.
    _write(
        tmp_path / '.claude-plugin' / 'marketplace.json',
        json.dumps(
            {
                'name': 'fixture-marketplace',
                'plugins': [{'name': 'demo', 'description': 'demo', 'source': './bundles/demo'}],
            },
            indent=2,
        )
        + '\n',
    )
    return marketplace


def test_generator_returns_success_with_emitted_count(fixture_marketplace: Path, tmp_path: Path):
    """The deploy-target executor walks the generator's TOON return — verify
    the live generator produces the expected ``status: success`` with a
    non-zero ``produced`` count for a tiny fixture marketplace."""
    output_dir = tmp_path / 'out'
    result = subprocess.run(
        [
            sys.executable,
            str(_GENERATE_PY),
            '--target', 'claude',
            '--output', str(output_dir),
            '--marketplace-dir', str(fixture_marketplace),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f'generator exit={result.returncode}, stderr={result.stderr}'
    # The generator's stdout includes a "claude: produced N entries" summary line
    assert 'claude:' in result.stdout, f'expected "claude:" in stdout: {result.stdout!r}'
    # Output directory must exist with at least one file
    assert output_dir.is_dir()
    written = list(output_dir.rglob('*'))
    files_only = [p for p in written if p.is_file()]
    assert len(files_only) > 0, 'generator must emit at least one file for a non-empty bundle'


def test_emit_marker_carries_file_hash_manifest(fixture_marketplace: Path, tmp_path: Path):
    """A successful emit writes a ``file_hashes`` manifest into the sentinel.

    The manifest pins every emitted file (keyed by output-root-relative
    POSIX path, excluding the sentinel itself) so the sync staleness guard
    can diagnose per-file drift against transformed generator output without
    re-deriving a raw source counterpart. The manifest must cover exactly the
    emitted regular files minus ``.emit-marker.json``.
    """
    output_dir = tmp_path / 'out'
    result = subprocess.run(
        [
            sys.executable,
            str(_GENERATE_PY),
            '--target', 'claude',
            '--output', str(output_dir),
            '--marketplace-dir', str(fixture_marketplace),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f'generator exit={result.returncode}, stderr={result.stderr}'

    marker_path = output_dir / '.emit-marker.json'
    assert marker_path.is_file(), 'emit must write the .emit-marker.json sentinel'
    marker = json.loads(marker_path.read_text(encoding='utf-8'))

    file_hashes = marker.get('file_hashes')
    assert isinstance(file_hashes, dict), 'sentinel must carry a file_hashes manifest'
    assert file_hashes, 'manifest must be non-empty for a non-empty bundle'
    # The sentinel never lists itself.
    assert '.emit-marker.json' not in file_hashes
    # Every SHA is a 40-char git blob hex digest.
    assert all(len(sha) == 40 for sha in file_hashes.values())

    # The manifest keys are exactly the emitted regular files minus the sentinel.
    emitted_rel = {
        p.relative_to(output_dir).as_posix()
        for p in output_dir.rglob('*')
        if p.is_file() and not p.is_symlink()
    }
    emitted_rel.discard('.emit-marker.json')
    assert set(file_hashes) == emitted_rel
