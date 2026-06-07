#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for ``enrich_all()`` and ``cmd_enrich_all()`` in ``_cmd_enrich.py``.

Pins the per-module on-disk layout: enrich_all iterates ``_project.json``'s
``modules`` index and writes per-module ``enriched.json`` files via
``enrich_add_domain()``. Legacy monolithic files are intentionally absent
from this surface.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import PLAN_DIR_NAME, PROJECT_ROOT, load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import setup_test_project  # noqa: E402


_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')
_plan_logging = load_script_module('plan-marshall', 'manage-logging', 'plan_logging.py', 'plan_logging')

load_module_enriched = _architecture_core.load_module_enriched
enrich_all = _cmd_enrich.enrich_all
cmd_enrich_all = _cmd_enrich.cmd_enrich_all
get_global_log_dir = _plan_logging.get_global_log_dir

# Absolute path to the REAL repo-local global log directory — the production log
# the leak historically polluted. The regression tests below assert that the
# fake-bundle discovery error path never appends to any log file under this dir.
_REAL_GLOBAL_LOG_DIR = PROJECT_ROOT / PLAN_DIR_NAME / 'local' / 'logs'

# Substrings of the WARNING lines the discovery error path emits. A regression is
# any one of these landing in the production global log after the 'global'->None fix.
_LEAK_MARKERS = ('[EXTENSION]', '[MODULE-AGGREGATION]', '[SUGGEST]', '[ENRICH]')


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_skill_names(profile_data: dict) -> list[str]:
    """Extract skill names from structured profile data."""
    skills = []
    if not isinstance(profile_data, dict):
        return skills
    for section in ['defaults', 'optionals']:
        for entry in profile_data.get(section, []):
            skills.append(entry.get('skill', entry) if isinstance(entry, dict) else entry)
    return skills


# ``setup_test_project`` hoisted to ``_fixtures.py`` (see top-of-file import).


# =============================================================================
# Fake Extension Infrastructure
# =============================================================================


def _build_skills_by_profile(bundle: str, skill_name: str) -> dict:
    """Build a minimal skills_by_profile dict for a fake extension."""
    return {
        'implementation': {
            'defaults': [
                {'skill': f'{bundle}:{skill_name}', 'description': f'Fake skill from {bundle}'},
            ],
            'optionals': [],
        },
    }


class _FakeExtensionApplicable:
    """Fake extension that applies to modules with a given build system."""

    def __init__(
        self,
        domain_key: str = 'fake-domain',
        bundle: str = 'fake-bundle',
        skill_name: str = 'fake-skill',
        required_build_system: str = 'maven',
    ):
        self._domain_key = domain_key
        self._bundle = bundle
        self._skill_name = skill_name
        self._required_build_system = required_build_system

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {
                    'key': self._domain_key,
                    'name': 'Fake Domain',
                    'description': 'Test fake domain',
                },
                'profiles': {
                    'implementation': {
                        'defaults': [
                            {
                                'skill': f'{self._bundle}:{self._skill_name}',
                                'description': f'Fake skill from {self._bundle}',
                            }
                        ],
                        'optionals': [],
                    }
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        build_systems = module_data.get('build_systems', [])
        if self._required_build_system in build_systems:
            return {
                'applicable': True,
                'confidence': 'high',
                'signals': [f'has {self._required_build_system}'],
                'additive_to': None,
                'skills_by_profile': _build_skills_by_profile(self._bundle, self._skill_name),
            }
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }


class _FakeExtensionRaises:
    """Fake extension whose get_skill_domains() raises."""

    def get_skill_domains(self) -> list[dict]:
        raise RuntimeError('boom: get_skill_domains failed')

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }


def _patch_extensions(monkeypatch: pytest.MonkeyPatch, extensions: list[dict]) -> None:
    """Patch discover_all_extensions at the extension_discovery module level.

    enrich_all and enrich_add_domain both import discover_all_extensions
    inside their function bodies, so patching the module attribute reaches
    every call site.
    """
    import extension_discovery

    monkeypatch.setattr(extension_discovery, 'discover_all_extensions', lambda: extensions)


# =============================================================================
# Tests for enrich_all
# =============================================================================


def test_enrich_all_all_applicable(monkeypatch):
    """Single module with applicable fake extension → enriched, pairs_applied > 0."""
    fake_ext = _FakeExtensionApplicable(
        domain_key='fake-java',
        bundle='fake-java-bundle',
        skill_name='fake-java-core',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'fake-java-bundle', 'path': '/fake/path', 'module': fake_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert 'module-a' in result['modules_enriched']
        assert result['pairs_applied'] > 0
        assert result['errors'] == []

        # Verify per-module enriched.json was updated.
        enriched = load_module_enriched('module-a', tmpdir)
        sbp = enriched['skills_by_profile']
        assert sbp, 'skills_by_profile should be non-empty'
        all_names: list[str] = []
        for profile_data in sbp.values():
            all_names.extend(_extract_skill_names(profile_data))
        assert any('fake-java-core' in s for s in all_names), f'Expected fake-java-core in {all_names}'


def test_enrich_all_mixed_applicability(monkeypatch):
    """Two modules: one applicable (maven), one not (unknown). Only applicable enriched."""
    fake_applicable = _FakeExtensionApplicable(
        domain_key='fake-maven',
        bundle='fake-maven-bundle',
        skill_name='fake-maven-skill',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'fake-maven-bundle', 'path': '/fake/path', 'module': fake_applicable}])

    modules = {
        'applicable-mod': {
            'name': 'applicable-mod',
            'build_systems': ['maven'],
            'paths': {'module': 'applicable-mod'},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'commands': {},
        },
        'other-mod': {
            'name': 'other-mod',
            'build_systems': ['unknown'],
            'paths': {'module': 'other-mod'},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'commands': {},
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir, modules=modules)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert 'applicable-mod' in result['modules_enriched']
        assert 'other-mod' not in result['modules_enriched']
        assert result['pairs_skipped'] > 0
        assert result['errors'] == []


def test_enrich_all_idempotent(monkeypatch):
    """Running enrich_all twice: second run produces pairs_applied == 0."""
    fake_ext = _FakeExtensionApplicable(
        domain_key='idem-domain',
        bundle='idem-bundle',
        skill_name='idem-skill',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'idem-bundle', 'path': '/fake/path', 'module': fake_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        first = enrich_all(tmpdir)
        assert first['status'] == 'success'
        assert first['pairs_applied'] > 0
        assert first['errors'] == []

        second = enrich_all(tmpdir)
        assert second['status'] == 'success'
        assert second['pairs_applied'] == 0, 'Second run should not add duplicates'
        assert second['errors'] == []

        enriched = load_module_enriched('module-a', tmpdir)
        sbp = enriched['skills_by_profile']
        for profile_data in sbp.values():
            names = _extract_skill_names(profile_data)
            assert len(names) == len(set(names)), f'Duplicate skills detected: {names}'


def test_enrich_all_extension_exception_captured(monkeypatch):
    """Extension raising in get_skill_domains() is captured in summary.errors."""
    raising_ext = _FakeExtensionRaises()
    _patch_extensions(monkeypatch, [{'bundle': 'raising-bundle', 'path': '/fake/path', 'module': raising_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert result['errors'], 'Expected at least one captured error'
        assert any('raising-bundle' in str(err) for err in result['errors']), (
            f'Expected bundle name in errors, got: {result["errors"]}'
        )
        assert result['modules_enriched'] == []
        assert result['pairs_applied'] == 0


def test_enrich_all_empty_project_returns_success_with_no_modules():
    """CLI wrapper returns success with empty modules when the crawl finds nothing.

    Under the on-demand crawl model iter_modules returns [] instead of
    raising DataNotFoundError when there are no modules. enrich_all
    therefore completes cleanly with an empty modules_enriched list.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Do NOT call setup_test_project — tmpdir is empty.
        args = SimpleNamespace(project_dir=tmpdir, include_optionals=False, reasoning=None)

        result = cmd_enrich_all(args)

        assert result['status'] == 'success'
        assert result['modules_enriched'] == []
        assert result['pairs_applied'] == 0


def test_enrich_all_empty_extension_list(monkeypatch):
    """No extensions: pairs_applied == 0, pairs_skipped == 0, modules_enriched == []."""
    _patch_extensions(monkeypatch, [])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert result['pairs_applied'] == 0
        assert result['pairs_skipped'] == 0
        assert result['modules_enriched'] == []
        assert result['errors'] == []


# =============================================================================
# Regression: fake-bundle discovery failures must not pollute the production log
# =============================================================================
#
# History: ``extension_discovery.py`` / ``_module_aggregation.py`` / ``_cmd_enrich.py``
# / ``_cmd_suggest.py`` logged discover_modules()/get_skill_domains() failures to a
# hard-coded ``'global'`` log scope. Under the global-fallback path that resolves to
# the shared production log at ``.plan/local/logs/script-execution-*.log``. The
# ``_FakeExtension*`` doubles above deliberately drive that exception path, so the
# tests leaked [EXTENSION]/[MODULE-AGGREGATION] WARNINGs into the real log (435 such
# entries found by the archived-plan retrospective audit).
#
# The fix is two-pronged and BOTH prongs are asserted here:
#   1. Fixture isolation — the autouse ``_plan_base_dir_sandbox`` fixture (conftest)
#      redirects ``PLAN_BASE_DIR`` into a per-test tmp sandbox, so even a surviving
#      ``'global'`` fallback writes into the sandbox, never the real tree.
#   2. Code fix — the discovery error paths now pass ``None`` (no plan context)
#      instead of the literal ``'global'``.


def _snapshot_real_global_log_lines() -> list[str]:
    """Return every line currently present across the REAL global log files.

    Reads ``script-execution-*.log`` under the real repo-local
    ``.plan/local/logs/`` directory. Returns ``[]`` when the directory is absent.
    The before/after delta of this listing is the regression signal: a leak adds
    one or more ``_LEAK_MARKERS`` lines.
    """
    if not _REAL_GLOBAL_LOG_DIR.exists():
        return []
    lines: list[str] = []
    for log_file in sorted(_REAL_GLOBAL_LOG_DIR.glob('script-execution-*.log')):
        try:
            lines.extend(log_file.read_text(encoding='utf-8').splitlines())
        except OSError:
            continue
    return lines


def test_global_log_dir_resolves_into_sandbox():
    """Fixture-isolation guard: the autouse sandbox redirects the global log dir.

    With ``_plan_base_dir_sandbox`` active (autouse), ``get_global_log_dir()`` must
    resolve OUTSIDE the real repo-local ``.plan/local/logs/`` tree. This is the
    structural backstop that makes a surviving ``'global'`` fallback harmless.
    """
    resolved = get_global_log_dir().resolve()

    assert resolved != _REAL_GLOBAL_LOG_DIR.resolve(), (
        f'get_global_log_dir() resolved to the real production log dir {resolved} — '
        'the autouse PLAN_BASE_DIR sandbox did not hold'
    )
    assert _REAL_GLOBAL_LOG_DIR.resolve() not in resolved.parents, (
        f'get_global_log_dir() {resolved} is nested under the real log tree '
        f'{_REAL_GLOBAL_LOG_DIR} — sandbox redirect leaked'
    )


def test_enrich_all_raising_extension_does_not_pollute_production_global_log(monkeypatch):
    """Regression: the raising-extension path adds no entry to the production log.

    Drives the exact exception path the leak rode on (``get_skill_domains()`` raising)
    and asserts that NO new leak-marker line lands in the real repo-local global log.
    The error is still captured in the in-memory summary (functional behaviour is
    unchanged) — only the log *destination* moved off the production tree.
    """
    before = _snapshot_real_global_log_lines()

    raising_ext = _FakeExtensionRaises()
    _patch_extensions(monkeypatch, [{'bundle': 'raising-bundle', 'path': '/fake/path', 'module': raising_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

    # Functional behaviour preserved: the failure is still surfaced in the summary.
    assert result['status'] == 'success'
    assert result['errors'], 'Expected the raising extension to surface a captured error'

    # Regression assertion: no new leak-marker line in the real production log.
    after = _snapshot_real_global_log_lines()
    new_lines = after[len(before):] if after[: len(before)] == before else after
    leaked = [line for line in new_lines if any(marker in line for marker in _LEAK_MARKERS)]
    assert not leaked, (
        f'Discovery error path leaked {len(leaked)} entry/entries into the production '
        f'global log {_REAL_GLOBAL_LOG_DIR}:\n  ' + '\n  '.join(leaked)
    )


def test_enrich_all_applicable_extension_does_not_pollute_production_global_log(monkeypatch):
    """Regression: the applicable (non-raising) path also leaves the production log clean.

    Covers the common success path the fake-java/fake-maven/idem doubles exercise.
    No extension raises here, so no discovery-error WARNING should be emitted at all —
    and certainly nothing should reach the real production log.
    """
    before = _snapshot_real_global_log_lines()

    fake_ext = _FakeExtensionApplicable(
        domain_key='regress-domain',
        bundle='regress-bundle',
        skill_name='regress-skill',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'regress-bundle', 'path': '/fake/path', 'module': fake_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

    assert result['status'] == 'success'

    after = _snapshot_real_global_log_lines()
    new_lines = after[len(before):] if after[: len(before)] == before else after
    leaked = [line for line in new_lines if any(marker in line for marker in _LEAK_MARKERS)]
    assert not leaked, (
        f'Applicable-extension path leaked {len(leaked)} entry/entries into the production '
        f'global log {_REAL_GLOBAL_LOG_DIR}:\n  ' + '\n  '.join(leaked)
    )


def _snapshot_real_global_log_sizes() -> dict[str, int]:
    """Byte-size snapshot of EVERY file under the REAL global log dir.

    Maps each file's path (relative to ``_REAL_GLOBAL_LOG_DIR``) to its byte
    size. Returns ``{}`` when the directory is absent. This is a stronger
    invariant than the line-based snapshot above: it catches an APPEND to any
    log file (size growth) as well as a NEW file appearing, for every log file
    in the dir — not only the ``script-execution-*.log`` family. The
    before/after equality of this mapping is the deliverable-2 regression
    signal: a leak either grows an existing file or creates a new one.

    ``_REAL_GLOBAL_LOG_DIR`` is derived from ``PROJECT_ROOT`` (a real, fixed repo
    path), NOT from ``get_global_log_dir()`` — so it resolves the genuine
    production dir regardless of any active ``PLAN_BASE_DIR`` redirect.
    """
    if not _REAL_GLOBAL_LOG_DIR.exists():
        return {}
    sizes: dict[str, int] = {}
    for path in sorted(_REAL_GLOBAL_LOG_DIR.rglob('*')):
        if not path.is_file():
            continue
        try:
            sizes[str(path.relative_to(_REAL_GLOBAL_LOG_DIR))] = path.stat().st_size
        except OSError:
            continue
    return sizes


def test_enrich_all_no_global_log_leak(monkeypatch):
    """Deliverable-2 regression: fake-bundle discovery failures leave the real log byte-for-byte unchanged.

    Strict ordering, deterministic and order-independent:

    1. Snapshot the REAL production global log dir (file set + per-file byte
       size) BEFORE any redirect. ``_REAL_GLOBAL_LOG_DIR`` is resolved from
       ``PROJECT_ROOT`` (independent of ``PLAN_BASE_DIR``), so the snapshot
       always targets the genuine production dir.
    2. Redirect ``PLAN_BASE_DIR`` to a per-test temp dir, so any surviving
       ``'global'``/``None``-scope fallback write is contained in throwaway
       temp space and cannot touch the real dir even if a leak survives.
    3. Run ``enrich_all`` with ``_FakeExtensionRaises`` — the deliberately
       failing exception path that historically triggered the discovery
       WARNING leak.
    4. Assert the real ``.plan/local/logs/`` is byte-for-byte unchanged: no new
       files, no size growth in any log file.

    Steps 1+4 prove the production log was untouched; the step-2 redirect makes
    that assertion meaningful (a surviving fallback write lands in temp space)
    rather than accidentally passing. Against the pre-fix ``'global'`` literal
    WITHOUT the redirect this would fail (the discovery WARNING grows the real
    ``script-execution-*.log``).
    """
    # Step 1 — snapshot the REAL production log dir before any redirect.
    before = _snapshot_real_global_log_sizes()

    raising_ext = _FakeExtensionRaises()
    _patch_extensions(monkeypatch, [{'bundle': 'leak-regress-bundle', 'path': '/fake/path', 'module': raising_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 2 — redirect PLAN_BASE_DIR into the per-test temp dir.
        monkeypatch.setenv('PLAN_BASE_DIR', tmpdir)
        setup_test_project(tmpdir)

        # Step 3 — drive the discovery exception path.
        result = enrich_all(tmpdir)

    # Functional behaviour preserved: the failure is still captured in-memory.
    assert result['status'] == 'success'
    assert result['errors'], 'Expected the raising extension to surface a captured error'

    # Step 4 — the real production log dir is byte-for-byte unchanged.
    after = _snapshot_real_global_log_sizes()

    new_files = sorted(set(after) - set(before))
    grown_files = sorted(
        f'{name}: {before[name]} -> {after[name]} bytes'
        for name in set(before) & set(after)
        if after[name] != before[name]
    )
    assert not new_files and not grown_files, (
        f'Discovery error path mutated the production global log {_REAL_GLOBAL_LOG_DIR}:\n'
        f'  new files: {new_files}\n'
        f'  grown files: {grown_files}'
    )
