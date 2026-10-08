# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every file a skill routes to is present in each target's emitted skill.

A ``SKILL.md`` sends its reader to other files of the same skill directory. A
target that emits the manifest but not the file it routes to ships a skill that
points at nothing. Each component-tree target is generated from the real
``marketplace/bundles/`` tree, every route an emitted ``SKILL.md`` carries is
extracted, and the routes that name a file of the source skill must name a file
of the emitted skill too.

The expected set is read off the source tree, never off a list of directory
names: a route counts when the source skill holds a file at that path.

The sweep and ``test_a_removed_directory_is_reported_as_a_missing_route`` are a
matched pair. The sweep alone is consistent with an extractor that finds
nothing; the control alone is consistent with a tree that is broken everywhere.
Weakening either one voids what the other proves.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath

import deployed_layout
import pytest

from conftest import PROJECT_ROOT
from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.component_targets import (
    component_tree_target_names,
    excluded_emission_roots,
    is_under_any,
    iter_component_manifests,
)

# One worker generates the three trees once, instead of each worker that is
# handed a test of this module regenerating all of them.
pytestmark = pytest.mark.xdist_group('skill-route-emission')

BUNDLES = Path(PROJECT_ROOT) / 'marketplace' / 'bundles'

TREE_TARGETS = sorted(component_tree_target_names())
assert TREE_TARGETS, 'no component-tree target is registered, so TREE_TARGETS parametrizes nothing'

#: Route forms the extractor does not parse. A file reached only through one of
#: these is outside what this module checks.
UNPARSED_ROUTE_FORMS = (
    'bundle notation: {bundle}:{skill}/workflow/{file}.md',
    'cross-skill relative path: ../{skill}/{subdir}/{file}',
    'a full-line Read: directive after a target rewrote it into its own tool-call wording',
    'a path assembled from a placeholder: standards/{name}.md',
    'a route carried by a file other than SKILL.md',
)

#: The skill and route the negative control removes and expects to be reported.
CONTROL_SKILL = ('plan-marshall', 'plan-marshall')
CONTROL_DIRECTORY = 'workflow'
CONTROL_ROUTE = 'workflow/planning.md'

_MARKDOWN_LINK_RE = re.compile(r'\]\(\s*<?([^)\s>#]+)')
_BACKTICKED_PATH_RE = re.compile(r'`([\w.-]+(?:/[\w.-]+)+)`')
_READ_TOKEN_RE = re.compile(r'\bRead:?[ \t]+([\w./-]+)')
_SKILL_RELATIVE_RE = re.compile(r'[\w.-]+(?:/[\w.-]+)*')


@dataclass(frozen=True)
class _SourceSkill:
    bundle: str
    name: str
    directory: Path
    bundle_dir: Path


@dataclass(frozen=True)
class _RouteReport:
    route_count: int
    missing: tuple[str, ...]


def _route_candidates(text: str) -> set[str]:
    """Return every skill-relative path ``text`` routes to, in any parsed form."""
    found = {
        match.group(1)
        for pattern in (_MARKDOWN_LINK_RE, _BACKTICKED_PATH_RE, _READ_TOKEN_RE)
        for match in pattern.finditer(text)
    }
    return {
        candidate
        for candidate in found
        if _SKILL_RELATIVE_RE.fullmatch(candidate) and '..' not in PurePosixPath(candidate).parts
    }


@cache
def _source_skills() -> dict[str, _SourceSkill]:
    """Index every source skill by the directory names a target may emit it under.

    Two keys per skill: its bundle-relative source path, which a target that
    mirrors the bundle tree keeps, and the flat ``{bundle}-{skill}`` name.
    """
    index: dict[str, _SourceSkill] = {}
    for plugin_json in sorted(BUNDLES.glob('*/.claude-plugin/plugin.json')):
        bundle_dir = plugin_json.parents[1]
        for _manifest, emission_root in iter_component_manifests(bundle_dir):
            if not emission_root.is_dir():
                continue
            skill = _SourceSkill(bundle_dir.name, emission_root.name, emission_root, bundle_dir)
            index[emission_root.relative_to(BUNDLES).as_posix()] = skill
            index[deployed_layout.flat_skill_dir_name(skill.bundle, skill.name)] = skill
    assert index, f'no source skill found under {BUNDLES}'
    return index


def _emitted_skills(tree: Path) -> dict[tuple[str, str], Path]:
    """Map ``(bundle, skill)`` to the directory ``tree`` emitted that skill into."""
    index = _source_skills()
    emitted: dict[tuple[str, str], Path] = {}
    for manifest in sorted(tree.rglob('SKILL.md')):
        relative = manifest.parent.relative_to(tree)
        skill = index.get(relative.as_posix()) or index.get(relative.name)
        if skill is not None:
            emitted[(skill.bundle, skill.name)] = manifest.parent
    return emitted


@cache
def _scoped_away(bundle_dir: Path, target: str) -> frozenset[Path]:
    return excluded_emission_roots(bundle_dir, target)


def _expected_routes(emitted_skill_dir: Path, skill: _SourceSkill, target: str) -> set[str]:
    """Return the routes of the emitted manifest that name a file of the source skill.

    A file a ``targets:`` declaration scopes away from ``target`` is exempt: it
    is absent from that target on purpose.
    """
    text = (emitted_skill_dir / 'SKILL.md').read_text(encoding='utf-8')
    excluded = _scoped_away(skill.bundle_dir, target)
    return {
        route
        for route in _route_candidates(text)
        if (skill.directory / route).is_file()
        and not is_under_any((skill.directory / route).relative_to(skill.bundle_dir), excluded)
    }


def _missing_routes(emitted_skill_dir: Path, skill: _SourceSkill, target: str) -> list[str]:
    """Return the expected routes ``emitted_skill_dir`` holds no file for."""
    return sorted(
        route
        for route in _expected_routes(emitted_skill_dir, skill, target)
        if not (emitted_skill_dir / route).is_file()
    )


def _source_skill(key: tuple[str, str]) -> _SourceSkill:
    return _source_skills()[deployed_layout.flat_skill_dir_name(*key)]


@pytest.fixture(scope='module')
def emitted_trees(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Generate every component-tree target from the real bundles, once per module."""
    root = tmp_path_factory.mktemp('skill-route-emission')
    trees: dict[str, Path] = {}
    for name in TREE_TARGETS:
        trees[name] = root / name
        TARGET_REGISTRY[name]().generate(BUNDLES, trees[name])
    return trees


@pytest.fixture(scope='module')
def route_reports(emitted_trees: dict[str, Path]) -> dict[str, _RouteReport]:
    """Sweep every emitted skill of every target, once per module."""
    reports: dict[str, _RouteReport] = {}
    for target, tree in emitted_trees.items():
        route_count = 0
        missing: list[str] = []
        for key, emitted_skill_dir in sorted(_emitted_skills(tree).items()):
            skill = _source_skill(key)
            route_count += len(_expected_routes(emitted_skill_dir, skill, target))
            missing.extend(
                f'{skill.bundle}:{skill.name} -> {route}' for route in _missing_routes(emitted_skill_dir, skill, target)
            )
        reports[target] = _RouteReport(route_count, tuple(missing))
    return reports


@pytest.mark.parametrize(
    ('text', 'route'),
    [
        ('see [the outline flow](workflow/planning-outline.md) first', 'workflow/planning-outline.md'),
        ('see [Step 0](workflow/planning.md#step-0) first', 'workflow/planning.md'),
        ('the rules live in `standards/operations.md`', 'standards/operations.md'),
        ('| `list` | `Read workflow/planning.md` | List all plans |', 'workflow/planning.md'),
        ('Read: standards/agent-behavior-rules.md', 'standards/agent-behavior-rules.md'),
        ('a loose file: [extension](extension.py)', 'extension.py'),
    ],
    ids=['markdown-link', 'markdown-link-with-anchor', 'backticked-path', 'read-token', 'read-directive', 'root-file'],
)
def test_route_form_is_extracted(text: str, route: str):
    """Each parsed route form yields the skill-relative path it names."""
    assert route in _route_candidates(text)


@pytest.mark.parametrize(
    'text',
    ['see [the sibling](../other-skill/SKILL.md)', 'see [the site](https://example.org/a/b.md)'],
    ids=['leaves-the-skill', 'external-url'],
)
def test_text_naming_no_skill_relative_path_yields_no_route(text: str):
    """A path that leaves the skill directory, and a URL, are not skill-relative routes."""
    assert _route_candidates(text) == set()


@pytest.mark.parametrize('target', TREE_TARGETS)
def test_route_population_is_not_empty(target: str, route_reports: dict[str, _RouteReport]):
    """The sweep extracts routes for every target, so a clean result is a measured one."""
    assert route_reports[target].route_count > 0, f'no route was extracted from any SKILL.md emitted by {target}'


@pytest.mark.parametrize('target', TREE_TARGETS)
def test_every_routed_file_is_emitted(target: str, route_reports: dict[str, _RouteReport]):
    """A file an emitted ``SKILL.md`` routes to is present in that target's emitted skill."""
    assert route_reports[target].missing == (), f'{target} emitted a SKILL.md routing to a file it did not emit'


@pytest.mark.parametrize('target', TREE_TARGETS)
def test_a_removed_directory_is_reported_as_a_missing_route(
    target: str, emitted_trees: dict[str, Path], tmp_path: Path
):
    """An emitted skill stripped of a routed directory is reported as missing that route."""
    broken = tmp_path / 'broken-skill'
    shutil.copytree(_emitted_skills(emitted_trees[target])[CONTROL_SKILL], broken)
    shutil.rmtree(broken / CONTROL_DIRECTORY)

    missing = _missing_routes(broken, _source_skill(CONTROL_SKILL), target)

    assert CONTROL_ROUTE in missing
