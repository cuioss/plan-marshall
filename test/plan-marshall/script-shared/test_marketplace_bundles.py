# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for marketplace_bundles shared module.

Both DEPLOYED shapes are exercised against real trees. The nested cases (the
marketplace source layout and the versioned plugin cache) are the historical
population and are unchanged; the flat cases at the end cover the shape the
OpenCode and Antigravity targets actually deploy, which no case here modelled
before ``deployed_layout`` existed — so ``collect_script_dirs`` returned an empty
list against a real deployment and every consumer of it inherited that.
"""

from pathlib import Path

import pytest
from deployed_layout import FLAT_DIR_SEPARATOR as _FLAT_DIR_SEPARATOR
from deployed_layout import SKILL_ROOT_NAMES, flat_skill_dir_name
from marketplace_bundles import (
    build_pythonpath,
    collect_script_dirs,
    extract_bundle_name,
    find_bundles,
    resolve_bundle_path,
    resolve_bundles_root,
    resolve_skills_root,
    select_live_version_dir,
)

SUBPATH = 'skills/skill-x/scripts/bar.py'

#: The bundle the flat fixtures publish under, matching the real deployment.
BUNDLE = 'plan-marshall'


def _make_flat_tree(root: Path, *, root_name: str = 'skills', skills: tuple[str, ...] = ('skill-x',)) -> Path:
    """Build a real flat deployed tree under ``root`` and return its skill root.

    ``root_name`` selects the skill-root spelling, so the same builder produces
    the deployed plural ``skills/`` and the generated singular ``skill/``. The
    script file is named after the module-level :data:`SUBPATH` requests
    (``bar.py``), so the fixtures carry the path the resolver is asked for rather
    than a convenient one of their own.
    """
    skills_root = root / root_name
    for skill in skills:
        scripts = skills_root / flat_skill_dir_name(BUNDLE, skill) / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'bar.py').write_text('# script')
    return skills_root


def _create_bundle(base: Path, name: str, version: str | None = None, orphaned: bool = False) -> Path:
    """Helper to create a bundle directory with plugin.json.

    When ``orphaned`` is set, a ``.orphaned_at`` marker file is placed in the
    bundle directory — the selector ignores it, so these fixtures prove the
    marker no longer changes which version dir is chosen.
    """
    if version:
        bundle_dir = base / name / version
    else:
        bundle_dir = base / name
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text('{}')
    if orphaned:
        (bundle_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z')
    return bundle_dir


def _create_full_version_dir(base: Path, name: str, version: str, orphaned: bool = False) -> Path:
    """Create a version dir eligible for ALL THREE legs of the resolver family.

    Carries a ``.claude-plugin/plugin.json`` (``find_bundles``), the shared
    ``SUBPATH`` script (``resolve_bundle_path``) and a ``skills/`` tree
    (``collect_script_dirs``), so one fixture can prove the three legs agree.
    """
    version_dir = _create_bundle(base, name, version, orphaned=orphaned)
    script = version_dir / SUBPATH
    script.parent.mkdir(parents=True)
    script.write_text('# script')
    return version_dir


def _bare_version_dir(base: Path, name: str, version: str) -> Path:
    """Create a version dir that satisfies NO leg's eligibility predicate.

    Used to make the newest-on-disk dir ineligible, so selection must fall
    through to the newest ELIGIBLE (lower-versioned) dir — the shape that proves
    eligibility, not the marker, drives the choice.
    """
    version_dir = base / name / version
    version_dir.mkdir(parents=True)
    return version_dir


class TestFindBundles:
    def test_finds_marketplace_bundles(self, tmp_path):
        _create_bundle(tmp_path, 'bundle-a')
        _create_bundle(tmp_path, 'bundle-b')
        result = find_bundles(tmp_path)
        names = [b.name for b in result]
        assert 'bundle-a' in names
        assert 'bundle-b' in names

    def test_finds_versioned_bundles(self, tmp_path):
        _create_bundle(tmp_path, 'bundle-a', '0.1-BETA')
        result = find_bundles(tmp_path)
        assert len(result) == 1
        assert result[0].name == '0.1-BETA'

    def test_empty_directory(self, tmp_path):
        assert find_bundles(tmp_path) == []

    def test_multi_version_selects_newest(self, tmp_path):
        # Two cache version dirs for the same bundle: find_bundles returns only the
        # NEWEST ('1.0.10' -> (1, 0, 10)), not the lexically-first ('1.0.0'), so a
        # stale dir cannot shadow the current one in the last-write-wins merge.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        new = _create_bundle(tmp_path, 'bundle-a', '1.0.10')
        assert find_bundles(tmp_path) == [new]

    def test_mark_on_the_newest_dir_is_ignored(self, tmp_path, capsys):
        # The .orphaned_at marker is never consulted: the newest eligible dir is
        # selected whether or not it carries a mark, and no stderr is emitted.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        assert find_bundles(tmp_path) == [newest]
        assert capsys.readouterr().err == '', 'marker-free selection must emit no stderr'

    def test_all_marked_still_selects_newest_eligible_without_warning(self, tmp_path, capsys):
        # Every eligible dir marked (the observed saturated state) resolves to the
        # newest eligible dir with NO degraded/saturation stderr — the marker is
        # simply ignored, so there is no saturation state to warn about. The bare
        # 1.0.20 dir makes the newest-on-disk ineligible, the only shape in which
        # the retired degraded fallback used to fire.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        newest_eligible = _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.20')

        assert find_bundles(tmp_path) == [newest_eligible]
        assert capsys.readouterr().err == '', 'marker-free selection must never emit a degraded warning'

    def test_highest_version_wins_emits_no_stderr(self, tmp_path, capsys):
        # Highest-version-wins resolution: an unmarked newest dir is selected and
        # nothing is emitted to stderr.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_bundle(tmp_path, 'bundle-a', '1.0.10')

        assert find_bundles(tmp_path) == [newest]
        assert capsys.readouterr().err == '', 'a resolvable dir must not emit any stderr'

    def test_non_versioned_bundle_starting_with_digits(self, tmp_path):
        # A non-versioned bundle whose name starts with digits (e.g. '1.0-my-bundle')
        # must be treated as a singleton, not grouped by its parent (base_path) and
        # discarded in favor of a sibling that also matches the version-dir pattern.
        b1 = _create_bundle(tmp_path, '1.0-bundle-a')
        b2 = _create_bundle(tmp_path, '2.0-bundle-b')
        assert sorted(find_bundles(tmp_path)) == sorted([b1, b2])


class TestSelectLiveVersionDir:
    """Direct coverage of the one function that decides version-dir ordering."""

    @staticmethod
    def _eligible(version_dir: Path) -> bool:
        return (version_dir / '.claude-plugin' / 'plugin.json').is_file()

    def test_none_marked_selects_newest(self, tmp_path):
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_bundle(tmp_path, 'bundle-a', '1.0.10')

        assert select_live_version_dir(tmp_path / 'bundle-a', self._eligible) == newest

    def test_all_marked_selects_newest_eligible_without_warning(self, tmp_path, capsys):
        # The marker is ignored: every eligible dir marked still resolves to the
        # newest eligible one, with no degraded/saturation stderr. The bare 1.0.20
        # makes the newest-on-disk ineligible — the only shape the retired
        # degraded fallback used to fire in.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        newest_eligible = _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.20')

        assert select_live_version_dir(tmp_path / 'bundle-a', self._eligible) == newest_eligible
        assert capsys.readouterr().err == ''

    def test_mark_on_the_newest_dir_is_ignored(self, tmp_path, capsys):
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        assert select_live_version_dir(tmp_path / 'bundle-a', self._eligible) == newest
        assert capsys.readouterr().err == ''

    def test_no_eligible_candidate_returns_none(self, tmp_path):
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.0')

        assert select_live_version_dir(tmp_path / 'bundle-a', self._eligible) is None

    def test_unreadable_bundle_dir_returns_none(self, tmp_path):
        assert select_live_version_dir(tmp_path / 'does-not-exist', self._eligible) is None


#: ``(fully-eligible version dirs as ``(version, marked)``, version dirs that
#: satisfy NO leg's eligibility predicate)``. Every row must resolve to
#: ``1.0.10`` on all three legs. The marked rows show the ``.orphaned_at`` marker
#: is ignored wherever it sits; the bare-dir row makes the newest-on-disk
#: INELIGIBLE, so selection falls through to the newest eligible one — the shape
#: that shows eligibility, not the marker, drives the choice.
_LEG_AGREEMENT_CASES = [
    ([('1.0.0', False), ('1.0.10', False)], []),
    ([('1.0.0', False), ('1.0.10', True)], []),
    ([('1.0.0', True), ('1.0.10', True)], []),
    ([('1.0.0', False), ('1.0.10', True)], ['1.0.20']),
]

_LEG_AGREEMENT_IDS = [
    'nothing-marked',
    'the-newest-dir-is-marked',
    'every-dir-is-marked',
    'the-newest-dir-on-disk-is-ineligible',
]


class TestLegAgreement:
    """All three legs must resolve to the SAME version dir.

    A single selector (newest-eligible wins) makes find_bundles,
    resolve_bundle_path and collect_script_dirs agree by construction; these
    cases pin that agreement, including when a foreign ``.orphaned_at`` mark is
    present — it is ignored identically by every leg.
    """

    @staticmethod
    def _versions(tmp_path: Path) -> tuple[str, str, str]:
        found = find_bundles(tmp_path)
        assert len(found) == 1
        resolved = resolve_bundle_path(tmp_path, 'bundle-a', SUBPATH)
        script_dirs = [d for d in collect_script_dirs(tmp_path) if d.endswith('scripts')]
        assert len(script_dirs) == 1
        # resolved:   .../bundle-a/{version}/skills/skill-x/scripts/bar.py
        # script dir: .../bundle-a/{version}/skills/skill-x/scripts
        return found[0].name, resolved.parts[-5], Path(script_dirs[0]).parts[-4]

    @pytest.mark.parametrize('full_dirs,bare_dirs', _LEG_AGREEMENT_CASES, ids=_LEG_AGREEMENT_IDS)
    def test_every_leg_selects_the_same_version_dir(self, tmp_path, full_dirs, bare_dirs):
        for version, orphaned in full_dirs:
            _create_full_version_dir(tmp_path, 'bundle-a', version, orphaned=orphaned)
        for version in bare_dirs:
            _bare_version_dir(tmp_path, 'bundle-a', version)

        assert self._versions(tmp_path) == ('1.0.10', '1.0.10', '1.0.10')


#: ``(directory parts under tmp_path, the bundle name extracted from it)``. The
#: two-part rows are the cache layout, where the leaf is a VERSION and the bundle
#: name is its parent.
_BUNDLE_NAME_CASES = [
    (('plan-marshall',), 'plan-marshall'),
    (('plan-marshall', '0.1-BETA'), 'plan-marshall'),
    (('my-bundle', '2.0.0-rc1'), 'my-bundle'),
]

_BUNDLE_NAME_IDS = [
    'marketplace-source-layout',
    'versioned-cache-layout',
    'a-numeric-version-with-a-suffix',
]


class TestExtractBundleName:
    @pytest.mark.parametrize('parts,expected', _BUNDLE_NAME_CASES, ids=_BUNDLE_NAME_IDS)
    def test_extract_bundle_name(self, tmp_path, parts: tuple[str, ...], expected: str):
        directory = tmp_path.joinpath(*parts)
        directory.mkdir(parents=True)

        assert extract_bundle_name(directory) == expected


class TestResolveBundlePath:
    def test_marketplace_structure(self, tmp_path):
        target = tmp_path / 'plan-marshall' / 'skills' / 'foo' / 'bar.py'
        target.parent.mkdir(parents=True)
        target.write_text('content')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == target

    def test_versioned_structure(self, tmp_path):
        target = tmp_path / 'plan-marshall' / '0.1-BETA' / 'skills' / 'foo' / 'bar.py'
        target.parent.mkdir(parents=True)
        target.write_text('content')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == target

    def test_nonexistent_returns_fallback_path(self, tmp_path):
        result = resolve_bundle_path(tmp_path, 'missing', 'some/path')
        assert result == tmp_path / 'missing' / 'some' / 'path'

    def test_multi_version_selects_newest(self, tmp_path):
        # Two cache version dirs carry the same subpath: the resolver must return
        # the NEWEST ('1.0.10' -> (1, 0, 10)), not the lexically-first ('1.0.0').
        old = tmp_path / 'plan-marshall' / '1.0.0' / 'skills' / 'foo' / 'bar.py'
        new = tmp_path / 'plan-marshall' / '1.0.10' / 'skills' / 'foo' / 'bar.py'
        old.parent.mkdir(parents=True)
        new.parent.mkdir(parents=True)
        old.write_text('old')
        new.write_text('new')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == new

    def test_mark_on_the_newest_dir_carrying_the_subpath_is_ignored(self, tmp_path):
        # The newest dir carrying the subpath is selected regardless of a mark.
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        assert resolve_bundle_path(tmp_path, 'bundle-a', SUBPATH) == newest / SUBPATH

    def test_all_eligible_marked_resolves_to_newest_carrying_the_subpath(self, tmp_path, capsys):
        # Marker ignored: even with every eligible dir marked, the newest dir
        # carrying the subpath resolves, with no degraded stderr.
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        newest_eligible = _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.20')

        assert resolve_bundle_path(tmp_path, 'bundle-a', SUBPATH) == newest_eligible / SUBPATH
        assert capsys.readouterr().err == ''


#: ``(older version dir, newer version dir, the scripts subpath created in
#: each)``. Only the newest version dir may be scanned, or an older copy pollutes
#: PYTHONPATH and shadows the current one. The beta row pins the ORDERING rule
#: (a numbered build ``0.1.5`` → ``(0, 1, 5)`` sorts newer than a bare
#: ``0.1-BETA`` → ``(0, 1)``); the ``build`` row pins that the same selection
#: governs the scripts/ subdir expansion, not only the scripts dir itself.
_NEWEST_ONLY_SCAN_CASES = [
    ('0.1.100', '0.1.200', 'skills/skill-x/scripts'),
    ('0.1-BETA', '0.1.5', 'skills/skill-x/scripts'),
    ('0.1.100', '0.1.200', 'skills/skill-x/scripts/build'),
]

_NEWEST_ONLY_SCAN_IDS = [
    'two-numbered-versions',
    'a-numbered-build-beats-a-bare-beta',
    'the-scripts-subdir-expansion',
]


class TestCollectScriptDirs:
    def test_marketplace_structure(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result

    def test_includes_subdirs(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        subdir = scripts / 'build'
        subdir.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result
        assert str(subdir) in result

    def test_excludes_pycache(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        pycache = scripts / '__pycache__'
        pycache.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(pycache) not in result

    def test_versioned_structure(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / '1.0' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        # Need a skills dir for version detection
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result

    @pytest.mark.parametrize('older,newer,subpath', _NEWEST_ONLY_SCAN_CASES, ids=_NEWEST_ONLY_SCAN_IDS)
    def test_only_the_newest_version_dir_is_scanned(self, tmp_path, older: str, newer: str, subpath: str):
        older_dir = tmp_path / 'bundle-a' / older / subpath
        newer_dir = tmp_path / 'bundle-a' / newer / subpath
        older_dir.mkdir(parents=True)
        newer_dir.mkdir(parents=True)

        result = collect_script_dirs(tmp_path)

        assert str(newer_dir) in result
        assert str(older_dir) not in result

    def test_mark_on_the_newest_dir_with_a_skills_tree_is_ignored(self, tmp_path):
        # The newest dir carrying a skills/ tree is scanned regardless of a mark.
        old = _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0')
        newest = _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        result = collect_script_dirs(tmp_path)
        assert str(newest / 'skills' / 'skill-x' / 'scripts') in result
        assert str(old / 'skills' / 'skill-x' / 'scripts') not in result

    def test_all_eligible_marked_scans_newest_with_a_skills_tree(self, tmp_path, capsys):
        # Marker ignored: even with every eligible dir marked, only the newest
        # dir with a skills/ tree is scanned, with no degraded stderr.
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        newest_eligible = _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.20')

        result = collect_script_dirs(tmp_path)
        assert str(newest_eligible / 'skills' / 'skill-x' / 'scripts') in result
        assert capsys.readouterr().err == ''


class TestResolveBundlesRoot:
    def test_source_layout(self, tmp_path):
        # tmp_path/marketplace/bundles/plan-marshall/.claude-plugin/plugin.json
        bundles = tmp_path / 'marketplace' / 'bundles'
        plan_marshall = bundles / 'plan-marshall'
        (plan_marshall / '.claude-plugin').mkdir(parents=True)
        (plan_marshall / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = plan_marshall / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_bundles_root(script) == bundles

    def test_cache_layout(self, tmp_path):
        # tmp_path/cache/plan-marshall/0.1-BETA/.claude-plugin/plugin.json
        cache = tmp_path / 'cache'
        version_dir = cache / 'plan-marshall' / '0.1-BETA'
        (version_dir / '.claude-plugin').mkdir(parents=True)
        (version_dir / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = version_dir / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_bundles_root(script) == cache

    def test_raises_outside_bundle(self, tmp_path):
        script = tmp_path / 'a' / 'b' / 'c.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_bundles_root'):
            resolve_bundles_root(script)


class TestResolveSkillsRoot:
    def test_happy_path(self, tmp_path):
        bundle = tmp_path / 'marketplace' / 'bundles' / 'plan-marshall'
        (bundle / '.claude-plugin').mkdir(parents=True)
        (bundle / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = bundle / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_skills_root(script) == bundle / 'skills'

    def test_cache_layout(self, tmp_path):
        version_dir = tmp_path / 'cache' / 'plan-marshall' / '0.1-BETA'
        (version_dir / '.claude-plugin').mkdir(parents=True)
        (version_dir / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = version_dir / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_skills_root(script) == version_dir / 'skills'

    def test_raises_outside_skill(self, tmp_path):
        # 'skills' dir exists but no sibling .claude-plugin/plugin.json
        skills = tmp_path / 'random' / 'skills'
        script = skills / 'foo' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_skills_root'):
            resolve_skills_root(script)

    def test_raises_when_no_skills_ancestor(self, tmp_path):
        script = tmp_path / 'a' / 'b' / 'c.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_skills_root'):
            resolve_skills_root(script)


class TestBuildPythonpath:
    def test_returns_joined_dirs(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        result = build_pythonpath(tmp_path)
        assert str(scripts) in result


class TestFlatDeployedShape:
    """The shape the OpenCode and Antigravity targets actually deploy.

    Every case builds a real flat tree. The nested population above cannot reach
    these: ``collect_script_dirs``' nested loop iterates a root's bundle
    directories, and a flat root has none — its children are the ``skills/``
    directory — so it contributed nothing while reporting success, and
    ``resolve_bundle_path``'s nested leg constructed a path under a ``{bundle}/``
    directory that does not exist on such a root.
    """

    def test_resolve_bundle_path_reads_the_deployed_plural_root(self, tmp_path):
        """A flat root resolves the nested-layout subpath against its own spelling."""
        skills_root = _make_flat_tree(tmp_path)

        result = resolve_bundle_path(tmp_path, BUNDLE, SUBPATH)

        assert result == skills_root / f'{BUNDLE}-skill-x' / 'scripts' / 'bar.py'
        assert result.is_file(), 'the resolved path must be one that exists, not one that was constructed'

    def test_resolve_bundle_path_reads_the_singular_generated_root(self, tmp_path):
        """The generated singular tree resolves through the same call.

        The emitter writes ``skill/`` and ``install.sh`` maps it to ``skills/``,
        so both spellings are trees a reader meets in the field.
        """
        skills_root = _make_flat_tree(tmp_path, root_name='skill')

        assert (
            resolve_bundle_path(tmp_path, BUNDLE, SUBPATH) == skills_root / f'{BUNDLE}-skill-x' / 'scripts' / 'bar.py'
        )

    def test_resolve_bundle_path_prefers_the_deployed_plural_over_singular(self, tmp_path):
        """With both spellings present, the deployed one is the one that resolves.

        Each spelling carries a DIFFERENT file, so a reader that probed singular
        first would answer with the other root's path.
        """
        plural = _make_flat_tree(tmp_path, root_name='skills')
        singular = _make_flat_tree(tmp_path, root_name='skill')

        assert resolve_bundle_path(tmp_path, BUNDLE, SUBPATH) == plural / f'{BUNDLE}-skill-x' / 'scripts' / 'bar.py'
        assert plural != singular

    def test_resolve_bundle_path_returns_the_constructed_path_when_a_flat_root_misses(self, tmp_path):
        """A miss on a flat root still returns a deterministic path, never ``None``.

        The never-``None`` contract belongs to this function — its callers want a
        reportable path, not a probe outcome — so the flat leg is consulted only
        for an EXISTING candidate and a miss falls back to the nested
        construction. A resolver returning ``None`` here would break every caller
        that formats the result into a diagnostic.
        """
        _make_flat_tree(tmp_path, skills=('skill-x',))

        result = resolve_bundle_path(tmp_path, BUNDLE, 'skills/absent-skill/scripts/x.py')

        assert result == tmp_path / BUNDLE / 'skills' / 'absent-skill' / 'scripts' / 'x.py'

    def test_resolve_bundle_path_does_not_touch_a_nested_root_with_the_flat_leg(self, tmp_path):
        """A nested root is answered by the nested leg, unchanged.

        The flat leg is a FALLBACK, so a nested root that ALSO carries a
        ``skills/`` directory at its own top level — a bundles root with a
        ``skills/`` sibling, which is what makes it a flat root by the shared
        resolver's own predicate — must still resolve through its own bundle
        subtree rather than being answered by the flat sibling.
        """
        nested_target = tmp_path / BUNDLE / SUBPATH
        nested_target.parent.mkdir(parents=True)
        nested_target.write_text('nested')
        _make_flat_tree(tmp_path, skills=(f'{BUNDLE}-{SUBPATH.split("/")[0]}',))

        assert resolve_bundle_path(tmp_path, BUNDLE, SUBPATH) == nested_target

    def test_collect_script_dirs_is_non_empty_on_a_flat_root(self, tmp_path):
        """The headline property: script-dir collection is non-empty on a deployment.

        This is the one assertion a flat root had no answer to: every consumer of
        the collected list — the executor's ``build_pythonpath``, its shared-module
        set and its generated ``EXTRA_SCRIPT_DIRS`` — inherits an empty list while
        generation still reports success.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('skill-x', 'skill-y'))

        result = collect_script_dirs(tmp_path)

        assert str(skills_root / f'{BUNDLE}-skill-x' / 'scripts') in result
        assert str(skills_root / f'{BUNDLE}-skill-y' / 'scripts') in result
        assert result, 'script-dir collection must not be empty against a flat deployment'

    def test_collect_script_dirs_reads_the_singular_root_too(self, tmp_path):
        """The singular generated tree enumerates identically."""
        skills_root = _make_flat_tree(tmp_path, root_name='skill', skills=('skill-x',))

        assert str(skills_root / f'{BUNDLE}-skill-x' / 'scripts') in collect_script_dirs(tmp_path)

    def test_collect_script_dirs_includes_flat_skill_subdirs(self, tmp_path):
        """A flat skill's ``scripts/`` sub-directories are collected, as nested ones are.

        ``script-shared/scripts/build/`` is an organised layout that exists in the
        real tree, and the extra entries are what let a subprocess import from it.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('script-shared',))
        subdir = skills_root / f'{BUNDLE}-script-shared' / 'scripts' / 'build'
        subdir.mkdir()

        result = collect_script_dirs(tmp_path)

        assert str(subdir) in result

    def test_collect_script_dirs_counts_each_directory_once_across_both_spellings(self, tmp_path):
        """The skill-root directories are not re-walked by the nested loop.

        A flat root's children include ``skills/``, and the nested loop would
        otherwise descend into it a second time — under a different owner — and
        double every entry on the PYTHONPATH the executor hands its subprocesses.
        """
        _make_flat_tree(tmp_path, skills=('skill-x',))

        result = collect_script_dirs(tmp_path)

        assert len(result) == len(set(result)), f'a directory was collected twice: {result}'

    def test_collect_script_dirs_reads_a_root_carrying_both_shapes(self, tmp_path):
        """A root with a nested bundle AND a flat skill root yields both.

        The two shapes are complementary, not exclusive, and a consumer that can
        only read one loses whichever it cannot see.
        """
        nested_scripts = tmp_path / 'bundle-a' / 'skills' / 'nested-skill' / 'scripts'
        nested_scripts.mkdir(parents=True)
        flat_scripts = _make_flat_tree(tmp_path, skills=('flat-skill',)) / f'{BUNDLE}-flat-skill' / 'scripts'

        result = collect_script_dirs(tmp_path)

        assert str(nested_scripts) in result
        assert str(flat_scripts) in result

    def test_collect_script_dirs_excludes_pycache_on_a_flat_root(self, tmp_path):
        """The build-artefact exclusion holds for the flat shape too.

        A real deployed root carries ``__pycache__`` directories next to live
        scripts, and adding one to PYTHONPATH shadows the live module with a
        stale compiled copy.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('skill-x',))
        pycache = skills_root / f'{BUNDLE}-skill-x' / 'scripts' / '__pycache__'
        pycache.mkdir()

        assert str(pycache) not in collect_script_dirs(tmp_path)

    def test_build_pythonpath_carries_flat_script_dirs(self, tmp_path):
        """PYTHONPATH is populated from a flat root, which is what makes the tree usable.

        The join is the last step before a subprocess can import anything at all,
        so a non-empty ``collect_script_dirs`` that never reaches this output
        would leave the defect in place for the one consumer that matters most.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('skill-x',))
        scripts = str(skills_root / f'{BUNDLE}-skill-x' / 'scripts')

        joined = build_pythonpath(tmp_path).split(':')

        assert scripts in joined

    def test_the_nested_population_is_unchanged(self, tmp_path):
        """A nested root answers exactly as it did before the flat leg existed.

        The flat leg is a fallback, and this is the assertion that keeps it one:
        a root that resolves through the nested path must not be diverted by a
        sibling skill root.
        """
        nested_target = tmp_path / 'bundle-a' / SUBPATH
        nested_target.parent.mkdir(parents=True)
        nested_target.write_text('# nested')
        # A sibling skill root whose dash-joined name would satisfy the flat leg
        # for a DIFFERENT bundle, so a reader that probed flat first would answer
        # with this root's other directory.
        _make_flat_tree(tmp_path, skills=('skill-x',))

        assert collect_script_dirs(tmp_path)
        assert str(nested_target.parent) in collect_script_dirs(tmp_path)
        assert resolve_bundle_path(tmp_path, 'bundle-a', SUBPATH) == nested_target

    def test_the_declared_vocabulary_is_what_both_shapes_are_read_through(self):
        """The fixtures build from the shared vocabulary, so a renamed spelling fails here.

        ``SKILL_ROOT_NAMES`` and ``flat_skill_dir_name`` are read rather than
        restated: if either moves, every fixture above follows it, and a resolver
        still hardcoding the old spelling fails the case that exercises it rather
        than passing on a fixture that agrees with it by construction.
        """
        assert SKILL_ROOT_NAMES == ('skills', 'skill')
        assert flat_skill_dir_name('b', 's') == 'b' + _FLAT_DIR_SEPARATOR + 's'
