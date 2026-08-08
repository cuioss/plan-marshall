# SPDX-License-Identifier: FSL-1.1-ALv2
"""Enforcement test for the existence-only ``.orphaned_at`` marker invariant.

``.orphaned_at`` is a plugin-cache marker with TWO producers writing ONE field in
TWO encodings: ours (ISO-8601 UTC, written by
``generate_executor._mark_superseded_version_dirs``) and Claude Code's own plugin
GC (raw epoch-ms). The encoding split is inert only because every consumer in this
repository reads the marker's EXISTENCE and never its content — the invariant
declared at the single read site, ``marketplace_bundles._partition_version_dirs``.
This module pins that invariant, so a future content-dependent read fails the build
instead of silently coupling this repository to a format it does not own.

The detector is POPULATION-DERIVED: it enumerates the production sources that
mention the marker and publishes the discovered population size in every assertion
message, so it can never pass vacuously from an empty scan. Files whose only
mentions are inside a docstring or comment are classified as NON-consumers but are
still COUNTED in the published population, so a silent shrink of the population is
itself a failure rather than a quiet pass. Matched controls run in both directions:
a source that parses the marker's content MUST be detected, and an existence-only
source MUST NOT be.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLES_ROOT = _REPO_ROOT / 'marketplace' / 'bundles'

#: The marker filename, exactly as both producers write it.
_MARKER_NAME = '.orphaned_at'

#: The production-source population this invariant governs. Taken verbatim from the
#: deliverable spec: ``marketplace/bundles/**/skills/**/scripts/*.py``.
_SOURCE_GLOB = '**/skills/**/scripts/*.py'

#: Attribute accesses on a marker path that CONSUME its content.
_CONTENT_READ_ATTRS = frozenset({'read_text', 'read_bytes', 'open'})

#: Attribute accesses on a marker path that WRITE its content.
_CONTENT_WRITE_ATTRS = frozenset({'write_text', 'write_bytes'})

#: Callables that turn a marker path into a parsed value.
_CONTENT_PARSE_CALLS = frozenset(
    {
        'open',
        'json.loads',
        'loads',
        'float',
        'int',
        'datetime.fromisoformat',
        'fromisoformat',
        'datetime.strptime',
        'strptime',
    }
)

#: The ONE sanctioned content-bearing site. It is allow-listed BY NAME — a single
#: named function, not a suppression pattern — so the same write in any other
#: function is still a violation.
_SANCTIONED_WRITE_FUNCTION = '_mark_superseded_version_dirs'


@dataclass
class MarkerReport:
    """The per-source verdict of one detector pass."""

    label: str
    mentions_marker: bool = False
    code_occurrences: int = 0
    violations: list[str] = field(default_factory=list)
    sanctioned_writes: list[str] = field(default_factory=list)

    @property
    def is_consumer(self) -> bool:
        """True when the marker is reached from executable code, not just prose."""
        return self.code_occurrences > 0


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Return a child -> parent map over ``tree`` (the ast module provides none)."""
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    """Return the ``id()`` of every module/class/function docstring constant."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            ids.add(id(first.value))
    return ids


def _dotted_name(node: ast.AST) -> str:
    """Render ``Name``/``Attribute`` chains as a dotted string, else ``''``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f'{base}.{node.attr}' if base else node.attr
    return ''


def _enclosing_scope(node: ast.AST, parents: dict[ast.AST, ast.AST], tree: ast.AST) -> ast.AST:
    """Return the nearest enclosing function node, or ``tree`` at module level."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef):
            return current
        current = parents.get(current)
    return tree


def _scope_name(scope: ast.AST) -> str:
    """Name the scope a use was found in (``'<module>'`` at module level)."""
    if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        return scope.name
    return '<module>'


def _marker_path_node(constant: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    """Widen a ``'.orphaned_at'`` constant to the whole path-join expression.

    ``version_dir / '.orphaned_at'`` is a ``BinOp`` with ``Div``; walking up through
    consecutive joins yields the node that actually denotes the marker path.
    """
    node = constant
    parent = parents.get(node)
    while isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
        node = parent
        parent = parents.get(node)
    return node


def _classify_use(
    marker_node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    tree: ast.AST,
    label: str,
    report: MarkerReport,
) -> None:
    """Record a violation or a sanctioned write for one marker-path expression."""
    scope = _enclosing_scope(marker_node, parents, tree)
    scope_name = _scope_name(scope)
    parent = parents.get(marker_node)
    lineno = getattr(marker_node, 'lineno', 0)

    if isinstance(parent, ast.Attribute):
        _record_attribute_use(parent.attr, label, lineno, scope_name, report)
        return

    if isinstance(parent, ast.Call) and any(arg is marker_node for arg in parent.args):
        callee = _dotted_name(parent.func)
        if callee in _CONTENT_PARSE_CALLS:
            report.violations.append(
                f'{label}:{lineno}: marker path passed to {callee}() in {scope_name}() — '
                f'the marker is existence-only, its content must never be parsed'
            )
        return

    alias = _assigned_alias(marker_node, parents)
    if alias:
        _check_alias_uses(scope, alias, label, scope_name, report)


def _record_attribute_use(attr: str, label: str, lineno: int, scope_name: str, report: MarkerReport) -> None:
    """Classify an attribute access made directly on a marker path."""
    if attr in _CONTENT_READ_ATTRS:
        report.violations.append(
            f'{label}:{lineno}: marker path .{attr}() in {scope_name}() — '
            f'the marker is existence-only, its content must never be read'
        )
        return
    if attr in _CONTENT_WRITE_ATTRS and scope_name != _SANCTIONED_WRITE_FUNCTION:
        report.violations.append(
            f'{label}:{lineno}: marker path .{attr}() in {scope_name}() — the only '
            f'sanctioned content-bearing site is {_SANCTIONED_WRITE_FUNCTION}()'
        )
        return
    if attr in _CONTENT_WRITE_ATTRS:
        report.sanctioned_writes.append(f'{label}:{lineno}: {scope_name}().{attr}()')


def _assigned_alias(marker_node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    """Return the variable name a marker path is bound to, or ``''``."""
    parent = parents.get(marker_node)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and isinstance(parent.targets[0], ast.Name):
        return parent.targets[0].id
    if isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
        return parent.target.id
    return ''


def _check_alias_uses(scope: ast.AST, alias: str, label: str, scope_name: str, report: MarkerReport) -> None:
    """Flag content-consuming uses of a variable bound to the marker path."""
    for node in ast.walk(scope):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == alias:
            _record_attribute_use(node.attr, label, node.lineno, scope_name, report)
        elif isinstance(node, ast.Call):
            callee = _dotted_name(node.func)
            if callee not in _CONTENT_PARSE_CALLS:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id == alias:
                    report.violations.append(
                        f'{label}:{node.lineno}: marker path passed to {callee}() in '
                        f'{scope_name}() — the marker is existence-only, its content '
                        f'must never be parsed'
                    )


def analyse_source(source: str, label: str) -> MarkerReport:
    """Run the existence-only detector over one Python source text."""
    report = MarkerReport(label=label)
    report.mentions_marker = _MARKER_NAME in source
    if not report.mentions_marker:
        return report

    tree = ast.parse(source)
    parents = _parent_map(tree)
    docstring_ids = _docstring_constant_ids(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or node.value != _MARKER_NAME:
            continue
        if id(node) in docstring_ids:
            continue
        report.code_occurrences += 1
        _classify_use(_marker_path_node(node, parents), parents, tree, label, report)

    return report


def _population() -> list[Path]:
    """Enumerate the production sources that mention the marker, sorted by path."""
    found = [
        path
        for path in sorted(_BUNDLES_ROOT.glob(_SOURCE_GLOB))
        if _MARKER_NAME in path.read_text(encoding='utf-8')
    ]
    return found


def _reports() -> list[MarkerReport]:
    """Analyse every member of the population."""
    return [
        analyse_source(path.read_text(encoding='utf-8'), str(path.relative_to(_REPO_ROOT)))
        for path in _population()
    ]


def _population_summary(reports: list[MarkerReport]) -> str:
    """Render the published population size and its consumer split."""
    consumers = [r.label for r in reports if r.is_consumer]
    non_consumers = [r.label for r in reports if not r.is_consumer]
    return (
        f'scanned population = {len(reports)} production source(s) matching '
        f'{_SOURCE_GLOB!r} under marketplace/bundles that mention {_MARKER_NAME!r} '
        f'({len(consumers)} consumer(s): {consumers}; '
        f'{len(non_consumers)} docstring-only non-consumer(s): {non_consumers})'
    )


class TestPopulationIsNonVacuous:
    """The scan population must be real, and its size must be published."""

    def test_population_is_non_empty(self):
        reports = _reports()

        assert reports, (
            'Existence-only marker detector scanned an EMPTY population — '
            f'{_population_summary(reports)}. A zero population makes every other '
            'assertion in this module vacuous, so the empty scan is itself the '
            'failure. Check that the source glob still matches the marketplace '
            'layout.'
        )

    def test_population_contains_both_code_consumers_and_docstring_only_mentions(self):
        reports = _reports()

        consumers = [r.label for r in reports if r.is_consumer]
        non_consumers = [r.label for r in reports if not r.is_consumer]

        assert consumers, f'No code-level marker consumer found — {_population_summary(reports)}'
        assert non_consumers, (
            'No docstring-only mention found, so the detector is no longer proven to '
            'COUNT non-consumers in its population rather than silently dropping them '
            f'— {_population_summary(reports)}'
        )


class TestNoConsumerParsesMarkerContent:
    """No production site may read, parse, or compare the marker's content."""

    def test_no_content_consuming_use_exists(self):
        reports = _reports()

        violations = [violation for report in reports for violation in report.violations]

        assert not violations, (
            'The .orphaned_at marker is EXISTENCE-ONLY: its content is written by two '
            'producers in two encodings (our ISO-8601 UTC and Claude Code plugin GC '
            'raw epoch-ms), so reading it couples this repository to a format it does '
            f'not own. Offending site(s): {violations}. {_population_summary(reports)}'
        )

    def test_the_one_sanctioned_write_site_still_exists(self):
        reports = _reports()

        sanctioned = [entry for report in reports for entry in report.sanctioned_writes]

        assert sanctioned, (
            'The allow-list names exactly one sanctioned content-bearing site, '
            f'{_SANCTIONED_WRITE_FUNCTION}(), and it was not found. An allow-list that '
            'matches nothing silently weakens this detector into a rule about a site '
            f'that no longer exists. {_population_summary(reports)}'
        )


_NEGATIVE_CONTROL = '''
"""A source that parses the marker's content — the detector MUST catch this."""

from datetime import datetime
from pathlib import Path


def read_marker_age(version_dir: Path) -> datetime:
    marker = version_dir / '.orphaned_at'
    return datetime.fromisoformat(marker.read_text(encoding='utf-8'))
'''

_NEGATIVE_CONTROL_UNSANCTIONED_WRITE = '''
"""A write from a function the allow-list does not name — MUST be caught."""

from pathlib import Path


def stamp_marker(version_dir: Path) -> None:
    (version_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z', encoding='utf-8')
'''

_POSITIVE_CONTROL = '''
"""An existence-only source — the detector MUST NOT flag this."""

from pathlib import Path


def is_orphaned(version_dir: Path) -> bool:
    return (version_dir / '.orphaned_at').exists()
'''


class TestDetectorControls:
    """Matched controls prove the detector can both fire and stay silent."""

    def test_negative_control_content_parse_is_detected(self):
        report = analyse_source(_NEGATIVE_CONTROL, 'negative_control.py')

        assert report.violations, (
            'The detector failed to flag a source that reads and parses the marker '
            'content. A detector that cannot fail is not evidence of compliance.'
        )

    def test_negative_control_unsanctioned_write_is_detected(self):
        report = analyse_source(_NEGATIVE_CONTROL_UNSANCTIONED_WRITE, 'negative_control_write.py')

        assert report.violations, (
            'The detector failed to flag a marker write outside '
            f'{_SANCTIONED_WRITE_FUNCTION}(), so the allow-list is behaving as a '
            'blanket suppression rather than as one named site.'
        )

    def test_positive_control_existence_only_is_not_detected(self):
        report = analyse_source(_POSITIVE_CONTROL, 'positive_control.py')

        assert report.is_consumer, 'The existence-only control should register as a code-level consumer'
        assert not report.violations, (
            f'The detector flagged an existence-only source: {report.violations}. '
            'A false positive here would make the invariant unenforceable.'
        )
