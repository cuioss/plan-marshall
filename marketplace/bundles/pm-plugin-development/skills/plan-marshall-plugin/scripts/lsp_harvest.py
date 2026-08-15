#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Language-server symbol-reference harvest, run once at discovery time.

A language server resolves references with a real parser, which is knowledge no
static join in this repository can derive. The protocol, however, is built for a
long-lived editor session that amortizes index cost over thousands of queries,
while a derivation resolver is dispatched at graph-QUERY time, once per
``graph`` / ``path`` / ``neighbors`` / ``impact`` call, and is contractually a
pure function of its arguments — no subprocess, no filesystem access.

So the harvest runs HERE, at discovery time, exactly as the marketplace
dependency-detection engine behind ``build_component_refs`` does, and its output
is persisted into ``derived.json`` for the ``lsp`` resolver to join over.

**This module owns no LSP transport of its own.** The session, the JSON-RPC
plumbing, and the machine-local server binding all belong to
``plan-marshall:lsp-client``, which already ships them for the interactive
lookup/edit path; this engine drives that same client in batch. Re-implementing
the transport would put a second, silently diverging LSP client in one
repository, and re-reading the server binary from a different config key would
be exactly the parallel configuration surface the shared store exists to prevent.

The harvest emits ``component_refs`` entries carrying :data:`DEP_TYPE_LSP`, plus
a per-module :data:`HARVEST_STATUS_FIELD` record. That status record is what
keeps a failed harvest from reading as a real answer: a server that is absent,
fails to start, times out, or has no workspace to scan produces ``ran: False``
with a distinct stated reason, which the resolver turns into a note. Without it a
dead server and a genuinely edge-free workspace would both surface as
``status: ok, edge_count: 0``.

See ``plan-marshall:extension-api/standards/ext-point-derivation-resolver.md``
for the resolver contract this engine feeds, and the ``language_servers`` section
of ``plan-marshall:manage-run-config`` for the binding it reads.
"""

from __future__ import annotations

import ast
import shutil
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEP_TYPE_LSP = 'lsp'
"""The ``dep_type`` stamped on every reference this engine materializes.

Sibling kinds (``script`` / ``skill`` / ``import`` / ``path`` / ``implements``)
belong to the markdown, python, and documentation resolvers. Keeping this kind
distinct is what lets the ``lsp`` resolver join over its own references without
competing for the import join's edges — where both derive the same pair, the core
merge unions them into one edge carrying both producer ids.
"""

HARVEST_STATUS_FIELD = 'lsp_harvest'
"""Module-dict field carrying ``{ran, reason, notes, ...}``.

Read by the ``lsp`` resolver so a harvest that did not run is reported rather
than collapsing into a silent zero-edge success.
"""

DEFAULT_TIMEOUT_S = 300.0
"""Whole-harvest wall-clock budget, after which the harvest reports a timeout."""

DEFAULT_REQUEST_TIMEOUT_S = 15.0
"""Handshake budget, scaled to bound the ``initialize`` round trip.

⚠ This does **not** bound the individual definition requests. The shared
``LspSession`` exposes no per-call timeout, so those use the transport's own
default; the whole-harvest ``timeout_s`` is what bounds them in aggregate. Naming
this a per-request budget would promise an enforcement that does not exist.
"""

INITIALIZE_BUDGET_FACTOR = 2.0
"""How much longer than a normal request the ``initialize`` handshake may take.

A server builds its index during ``initialize``, so it legitimately needs longer
than a lookup. The factor is bounded rather than generous because a server that
died on launch is only detectable here by NOT answering: the shared transport
returns on EOF without waking its waiters, so a dead binding costs exactly this
budget on every crawl before the harvest gives up.
"""

HARVEST_LANGUAGE = 'python'
"""The language key looked up in the shared ``language_servers`` binding.

One language, deliberately: the per-language parser cost is the real argument
against chasing this tier broadly, so one language end-to-end is the deliverable
and generalization follows evidence. Widening means a per-language
position-enumeration strategy beside :func:`import_positions`, not just another
binding.
"""

# --- Stated failure reasons. One per lifecycle failure mode. ------------------
# Each is a distinct, human-readable prefix so a reader can tell WHICH mode
# fired. None of them may ever be reported as a successful empty harvest.
REASON_NOT_CONFIGURED = (
    'not-configured: no enabled language_servers binding for {language} in the run-configuration store'
)
REASON_CLIENT_UNAVAILABLE = 'client-unavailable: the plan-marshall lsp-client scripts could not be imported ({detail})'
REASON_SERVER_ABSENT = 'server-absent: {binary} is not on PATH'
REASON_SERVER_FAILED = 'server-failed-to-start: {binary} could not be launched ({detail})'
REASON_SERVER_TIMEOUT = 'server-timeout: {binary} did not respond within {budget:.0f}s ({detail})'
REASON_WORKSPACE_UNSUPPORTED = 'workspace-unsupported: no {language} sources found under the project root'


@dataclass
class HarvestOutcome:
    """The result of one harvest attempt.

    ``ran`` is the load-bearing field. ``ran=False`` with empty ``references``
    means the harvest could not be performed and ``reason`` says why; ``ran=True``
    with empty ``references`` means the server ran and genuinely found nothing.
    Those two states warrant opposite reactions, which is why they are never
    collapsed.
    """

    ran: bool
    reason: str = ''
    references: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    files_scanned: int = 0
    elapsed_s: float = 0.0

    def as_status(self) -> dict[str, Any]:
        """Render the status record attached to each module dict."""
        return {
            'ran': self.ran,
            'reason': self.reason,
            'files_scanned': self.files_scanned,
            'reference_count': len(self.references),
            'elapsed_s': round(self.elapsed_s, 3),
        }


def _load_lsp_client() -> Any:
    """Import the shared lsp-client module, or raise ImportError.

    Deferred and guarded so discovery still works in an envelope that does not
    carry the plan-marshall bundle on its path: an unavailable client degrades to
    a stated no-harvest rather than failing the crawl.
    """
    import lsp_client

    return lsp_client


# =============================================================================
# Position enumeration
# =============================================================================


def import_positions(source: str) -> list[tuple[int, int]]:
    """Return zero-based ``(line, character)`` positions of imported names.

    The positions come from ``ast.alias`` nodes, which carry exact source
    coordinates on Python 3.10+. Anchoring on the statement's own ``col_offset``
    instead would put the request on the ``from`` keyword, where the server
    resolves nothing — a silent zero that reads exactly like a workspace with no
    references. This function is why the harvest resolves anything at all.

    Args:
        source: The file's text.

    Returns:
        Positions to query, in source order. A file that does not parse yields no
        positions rather than raising — an unparseable file is a scanned-but-empty
        file, not a harvest failure.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    positions: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for alias in node.names:
            if alias.name == '*':
                continue
            positions.append((alias.lineno - 1, alias.col_offset))
        if isinstance(node, ast.ImportFrom) and node.module:
            # 'from ' is five characters wide; the module name starts after it.
            positions.append((node.lineno - 1, node.col_offset + 5))
    return positions


# =============================================================================
# The harvest
# =============================================================================


def _candidate_files(project_root: Path, suffix: str, file_budget: int | None) -> list[Path]:
    """Collect workspace sources, skipping trees no crawl should descend into.

    The skip list is matched against each file's path RELATIVE to the workspace
    root, never against its absolute path. Matching absolutely would let a
    component of the root's own location veto the entire workspace: a project
    checked out under a directory named ``target`` or ``venv`` would match on
    every file, harvest nothing, and report the workspace as unsupported — a
    stated-but-wrong reason, which is worse than a silent one because it looks
    considered.
    """
    skip = {'.git', 'node_modules', 'target', '.venv', 'venv', '__pycache__', '.plan'}
    found: list[Path] = []
    for path in sorted(project_root.rglob(f'*{suffix}')):
        if skip.intersection(path.relative_to(project_root).parts):
            continue
        found.append(path)
        if file_budget is not None and len(found) >= file_budget:
            break
    return found


def harvest_workspace(
    project_root: str | Path,
    *,
    server_cmd: list[str],
    language_id: str = HARVEST_LANGUAGE,
    suffix: str = '.py',
    timeout_s: float = DEFAULT_TIMEOUT_S,
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    file_budget: int | None = None,
) -> HarvestOutcome:
    """Drive the shared LSP client over the workspace and harvest file references.

    Every lifecycle failure resolves to ``ran=False`` plus a distinct stated
    reason rather than to an empty success. That is the whole point of the return
    shape: a caller must be able to tell "no server ran" from "a server ran and
    found nothing" without inspecting the reference list.

    Args:
        project_root: Workspace root handed to the server as its root.
        server_cmd: Language-server argv, from the shared binding.
        language_id: LSP ``languageId`` for opened documents.
        suffix: File suffix selecting workspace sources.
        timeout_s: Whole-harvest wall-clock budget, and the only bound on the
            definition requests in aggregate.
        request_timeout_s: Handshake budget, scaled by
            :data:`INITIALIZE_BUDGET_FACTOR`. It does NOT bound individual
            definition calls — the shared session exposes no per-call timeout.
        file_budget: Optional cap on files scanned, for a bounded probe.

    Returns:
        A :class:`HarvestOutcome`. ``references`` holds repo-relative
        ``(from_file, to_file)`` pairs; references leaving the workspace (the
        standard library, site-packages) are dropped, since no module owns them.
    """
    root = Path(project_root).resolve()
    binary = server_cmd[0] if server_cmd else ''
    started = time.monotonic()

    try:
        client = _load_lsp_client()
    except ImportError as exc:
        return HarvestOutcome(ran=False, reason=REASON_CLIENT_UNAVAILABLE.format(detail=exc))

    if not binary or shutil.which(binary) is None:
        return HarvestOutcome(ran=False, reason=REASON_SERVER_ABSENT.format(binary=binary or '<unset>'))

    files = _candidate_files(root, suffix, file_budget)
    if not files:
        return HarvestOutcome(ran=False, reason=REASON_WORKSPACE_UNSUPPORTED.format(language=language_id))

    try:
        transport = client.StdioTransport(server_cmd, str(root))
    except OSError as exc:
        return HarvestOutcome(ran=False, reason=REASON_SERVER_FAILED.format(binary=binary, detail=exc))

    deadline = started + timeout_s
    session = client.LspSession(transport, str(root))
    references: set[tuple[str, str]] = set()
    notes: list[str] = []
    scanned = 0
    external = 0
    unresolved = 0
    truncated = False
    # Bind the handshake budget once so the failure reason can report the budget
    # that was ACTUALLY waited on. Interpolating the whole-harvest timeout here
    # would state a number no code used.
    initialize_budget = min(request_timeout_s * INITIALIZE_BUDGET_FACTOR, max(deadline - time.monotonic(), 0.0))

    try:
        session.initialize(timeout=initialize_budget)

        for path in files:
            if time.monotonic() >= deadline:
                truncated = True
                break
            try:
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError) as exc:
                notes.append(f'unreadable: {_rel(path, root)} ({type(exc).__name__})')
                continue

            positions = import_positions(text)
            scanned += 1
            if not positions:
                continue

            session.open(str(path))
            for line, character in positions:
                if time.monotonic() >= deadline:
                    # Truncation inside the LAST file would otherwise exit the
                    # outer loop normally and report a partial harvest as
                    # complete.
                    truncated = True
                    break
                locations = session.definition(str(path), line, character)
                if not locations:
                    unresolved += 1
                    continue
                for target in _definition_targets(locations):
                    if target == path:
                        continue
                    if not _within(target, root):
                        external += 1
                        continue
                    references.add((_rel(path, root), _rel(target, root)))

    except client.LspError as exc:
        # The shared transport reports a wedged server, a dead server, and a
        # protocol error alike as LspError — it returns on EOF without waking its
        # waiters, so a server that died on launch is indistinguishable here from
        # one that is merely slow. None of them may escape into the crawl, and
        # none may read as a successful empty harvest.
        return HarvestOutcome(
            ran=False,
            reason=REASON_SERVER_TIMEOUT.format(binary=binary, budget=initialize_budget, detail=exc),
            files_scanned=scanned,
            elapsed_s=time.monotonic() - started,
        )
    except OSError as exc:
        return HarvestOutcome(
            ran=False,
            reason=REASON_SERVER_FAILED.format(binary=binary, detail=exc),
            files_scanned=scanned,
            elapsed_s=time.monotonic() - started,
        )
    finally:
        transport.close()

    if truncated:
        notes.append(
            f'harvest-budget: stopped after {scanned} of {len(files)} files at the '
            f'{timeout_s:.0f}s budget; the reference set is partial'
        )
    if external:
        notes.append(f'out-of-workspace: {external} reference(s) resolved outside the project root and own no module')
    if unresolved:
        notes.append(f'unresolved-symbol: {unresolved} position(s) the server could not resolve to a definition')

    return HarvestOutcome(
        ran=True,
        references=sorted(references),
        notes=notes,
        files_scanned=scanned,
        elapsed_s=time.monotonic() - started,
    )


def _definition_targets(locations: Iterable[Any]) -> list[Path]:
    """Normalize the shapes ``textDocument/definition`` may return."""
    targets: list[Path] = []
    for item in locations:
        if not isinstance(item, dict):
            continue
        uri = item.get('uri') or item.get('targetUri') or ''
        path = _path_from_uri(uri)
        if path is not None:
            targets.append(path)
    return targets


def _path_from_uri(uri: str) -> Path | None:
    """Convert a ``file://`` URI to a path, decoding percent-escapes.

    The unquote is not optional: a workspace path containing a space arrives as
    ``%20``, and a path left encoded fails the in-workspace test below, so every
    reference in that workspace would be miscounted as out-of-workspace — a
    stated but wrong reason.
    """
    if not uri.startswith('file://'):
        return None
    from urllib.parse import unquote, urlparse

    return Path(unquote(urlparse(uri).path))


def _within(path: Path, root: Path) -> bool:
    return root == path or root in path.parents


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


# =============================================================================
# The file-to-module lift
# =============================================================================


def lift_to_modules(
    file_references: Iterable[tuple[str, str]],
    attribute: Callable[[str], str | None],
    known_modules: Iterable[str],
) -> tuple[list[tuple[str, str]], list[str]]:
    """Lift file-granular references to module-granular pairs.

    Symbol references are file-granular; edges are module-granular. The lift goes
    through the path-attribution seam — the ``attribute`` callable is that seam's
    ``path -> owning module`` answer — because a resolver may not invent an owner
    for a path.

    An endpoint the seam cannot attribute produces **no edge and a note**, never a
    guessed module. That is the rule the whole substrate turns on: a
    confidently-labelled wrong edge is worse than a missing one, and this function
    is capable of producing them at volume.

    Args:
        file_references: ``(from_file, to_file)`` repo-relative pairs.
        attribute: Path-attribution seam lookup; returns ``None`` when no
            attributor claims the path.
        known_modules: The discovered module set. An attributed name outside it is
            dropped, since a resolver cannot invent a node.

    Returns:
        ``(edges, notes)`` — sorted deduplicated module pairs, plus one aggregated
        note per non-empty suppression category.
    """
    known = set(known_modules)
    edges: set[tuple[str, str]] = set()
    suppressed: dict[str, list[str]] = {
        'unattributable-endpoint': [],
        'unknown-endpoint': [],
        'self-edge': [],
    }

    for from_file, to_file in file_references:
        from_module = attribute(from_file)
        to_module = attribute(to_file)

        if from_module is None or to_module is None:
            unowned = from_file if from_module is None else to_file
            suppressed['unattributable-endpoint'].append(f'{from_file} -> {to_file} (no module owns {unowned})')
        elif from_module not in known or to_module not in known:
            unknown = from_module if from_module not in known else to_module
            suppressed['unknown-endpoint'].append(f'{from_module} -> {to_module} ({unknown} is not a known module)')
        elif from_module == to_module:
            suppressed['self-edge'].append(f'{from_module} -> {to_module}')
        else:
            edges.add((from_module, to_module))

    return sorted(edges), aggregate_notes(suppressed)


def aggregate_notes(suppressed: dict[str, list[str]], sample_size: int = 3) -> list[str]:
    """Render one note per non-empty suppression category, with a bounded sample.

    Aggregation is load-bearing: a per-instance note over a large workspace would
    bury the report under thousands of lines, and a suppression nobody reads is
    functionally a silent one.
    """
    notes: list[str] = []
    for category, entries in suppressed.items():
        if not entries:
            continue
        sample = '; '.join(sorted(entries)[:sample_size])
        suffix = ', ...' if len(entries) > sample_size else ''
        notes.append(f'{category}: {len(entries)} suppressed [{sample}{suffix}]')
    return notes


# =============================================================================
# component_refs materialization
# =============================================================================


def resolve_binding(language: str = HARVEST_LANGUAGE) -> dict[str, Any] | None:
    """Read the machine-local server binding from the shared run-config store.

    Returns ``None`` when the language has no enabled binding — the section is
    absent, the language is absent, the entry is disabled, or its command is
    missing. All of those are the opt-out path.

    This is the ONLY switch the harvest has. It ships no ``enabled`` key of its
    own, because the shared binding already carries enabled/disabled semantics,
    and a second switch naming the same server for the same language would be the
    parallel configuration surface the shared store exists to prevent. It also
    makes the harvest off-by-default for free: the store is machine-local and
    git-ignored, so a fresh clone has no binding and runs no server.
    """
    try:
        client = _load_lsp_client()
    except ImportError:
        return None
    try:
        binding = client.resolve_language_server(language)
    except (OSError, ValueError, KeyError, TypeError):
        # A malformed or unreadable store is an opt-out, not a crawl failure.
        return None
    return binding if isinstance(binding, dict) else None


def build_lsp_component_refs(
    project_root: str | Path,
    module_paths: dict[str, str],
    *,
    binding: dict[str, Any] | None,
    **harvest_kwargs: Any,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Harvest the workspace and project references onto module granularity.

    Args:
        project_root: Project root.
        module_paths: Module name → repo-relative module directory, the
            attribution table the lift resolves endpoints against.
        binding: The resolved ``language_servers`` entry, or ``None`` to report
            the language as not configured and run nothing.
        **harvest_kwargs: Forwarded to :func:`harvest_workspace`.

    Returns:
        ``(refs_by_module, status)`` where ``refs_by_module`` maps a module name
        to its ``component_refs`` additions and ``status`` is the record every
        module carries under :data:`HARVEST_STATUS_FIELD`.
    """
    if not binding:
        # "No binding" has two causes with different remedies, and collapsing
        # them would tell an operator to configure a language server when the
        # real problem is that the client module is not on the path.
        try:
            _load_lsp_client()
        except ImportError as exc:
            return {}, HarvestOutcome(ran=False, reason=REASON_CLIENT_UNAVAILABLE.format(detail=exc)).as_status()
        return {}, HarvestOutcome(ran=False, reason=REASON_NOT_CONFIGURED.format(language=HARVEST_LANGUAGE)).as_status()

    outcome = harvest_workspace(
        project_root,
        server_cmd=list(binding.get('command') or []),
        language_id=str(binding.get('language_id') or HARVEST_LANGUAGE),
        **harvest_kwargs,
    )
    if not outcome.ran:
        return {}, outcome.as_status()

    attribute = make_prefix_attributor(module_paths)
    edges, notes = lift_to_modules(outcome.references, attribute, module_paths)

    refs: dict[str, list[dict[str, Any]]] = {}
    for from_module, to_module in edges:
        refs.setdefault(from_module, []).append(
            {'target_bundle': to_module, 'dep_type': DEP_TYPE_LSP, 'resolved': True}
        )

    status = outcome.as_status()
    status['notes'] = outcome.notes + notes
    return refs, status


def make_prefix_attributor(module_paths: dict[str, str]) -> Callable[[str], str | None]:
    """Build a longest-prefix ``path -> module`` lookup over a claim table.

    Longest-prefix rather than first-match: a nested module's directory is a
    strict extension of its parent's, so a shortest- or arbitrary-match lookup
    would attribute a nested module's files to the enclosing module and derive a
    confidently wrong edge. Containment is segment-wise, so ``doc`` does not claim
    ``docs/x``.
    """
    table = sorted(
        ((path.strip('/'), name) for name, path in module_paths.items()),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    def attribute(path: str) -> str | None:
        candidate = path.strip('/')
        for prefix, name in table:
            if not prefix or prefix == '.':
                continue
            if candidate == prefix or candidate.startswith(prefix + '/'):
                return name
        # A root-scoped module ('.' or '') owns whatever nothing else claims.
        for prefix, name in table:
            if prefix in ('', '.'):
                return name
        return None

    return attribute
