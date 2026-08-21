#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Strictly opt-in language server over the marketplace skill corpus.

Answers ``textDocument/definition``, ``textDocument/references`` and
``textDocument/hover`` for skill and script notations, from the dependency index
``tools-marketplace-inventory`` already builds. ⛔ The index is consumed, never
edited.

**Why a resident server rather than a one-shot verb.** Index construction costs
~1.9 s and is paid per process; a warm index answers `definition` and `hover` in
microseconds and `references` in under 5 ms once its per-component file lists are
cached.
A resident server pays that cost **once per process** — on the first request that
needs the index, not at ``initialize``, since :attr:`CorpusLanguageServer.index`
is a lazy property and the handshake builds nothing. Either way it is paid once,
which is the only shape in which this substrate is interactive at all.

⚠ **The staleness bound that buys.** The index is built once and is **never
rebuilt or invalidated** for the life of the process; the ``didOpen`` /
``didChange`` / ``didClose`` handlers update the synced document text — which is
what position resolution reads — and touch nothing else. So **answers may be
stale after an edit**: for the whole session a component added afterwards is
invisible, one removed is still answered for, and the per-file line caches keep
their first-read contents. Restart the server to pick up corpus changes; the
``query`` verb builds a fresh index every call and is always current. Invalidate
-and-debounce is recorded as a proposal rather than implemented — a rebuild costs
a full index build, and the debounce policy is a design decision.

**Opt-in, and where it is enforced.** A plugin-declared LSP server starts
automatically when its plugin is enabled, so the manifest cannot be the opt-in
switch. The switch is ``code_intelligence.corpus_language_server.enabled`` in the
project's ``.plan/marshal.json``. When it is absent or false the server still
starts (the client expects it to) but advertises **no capabilities** and returns
an empty result for every request — the documented no-op path. An unconfigured
project's behaviour is unchanged.

⚠ **No diagnostics are advertised.** Live broken-reference diagnostics are
deliverable D3 of the ``240-skill-lsp-server`` plan, gated on validator
precision: a diagnostic provider inherits that precision, so shipping one while
the unresolved set carries a substantial false-positive share would put
confident-wrong squiggles at the corpus's most visible surface. ⛔ The ~97 %
false-positive figure the gate was originally argued on **no longer holds** —
re-measured, a minority of the remaining unresolved set is false positives.
Whether the gate should therefore come down is an open question recorded as a
proposal, not one this docstring settles.

Output: TOON to stdout for the CLI verbs; JSON-RPC on stdio for ``serve``.
Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

# The sibling skills whose ``scripts/`` directories this script imports from,
# as (bundle, skill) pairs. Resolved at runtime, because the deployed layout is
# not the source layout — see :func:`_bootstrap_sys_path`.
_REQUIRED_SCRIPT_DIRS = (
    ('pm-plugin-development', 'tools-marketplace-inventory'),
    ('plan-marshall', 'tools-file-ops'),
    ('plan-marshall', 'ref-toon-format'),
    ('plan-marshall', 'script-shared'),
    ('plan-marshall', 'manage-logging'),
    ('plan-marshall', 'manage-run-config'),
)


def _version_key(name: str) -> tuple[int, ...]:
    """Order a version directory numerically, not lexically.

    ⚠ A plain string sort puts ``0.1.9`` above ``0.1.62``, which would pick a
    stale bundle whenever the patch number passes single digits. Non-numeric
    segments sort as ``-1`` so a malformed directory never outranks a real
    version.
    """
    parts: list[int] = []
    for segment in name.split('.'):
        parts.append(int(segment) if segment.isdigit() else -1)
    return tuple(parts)


def _own_bundle_root(here: Path) -> Path | None:
    """The nearest ancestor that is a bundle root (holds ``.claude-plugin/plugin.json``)."""
    for ancestor in here.parents:
        if (ancestor / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
    return None


def _resolve_script_dir(root: Path, bundle: str, skill: str) -> Path | None:
    """Find ``{bundle}/skills/{skill}/scripts`` under ``root``, flat or versioned.

    ⚠ **Two layouts differ by exactly one path segment, and assuming either one
    breaks the other.** The source tree keeps bundles as flat siblings
    (``bundles/{bundle}/skills/...``); the deployed plugin cache interposes a
    version (``{bundle}/{version}/skills/...``). Because the imports this feeds
    are module-level, guessing wrong is a start-up crash rather than a degraded
    answer — an earlier flat-only resolver failed with ``ModuleNotFoundError``
    in every installed project.
    """
    direct = root / bundle / 'skills' / skill / 'scripts'
    if direct.is_dir():
        return direct
    versioned = [c for c in root.glob(f'{bundle}/*/skills/{skill}/scripts') if c.is_dir()]
    if not versioned:
        return None
    return max(versioned, key=lambda c: _version_key(c.parents[2].name))


def _bootstrap_sys_path() -> None:
    """Put the sibling skills' ``scripts/`` directories on ``sys.path``.

    ⭐ **This script has two callers with different environments, and only one of
    them is the executor.** Run as an executor verb (``preflight`` / ``query``)
    it needs nothing: the executor injects a ``PYTHONPATH`` covering every
    skill's ``scripts/`` directory. But ``serve`` is spawned **directly by an LSP
    client**, from a declaration an operator adds (no bundle ships one) — so the
    executor is never in the picture and no ``PYTHONPATH`` is injected. That is
    the "entry points that run without the executor" case the
    ``sys-path-bootstrap`` allowlist sanctions.

    Resolution is layout-derived rather than hardcoded, and covers **both** the
    flat source tree and the **versioned** deployed cache. Anchoring on this
    file's own bundle root and searching one and two levels above it finds the
    sibling bundles in either shape. Inserts are idempotent and additive, so
    running under the executor as well is harmless.
    """
    own = _own_bundle_root(Path(__file__).resolve())
    if own is None:
        return  # executor-provided PYTHONPATH is the only route; imports below decide
    # Flat: siblings sit beside our bundle root. Versioned: our root is
    # ``{bundle}/{version}``, so siblings sit one further level up.
    search_roots = [own.parent]
    if own.parent.parent != own.parent:
        search_roots.append(own.parent.parent)
    for bundle, skill in _REQUIRED_SCRIPT_DIRS:
        for root in search_roots:
            directory = _resolve_script_dir(root, bundle, skill)
            if directory is not None:
                resolved = str(directory)
                if resolved not in sys.path:
                    sys.path.insert(0, resolved)
                break
_bootstrap_sys_path()

from _corpus_index import CorpusIndex, notation_at  # noqa: E402
from _corpus_lsp_protocol import LspServer, active_capabilities  # noqa: E402
from file_ops import output_toon, safe_main  # noqa: E402

# Coverage-contract states, mirroring the `lsp-client` skill's vocabulary so a
# consumer reads one contract across both surfaces.
STATE_NOT_CONFIGURED = 'not_configured'  # absent or disabled — the no-op path
STATE_READY = 'ready'  # preflight only: enabled and the index builds
STATE_OK = 'ok'  # a run verb executed (an empty result is then a real answer)

# LSP MessageType.Info — the level a withheld-site report is sent at. Withholding
# is expected behaviour, not a fault, so it is not a warning.
LOG_MESSAGE_INFO = 3

CONFIG_SECTION = 'code_intelligence'
CONFIG_KEY = 'corpus_language_server'
PLAN_DIR_NAME = '.plan'
MARSHAL_FILE = 'marshal.json'

DEFAULT_CORPUS_SUBPATH = ('marketplace', 'bundles')


# =============================================================================
# Configuration surface (D4) — project-local, version-controlled, opt-in
# =============================================================================


def find_project_root(start: Path) -> Path | None:
    """Walk up from ``start`` to the nearest directory holding ``.plan/marshal.json``."""
    resolved = start.resolve()
    for parent in (resolved, *resolved.parents):
        if (parent / PLAN_DIR_NAME / MARSHAL_FILE).is_file():
            return parent
    return None


def read_corpus_config(project_root: Path | None) -> dict[str, Any]:
    """Read the opt-in block, defaulting to disabled.

    Every failure mode — no project root, no ``marshal.json``, malformed JSON, a
    non-dict section — collapses to *not enabled*. ⭐ Failing closed is the point:
    an unreadable configuration must never accidentally switch a surface **on**.
    """
    disabled: dict[str, Any] = {'enabled': False}
    if project_root is None:
        return disabled
    path = project_root / PLAN_DIR_NAME / MARSHAL_FILE
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return disabled
    if not isinstance(data, dict):
        return disabled
    section = data.get(CONFIG_SECTION)
    if not isinstance(section, dict):
        return disabled
    entry = section.get(CONFIG_KEY)
    if not isinstance(entry, dict):
        return disabled
    if entry.get('enabled') is not True:
        return disabled
    return {
        'enabled': True,
        'corpus_path': entry.get('corpus_path') if isinstance(entry.get('corpus_path'), str) else None,
    }


def resolve_corpus_path(project_root: Path | None, config: dict[str, Any]) -> Path | None:
    """Resolve the corpus root the index is built over."""
    if project_root is None:
        return None
    configured = config.get('corpus_path')
    if isinstance(configured, str) and configured:
        candidate = (project_root / configured).resolve()
    else:
        candidate = project_root.joinpath(*DEFAULT_CORPUS_SUBPATH)
    return candidate if candidate.is_dir() else None


# =============================================================================
# URI helpers
# =============================================================================


def uri_to_path(uri: str) -> Path | None:
    """Convert a ``file://`` URI to a path; ``None`` for any other scheme."""
    parsed = urlparse(uri)
    if parsed.scheme != 'file':
        return None
    return Path(unquote(parsed.path))


def path_to_uri(path: Path) -> str:
    """Convert a path to a ``file://`` URI."""
    return path.resolve().as_uri()


def client_root_from(params: dict[str, Any]) -> Path | None:
    """Extract the workspace root a client declares in ``initialize`` params.

    Tried in the LSP's own order of preference: ``rootUri``, then the deprecated
    ``rootPath``, then the first entry of ``workspaceFolders``. Returns ``None``
    when the client declared none of them, or declared one this server cannot
    read as a local path.
    """
    root_uri = params.get('rootUri')
    if isinstance(root_uri, str) and root_uri:
        path = uri_to_path(root_uri)
        if path is not None:
            return path

    root_path = params.get('rootPath')
    if isinstance(root_path, str) and root_path:
        return Path(root_path)

    folders = params.get('workspaceFolders')
    if isinstance(folders, list) and folders:
        first = folders[0]
        if isinstance(first, dict) and isinstance(first.get('uri'), str):
            return uri_to_path(first['uri'])
    return None


# =============================================================================
# The server
# =============================================================================


class CorpusLanguageServer:
    """Wires the resident index to LSP methods, behind the opt-in gate."""

    def __init__(self, project_root: Path | None, config: dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.enabled = bool(config.get('enabled'))
        self.corpus_path = resolve_corpus_path(project_root, config) if self.enabled else None
        self.documents: dict[str, str] = {}
        self._index: CorpusIndex | None = None
        # Server-to-client notification hook, bound by `build_server` when a
        # client is connected. `None` when this object is driven directly.
        self.notify: Callable[[str, dict[str, Any]], None] | None = None
        # How many sites the last `textDocument/references` answer withheld.
        self.last_omitted_unverified = 0

    def adopt_client_root(self, params: dict[str, Any]) -> bool:
        """Re-resolve this server's project from the client's ``initialize`` params.

        The documented editor configuration is the one most likely to omit
        ``--project-path``, and its failure was silent and looked exactly like a
        deliberate opt-out: the project root came only from the CLI, defaulting
        to whatever directory the client happened to launch the server in.

        Only called when ``--project-path`` was **not** given (see
        :func:`build_server`), so an explicit flag still wins.

        Returns:
            Whether a project was adopted. ``False`` leaves this server exactly
            as the CLI configured it.
        """
        root = client_root_from(params)
        if root is None:
            return False
        project_root = find_project_root(root)
        if project_root is None:
            return False
        config = read_corpus_config(project_root)
        self.project_root = project_root
        self.config = config
        self.enabled = bool(config.get('enabled'))
        self.corpus_path = resolve_corpus_path(project_root, config) if self.enabled else None
        self._index = None  # the previous root's index, if any, is now wrong
        return True

    @property
    def index(self) -> CorpusIndex | None:
        """Build the index lazily, once, and only when enabled."""
        if not self.enabled or self.corpus_path is None:
            return None
        if self._index is None:
            self._index = CorpusIndex(self.corpus_path)
        return self._index

    # -- document sync ------------------------------------------------------

    def did_open(self, params: dict[str, Any]) -> None:
        doc = params.get('textDocument') or {}
        uri, text = doc.get('uri'), doc.get('text')
        if isinstance(uri, str) and isinstance(text, str):
            self.documents[uri] = text

    def did_change(self, params: dict[str, Any]) -> None:
        doc = params.get('textDocument') or {}
        uri = doc.get('uri')
        changes = params.get('contentChanges') or []
        if isinstance(uri, str) and changes:
            last = changes[-1]
            if isinstance(last, dict) and isinstance(last.get('text'), str):
                self.documents[uri] = last['text']

    def did_close(self, params: dict[str, Any]) -> None:
        doc = params.get('textDocument') or {}
        uri = doc.get('uri')
        if isinstance(uri, str):
            self.documents.pop(uri, None)

    # -- position resolution ------------------------------------------------

    def notation_at_position(self, params: dict[str, Any]) -> str | None:
        """Resolve the notation token under the request's cursor.

        Prefers the synced document text; falls back to reading the file, so a
        client that never sent ``didOpen`` still gets an answer.
        """
        doc = params.get('textDocument') or {}
        uri = doc.get('uri')
        position = params.get('position') or {}
        line_no = position.get('line')
        character = position.get('character')
        if not isinstance(uri, str) or not isinstance(line_no, int) or not isinstance(character, int):
            return None

        text = self.documents.get(uri)
        if text is None:
            path = uri_to_path(uri)
            if path is None:
                return None
            try:
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                return None

        lines = text.split('\n')
        if not 0 <= line_no < len(lines):
            return None
        return notation_at(lines[line_no], character)

    # -- LSP methods --------------------------------------------------------

    def on_definition(self, params: dict[str, Any]) -> Any:
        index = self.index
        if index is None:
            return None
        notation = self.notation_at_position(params)
        if notation is None:
            return None
        location = index.definition(notation)
        if location is None:
            return None
        return _lsp_location(location.path, location.line)

    def on_references(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the CONFIRMED reference sites, and say how many were withheld.

        LSP has no weaker form than ``Location``: a site the index could not
        confirm, emitted here, reaches an editor as an exact position — and two
        shipped pages promise, in near-identical words, that such a site is never
        presented as one. So an unverified site is omitted rather than downgraded.

        Omission alone would substitute one false signal for another — a silent
        empty result — so the count of withheld sites travels with the answer two
        ways: on each returned ``Location`` as ``omittedUnverifiedCount`` (an
        extra key a client ignores), and as a ``window/logMessage`` notification,
        which is the only channel left when every site was withheld and the list
        is empty.

        The ``query`` verb is unaffected and still emits **every** site with its
        ``verified`` flag; it is the surface where an unconfirmed site is
        legible as unconfirmed.
        """
        index = self.index
        if index is None:
            return []
        notation = self.notation_at_position(params)
        if notation is None:
            return []
        references = index.references(notation)
        confirmed = [ref for ref in references if ref.verified]
        omitted = len(references) - len(confirmed)
        self.last_omitted_unverified = omitted
        if omitted:
            self._report_omitted(notation, omitted, len(references))
        return [
            {**_lsp_location(ref.location.path, ref.location.line), 'omittedUnverifiedCount': omitted}
            for ref in confirmed
        ]

    def _report_omitted(self, notation: str, omitted: int, total: int) -> None:
        """Tell the client that sites were withheld, so an empty list is not read as none."""
        if self.notify is None:
            return
        self.notify('window/logMessage', {
            'type': LOG_MESSAGE_INFO,
            'message': (
                f'{omitted} of {total} reference site(s) for {notation} could not be confirmed against the '
                f'cited line and were omitted; run `corpus_lsp query --kind references` to see them with '
                f'their verified flag'
            ),
        })

    def on_hover(self, params: dict[str, Any]) -> Any:
        index = self.index
        if index is None:
            return None
        notation = self.notation_at_position(params)
        if notation is None:
            return None
        payload = index.hover(notation)
        if payload is None:
            return None
        return {'contents': {'kind': 'markdown', 'value': _render_hover(payload)}}


def _lsp_location(path: Path, line: int) -> dict[str, Any]:
    """An LSP Location covering the whole line — the index's resolution."""
    return {
        'uri': path_to_uri(path),
        'range': {
            'start': {'line': line, 'character': 0},
            'end': {'line': line, 'character': 0},
        },
    }


def _render_hover(payload: dict[str, Any]) -> str:
    """Render the hover payload as Markdown: description plus frontmatter."""
    lines = [f'**{payload["notation"]}** — `{payload["kind"]}`']
    description = payload.get('description')
    if description:
        lines.extend(['', str(description)])
    frontmatter = payload.get('frontmatter') or {}
    if frontmatter:
        lines.append('')
        for key in sorted(frontmatter):
            lines.append(f'- `{key}`: {frontmatter[key]}')
    lines.extend(
        [
            '',
            f'_{payload.get("inbound_edges", 0)} inbound, '
            f'{payload.get("outbound_edges", 0)} outbound edges in the index_',
        ]
    )
    return '\n'.join(lines)


def build_server(
    project_root: Path | None,
    config: dict[str, Any],
    *,
    project_path_explicit: bool = True,
) -> tuple[LspServer, CorpusLanguageServer]:
    """Assemble the JSON-RPC server and register the corpus handlers.

    Args:
        project_root: Project root resolved from the CLI, or ``None``.
        config: The corpus config read from that root.
        project_path_explicit: Whether ``--project-path`` was actually passed.
            When it was not, the ``initialize`` handler adopts the root the
            client declares — the case the documented editor block produces, and
            the one whose failure looked exactly like a deliberate opt-out. An
            explicit flag always wins, so the documented block's behaviour is
            unchanged for anyone who passes it.
    """
    corpus = CorpusLanguageServer(project_root, config)
    rpc = LspServer(enabled=corpus.enabled)
    corpus.notify = rpc.notify

    def _on_initialize(params: dict[str, Any]) -> dict[str, Any]:
        if not project_path_explicit and corpus.adopt_client_root(params):
            # Capabilities are derived from `enabled`, which adopting may have
            # changed, so the roster is rebuilt BEFORE it is advertised.
            rpc.enabled = corpus.enabled
        return {'capabilities': rpc.capabilities()}

    rpc.register('initialize', _on_initialize)
    rpc.register('initialized', lambda params: None)
    rpc.register('textDocument/didOpen', lambda params: corpus.did_open(params))
    rpc.register('textDocument/didChange', lambda params: corpus.did_change(params))
    rpc.register('textDocument/didClose', lambda params: corpus.did_close(params))
    rpc.register('textDocument/definition', corpus.on_definition)
    rpc.register('textDocument/references', corpus.on_references)
    rpc.register('textDocument/hover', corpus.on_hover)
    return rpc, corpus


# =============================================================================
# CLI verbs
# =============================================================================


def _context(args: argparse.Namespace) -> tuple[Path | None, dict[str, Any]]:
    project_root = find_project_root(Path(args.project_path or '.'))
    return project_root, read_corpus_config(project_root)


def cmd_preflight(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether the surface is enabled, and whether its index builds."""
    project_root, config = _context(args)
    if not config.get('enabled'):
        return {
            'status': 'degraded',
            'state': STATE_NOT_CONFIGURED,
            'configured': False,
            'provider_count': 0,
            'fallback': 'read_grep',
            'config_key': f'{CONFIG_SECTION}.{CONFIG_KEY}.enabled',
        }
    corpus_path = resolve_corpus_path(project_root, config)
    if corpus_path is None:
        return {
            'status': 'degraded',
            'state': STATE_NOT_CONFIGURED,
            'configured': True,
            'provider_count': 0,
            'fallback': 'read_grep',
            'reason': 'configured corpus path does not exist',
        }
    index = CorpusIndex(corpus_path)
    stats = index.stats()
    return {
        'status': 'success',
        'state': STATE_READY,
        'configured': True,
        'provider_count': 1,
        'capabilities': sorted(active_capabilities()),
        **stats,
    }


def cmd_query(args: argparse.Namespace) -> dict[str, Any]:
    """Answer one lookup without a client — the same answers ``serve`` gives."""
    project_root, config = _context(args)
    if not config.get('enabled'):
        return {
            'status': 'degraded',
            'state': STATE_NOT_CONFIGURED,
            'provider_count': 0,
            'fallback': 'read_grep',
            'notation': args.notation,
        }
    corpus_path = resolve_corpus_path(project_root, config)
    if corpus_path is None:
        return {
            'status': 'degraded',
            'state': STATE_NOT_CONFIGURED,
            'provider_count': 0,
            'fallback': 'read_grep',
            'reason': 'configured corpus path does not exist',
        }
    index = CorpusIndex(corpus_path)
    payload: dict[str, Any] = {
        'status': 'success',
        'state': STATE_OK,
        'provider_count': 1,
        'kind': args.kind,
        'notation': args.notation,
        'known': index.knows(args.notation),
    }
    if args.kind == 'definition':
        location = index.definition(args.notation)
        payload['definition'] = location.as_dict() if location else None
    elif args.kind == 'references':
        references = [ref.as_dict() for ref in index.references(args.notation)]
        payload['references'] = references
        payload['reference_count'] = len(references)
        payload['verified_count'] = sum(1 for r in references if r['verified'])
        payload['completeness_note'] = (
            'bounded by index coverage — an empty result means the index found no '
            'inbound edge, not that the corpus contains none'
        )
    else:
        payload['hover'] = index.hover(args.notation)
    return payload


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the JSON-RPC loop on stdio. Starts even when not enabled (a no-op)."""
    project_root, config = _context(args)
    rpc, _corpus = build_server(project_root, config, project_path_explicit=args.project_path is not None)
    return rpc.serve(sys.stdin.buffer, sys.stdout.buffer)


# =============================================================================
# CLI
# =============================================================================


def _add_project_path(parser: argparse.ArgumentParser) -> None:
    # Default `None`, not '.', so the code can tell "not given" from "given as
    # the cwd" — `serve` adopts the client's declared root only in the first
    # case. Every reader spells the fallback as `args.project_path or '.'`, so
    # the effective default is unchanged.
    parser.add_argument(
        '--project-path',
        default=None,
        help=(
            'Project root to resolve config from. An explicit value always wins. '
            'Omitted, `serve` adopts the root the client declares at initialize '
            '(rootUri, rootPath, then workspaceFolders[0]) and falls back to the cwd '
            'only when the client declares none; the other verbs use the cwd.'
        ),
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Opt-in language server over the marketplace skill corpus',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    p_preflight = subparsers.add_parser('preflight', help='Report enabled/index state', allow_abbrev=False)
    _add_project_path(p_preflight)
    p_preflight.set_defaults(func=cmd_preflight)

    p_query = subparsers.add_parser('query', help='Answer one lookup without an LSP client', allow_abbrev=False)
    _add_project_path(p_query)
    p_query.add_argument('--kind', required=True, choices=['definition', 'references', 'hover'])
    p_query.add_argument('--notation', required=True, help='Component notation, e.g. bundle:skill or bundle:skill:script')
    p_query.set_defaults(func=cmd_query)

    p_serve = subparsers.add_parser('serve', help='Run the LSP server on stdio', allow_abbrev=False)
    _add_project_path(p_serve)
    p_serve.set_defaults(func=None)

    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    if args.command == 'serve':
        return cmd_serve(args)
    output_toon(args.func(args))
    return 0


@safe_main
def _main() -> int:
    return main()


def _entry() -> int:
    """Route ``serve`` around ``@safe_main``.

    ``safe_main``'s contract is TOON-on-stdout, which is correct for a verb and
    fatal for a stdio protocol channel: an escaping exception would append
    ``status: error`` to the byte stream a client is still parsing as
    ``Content-Length`` frames, corrupting every message after it. ``serve``
    contains its own failures (see ``_corpus_lsp_protocol.LspServer.serve``) and
    reports them on stderr, so it needs no such wrapper — it needs to be kept
    out of one.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()
    if args.command == 'serve':
        return cmd_serve(args)
    # `_main` is the @safe_main-wrapped path and exits the process itself, so
    # nothing after this line runs for a TOON verb.
    _main()
    return 0


if __name__ == '__main__':
    sys.exit(_entry())
