# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``readme-skill-registration-drift`` rule analyzer.

The analyzer flags every skill a bundle's ``.claude-plugin/plugin.json``
registers that the bundle README never names — a stale enumeration that hides a
registered skill (three of the real-tree undercounts hid a security skill). The
check is coverage-keyed, not headline-count-keyed: a README whose parenthetical
count is off but whose enumeration is complete hides nothing and passes.

Test layers:
  * (D6d) A README omitting a registered skill is flagged, naming that skill; a
    README that names every registered skill passes.
  * Positive population: the population derived over the REAL marketplace tree is
    non-empty and holds a known bundle with its full registration.
  * A longer sibling name never counts as a match (``plan-marshall`` inside
    ``plan-marshall-plugin``).
  * Fail-closed: a bundle with no plugin.json, no README, or no registered
    skills is out of scope and emits nothing.
"""

import json
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

from _plugin_doctor_fixtures import assert_analyzer_findings

_mod = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_readme_skill_coverage.py',
    '_analyze_readme_skill_coverage',
)
analyze_readme_skill_coverage = _mod.analyze_readme_skill_coverage
derive_readme_population = _mod.derive_readme_population
RULE_ID = _mod.RULE_ID


def _write_bundle(root: Path, bundle: str, skills: list[str], readme_body: str) -> Path:
    """Write a synthetic bundle: a plugin.json registering ``skills`` + a README."""
    bundle_dir = root / bundle
    (bundle_dir / '.claude-plugin').mkdir(parents=True, exist_ok=True)
    (bundle_dir / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'name': bundle, 'skills': [f'./skills/{s}' for s in skills]}),
        encoding='utf-8',
    )
    readme = bundle_dir / 'README.md'
    readme.write_text(readme_body, encoding='utf-8')
    return readme


def test_flags_omitted_skill(tmp_path):
    """(D6d) A README missing a registered skill is flagged, naming that skill."""
    _write_bundle(
        tmp_path,
        'demo',
        ['alpha', 'beta', 'gamma-security'],
        '# Demo\n\n### Skills (2 skills)\n\n- `alpha`\n- `beta`\n',
    )
    findings = assert_analyzer_findings(analyze_readme_skill_coverage, tmp_path, [RULE_ID])
    finding = findings[0]
    assert finding['details']['skill'] == 'gamma-security'
    assert finding['details']['population_size'] == 3


def test_passes_complete_enumeration(tmp_path):
    """(D6d) A README naming every registered skill passes, even with an off count."""
    _write_bundle(
        tmp_path,
        'demo',
        ['alpha', 'beta', 'gamma-security'],
        # Deliberately wrong parenthetical count, but every skill is named.
        '# Demo\n\n### Skills (2 skills)\n\n- `alpha`\n- `beta`\n- `gamma-security`\n',
    )
    assert_analyzer_findings(analyze_readme_skill_coverage, tmp_path, [])


def test_longer_sibling_name_is_not_a_match(tmp_path):
    """A registered skill is not counted as named by a longer sibling token."""
    # README names only `plan-marshall-plugin`; the distinct skill `plan-marshall`
    # is registered but never named on its own, so it must be flagged.
    _write_bundle(
        tmp_path,
        'demo',
        ['plan-marshall', 'plan-marshall-plugin'],
        '# Demo\n\n### Skills\n\n- `plan-marshall-plugin`\n',
    )
    findings = analyze_readme_skill_coverage(tmp_path)
    assert [f['details']['skill'] for f in findings] == ['plan-marshall']


def test_positive_population_over_real_tree():
    """The real-tree population is non-empty and holds a known bundle's registration."""
    population = derive_readme_population(MARKETPLACE_ROOT)
    assert len(population) > 0
    by_bundle = {c.bundle: c for c in population}
    assert 'plan-marshall' in by_bundle
    core = by_bundle['plan-marshall']
    assert len(core.registered) > 0
    assert 'manage-lessons' in core.registered
    # The real tree is expected clean after the D4 fixes.
    assert core.undocumented == ()


def test_missing_plugin_json_or_readme_skipped(tmp_path):
    """A bundle lacking a plugin.json or a README is out of scope (no findings)."""
    # plugin.json but no README.
    bundle_dir = tmp_path / 'noreadme'
    (bundle_dir / '.claude-plugin').mkdir(parents=True)
    (bundle_dir / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'skills': ['./skills/alpha']}), encoding='utf-8'
    )
    # README but no plugin.json.
    other = tmp_path / 'nomanifest'
    other.mkdir()
    (other / 'README.md').write_text('# No manifest\n', encoding='utf-8')
    assert_analyzer_findings(analyze_readme_skill_coverage, tmp_path, [])


def test_no_registered_skills_skipped(tmp_path):
    """A bundle whose plugin.json registers no skills is out of scope."""
    _write_bundle(tmp_path, 'empty', [], '# Empty\n\n### Skills (0)\n')
    assert_analyzer_findings(analyze_readme_skill_coverage, tmp_path, [])
