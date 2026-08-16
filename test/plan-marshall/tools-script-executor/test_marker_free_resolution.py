# SPDX-License-Identifier: FSL-1.1-ALv2
"""D6 regression suite for marker-free plugin-cache version resolution.

The version-selection machinery no longer consults the shared ``.orphaned_at``
marker. Resolution — both the executor's embedded runtime resolver and the
shared ``select_live_version_dir`` selector — picks the numerically-newest
*eligible* version directory and ignores the marker entirely. There is no
degraded "orphan-marker saturation" fallback and no stderr warning, because a
state that no longer turns on the marker cannot be saturated by it. Nothing
under this repository's tree writes the marker.

These are the four D6 deliverables of the collapse-the-version-selection plan:

* (a) the embedded resolver ignores an ``.orphaned_at`` mark and returns the
  newest version dir that actually carries the script, even when a still-newer
  dir does not carry it (the case the pre-fix marker rule mis-selected);
* (b) a fully marker-saturated cache resolves to the newest eligible dir with
  NO degraded-fallback stderr line;
* (c) a genuinely broken cache (no eligible candidate) still fails LOUDLY —
  ``None`` — so the fix never becomes a resolver that always finds *something*;
* (d) no production source under our tree writes the shared marker.
"""

from __future__ import annotations

import ast
from pathlib import Path

from marketplace_bundles import select_live_version_dir

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_REPO_ROOT = PROJECT_ROOT
_BUNDLES_ROOT = _REPO_ROOT / 'marketplace' / 'bundles'
_MARKER_NAME = '.orphaned_at'
_SOURCE_GLOB = '**/skills/**/scripts/*.py'

_GENERATE_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'tools-script-executor'
    / 'scripts'
    / 'generate_executor.py'
)

_SUBPATH = 'skills/skill-x/scripts/bar.py'


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _load_generate_module():
    """Load generate_executor as a module (mirrors the sibling suite's loader)."""
    import types

    module = types.ModuleType('generate_executor')
    module.__dict__['__file__'] = str(_GENERATE_SCRIPT)
    exec(_GENERATE_SCRIPT.read_text(encoding='utf-8'), module.__dict__)  # noqa: S102 — repo-owned source
    return module


def _load_claude_resolver():
    """Render and load the REAL embedded Claude target-aware resolver.

    Pulls the actual resolver body via ``generate_target_aware_resolver_code``
    and execs it, so the production resolver source is what is under test.
    """
    module = _load_generate_module()
    src = module.generate_target_aware_resolver_code('claude')
    namespace: dict = {'Path': Path}
    exec(src, namespace)  # noqa: S102 — generator-owned template source
    return namespace['_resolve_notation_by_target']


def _make_cache_script(home: Path, version: str, skill: str, script: str, *, marked: bool = False) -> Path:
    """Create ``{home}/.claude/plugins/cache/plan-marshall/{version}/skills/{skill}/scripts/{script}.py``."""
    version_dir = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / version
    scripts_dir = version_dir / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / f'{script}.py'
    script_file.write_text(f'# {version} {skill} {script}\n')
    if marked:
        (version_dir / _MARKER_NAME).write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return script_file


def _make_empty_version(home: Path, version: str, *, marked: bool = False) -> Path:
    """Create a bundle version dir under the fake cache that carries NO skill script."""
    version_dir = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / version
    version_dir.mkdir(parents=True, exist_ok=True)
    if marked:
        (version_dir / _MARKER_NAME).write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return version_dir


def _version_dir(base: Path, name: str, version: str, *, subpath: str | None, marked: bool = False) -> Path:
    """Create a selector-eligibility fixture version dir.

    When ``subpath`` is given the dir carries it (so a ``has-subpath`` predicate
    treats it as eligible); when ``None`` the dir is bare and ineligible.
    """
    version_dir = base / name / version
    version_dir.mkdir(parents=True, exist_ok=True)
    if subpath is not None:
        target = version_dir / subpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# script')
    if marked:
        (version_dir / _MARKER_NAME).write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return version_dir


# --------------------------------------------------------------------------- #
# (a) Embedded resolver ignores the marker and picks newest-with-script
# --------------------------------------------------------------------------- #


def test_resolver_ignores_orphan_mark_and_selects_newest_carrying_the_script(tmp_path, monkeypatch):
    """D6(a). The embedded resolver returns the newest version dir that carries
    the script, IGNORING a ``.orphaned_at`` mark on it — even when a still-newer
    dir does not carry the script.

    Pre-fix the resolver excluded a marked non-pinned candidate and mis-selected
    the OLDER unmarked ``0.1.100``; the marker-free resolver returns ``0.1.200``.
    A newer ``0.1.300`` that lacks the script is present so the newest-on-disk
    'pin' cannot rescue the marked ``0.1.200`` — this is the exact shape the old
    marker rule got wrong.
    """
    home = tmp_path / 'home'
    older = _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files', marked=False)
    newest_with_script = _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files', marked=True)
    _make_empty_version(home, '0.1.300')  # newest-on-disk, but carries no skill script

    monkeypatch.setattr(Path, 'home', lambda: home)

    resolve = _load_claude_resolver()
    result = resolve('plan-marshall:manage-files:manage-files')

    assert result == str(newest_with_script.resolve()), (
        f'the resolver must ignore the .orphaned_at mark and return the newest dir '
        f'carrying the script {newest_with_script.resolve()!r}, got {result!r} '
        f'(the pre-fix marker rule mis-selected the older {older.resolve()!r})'
    )


def test_resolver_survives_deletion_of_generation_time_version(tmp_path, monkeypatch):
    """D6(a), survival axis. After the version dir the executor resolved against
    is deleted, a later resolve re-resolves at runtime to the newest surviving
    dir carrying the script — with an ``.orphaned_at`` mark present on it, which
    must not suppress it.
    """
    home = tmp_path / 'home'
    older = _make_cache_script(home, '0.1.5', 'manage-status', 'manage-status', marked=True)
    newest = _make_cache_script(home, '0.1.10', 'manage-status', 'manage-status', marked=True)

    monkeypatch.setattr(Path, 'home', lambda: home)
    resolve = _load_claude_resolver()

    first = resolve('plan-marshall:manage-status:manage-status')
    assert first == str(newest.resolve()), f'expected newest {newest.resolve()!r}, got {first!r}'

    # Delete the generation-time (newest) version dir wholesale.
    import shutil

    shutil.rmtree(newest.parents[3])

    second = resolve('plan-marshall:manage-status:manage-status')
    assert second == str(older.resolve()), (
        f'after deleting the generation-time version, the resolver must re-resolve to '
        f'the surviving {older.resolve()!r} despite its .orphaned_at mark, got {second!r}'
    )


# --------------------------------------------------------------------------- #
# (b) Saturated cache resolves with no degraded fallback / no warning
# --------------------------------------------------------------------------- #


def test_saturated_cache_resolves_to_newest_without_degraded_warning(tmp_path, capsys):
    """D6(b). With EVERY eligible version dir marked ``.orphaned_at`` — the
    observed saturated state — ``select_live_version_dir`` returns the newest
    eligible dir and emits NO stderr line. Pre-fix this hit the degraded
    'orphan-marker saturation' fallback and warned; there is no such path now.
    """
    base = tmp_path / 'cache'
    _version_dir(base, 'bundle-a', '1.0.0', subpath=_SUBPATH, marked=True)
    newest_eligible = _version_dir(base, 'bundle-a', '1.0.10', subpath=_SUBPATH, marked=True)
    # A newer, ineligible dir so the newest-on-disk cannot be the eligible pin.
    _version_dir(base, 'bundle-a', '1.0.20', subpath=None, marked=False)

    selected = select_live_version_dir(base / 'bundle-a', lambda d: (d / _SUBPATH).exists())

    assert selected == newest_eligible, (
        f'a saturated cache must resolve to the newest eligible dir '
        f'{newest_eligible!r}, got {selected!r}'
    )
    assert capsys.readouterr().err == '', (
        'the marker-free selector must emit no degraded / saturation stderr line'
    )


# --------------------------------------------------------------------------- #
# (c) A genuinely broken cache fails LOUDLY (the matched negative control)
# --------------------------------------------------------------------------- #


def test_broken_cache_with_no_eligible_candidate_fails_loudly(tmp_path):
    """D6(c). A genuinely broken cache — version dirs present but NONE carrying
    the requested subpath — resolves to ``None``, never to some arbitrary
    newest dir. This is the matched negative control that stops the marker-free
    fix from degrading into a resolver that always finds *something*.
    """
    base = tmp_path / 'cache'
    _version_dir(base, 'bundle-a', '1.0.0', subpath=None, marked=True)
    _version_dir(base, 'bundle-a', '1.0.10', subpath=None, marked=False)

    selected = select_live_version_dir(base / 'bundle-a', lambda d: (d / _SUBPATH).exists())

    assert selected is None, (
        f'a cache with no eligible candidate must fail loudly (None), got {selected!r}'
    )


def test_unreadable_bundle_dir_fails_loudly(tmp_path):
    """D6(c), companion. A nonexistent bundle dir resolves to ``None``."""
    selected = select_live_version_dir(tmp_path / 'does-not-exist', lambda d: (d / _SUBPATH).exists())
    assert selected is None


# --------------------------------------------------------------------------- #
# (d) No production source under our tree WRITES the shared marker
# --------------------------------------------------------------------------- #


def _writes_marker(source: str) -> list[str]:
    """Return descriptions of every ``.orphaned_at`` write in ``source``.

    A write is a ``.write_text(...)`` / ``.write_bytes(...)`` call whose target
    object is a path expression containing the ``.orphaned_at`` literal — the
    exact shape ``(version_dir / '.orphaned_at').write_text(...)`` took. Reads
    (``.exists()``) are deliberately not flagged: D6(d) governs writes only.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    def _mentions_marker(node: ast.AST) -> bool:
        return any(
            isinstance(sub, ast.Constant) and sub.value == _MARKER_NAME
            for sub in ast.walk(node)
        )

    hits: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ('write_text', 'write_bytes')
            and _mentions_marker(node.func.value)
        ):
            hits.append(f'{node.func.attr}() on a .orphaned_at path at line {node.lineno}')
    return hits


def test_no_production_source_writes_the_shared_marker():
    """D6(d). No production script under ``marketplace/bundles/**/scripts`` writes
    the shared ``.orphaned_at`` field. The field has a foreign co-producer
    (Claude Code's plugin GC); this repository no longer writes it at all, so a
    write reappearing anywhere under our tree is a regression.
    """
    offenders: dict[str, list[str]] = {}
    for path in sorted(_BUNDLES_ROOT.glob(_SOURCE_GLOB)):
        text = path.read_text(encoding='utf-8')
        if _MARKER_NAME not in text:
            continue
        writes = _writes_marker(text)
        if writes:
            offenders[str(path.relative_to(_REPO_ROOT))] = writes

    assert not offenders, (
        'The shared .orphaned_at marker must not be written by any production source '
        f'under our tree (it has a foreign co-producer). Offending write(s): {offenders}'
    )
