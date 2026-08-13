# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for marketplace_bundles shared module."""

from pathlib import Path

import pytest
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

    def test_none_marked(self, tmp_path):
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0')
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10')

        assert self._versions(tmp_path) == ('1.0.10', '1.0.10', '1.0.10')

    def test_newest_marked(self, tmp_path):
        # The mark on the newest dir is ignored, so every leg keeps it.
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0')
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        assert self._versions(tmp_path) == ('1.0.10', '1.0.10', '1.0.10')

    def test_all_marked(self, tmp_path):
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)

        assert self._versions(tmp_path) == ('1.0.10', '1.0.10', '1.0.10')

    def test_ineligible_newest_falls_through_to_newest_eligible(self, tmp_path):
        # The newest-on-disk 1.0.20 satisfies no leg's eligibility predicate, so
        # every leg selects the newest ELIGIBLE dir — 1.0.10 — and its
        # .orphaned_at mark is ignored (eligibility, not the marker, drives the
        # choice).
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.0')
        _create_full_version_dir(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        _bare_version_dir(tmp_path, 'bundle-a', '1.0.20')

        assert self._versions(tmp_path) == ('1.0.10', '1.0.10', '1.0.10')


class TestExtractBundleName:
    def test_marketplace_structure(self, tmp_path):
        bundle = tmp_path / 'plan-marshall'
        bundle.mkdir()
        assert extract_bundle_name(bundle) == 'plan-marshall'

    def test_versioned_cache_structure(self, tmp_path):
        version_dir = tmp_path / 'plan-marshall' / '0.1-BETA'
        version_dir.mkdir(parents=True)
        assert extract_bundle_name(version_dir) == 'plan-marshall'

    def test_numeric_version_pattern(self, tmp_path):
        version_dir = tmp_path / 'my-bundle' / '2.0.0-rc1'
        version_dir.mkdir(parents=True)
        assert extract_bundle_name(version_dir) == 'my-bundle'


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

    def test_multi_version_selects_newest_only(self, tmp_path):
        # Two version dirs for the same bundle: only the newest must be scanned,
        # so an older version cannot pollute PYTHONPATH and shadow the newest.
        old_scripts = tmp_path / 'bundle-a' / '0.1.100' / 'skills' / 'skill-x' / 'scripts'
        new_scripts = tmp_path / 'bundle-a' / '0.1.200' / 'skills' / 'skill-x' / 'scripts'
        old_scripts.mkdir(parents=True)
        new_scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(new_scripts) in result
        assert str(old_scripts) not in result

    def test_multi_version_numbered_beats_beta(self, tmp_path):
        # A numbered build (0.1.5 -> (0, 1, 5)) sorts newer than a bare beta
        # (0.1-BETA -> (0, 1)); the numbered version dir wins.
        beta_scripts = tmp_path / 'bundle-a' / '0.1-BETA' / 'skills' / 'skill-x' / 'scripts'
        numbered_scripts = tmp_path / 'bundle-a' / '0.1.5' / 'skills' / 'skill-x' / 'scripts'
        beta_scripts.mkdir(parents=True)
        numbered_scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(numbered_scripts) in result
        assert str(beta_scripts) not in result

    def test_multi_version_subdirs_from_newest_only(self, tmp_path):
        # The newest-only selection also governs the scripts/ subdir expansion:
        # an older version's scripts subdir must not appear in the result.
        old_sub = tmp_path / 'bundle-a' / '0.1.100' / 'skills' / 'skill-x' / 'scripts' / 'build'
        new_sub = tmp_path / 'bundle-a' / '0.1.200' / 'skills' / 'skill-x' / 'scripts' / 'build'
        old_sub.mkdir(parents=True)
        new_sub.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(new_sub) in result
        assert str(old_sub) not in result

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
