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

import pytest
from marketplace_bundles import select_live_version_dir

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_REPO_ROOT = PROJECT_ROOT
_BUNDLES_ROOT = _REPO_ROOT / 'marketplace' / 'bundles'
_MARKER_NAME = '.orphaned_at'

#: Sweep glob for (d). ``**`` after ``scripts/`` is load-bearing: the previous
#: ``scripts/*.py`` reached only files sitting DIRECTLY in a ``scripts/``
#: directory, so every module under an organised subdirectory
#: (``script-shared/scripts/build/`` and its three siblings) was outside the
#: sweep entirely — a blind spot the sweep reported nothing about, because a
#: population it never visited produces no offenders.
_SOURCE_GLOB = '**/skills/**/scripts/**/*.py'

#: Floor on the swept population. The sweep's assertion is "no member offends",
#: which passes over an EMPTY population while checking nothing — so the size is
#: asserted first. The floor sits well under the currently-derived recursive
#: count so ordinary bundle churn never trips it; it exists to catch a glob that
#: stopped matching, not to pin a number.
_MIN_SWEPT_SOURCES = 300

#: Modules known to mention the marker today. The sweep must at minimum still be
#: LOOKING AT these — a glob change that silently stopped reaching one of them
#: would leave the offender check green while no longer covering the only files
#: where an offence could plausibly appear.
_KNOWN_MARKER_MENTIONING_MODULES = frozenset(
    {
        'cache_retention.py',
        'marketplace_bundles.py',
        'generate_executor.py',
        '_plugin_pin_trap.py',
    }
)

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


#: Path methods that WRITE through a path object. ``touch`` is a write: it
#: creates the marker, and the marker is existence-only — creating it IS the
#: whole act the guard forbids, even though it writes no bytes.
_MARKER_WRITE_METHODS = frozenset({'write_text', 'write_bytes', 'touch'})

#: Mode characters that make an ``open()`` a write. ``open(p)`` with no mode
#: defaults to reading and is NOT flagged — the guard governs writes only.
_WRITE_MODE_CHARS = ('w', 'a', 'x', '+')


def _assign_target_name(node: ast.AST) -> str | None:
    """Return the single ``Name`` a simple assignment binds, else ``None``."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _marker_constant_names(tree: ast.AST) -> set[str]:
    """Names bound to the marker STRING itself (``ORPHAN_MARKER_NAME = '...'``).

    Without this the detector only sees the literal, so the ordinary practice of
    naming a constant once and referring to it everywhere hides every subsequent
    use. The scan is over the whole tree rather than only module level, because a
    constant bound inside a function indirects exactly as effectively.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        target = _assign_target_name(node)
        value = getattr(node, 'value', None)
        if target and isinstance(value, ast.Constant) and value.value == _MARKER_NAME:
            names.add(target)
    return names


def _mentions_marker(node: ast.AST, constant_names: set[str]) -> bool:
    """Whether ``node`` names the marker — as a literal or through a constant."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and sub.value == _MARKER_NAME:
            return True
        if isinstance(sub, ast.Name) and sub.id in constant_names:
            return True
    return False


def _marker_aliases(tree: ast.AST, constant_names: set[str]) -> set[str]:
    """Names bound to an expression that builds the marker PATH.

    ``marker = version_dir / '.orphaned_at'`` followed by ``marker.write_text(…)``
    is the same write as the inline form, split across two statements. A detector
    that only matches the inline shape is defeated by a local variable.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        target = _assign_target_name(node)
        value = getattr(node, 'value', None)
        if target and value is not None and _mentions_marker(value, constant_names):
            aliases.add(target)
    return aliases


def _open_mode(node: ast.Call, mode_index: int) -> str | None:
    """Return the mode string an ``open`` call was given, or ``None`` if absent.

    ``mode_index`` differs between the two call forms and getting it wrong makes
    the check silently answer "no mode given" — which reads as a harmless default
    read: builtin ``open(path, mode)`` carries the mode SECOND, while the method
    form ``path.open(mode)`` carries it FIRST, the path being the receiver.
    """
    if len(node.args) > mode_index:
        positional = node.args[mode_index]
        if isinstance(positional, ast.Constant):
            return positional.value if isinstance(positional.value, str) else None
    for keyword in node.keywords:
        if keyword.arg == 'mode' and isinstance(keyword.value, ast.Constant):
            return keyword.value.value if isinstance(keyword.value.value, str) else None
    return None


def _is_write_mode(mode: str | None) -> bool:
    """A mode that can create or modify. ``None`` (the default) reads."""
    return mode is not None and any(char in mode for char in _WRITE_MODE_CHARS)


def _targets_marker(node: ast.AST, constant_names: set[str], aliases: set[str]) -> bool:
    """Whether an expression resolves to the marker path, inline or by alias."""
    if isinstance(node, ast.Name) and node.id in aliases:
        return True
    return _mentions_marker(node, constant_names)


def _writes_in_tree(tree: ast.AST, label: str) -> list[str]:
    """Every marker write in one already-parsed tree, in source order."""
    constant_names = _marker_constant_names(tree)
    aliases = _marker_aliases(tree, constant_names)
    prefix = f'{label}: ' if label else ''
    hits: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Builtin open(marker_path, 'w') — the stdlib route around pathlib.
        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            if (
                node.args
                and _targets_marker(node.args[0], constant_names, aliases)
                and _is_write_mode(_open_mode(node, 1))
            ):
                hits.append(f'{prefix}open() in write mode on a .orphaned_at path at line {node.lineno}')
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not _targets_marker(node.func.value, constant_names, aliases):
            continue
        if node.func.attr in _MARKER_WRITE_METHODS:
            hits.append(f'{prefix}{node.func.attr}() on a .orphaned_at path at line {node.lineno}')
        elif node.func.attr == 'open' and _is_write_mode(_open_mode(node, 0)):
            hits.append(f'{prefix}.open() in write mode on a .orphaned_at path at line {node.lineno}')

    hits.extend(_template_writes(tree, constant_names, label))
    return sorted(hits)


def _template_writes(tree: ast.AST, constant_names: set[str], label: str) -> list[str]:
    """Descend into string constants that are themselves emitted Python.

    A generator holds the code it emits as a string constant
    (``generate_executor``'s resolver template is exactly that shape), so a write
    inside one is invisible to an AST walk of the OUTER module — the write is
    text there, not a call. Each module-level string constant carrying the marker
    is re-parsed and re-scanned, and its hits are labelled with the constant's
    name so an offence points at the template rather than at a line number in a
    file that does not contain the call.

    A constant that is not valid Python (ordinary prose, a docstring) simply does
    not parse and is skipped, so nothing but real embedded code is examined.
    """
    del constant_names  # the embedded tree resolves its own constants
    hits: list[str] = []
    for node in ast.walk(tree):
        target = _assign_target_name(node)
        value = getattr(node, 'value', None)
        if target is None or not isinstance(value, ast.Constant):
            continue
        text = value.value
        if not isinstance(text, str) or _MARKER_NAME not in text or text.strip() == _MARKER_NAME:
            continue
        try:
            embedded = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        inner_label = f'{label}[{target}]' if label else f'[{target}]'
        hits.extend(_writes_in_tree(embedded, inner_label))
    return hits


def _writes_marker(source: str, label: str = '') -> list[str]:
    """Return descriptions of every ``.orphaned_at`` write in ``source``.

    A write is any of: ``.write_text()`` / ``.write_bytes()`` / ``.touch()`` on a
    path expression that resolves to the marker, or an ``open()`` of one in a
    write mode — reached inline, through a variable the marker path was bound to,
    or through a named constant holding the marker string. Writes inside a string
    constant that is itself emitted Python are found by re-parsing that constant.

    Reads (``.exists()``) are deliberately not flagged: D6(d) governs writes only,
    and the marker is legitimately CONSULTED by this repository.

    Every widening here closes a shape the previous inline-only detector could
    not see. That mattered because the sweep's verdict is "no offenders found",
    and a detector blind to a shape reports exactly the same clean result whether
    or not that shape is present.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    return _writes_in_tree(tree, label)


def _swept_sources() -> list[Path]:
    """The production sources the marker sweep visits, ``__pycache__`` excluded."""
    return sorted(
        path
        for path in _BUNDLES_ROOT.glob(_SOURCE_GLOB)
        if '__pycache__' not in path.parts
    )


def _recursive_source_population() -> list[Path]:
    """Every bundle script at ANY depth under a skill's ``scripts/`` directory.

    Computed by WALKING and filtering on path shape, deliberately not by reusing
    ``_SOURCE_GLOB`` — comparing the sweep's glob against itself would assert
    nothing. This is the second, independent answer the sweep's population is
    checked against.
    """
    found: list[Path] = []
    for path in _BUNDLES_ROOT.rglob('*.py'):
        parts = path.relative_to(_BUNDLES_ROOT).parts
        if '__pycache__' in parts or 'skills' not in parts or 'scripts' not in parts:
            continue
        if parts.index('scripts') > parts.index('skills'):
            found.append(path)
    return sorted(found)


#: Each entry is one WRITE shape the detector must see. They are held as a table
#: so a shape cannot be added to the detector without declaring the source that
#: exercises it — and, through the matched read table below, without declaring
#: the read form that must still be left alone.
_WRITE_SHAPES: dict[str, str] = {
    'inline': "from pathlib import Path\n(Path('d') / '.orphaned_at').write_text('x')\n",
    'inline_bytes': "from pathlib import Path\n(Path('d') / '.orphaned_at').write_bytes(b'x')\n",
    'inline_touch': "from pathlib import Path\n(Path('d') / '.orphaned_at').touch()\n",
    'alias_write_text': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "marker.write_text('x')\n"
    ),
    'alias_touch': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "marker.touch()\n"
    ),
    'named_constant': (
        "from pathlib import Path\n"
        "ORPHAN_MARKER_NAME = '.orphaned_at'\n"
        "(Path('d') / ORPHAN_MARKER_NAME).write_text('x')\n"
    ),
    'named_constant_alias': (
        "from pathlib import Path\n"
        "ORPHAN_MARKER_NAME = '.orphaned_at'\n"
        "marker = Path('d') / ORPHAN_MARKER_NAME\n"
        "marker.touch()\n"
    ),
    'builtin_open_write': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "with open(marker, 'w') as handle:\n"
        "    handle.write('x')\n"
    ),
    'builtin_open_append_kwarg': (
        "from pathlib import Path\n"
        "with open(Path('d') / '.orphaned_at', mode='a') as handle:\n"
        "    handle.write('x')\n"
    ),
    'path_open_write': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "with marker.open('w') as handle:\n"
        "    handle.write('x')\n"
    ),
    'template_embedded': (
        "TEMPLATE = '''\\\n"
        "from pathlib import Path\n"
        "(Path('d') / '.orphaned_at').write_text('x')\n"
        "'''\n"
    ),
}

#: Matched READ controls — the same shapes, consuming rather than producing. The
#: guard governs writes only and this repository legitimately CONSULTS the
#: marker, so a detector that flagged these would be unusable; without the
#: controls, every widening above could be satisfied by one that flagged
#: everything.
_READ_SHAPES: dict[str, str] = {
    'inline_exists': "from pathlib import Path\n(Path('d') / '.orphaned_at').exists()\n",
    'alias_exists': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "if marker.exists():\n"
        "    pass\n"
    ),
    'alias_read_text': (
        "from pathlib import Path\n"
        "marker = Path('d') / '.orphaned_at'\n"
        "marker.read_text()\n"
    ),
    'builtin_open_default_mode': (
        "from pathlib import Path\n"
        "with open(Path('d') / '.orphaned_at') as handle:\n"
        "    handle.read()\n"
    ),
    'builtin_open_explicit_read': (
        "from pathlib import Path\n"
        "with open(Path('d') / '.orphaned_at', 'r') as handle:\n"
        "    handle.read()\n"
    ),
    'unrelated_write': "from pathlib import Path\n(Path('d') / 'other.json').write_text('x')\n",
    'prose_constant': "NOTE = 'the .orphaned_at marker is existence-only'\n",
}


@pytest.mark.parametrize('shape', sorted(_WRITE_SHAPES))
def test_writes_marker_detects_every_write_shape(shape):
    """Each write shape produces at least one hit.

    The pre-change detector matched only ``inline`` and ``inline_bytes``; every
    other row here was a write it reported nothing about. Because the sweep's
    verdict is "no offenders found", a blind spot and a clean tree are
    indistinguishable in its output — which is why the shapes are enumerated
    against synthetic source rather than inferred from the real tree being green.
    """
    hits = _writes_marker(_WRITE_SHAPES[shape], label=shape)

    assert hits, f'{shape}: expected at least one detected marker write, got none'


@pytest.mark.parametrize('shape', sorted(_READ_SHAPES))
def test_control_writes_marker_ignores_read_and_unrelated_shapes(shape):
    """CONTROL: reads, unrelated writes and prose produce NO hit.

    Without this the parametrised write cases above would all be satisfied by a
    detector that returned a hit for every file mentioning the marker — which
    would fail the real-tree sweep immediately, on four files that only read it.
    """
    hits = _writes_marker(_READ_SHAPES[shape], label=shape)

    assert hits == [], f'{shape}: expected no detected write, got {hits}'


def test_a_template_hit_is_labelled_with_the_constant_that_carries_it():
    """An embedded-code hit names the template, not just a line number.

    The line number belongs to the parsed STRING, not to the enclosing file, so
    an unlabelled hit would point a reader at a line whose content is unrelated.
    """
    hits = _writes_marker(_WRITE_SHAPES['template_embedded'], label='gen.py')

    assert hits
    assert all('gen.py[TEMPLATE]' in hit for hit in hits), hits


def test_writes_marker_tolerates_unparseable_source():
    """A file that is not valid Python yields no hits rather than raising.

    The sweep reads every matched file; one that fails to parse must not take the
    whole guard down with it.
    """
    assert _writes_marker('def broken(:\n') == []


def test_the_swept_population_is_bound_and_non_vacuous():
    """The sweep's population is bound BEFORE anything is asserted about it.

    ``assert not offenders`` passes over an empty population while checking
    nothing, and the glob that produces that population had silently stopped
    reaching an entire subtree. Three bindings close that: a floor on the size, a
    superset check against the modules known to mention the marker, and equality
    with an independently-walked recursive population.
    """
    swept = _swept_sources()

    assert len(swept) >= _MIN_SWEPT_SOURCES, (
        f'the marker sweep visited only {len(swept)} source file(s) under '
        f'{_BUNDLES_ROOT} via {_SOURCE_GLOB!r} — below the {_MIN_SWEPT_SOURCES} '
        'floor, so its "no offenders" verdict would be about almost nothing'
    )

    names = {path.name for path in swept}
    missing = sorted(_KNOWN_MARKER_MENTIONING_MODULES - names)
    assert not missing, (
        f'the sweep no longer reaches module(s) known to mention {_MARKER_NAME}: '
        f'{missing}. Those are the only files where an offence could plausibly '
        'appear, so a sweep that misses them is green for the wrong reason'
    )


def test_the_sweep_glob_reaches_every_nested_script():
    """``_SOURCE_GLOB`` matches the independently-walked recursive population.

    The pre-change ``scripts/*.py`` matched only direct children, so every module
    in an organised subdirectory was unreachable. Asserting set EQUALITY (not a
    count) names the exact files if the two ever disagree again.
    """
    swept = set(_swept_sources())
    walked = set(_recursive_source_population())

    assert swept == walked, (
        f'the sweep glob {_SOURCE_GLOB!r} and an independent recursive walk '
        f'disagree; only-in-glob={sorted(p.name for p in swept - walked)}, '
        f'only-in-walk={sorted(p.name for p in walked - swept)}'
    )


def test_no_production_source_writes_the_shared_marker():
    """D6(d). No production script under ``marketplace/bundles/**/scripts`` writes
    the shared ``.orphaned_at`` field. The field has a foreign co-producer
    (Claude Code's plugin GC); this repository no longer writes it at all, so a
    write reappearing anywhere under our tree is a regression.

    The population this verdict covers is published in the assertion message: a
    clean result means nothing without the size of the set it was clean over.
    """
    swept = _swept_sources()
    offenders: dict[str, list[str]] = {}
    for path in swept:
        text = path.read_text(encoding='utf-8')
        if _MARKER_NAME not in text:
            continue
        writes = _writes_marker(text, label=path.name)
        if writes:
            offenders[str(path.relative_to(_REPO_ROOT))] = writes

    assert not offenders, (
        'The shared .orphaned_at marker must not be written by any production source '
        f'under our tree (it has a foreign co-producer). Swept {len(swept)} source '
        f'file(s); offending write(s): {offenders}'
    )
