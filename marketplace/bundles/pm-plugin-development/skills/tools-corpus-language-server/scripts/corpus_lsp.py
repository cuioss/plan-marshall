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
A resident server pays that cost once at ``initialize``, which is the only shape
in which this substrate is interactive at all.

**Opt-in, and where it is enforced.** A plugin-declared LSP server starts
automatically when its plugin is enabled, so the manifest cannot be the opt-in
switch. The switch is ``code_intelligence.corpus_language_server.enabled`` in the
project's ``.plan/marshal.json``. When it is absent or false the server still
starts (the client expects it to) but advertises **no capabilities** and returns
an empty result for every request — the documented no-op path. An unconfigured
project's behaviour is unchanged.

⚠ **No diagnostics are advertised.** Live broken-reference diagnostics are
deliverable D3 of the ``240-skill-lsp-server`` plan, hard-gated on the
validator-precision work: the validator's current unresolved set is
overwhelmingly false positives, so a diagnostic provider would ship
confident-wrong squiggles at the corpus's most visible surface.

Output: TOON to stdout for the CLI verbs; JSON-RPC on stdio for ``serve``.
Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def _bootstrap_sys_path() -> None:
    """Put the sibling skills' ``scripts/`` directories on ``sys.path``.

    ⭐ **This script has two callers with different environments, and only one of
    them is the executor.** Run as an executor verb it needs nothing: the
    executor injects a ``PYTHONPATH`` covering every skill's ``scripts/``
    directory. But the ``serve`` verb is spawned **directly by an LSP client**
    from the plugin manifest's ``lspServers`` declaration — no executor, and
    therefore no ``PYTHONPATH`` — which is exactly the "pre-executor entry point"
    case the ``sys-path-bootstrap`` allowlist sanctions.

    Resolution walks up from this file to the bundles root (the ancestor holding
    sibling bundle directories, each with a ``.claude-plugin/plugin.json``), so
    it is layout-derived rather than hardcoded and works identically in the
    source tree and in a deployed plugin cache, where bundles are likewise
    siblings. Inserts are idempotent and additive, so running under the executor
    as well is harmless.
    """
    here = Path(__file__).resolve()
    bundles_root: Path | None = None
    for ancestor in here.parents:
        if (ancestor / 'pm-plugin-development' / '.claude-plugin' / 'plugin.json').is_file():
            bundles_root = ancestor
            break
    if bundles_root is None:
        return  # executor-provided PYTHONPATH is the only route; imports below decide
    needed = [
        bundles_root / 'pm-plugin-development' / 'skills' / 'tools-marketplace-inventory' / 'scripts',
        bundles_root / 'plan-marshall' / 'skills' / 'tools-file-ops' / 'scripts',
        bundles_root / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts',
        bundles_root / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts',
        bundles_root / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts',
        bundles_root / 'plan-marshall' / 'skills' / 'manage-run-config' / 'scripts',
    ]
    for directory in needed:
        resolved = str(directory)
        if directory.is_dir() and resolved not in sys.path:
            sys.path.insert(0, resolved)


_bootstrap_sys_path()

from _corpus_index import CorpusIndex, notation_at  # noqa: E402
from _corpus_lsp_protocol import LspServer, active_capabilities  # noqa: E402
from file_ops import output_toon, safe_main  # noqa: E402

# Coverage-contract states, mirroring the `lsp-client` skill's vocabulary so a
# consumer reads one contract across both surfaces.
STATE_NOT_CONFIGURED = 'not_configured'  # absent or disabled — the no-op path
STATE_READY = 'ready'  # preflight only: enabled and the index builds
STATE_OK = 'ok'  # a run verb executed (an empty result is then a real answer)

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
        index = self.index
        if index is None:
            return []
        notation = self.notation_at_position(params)
        if notation is None:
            return []
        return [_lsp_location(ref.location.path, ref.location.line) for ref in index.references(notation)]

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


def build_server(project_root: Path | None, config: dict[str, Any]) -> tuple[LspServer, CorpusLanguageServer]:
    """Assemble the JSON-RPC server and register the corpus handlers."""
    corpus = CorpusLanguageServer(project_root, config)
    rpc = LspServer(enabled=corpus.enabled)

    rpc.register('initialize', lambda params: {'capabilities': rpc.capabilities()})
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
    project_root = find_project_root(Path(args.project_path))
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
    rpc, _corpus = build_server(project_root, config)
    return rpc.serve(sys.stdin.buffer, sys.stdout.buffer)


# =============================================================================
# CLI
# =============================================================================


def _add_project_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--project-path', default='.', help='Project root to resolve config from (default: cwd)')


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


if __name__ == '__main__':
    _main()
