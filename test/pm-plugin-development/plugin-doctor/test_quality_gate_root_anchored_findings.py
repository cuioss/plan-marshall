# SPDX-License-Identifier: FSL-1.1-ALv2
"""Root-anchored anti-vacuity findings survive a ``--paths``-scoped quality gate.

Three rules emit a finding anchored at the marketplace ROOT when their derived
population is empty: ``analyze_thinking_directive_in_workflow_docs``,
``analyze_shim_marker`` (both through a module-level ``EMPTY_POPULATION_TYPE``)
and ``analyze_incident_reference_in_docs`` (its ordinary ``FINDING_TYPE``,
distinguished by ``pattern_family == 'empty_population'`` — passed as an
``extra`` field and flattened onto the finding dict by ``Finding.to_dict()``).

``_finding_in_scope`` keeps a finding only when its path IS a ``--paths`` scope
dir or lies below one. The marketplace root is a strict PARENT of every scope
dir, so that test can never admit a root-anchored finding — under ``--paths``
the guard was dropped and the rule reported zero findings over a population it
had not read. ``cmd_quality_gate`` now keeps a root-anchored finding unfiltered
(``_finding_is_tree_wide``); these tests pin that.

The population that anchors this way is derived from the finding's ANCHOR, not
from a registry of finding types, so a rule that starts anchoring at the root is
covered without being registered anywhere.
"""

from pathlib import Path

import pytest

from conftest import load_script_module

_doctor = load_script_module(
    'pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py', 'doctor_marketplace'
)
_thinking = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_thinking_directive_in_workflow_docs.py',
    '_analyze_thinking_directive_in_workflow_docs',
)
_shim = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_shim_marker.py', '_analyze_shim_marker'
)
_incident = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_incident_reference_in_docs.py',
    '_analyze_incident_reference_in_docs',
)

THINKING_EMPTY_TYPE = _thinking.EMPTY_POPULATION_TYPE
THINKING_STANDARD_REL = _thinking._EXT_POINT_STANDARD_REL
SHIM_EMPTY_TYPE = _shim.EMPTY_POPULATION_TYPE
SHIM_CONVENTION_REL = _shim._CONVENTION_DOC_REL
INCIDENT_TYPE = _incident.FINDING_TYPE


class _Args:
    """Minimal argparse-Namespace stand-in for ``cmd_quality_gate``.

    ``marketplace_root`` is the parent of ``bundles/``; ``paths`` is the
    optional ``--paths`` scope.
    """

    def __init__(self, marketplace_root: str | None = None, paths: list[str] | None = None):
        self.marketplace_root = marketplace_root
        self.paths = paths


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Return ``(repo_root, bundles_root)`` for a fresh empty fixture tree."""
    repo = tmp_path / 'repo'
    bundles = repo / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True)
    return repo / 'marketplace', bundles


def _write(path: Path, content: str = 'placeholder\n') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _scope_dir(bundles: Path) -> Path:
    """A real subdirectory of the tree, used as the ``--paths`` scope.

    It must EXIST: ``_resolve_scope_dirs`` drops a non-existent path, and an
    empty ``scope_dirs`` makes the scope filter the identity — which would make
    every assertion below pass without the fix under test.
    """
    scoped = bundles / 'scoped-bundle' / 'skills' / 'a-skill'
    scoped.mkdir(parents=True, exist_ok=True)
    return scoped


def _findings_of_type(result: dict, finding_type: str) -> list[dict]:
    return [i for i in result['issues'] if i.get('type') == finding_type]


def _summary(result: dict, rule: str) -> dict:
    return next(s for s in result['rules_run'] if s['rule'] == rule)


def _empty_population_tree(tmp_path: Path) -> tuple[Path, Path]:
    """A tree deriving zero members for the two ``EMPTY_POPULATION_TYPE`` rules.

    Both gate their guard on their own convention document existing, so both are
    written; neither an ``implements:`` workflow doc nor any ``scripts/*.py``
    is, so both populations derive empty.
    """
    root, bundles = _fixture_repo(tmp_path)
    _write(bundles / THINKING_STANDARD_REL)
    _write(bundles / SHIM_CONVENTION_REL)
    _scope_dir(bundles)
    return root, bundles


@pytest.mark.parametrize(
    ('rule', 'finding_type'),
    [
        ('analyze_thinking_directive_in_workflow_docs', THINKING_EMPTY_TYPE),
        ('analyze_shim_marker', SHIM_EMPTY_TYPE),
    ],
    ids=['thinking-directive', 'shim-marker'],
)
def test_empty_population_finding_survives_scoped_run(
    tmp_path: Path, rule: str, finding_type: str
) -> None:
    """The root-anchored guard is reported under ``--paths``, not filtered away.

    The rule's summary count is non-zero and the finding itself is present in
    ``issues`` — the positive assertion, so a regression to any other finding
    type is caught too.
    """
    root, bundles = _empty_population_tree(tmp_path)

    result = _doctor.cmd_quality_gate(
        _Args(marketplace_root=str(root), paths=[str(_scope_dir(bundles))])
    )

    assert _summary(result, rule)['findings'] > 0
    findings = _findings_of_type(result, finding_type)
    assert len(findings) == 1
    assert Path(findings[0]['file']).resolve() == bundles.resolve()


def test_empty_population_guard_is_dropped_by_the_scope_test_alone(tmp_path: Path) -> None:
    """``_finding_in_scope`` alone rejects the root anchor — the defect's mechanism.

    Pins WHY the bypass is needed: the guard's own finding fails the scope test,
    so without ``_finding_is_tree_wide`` the scoped run reports zero. Written
    against the scope predicate directly so it stays true regardless of how the
    bypass is wired.
    """
    root, bundles = _empty_population_tree(tmp_path)
    scope = _scope_dir(bundles)

    findings = _thinking.analyze_thinking_directive_in_workflow_docs(bundles)

    assert len(findings) == 1
    assert _doctor._finding_in_scope(findings[0], [scope]) is False
    assert _doctor._finding_is_tree_wide(findings[0], bundles) is True
    assert root.exists()


def test_incident_reference_empty_population_survives_scoped_run(tmp_path: Path) -> None:
    """The ``suppressed(...)``-routed member is kept too.

    ``analyze_incident_reference_in_docs`` reaches the scope filter through
    ``_suppressed``, which calls ``_scoped`` before applying the suppression
    config, so it is scope-filtered exactly as a ``scoped(...)`` rule is. Its
    population is every ``*.md``/``*.py`` under ``*/{skills,agents,commands}/**``
    — so the fixture keeps its only file outside those subtrees, and the scope
    dir is an EMPTY directory (a directory is not a population member).
    """
    root, bundles = _fixture_repo(tmp_path)
    _write(bundles / 'scoped-bundle' / 'README.md')
    scope = _scope_dir(bundles)

    result = _doctor.cmd_quality_gate(_Args(marketplace_root=str(root), paths=[str(scope)]))

    assert _summary(result, 'analyze_incident_reference_in_docs')['findings'] > 0
    findings = _findings_of_type(result, INCIDENT_TYPE)
    assert len(findings) == 1
    assert findings[0].get('pattern_family') == 'empty_population'
    assert findings[0].get('population_size') == 0
    assert Path(findings[0]['file']).resolve() == bundles.resolve()


def test_per_file_findings_still_obey_the_scope_filter(tmp_path: Path) -> None:
    """The bypass is anchor-scoped: an in-tree finding outside the scope is dropped.

    Without this control the rules above would also pass if ``--paths`` had been
    disabled outright rather than given a root-anchor exception.

    ⛔ Driven through a real ``cmd_quality_gate`` run, because the predicate
    assertions below CANNOT detect that failure. This test called only
    ``_finding_in_scope`` and ``_finding_is_tree_wide``; if ``_scoped`` were
    changed to return every finding unfiltered, both predicates would still
    return exactly the same values and the control would still pass — a control
    that cannot fail for the reason it names, which is this plan's own subject
    committed inside the test written to close it.
    """
    root, bundles = _fixture_repo(tmp_path)
    inside = _write(bundles / 'b' / 'skills' / 's' / 'inside.md')
    outside = _write(
        bundles / 'b' / 'skills' / 'other' / 'outside.md',
        'Observed on #812 the run failed.\n',
    )

    result = _doctor.cmd_quality_gate(
        _Args(marketplace_root=str(root), paths=[str(inside.parent)])
    )

    # The out-of-scope file carries a real, file-anchored violation. It must be
    # absent from a run scoped elsewhere — the assertion that actually fails if
    # ``_scoped`` stops filtering.
    anchored = [
        i for i in result['issues']
        if Path(i.get('file', '')).resolve() == outside.resolve()
    ]
    assert anchored == []

    # Supporting unit check on the predicates the gate composes.
    assert _doctor._finding_in_scope({'file': str(inside)}, [inside.parent]) is True
    assert _doctor._finding_in_scope({'file': str(outside)}, [inside.parent]) is False
    assert _doctor._finding_is_tree_wide({'file': str(outside)}, bundles) is False


def test_the_bypass_keys_on_the_anchor_not_on_a_finding_type(tmp_path: Path) -> None:
    """A root-anchored finding of an UNKNOWN type is kept too.

    The bypass must not degrade into a whitelist of the three finding types
    that anchor this way today: a fourth rule that starts anchoring at the root
    is covered without being registered anywhere. Driven with a synthetic
    finding type no rule emits, so a type-list implementation fails here.
    """
    _root, bundles = _fixture_repo(tmp_path)
    scope = _scope_dir(bundles)
    synthetic = {'type': 'a_rule_that_does_not_exist_yet', 'file': str(bundles), 'line': 0}

    assert _doctor._finding_in_scope(synthetic, [scope]) is False
    assert _doctor._finding_is_tree_wide(synthetic, bundles) is True


def test_a_root_anchor_of_a_different_tree_is_not_tree_wide(tmp_path: Path) -> None:
    """``_finding_is_tree_wide`` compares against THIS run's root, not any root.

    A finding anchored at some other directory that happens to be a parent of
    the scope dir — the repository root above ``bundles/``, say — is not a
    whole-tree finding of this gate and stays filtered.
    """
    root, bundles = _fixture_repo(tmp_path)
    _scope_dir(bundles)

    assert _doctor._finding_is_tree_wide({'file': str(root)}, bundles) is False
    assert _doctor._finding_is_tree_wide({'file': str(bundles.parent)}, bundles) is False
    assert _doctor._finding_is_tree_wide({'file': ''}, bundles) is False
    assert _doctor._finding_is_tree_wide({}, bundles) is False
