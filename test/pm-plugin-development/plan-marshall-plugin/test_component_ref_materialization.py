#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for per-bundle component-reference materialization.

``discover_plugin_modules`` stamps every bundle module with a ``component_refs``
list holding that bundle's outbound references to other bundles. The list is the
caller-side materialization the Axis-C derivation-resolver contract requires: a
resolver is a pure function of its arguments, so the filesystem-reading
dependency engine has to run at discovery time and its component-granular
vocabulary (``bundle:skill:script``) has to be projected onto the bundle
granularity the architecture graph keys on before a resolver ever sees it.

The fixture marketplace below is built so that every ``DependencyType`` value is
reachable from one bundle, and so that ``resolved`` is a discriminating flag
rather than a constant — ``alpha`` references a bundle that exists (``beta``)
and one that does not (``gamma``).
"""

import json
import tempfile
from pathlib import Path

from _dep_detection import DependencyType
from plugin_discover import build_component_refs, discover_plugin_modules

ALL_DEP_TYPES = frozenset(member.value for member in DependencyType)
"""Every dependency kind the authoritative :class:`DependencyType` enum declares.

Derived rather than restated as literals: a sixth kind added to the enum must
fail the round-trip sweep below (the fixture does not produce it yet) instead of
slipping through a hand-listed set that still reads as complete.
"""

# =============================================================================
# Fixture marketplace
#
# alpha  — carries every dependency type outbound, with deliberate duplicates
# beta   — referenced by alpha; carries no outbound references itself
# plan-marshall — import target for ``toon_parser`` (PYTHON_MODULE_MAPPINGS);
#          carries no outbound references itself
# gamma  — deliberately absent from disk, so references to it stay unresolved
# =============================================================================

# ``beta:b-skill:b_script`` appears twice on purpose: the materialized field
# deduplicates on the (target_bundle, dep_type, resolved) triple, so both
# mentions must collapse into a single entry. The relative link supplies the
# ``path`` edge and the frontmatter supplies ``implements`` and ``skill``.
ALPHA_SKILL_MD = """---
name: a-skill
description: Alpha fixture skill
implements: beta:b-skill/standards/contract.md
---

# A Skill

Run `python3 .plan/execute-script.py beta:b-skill:b_script run` to start.

Re-run `python3 .plan/execute-script.py beta:b-skill:b_script run` to retry.

Skill: beta:b-skill

Skill: beta:b-skill

Skill: gamma:missing-skill

See [the beta skill](../../../beta/skills/b-skill/SKILL.md) for details.
"""

# Imports a module in PYTHON_MODULE_MAPPINGS, which the engine maps onto
# ``plan-marshall:ref-toon-format:toon_parser`` — present in the fixture, so the
# resulting ``import`` reference resolves.
ALPHA_SCRIPT_PY = """#!/usr/bin/env python3
\"\"\"Alpha fixture script.\"\"\"

from toon_parser import parse_toon

RESULT = parse_toon
"""

BETA_SKILL_MD = """---
name: b-skill
description: Beta fixture skill
---

# B Skill

This skill is a reference target only.
"""

INERT_SCRIPT_PY = """#!/usr/bin/env python3
\"\"\"Fixture script with no outbound references.\"\"\"

VALUE = 1
"""

TOON_PARSER_SKILL_MD = """---
name: ref-toon-format
description: Fixture stand-in for the TOON format skill
---

# Ref Toon Format

This skill is a reference target only.
"""


def _write(path: Path, content: str) -> None:
    """Create parent directories and write ``content`` to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _write_bundle(bundles_dir: Path, bundle: str, skill: str) -> Path:
    """Create ``bundle`` with a single ``skill`` and return the skill directory."""
    _write(
        bundles_dir / bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': bundle, 'version': '1.0.0', 'skills': [f'./skills/{skill}']}),
    )
    return bundles_dir / bundle / 'skills' / skill


def _build_fixture_marketplace(root: Path) -> None:
    """Populate ``root`` with the fixture marketplace described above."""
    _write(
        root / 'marketplace' / '.claude-plugin' / 'marketplace.json',
        json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}),
    )
    bundles_dir = root / 'marketplace' / 'bundles'

    alpha_skill = _write_bundle(bundles_dir, 'alpha', 'a-skill')
    _write(alpha_skill / 'SKILL.md', ALPHA_SKILL_MD)
    _write(alpha_skill / 'scripts' / 'a_script.py', ALPHA_SCRIPT_PY)

    beta_skill = _write_bundle(bundles_dir, 'beta', 'b-skill')
    _write(beta_skill / 'SKILL.md', BETA_SKILL_MD)
    _write(beta_skill / 'scripts' / 'b_script.py', INERT_SCRIPT_PY)

    toon_skill = _write_bundle(bundles_dir, 'plan-marshall', 'ref-toon-format')
    _write(toon_skill / 'SKILL.md', TOON_PARSER_SKILL_MD)
    _write(toon_skill / 'scripts' / 'toon_parser.py', INERT_SCRIPT_PY)


def _triples(refs: list[dict]) -> set[tuple[str, str, bool]]:
    """Project reference dicts onto their identity triples."""
    return {(ref['target_bundle'], ref['dep_type'], ref['resolved']) for ref in refs}


def _modules_by_name(root: Path) -> dict[str, dict]:
    """Run discovery over ``root`` and index the resulting modules by name."""
    return {module['name']: module for module in discover_plugin_modules(str(root))}


# =============================================================================
# component_refs is materialized onto every discovered module
# =============================================================================


def test_every_module_carries_component_refs():
    """Discovery stamps a component_refs list onto each bundle module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        modules = _modules_by_name(root)

        assert set(modules) == {'alpha', 'beta', 'plan-marshall'}
        for name, module in modules.items():
            assert 'component_refs' in module, f'{name} is missing component_refs'
            assert isinstance(module['component_refs'], list)


def test_refs_are_produced_for_the_fixture_bundle_tree():
    """The referencing bundle carries exactly the expected projected references."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        assert _triples(refs) == {
            ('beta', 'implements', True),
            ('beta', 'path', True),
            ('beta', 'script', True),
            ('beta', 'skill', True),
            ('gamma', 'skill', False),
            ('plan-marshall', 'import', True),
        }


def test_every_entry_carries_the_three_contract_fields():
    """Each entry is exactly {target_bundle, dep_type, resolved}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        assert refs
        for ref in refs:
            assert set(ref) == {'target_bundle', 'dep_type', 'resolved'}
            assert isinstance(ref['target_bundle'], str)
            assert isinstance(ref['dep_type'], str)
            assert isinstance(ref['resolved'], bool)


# =============================================================================
# Every dependency type round-trips
# =============================================================================


def test_every_dep_type_round_trips():
    """Every ``DependencyType`` value survives materialization.

    The expected set is derived from the enum, so a sixth kind added there turns
    this into a red test naming the gap rather than leaving a hand-listed set of
    five that still reads as complete while the new kind goes untested.
    """
    assert ALL_DEP_TYPES, 'the derived dep-type population must not be empty'

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        assert {ref['dep_type'] for ref in refs} == set(ALL_DEP_TYPES)


# =============================================================================
# Unresolved targets are stamped, not dropped
# =============================================================================


def test_unresolved_target_is_stamped_rather_than_dropped():
    """A reference to a bundle that does not exist survives with resolved False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        unresolved = [ref for ref in refs if not ref['resolved']]
        assert [(ref['target_bundle'], ref['dep_type']) for ref in unresolved] == [('gamma', 'skill')]


def test_resolved_flag_discriminates():
    """The fixture yields both resolved and unresolved entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        assert any(ref['resolved'] for ref in refs)
        assert any(not ref['resolved'] for ref in refs)


# =============================================================================
# Deduplication on the (target_bundle, dep_type, resolved) triple
# =============================================================================


def test_repeated_references_collapse_to_one_entry():
    """Two mentions of the same script and skill yield one entry each."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs = _modules_by_name(root)['alpha']['component_refs']

        assert [ref for ref in refs if ref['dep_type'] == 'script'] == [
            {'target_bundle': 'beta', 'dep_type': 'script', 'resolved': True}
        ]
        assert [ref for ref in refs if ref['dep_type'] == 'skill' and ref['target_bundle'] == 'beta'] == [
            {'target_bundle': 'beta', 'dep_type': 'skill', 'resolved': True}
        ]


def test_field_holds_no_duplicate_triples():
    """No entry repeats another entry's identity triple."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        for module in _modules_by_name(root).values():
            refs = module['component_refs']
            assert len(_triples(refs)) == len(refs)


# =============================================================================
# A bundle with no outbound references yields an empty list, not a missing key
# =============================================================================


def test_bundle_without_outbound_refs_yields_empty_list():
    """Reference-target-only bundles carry the key with an empty list value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        modules = _modules_by_name(root)

        assert modules['beta']['component_refs'] == []
        assert modules['plan-marshall']['component_refs'] == []


def test_build_component_refs_omits_bundles_without_refs():
    """The helper mapping only carries bundles that reference something.

    ``discover_plugin_modules`` is what turns that absence into the empty list
    every module dict carries, so the two layers are asserted separately.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        refs_by_bundle = build_component_refs(root)

        assert set(refs_by_bundle) == {'alpha'}


# =============================================================================
# Materialization is unconditional
# =============================================================================


def test_materialization_needs_no_flag_or_environment_opt_in():
    """No argument, flag, or environment variable gates the materialization.

    ``discover_plugin_modules`` takes only the project root, and the field is
    populated on a bare call — a regression that reintroduced an opt-in gate
    would have to change this signature to stay green.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _build_fixture_marketplace(root)

        modules = discover_plugin_modules(str(root))

        assert [module['name'] for module in modules if module['component_refs']] == ['alpha']


def test_missing_bundles_directory_yields_no_refs():
    """A marketplace with no bundles directory materializes an empty mapping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _write(
            root / 'marketplace' / '.claude-plugin' / 'marketplace.json',
            json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}),
        )

        assert build_component_refs(root) == {}
