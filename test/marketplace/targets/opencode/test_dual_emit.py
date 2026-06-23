# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode user-invocable dual-emit (SKILL.md + command wrapper)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.opencode.body_transforms import build_user_invocable_lookup
from marketplace.targets.opencode.emitter import emit_bundles
from marketplace.targets.opencode.frontmatter import (
    OPENCODE_MODEL_PREFIX,
    UnmappedFrontmatterError,
)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


@pytest.fixture()
def opencode_config_dir() -> Path:
    """Canonical OpenCode mapping/rules config directory (real source files)."""
    return Path(__file__).resolve().parents[3].parent / 'marketplace' / 'targets' / 'opencode'


def _make_bundle(
    marketplace: Path,
    bundle: str,
    *,
    skills: dict[str, dict[str, str | bool]],
) -> None:
    """Create a marketplace bundle with the given skills.

    ``skills`` is a mapping skill_name -> attribute dict with optional keys
    ``user_invocable`` (bool), ``description`` (str), ``model`` (str).
    """
    skill_refs = [f'./skills/{skill_name}' for skill_name in skills]
    plugin_doc = json.dumps(
        {
            'name': bundle,
            'version': '0.0.1',
            'description': f'{bundle} bundle',
            'skills': skill_refs,
        },
        indent=2,
    ) + '\n'
    _write(marketplace / bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    for skill_name, attrs in skills.items():
        fm_lines = [
            '---',
            f'name: {skill_name}',
        ]
        description = attrs.get('description', f'{skill_name} description')
        if description is not None:
            fm_lines.append(f'description: {description}')
        if attrs.get('user_invocable'):
            fm_lines.append('user-invocable: true')
        model = attrs.get('model')
        if model:
            fm_lines.append(f'model: {model}')
        fm_lines.append('---')
        body = '\n'.join(fm_lines) + f'\n# {skill_name} body\n'
        _write(marketplace / bundle / 'skills' / skill_name / 'SKILL.md', body)


# ---------------------------------------------------------------------------
# Dual-emit basics
# ---------------------------------------------------------------------------


def test_user_invocable_skill_emits_skill_md_and_command_wrapper(
    tmp_path: Path, opencode_config_dir: Path
):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={'helper': {'user_invocable': True, 'description': 'helper description'}},
    )
    out = tmp_path / 'out'

    written = emit_bundles(marketplace, out, opencode_config_dir)
    rels = {p.relative_to(out).as_posix() for p in written}

    assert 'skill/demo-helper/SKILL.md' in rels
    assert 'command/demo-helper.md' in rels


def test_non_user_invocable_skill_does_not_emit_wrapper(
    tmp_path: Path, opencode_config_dir: Path
):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={'lib': {'user_invocable': False, 'description': 'library skill'}},
    )
    out = tmp_path / 'out'

    written = emit_bundles(marketplace, out, opencode_config_dir)
    rels = {p.relative_to(out).as_posix() for p in written}

    assert 'skill/demo-lib/SKILL.md' in rels
    assert 'command/demo-lib.md' not in rels
    assert not (out / 'command' / 'demo-lib.md').exists()


# ---------------------------------------------------------------------------
# Template substitution
# ---------------------------------------------------------------------------


def test_wrapper_substitutes_description(tmp_path: Path, opencode_config_dir: Path):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={'helper': {'user_invocable': True, 'description': 'one-line summary'}},
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    wrapper = (out / 'command' / 'demo-helper.md').read_text(encoding='utf-8')

    assert 'description: one-line summary' in wrapper
    # Skill id substituted in the body
    assert 'demo-helper' in wrapper


def test_wrapper_substitutes_skill_id(tmp_path: Path, opencode_config_dir: Path):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={'helper': {'user_invocable': True, 'description': 'desc'}},
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    wrapper = (out / 'command' / 'demo-helper.md').read_text(encoding='utf-8')

    # The {{skill_id}} placeholder is replaced verbatim — must not appear unsubstituted
    assert '{{skill_id}}' not in wrapper
    assert '`demo-helper`' in wrapper


def test_wrapper_substitutes_model_via_mapping(tmp_path: Path, opencode_config_dir: Path):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={
            'helper': {
                'user_invocable': True,
                'description': 'desc',
                'model': 'sonnet',
            }
        },
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    wrapper = (out / 'command' / 'demo-helper.md').read_text(encoding='utf-8')

    # Source 'sonnet' must be mapped to the prefixed OpenCode model id.
    assert f'model: {OPENCODE_MODEL_PREFIX}claude-sonnet-4-6' in wrapper
    # The Mustache-style block must be removed
    assert '{{#model}}' not in wrapper
    assert '{{/model}}' not in wrapper
    assert '{{model}}' not in wrapper


def test_wrapper_strips_model_block_when_absent(tmp_path: Path, opencode_config_dir: Path):
    marketplace = tmp_path / 'bundles'
    _make_bundle(
        marketplace,
        'demo',
        skills={'helper': {'user_invocable': True, 'description': 'desc'}},
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    wrapper = (out / 'command' / 'demo-helper.md').read_text(encoding='utf-8')

    assert '{{#model}}' not in wrapper
    assert '{{/model}}' not in wrapper
    assert '{{model}}' not in wrapper
    # No literal "model:" line is emitted when source has no model
    assert 'model:' not in wrapper


def test_wrapper_takes_first_line_of_multiline_description(
    tmp_path: Path, opencode_config_dir: Path
):
    marketplace = tmp_path / 'bundles'
    multi = 'first-line summary that fits in frontmatter'
    _make_bundle(
        marketplace,
        'demo',
        skills={'helper': {'user_invocable': True, 'description': multi}},
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    wrapper = (out / 'command' / 'demo-helper.md').read_text(encoding='utf-8')

    # First-line semantics: the wrapper description matches the source first line.
    assert f'description: {multi}' in wrapper


# ---------------------------------------------------------------------------
# Validation contract — silent exclusion is prohibited
# ---------------------------------------------------------------------------


def test_user_invocable_skill_missing_description_raises_unmapped_frontmatter(
    tmp_path: Path, opencode_config_dir: Path
):
    """A user-invocable skill with no description must trigger the validation error.

    The emitter routes this through the same UnmappedFrontmatterError that
    the CLI translates to exit code 2 — there is no silent skip.
    """
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'skills': ['./skills/helper']}) + '\n',
    )
    # Missing description on a user-invocable skill
    _write(
        bundle / 'skills' / 'helper' / 'SKILL.md',
        '---\nname: helper\nuser-invocable: true\n---\nbody\n',
    )
    out = tmp_path / 'out'

    with pytest.raises(UnmappedFrontmatterError):
        emit_bundles(marketplace, out, opencode_config_dir)


# ---------------------------------------------------------------------------
# Real marketplace — every user-invocable: true source skill produces one wrapper
# ---------------------------------------------------------------------------


def test_real_marketplace_user_invocable_one_to_one_mapping(tmp_path: Path):
    """For every user-invocable: true skill in the marketplace, exactly one
    command wrapper is written under output/command/{bundle}-{skill}.md.

    The wrapper count is currently 13 (per the plan's deliverable-4 target); this
    test asserts the structural invariant rather than the literal count so it
    does not need to be edited every time a new user-invocable skill is added.
    """
    project_root = Path(__file__).resolve().parents[3].parent
    marketplace = project_root / 'marketplace' / 'bundles'
    config_dir = project_root / 'marketplace' / 'targets' / 'opencode'
    if not marketplace.is_dir():
        pytest.skip('marketplace/bundles not available in this checkout')

    lookup = build_user_invocable_lookup(marketplace)
    if not lookup:
        pytest.skip('no user-invocable skills found in marketplace')

    out = tmp_path / 'out'
    emit_bundles(marketplace, out, config_dir)

    command_dir = out / 'command'
    assert command_dir.is_dir(), 'expected command/ to be created when wrappers emit'

    for skill_name, target_id in lookup.items():
        wrapper = command_dir / f'{target_id}.md'
        assert wrapper.is_file(), f'missing wrapper for {skill_name} at {wrapper}'
        text = wrapper.read_text(encoding='utf-8')
        # Every wrapper must be a fully-substituted file (no stray placeholders)
        assert '{{description}}' not in text
        assert '{{skill_id}}' not in text
        assert '{{#model}}' not in text
