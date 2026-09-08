#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for module discovery utilities (via extension_base public API)."""

from pathlib import Path

import _build_discover as _build_discover_mod
import pytest

EXCLUDE_DIRS = _build_discover_mod.EXCLUDE_DIRS
README_PATTERNS = _build_discover_mod.README_PATTERNS
ModuleBase = _build_discover_mod.ModuleBase
ModulePaths = _build_discover_mod.ModulePaths
build_module_base = _build_discover_mod.build_module_base
discover_descriptors = _build_discover_mod.discover_descriptors
find_readme = _build_discover_mod.find_readme

#: A path no filesystem in the test environment provides, so both accessors that
#: take one are driven against a genuinely absent root.
NONEXISTENT_PATH = '/nonexistent/path'


def test_readme_patterns_defined():
    """README_PATTERNS should contain expected patterns."""
    assert 'README.md' in README_PATTERNS
    assert 'README.adoc' in README_PATTERNS
    assert 'README.txt' in README_PATTERNS
    assert 'README' in README_PATTERNS


def test_exclude_dirs_defined():
    """EXCLUDE_DIRS should contain expected directories."""
    assert '.git' in EXCLUDE_DIRS
    assert 'node_modules' in EXCLUDE_DIRS
    assert 'target' in EXCLUDE_DIRS
    assert 'build' in EXCLUDE_DIRS
    assert '__pycache__' in EXCLUDE_DIRS


def test_module_paths_creation():
    """ModulePaths can be created with all fields."""
    paths = ModulePaths(module='core', descriptor='core/pom.xml', readme='core/README.md')
    assert paths.module == 'core'
    assert paths.descriptor == 'core/pom.xml'
    assert paths.readme == 'core/README.md'


def test_module_paths_readme_none():
    """ModulePaths can have None readme."""
    paths = ModulePaths(module='core', descriptor='core/pom.xml', readme=None)
    assert paths.readme is None


def test_module_base_creation():
    """ModuleBase can be created with name and paths."""
    paths = ModulePaths(module='core', descriptor='core/pom.xml', readme=None)
    base = ModuleBase(name='core', paths=paths)
    assert base.name == 'core'
    assert base.paths.module == 'core'


def test_module_base_to_dict():
    """to_dict returns proper structure."""
    paths = ModulePaths(module='core', descriptor='core/pom.xml', readme='core/README.md')
    base = ModuleBase(name='core', paths=paths)
    result = base.to_dict()

    assert result['name'] == 'core'
    assert result['paths']['module'] == 'core'
    assert result['paths']['descriptor'] == 'core/pom.xml'
    assert result['paths']['readme'] == 'core/README.md'


def _touch_descriptors(root: Path, relative_dirs: list[str], descriptor: str) -> None:
    """Create ``descriptor`` inside each of ``relative_dirs`` under ``root``.

    An empty string names the root itself, which is how the tables below express
    "a descriptor at the top level" without a second column.
    """
    for relative in relative_dirs:
        directory = root / relative if relative else root
        directory.mkdir(parents=True, exist_ok=True)
        (directory / descriptor).touch()


#: ``(directories holding a descriptor, expected count)``. Every row is the same
#: walk over the same descriptor name, so only the tree laid down and the number
#: of hits it should yield vary.
_DESCRIPTOR_COUNT_CASES = [
    ([], 0),
    ([''], 1),
    (['', 'core', 'core/api'], 3),
]

_DESCRIPTOR_COUNT_IDS = [
    'no-descriptor-anywhere',
    'one-descriptor-at-the-root',
    'descriptors-at-three-nesting-levels',
]


@pytest.mark.parametrize(
    'relative_dirs,expected_count', _DESCRIPTOR_COUNT_CASES, ids=_DESCRIPTOR_COUNT_IDS
)
def test_discover_descriptors_finds_every_descriptor_in_the_tree(
    tmp_path: Path, relative_dirs: list[str], expected_count: int
):
    _touch_descriptors(tmp_path, relative_dirs, 'pom.xml')

    result = discover_descriptors(str(tmp_path), 'pom.xml')

    assert len(result) == expected_count
    assert all(path.name == 'pom.xml' for path in result)


def test_discover_descriptors_depth_ordering(tmp_path: Path):
    """Results are sorted by depth, root first."""
    root = tmp_path.resolve()
    _touch_descriptors(root, ['deep/nested', '', 'shallow'], 'pom.xml')

    result = discover_descriptors(str(root), 'pom.xml')

    depths = [len(path.relative_to(root).parts) for path in result]
    assert depths == sorted(depths)


#: Excluded names whose row needs a shape other than the default flat ``{name}``
#: holding a ``pom.xml``, keyed by the excluded name:
#: ``(directory the walk must not enter, descriptor filename)``. ``node_modules``
#: keeps the package-inside-node_modules shape a real npm tree has, which a flat
#: row would not exercise.
_EXCLUDED_DIR_SHAPES = {
    'node_modules': ('node_modules/some-package', 'package.json'),
}

#: ``(directory the walk must not enter, descriptor filename)``, one row per
#: member of ``EXCLUDE_DIRS``. Derived from that set rather than restated, so a
#: name added to it is swept here without an edit — a hand-written table cannot
#: fail for a member it does not happen to name. Sorted because ``EXCLUDE_DIRS``
#: is a set and the row order would otherwise vary between runs. The first path
#: segment of each row is the excluded name.
_EXCLUDED_DIR_CASES = [
    _EXCLUDED_DIR_SHAPES.get(name, (name, 'pom.xml')) for name in sorted(EXCLUDE_DIRS)
]

_EXCLUDED_DIR_IDS = [
    relative_dir.split('/', 1)[0].strip('._').replace('_', '-')
    for relative_dir, _ in _EXCLUDED_DIR_CASES
]


def test_excluded_dir_sweep_covers_every_exclude_dir():
    """The excluded-directory sweep states every member of ``EXCLUDE_DIRS``.

    The sweep is derived from that set, so this asserts the derivation did not
    silently drop or duplicate a member — and the non-emptiness guard is what
    stops an ``EXCLUDE_DIRS`` emptied by a refactor from turning the sweep into
    zero rows that pass by collecting nothing.
    """
    assert EXCLUDE_DIRS, 'EXCLUDE_DIRS is empty — the sweep below would collect no rows'
    swept = {relative_dir.split('/', 1)[0] for relative_dir, _ in _EXCLUDED_DIR_CASES}
    assert swept == set(EXCLUDE_DIRS)
    assert len(_EXCLUDED_DIR_IDS) == len(set(_EXCLUDED_DIR_IDS)), 'row ids must be unique'


@pytest.mark.parametrize(
    'excluded_relative_dir,descriptor', _EXCLUDED_DIR_CASES, ids=_EXCLUDED_DIR_IDS
)
def test_discover_descriptors_skips_excluded_directories(
    tmp_path: Path, excluded_relative_dir: str, descriptor: str
):
    """A descriptor inside an excluded directory is never reported.

    The result is compared RELATIVE to the fixture root. The absolute path runs
    through the repository's own basetemp, which itself sits under a directory
    named in ``EXCLUDE_DIRS`` — so a substring check against the absolute path
    would match an ancestor rather than anything the walk returned.
    """
    _touch_descriptors(tmp_path, [excluded_relative_dir, ''], descriptor)

    result = discover_descriptors(str(tmp_path), descriptor)

    assert [path.relative_to(tmp_path.resolve()) for path in result] == [Path(descriptor)]


def test_discover_descriptors_nonexistent():
    """Returns empty list for nonexistent directory."""
    assert discover_descriptors(NONEXISTENT_PATH, 'pom.xml') == []


#: ``(directory holding the descriptor, module name, module path, descriptor
#: path)``. The root row is the special case the other two contrast with: it is
#: named ``default`` and its module path is ``.`` rather than a directory name.
_MODULE_BASE_CASES = [
    ('', 'default', '.', 'pom.xml'),
    ('core', 'core', 'core', 'core/pom.xml'),
    ('parent/child', 'child', 'parent/child', 'parent/child/pom.xml'),
]

_MODULE_BASE_IDS = [
    'descriptor-at-the-root',
    'descriptor-one-level-down',
    'descriptor-two-levels-down',
]


@pytest.mark.parametrize(
    'relative_dir,expected_name,expected_module,expected_descriptor',
    _MODULE_BASE_CASES,
    ids=_MODULE_BASE_IDS,
)
def test_build_module_base_names_the_module_after_its_own_directory(
    tmp_path: Path,
    relative_dir: str,
    expected_name: str,
    expected_module: str,
    expected_descriptor: str,
):
    _touch_descriptors(tmp_path, [relative_dir], 'pom.xml')
    descriptor_path = (tmp_path / relative_dir / 'pom.xml') if relative_dir else (tmp_path / 'pom.xml')

    base = build_module_base(str(tmp_path), str(descriptor_path))

    assert base.name == expected_name
    assert base.paths.module == expected_module
    assert base.paths.descriptor == expected_descriptor


def test_build_module_base_with_readme(tmp_path: Path):
    """Finds README when present."""
    _touch_descriptors(tmp_path, ['core'], 'pom.xml')
    (tmp_path / 'core' / 'README.md').touch()

    base = build_module_base(str(tmp_path), str(tmp_path / 'core' / 'pom.xml'))

    assert base.paths.readme == 'core/README.md'


def test_build_module_base_without_readme(tmp_path: Path):
    """readme is None when not present."""
    _touch_descriptors(tmp_path, ['core'], 'pom.xml')

    base = build_module_base(str(tmp_path), str(tmp_path / 'core' / 'pom.xml'))

    assert base.paths.readme is None


#: ``(README files present, the one that is reported)``. The last row is the
#: preference case: both candidates exist and ``.md`` wins, which is the only
#: thing that distinguishes an ordered pattern list from an arbitrary one.
_FIND_README_CASES = [
    (['README.md'], 'README.md'),
    (['README.adoc'], 'README.adoc'),
    (['README.txt'], 'README.txt'),
    (['README'], 'README'),
    (['README.md', 'README.adoc'], 'README.md'),
]

_FIND_README_IDS = [
    'md',
    'adoc',
    'txt',
    'no-extension',
    'md-wins-when-md-and-adoc-both-exist',
]


@pytest.mark.parametrize('present,expected', _FIND_README_CASES, ids=_FIND_README_IDS)
def test_find_readme_reports_the_first_matching_pattern(
    tmp_path: Path, present: list[str], expected: str
):
    for name in present:
        (tmp_path / name).touch()

    assert find_readme(str(tmp_path)) == expected


def test_find_readme_none(tmp_path: Path):
    """Returns None when no README exists."""
    assert find_readme(str(tmp_path)) is None


def test_find_readme_nonexistent():
    """Returns None for nonexistent directory."""
    assert find_readme(NONEXISTENT_PATH) is None
