# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``shim-marker-missing`` rule analyzer.

The analyzer (`analyze_shim_marker`) is a pure static scanner that flags a
migration / back-compat *version shim* — a read path accommodating a data shape
an earlier version of this tooling wrote and the current version no longer
writes — that is unmarked or malformedly marked. The convention
(`pm-plugin-development:plugin-script-architecture` `standards/
shim-marker-convention.md`) requires every shim to carry a `# SHIM(A|B):`
marker declaring an owner, a version floor, and a removal trigger.

The population is DERIVED from `marketplace/bundles/*/skills/*/scripts/**/*.py` —
never a hardcoded path list. Comments are read via `tokenize` (COMMENT tokens
only, so a `#` inside a string is never a comment and the analyzer never
self-triggers on its own doc examples) and function spans via `ast`.

Test layers:
  * (a) Positive — each indicator family fires when unmarked; a malformed marker
        (bad anchor, or a missing required field) fires.
  * (b) Negative (the load-bearing half) — defensive `None`-handling, a
        write-side guard that *rejects* a retired key, a caller that merely
        *triggers* a migration, env-var compatibility, and external-system
        variance do NOT fire; and a well-marked shim is suppressed.
  * (c) Population derivation — an indicator in a file outside
        `skills/*/scripts/` is invisible.
  * (d) Population-size publication — every finding carries the roster size.
  * (e) Empty-population anti-vacuity guard — an empty population fires ONLY
        when the tree actually has bundle/skills structure; a minimal tree is
        clean.
  * (f) Finding shape.
  * (g) Real-marketplace — the population is non-empty (a floor), and the real
        tree produces zero findings (the D1 + D2 regression anchor).
"""

from pathlib import Path

import pytest
from conftest import MARKETPLACE_ROOT, load_script_module
from _fixtures import assert_analyzer_findings


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_mod = _load_module('_analyze_shim_marker', '_analyze_shim_marker.py')

analyze = _mod.analyze_shim_marker
enumerate_scripts = _mod.enumerate_script_files
RULE_ID = _mod.RULE_ID
UNMARKED_TYPE = _mod.UNMARKED_TYPE
MALFORMED_TYPE = _mod.MALFORMED_TYPE
EMPTY_POPULATION_TYPE = _mod.EMPTY_POPULATION_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_script(
    root: Path,
    body: str,
    *,
    bundle: str = 'plan-marshall',
    skill: str = 'fixture-skill',
    name: str = 'mod.py',
) -> Path:
    """Materialize a script under a scratch ``bundle/skills/skill/scripts/`` tree."""
    target = root / bundle / 'skills' / skill / 'scripts' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding='utf-8')
    return target


def _marker(category: str, *, owner='fixture-skill', floor='the rename change', remove='never') -> str:
    """Return a conforming 4-line marker block (2-space indent for a function body)."""
    return (
        f'    # SHIM({category}): tolerate the pre-migration key shape\n'
        f'    # shim-owner: {owner}\n'
        f'    # shim-floor: {floor}\n'
        f'    # shim-remove-when: {remove}\n'
    )


# ===========================================================================
# (a) Positive — unmarked indicators and malformed markers fire
# ===========================================================================


# One comment per indicator family. Each is an unmarked shim → must fire.
_POSITIVE_COMMENTS = [
    '# tolerate a pre-migration key shape written by an older writer',
    '# handle the legacy bare-string form of the entry',
    '# the unforced path returns legacy_string_entry and writes nothing',
    '# a legacy list-of-id-strings is also accepted here',
    '# one-shot and self-disarming once the old key is gone',
    '# accept the older format of the rule as well',
    '# Supports both formats for backward compatibility',
    '# a legacy list is accepted for backward compatibility',
    '# pre-PR#666 files accumulated several blocks',
]


@pytest.mark.parametrize('comment', _POSITIVE_COMMENTS)
def test_unmarked_indicator_fires(tmp_path, comment):
    """An unmarked shim indicator in a script comment fires the rule."""
    _write_script(tmp_path, f'def read_state(data):\n    {comment}\n    return data.get("old")\n')
    findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])
    assert findings[0]['type'] == UNMARKED_TYPE


def test_malformed_marker_missing_category_fires(tmp_path):
    """A `# SHIM:` anchor without a category is a malformed-marker finding."""
    body = (
        'def read_state(data):\n'
        '    # SHIM: tolerate the old key shape\n'
        '    # shim-owner: fixture-skill\n'
        '    # shim-floor: some change\n'
        '    # shim-remove-when: never\n'
        '    return data.get("old")\n'
    )
    _write_script(tmp_path, body)
    findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])
    assert findings[0]['type'] == MALFORMED_TYPE


def test_malformed_marker_missing_field_fires(tmp_path):
    """A conforming anchor missing a required field is a malformed-marker finding."""
    body = (
        'def read_state(data):\n'
        '    # SHIM(B): tolerate the old key shape\n'
        '    # shim-owner: fixture-skill\n'
        '    # shim-floor: some change\n'
        '    return data.get("old")\n'  # no shim-remove-when
    )
    _write_script(tmp_path, body)
    findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])
    assert findings[0]['type'] == MALFORMED_TYPE
    assert 'shim-remove-when' in findings[0]['message']


# ===========================================================================
# (b) Negative — the load-bearing false-positive boundary
# ===========================================================================


_NEGATIVE_BODIES = [
    # ordinary defensive None-handling (the canonical negative)
    'def read(p):\n'
    '    # missing file, malformed JSON, missing key, non-string value all return None\n'
    '    return None\n',
    # write-side guard that REJECTS a retired key (a breaking refusal, not a shim)
    'def check(cfg):\n'
    "    # a typo'd or retired key is rejected rather than silently ignored\n"
    '    raise KeyError\n',
    # a caller that merely TRIGGERS a migration (not the shim definition itself)
    'def scan():\n'
    '    # lazily migrate the pre-home-root credentials dir before scanning\n'
    '    return 1\n',
    # env-var / CLI compatibility (not persisted-data shape)
    'def base():\n'
    '    # PLAN_BASE_DIR is honoured for backward compatibility for tests\n'
    '    return None\n',
    # external-system shape variance (not our own version boundary)
    'def login(name):\n'
    '    # tolerate GitHub login-casing drift across the contents API\n'
    '    return name.lower()\n',
]


@pytest.mark.parametrize('body', _NEGATIVE_BODIES)
def test_negative_boundary_does_not_fire(tmp_path, body):
    """Defensive / rejection / caller / env-var / external comments do NOT fire."""
    _write_script(tmp_path, body)
    assert_analyzer_findings(analyze, tmp_path, [])


def test_well_marked_shim_is_suppressed(tmp_path):
    """A shim indicator covered by a conforming marker in its function is clean."""
    body = (
        'def read_state(data):\n'
        f'{_marker("B")}'
        '    return data.get("old")\n'
    )
    _write_script(tmp_path, body)
    assert_analyzer_findings(analyze, tmp_path, [])


def test_marker_directly_above_long_def_covers_full_body(tmp_path):
    """A marker block sitting directly above a def covers the WHOLE function.

    Regression for the cover-window gap: a conforming marker block is 4 lines, so
    the def lands 4 lines below the anchor. If the gap were < 4 the def would be
    missed, coverage would fall back to a fixed +N window, and an indicator deep
    in a long function body (past that window) would be a FALSE shim_unmarked.
    """
    filler = '\n'.join(f'    v{i} = {i}' for i in range(70))
    body = (
        '# SHIM(A): migrate the retired shape and delete it\n'
        '# shim-owner: fixture-skill\n'
        '# shim-floor: the change that added the new shape\n'
        '# shim-remove-when: no old-shape data remains\n'
        'def migrate(data):\n'
        f'{filler}\n'
        '    # one-shot and self-disarming once the old key is gone\n'
        '    return data\n'
    )
    _write_script(tmp_path, body)
    assert_analyzer_findings(analyze, tmp_path, [])


def test_marker_above_module_constant_suppresses_leading_comment(tmp_path):
    """A module-level marker covers the comment block that describes the shim."""
    body = (
        '# migrate-bot-lists is one-shot and self-disarming once the old key is gone\n'
        '# SHIM(A): retired enabled_bots knob seeded into the new keys and deleted\n'
        '# shim-owner: fixture-skill\n'
        '# shim-floor: the two-list participation change\n'
        '# shim-remove-when: no live config carries enabled_bots\n'
        '_LEGACY_KEY = "enabled_bots"\n'
    )
    _write_script(tmp_path, body)
    assert_analyzer_findings(analyze, tmp_path, [])


# ===========================================================================
# (c) Population derivation — only scripts under skills/*/scripts/ are scanned
# ===========================================================================


def test_indicator_outside_scripts_dir_is_invisible(tmp_path):
    """A shim indicator in a .py file NOT under skills/*/scripts/ is not scanned."""
    # A clean script keeps the population non-empty (so the empty-population guard
    # does not fire); the indicator lives OUTSIDE any scripts/ dir.
    _write_script(tmp_path, 'def clean():\n    return 1\n', name='clean.py')
    outside = tmp_path / 'plan-marshall' / 'skills' / 'fixture-skill' / 'outside.py'
    outside.write_text('def g():\n    # a pre-migration shim here\n    return None\n', encoding='utf-8')
    assert_analyzer_findings(analyze, tmp_path, [])


def test_population_is_derived_not_hardcoded(tmp_path):
    """A script added under a fresh bundle/skill is scanned with no registration."""
    _write_script(
        tmp_path,
        'def f(d):\n    # tolerate a pre-migration shape\n    return d\n',
        bundle='pm-brand-new-bundle',
        skill='brand-new-skill',
    )
    findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])
    assert findings[0]['type'] == UNMARKED_TYPE


# ===========================================================================
# (d) Population-size publication
# ===========================================================================


def test_finding_publishes_population_size(tmp_path):
    """Every finding carries details.population_size equal to the scripts scanned."""
    _write_script(tmp_path, 'def f(d):\n    # a pre-migration shim\n    return d\n', name='a.py')
    _write_script(tmp_path, 'def g():\n    return 1\n', name='b.py')
    findings = analyze(tmp_path)
    assert len(findings) == 1
    assert findings[0]['details']['population_size'] == len(enumerate_scripts(tmp_path))
    assert findings[0]['details']['population_size'] == 2


# ===========================================================================
# (e) Empty-population anti-vacuity guard
# ===========================================================================


_CONVENTION_DOC_REL = _mod._CONVENTION_DOC_REL


def test_empty_population_with_convention_doc_fires(tmp_path):
    """Zero scripts over a tree that DEFINES the convention fires the guard."""
    convention = tmp_path / _CONVENTION_DOC_REL
    convention.parent.mkdir(parents=True)
    convention.write_text('# convention\n', encoding='utf-8')
    findings = analyze(tmp_path)
    assert len(findings) == 1
    assert findings[0]['type'] == EMPTY_POPULATION_TYPE
    assert findings[0]['details']['reason'] == 'empty_population'


def test_bundle_tree_without_convention_doc_is_clean(tmp_path):
    """A tree with skills but zero scripts and no convention doc is NOT flagged.

    This is the shape a doctor clean-fixture tree takes; the guard must not fire
    there or every fixture-based quality-gate test would regress.
    """
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'fixture-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# skill\n', encoding='utf-8')
    assert analyze(tmp_path) == []


def test_minimal_tree_without_bundle_structure_is_clean(tmp_path):
    """A tree with no bundle/skills structure legitimately has no population."""
    (tmp_path / 'notes.txt').write_text('hello\n', encoding='utf-8')
    assert analyze(tmp_path) == []


# ===========================================================================
# (f) Finding shape
# ===========================================================================


def test_finding_shape(tmp_path):
    """A finding carries the documented keys."""
    _write_script(tmp_path, 'def f(d):\n    # a pre-migration shim\n    return d\n')
    finding = analyze(tmp_path)[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['type'] == UNMARKED_TYPE
    assert finding['severity'] == 'error'
    assert finding['fixable'] is False
    assert finding['rule'] == _mod.RULE_NAME
    assert isinstance(finding['line'], int) and finding['line'] >= 1
    assert 'population_size' in finding['details']


# ===========================================================================
# (g) Real-marketplace anchors
# ===========================================================================


def test_real_marketplace_population_is_non_empty():
    """The derived script population over the real tree is well above a floor.

    An anti-vacuity floor: a broken derivation returning near-zero scripts would
    make the whole sweep vacuous.
    """
    population = enumerate_scripts(MARKETPLACE_ROOT)
    assert len(population) >= 100, (
        f'expected the real script population to exceed 100, got {len(population)}'
    )


def test_real_marketplace_tree_produces_zero_findings():
    """The real marketplace tree is clean — the D1 + D2 regression anchor.

    Every migration/back-compat shim in the tree carries a conforming marker,
    and the precision-first indicator set fires on none of the defensive /
    rejection / caller / external code. A regression on either side (a new
    unmarked shim, or an over-broad indicator) turns this red.
    """
    assert analyze(MARKETPLACE_ROOT) == []
