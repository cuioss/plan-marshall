# SPDX-License-Identifier: FSL-1.1-ALv2
"""Enforcement test for the existence-only ``.orphaned_at`` marker invariant.

``.orphaned_at`` is a plugin-cache marker with TWO producers writing ONE field in
TWO encodings: ours (ISO-8601 UTC, written by
``generate_executor._mark_superseded_version_dirs``) and Claude Code's own plugin
GC (raw epoch-ms). The encoding split is inert only because every consumer in this
repository reads the marker's EXISTENCE and never its content. That invariant is
declared at each of the TWO sanctioned existence-read sites —
``marketplace_bundles._partition_version_dirs`` (the selector) and the mirrored
predicate inside ``generate_executor._CLAUDE_RESOLVER_TEMPLATE``, which is
substituted verbatim into the generated ``.plan/execute-script.py``. This module
pins the invariant at both, so a future content-dependent read fails the build
instead of silently coupling this repository to a format it does not own.

The detector is POPULATION-DERIVED: it enumerates the production sources that
mention the marker and publishes the discovered population size in every assertion
message, so it can never pass vacuously from an empty scan. Files whose only
mentions are inside a docstring or comment are classified as NON-consumers but are
still COUNTED in the published population, so a silent shrink of the population is
itself a failure rather than a quiet pass.

**Emitted code is scanned too.** A read site can be embedded in a string constant
that is substituted into generated code rather than executed in place — which is
exactly the shape of the mandated mirror in ``_CLAUDE_RESOLVER_TEMPLATE``. A plain
AST walk never sees the marker there, because the template is one large string
constant and no ``ast.Constant`` equals the marker name. The detector therefore
re-parses every non-docstring string constant that carries the marker and, when it
is valid Python holding a marker constant, runs the same classification over it.
Coverage of the shipped template is asserted by name, so the mandated-mirror site
cannot silently drop out of scope. The published population is unchanged by this —
the template lives inside a file the population already contains — but the covered
read-site set is not, so ``_population_summary`` names every template it descended
into alongside the file count.

**The sanctioned set is CLOSED, and the closure is asserted rather than declared.**
An existence read is not merely "not a violation" — it is RECORDED, with the scope
that performs it, and the set of those scopes must equal the two names above. An
unrecorded read would be invisible to every assertion here: a new ``.orphaned_at``
existence probe added to a file that is currently a docstring-only non-consumer
satisfies every content-oriented check in this module while quietly turning that
file into a marker-driven oracle — the liveness hazard being a retention pass that
deletes a live version dir. Recording the read is what turns the "TWO sites"
sentence above into an enforced closure instead of a claim the tests never check.

Matched controls run in both directions at BOTH shapes: a source that parses the
marker's content MUST be detected and an existence-only source MUST NOT be, in
plain module code and again inside a template-shaped string constant. The
sanctioned-set arm carries its own matched pair — an existence read from an
unsanctioned scope MUST be flagged and one from a sanctioned scope MUST NOT be —
so the closure guard is observed to fire rather than assumed to.
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

#: Attribute accesses that probe a marker path's EXISTENCE without touching its
#: content. These are the sanctioned shape — but only from a sanctioned scope, so
#: they are RECORDED rather than ignored. ``stat``/``lstat`` are included because a
#: stat call answers the same "is it there?" question ``exists`` does; leaving them
#: out would let the closure below be evaded by spelling.
_EXISTENCE_READ_ATTRS = frozenset({'exists', 'is_file', 'is_dir', 'stat', 'lstat'})

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

#: The second sanctioned existence-read site: the policy mirror the selector's
#: docstring mandates keeping in step. It lives inside an emitted-code template
#: constant, so it is reachable only through the template descent above — which is
#: precisely why its coverage is asserted by name rather than assumed.
_MIRROR_SOURCE = 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
_MIRROR_TEMPLATE = '_CLAUDE_RESOLVER_TEMPLATE'

#: The CLOSED set of scopes allowed to probe the marker's existence, allow-listed
#: BY NAME exactly as ``_SANCTIONED_WRITE_FUNCTION`` is. ``_partition_version_dirs``
#: is the selector in ``marketplace_bundles``; ``_resolve_notation_by_target`` is the
#: mirrored predicate inside ``_CLAUDE_RESOLVER_TEMPLATE``, reachable only through the
#: emitted-code descent. The set was derived by surveying the population, not by
#: widening an allow-list until the suite went green.
_SANCTIONED_EXISTENCE_READ_SCOPES = frozenset({'_partition_version_dirs', '_resolve_notation_by_target'})


@dataclass(frozen=True)
class ExistenceRead:
    """One recorded existence-shaped probe of a marker path."""

    label: str
    lineno: int
    scope_name: str
    attr: str

    def __str__(self) -> str:
        return f'{self.label}:{self.lineno}: {self.scope_name}().{self.attr}()'


@dataclass
class MarkerReport:
    """The per-source verdict of one detector pass."""

    label: str
    mentions_marker: bool = False
    code_occurrences: int = 0
    violations: list[str] = field(default_factory=list)
    sanctioned_writes: list[str] = field(default_factory=list)
    existence_reads: list[ExistenceRead] = field(default_factory=list)
    templates_analysed: list[str] = field(default_factory=list)

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
    """Classify an attribute access made directly on a marker path.

    An existence-shaped probe is RECORDED rather than dropped. Falling through on
    it would make the read invisible to every ledger — neither a violation nor
    anything else — which is precisely how a new marker consumer could appear while
    the whole module stayed green.
    """
    if attr in _EXISTENCE_READ_ATTRS:
        report.existence_reads.append(ExistenceRead(label=label, lineno=lineno, scope_name=scope_name, attr=attr))
        return
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


def _embedded_code_tree(text: str) -> ast.AST | None:
    """Parse ``text`` as emitted Python carrying the marker, else ``None``.

    A read site can be embedded in a string constant that is substituted into
    generated code — ``generate_executor._CLAUDE_RESOLVER_TEMPLATE`` is exactly
    that shape. Such a constant is accepted only when it is valid Python AND holds
    a constant equal to the marker name, so ordinary prose (which does not parse)
    and unrelated code templates are both left alone.
    """
    if _MARKER_NAME not in text:
        return None
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == _MARKER_NAME:
            return tree
    return None


def _template_label(node: ast.AST, parents: dict[ast.AST, ast.AST], label: str) -> str:
    """Name an embedded-code constant by the variable it is bound to."""
    parent = parents.get(node)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and isinstance(parent.targets[0], ast.Name):
        return f'{label}[{parent.targets[0].id}]'
    if isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
        return f'{label}[{parent.target.id}]'
    return f'{label}[<template@{getattr(node, "lineno", 0)}>]'


def _analyse_tree(tree: ast.AST, label: str, report: MarkerReport) -> None:
    """Classify every marker use in ``tree``, descending into emitted-code constants.

    Recursion terminates without a depth guard: an embedded constant is strictly
    shorter than the source it was parsed out of. Line numbers reported from inside
    a template are relative to the template text, and the label names the template.
    """
    parents = _parent_map(tree)
    docstring_ids = _docstring_constant_ids(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstring_ids:
            continue
        if node.value == _MARKER_NAME:
            report.code_occurrences += 1
            _classify_use(_marker_path_node(node, parents), parents, tree, label, report)
            continue
        embedded = _embedded_code_tree(node.value)
        if embedded is None:
            continue
        nested_label = _template_label(node, parents, label)
        report.templates_analysed.append(nested_label)
        _analyse_tree(embedded, nested_label, report)


def analyse_source(source: str, label: str) -> MarkerReport:
    """Run the existence-only detector over one Python source text."""
    report = MarkerReport(label=label)
    report.mentions_marker = _MARKER_NAME in source
    if not report.mentions_marker:
        return report

    _analyse_tree(ast.parse(source), label, report)
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
    """Render the published population size, its consumer split, and template coverage."""
    consumers = [r.label for r in reports if r.is_consumer]
    non_consumers = [r.label for r in reports if not r.is_consumer]
    templates = [name for r in reports for name in r.templates_analysed]
    return (
        f'scanned population = {len(reports)} production source(s) matching '
        f'{_SOURCE_GLOB!r} under marketplace/bundles that mention {_MARKER_NAME!r} '
        f'({len(consumers)} consumer(s): {consumers}; '
        f'{len(non_consumers)} docstring-only non-consumer(s): {non_consumers}); '
        f'{len(templates)} emitted-code template(s) descended into: {templates}'
    )


def _all_existence_reads(reports: list[MarkerReport]) -> list[ExistenceRead]:
    """Flatten every recorded existence read across ``reports``."""
    return [read for report in reports for read in report.existence_reads]


def _existence_read_scopes(reports: list[MarkerReport]) -> set[str]:
    """Return the distinct scope names that probe the marker's existence."""
    return {read.scope_name for read in _all_existence_reads(reports)}


def _unsanctioned_existence_read_scopes(reports: list[MarkerReport]) -> set[str]:
    """Return the existence-read scopes the sanctioned set does not name.

    Extracted as a named predicate so the matched controls below can drive it over
    synthetic sources and observe it both firing and staying silent — a closure
    guard that is only ever exercised against the real tree is an unobserved guard.
    """
    return _existence_read_scopes(reports) - _SANCTIONED_EXISTENCE_READ_SCOPES


def _render_existence_reads(reports: list[MarkerReport]) -> list[str]:
    """Render every recorded existence read as ``label:lineno: scope().attr()``."""
    return [str(read) for read in _all_existence_reads(reports)]


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


class TestExistenceReadsAreConfinedToTheSanctionedSet:
    """The set of scopes that probe the marker's existence is CLOSED at two."""

    def test_existence_read_scopes_are_exactly_the_sanctioned_two(self):
        reports = _reports()

        observed = _existence_read_scopes(reports)
        unsanctioned = sorted(observed - _SANCTIONED_EXISTENCE_READ_SCOPES)
        missing = sorted(_SANCTIONED_EXISTENCE_READ_SCOPES - observed)

        assert observed == set(_SANCTIONED_EXISTENCE_READ_SCOPES), (
            'The .orphaned_at existence-read sanction set is CLOSED at exactly '
            f'{sorted(_SANCTIONED_EXISTENCE_READ_SCOPES)}, and the scan disagrees. '
            f'Unsanctioned scope(s) now reading the marker: {unsanctioned}. '
            f'Sanctioned scope(s) the scan could not find: {missing}. '
            'An UNSANCTIONED entry means a new site consults the marker: the field has '
            'a foreign co-producer, and a third consumer is how a marker-driven '
            'retention oracle removes a live version dir. Either justify the site and '
            'add it here together with the "two sites" statement in '
            'manage-config/standards/data-model.md, or remove the read. A MISSING '
            'entry means the allow-list has drifted off the code and is now guarding a '
            'site that no longer exists. '
            f'Recorded existence read(s): {_render_existence_reads(reports)}. '
            f'{_population_summary(reports)}'
        )


class TestMandatedMirrorSiteIsCovered:
    """The read site the mirroring mandate lands on must be inside the scan."""

    def test_claude_resolver_template_is_descended_into(self):
        reports = _reports()

        analysed = [name for report in reports for name in report.templates_analysed]
        expected = f'{_MIRROR_SOURCE}[{_MIRROR_TEMPLATE}]'

        assert expected in analysed, (
            f'The detector did not descend into {expected}. That template carries the '
            'mirrored .orphaned_at predicate substituted verbatim into the generated '
            'executor, and its own docstring makes it the site any selector-policy '
            'change MUST be applied to — so a scan that cannot see inside it leaves the '
            'one mandated-mirror location unguarded while still reporting green. '
            f'{_population_summary(reports)}'
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

# The matched pair for the sanctioned-set closure. The negative member is the
# cache_retention._keep_reason() shape the finding named: an existence read that is
# not a content violation, so every content-oriented assertion in this module stays
# green while the file becomes a marker consumer.
_NEGATIVE_CONTROL_UNSANCTIONED_EXISTENCE_READ = '''
"""An existence read from a scope the sanction set does not name — MUST be caught."""

from pathlib import Path


def _keep_reason(version_dir: Path) -> str:
    if (version_dir / '.orphaned_at').exists():
        return 'orphaned'
    return 'live'
'''

_POSITIVE_CONTROL_SANCTIONED_EXISTENCE_READ = '''
"""An existence read from a sanctioned scope — MUST NOT be flagged."""

from pathlib import Path


def _partition_version_dirs(bundle_dir: Path) -> list[Path]:
    return [d for d in bundle_dir.iterdir() if not (d / '.orphaned_at').exists()]
'''

# The template-shaped half of the matched pair. Both members carry the marker read
# inside a string constant that is substituted into emitted code — the shape of
# _CLAUDE_RESOLVER_TEMPLATE — so together they prove the template descent both fires
# on a content-dependent read and stays silent on an existence-only one. The pair is
# what makes the descent evidence of compliance rather than an unobserved guard.
_TEMPLATE_CONTROL_CONTENT_PARSE = '''
_EMITTED_RESOLVER_TEMPLATE = """
def pick_live_dir(version_dir):
    marker = version_dir / '.orphaned_at'
    return float(marker.read_text(encoding='utf-8'))
"""
'''

_TEMPLATE_CONTROL_EXISTENCE_ONLY = '''
_EMITTED_RESOLVER_TEMPLATE = """
def pick_live_dir(version_dir):
    return (version_dir / '.orphaned_at').exists()
"""
'''

_TEMPLATE_CONTROL_INERT_PROSE = '''
_ADVICE = """
The .orphaned_at marker is advisory and is never consulted as a keep-or-delete
oracle, so this prose must not be mistaken for emitted code.
"""
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


class TestExistenceReadSanctionControls:
    """Matched controls proving the closure guard fires — and only when it should."""

    def test_existence_read_is_recorded_rather_than_dropped(self):
        report = analyse_source(_POSITIVE_CONTROL, 'positive_control.py')

        assert report.existence_reads, (
            'An existence read was classified as neither a violation nor a recorded '
            'read, so it left no trace in any ledger. A read nothing records is a read '
            'no assertion can constrain — this is the exact fall-through the '
            'sanctioned-set closure exists to close, so the closure is meaningless '
            'unless this control holds.'
        )

    def test_negative_control_unsanctioned_existence_read_is_caught(self):
        report = analyse_source(_NEGATIVE_CONTROL_UNSANCTIONED_EXISTENCE_READ, 'negative_control_existence.py')

        assert _unsanctioned_existence_read_scopes([report]) == {'_keep_reason'}, (
            'The closure guard did not flag an existence read from an unsanctioned '
            f'scope. Recorded: {_render_existence_reads([report])}. A guard that cannot '
            'fire on the very shape it was written for is not enforcement.'
        )

    def test_positive_control_sanctioned_existence_read_is_not_caught(self):
        report = analyse_source(_POSITIVE_CONTROL_SANCTIONED_EXISTENCE_READ, 'positive_control_existence.py')

        assert report.existence_reads, (
            'The sanctioned-scope control recorded no existence read at all, so the '
            'silent verdict below would be silence from not looking.'
        )
        assert not _unsanctioned_existence_read_scopes([report]), (
            'The closure guard flagged an existence read from a scope it names as '
            f'sanctioned: {_render_existence_reads([report])}. A false positive here '
            'would make the invariant unenforceable at the two sites that must have it.'
        )

    def test_template_embedded_existence_read_is_recorded(self):
        report = analyse_source(_TEMPLATE_CONTROL_EXISTENCE_ONLY, 'template_control_existence.py')

        assert report.existence_reads, (
            'An existence read inside an emitted-code template left no record. The '
            f'mandated mirror in {_MIRROR_TEMPLATE} is reachable ONLY through the '
            'template descent, so an unrecorded read there silently drops one of the '
            'two sanctioned sites out of the observed set — and the closure assertion '
            'would then be satisfiable by the selector alone.'
        )


class TestTemplateDescentControls:
    """The matched pair proving the template descent fires — and only when it should."""

    def test_template_embedded_content_parse_is_detected(self):
        report = analyse_source(_TEMPLATE_CONTROL_CONTENT_PARSE, 'template_control_parse.py')

        assert report.templates_analysed, (
            'The detector did not recognise the template constant as emitted code, so '
            'the read inside it was never classified at all.'
        )
        assert report.violations, (
            'The detector failed to flag a content-dependent marker read embedded in an '
            'emitted-code template. This is the exact shape of the mandated mirror in '
            f'{_MIRROR_TEMPLATE}, so a descent that cannot fire here is an unobserved '
            'guard, not enforcement.'
        )

    def test_template_embedded_existence_only_is_not_detected(self):
        report = analyse_source(_TEMPLATE_CONTROL_EXISTENCE_ONLY, 'template_control_existence.py')

        assert report.templates_analysed, (
            'The detector did not recognise the template constant as emitted code, so '
            'the silent verdict below would be silence from not looking.'
        )
        assert report.is_consumer, (
            'An existence-only read inside a template must still register as a code-level '
            'consumer — otherwise the descent found nothing and proves nothing.'
        )
        assert not report.violations, (
            f'The detector flagged an existence-only read inside a template: {report.violations}. '
            'A false positive here would make every emitted-code template unshippable.'
        )

    def test_prose_string_constant_is_not_treated_as_emitted_code(self):
        report = analyse_source(_TEMPLATE_CONTROL_INERT_PROSE, 'template_control_prose.py')

        assert not report.templates_analysed, (
            'A prose string constant that merely names the marker was parsed as emitted '
            f'code: {report.templates_analysed}. The descent must key on "valid Python '
            'holding a marker constant", not on the marker name appearing in text.'
        )
        assert not report.violations
