#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Attribution of a ``discover --force`` rewrite of ``.plan/project-architecture/``.

``discover --force`` rewrites the whole descriptor tree through one atomic swap.
Part of that rewrite can be structural knowledge the plan's tree carries (a
module added or removed, a changed extension set) and part of it can be the
tool migrating documents it wrote under an older contract (a generation header
back-fill, a concept ``type`` back-fill, a dotted ``key_packages`` key re-keyed
to its repo-relative path). This module is the single home of the vocabulary
that tells the two apart, and of the pure functions that apply it:

* :data:`DELTA_CLASSES` — every delta class with its attribution;
* :func:`classify_delta` — decomposes one (pre-state, regenerated) pair per
  document into classes and reduces them to a verdict;
* :func:`build_plan_projection` / :func:`build_migration_projection` — the
  staged tree content that carries only the requested kind of change, with every
  untouched document carried as its original bytes;
* :func:`match_rekeys` — the ``key_packages`` re-key matcher, shared with the
  descriptor regression check.

Nothing here performs I/O: callers read the pre-state, pass it in, and write
whatever projection they receive.
"""

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from _architecture_core import (
    CONCEPT_TYPE_FIELD,
    GENERATION_FIELD,
    LEGACY_CONCEPT_TYPE,
    unknown_generation,
)
from constants import DIR_PER_MODULE_ENRICHED, FILE_PROJECT_META

# =============================================================================
# Vocabulary
# =============================================================================

ATTRIBUTION_PLAN = 'plan'
ATTRIBUTION_MIGRATION = 'migration'
ATTRIBUTION_UNDECIDABLE = 'undecidable'

CLASS_MODULE_ADDED = 'module_added'
CLASS_MODULE_REMOVED = 'module_removed'
CLASS_EXTENSIONS_USED_CHANGED = 'extensions_used_changed'
CLASS_GENERATION_BACKFILL = 'generation_backfill'
CLASS_CONCEPT_TYPE_BACKFILL = 'concept_type_backfill'
CLASS_KEY_PACKAGES_REKEY = 'key_packages_rekey'
CLASS_UNCLASSIFIED = 'unclassified'

# The class table. Declaration order is the reporting order.
DELTA_CLASSES: dict[str, str] = {
    CLASS_MODULE_ADDED: ATTRIBUTION_PLAN,
    CLASS_MODULE_REMOVED: ATTRIBUTION_PLAN,
    CLASS_EXTENSIONS_USED_CHANGED: ATTRIBUTION_PLAN,
    CLASS_GENERATION_BACKFILL: ATTRIBUTION_MIGRATION,
    CLASS_CONCEPT_TYPE_BACKFILL: ATTRIBUTION_MIGRATION,
    CLASS_KEY_PACKAGES_REKEY: ATTRIBUTION_MIGRATION,
    CLASS_UNCLASSIFIED: ATTRIBUTION_UNDECIDABLE,
}

VERDICT_CLEAN = 'clean'
VERDICT_PLAN_ATTRIBUTABLE = 'plan_attributable'
VERDICT_MIGRATION_ONLY = 'migration_only'
VERDICT_MIXED = 'mixed'
VERDICT_UNDECIDABLE = 'undecidable'
VERDICT_NO_BASELINE = 'no_baseline'

VERDICTS: tuple[str, ...] = (
    VERDICT_CLEAN,
    VERDICT_PLAN_ATTRIBUTABLE,
    VERDICT_MIGRATION_ONLY,
    VERDICT_MIXED,
    VERDICT_UNDECIDABLE,
    VERDICT_NO_BASELINE,
)

APPLY_ALL = 'all'
APPLY_PLAN = 'plan'
APPLY_MIGRATION = 'migration'
APPLY_NONE = 'none'

# The ``--apply`` choices. ``none`` is an outcome (nothing was written), never a
# requested mode.
APPLY_MODES: tuple[str, ...] = (APPLY_ALL, APPLY_PLAN, APPLY_MIGRATION)

# The ``field`` an unreadable pre-state document is reported under.
UNREADABLE_FIELD = '(unreadable)'

_MODULES_FIELD = 'modules'
_EXTENSIONS_USED_FIELD = 'extensions_used'
_KEY_PACKAGES_FIELD = 'key_packages'


# =============================================================================
# Data shapes
# =============================================================================


@dataclass(frozen=True)
class TreeState:
    """The on-disk descriptor tree as the caller read it before discover wrote.

    ``meta`` is the parsed ``_project.json`` (``None`` when absent or
    unreadable) and ``meta_bytes`` its raw bytes (``None`` only when absent).
    ``document_bytes`` holds the raw bytes of every module ``enriched.json`` on
    disk; ``documents`` holds the parsed form of each one that parsed.
    """

    meta: dict[str, Any] | None
    meta_bytes: bytes | None
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    document_bytes: dict[str, bytes] = field(default_factory=dict)

    @property
    def has_baseline(self) -> bool:
        return self.meta_bytes is not None

    @property
    def unreadable_documents(self) -> frozenset[str]:
        """Modules whose document exists on disk but did not parse."""
        return frozenset(self.document_bytes) - frozenset(self.documents)


@dataclass(frozen=True)
class RekeyMatch:
    """How a ``key_packages`` map moved between two versions of one document.

    * ``rekeys`` — ``(from_key, to_key)`` pairs whose value is byte-identical;
    * ``lost`` — keys present before with neither the same key nor a re-keyed
      counterpart after;
    * ``gained`` — keys present after that pair with nothing before;
    * ``changed`` — keys present on both sides whose value differs.
    """

    rekeys: tuple[tuple[str, str], ...]
    lost: tuple[str, ...]
    gained: tuple[str, ...]
    changed: tuple[str, ...]

    @property
    def is_pure_rekey(self) -> bool:
        return bool(self.rekeys) and not (self.lost or self.gained or self.changed)


@dataclass(frozen=True)
class DeltaReport:
    """The classification of one discover rewrite.

    ``unclassified_fields`` holds ``(document, field)`` pairs, ``document`` being
    the path relative to the descriptor tree.
    """

    has_baseline: bool
    added: frozenset[str]
    removed: frozenset[str]
    document_classes: dict[str, frozenset[str]]
    index_classes: dict[str, frozenset[str]]
    project_classes: frozenset[str]
    unclassified_fields: tuple[tuple[str, str], ...]
    modules_examined: int

    @property
    def verdict(self) -> str:
        return reduce_verdict(self.classes, self.has_baseline)

    @property
    def classes(self) -> frozenset[str]:
        """Every class observed anywhere in the delta."""
        found: set[str] = set(self.project_classes)
        if self.added:
            found.add(CLASS_MODULE_ADDED)
        if self.removed:
            found.add(CLASS_MODULE_REMOVED)
        for per_module in (self.document_classes, self.index_classes):
            for module_classes in per_module.values():
                found.update(module_classes)
        return frozenset(found)

    def has_attribution(self, attribution: str) -> bool:
        return any(DELTA_CLASSES[name] == attribution for name in self.classes)

    def delta_classes(self) -> list[dict[str, Any]]:
        """The ``delta_classes[]{class,attribution,module_count}`` rows, in table order.

        ``module_count`` is the number of distinct modules the class was observed
        on. A class observed only on ``_project.json``'s top-level fields (for
        example ``extensions_used_changed``) reports ``0``.
        """
        modules_by_class: dict[str, set[str]] = {name: set() for name in DELTA_CLASSES}
        modules_by_class[CLASS_MODULE_ADDED].update(self.added)
        modules_by_class[CLASS_MODULE_REMOVED].update(self.removed)
        for per_module in (self.document_classes, self.index_classes):
            for module, module_classes in per_module.items():
                for name in module_classes:
                    modules_by_class[name].add(module)
        present = self.classes
        return [
            {'class': name, 'attribution': DELTA_CLASSES[name], 'module_count': len(modules_by_class[name])}
            for name in DELTA_CLASSES
            if name in present
        ]


# =============================================================================
# Helpers
# =============================================================================


def canonical_json(value: Any) -> str:
    """Canonical JSON form used for every byte-identity comparison."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def document_path(module_name: str) -> str:
    """Relative path of a module's concept document inside the descriptor tree."""
    return f'{module_name}/{DIR_PER_MODULE_ENRICHED}'


def _has_header(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def match_rekeys(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    bridge: Mapping[str, str] | None = None,
) -> RekeyMatch:
    """Pair the keys a ``key_packages`` map lost with the keys it gained.

    A lost key and a gained key form a re-key when their values are
    byte-identical (canonical JSON). When ``bridge`` (dotted key → bridge path)
    is supplied, the gained key must additionally be the lost key's bridge path;
    without it, pairing is by value identity alone, first match in sorted order.
    """
    lost_keys = sorted(key for key in before if key not in after)
    gained_keys = sorted(key for key in after if key not in before)
    changed = tuple(
        sorted(key for key in before if key in after and canonical_json(before[key]) != canonical_json(after[key]))
    )

    available = list(gained_keys)
    rekeys: list[tuple[str, str]] = []
    unmatched_lost: list[str] = []
    for key in lost_keys:
        value = canonical_json(before[key])
        target = None
        for candidate in available:
            if bridge is not None and bridge.get(key) != candidate:
                continue
            if canonical_json(after[candidate]) == value:
                target = candidate
                break
        if target is None:
            unmatched_lost.append(key)
            continue
        available.remove(target)
        rekeys.append((key, target))

    return RekeyMatch(
        rekeys=tuple(rekeys),
        lost=tuple(unmatched_lost),
        gained=tuple(available),
        changed=changed,
    )


# =============================================================================
# Classification
# =============================================================================


def classify_document(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    bridge: Mapping[str, str] | None = None,
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Classify the field differences between two versions of one concept document.

    Returns ``(classes, unclassified_field_names)``. Every differing field maps
    to exactly one class; a difference no migration class explains is
    ``unclassified`` and its field name is reported.
    """
    classes: set[str] = set()
    unclassified: list[str] = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name)
        new = after.get(name)
        if name in before and name in after and canonical_json(old) == canonical_json(new):
            continue
        if name == GENERATION_FIELD and not _has_header(old) and new == unknown_generation():
            classes.add(CLASS_GENERATION_BACKFILL)
        elif name == CONCEPT_TYPE_FIELD and name not in before and new == LEGACY_CONCEPT_TYPE:
            classes.add(CLASS_CONCEPT_TYPE_BACKFILL)
        elif (
            name == _KEY_PACKAGES_FIELD
            and isinstance(old, dict)
            and isinstance(new, dict)
            and match_rekeys(old, new, bridge).is_pure_rekey
        ):
            classes.add(CLASS_KEY_PACKAGES_REKEY)
        else:
            classes.add(CLASS_UNCLASSIFIED)
            unclassified.append(name)
    return frozenset(classes), tuple(unclassified)


def _classify_index_entry(
    before: Any,
    after: Mapping[str, Any],
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Classify one ``_project.json`` module index entry.

    The entry is derived from its document, so the only migration an entry can
    carry is a missing generation header receiving the header its regenerated
    document carries. An absent or non-dict entry, and any other difference,
    is ``unclassified``.
    """
    if not isinstance(before, dict):
        return frozenset({CLASS_UNCLASSIFIED}), ('',)
    classes: set[str] = set()
    unclassified: list[str] = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name)
        new = after.get(name)
        if name in before and name in after and canonical_json(old) == canonical_json(new):
            continue
        if name == GENERATION_FIELD and not _has_header(old) and _has_header(new):
            classes.add(CLASS_GENERATION_BACKFILL)
        else:
            classes.add(CLASS_UNCLASSIFIED)
            unclassified.append(name)
    return frozenset(classes), tuple(unclassified)


def reduce_verdict(classes: frozenset[str] | set[str], has_baseline: bool = True) -> str:
    """Reduce a set of observed classes to one verdict.

    ``no_baseline`` when there is no pre-state to compare against; otherwise any
    ``undecidable`` class dominates, then a plan class together with a migration
    class is ``mixed``.
    """
    if not has_baseline:
        return VERDICT_NO_BASELINE
    attributions = {DELTA_CLASSES[name] for name in classes}
    if ATTRIBUTION_UNDECIDABLE in attributions:
        return VERDICT_UNDECIDABLE
    has_plan = ATTRIBUTION_PLAN in attributions
    has_migration = ATTRIBUTION_MIGRATION in attributions
    if has_plan and has_migration:
        return VERDICT_MIXED
    if has_plan:
        return VERDICT_PLAN_ATTRIBUTABLE
    if has_migration:
        return VERDICT_MIGRATION_ONLY
    return VERDICT_CLEAN


def classify_delta(
    pre: TreeState,
    regenerated_meta: Mapping[str, Any],
    regenerated_documents: Mapping[str, Mapping[str, Any]],
    bridges: Mapping[str, Mapping[str, str]] | None = None,
) -> DeltaReport:
    """Decompose a discover rewrite, per document, into delta classes and a verdict.

    Args:
        pre: The descriptor tree as it stood on disk before discover wrote.
        regenerated_meta: The ``_project.json`` discover built.
        regenerated_documents: Every module document discover built, keyed by
            module name (the live crawl's module set).
        bridges: Per module, the dotted key → bridge path map the re-key
            migration used.

    A module is ``module_added`` when the live crawl holds it and the pre-state
    has no document for it, and ``module_removed`` when the pre-state holds it
    (document or index entry) and the crawl does not.
    """
    if not pre.has_baseline:
        return DeltaReport(
            has_baseline=False,
            added=frozenset(),
            removed=frozenset(),
            document_classes={},
            index_classes={},
            project_classes=frozenset(),
            unclassified_fields=(),
            modules_examined=0,
        )

    bridges = bridges or {}
    unclassified: list[tuple[str, str]] = []
    project_classes: set[str] = set()

    pre_meta = pre.meta
    if pre_meta is None:
        project_classes.add(CLASS_UNCLASSIFIED)
        unclassified.append((FILE_PROJECT_META, UNREADABLE_FIELD))
        pre_meta = {}

    pre_index_raw = pre_meta.get(_MODULES_FIELD)
    pre_index: dict[str, Any] = pre_index_raw if isinstance(pre_index_raw, dict) else {}
    if _MODULES_FIELD in pre_meta and not isinstance(pre_index_raw, dict):
        project_classes.add(CLASS_UNCLASSIFIED)
        unclassified.append((FILE_PROJECT_META, _MODULES_FIELD))

    regenerated_index_raw = regenerated_meta.get(_MODULES_FIELD)
    regenerated_index: Mapping[str, Any] = regenerated_index_raw if isinstance(regenerated_index_raw, dict) else {}

    new_modules = set(regenerated_documents)
    pre_documented = set(pre.document_bytes)
    pre_modules = pre_documented | set(pre_index)

    added = frozenset(new_modules - pre_documented)
    removed = frozenset(pre_modules - new_modules)
    common = sorted(new_modules & pre_documented)

    document_classes: dict[str, frozenset[str]] = {}
    index_classes: dict[str, frozenset[str]] = {}
    for module in common:
        if module in pre.unreadable_documents:
            document_classes[module] = frozenset({CLASS_UNCLASSIFIED})
            unclassified.append((document_path(module), UNREADABLE_FIELD))
        else:
            doc_classes, doc_fields = classify_document(
                pre.documents[module], regenerated_documents[module], bridges.get(module)
            )
            if doc_classes:
                document_classes[module] = doc_classes
            unclassified.extend((document_path(module), name) for name in doc_fields)

        entry_classes, entry_fields = _classify_index_entry(pre_index.get(module), regenerated_index.get(module) or {})
        if entry_classes:
            index_classes[module] = entry_classes
        unclassified.extend(
            (FILE_PROJECT_META, f'{_MODULES_FIELD}.{module}' + (f'.{name}' if name else '')) for name in entry_fields
        )

    for name in sorted((set(pre_meta) | set(regenerated_meta)) - {_MODULES_FIELD}):
        old = pre_meta.get(name)
        new = regenerated_meta.get(name)
        if name in pre_meta and name in regenerated_meta and canonical_json(old) == canonical_json(new):
            continue
        if name == _EXTENSIONS_USED_FIELD and name in pre_meta and name in regenerated_meta:
            project_classes.add(CLASS_EXTENSIONS_USED_CHANGED)
        else:
            project_classes.add(CLASS_UNCLASSIFIED)
            unclassified.append((FILE_PROJECT_META, name))

    return DeltaReport(
        has_baseline=True,
        added=added,
        removed=removed,
        document_classes=document_classes,
        index_classes=index_classes,
        project_classes=frozenset(project_classes),
        unclassified_fields=tuple(unclassified),
        modules_examined=len(pre_modules | new_modules),
    )


# =============================================================================
# Projections
# =============================================================================

# A staged tree: relative path → raw bytes (carried verbatim) or a parsed
# document the writer serializes.
StagedTree = dict[str, bytes | dict[str, Any]]


def _pre_state_tree(pre: TreeState) -> StagedTree:
    staged: StagedTree = {document_path(module): data for module, data in sorted(pre.document_bytes.items())}
    if pre.meta_bytes is not None:
        staged[FILE_PROJECT_META] = pre.meta_bytes
    return staged


def _mutable_meta(pre: TreeState) -> tuple[dict[str, Any], dict[str, Any]]:
    meta = copy.deepcopy(pre.meta) if pre.meta is not None else {}
    index = meta.get(_MODULES_FIELD)
    if not isinstance(index, dict):
        index = {}
        meta[_MODULES_FIELD] = index
    return meta, index


def build_plan_projection(
    pre: TreeState,
    regenerated_meta: Mapping[str, Any],
    regenerated_documents: Mapping[str, Mapping[str, Any]],
    report: DeltaReport,
) -> StagedTree:
    """The staged tree carrying the pre-state plus the plan classes only.

    An added module contributes its regenerated document and index entry; a
    removed module loses both; a changed extension set is taken over. Every
    other document keeps its original bytes, and ``_project.json`` keeps its
    original bytes unless a plan class changed it.
    """
    staged = _pre_state_tree(pre)
    meta, index = _mutable_meta(pre)
    regenerated_index = regenerated_meta.get(_MODULES_FIELD) or {}
    meta_changed = False

    for module in sorted(report.added):
        staged[document_path(module)] = copy.deepcopy(dict(regenerated_documents[module]))
        index[module] = copy.deepcopy(regenerated_index.get(module, {}))
        meta_changed = True

    for module in sorted(report.removed):
        staged.pop(document_path(module), None)
        if module in index:
            del index[module]
            meta_changed = True

    if CLASS_EXTENSIONS_USED_CHANGED in report.project_classes:
        meta[_EXTENSIONS_USED_FIELD] = copy.deepcopy(regenerated_meta.get(_EXTENSIONS_USED_FIELD))
        meta_changed = True

    if meta_changed:
        staged[FILE_PROJECT_META] = meta
    return staged


def build_migration_projection(
    pre: TreeState,
    regenerated_meta: Mapping[str, Any],
    regenerated_documents: Mapping[str, Mapping[str, Any]],
    report: DeltaReport,
) -> StagedTree:
    """The staged tree carrying the pre-state plus the migration classes only.

    A pre-existing document with a migration class takes its regenerated
    version, and its index entry follows it. Added modules are not written,
    removed modules are kept verbatim, and the extension set is left alone.
    Every other document keeps its original bytes.
    """
    staged = _pre_state_tree(pre)
    meta, index = _mutable_meta(pre)
    regenerated_index = regenerated_meta.get(_MODULES_FIELD) or {}
    meta_changed = False

    migrated_modules = sorted(
        module
        for module in set(report.document_classes) | set(report.index_classes)
        if any(
            DELTA_CLASSES[name] == ATTRIBUTION_MIGRATION
            for name in report.document_classes.get(module, frozenset()) | report.index_classes.get(module, frozenset())
        )
    )
    for module in migrated_modules:
        if any(
            DELTA_CLASSES[name] == ATTRIBUTION_MIGRATION for name in report.document_classes.get(module, frozenset())
        ):
            staged[document_path(module)] = copy.deepcopy(dict(regenerated_documents[module]))
        entry = regenerated_index.get(module)
        if entry is not None and canonical_json(index.get(module)) != canonical_json(entry):
            index[module] = copy.deepcopy(entry)
            meta_changed = True

    if meta_changed:
        staged[FILE_PROJECT_META] = meta
    return staged


def projection_equals_pre_state(staged: StagedTree, pre: TreeState) -> bool:
    """Whether writing ``staged`` would change nothing in the pre-state.

    Byte entries compare by bytes; parsed entries compare by canonical content
    against the parsed pre-state document.
    """
    expected = _pre_state_tree(pre)
    if set(staged) != set(expected):
        return False
    parsed_pre: dict[str, Any] = {document_path(module): doc for module, doc in pre.documents.items()}
    if pre.meta is not None:
        parsed_pre[FILE_PROJECT_META] = pre.meta
    for path, content in staged.items():
        if isinstance(content, bytes):
            if content != expected[path]:
                return False
        elif path not in parsed_pre or canonical_json(content) != canonical_json(parsed_pre[path]):
            return False
    return True


__all__ = [
    'APPLY_ALL',
    'APPLY_MIGRATION',
    'APPLY_MODES',
    'APPLY_NONE',
    'APPLY_PLAN',
    'ATTRIBUTION_MIGRATION',
    'ATTRIBUTION_PLAN',
    'ATTRIBUTION_UNDECIDABLE',
    'DELTA_CLASSES',
    'DeltaReport',
    'RekeyMatch',
    'StagedTree',
    'TreeState',
    'UNREADABLE_FIELD',
    'VERDICTS',
    'build_migration_projection',
    'build_plan_projection',
    'canonical_json',
    'classify_delta',
    'classify_document',
    'document_path',
    'match_rekeys',
    'projection_equals_pre_state',
    'reduce_verdict',
]
