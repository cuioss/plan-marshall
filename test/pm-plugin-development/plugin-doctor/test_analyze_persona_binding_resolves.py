# ruff: noqa: I001, E402
"""Tests for the ``persona-binding-resolves`` rule analyzer.

Every persona that declares a ``profiles:`` binding is a dispatch target
phase-4-plan resolves via ``manage-personas resolve``. The binding must be
backed by a resolvable persona: the persona's composition DAG must walk cleanly
(no cycle, every composed ``persona-*`` present on disk) so the resolver returns
a non-empty ``skills[]`` rather than an error discriminator. The analyzer checks
this statically by mirroring the resolver's DAG walk.

Test layers:
  * A ``profiles:`` binding whose composition resolves → clean.
  * A binding whose composed persona is missing → finding
    (``resolve_error == composed_persona_not_found``).
  * A binding in a composition cycle → finding
    (``resolve_error == composition_cycle``).
  * Non-persona skills → not checked.
  * Meta personas that omit ``profiles:`` → out of scope.
  * The rule id is present in ``rule-provenance.md``.
"""

from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_apbr = _load_module('_analyze_persona_binding_resolves', '_analyze_persona_binding_resolves.py')

analyze_persona_binding_resolves = _apbr.analyze_persona_binding_resolves
RULE_ID = _apbr.RULE_ID


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
    composes: list[str] | None = None,
) -> str:
    """Build a minimal persona SKILL.md body (inline-flow lists)."""
    lines = ['---', f'name: {name}', 'description: A persona', 'mode: knowledge']
    if is_persona:
        lines.append('implements: persona')
    if profiles is not None:
        lines.append(f'profiles: [{", ".join(profiles)}]')
    if composes is not None:
        lines.append(f'composes: [{", ".join(composes)}]')
    lines.append('---')
    lines.append('')
    lines.append(f'# {name}')
    return '\n'.join(lines) + '\n'


# ===========================================================================
# Clean cases — resolvable binding → no finding.
# ===========================================================================


def test_resolvable_binding_with_ref_composition_is_clean(tmp_path):
    # Arrange — a persona declaring profiles + a ref-* composition (a leaf skill
    # that need not itself be a persona) resolves cleanly.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-implementer',
        _persona_body(
            'persona-implementer',
            profiles=['implementation'],
            composes=['plan-marshall:ref-code-quality'],
        ),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert — ref-* edges are leaf concerns, not personas; the walk succeeds.
    assert findings == []


def test_resolvable_binding_composing_present_persona_is_clean(tmp_path):
    # Arrange — a profile-declaring persona composing another present persona.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-child',
        _persona_body('persona-child', profiles=['module_testing']),
    )
    _write_skill(
        root,
        'plan-marshall',
        'persona-parent',
        _persona_body(
            'persona-parent',
            profiles=['implementation'],
            composes=['plan-marshall:persona-child'],
        ),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert
    assert findings == []


def test_binding_with_no_composition_resolves_to_base_only(tmp_path):
    # Arrange — a profile-declaring persona with no composes: still resolves
    # (the resolver always seeds the base, so skills[] is non-empty).
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-bare',
        _persona_body('persona-bare', profiles=['implementation']),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert
    assert findings == []


# ===========================================================================
# Unresolvable cases — broken composition → finding.
# ===========================================================================


def test_missing_composed_persona_triggers_finding(tmp_path):
    # Arrange — the composed persona does not exist on disk.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-broken',
        _persona_body(
            'persona-broken',
            profiles=['implementation'],
            composes=['plan-marshall:persona-ghost'],
        ),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['details']['resolve_error'] == 'composed_persona_not_found'
    assert finding['details']['profiles'] == ['implementation']


def test_composition_cycle_triggers_finding(tmp_path):
    # Arrange — persona-x composes persona-y composes persona-x; persona-x
    # declares a profiles binding so it is in scope.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-x',
        _persona_body(
            'persona-x', profiles=['implementation'], composes=['plan-marshall:persona-y']
        ),
    )
    _write_skill(
        root,
        'plan-marshall',
        'persona-y',
        _persona_body('persona-y', composes=['plan-marshall:persona-x']),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert — persona-x (the in-scope, profile-declaring persona) is flagged.
    cycle_findings = [f for f in findings if f['details']['resolve_error'] == 'composition_cycle']
    assert len(cycle_findings) >= 1
    assert any(f['details']['persona_key'] == 'plan-marshall:persona-x' for f in cycle_findings)


# ===========================================================================
# Out-of-scope cases — not checked.
# ===========================================================================


def test_non_persona_skill_is_not_checked(tmp_path):
    # Arrange — a non-persona skill with a broken composes: must be ignored.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'just-a-skill',
        _persona_body(
            'just-a-skill',
            is_persona=False,
            profiles=['implementation'],
            composes=['plan-marshall:persona-ghost'],
        ),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert
    assert findings == []


def test_meta_persona_without_profiles_is_out_of_scope(tmp_path):
    # Arrange — a meta persona omitting profiles: even with a broken composes:
    # is not a dispatch target and is not checked.
    root = _bundles_root(tmp_path)
    _write_skill(
        root,
        'plan-marshall',
        'persona-auditor',
        _persona_body('persona-auditor', composes=['plan-marshall:persona-ghost']),
    )

    # Act
    findings = analyze_persona_binding_resolves(root)

    # Assert
    assert findings == []


def test_empty_tree_yields_no_findings(tmp_path):
    # Arrange
    root = _bundles_root(tmp_path)

    # Act
    findings = analyze_persona_binding_resolves(root)

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

    # Assert
    assert f'`{RULE_ID}`' in text
    assert '_analyze_persona_binding_resolves.py' in text
