# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``persona-profile-uniqueness`` rule analyzer.

In the persona / ref / profile identity model, a persona skill's **primary**
identity profile is the **first** entry of its ``profiles:`` frontmatter list.
Phase-4-plan reverse-looks-up a task's persona by matching that primary profile,
so no two ``implements: persona`` skills may declare the same first
``profiles:`` entry. This analyzer flags any such collision.

Test layers:
  * Two personas with identical first ``profiles:`` entry → one finding.
  * Two personas with different primary profiles → no finding.
  * A non-persona skill with a duplicate ``profiles:`` first entry → ignored.
  * A meta persona that omits ``profiles:`` → ignored (no primary profile).
  * Block-form ``profiles:`` lists are parsed identically to inline-flow.
  * The rule is registered with a provenance row in ``rule-provenance.md``.
"""

from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_appu = _load_module(
    '_analyze_persona_profile_uniqueness', '_analyze_persona_profile_uniqueness.py'
)

analyze_persona_profile_uniqueness = _appu.analyze_persona_profile_uniqueness
RULE_ID = _appu.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundle tree.
# ---------------------------------------------------------------------------


def _bundles_root(tmp_path: Path) -> Path:
    """Return the ``marketplace/bundles`` root, created under ``tmp_path``."""
    root = tmp_path / 'marketplace' / 'bundles'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_skill(bundles_root: Path, bundle: str, skill: str, body: str) -> Path:
    """Write ``{bundle}/skills/{skill}/SKILL.md`` and return the SKILL.md path."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


def _persona_body(
    name: str,
    *,
    is_persona: bool = True,
    profiles: list[str] | None = None,
    block_form: bool = False,
) -> str:
    """Build a minimal persona SKILL.md body."""
    lines = ['---', f'name: {name}', 'description: A persona', 'mode: knowledge']
    if is_persona:
        lines.append('implements: persona')
    if profiles is not None:
        if block_form:
            lines.append('profiles:')
            for value in profiles:
                lines.append(f'  - {value}')
        else:
            lines.append(f'profiles: [{", ".join(profiles)}]')
    lines.append('---')
    lines.append('')
    lines.append(f'# {name}')
    return '\n'.join(lines) + '\n'


# ===========================================================================
# Collision cases — duplicate primary profile → finding.
# ===========================================================================


def test_two_personas_with_identical_primary_profile_trigger_finding(tmp_path):
    # Arrange — bundle dirs sort alphabetically; persona-a is declared first.
    root = _bundles_root(tmp_path)
    _write_skill(
        root, 'plan-marshall', 'persona-a', _persona_body('persona-a', profiles=['implementation'])
    )
    _write_skill(
        root, 'plan-marshall', 'persona-b', _persona_body('persona-b', profiles=['implementation'])
    )

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['details']['primary_profile'] == 'implementation'
    assert finding['details']['conflicting_skill'] == 'persona-a'
    # The finding attaches to the later-declared colliding persona.
    assert finding['file'].endswith('persona-b/SKILL.md')


def test_collision_only_on_first_profile_not_secondary(tmp_path):
    # Arrange — both share 'quality' as a SECONDARY profile; primaries differ.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-impl',
        _persona_body('persona-impl', profiles=['implementation', 'quality']),
    )
    _write_skill(
        root,
        'plan-marshall',
        'persona-test',
        _persona_body('persona-test', profiles=['module_testing', 'quality']),
    )

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert — a shared non-primary profile is not a collision.
    assert findings == []


def test_block_form_profiles_collide_same_as_inline(tmp_path):
    # Arrange — one inline-flow, one block-form, same primary entry.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-x',
        _persona_body('persona-x', profiles=['documentation']),
    )
    _write_skill(
        root,
        'plan-marshall',
        'persona-y',
        _persona_body('persona-y', profiles=['documentation'], block_form=True),
    )

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert
    assert len(findings) == 1
    assert findings[0]['details']['primary_profile'] == 'documentation'


# ===========================================================================
# Clean cases — no finding.
# ===========================================================================


def test_two_personas_with_different_primary_profiles_are_clean(tmp_path):
    # Arrange
    root = _bundles_root(tmp_path)
    _write_skill(
        root, 'plan-marshall', 'persona-a', _persona_body('persona-a', profiles=['implementation'])
    )
    _write_skill(
        root, 'plan-marshall', 'persona-b', _persona_body('persona-b', profiles=['module_testing'])
    )

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert
    assert findings == []


def test_non_persona_skill_with_duplicate_profiles_is_ignored(tmp_path):
    # Arrange — a persona owns 'implementation'; a NON-persona skill also
    # declares profiles: [implementation], which must NOT collide.
    root = _bundles_root(tmp_path)
    _write_skill(
        root, 'plan-marshall', 'persona-a', _persona_body('persona-a', profiles=['implementation'])
    )
    _write_skill(
        root,
        'plan-marshall',
        'just-a-skill',
        _persona_body('just-a-skill', is_persona=False, profiles=['implementation']),
    )

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert — only persona skills participate in the uniqueness check.
    assert findings == []


def test_meta_persona_without_profiles_is_exempt(tmp_path):
    # Arrange — two meta personas that omit profiles: entirely.
    root = _bundles_root(tmp_path)
    _write_skill(root, 'plan-marshall', 'persona-auditor', _persona_body('persona-auditor'))
    _write_skill(root, 'plan-marshall', 'persona-reviewer', _persona_body('persona-reviewer'))

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert — personas with no primary profile are not subject to the check.
    assert findings == []


def test_empty_tree_yields_no_findings(tmp_path):
    # Arrange — zero registered personas.
    root = _bundles_root(tmp_path)

    # Act
    findings = analyze_persona_profile_uniqueness(root)

    # Assert
    assert findings == []


# ===========================================================================
# Registration — rule is wired with a provenance row.
# ===========================================================================


def test_rule_id_present_in_rule_provenance_table():
    # Arrange
    provenance = (
        MARKETPLACE_ROOT
        / 'pm-plugin-development'
        / 'skills'
        / 'plugin-doctor'
        / 'references'
        / 'rule-provenance.md'
    )

    # Act
    text = provenance.read_text(encoding='utf-8')

    # Assert — the rule id appears as a provenance-table row entry.
    assert f'`{RULE_ID}`' in text
    assert '_analyze_persona_profile_uniqueness.py' in text
