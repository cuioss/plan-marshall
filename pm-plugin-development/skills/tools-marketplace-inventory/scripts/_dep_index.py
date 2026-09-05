#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Dependency index building and querying for resolve-dependencies.py.

Provides functions to:
- Discover all components in marketplace
- Build a dependency index from all components
- Query forward and reverse dependencies
- Detect circular dependencies
"""

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from _dep_detection import (
    VERB_BEARING_EXCLUSIONS,
    ComponentId,
    Dependency,
    DependencyType,
    detect_all_dependencies,
    extract_frontmatter,
)
from argparse_surface import derive_surface, is_derivable, resolve_executor
from marketplace_bundles import resolve_bundles_root
from marketplace_paths import get_bundle_cache_roots

# Constants for path discovery
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'


class AstCache:
    """Parse-once cache of ``ast.parse`` results for ``.py`` files.

    The index substrate indexes frontmatter; the parsed Python AST is the one
    piece it does not provide. This cache memoizes ``ast.parse`` so each file is
    read and parsed at most once per scan run: repeated ``get_tree`` calls for
    the same path return the identical cached ``ast.Module`` object (or ``None``
    when the file is unreadable or fails to parse — the negative result is
    cached too, so a bad file is never re-parsed). ``parse_count`` records how
    many successful ``ast.parse`` calls ran, letting callers assert the
    parse-once invariant.
    """

    def __init__(self) -> None:
        self._trees: dict[str, ast.Module | None] = {}
        self.parse_count = 0

    def get_tree(self, file_path: Path) -> ast.Module | None:
        """Return the cached AST for ``file_path``, parsing it on first request.

        Reads the file as UTF-8 and parses with ``filename=str(file_path)`` —
        byte-identical to the per-analyzer ``ast.parse`` calls this cache
        replaces. ``None`` is returned and cached for unreadable or unparseable
        files so the same path is never processed twice.
        """
        key = str(file_path)
        if key in self._trees:
            return self._trees[key]
        tree = self._parse(file_path)
        self._trees[key] = tree
        return tree

    def _parse(self, file_path: Path) -> ast.Module | None:
        try:
            source = file_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return None
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return None
        self.parse_count += 1
        return tree


@dataclass
class ComponentInfo:
    """Information about a discovered component."""

    component_id: ComponentId
    file_path: Path
    frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyIndex:
    """Index of all dependencies between components."""

    components: dict[str, ComponentInfo] = field(default_factory=dict)
    forward_deps: dict[str, list[Dependency]] = field(default_factory=lambda: defaultdict(list))
    reverse_deps: dict[str, list[Dependency]] = field(default_factory=lambda: defaultdict(list))
    implements_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_component(self, component: ComponentInfo) -> None:
        """Add a component to the index."""
        key = component.component_id.to_notation()
        self.components[key] = component

    def add_dependency(self, dep: Dependency) -> None:
        """Add a dependency to the index."""
        source_key = dep.source.to_notation()
        target_key = dep.target.to_notation()

        self.forward_deps[source_key].append(dep)
        self.reverse_deps[target_key].append(dep)

        # Track implements relationships specially
        if dep.dep_type == DependencyType.IMPLEMENTS:
            self.implements_index[target_key].append(source_key)

    def get_forward_deps(self, notation: str) -> list[Dependency]:
        """Get direct dependencies of a component."""
        return self.forward_deps.get(notation, [])

    def get_reverse_deps(self, notation: str) -> list[Dependency]:
        """Get components that depend on this component."""
        return self.reverse_deps.get(notation, [])

    def get_implementations(self, interface_notation: str) -> list[str]:
        """Get all components implementing an interface."""
        return self.implements_index.get(interface_notation, [])

    def resolve_transitive_deps(
        self,
        notation: str,
        max_depth: int = 10,
        dep_types: set[DependencyType] | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve transitive dependencies.

        Args:
            notation: Component notation to resolve
            max_depth: Maximum depth to traverse
            dep_types: Filter to specific dependency types

        Returns:
            List of dicts with target, depth, via fields
        """
        result: list[dict[str, Any]] = []
        visited: set[str] = {notation}
        queue: list[tuple[str, int, str]] = [(notation, 0, '')]

        while queue:
            current, depth, via = queue.pop(0)
            if depth >= max_depth:
                continue

            for dep in self.forward_deps.get(current, []):
                if dep_types and dep.dep_type not in dep_types:
                    continue

                target_key = dep.target.to_notation()
                if target_key not in visited:
                    visited.add(target_key)
                    new_via = current if depth > 0 else ''
                    result.append(
                        {
                            'target': target_key,
                            'depth': depth + 1,
                            'via': new_via,
                        }
                    )
                    queue.append((target_key, depth + 1, current))

        return result

    def detect_circular_deps(self) -> list[list[str]]:
        """Detect circular dependencies.

        Returns:
            List of cycles, where each cycle is a list of component notations
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.forward_deps.get(node, []):
                target = dep.target.to_notation()
                if target not in visited:
                    dfs(target, path.copy())
                elif target in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(target)
                    cycle = path[cycle_start:] + [target]
                    # Normalize cycle to avoid duplicates
                    min_idx = cycle.index(min(cycle))
                    normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                    if normalized not in cycles:
                        cycles.append(normalized)

            rec_stack.remove(node)

        for component in self.components:
            if component not in visited:
                dfs(component, [])

        return cycles


def discover_components(base_path: Path) -> list[ComponentInfo]:
    """Discover all components in a marketplace directory.

    Args:
        base_path: Path to marketplace/bundles or similar

    Returns:
        List of discovered components
    """
    components: list[ComponentInfo] = []

    # Find all bundles (directories with .claude-plugin/plugin.json)
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        bundle_name = _extract_bundle_name(bundle_dir)

        # Discover agents
        agents_dir = bundle_dir / 'agents'
        if agents_dir.is_dir():
            for agent_file in agents_dir.glob('*.md'):
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='agent',
                    name=agent_file.stem,
                )
                content = agent_file.read_text()
                frontmatter = extract_frontmatter(content).fields
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=agent_file,
                        frontmatter=frontmatter,
                    )
                )

        # Discover commands
        commands_dir = bundle_dir / 'commands'
        if commands_dir.is_dir():
            for command_file in commands_dir.glob('*.md'):
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='command',
                    name=command_file.stem,
                )
                content = command_file.read_text()
                frontmatter = extract_frontmatter(content).fields
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=command_file,
                        frontmatter=frontmatter,
                    )
                )

        # Discover skills and scripts
        skills_dir = bundle_dir / 'skills'
        if skills_dir.is_dir():
            for skill_md in skills_dir.glob('*/SKILL.md'):
                skill_dir = skill_md.parent
                skill_name = skill_dir.name

                # Add skill
                content = skill_md.read_text()
                frontmatter = extract_frontmatter(content).fields
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='skill',
                    name=skill_name,
                )
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=skill_md,
                        frontmatter=frontmatter,
                    )
                )

                # Add scripts (excluding private modules)
                scripts_dir = skill_dir / 'scripts'
                if scripts_dir.is_dir():
                    for script_file in scripts_dir.glob('*.py'):
                        # Skip private modules (underscore prefix)
                        if script_file.name.startswith('_'):
                            continue
                        script_id = ComponentId(
                            bundle=bundle_name,
                            component_type='script',
                            name=script_file.stem,
                            parent_skill=skill_name,
                        )
                        components.append(
                            ComponentInfo(
                                component_id=script_id,
                                file_path=script_file,
                                frontmatter={},
                            )
                        )

                    for script_file in scripts_dir.glob('*.sh'):
                        if script_file.name.startswith('_'):
                            continue
                        script_id = ComponentId(
                            bundle=bundle_name,
                            component_type='script',
                            name=script_file.stem,
                            parent_skill=skill_name,
                        )
                        components.append(
                            ComponentInfo(
                                component_id=script_id,
                                file_path=script_file,
                                frontmatter={},
                            )
                        )

    return components


def _extract_bundle_name(bundle_dir: Path) -> str:
    """Extract bundle name, handling versioned plugin-cache structure.

    For versioned structure (plugin-cache): .../plan-marshall/0.1-BETA/ -> "plan-marshall"
    For non-versioned structure (marketplace): .../plan-marshall/ -> "plan-marshall"
    """
    name = bundle_dir.name
    # If name looks like a version, use parent name
    if re.match(r'^\d+\.\d+', name):
        return bundle_dir.parent.name
    return name


# Sub-document directories under a skill that hold markdown reference material.
#
# DELIBERATELY NARROWER than the dependency-edge-source walk in
# :func:`iter_skill_subdoc_edge_sources`. This constant defines the
# plugin-doctor LINT POPULATION (consumed by :func:`enumerate_skill_files`,
# whose downstream framework passes lint every file it returns), while the edge
# walk answers a different question — *where can a dependency edge be written*.
# Widening this tuple to every sub-directory kind present on disk would silently
# widen what plugin-doctor lints; that is a separate, opt-in change. The two
# enumerations diverge by decision, not by oversight.
SKILL_SUBDOC_DIRS = ('references', 'standards', 'workflow', 'templates')


@dataclass
class SkillFile:
    """An enumerated file belonging to a skill (markdown or script).

    ``kind`` is one of ``skill_md`` (the skill's SKILL.md), ``subdoc`` (a markdown
    sub-document under references/standards/workflow/templates), or ``script`` (a
    ``.py``/``.sh`` file under ``scripts/`` — private ``_``-prefixed modules
    included). Downstream framework passes (AST cache, single-pass runner) consume
    this enumeration instead of re-globbing the bundle tree.
    """

    bundle: str
    skill: str
    kind: str
    file_path: Path


def enumerate_skill_files(base_path: Path) -> list[SkillFile]:
    """Enumerate every skill SKILL.md, markdown sub-document, and script file.

    Walks each bundle's ``skills/`` tree once and returns the full file set the
    plugin-doctor framework needs: the skill definition, its sub-documents, and
    its scripts (including private ``_``-prefixed Python modules). Pure
    enumeration — no parsing — so callers layer their own frontmatter/AST passes.
    """
    files: list[SkillFile] = []

    for plugin_json in sorted(base_path.rglob('.claude-plugin/plugin.json')):
        bundle_dir = plugin_json.parent.parent
        bundle_name = _extract_bundle_name(bundle_dir)

        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue

        for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
            skill_dir = skill_md.parent
            skill_name = skill_dir.name

            files.append(SkillFile(bundle_name, skill_name, 'skill_md', skill_md))

            for subdoc_dir_name in SKILL_SUBDOC_DIRS:
                subdoc_dir = skill_dir / subdoc_dir_name
                if subdoc_dir.is_dir():
                    for md_file in sorted(subdoc_dir.rglob('*.md')):
                        files.append(SkillFile(bundle_name, skill_name, 'subdoc', md_file))

            scripts_dir = skill_dir / 'scripts'
            if scripts_dir.is_dir():
                for script_file in sorted(scripts_dir.glob('*.py')):
                    files.append(SkillFile(bundle_name, skill_name, 'script', script_file))
                for script_file in sorted(scripts_dir.glob('*.sh')):
                    files.append(SkillFile(bundle_name, skill_name, 'script', script_file))

    return files


def iter_skill_subdoc_edge_sources(base_path: Path) -> list[tuple[ComponentId, Path]]:
    """Return ``(owning skill, markdown file)`` for every skill sub-document.

    The enumeration is **name-free**: every ``.md`` under ``skills/<skill>/**``
    except those under ``scripts/``, derived by walking the tree rather than from
    a directory-name list. A new sub-directory kind therefore contributes edges
    automatically instead of silently re-opening a blind spot. ``SKILL.md``
    itself is excluded — it is already scanned as the skill component's own
    definition file.

    Deliberately does NOT reuse :data:`SKILL_SUBDOC_DIRS`: that constant is the
    plugin-doctor lint population, and widening it to match this walk would widen
    what plugin-doctor lints. See the comment at that constant for the full
    rationale.
    """
    sources: list[tuple[ComponentId, Path]] = []

    for plugin_json in sorted(base_path.rglob('.claude-plugin/plugin.json')):
        bundle_dir = plugin_json.parent.parent
        bundle_name = _extract_bundle_name(bundle_dir)

        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue

        for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
            skill_dir = skill_md.parent
            owner = ComponentId(
                bundle=bundle_name,
                component_type='skill',
                name=skill_dir.name,
            )
            for md_file in sorted(skill_dir.rglob('*.md')):
                if md_file == skill_md:
                    continue
                if 'scripts' in md_file.relative_to(skill_dir).parts[:-1]:
                    continue
                sources.append((owner, md_file))

    return sources


def _normalize_segment(segment: str) -> str:
    """Fold a notation segment to one case style so `_`/`-` variants compare equal."""
    return segment.replace('_', '-')


def _is_misspelled_script_segment(target: ComponentId) -> bool:
    """True when the script segment is the skill's own name in the wrong case style.

    `plugin-doctor`'s `manage-findings-invocation-invalid` rule names this defect:
    the executor keys on the third segment literally, so an underscored spelling of
    the script does not resolve. It is a misspelling, never a verb.
    """
    return bool(target.parent_skill) and _normalize_segment(target.name) == _normalize_segment(
        target.parent_skill or ''
    )


def _entry_script_candidates(skill: str) -> tuple[str, ...]:
    """Return the names an entry script may carry for `skill`, in probe order.

    Nine skills in this marketplace spell the entry script with underscores
    (`plan-doctor:plan_doctor`, `extension-api:extension_api`, …), so assuming
    filename == skill name exactly is the assumption plugin-doctor's own rule
    catalogue rejects.
    """
    return (skill, skill.replace('-', '_'), skill.replace('_', '-'))


def _verb_is_registered(entry: ComponentId, verb: str, executor: Path | None) -> bool:
    """Whether ``verb`` is a subcommand the entry script actually registers.

    The retarget's premise is that the notation's third segment names a VERB of
    the entry script. That premise was previously never tested, so a notation
    naming a verb the script does not register resolved clean — the reference was
    broken and the validator said nothing.

    Ground truth is the script's own ``--help``-derived argparse surface, via the
    shared ``argparse_surface`` module plugin-doctor's ``manage-invocation-invalid``
    rule already uses; the accept-set therefore includes registered ALIASES, not
    just canonical spellings.

    ⛔ Returns True when no surface can be derived — no executor, a script whose
    ``--help`` fails, or a probe budget exhausted. Absence of a surface is absence
    of EVIDENCE, not evidence of absence, and manufacturing an unresolved row from
    a failed probe would report a broken reference that is not broken. This
    mirrors the established idiom in `_analyze_manage_invocation.derive_script_tree`,
    where a non-derivable surface means "no ground truth here, emit nothing".
    """
    if executor is None:
        return True
    surface = derive_surface(entry.to_notation(), executor)
    if not is_derivable(surface):
        return True
    return verb in surface.known_subcommands()


class Retarget(NamedTuple):
    """The outcome of attempting to resolve a notation onto an entry script.

    Three distinct outcomes, which a bare ``ComponentId | None`` collapsed into
    two: ``entry`` set (retargeted), and — both previously ``None`` — no entry
    script to retarget onto versus an entry script that exists but does not
    register the verb. The second of those is a BROKEN REFERENCE that must be
    reported, while the first is merely a notation this resolver has nothing to
    say about, so the caller has to tell them apart.
    """

    entry: ComponentId | None
    verb_unregistered: bool = False


def _entry_script_for_subcommand(
    index: DependencyIndex,
    target: ComponentId,
    dep_type: DependencyType,
    executor: Path | None = None,
) -> Retarget:
    """Return the skill's entry script when ``target``'s final segment is a subcommand.

    A skill exposes ONE entry script named after the skill itself
    (``manage-execution-manifest:manage-execution-manifest``) and dispatches its
    verbs as subcommands of it. Documentation names those verbs in the same
    three-part shape — a `compose` verb in the script segment — and the detector,
    which builds a script ``ComponentId`` from any three-part notation, then
    looks for a *script* of that name and finds none.

    The reference is real; only the segment it lands on is a verb rather than a
    filename. So it resolves to the entry script that owns the verb, and the
    edge is recorded against that script. When the skill has NO same-named entry
    script the notation is genuinely wrong (the script segment names neither a
    script nor a dispatchable verb) and ``None`` is returned so it stays
    unresolved — plugin-doctor is that case, since a `validate` verb in the
    script segment names neither a script nor a dispatchable verb of its entry
    script ``doctor-marketplace``.

    Returns a :class:`Retarget`. ``verb_unregistered`` is set only on the one
    outcome where the entry script EXISTS but does not register the verb — the
    caller uses it to keep that row disclosed rather than dropped.
    """
    if dep_type is not DependencyType.SCRIPT_NOTATION:
        # Only a written notation can carry a verb in its script segment. A
        # PYTHON_IMPORT target names a MODULE — `extension_base` is a different
        # file from `extension_api`, not a verb of it — so retargeting an import
        # onto a same-named entry script would silently resolve a stale module
        # mapping that ought to be reported.
        return Retarget(None)
    if target.component_type != 'script' or not target.parent_skill:
        return Retarget(None)
    # A script segment that is the skill's own name in the WRONG CASE STYLE is a
    # misspelled script reference, not a verb. `plugin-doctor`'s
    # `manage-findings-invocation-invalid` rule names this exact defect — the
    # executor keys on the third segment literally, so
    # an underscored script segment does not resolve — and
    # retargeting it onto the entry script would suppress a finding the
    # repository deliberately raises.
    if _is_misspelled_script_segment(target):
        return Retarget(None)
    for entry_name in _entry_script_candidates(target.parent_skill):
        entry = ComponentId(
            bundle=target.bundle,
            component_type='script',
            name=entry_name,
            parent_skill=target.parent_skill,
        )
        if entry.to_notation() in index.components:
            # The entry script exists; the retarget is only sound if it actually
            # registers the verb. When it does not, the notation names neither a
            # script nor a dispatchable verb, so it stays unresolved rather than
            # resolving onto a script that would reject the call.
            if not _verb_is_registered(entry, target.name, executor):
                return Retarget(None, verb_unregistered=True)
            return Retarget(entry)
    return Retarget(None)


#: Why a dependency stayed unresolved. Every unresolved row carries exactly one.
#:
#: The partition is the one the SKILL's "Precision of `validate`" section already
#: draws in prose: a target whose bundle IS indexed names a component that
#: genuinely does not exist and is directly actionable, while a target whose
#: bundle is not indexed at all may be an npm script name, a time literal or a
#: Gradle coordinate and is not yet triaged. Reporting both under one undifferentiated
#: `unresolved` list forced every reader to re-derive that split by hand, and a
#: count over the union measured neither class.
UNRESOLVED_REASON_UNKNOWN_BUNDLE = 'unknown-bundle'
UNRESOLVED_REASON_MISSING_COMPONENT = 'missing-component'
#: The entry script exists and was found, but does not register the named verb.
#: Distinct from `missing-component`: the component IS there, so a reader chasing
#: this row must look at the script's verb set rather than at whether it exists.
UNRESOLVED_REASON_UNREGISTERED_VERB = 'unregistered-verb'

#: Every reason a row can carry — published so a consumer can render a complete
#: per-reason breakdown including the classes that scored zero. A breakdown built
#: only from observed rows cannot distinguish "no row fell in this class" from
#: "this class is not computed", which is the ambiguity this constant removes.
UNRESOLVED_REASONS: tuple[str, ...] = (
    UNRESOLVED_REASON_UNKNOWN_BUNDLE,
    UNRESOLVED_REASON_MISSING_COMPONENT,
    UNRESOLVED_REASON_UNREGISTERED_VERB,
)


def indexed_bundles(index: DependencyIndex) -> set[str]:
    """The set of bundle names the index actually discovered components for.

    Derived from the discovered components rather than from a directory listing,
    so it names the bundles this run INDEXED — the only population against which
    "the bundle is unknown" is a meaningful statement.
    """
    return {info.component_id.bundle for info in index.components.values()}


def unresolved_reason(dep: Dependency, bundles: set[str]) -> str:
    """Classify an unresolved dependency into :data:`UNRESOLVED_REASONS`.

    `bundles` is the indexed-bundle set from :func:`indexed_bundles`, passed in
    rather than recomputed per row so the classification of every row in a run is
    made against one and the same population.
    """
    if dep.verb_unregistered:
        # Tested first: the target component EXISTS, so the bundle-membership
        # test below would label it `missing-component` and send the reader to
        # look for a script that is there.
        return UNRESOLVED_REASON_UNREGISTERED_VERB
    if dep.target.bundle in bundles:
        return UNRESOLVED_REASON_MISSING_COMPONENT
    return UNRESOLVED_REASON_UNKNOWN_BUNDLE


def _index_dependencies_from(
    index: DependencyIndex,
    file_path: Path,
    component_id: ComponentId,
    dep_types: set[DependencyType] | None,
    executor: Path | None = None,
) -> None:
    """Detect dependencies in ``file_path`` and record them under ``component_id``.

    Shared by the per-component pass and the sub-document edge-source pass; the
    two differ only in whether the scanned file IS the component's own
    definition. A target absent from the index resolves to the owning skill's
    entry script when its final segment is a subcommand of it
    (:func:`_entry_script_for_subcommand`), and is marked unresolved otherwise.
    """
    for dep in detect_all_dependencies(file_path, component_id, dep_types):
        if dep.target.to_notation() not in index.components:
            # The retarget is attempted before the drop, but ONLY for a shape whose
            # third segment can still be a verb. A plain notation qualifies, and so
            # does a decision-log prefix — a step id is very often a verb of the
            # skill's entry script, and dropping it on shape alone hid exactly what
            # this module calls a real reference. A sub-document path, placeholder,
            # or build coordinate never qualifies: its third segment is a directory
            # or a meta-variable, and letting those retarget manufactured five false
            # edges onto `manage-lessons`.
            may_be_verb = not dep.exclusion or dep.exclusion in VERB_BEARING_EXCLUSIONS
            retarget = (
                _entry_script_for_subcommand(index, dep.target, dep.dep_type, executor)
                if may_be_verb
                else Retarget(None)
            )
            if retarget.entry is not None:
                if retarget.entry.to_notation() == component_id.to_notation():
                    # An entry script documenting its OWN verbs. Retargeting that
                    # onto itself would manufacture a self-loop and report it as a
                    # circular dependency; a script is not dependent on itself.
                    continue
                dep.target = retarget.entry
            elif retarget.verb_unregistered:
                # ⛔ Tested BEFORE the exclusion drop, and that order is the whole
                # point. The entry script exists and the verb does not — a broken
                # reference this validator can now prove. Falling through to the
                # drop below would delete exactly the finding the check was added
                # to surface, so the row is disclosed as unresolved instead.
                dep.verb_unregistered = True
                dep.resolved = False
            elif dep.exclusion:
                # An excluded SHAPE that names no component and no verb — the
                # only case in which a match is discarded.
                continue
            else:
                dep.resolved = False
        index.add_dependency(dep)


def build_dependency_index(
    base_path: Path,
    dep_types: set[DependencyType] | None = None,
) -> DependencyIndex:
    """Build a complete dependency index from a marketplace directory.

    Args:
        base_path: Path to marketplace/bundles or similar
        dep_types: Filter to specific dependency types

    Returns:
        Populated DependencyIndex
    """
    index = DependencyIndex()

    # Resolved ONCE per index build, not per retarget: the executor is what makes
    # the entry script's argparse surface probeable, and re-resolving it per row
    # would let the ground truth differ between rows of the same run. `None` means
    # no executor is reachable, in which case verb validation abstains entirely.
    # `base_path` is `marketplace/bundles`, so its parent is the `marketplace`
    # directory `resolve_executor` documents as an accepted root.
    executor = resolve_executor(base_path.parent)

    # Discover all components
    components = discover_components(base_path)

    # Add components to index
    for component in components:
        index.add_component(component)

    # Detect dependencies for each component
    for component in components:
        _index_dependencies_from(
            index, component.file_path, component.component_id, dep_types, executor
        )

    # Sub-documents are EDGE SOURCES, never components: an edge cited in
    # ``workflow/light-lane.md`` is attributed to the skill that owns the file.
    # ``ComponentId`` has no sub-document type, and inventing one would change
    # the component namespace that deps / rdeps / tree / validate all key on.
    for owner_id, subdoc_path in iter_skill_subdoc_edge_sources(base_path):
        _index_dependencies_from(index, subdoc_path, owner_id, dep_types, executor)

    return index


def _first_existing_bundle_cache_root() -> Path | None:
    """Return the first deployed-bundle cache root that exists on disk, else None.

    Routes through the platform-runtime ``layout bundle-cache-root`` op (via
    ``marketplace_paths.get_bundle_cache_roots``), so deployed-bundle discovery
    covers both the Claude ``~/.claude/plugins/cache/plan-marshall`` cache root
    and the OpenCode user-global skill roots. The literal Claude cache subpath
    is no longer hardcoded here.
    """
    for root in get_bundle_cache_roots():
        candidate = Path(root).expanduser()
        if candidate.is_dir():
            return candidate
    return None


def get_base_path(scope: str) -> Path:
    """Determine base path based on scope.

    Args:
        scope: One of 'auto', 'marketplace', 'plugin-cache', 'project'

    Returns:
        Path to the base directory

    Raises:
        FileNotFoundError: If the specified scope cannot be found
    """
    # Script-relative path to bundles root, validated by anchor helper.
    marketplace_from_script = resolve_bundles_root(Path(__file__))

    if scope == 'auto':
        # Try marketplace first
        if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
            return Path.cwd() / MARKETPLACE_BUNDLES_PATH
        if marketplace_from_script.is_dir():
            return marketplace_from_script
        # Fall back to the deployed-bundle cache (target-aware roots).
        cache = _first_existing_bundle_cache_root()
        if cache is not None:
            return cache
        raise FileNotFoundError(f'Neither {MARKETPLACE_BUNDLES_PATH} nor plugin cache found.')

    if scope == 'marketplace':
        if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
            return Path.cwd() / MARKETPLACE_BUNDLES_PATH
        if marketplace_from_script.is_dir():
            return marketplace_from_script
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} directory not found')

    if scope == 'plugin-cache':
        cache = _first_existing_bundle_cache_root()
        if cache is not None:
            return cache
        raise FileNotFoundError(
            f'Plugin cache not found in any of: {", ".join(get_bundle_cache_roots())}'
        )

    if scope == 'project':
        project_claude = Path.cwd() / CLAUDE_DIR
        if project_claude.is_dir():
            return project_claude
        raise FileNotFoundError(f'Project .claude directory not found: {project_claude}')

    raise ValueError(f'Invalid scope: {scope}')
