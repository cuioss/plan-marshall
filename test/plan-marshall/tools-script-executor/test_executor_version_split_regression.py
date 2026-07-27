# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression: a marked newest version dir can never split an executor.

Scope note — deliberately different from the co-located unit tests. D1's tests in
``test_marketplace_bundles.py`` and ``test_generate_executor.py`` assert each
resolver and each guard in isolation. This file builds a **synthetic
multi-version plugin-cache fixture on disk** and drives ``generate_executor``
across it, exercising the composition path the way a real preflight run does:
the notation->path mappings come from the ``find_bundles`` leg while the
``sys.path`` / PYTHONPATH entries come from the ``resolve_bundle_path`` and
``collect_script_dirs`` legs, and both land in the SAME emitted file.

The defect this pins: those legs used to disagree about whether ``.orphaned_at``
disqualifies a candidate, so with the newest dir marked and an older dir unmarked
the mappings resolved under one version dir while the import paths resolved under
another — a perfectly parseable, fully substituted, internally version-split
executor that every existing shape check reported as green.

Pre-fix behaviour of case 1 (documented, not executed here — the pre-fix code is
not importable from this branch): ``find_bundles`` was marker-aware and would
return the older ``1.0.0`` dir, while ``collect_script_dirs`` /
``resolve_bundle_path`` were marker-blind and returned the marked ``1.0.10`` dir.
Both version strings would therefore appear in the emitted executor and
``test_newest_marked_never_writes_a_mixed_version_executor`` would fail on its
"exactly one version dir per bundle" assertion.

No ``conftest.py`` is added under this directory; every helper lives here.
"""

import json
import re
from pathlib import Path

from marketplace_bundles import find_bundles

from conftest import load_script_module

# ``find_bundles`` is the mappings leg: generate_executor reaches it through the
# inventory subprocess, so this file drives the shared module directly.
gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py')

BUNDLE = 'plan-marshall'
OLDER = '1.0.0'
NEWEST = '1.0.10'

#: Shared-module skills ``get_shared_module_dirs`` resolves through
#: ``resolve_bundle_path``; seeding them makes that leg contribute emitted paths.
_SHARED_SKILLS = (
    'tools-file-ops',
    'tools-input-validation',
    'ref-toon-format',
    'script-shared',
    'manage-change-ledger',
)


def _make_version_dir(cache_root: Path, version: str, marked: bool = False) -> Path:
    """Create one fully-eligible plugin-cache version dir under ``cache_root``.

    Eligible for all three legs: carries ``.claude-plugin/plugin.json``
    (``find_bundles``), the shared-module skill subpaths
    (``resolve_bundle_path``) and a ``skills/`` tree (``collect_script_dirs``).
    """
    version_dir = cache_root / BUNDLE / version
    plugin_dir = version_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': BUNDLE, 'version': version}), encoding='utf-8')

    for skill in (*_SHARED_SKILLS, 'manage-logging', 'demo-skill'):
        scripts = version_dir / 'skills' / skill / 'scripts'
        scripts.mkdir(parents=True)
    (version_dir / 'skills' / 'demo-skill' / 'scripts' / 'foo.py').write_text('# foo\n', encoding='utf-8')

    if marked:
        (version_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return version_dir


def _build_cache(tmp_path: Path, newest_marked: bool = False, older_marked: bool = False) -> Path:
    """Build a two-version plugin-cache fixture and return its root."""
    cache_root = tmp_path / 'cache'
    _make_version_dir(cache_root, OLDER, marked=older_marked)
    _make_version_dir(cache_root, NEWEST, marked=newest_marked)
    return cache_root


def _mappings_from_discovery(cache_root: Path) -> dict[str, str]:
    """Build notation->path mappings through the REAL discovery leg.

    ``discover_scripts`` obtains its mappings by subprocess-invoking the
    inventory scanner, which imports ``find_bundles``. Calling ``find_bundles``
    directly exercises the same leg without the subprocess, so the mappings and
    the import paths still come from two independently-resolved families.
    """
    mappings: dict[str, str] = {}
    for bundle_dir in find_bundles(cache_root):
        script = bundle_dir / 'skills' / 'demo-skill' / 'scripts' / 'foo.py'
        if script.is_file():
            mappings[f'{BUNDLE}:demo-skill:foo'] = str(script)
    return mappings


def _generate(tmp_path: Path, cache_root: Path, monkeypatch, mappings: dict[str, str] | None = None) -> dict:
    """Run a real generation against the fixture, writing under ``tmp_path``."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    resolved = _mappings_from_discovery(cache_root) if mappings is None else mappings
    result: dict = gen.generate_executor(resolved, cache_root, dry_run=False, target='claude')
    return result


def _executor_path(tmp_path: Path) -> Path:
    return tmp_path / '.plan' / 'execute-script.py'


def _emitted_versions(text: str, cache_root: Path) -> set[str]:
    """Return every fixture version dir the emitted executor references."""
    prefix = re.escape(f'{cache_root}/{BUNDLE}/')
    return set(re.findall(rf'{prefix}([^/\'"]+)/', text))


# ============================================================================
# Case 1: newest marked, older unmarked, end to end
# ============================================================================


def test_newest_marked_never_writes_a_mixed_version_executor(tmp_path, monkeypatch):
    """The user-visible symptom this plan exists to eliminate.

    With the newest version dir marked, generation must either produce an
    executor whose every emitted path lives under ONE version dir for the
    bundle, or refuse with ``status: error``. It must never write a
    mixed-version executor.
    """
    cache_root = _build_cache(tmp_path, newest_marked=True)

    result = _generate(tmp_path, cache_root, monkeypatch)

    if result['status'] == 'error':
        return  # A fail-closed refusal is an acceptable outcome of the contract.

    assert result['status'] == 'success', f'unexpected status: {result}'
    versions = _emitted_versions(_executor_path(tmp_path).read_text(encoding='utf-8'), cache_root)
    assert len(versions) == 1, f'emitted executor spans multiple version dirs: {sorted(versions)}'


# ============================================================================
# Case 2: three marker states, all legs agreeing
# ============================================================================


def _leg_versions(cache_root: Path) -> tuple[str, str, str]:
    """Version dir chosen by the mappings leg, the shared-module leg, the script-dir leg."""
    found = find_bundles(cache_root)
    assert len(found) == 1, f'fixture must reduce to one version dir, got {found}'

    shared = gen.get_shared_module_dirs(cache_root)
    assert shared, 'fixture must offer shared-module dirs'
    shared_versions = {d.parts[-4] for d in shared}
    assert len(shared_versions) == 1, f'shared-module dirs span versions: {shared_versions}'

    script_dirs = [d for d in gen.collect_script_dirs(cache_root) if d.endswith('scripts')]
    assert script_dirs, 'fixture must offer collected script dirs'
    script_versions = {Path(d).parts[-4] for d in script_dirs}
    assert len(script_versions) == 1, f'collected script dirs span versions: {script_versions}'

    return found[0].name, shared_versions.pop(), script_versions.pop()


def test_all_legs_agree_none_marked(tmp_path):
    cache_root = _build_cache(tmp_path)
    mappings_version, shared_version, scripts_version = _leg_versions(cache_root)
    assert mappings_version == shared_version == scripts_version == NEWEST


def test_all_legs_agree_newest_marked(tmp_path):
    cache_root = _build_cache(tmp_path, newest_marked=True)
    mappings_version, shared_version, scripts_version = _leg_versions(cache_root)
    assert mappings_version == shared_version == scripts_version


def test_all_legs_agree_all_marked(tmp_path):
    """Saturation: every candidate is marked, so no marker carries a currency
    signal and all three legs fall back to the retention-pinned NEWEST dir.

    The assertion pins WHICH dir they agree on, not merely that they agree — a
    bare cross-leg comparison also passes when all three regress together to
    OLDER, so it cannot fail in the direction that matters. The tuple form still
    proves agreement as a side effect.
    """
    cache_root = _build_cache(tmp_path, newest_marked=True, older_marked=True)
    mappings_version, shared_version, scripts_version = _leg_versions(cache_root)
    assert (mappings_version, shared_version, scripts_version) == (NEWEST, NEWEST, NEWEST)


# ============================================================================
# Case 3: the guard preserves the prior executor byte-for-byte
# ============================================================================


def test_provenance_violation_preserves_the_prior_executor_byte_for_byte(tmp_path, monkeypatch):
    """A forced provenance violation is refused and the seeded executor's FULL
    content is unchanged — compared byte-for-byte, not by mtime or length."""
    cache_root = _build_cache(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    executor = plan_dir / 'execute-script.py'
    seeded = '# SENTINEL known-good executor\nSCRIPTS = {}\n'
    executor.write_text(seeded, encoding='utf-8')

    # Synthetic violation: one bundle contributing paths from BOTH version dirs.
    split_mappings = {
        f'{BUNDLE}:demo-skill:older': str(cache_root / BUNDLE / OLDER / 'skills/demo-skill/scripts/foo.py'),
        f'{BUNDLE}:demo-skill:newest': str(cache_root / BUNDLE / NEWEST / 'skills/demo-skill/scripts/foo.py'),
    }
    result = _generate(tmp_path, cache_root, monkeypatch, mappings=split_mappings)

    assert result['status'] == 'error', f'a version-split path set must be refused, got {result}'
    assert executor.read_text(encoding='utf-8') == seeded, (
        'the prior executor must be preserved byte-for-byte after a refusal'
    )


# ============================================================================
# Case 4: a marker on the retention-pinned dir does not suppress it
# ============================================================================


def test_marker_on_the_retention_pinned_dir_does_not_suppress_it(tmp_path):
    """The newest-on-disk dir is the retention pin: a stale marker on it is
    ignored, so the fixture still resolves to that dir."""
    cache_root = _build_cache(tmp_path, newest_marked=True)

    assert _leg_versions(cache_root) == (NEWEST, NEWEST, NEWEST)


# ============================================================================
# Case 5: the GENERATED executor's own runtime resolver agrees, end to end
# ============================================================================
# The write-time guard certifies the emitted paths, but the generated executor
# also re-derives a version dir at RUNTIME for any notation missing from its
# baked-in SCRIPTS dict. That resolver is the fourth marker-blind site the plan
# closes, and it is the one place the policy is deliberately duplicated (the
# executor is bootstrap-free and cannot import the selector). These cases extend
# case 1's guarantee past the write boundary: a runtime miss cannot re-split an
# executor the guard already certified.


def _resolver_from_generated_executor(tmp_path: Path):
    """Extract and load ``_resolve_notation_by_target`` from the GENERATED file.

    Deliberately reads the function out of the written executor rather than the
    ``_CLAUDE_RESOLVER_TEMPLATE`` constant, so substitution itself is covered.
    """
    text = _executor_path(tmp_path).read_text(encoding='utf-8')
    start = text.index('def _resolve_notation_by_target(')
    rest = text[start:]
    match = re.search(r'\n(?=\S)', rest[1:])
    body = rest[: match.start() + 1] if match else rest

    namespace: dict = {'Path': Path}
    exec(body, namespace)  # noqa: S102 — generator-owned source under test
    return namespace['_resolve_notation_by_target']


def _seed_runtime_cache(home: Path, marked: tuple[str, ...] = ()) -> Path:
    """Seed a plugin-cache under ``home`` carrying a MISS-notation script."""
    cache_root = home / '.claude' / 'plugins' / 'cache' / BUNDLE
    for version in (OLDER, NEWEST):
        scripts = cache_root / version / 'skills' / 'miss-skill' / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'absent.py').write_text('# absent from SCRIPTS\n', encoding='utf-8')
        if version in marked:
            (cache_root / version / '.orphaned_at').write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return cache_root


def _assert_generated_resolver_agrees(tmp_path, monkeypatch, marked: tuple[str, ...]) -> None:
    cache_root = _build_cache(tmp_path)
    result = _generate(tmp_path, cache_root, monkeypatch)
    assert result['status'] == 'success', f'fixture generation must succeed, got {result}'

    home = tmp_path / 'home'
    runtime_cache = _seed_runtime_cache(home, marked=marked)
    monkeypatch.setattr(Path, 'home', lambda: home)

    expected = gen.select_live_version_dir(
        runtime_cache, lambda d: (d / 'skills' / 'miss-skill' / 'scripts' / 'absent.py').is_file()
    )
    assert expected is not None

    resolve = _resolver_from_generated_executor(tmp_path)
    resolved = resolve(f'{BUNDLE}:miss-skill:absent')

    assert resolved is not None, 'the generated resolver must resolve a SCRIPTS-miss notation'
    assert Path(resolved).parents[3] == expected.resolve(), (
        f'generated resolver chose {Path(resolved).parents[3]}, generation-time selector chose {expected.resolve()}'
    )


def test_generated_resolver_agrees_none_marked(tmp_path, monkeypatch):
    _assert_generated_resolver_agrees(tmp_path, monkeypatch, marked=())


def test_generated_resolver_agrees_newest_marked(tmp_path, monkeypatch):
    _assert_generated_resolver_agrees(tmp_path, monkeypatch, marked=(NEWEST,))


def test_generated_resolver_agrees_all_marked(tmp_path, monkeypatch):
    _assert_generated_resolver_agrees(tmp_path, monkeypatch, marked=(OLDER, NEWEST))
