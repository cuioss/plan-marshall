# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``target_context`` — the single target/context resolver.

The contract under test is the one the rest of the tree now depends on:

* every cascade tier resolves, and the tier that produced the answer is
  REPORTED rather than assumed (ADR-015);
* the four distinct fall-through conditions — no local config, one that
  cannot be read, one that is malformed, one carrying no target / harness —
  stay distinguishable instead of collapsing into a single ``'claude'``;
* an explicit target outranks the cascade and says so;
* a caller-supplied ``marketplace_root`` is validated AT THE RESOLVER rather
  than at each entry point (ADR-016), and a ``..`` traversal is refused.

The tiers are pinned INDEPENDENTLY of one another. A suite that only asserted
the final string would pass on a reader that hardcoded ``'claude'`` and had no
env leg at all — which is exactly the defect this resolver replaced.
"""

import json
import os
from pathlib import Path

import pytest
import target_context
from target_context import (
    REASON_LOCAL_CONFIG_ABSENT,
    REASON_LOCAL_CONFIG_MALFORMED,
    REASON_LOCAL_CONFIG_UNREADABLE,
    REASON_TARGET_ABSENT,
    SOURCE_ENV,
    SOURCE_EXPLICIT,
    SOURCE_FALLBACK,
    SOURCE_LOCAL_CONFIG,
    default_target,
    detect_target_from_env,
    find_local_config,
    resolve_context,
    resolve_marketplace_root,
    resolve_target,
)

from conftest import PROJECT_ROOT

#: Every env signal the cascade reads. Each is cleared before a test so a signal
#: the DEVELOPER's shell happens to carry (this suite is routinely run on a
#: Claude machine AND on an OpenCode one) cannot decide the outcome.
PLATFORM_ENV_SIGNALS = ('ANTIGRAVITY_AGENT', 'OPENCODE', 'OPENCODE_PID', 'CLAUDE_CODE_SESSION_ID')


@pytest.fixture(autouse=True)
def no_platform_signal(monkeypatch):
    """Clear every platform env signal so the cascade tier under test is the only input."""
    for name in PLATFORM_ENV_SIGNALS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv(target_context.MARKETPLACE_ROOT_ENV, raising=False)


def _write_local_harness_config(root: Path, harness: str, body: str | None = None) -> Path:
    """Write machine-local harness config to ``<root>/.plan/local/harness/{harness}.json``."""
    harness_dir = root / '.plan' / 'local' / 'harness'
    harness_dir.mkdir(parents=True, exist_ok=True)
    cfg = harness_dir / f'{harness}.json'
    if body is None:
        body = json.dumps({'schema_version': 1, 'harness': harness})
    cfg.write_text(body, encoding='utf-8')
    return cfg


def _write_run_config(root: Path, body: str) -> Path:
    """Write machine-local run configuration to ``<root>/.plan/run-configuration.json``."""
    plan_dir = root / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    cfg = plan_dir / 'run-configuration.json'
    cfg.write_text(body, encoding='utf-8')
    return cfg


@pytest.fixture()
def project(outside_repo_dir):
    """A project root OUTSIDE the repo, with no machine-local config above it.

    ``tmp_path`` cannot serve here: pytest's basetemp is repo-local
    (``.plan/temp/pytest-*``), so the upward walk from a ``tmp_path`` fixture
    finds the REPOSITORY's real machine-local config and every "no config"
    case would silently measure the developer's checkout instead of the absence
    the test is about. A directory outside the repo is the only place the
    absent-config condition is genuinely absent.
    """
    root = outside_repo_dir / 'project'
    root.mkdir()
    return root


class TestCascadeTiers:
    """Each tier resolves, and reports itself."""

    def test_env_tier_resolves_each_platform_signal(self, monkeypatch):
        """Every platform env signal names its target through the ``env`` tier."""
        expected = {
            'ANTIGRAVITY_AGENT': 'antigravity',
            'OPENCODE': 'opencode',
            'OPENCODE_PID': 'opencode',
            'CLAUDE_CODE_SESSION_ID': 'claude',
        }
        for signal, target in expected.items():
            monkeypatch.setenv(signal, '1')
            resolved = resolve_target()
            assert resolved['target'] == target, f'{signal} must resolve to {target}'
            assert resolved['target_source'] == SOURCE_ENV, f'{signal} must be reported as the env tier'
            assert resolved['reason'] == '', 'a tier that found a target has nothing to explain'
            monkeypatch.delenv(signal)

    def test_local_config_tier_resolves_a_declared_harness(self, tmp_path):
        """Harness state in .plan/local/harness/{harness}.json names the target."""
        _write_local_harness_config(tmp_path, 'antigravity')

        resolved = resolve_target(cwd=tmp_path)

        assert resolved['target'] == 'antigravity'
        assert resolved['target_source'] == SOURCE_LOCAL_CONFIG
        assert resolved['reason'] == ''

    def test_local_config_tier_resolves_a_declared_run_config_target(self, tmp_path):
        """``target`` in run-configuration.json names the target."""
        _write_run_config(tmp_path, json.dumps({'target': 'opencode'}))

        resolved = resolve_target(cwd=tmp_path)

        assert resolved['target'] == 'opencode'
        assert resolved['target_source'] == SOURCE_LOCAL_CONFIG
        assert resolved['reason'] == ''

    def test_local_config_tier_walks_up_from_a_subdirectory(self, tmp_path):
        """The walk starts at ``cwd`` and climbs, so a nested cwd still finds the file."""
        _write_local_harness_config(tmp_path, 'opencode')
        nested = tmp_path / 'a' / 'b' / 'c'
        nested.mkdir(parents=True)

        resolved = resolve_target(cwd=nested)

        assert resolved['target'] == 'opencode'
        assert resolved['target_source'] == SOURCE_LOCAL_CONFIG

    def test_env_tier_outranks_a_declared_local_config_target(self, tmp_path, monkeypatch):
        """The cascade is ordered: an env signal wins over machine-local config."""
        _write_local_harness_config(tmp_path, 'claude')
        monkeypatch.setenv('OPENCODE', '1')

        resolved = resolve_target(cwd=tmp_path)

        assert resolved['target'] == 'opencode'
        assert resolved['target_source'] == SOURCE_ENV

    def test_fallback_tier_is_reported_not_assumed(self, project):
        """With no env signal and no usable config, the fallback says it IS a fallback.

        The value and the source are asserted as a PAIR because they carry
        different information: ``'claude'`` alone is indistinguishable from a
        genuine ``env``-tier resolution of claude, which is the whole reason the
        tier rides the result.
        """
        resolved = resolve_target(cwd=project)

        assert resolved['target'] == default_target()
        assert resolved['target_source'] == SOURCE_FALLBACK
        assert resolved['reason'] == REASON_LOCAL_CONFIG_ABSENT


class TestFallbackReasonsAreDistinguishable:
    """The four fall-through conditions must not collapse into one answer."""

    def test_absent_malformed_and_target_absent_are_distinct_outcomes(self, project):
        """Each unusable-config condition carries its OWN reason.

        A reader that collapsed them would answer ``fallback`` for all three with
        one shared reason, and this test fails on the FIRST of the three that
        disagrees with it. The pairwise check at the end is what makes the
        discrimination mechanical rather than a matter of reading three literals
        side by side.
        """
        plan_dir = project / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)

        # 1. Absent — nothing at the path at all.
        absent = resolve_target(cwd=project)
        assert absent['target_source'] == SOURCE_FALLBACK
        assert absent['reason'] == REASON_LOCAL_CONFIG_ABSENT

        # 2. Malformed — readable, but not a JSON object.
        _write_run_config(project, 'not json {{{')
        malformed = resolve_target(cwd=project)
        assert malformed['target_source'] == SOURCE_FALLBACK
        assert malformed['reason'] == REASON_LOCAL_CONFIG_MALFORMED

        # 3. Parseable, and naming no target.
        _write_run_config(project, json.dumps({}))
        unnamed = resolve_target(cwd=project)
        assert unnamed['target_source'] == SOURCE_FALLBACK
        assert unnamed['reason'] == REASON_TARGET_ABSENT

        assert len({absent['reason'], malformed['reason'], unnamed['reason']}) == 3

    def test_a_directory_at_the_config_path_is_absent_not_unreadable(self, project):
        """The LOCATE requires a file, so a directory is never read at all.

        This is the discrimination the ``unreadable`` row below depends on: a
        reader that located on ``exists()`` instead of ``is_file()`` would reach
        the read, fail there, and report a condition that is actually a locate
        miss. Asserting the absent verdict pins which leg actually ran.
        """
        (project / '.plan').mkdir(parents=True, exist_ok=True)
        (project / '.plan' / 'run-configuration.json').mkdir()

        resolved = resolve_target(cwd=project)

        assert resolved['target_source'] == SOURCE_FALLBACK
        assert resolved['reason'] == REASON_LOCAL_CONFIG_ABSENT

    @pytest.mark.skipif(
        hasattr(os, 'geteuid') and os.geteuid() == 0,
        reason='a root host bypasses the file mode, so the read cannot be made to fail',
    )
    def test_an_unreadable_local_config_names_its_own_condition(self, project):
        """A file that exists but cannot be read reports ``local_config_unreadable``.

        The fourth fall-through condition, and the one a value-only assertion
        cannot reach: the verdict carries the same target as every other
        fallback, so only the reason separates it. The mode change is restored in
        a ``finally`` so a failing assertion cannot leave an unreadable tree for
        the next test in the session.
        """
        cfg = _write_run_config(project, json.dumps({'target': 'claude'}))
        original_mode = cfg.stat().st_mode
        try:
            os.chmod(cfg, 0o000)
            resolved = resolve_target(cwd=project)
        finally:
            os.chmod(cfg, original_mode)

        assert resolved['target_source'] == SOURCE_FALLBACK
        assert resolved['reason'] == REASON_LOCAL_CONFIG_UNREADABLE

    @pytest.mark.parametrize(
        ('body', 'case'),
        [
            (json.dumps({}), 'no-target-key'),
            (json.dumps({'runtime': 'opencode'}), 'runtime-is-a-scalar'),
            (json.dumps({'runtime': {}}), 'runtime-block-empty'),
            (json.dumps({'target': ''}), 'target-is-empty-string'),
            (json.dumps({'target': 7}), 'target-is-not-a-string'),
            (json.dumps({'harness': ''}), 'harness-is-empty-string'),
        ],
        ids=[
            'no-target-key',
            'runtime-is-a-scalar',
            'runtime-block-empty',
            'target-is-empty-string',
            'target-is-not-a-string',
            'harness-is-empty-string',
        ],
    )
    def test_a_config_present_but_unusable_names_its_own_condition(self, project, body, case):
        """A file that EXISTS but names no target reports ``target_absent``.

        Every row is a different shape that fails to name a target; all of them
        are the same CONDITION (``the file is there, the declaration is not``)
        and therefore share one reason.
        """
        _write_run_config(project, body)

        resolved = resolve_target(cwd=project)

        assert resolved['target_source'] == SOURCE_FALLBACK, case
        assert resolved['reason'] == REASON_TARGET_ABSENT, case

    def test_a_payload_that_is_not_an_object_is_malformed_not_unusable(self, project):
        """A JSON list is a MALFORMED config, not a config with nothing in it.

        The distinction is which file was found: a list is not the object the
        contract describes at all, so it belongs with the unparseable shapes
        rather than with the ones that parse and name no target. Asserting it
        here is what stops the two conditions from being merged later.
        """
        _write_run_config(project, json.dumps(['a', 'list']))

        resolved = resolve_target(cwd=project)

        assert resolved['target_source'] == SOURCE_FALLBACK
        assert resolved['reason'] == REASON_LOCAL_CONFIG_MALFORMED

    def test_every_documented_reason_is_reachable(self, project):
        """Each ``REASON_*`` constant names a condition the resolver can actually reach.

        A constant nothing produces is a constant that documents a condition
        that does not exist, and this test is what tells the two apart. The
        reasons are derived by DRIVING the resolver, never by restating the
        expected set, so adding a reason without implementing it fails here.

        ``REASON_LOCAL_CONFIG_UNREADABLE`` is reached by the chmod case above and is
        therefore asserted here by identity rather than re-driven, because a root
        host cannot make the read fail and this test must not skip.
        """
        plan_dir = project / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        seen = {resolve_target(cwd=project)['reason']}

        for body in ('not json', json.dumps({})):
            _write_run_config(project, body)
            seen.add(resolve_target(cwd=project)['reason'])

        assert seen == {
            REASON_LOCAL_CONFIG_ABSENT,
            REASON_LOCAL_CONFIG_MALFORMED,
            REASON_TARGET_ABSENT,
        }
        # The fourth leg is covered by its own test; this asserts the exported
        # vocabulary is exactly the reachable set plus that one, so a constant
        # added without an implementing leg fails here.
        exported = {value for name, value in vars(target_context).items() if name.startswith('REASON_')}
        assert exported == seen | {REASON_LOCAL_CONFIG_UNREADABLE}


class TestDefaultTarget:
    """The fallback value follows the runtime registry, not a repeated literal."""

    def test_default_matches_the_registry(self):
        """``default_target()`` agrees with ``platform_runtime._DEFAULT_TARGET``."""
        from platform_runtime import _DEFAULT_TARGET

        assert default_target() == _DEFAULT_TARGET

    def test_env_detection_returns_none_without_a_signal(self):
        """No platform signal means no env verdict, not a default."""
        assert detect_target_from_env() is None


class TestFindLocalConfig:
    """The locate half of the machine-local config tier, split out so it is testable alone."""

    def test_returns_none_when_no_ancestor_carries_one(self, outside_repo_dir):
        """A tree with no machine-local config anywhere above cwd locates nothing."""
        assert find_local_config(outside_repo_dir) is None

    def test_returns_the_nearest_of_several(self, tmp_path):
        """The FIRST hit walking up wins — the nearest, not the outermost."""
        _write_local_harness_config(tmp_path, 'claude')
        nested = tmp_path / 'child'
        nested.mkdir()
        _write_local_harness_config(nested, 'opencode')
        deeper = nested / 'deeper'
        deeper.mkdir()

        found = find_local_config(deeper)

        assert found == nested / '.plan' / 'local' / 'harness' / 'opencode.json'
        assert json.loads(found.read_text(encoding='utf-8'))['harness'] == 'opencode'

    def test_stops_at_project_root_boundary_without_escaping(self, tmp_path):
        """The walk stops at a project root boundary (.plan/marshal.json or .git) and does not escape."""
        outer = tmp_path / 'outer'
        _write_local_harness_config(outer, 'claude')
        inner = outer / 'inner_project'
        (inner / '.plan').mkdir(parents=True)
        (inner / '.plan' / 'marshal.json').write_text('{}', encoding='utf-8')
        child = inner / 'child'
        child.mkdir()

        # Inside inner_project, which has its own marshal.json boundary but no local config,
        # it must NOT escape to outer's local harness config.
        assert find_local_config(child) is None


class TestResolveContext:
    """The ``{target, marketplace-root}`` pair every executor verb operates under."""

    def test_returns_the_documented_keys(self, tmp_path):
        """The payload carries ``target``, ``target_source`` and ``marketplace_root``."""
        _write_local_harness_config(tmp_path, 'opencode')

        ctx = resolve_context(cwd=tmp_path)

        assert ctx['target'] == 'opencode'
        assert ctx['target_source'] == SOURCE_LOCAL_CONFIG
        assert ctx['marketplace_root'] is None

    def test_explicit_target_outranks_the_whole_cascade(self, tmp_path, monkeypatch):
        """An explicit target wins over an env signal AND over machine-local config."""
        _write_local_harness_config(tmp_path, 'claude')
        monkeypatch.setenv('OPENCODE', '1')

        ctx = resolve_context(target='antigravity', cwd=tmp_path)

        assert ctx['target'] == 'antigravity'
        assert ctx['target_source'] == SOURCE_EXPLICIT

    def test_verb_argv_needing_no_context_still_resolves(self, tmp_path):
        """A call with neither a target nor an anchor resolves rather than raising.

        ``verify`` and ``paths`` register ``--target`` but not
        ``--marketplace-root``, so the pair is routinely absent together.
        """
        _write_local_harness_config(tmp_path, 'opencode')

        ctx = resolve_context(cwd=tmp_path)

        assert ctx['target'] == 'opencode'
        assert ctx['marketplace_root'] is None

    def test_explicit_marketplace_root_is_normalised(self, tmp_path):
        """A supplied anchor comes back as an expanded ``Path``, not a raw string."""
        ctx = resolve_context(marketplace_root=str(tmp_path / 'anchor'))

        assert ctx['marketplace_root'] == tmp_path / 'anchor'

    def test_cwd_current_directory_anchor_is_accepted(self, tmp_path):
        """``.`` names a directory and stays a valid anchor."""
        assert resolve_marketplace_root('.') == Path('.')

    @pytest.mark.parametrize('value', ['', '   '], ids=['empty', 'whitespace-only'])
    def test_empty_anchor_is_refused(self, value):
        """An anchor that names nothing is refused at the resolver."""
        with pytest.raises(ValueError, match='non-empty'):
            resolve_marketplace_root(value)

    @pytest.mark.parametrize(
        'value',
        ['..', '../escape', 'a/../../b', '/abs/../../etc'],
        ids=['bare-parent', 'leading-parent', 'embedded-parent', 'absolute-with-parent'],
    )
    def test_traversing_anchor_is_refused(self, value):
        """A ``..`` segment lets an anchor address outside itself, so it is refused."""
        with pytest.raises(ValueError, match='traversal'):
            resolve_marketplace_root(value)

    def test_filesystem_root_is_refused(self):
        """``/`` names no directory under itself, so it is not an anchor."""
        with pytest.raises(ValueError, match='filesystem root'):
            resolve_marketplace_root('/')

    def test_non_path_value_is_refused(self):
        """A non-path value is refused by TYPE, before any path construction."""
        with pytest.raises(ValueError, match='must be a path'):
            resolve_marketplace_root(42)

    def test_nul_byte_is_refused(self):
        """A NUL byte in an anchor is refused before it reaches the filesystem."""
        with pytest.raises(ValueError, match='NUL'):
            resolve_marketplace_root('/tmp/a\x00b')

    def test_env_anchor_applies_only_when_no_explicit_value(self, monkeypatch, tmp_path):
        """The env anchor is the LAST-RESORT input, so an explicit one outranks it."""
        monkeypatch.setenv(target_context.MARKETPLACE_ROOT_ENV, str(tmp_path / 'from-env'))

        assert resolve_marketplace_root(None) == tmp_path / 'from-env'
        assert resolve_marketplace_root(tmp_path / 'explicit') == tmp_path / 'explicit'

    def test_no_explicit_value_and_no_env_anchor_is_none(self):
        """Neither supplied nor declared means no anchor — the cwd-walk signal."""
        assert resolve_marketplace_root(None) is None

    def test_explicit_context_takes_precedence_over_the_env_anchor(self, tmp_path, monkeypatch):
        """The pair a verb forwards to its base-path resolution is unambiguous."""
        monkeypatch.setenv(target_context.MARKETPLACE_ROOT_ENV, str(tmp_path / 'from-env'))

        ctx = resolve_context(target='opencode', marketplace_root=tmp_path / 'explicit')

        assert ctx['target'] == 'opencode'
        assert ctx['target_source'] == SOURCE_EXPLICIT
        assert ctx['marketplace_root'] == tmp_path / 'explicit'

    @pytest.mark.parametrize('declared_by', ['explicit', 'env', 'local_config'])
    def test_a_declared_target_does_not_fold_in_the_env_anchor(self, declared_by, project, monkeypatch):
        """A declared target outranks PM_MARKETPLACE_ROOT, so no anchor comes back."""
        monkeypatch.setenv(target_context.MARKETPLACE_ROOT_ENV, str(project / 'from-env'))
        monkeypatch.chdir(project)
        if declared_by == 'env':
            monkeypatch.setenv('OPENCODE', '1')
        elif declared_by == 'local_config':
            _write_local_harness_config(project, 'opencode')

        ctx = resolve_context(target='opencode' if declared_by == 'explicit' else None, cwd=project)

        assert ctx['target'] == 'opencode'
        assert ctx['target_source'] == declared_by
        assert ctx['marketplace_root'] is None

    def test_the_env_anchor_still_applies_when_the_target_fell_back(self, project, monkeypatch):
        """Last resort means last: with no declared target the env anchor is used."""
        monkeypatch.setenv(target_context.MARKETPLACE_ROOT_ENV, str(project / 'from-env'))

        ctx = resolve_context(cwd=project)

        assert ctx['target_source'] == SOURCE_FALLBACK
        assert ctx['marketplace_root'] == project / 'from-env'


class TestSingleImplementation:
    """Guards against a second reader reappearing beside the shared one."""

    def test_marketplace_paths_re_exports_the_single_plan_dir_name(self):
        """``PLAN_DIR_NAME`` keeps ONE definition and two documented import surfaces."""
        import marketplace_paths

        assert marketplace_paths.PLAN_DIR_NAME == target_context.PLAN_DIR_NAME

    def test_marketplace_paths_resolves_through_the_shared_resolver(self, tmp_path, monkeypatch):
        """``marketplace_paths._read_runtime_target`` reaches the ENV tier."""
        import marketplace_paths

        monkeypatch.setenv('OPENCODE', '1')
        assert marketplace_paths._read_runtime_target() == 'opencode'

        monkeypatch.delenv('OPENCODE')
        _write_local_harness_config(tmp_path, 'antigravity')
        monkeypatch.chdir(tmp_path)
        assert marketplace_paths._read_runtime_target() == 'antigravity'

    def test_marshal_json_runtime_target_is_retired_and_ignored(self, tmp_path, monkeypatch, outside_repo_dir):
        """``runtime.target`` in marshal.json is completely retired and not consulted."""
        bare = outside_repo_dir / 'bare'
        bare.mkdir()
        plan_dir = bare / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'antigravity'}}), encoding='utf-8')

        resolved = resolve_target(cwd=bare)

        assert resolved['target'] == default_target()
        assert resolved['target_source'] == SOURCE_FALLBACK
        assert resolved['reason'] == REASON_LOCAL_CONFIG_ABSENT

    def test_retired_config_only_reader_is_gone(self):
        """``generate_executor.read_marshal_target`` must not reappear."""
        generator = (
            PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
        )
        assert 'def read_marshal_target' not in generator.read_text(encoding='utf-8')


class TestEnvIsolation:
    """The suite must not depend on the machine it runs on."""

    def test_no_platform_signal_leaks_into_the_fallback_verdict(self, project):
        """A developer shell carrying a platform signal cannot change this verdict."""
        for name in PLATFORM_ENV_SIGNALS:
            assert name not in os.environ, f'{name} leaked into the test environment'
        assert resolve_target(cwd=project)['target_source'] == SOURCE_FALLBACK
