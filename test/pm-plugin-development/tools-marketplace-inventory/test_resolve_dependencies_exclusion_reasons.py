#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the unresolved-row partition and the routed exclusions.

Two changes to the dependency validator are pinned here.

**(c) The five formerly-unconditional skips are now routed exclusions.** A
comment line, a line carrying a URL, a URI-scheme bundle, a digit-leading bundle
and an all-digit middle segment used to be bare ``continue`` statements in
``detect_script_notations``. That made them FAIL-OPEN: a genuine reference that
happened to sit on a comment line or beside a URL was discarded before anything
could examine it, and no report could ever mention it. Each is now recorded as
the SHAPE it matched, and the index — which alone knows what exists — makes the
keep/drop call. The tests below assert the reason each shape records, and that a
real notation sharing a line with a URL now survives to the index.

**(a) Every unresolved row states a reason.** ``unresolved_reason`` partitions
the unresolved set into ``missing-component`` (the bundle IS indexed, so the
named component genuinely does not exist), ``unknown-bundle`` (not indexed at
all — possibly an npm script name or a Gradle coordinate, not yet triaged) and
``unregistered-verb`` (the entry script exists but registers no such verb). The
precedence between them is load-bearing and is asserted directly.

**(d) The retarget's premise is tested.** A three-part notation whose script
segment names a VERB is retargeted onto the skill's entry script — but only when
that script actually registers the verb. The ground truth is the script's
``--help``-derived argparse surface, which is an out-of-process probe; the tests
that need a known verb set substitute that ORACLE (``derive_surface`` /
``is_derivable``) rather than the logic under test, so the refusal ordering — the
refusal is checked BEFORE the exclusion drop, or the refused row would vanish —
is exercised for real.
"""

from pathlib import Path

import _dep_detection as _dep_detection_mod
import pytest

from conftest import load_script_module

# ``_dep_detection`` is imported PLAINLY rather than file-loaded. A file-load
# publishes the module under its stem in ``sys.modules``, and sibling test modules
# import this one plainly — so loading it here would displace their copy, which is
# exactly the order-dependent hazard the loader-contract guard tracks. The plain
# import shares the single copy that ``_dep_index``'s own ``from _dep_detection
# import ...`` resolves to, which is what keeps the enum members and dataclasses
# below identical to the objects the index compares against.
#
# The two file-loads state their SCRIPT and MODULE NAME as literals. An indirection
# wrapper forwarding them as parameters cannot be resolved statically, and an
# unresolvable loader call site is one the collision guard is blind to — see
# test/plan-marshall/script-shared/test_conftest_loader_contract.py.
_dep_index_mod = load_script_module(
    'pm-plugin-development',
    'tools-marketplace-inventory',
    '_dep_index.py',
    '_dep_index',
)
_resolve_mod = load_script_module(
    'pm-plugin-development',
    'tools-marketplace-inventory',
    'resolve-dependencies.py',
    'resolve_dependencies',
)

ComponentId = _dep_detection_mod.ComponentId
Dependency = _dep_detection_mod.Dependency
DependencyType = _dep_detection_mod.DependencyType
Exclusion = _dep_detection_mod.Exclusion
VERB_BEARING_EXCLUSIONS = _dep_detection_mod.VERB_BEARING_EXCLUSIONS
detect_script_notations = _dep_detection_mod.detect_script_notations

build_dependency_index = _dep_index_mod.build_dependency_index
indexed_bundles = _dep_index_mod.indexed_bundles
unresolved_reason = _dep_index_mod.unresolved_reason
UNRESOLVED_REASONS = _dep_index_mod.UNRESOLVED_REASONS
UNRESOLVED_REASON_MISSING_COMPONENT = _dep_index_mod.UNRESOLVED_REASON_MISSING_COMPONENT
UNRESOLVED_REASON_UNKNOWN_BUNDLE = _dep_index_mod.UNRESOLVED_REASON_UNKNOWN_BUNDLE
UNRESOLVED_REASON_UNREGISTERED_VERB = _dep_index_mod.UNRESOLVED_REASON_UNREGISTERED_VERB

cmd_validate = _resolve_mod.cmd_validate


_SOURCE = ComponentId(bundle='test', component_type='skill', name='test')


def _only(deps):
    assert len(deps) == 1, f'expected exactly one detected notation, got {len(deps)}'
    return deps[0]


# =============================================================================
# (c) The five formerly-unconditional skips record a reason
# =============================================================================


class TestRoutedExclusionReasons:
    """Each formerly-unconditional skip records its own shape."""

    @pytest.mark.parametrize(
        ('line', 'expected'),
        [
            pytest.param(
                '# python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add',
                Exclusion.COMMENT_LINE,
                id='hash-comment-line',
            ),
            pytest.param(
                '// python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add',
                Exclusion.COMMENT_LINE,
                id='slash-comment-line',
            ),
            pytest.param(
                'See https://example.org — run plan-marshall:manage-files:manage-files add',
                Exclusion.URL_LINE,
                id='url-line',
            ),
            pytest.param('Use http:alpha:beta here.', Exclusion.URI_SCHEME, id='uri-scheme'),
            pytest.param(
                'Coordinate 1v:alpha:beta here.',
                Exclusion.VERSION_COORDINATE,
                id='digit-leading-bundle',
            ),
            pytest.param(
                'Endpoint hostname:8080:api here.',
                Exclusion.PORT_SEGMENT,
                id='all-digit-middle-segment',
            ),
        ],
    )
    def test_shape_is_recorded_not_discarded(self, line, expected):
        """The match survives detection carrying the shape it matched."""
        dep = _only(detect_script_notations(f'\n{line}\n', _SOURCE))
        assert dep.exclusion is expected

    def test_match_level_shape_wins_over_the_line_level_one(self):
        """A URI-scheme token on a comment line records the SCHEME, not the line.

        Match-level shapes are the more specific statement about the token, so
        they are tested first; the line-level shape is the fallback. Without this
        ordering every excluded token on a comment line would report the least
        informative of the reasons that apply to it.
        """
        dep = _only(detect_script_notations('\n# Use http:alpha:beta here.\n', _SOURCE))
        assert dep.exclusion is Exclusion.URI_SCHEME

    def test_only_the_decision_log_shape_can_still_name_a_verb(self):
        """The verb-bearing set is exactly the decision-log prefix.

        Membership decides whether an excluded row is offered to the subcommand
        retarget or sent straight to the index's drop path, so the set is pinned
        rather than left implicit in downstream outcomes.
        """
        assert VERB_BEARING_EXCLUSIONS == frozenset({Exclusion.DECISION_LOG})


class TestExcludedShapeStillReachesTheIndex:
    """The fail-open the routing closes: a real reference beside a URL."""

    def test_notation_on_a_url_line_resolves_to_a_real_component(self, tmp_path):
        """A genuine notation sharing a line with a URL is kept, not discarded.

        This is the whole point of recording the shape instead of skipping the
        line. Under the old ``continue`` the edge below did not exist as far as
        any report was concerned; the shape says only where to look, and the
        index decides on existence.
        """
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Docs at https://example.org — run '
                'demo-bundle:alpha:alpha add\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, {DependencyType.SCRIPT_NOTATION})

        targets = {
            dep.target.to_notation()
            for deps in index.forward_deps.values()
            for dep in deps
            if dep.resolved
        }
        assert 'demo-bundle:alpha:alpha' in targets

    def test_excluded_shape_naming_nothing_is_still_dropped(self, tmp_path):
        """Recording a shape widens what is EXAMINED, never what is reported.

        The complement of the test above, and the reason routing these shapes
        adds no findings by construction: an excluded shape that names no
        component and no verb is the one case the index discards.
        """
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Endpoint hostname:8080:api and coordinate 1v:beta:gamma.\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, {DependencyType.SCRIPT_NOTATION})

        recorded = {
            dep.target.to_notation()
            for deps in index.forward_deps.values()
            for dep in deps
        }
        assert 'hostname:8080:api' not in recorded
        assert '1v:beta:gamma' not in recorded


# =============================================================================
# (a) The unresolved-row partition
# =============================================================================


class TestUnresolvedReasonPartition:
    """``unresolved_reason`` assigns exactly one reason, by a pinned precedence."""

    @staticmethod
    def _dep(bundle: str, *, verb_unregistered: bool = False):
        return Dependency(
            source=_SOURCE,
            target=ComponentId(
                bundle=bundle, component_type='script', name='thing', parent_skill='sk'
            ),
            dep_type=DependencyType.SCRIPT_NOTATION,
            context='line:1',
            resolved=False,
            verb_unregistered=verb_unregistered,
        )

    def test_indexed_bundle_is_a_missing_component(self):
        """A target whose bundle IS indexed names a component that does not exist."""
        dep = self._dep('known-bundle')
        assert unresolved_reason(dep, {'known-bundle'}) == UNRESOLVED_REASON_MISSING_COMPONENT

    def test_unindexed_bundle_is_an_unknown_bundle(self):
        """A target in no indexed bundle is not yet triaged, not yet actionable."""
        dep = self._dep('never-heard-of-it')
        assert unresolved_reason(dep, {'known-bundle'}) == UNRESOLVED_REASON_UNKNOWN_BUNDLE

    def test_unregistered_verb_outranks_bundle_membership(self):
        """The verb refusal is tested FIRST, and the precedence is load-bearing.

        The component EXISTS on this row, so the bundle-membership test would
        label it ``missing-component`` and send a reader looking for a script
        that is right there.
        """
        dep = self._dep('known-bundle', verb_unregistered=True)
        assert unresolved_reason(dep, {'known-bundle'}) == UNRESOLVED_REASON_UNREGISTERED_VERB

    def test_every_producible_reason_is_published(self):
        """``UNRESOLVED_REASONS`` covers every value the classifier can return.

        Derived by running the classifier over the input states rather than by
        restating the literal, so a fourth reason added to the classifier without
        being published here fails rather than silently escaping the breakdown.
        """
        produced = {
            unresolved_reason(self._dep('known-bundle'), {'known-bundle'}),
            unresolved_reason(self._dep('other'), {'known-bundle'}),
            unresolved_reason(
                self._dep('known-bundle', verb_unregistered=True), {'known-bundle'}
            ),
        }
        assert produced <= set(UNRESOLVED_REASONS)
        assert set(UNRESOLVED_REASONS) == produced


class TestValidateEmitsTheFullReasonSet:
    """The breakdown is emitted over every reason, including the zero classes."""

    def test_zero_classes_are_present_as_zeros(self, tmp_path):
        """A class that scored zero is a zero, never an absent key.

        A breakdown assembled only from observed rows cannot tell "no row fell in
        this class" from "this class was not computed" — the zeros are what make
        the non-zero entries readable.
        """
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Skill: demo-bundle:no-such-skill\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, set(DependencyType))

        result = cmd_validate(index, dep_types=set(DependencyType))

        assert set(result['unresolved_by_reason']) == set(UNRESOLVED_REASONS)
        assert result['unresolved_by_reason'][UNRESOLVED_REASON_UNREGISTERED_VERB] == 0
        assert result['indexed_bundle_count'] == len(indexed_bundles(index))

    def test_the_breakdown_totals_the_unresolved_count(self, tmp_path):
        """Every unresolved row lands in exactly one class.

        The partition claim, asserted as a partition rather than as three
        independent counts: the buckets sum to the reported total.
        """
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Skill: demo-bundle:no-such-skill\n\n'
                'Skill: foreign-bundle:whatever\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, set(DependencyType))

        result = cmd_validate(index, dep_types=set(DependencyType))

        assert sum(result['unresolved_by_reason'].values()) == result['unresolved_count']
        assert result['unresolved_count'] > 0


# =============================================================================
# (d) The retarget's premise — verb registration
# =============================================================================


class _FakeSurface:
    """A stand-in for the ``--help``-derived argparse surface."""

    def __init__(self, verbs):
        self._verbs = frozenset(verbs)

    def known_subcommands(self):
        return self._verbs


@pytest.fixture
def registered_verbs(monkeypatch):
    """Substitute the out-of-process ``--help`` oracle with a known verb set.

    The ORACLE is replaced, not the logic under test: ``_verb_is_registered``,
    ``_entry_script_for_subcommand`` and ``_index_dependencies_from`` all run for
    real, so the refusal-before-drop ordering is genuinely exercised. Patching
    the surface derivation is what makes that possible without spawning a
    subprocess per probe.
    """

    def _install(verbs):
        monkeypatch.setattr(
            _dep_index_mod, 'resolve_executor', lambda _root: Path('/nonexistent/executor.py')
        )
        monkeypatch.setattr(
            _dep_index_mod, 'derive_surface', lambda _notation, _executor: _FakeSurface(verbs)
        )
        monkeypatch.setattr(_dep_index_mod, 'is_derivable', lambda _surface: True)

    return _install


class TestRetargetVerbValidation:
    """A verb-shaped notation retargets only onto a script that registers it."""

    def test_registered_verb_resolves_onto_the_entry_script(self, tmp_path, registered_verbs):
        """The retarget lands on the entry script that owns the verb."""
        registered_verbs({'compose'})
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Run demo-bundle:alpha:compose to build it.\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, {DependencyType.SCRIPT_NOTATION})

        rows = [dep for deps in index.forward_deps.values() for dep in deps]
        assert [(d.target.to_notation(), d.resolved) for d in rows] == [
            ('demo-bundle:alpha:alpha', True)
        ]

    def test_unregistered_verb_stays_unresolved_and_disclosed(self, tmp_path, registered_verbs):
        """A verb the script does not register is a broken reference, and is kept.

        The refusal is checked BEFORE the exclusion drop precisely so this row
        survives: it names a real entry script, so dropping it would delete the
        finding the check exists to surface.
        """
        registered_verbs({'compose'})
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Run demo-bundle:alpha:classify to sort it.\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, {DependencyType.SCRIPT_NOTATION})

        rows = [dep for deps in index.forward_deps.values() for dep in deps]
        assert len(rows) == 1
        assert rows[0].resolved is False
        assert rows[0].verb_unregistered is True
        assert (
            unresolved_reason(rows[0], indexed_bundles(index))
            == UNRESOLVED_REASON_UNREGISTERED_VERB
        )

    def test_a_non_derivable_surface_abstains(self, tmp_path, monkeypatch):
        """No derivable surface means no evidence, so no finding is manufactured.

        Absence of a surface is absence of EVIDENCE, not evidence of absence —
        reporting an unresolved row from a failed probe would name a broken
        reference that is not broken.
        """
        monkeypatch.setattr(
            _dep_index_mod, 'resolve_executor', lambda _root: Path('/nonexistent/executor.py')
        )
        monkeypatch.setattr(
            _dep_index_mod, 'derive_surface', lambda _notation, _executor: _FakeSurface(())
        )
        monkeypatch.setattr(_dep_index_mod, 'is_derivable', lambda _surface: False)
        bundles = _build_tree(
            tmp_path,
            skill_md=(
                '---\nname: alpha\ndescription: Alpha skill\n---\n'
                '# Alpha\n\n'
                'Run demo-bundle:alpha:classify to sort it.\n'
            ),
            script_source='def main() -> int:\n    return 0\n',
        )
        index = build_dependency_index(bundles, {DependencyType.SCRIPT_NOTATION})

        rows = [dep for deps in index.forward_deps.values() for dep in deps]
        assert [(d.target.to_notation(), d.resolved) for d in rows] == [
            ('demo-bundle:alpha:alpha', True)
        ]


# =============================================================================
# Synthetic tree
# =============================================================================


def _build_tree(root: Path, *, skill_md: str, script_source: str) -> Path:
    """Create a one-bundle ``marketplace/bundles`` tree and return the bundles dir.

    The bundle carries one skill ``alpha`` with a same-named entry script, which
    is the shape the subcommand retarget requires: a skill exposing ONE entry
    script named after itself and dispatching its verbs as subcommands.
    """
    bundles = root / 'marketplace' / 'bundles'
    bundle = bundles / 'demo-bundle'
    _write(bundle / '.claude-plugin' / 'plugin.json', '{\n  "name": "demo-bundle"\n}\n')
    _write(bundle / 'skills' / 'alpha' / 'SKILL.md', skill_md)
    _write(bundle / 'skills' / 'alpha' / 'scripts' / 'alpha.py', script_source)
    return bundles


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
