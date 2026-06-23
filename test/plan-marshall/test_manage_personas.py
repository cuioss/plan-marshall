#!/usr/bin/env python3
"""Tests for the ``manage-personas resolve`` verb.

The ``resolve`` verb computes the transitive closure of a persona's composition
DAG and emits one flat, deduped ``skills[]``:

1. always the base ``plan-marshall:persona-plan-marshall-agent``;
2. the persona's direct ``composes:`` frontmatter edges (ref-* and persona-*);
3. recursively, any composed persona's own composes/profiles (DAG, cycle-rejected);
4. for each profile x domain, the domain skills via the Extension API.

Coverage strategy is hybrid:

* **Real-tree** tests drive ``cmd_resolve`` (and the CLI entry point via
  ``run_script``) against the actual shipped persona shells, since
  ``cmd_resolve`` resolves the bundles root from ``Path(__file__)`` of the
  script itself — base-always-first, known-persona success, recursive
  composition + dedup (auditor), and the ``persona_not_found`` /
  ``not_a_persona`` error discriminators.
* **Fixture-based** tests drive the lower-level ``_flatten`` /
  ``_read_persona_frontmatter`` helpers (which take ``bundles_root`` as a
  parameter) against synthetic persona trees written under ``tmp_path``,
  exercising dedup across overlapping composition, cycle rejection, the
  zero-registered-personas edge case, and the inline-vs-block frontmatter
  parsing.

Follows the AAA (Arrange-Act-Assert) pattern; uses the shared
``load_script_module`` / ``run_script`` / ``get_script_path`` test
infrastructure from ``conftest``. Stdlib-only.
"""

import argparse
from pathlib import Path

from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

BASE_PERSONA = 'plan-marshall:persona-plan-marshall-agent'

# Load the script under test as an in-process module. conftest inserts every
# marketplace scripts/ dir onto sys.path at import time, so the module-level
# ``from marketplace_bundles import ...`` / ``from toon_parser import ...``
# imports inside manage_personas resolve cleanly.
_mp = load_script_module('plan-marshall', 'manage-personas', 'manage_personas.py')


# =============================================================================
# Fixture helpers — synthetic persona trees
# =============================================================================


def _write_persona(
    bundles_root: Path,
    bundle: str,
    skill: str,
    *,
    is_persona: bool = True,
    profiles: list[str] | None = None,
    composes: list[str] | None = None,
    block_form: bool = False,
) -> None:
    """Write a synthetic persona SKILL.md into a fixture bundle tree.

    Args:
        bundles_root: The fixture bundles root (parent of ``{bundle}/``).
        bundle: Bundle name segment.
        skill: Skill directory name.
        is_persona: Emit ``implements: persona`` when True.
        profiles: ``profiles:`` frontmatter list (omitted when None).
        composes: ``composes:`` frontmatter list (omitted when None).
        block_form: Emit list fields in block form (``- item`` lines) instead
            of the inline-flow ``[a, b]`` form.
    """
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    lines = ['---', f'name: {skill}', 'mode: knowledge']
    if is_persona:
        lines.append('implements: persona')

    def _emit_list(field: str, values: list[str]) -> None:
        if block_form:
            lines.append(f'{field}:')
            for value in values:
                lines.append(f'  - {value}')
        else:
            lines.append(f'{field}: [{", ".join(values)}]')

    if profiles is not None:
        _emit_list('profiles', profiles)
    if composes is not None:
        _emit_list('composes', composes)
    lines.append('---')
    lines.append('')
    lines.append(f'# {skill}')
    (skill_dir / 'SKILL.md').write_text('\n'.join(lines))


def _flatten_fixture(
    bundles_root: Path,
    persona_key: str,
    domains: list[str] | None = None,
) -> tuple[list[str], str | None]:
    """Run ``_flatten`` over a fixture tree, mirroring ``cmd_resolve``'s setup.

    Seeds the base persona first (as ``cmd_resolve`` does) and walks the
    top-level persona with ``include_self_composition=False``.

    Returns:
        ``(ordered_skills, error_discriminator)`` — ``error_discriminator`` is
        None on success.
    """
    ordered: list[str] = [BASE_PERSONA]
    seen: set[str] = {BASE_PERSONA}
    err = _mp._flatten(
        bundles_root,
        persona_key,
        domains or [],
        ordered,
        seen,
        visiting=set(),
        include_self_composition=False,
    )
    return ordered, err


# =============================================================================
# Real-tree tests — cmd_resolve against the shipped persona shells
# =============================================================================


def _resolve(persona_key: str, domains: str = '') -> dict:
    """Call ``cmd_resolve`` with a constructed argparse Namespace."""
    ns = argparse.Namespace(persona_key=persona_key, domains=domains)
    return _mp.cmd_resolve(ns)


def test_resolve_known_persona_returns_base_first_and_composed_ref():
    # Arrange / Act
    result = _resolve('plan-marshall:persona-implementer')

    # Assert
    assert result['status'] == 'success'
    assert result['persona_key'] == 'plan-marshall:persona-implementer'
    skills = result['skills']
    assert skills[0] == BASE_PERSONA, 'base persona must be first, unconditionally'
    assert 'plan-marshall:ref-code-quality' in skills, (
        'persona-implementer composes ref-code-quality'
    )


def test_resolve_emits_flat_deduped_skills_no_duplicates():
    # Arrange / Act
    result = _resolve('plan-marshall:persona-implementer')

    # Assert
    skills = result['skills']
    assert len(skills) == len(set(skills)), f'skills[] must be deduped: {skills}'


def test_resolve_base_persona_yields_only_the_base():
    # Arrange / Act — the base persona has no profiles and no composes.
    result = _resolve(BASE_PERSONA)

    # Assert — base is always included exactly once even when self-resolved.
    assert result['status'] == 'success'
    assert result['skills'] == [BASE_PERSONA]


def test_resolve_recursive_composition_auditor_dedups_overlapping_refs():
    # Arrange / Act — the auditor composes five other personas, several of
    # which carry overlapping ref-* concerns; the flattened result must dedup.
    result = _resolve('plan-marshall:persona-auditor')

    # Assert
    assert result['status'] == 'success'
    skills = result['skills']
    assert skills[0] == BASE_PERSONA
    assert len(skills) == len(set(skills)), f'recursive composition must dedup: {skills}'
    # Each composed persona's own identity skill is merged as a lens.
    assert 'plan-marshall:persona-implementer' in skills
    assert 'plan-marshall:persona-module-tester' in skills
    # Overlapping ref concern surfaces exactly once.
    assert skills.count('plan-marshall:ref-code-quality') == 1


def test_resolve_unknown_persona_returns_persona_not_found():
    # Arrange / Act
    result = _resolve('plan-marshall:persona-does-not-exist')

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'persona_not_found'
    assert result['persona_key'] == 'plan-marshall:persona-does-not-exist'


def test_resolve_non_persona_skill_returns_not_a_persona():
    # Arrange / Act — ref-code-quality is a real skill but not a persona.
    result = _resolve('plan-marshall:ref-code-quality')

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'not_a_persona'


def test_resolve_malformed_key_without_colon_is_persona_not_found():
    # Arrange / Act — a key with no bundle:skill colon cannot resolve a path.
    result = _resolve('not-a-valid-key')

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'persona_not_found'


# =============================================================================
# CLI E2E — drive the actual entry point via subprocess (constructed argv)
# =============================================================================


def test_cli_resolve_known_persona_emits_success_toon():
    # Arrange
    script = get_script_path('plan-marshall', 'manage-personas', 'manage_personas.py')

    # Act
    result = run_script(
        script,
        'resolve',
        '--persona-key',
        'plan-marshall:persona-implementer',
    )

    # Assert
    assert result.returncode == 0, result.stderr
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['skills'][0] == BASE_PERSONA
    assert 'plan-marshall:ref-code-quality' in parsed['skills']


def test_cli_resolve_unknown_persona_exits_nonzero():
    # Arrange
    script = get_script_path('plan-marshall', 'manage-personas', 'manage_personas.py')

    # Act
    result = run_script(
        script,
        'resolve',
        '--persona-key',
        'plan-marshall:persona-nope',
    )

    # Assert — error status maps to a non-zero process exit.
    assert result.returncode == 1
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'error'
    assert parsed['error'] == 'persona_not_found'


def test_cli_resolve_requires_persona_key():
    # Arrange
    script = get_script_path('plan-marshall', 'manage-personas', 'manage_personas.py')

    # Act — omitting the required --persona-key is an argparse rejection.
    result = run_script(script, 'resolve')

    # Assert
    assert result.returncode == 2


# =============================================================================
# Fixture-based tests — _flatten / _read_persona_frontmatter over synthetic trees
# =============================================================================


def test_flatten_dedups_overlapping_persona_composition(tmp_path):
    # Arrange — a meta persona composing two personas that both compose the
    # same ref concern; the overlap must collapse to a single entry.
    root = tmp_path / 'bundles'
    _write_persona(root, 'plan-marshall', 'persona-plan-marshall-agent')
    _write_persona(
        root, 'plan-marshall', 'persona-a', composes=['plan-marshall:ref-shared']
    )
    _write_persona(
        root, 'plan-marshall', 'persona-b', composes=['plan-marshall:ref-shared']
    )
    _write_persona(
        root,
        'plan-marshall',
        'persona-meta',
        composes=['plan-marshall:persona-a', 'plan-marshall:persona-b'],
    )

    # Act
    skills, err = _flatten_fixture(root, 'plan-marshall:persona-meta')

    # Assert
    assert err is None
    assert skills.count('plan-marshall:ref-shared') == 1, (
        f'overlapping ref concern must dedup: {skills}'
    )
    # Both composed-persona identity skills merge as lenses, exactly once each.
    assert skills.count('plan-marshall:persona-a') == 1
    assert skills.count('plan-marshall:persona-b') == 1


def test_flatten_rejects_composition_cycle(tmp_path):
    # Arrange — persona-x composes persona-y which composes persona-x back.
    root = tmp_path / 'bundles'
    _write_persona(root, 'plan-marshall', 'persona-plan-marshall-agent')
    _write_persona(
        root, 'plan-marshall', 'persona-x', composes=['plan-marshall:persona-y']
    )
    _write_persona(
        root, 'plan-marshall', 'persona-y', composes=['plan-marshall:persona-x']
    )

    # Act
    _skills, err = _flatten_fixture(root, 'plan-marshall:persona-x')

    # Assert
    assert err == 'composition_cycle'


def test_flatten_reports_missing_composed_persona(tmp_path):
    # Arrange — persona-x composes a persona that does not exist on disk.
    root = tmp_path / 'bundles'
    _write_persona(root, 'plan-marshall', 'persona-plan-marshall-agent')
    _write_persona(
        root, 'plan-marshall', 'persona-x', composes=['plan-marshall:persona-ghost']
    )

    # Act
    _skills, err = _flatten_fixture(root, 'plan-marshall:persona-x')

    # Assert
    assert err == 'composed_persona_not_found'


def test_read_frontmatter_returns_none_for_zero_registered_personas(tmp_path):
    # Arrange — an empty bundles tree: no personas registered at all.
    root = tmp_path / 'bundles'
    (root / 'plan-marshall' / 'skills').mkdir(parents=True)

    # Act — resolving any persona key against the empty tree finds nothing.
    fm = _mp._read_persona_frontmatter(root, 'plan-marshall:persona-anything')

    # Assert
    assert fm is None


def test_read_frontmatter_parses_inline_flow_lists(tmp_path):
    # Arrange
    root = tmp_path / 'bundles'
    _write_persona(
        root,
        'plan-marshall',
        'persona-inline',
        profiles=['implementation', 'quality'],
        composes=['plan-marshall:ref-code-quality'],
        block_form=False,
    )

    # Act
    fm = _mp._read_persona_frontmatter(root, 'plan-marshall:persona-inline')

    # Assert
    assert fm is not None
    assert fm['is_persona'] is True
    assert fm['profiles'] == ['implementation', 'quality']
    assert fm['composes'] == ['plan-marshall:ref-code-quality']


def test_read_frontmatter_parses_block_form_lists(tmp_path):
    # Arrange — same fields, block form (``- item`` lines).
    root = tmp_path / 'bundles'
    _write_persona(
        root,
        'plan-marshall',
        'persona-block',
        profiles=['implementation', 'quality'],
        composes=['plan-marshall:ref-code-quality'],
        block_form=True,
    )

    # Act
    fm = _mp._read_persona_frontmatter(root, 'plan-marshall:persona-block')

    # Assert
    assert fm is not None
    assert fm['profiles'] == ['implementation', 'quality']
    assert fm['composes'] == ['plan-marshall:ref-code-quality']


def test_read_frontmatter_flags_non_persona(tmp_path):
    # Arrange — a skill without implements: persona.
    root = tmp_path / 'bundles'
    _write_persona(root, 'plan-marshall', 'just-a-skill', is_persona=False)

    # Act
    fm = _mp._read_persona_frontmatter(root, 'plan-marshall:just-a-skill')

    # Assert
    assert fm is not None
    assert fm['is_persona'] is False


def test_flatten_preserves_deterministic_order(tmp_path):
    # Arrange — composition order is base, then composes edges in declared order.
    root = tmp_path / 'bundles'
    _write_persona(root, 'plan-marshall', 'persona-plan-marshall-agent')
    _write_persona(
        root,
        'plan-marshall',
        'persona-ordered',
        composes=['plan-marshall:ref-one', 'plan-marshall:ref-two', 'plan-marshall:ref-three'],
    )

    # Act
    skills, err = _flatten_fixture(root, 'plan-marshall:persona-ordered')

    # Assert
    assert err is None
    assert skills == [
        BASE_PERSONA,
        'plan-marshall:ref-one',
        'plan-marshall:ref-two',
        'plan-marshall:ref-three',
    ]
