#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Language-server symbol-reference harvest, run once at discovery time.

A language server resolves references with a real parser, which is knowledge no
static join in this repository can derive. The protocol, however, is built for a
long-lived editor session that amortizes index cost over thousands of queries,
while this project's consumers are one-shot subprocesses. Booting a server per
query is therefore not viable, and the resolution is to use the server as a
**derivation-time producer** rather than as a query backend.

That choice is forced by the Axis-C contract, not merely preferred: a derivation
resolver is a pure function of its arguments — no subprocess, no filesystem
access — and resolvers are dispatched at graph-QUERY time, once per
``graph`` / ``path`` / ``neighbors`` / ``impact`` call. A server booted inside
``derive_edges`` would pay its whole harvest on every one of those calls. So the
harvest runs HERE, at discovery time, exactly as the marketplace
dependency-detection engine behind ``build_component_refs`` does, and its output
is persisted into ``derived.json`` for the resolver to join over.

The harvest emits ``component_refs`` entries carrying :data:`DEP_TYPE_LSP`, plus
a per-module :data:`HARVEST_STATUS_FIELD` record. That status record is what
keeps a failed harvest from reading as a real answer: a server that is absent,
fails to start, times out, or does not support the workspace produces
``ran: False`` with a distinct stated reason, which the ``lsp`` resolver turns
into a note. Without it a dead server and a genuinely edge-free workspace would
both surface as ``status: ok, edge_count: 0`` — the confident-empty-answer this
substrate exists to eliminate.

See ``plan-marshall:extension-api/standards/ext-point-derivation-resolver.md``
for the resolver contract this engine feeds.
"""

from __future__ import annotations

import ast
import json
import os
import selectors
import shutil
import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

DEP_TYPE_LSP = 'lsp'
"""The ``dep_type`` stamped on every reference this engine materializes.

Sibling kinds (``script`` / ``skill`` / ``import`` / ``path`` / ``implements``)
belong to the markdown and python resolvers. Keeping this kind distinct is what
lets the ``lsp`` resolver join over its own references without competing for the
import join's edges — where both derive the same pair, the core merge unions them
into one edge carrying both producer ids.
"""

HARVEST_STATUS_FIELD = 'lsp_harvest'
"""Module-dict field carrying ``{ran, reason, files_scanned, reference_count}``.

Read by the ``lsp`` resolver so a harvest that did not run is reported rather
than collapsing into a silent zero-edge success.
"""

DEFAULT_TIMEOUT_S = 300.0
"""Whole-harvest wall-clock budget, after which the harvest reports a timeout."""

DEFAULT_REQUEST_TIMEOUT_S = 15.0
"""Per-request budget. A single wedged request must not consume the whole run."""

# --- Stated failure reasons (D3). One per lifecycle failure mode. --------------
# Each is a distinct, human-readable prefix so a reader can tell WHICH mode
# fired. None of them may ever be reported as a successful empty harvest.
REASON_DISABLED = 'disabled: lsp harvest is not enabled for this project'
REASON_SERVER_ABSENT = 'server-absent: {binary} is not on PATH'
REASON_SERVER_FAILED = 'server-failed-to-start: {binary} could not be launched ({detail})'
REASON_SERVER_TIMEOUT = 'server-timeout: {binary} did not respond within {budget:.0f}s ({phase})'
REASON_WORKSPACE_UNSUPPORTED = 'workspace-unsupported: no {language} sources found under the project root'
REASON_SERVER_GONE = 'server-failed-to-start: {binary} exited before completing the session ({phase})'


class LspTimeout(RuntimeError):
    """A read exceeded its budget."""


class LspServerGone(RuntimeError):
    """The server closed its stdout before answering."""


@dataclass
class HarvestOutcome:
    """The result of one harvest attempt.

    ``ran`` is the load-bearing field. ``ran=False`` with an empty
    ``references`` means the harvest could not be performed and ``reason`` says
    why; ``ran=True`` with an empty ``references`` means the server ran and
    genuinely found nothing. Those two states warrant opposite reactions, which
    is precisely why they are never collapsed.
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


# =============================================================================
# Minimal stdio LSP client
# =============================================================================


class LspClient:
    """A minimal JSON-RPC-over-stdio client, sufficient to drive one batch.

    Deliberately not a general client: it speaks only the handful of methods a
    batch harvest needs, and every read carries a deadline so a wedged server
    surfaces as a stated timeout rather than a hung crawl.
    """

    def __init__(self, proc: subprocess.Popen, stdin: IO[bytes], stdout: IO[bytes]) -> None:
        # The streams are passed explicitly rather than read off ``proc`` so the
        # not-None narrowing happens once, at the launch site that knows both
        # pipes were requested.
        self._proc = proc
        self._stdin = stdin
        self._stdout = stdout
        self._buf = bytearray()
        self._id = 0
        self._selector = selectors.DefaultSelector()
        self._selector.register(stdout, selectors.EVENT_READ)

    def _fill(self, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LspTimeout
        if not self._selector.select(timeout=remaining):
            raise LspTimeout
        chunk = os.read(self._stdout.fileno(), 65536)
        if not chunk:
            raise LspServerGone
        self._buf.extend(chunk)

    def _read_message(self, deadline: float) -> dict[str, Any]:
        while True:
            split = self._buf.find(b'\r\n\r\n')
            if split == -1:
                self._fill(deadline)
                continue
            header = self._buf[:split].decode('ascii', 'replace')
            length = 0
            for line in header.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    length = int(line.split(':', 1)[1].strip())
            body_start = split + 4
            while len(self._buf) < body_start + length:
                self._fill(deadline)
            body = bytes(self._buf[body_start : body_start + length])
            del self._buf[: body_start + length]
            decoded = json.loads(body)
            # A server sending a non-object payload is malformed; treat it as an
            # empty message rather than letting an unexpected shape reach callers
            # that index it.
            return decoded if isinstance(decoded, dict) else {}

    def _write(self, payload: dict) -> None:
        body = json.dumps(payload).encode('utf-8')
        self._stdin.write(b'Content-Length: %d\r\n\r\n%s' % (len(body), body))
        self._stdin.flush()

    def notify(self, method: str, params: dict) -> None:
        """Send a notification (no reply expected)."""
        self._write({'jsonrpc': '2.0', 'method': method, 'params': params})

    def request(self, method: str, params: dict, timeout_s: float) -> Any:
        """Send a request and return its ``result``, ignoring interleaved traffic."""
        self._id += 1
        request_id = self._id
        self._write({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout_s
        while True:
            message = self._read_message(deadline)
            if message.get('id') == request_id:
                return message.get('result')


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
        Positions to query, in source order. A file that does not parse yields
        no positions rather than raising — an unparseable file is reported by
        the caller as a scanned-but-empty file, not as a harvest failure.
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
    """Collect workspace sources, skipping trees no crawl should descend into."""
    skip = {'.git', 'node_modules', 'target', '.venv', 'venv', '__pycache__', '.plan'}
    found: list[Path] = []
    for path in sorted(project_root.rglob(f'*{suffix}')):
        if skip.intersection(path.parts):
            continue
        found.append(path)
        if file_budget is not None and len(found) >= file_budget:
            break
    return found


def harvest_workspace(
    project_root: str | Path,
    *,
    server_cmd: list[str],
    language: str = 'python',
    suffix: str = '.py',
    timeout_s: float = DEFAULT_TIMEOUT_S,
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    file_budget: int | None = None,
) -> HarvestOutcome:
    """Drive one language server over the workspace and harvest file references.

    Every lifecycle failure resolves to ``ran=False`` plus a distinct stated
    reason (:data:`REASON_SERVER_ABSENT` and siblings) rather than to an empty
    success. That is the whole point of the return shape: a caller must be able
    to tell "no server ran" from "a server ran and found nothing" without
    inspecting the reference list.

    Args:
        project_root: Workspace root handed to the server as its ``rootUri``.
        server_cmd: Argv of the language server, e.g.
            ``['pyright-langserver', '--stdio']``.
        language: LSP ``languageId`` for opened documents.
        suffix: File suffix selecting workspace sources.
        timeout_s: Whole-harvest wall-clock budget.
        request_timeout_s: Per-request budget.
        file_budget: Optional cap on files scanned, for a bounded probe.

    Returns:
        A :class:`HarvestOutcome`. ``references`` holds repo-relative
        ``(from_file, to_file)`` pairs; references leaving the workspace (the
        standard library, site-packages) are dropped, since no module owns them.
    """
    root = Path(project_root).resolve()
    binary = server_cmd[0] if server_cmd else ''
    started = time.monotonic()

    if not binary or shutil.which(binary) is None:
        return HarvestOutcome(ran=False, reason=REASON_SERVER_ABSENT.format(binary=binary or '<unset>'))

    files = _candidate_files(root, suffix, file_budget)
    if not files:
        return HarvestOutcome(ran=False, reason=REASON_WORKSPACE_UNSUPPORTED.format(language=language))

    try:
        proc = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
        )
    except OSError as exc:
        return HarvestOutcome(ran=False, reason=REASON_SERVER_FAILED.format(binary=binary, detail=exc))

    if proc.stdin is None or proc.stdout is None:
        proc.kill()
        return HarvestOutcome(ran=False, reason=REASON_SERVER_FAILED.format(binary=binary, detail='no stdio pipes'))

    deadline = started + timeout_s
    client = LspClient(proc, proc.stdin, proc.stdout)
    references: set[tuple[str, str]] = set()
    notes: list[str] = []
    scanned = 0
    external = 0
    unresolved = 0

    try:
        client.request(
            'initialize',
            {
                'processId': os.getpid(),
                'rootUri': root.as_uri(),
                'workspaceFolders': [{'uri': root.as_uri(), 'name': root.name}],
                'capabilities': {'textDocument': {'definition': {'linkSupport': True}}},
            },
            timeout_s=min(request_timeout_s * 4, max(deadline - time.monotonic(), 0.0)),
        )
        client.notify('initialized', {})

        for path in files:
            if time.monotonic() >= deadline:
                notes.append(
                    f'harvest-budget: stopped after {scanned} of {len(files)} files at the '
                    f'{timeout_s:.0f}s budget; the reference set is partial'
                )
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

            uri = path.as_uri()
            client.notify(
                'textDocument/didOpen',
                {'textDocument': {'uri': uri, 'languageId': language, 'version': 1, 'text': text}},
            )
            try:
                for line, character in positions:
                    budget = min(request_timeout_s, max(deadline - time.monotonic(), 0.0))
                    if budget <= 0:
                        break
                    result = client.request(
                        'textDocument/definition',
                        {'textDocument': {'uri': uri}, 'position': {'line': line, 'character': character}},
                        timeout_s=budget,
                    )
                    for target in _definition_targets(result):
                        if target == path:
                            continue
                        if not _within(target, root):
                            external += 1
                            continue
                        references.add((_rel(path, root), _rel(target, root)))
                    if not result:
                        unresolved += 1
            finally:
                client.notify('textDocument/didClose', {'textDocument': {'uri': uri}})

    except LspTimeout:
        return HarvestOutcome(
            ran=False,
            reason=REASON_SERVER_TIMEOUT.format(binary=binary, budget=timeout_s, phase='harvest'),
            files_scanned=scanned,
            elapsed_s=time.monotonic() - started,
        )
    except (LspServerGone, OSError, ValueError) as exc:
        # A server that died mid-session surfaces three ways depending on timing:
        # EOF on read (LspServerGone), BrokenPipeError on the next write (OSError),
        # or unparseable output (ValueError, which JSONDecodeError subclasses).
        # All three are the same event and must not escape into the crawl — an
        # unhandled exception here would fail discovery outright rather than
        # degrading to a stated no-harvest.
        return HarvestOutcome(
            ran=False,
            reason=REASON_SERVER_GONE.format(binary=binary, phase=f'harvest/{type(exc).__name__}'),
            files_scanned=scanned,
            elapsed_s=time.monotonic() - started,
        )
    finally:
        _shutdown(client, proc)

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


def _definition_targets(result: Any) -> list[Path]:
    """Normalize the three shapes ``textDocument/definition`` may return."""
    if not result:
        return []
    if isinstance(result, dict):
        result = [result]
    targets: list[Path] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        uri = item.get('uri') or item.get('targetUri') or ''
        if uri.startswith('file://'):
            targets.append(Path(uri[len('file://') :]))
    return targets


def _within(path: Path, root: Path) -> bool:
    return root == path or root in path.parents


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _shutdown(client: LspClient, proc: subprocess.Popen) -> None:
    """Close the session, escalating to a kill so no server outlives the crawl."""
    try:
        client.request('shutdown', {}, timeout_s=5.0)
        client.notify('exit', {})
    except (LspTimeout, LspServerGone, OSError, ValueError):
        pass
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
    finally:
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass


# =============================================================================
# The file-to-module lift (D2)
# =============================================================================


def lift_to_modules(
    file_references: Iterable[tuple[str, str]],
    attribute: Callable[[str], str | None],
    known_modules: Iterable[str],
) -> tuple[list[tuple[str, str]], list[str]]:
    """Lift file-granular references to module-granular pairs.

    Symbol references are file-granular; edges are module-granular. The lift
    goes through the path-attribution seam — the ``attribute`` callable is that
    seam's ``path -> owning module`` answer — because a resolver may not invent
    an owner for a path.

    An endpoint the seam cannot attribute produces **no edge and a note**, never
    a guessed module. That is the rule the whole substrate turns on: a
    confidently-labelled wrong edge is worse than a missing one, and this
    function is capable of producing them at volume.

    Args:
        file_references: ``(from_file, to_file)`` repo-relative pairs.
        attribute: Path-attribution seam lookup; returns ``None`` when no
            attributor claims the path.
        known_modules: The discovered module set. An attributed name outside it
            is dropped, since a resolver cannot invent a node.

    Returns:
        ``(edges, notes)`` — sorted deduplicated module pairs, plus one
        aggregated note per non-empty suppression category.
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


def build_lsp_component_refs(
    project_root: str | Path,
    module_paths: dict[str, str],
    *,
    server_cmd: list[str],
    enabled: bool,
    **harvest_kwargs: Any,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Harvest the workspace and project references onto module granularity.

    Args:
        project_root: Project root.
        module_paths: Module name → repo-relative module directory, used as the
            attribution table when the path-attribution seam is unavailable.
        server_cmd: Language-server argv.
        enabled: Whether the harvest is switched on for this project. A disabled
            harvest reports :data:`REASON_DISABLED` rather than running.
        **harvest_kwargs: Forwarded to :func:`harvest_workspace`.

    Returns:
        ``(refs_by_module, status)`` where ``refs_by_module`` maps a module name
        to its ``component_refs`` additions and ``status`` is the record every
        module carries under :data:`HARVEST_STATUS_FIELD`.
    """
    if not enabled:
        return {}, HarvestOutcome(ran=False, reason=REASON_DISABLED).as_status()

    outcome = harvest_workspace(project_root, server_cmd=server_cmd, **harvest_kwargs)
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
    confidently wrong edge. Containment is segment-wise, so ``doc`` does not
    claim ``docs/x``.
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
