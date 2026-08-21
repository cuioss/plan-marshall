#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Opt-in LSP client for phase-5-execute — lookup, edit, diagnose.

A dispatched leaf reaches a warm language server for the two things a server is
better at than reading files: **locating** work by coordinate and applying a
**verified multi-file edit**. The server is hosted *inside the envelope* — a
short-lived subprocess of this script, booted per call and torn down on exit
(the D0 hosting decision) — so there is no daemon, no socket, and no long-lived
child to trust.

Every verb carries the substrate's coverage contract: the caller can always tell
*no server ran* (``provider_count: 0``, ``state: not_configured`` /
``unreachable``) from *the server ran and found nothing* (``provider_count: 1``,
``state: ok`` with an empty result). A silent empty result — the archetype the
code-intelligence epic exists to remove — is not representable here.

The write side (:func:`_run_edit`) applies a ``WorkspaceEdit`` through the
recorded footprint-capturing path (:mod:`_lsp_workspace_edit`): the footprint is
taken *from the edit itself*, the edit is verified *after* application by
re-running diagnostics, and a **worsened diagnostic set fails the step** (and is
rolled back). An edit nobody read is at minimum an edit the parser re-checked.

**Diagnostics supplement the quality gate; they do not replace it.** The
``diagnose`` verb surfaces the class of errors a server sees ahead of the build
round-trip (unresolved imports, syntax, type errors); it is a pre-build signal,
never a substitute for ``./pw verify``.

Opt-in: for an unconfigured project the client returns a ``degraded`` no-op (no
mutation, no server contact) and the leaf takes today's ``Read`` / ``Edit`` path,
so the outcome is byte-identical to today. See the ``language_servers`` section in
``manage-run-config`` for the machine-local configuration surface.

Output: TOON to stdout. Stdlib only.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _lsp_jsonrpc import LspError, LspSession, StdioTransport, default_analysis_config
from _lsp_workspace_edit import (
    WorkspaceApplyError,
    apply_workspace_edit,
    capture_footprint,
    count_error_diagnostics,
    diagnostic_delta,
    edit_verdict,
    normalize_changes,
    restore_files,
    uri_to_path,
)
from file_ops import output_toon, safe_main
from run_config import get_run_config_path, read_run_config

# Client outcome states — the coverage-contract discriminator.
STATE_NOT_CONFIGURED = 'not_configured'  # no server configured/enabled for the language
STATE_UNREACHABLE = 'unreachable'  # configured, but the server did not start/initialise
STATE_OK = 'ok'  # a run verb's server ran (an empty result is then a real answer)
STATE_READY = 'ready'  # preflight only: configured AND reachable (the precondition for STATE_OK)
STATE_UNKNOWN = 'unknown'  # the server ran but published no verdict for the file — not "clean"

# Failure reasons the write path returns. Each names a distinct cause, so a leaf
# reading only the reason can tell "the edit was wrong" from "we could not check".
REASON_DIAGNOSTICS_WORSENED = 'diagnostics_worsened'  # the parser found NEW errors — the edit was wrong
REASON_DIAGNOSTICS_UNAVAILABLE = 'diagnostics_unavailable'  # no verdict was obtainable — verify by build
REASON_UNSUPPORTED_RESOURCE_OPERATION = 'unsupported_resource_operation'  # create/rename/delete file
REASON_APPLY_FAILED = 'apply_failed'  # a file failed mid-apply; the change was rolled back
REASON_DIAGNOSTICS_UNANSWERED = 'diagnostics_unanswered'  # diagnose: the server published no verdict

# The D3 boundary, carried in every diagnose payload so a consumer cannot read
# the signal as a gate replacement even when it reads only the machine output.
DIAGNOSTICS_BOUNDARY_NOTE = (
    'diagnostics supplement the quality gate; they do not replace it — run the '
    'canonical build (./pw verify) before relying on a clean result'
)


# =============================================================================
# Configuration surface (reads the shared machine-local run-configuration store)
# =============================================================================


def select_language_server(config: dict[str, Any], language: str) -> dict[str, Any] | None:
    """Return the enabled server entry for ``language``, or ``None`` (pure).

    ``None`` means *not configured* — the section is absent, the language is
    absent, the entry is explicitly disabled, or its command is missing. All of
    those collapse to the opt-out path, distinct from *configured but
    unreachable* which only a spawn attempt can establish.
    """
    section = config.get('language_servers')
    if not isinstance(section, dict):
        return None
    entry = section.get(language)
    if not isinstance(entry, dict):
        return None
    if not entry.get('enabled', True):
        return None
    command = entry.get('command')
    if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
        return None
    language_id = entry.get('language_id')
    return {
        'command': list(command),
        'language_id': language_id if isinstance(language_id, str) else language,
    }


def resolve_language_server(language: str) -> dict[str, Any] | None:
    """Resolve the enabled server entry for ``language`` from the run-config store."""
    return select_language_server(read_run_config(get_run_config_path()), language)


def analysis_config_with_extra_paths(extra_paths: list[str]) -> dict[str, Any]:
    """This client's analysis settings, plus a module search path for bare imports.

    A server rooted at the project root resolves an import the way the
    interpreter would from that root. Where a project's own scripts import each
    other by bare name — satisfied at runtime by a launcher that puts their
    directory on ``sys.path`` — that is the wrong root and **nothing** resolves.
    ``extraPaths`` hands the server the same search path.

    Deriving *which* paths is the caller's job, since it depends on how that
    project is laid out and launched; assembling them into the settings this
    client speaks is this module's.

    Args:
        extra_paths: Absolute directories to add to the server's search path.

    Returns:
        A config accepted by :class:`StdioTransport` and :class:`LspSession` as
        ``analysis_config``. Pass it to **both**: a server may read its settings
        from the handshake, from a ``workspace/configuration`` pull, or from
        both, and the two must not disagree.
    """
    config = default_analysis_config()
    config['extraPaths'] = list(extra_paths)
    return config


# =============================================================================
# Payload helpers
# =============================================================================


def _degraded(state: str, language: str, **extra: Any) -> dict[str, Any]:
    """Build the fail-soft payload the leaf reads as 'fall back to Read/Edit'."""
    payload: dict[str, Any] = {
        'status': 'degraded',
        'state': state,
        'language': language,
        'provider_count': 0,
        'fallback': 'read_edit',
    }
    payload.update(extra)
    return payload


def _location_rows(locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten LSP Location / SymbolInformation objects into coordinate rows."""
    rows: list[dict[str, Any]] = []
    for item in locations:
        location = item.get('location') if 'location' in item else item
        if not isinstance(location, dict):
            continue
        rng = location.get('range') or {}
        start = rng.get('start') or {}
        end = rng.get('end') or {}
        row: dict[str, Any] = {
            'path': uri_to_path(location.get('uri', '')),
            'line': start.get('line', 0),
            'character': start.get('character', 0),
            'end_line': end.get('line', 0),
            'end_character': end.get('character', 0),
        }
        if 'name' in item:
            row['name'] = item.get('name')
        rows.append(row)
    return rows


def _symbol_rows(symbols: list[dict[str, Any]], default_path: str = '') -> list[dict[str, Any]]:
    """Flatten documentSymbol / workspace symbol results into coordinate rows.

    Every row carries ``path``. Without it a ``workspace-symbol`` row — the only
    lookup kind that spans files — gives a line number and no file, which is
    exactly the ``Grep``/``Read`` round-trip this capability exists to remove.
    ``SymbolInformation`` rows take it from the server's ``location.uri``;
    hierarchical ``DocumentSymbol`` rows have no ``location``, so the caller
    passes the queried file as ``default_path`` and both kinds emit one key set.

    The walk is depth-first through ``children``, so a class's methods appear
    rather than only the top level the client's
    ``hierarchicalDocumentSymbolSupport`` asked the server to send. Each row
    records its ``container`` (the enclosing symbol's name, or the server's
    ``containerName`` for a flat result) and its ``depth``.
    """
    rows: list[dict[str, Any]] = []

    def _walk(items: list[dict[str, Any]], container: str, depth: int) -> None:
        for symbol in items:
            if not isinstance(symbol, dict):
                continue
            rng = symbol.get('selectionRange') or symbol.get('range') or {}
            path = default_path
            location = symbol.get('location')
            if isinstance(location, dict):
                rng = location.get('range') or rng
                path = uri_to_path(location.get('uri', '')) or default_path
            start = rng.get('start') or {}
            name = symbol.get('name', '')
            rows.append({
                'name': name,
                'kind': symbol.get('kind', 0),
                'path': path,
                'line': start.get('line', 0),
                'character': start.get('character', 0),
                'container': container or symbol.get('containerName', '') or '',
                'depth': depth,
            })
            children = symbol.get('children')
            if isinstance(children, list):
                _walk(children, name, depth + 1)

    _walk(symbols, '', 0)
    return rows


# =============================================================================
# Verb logic (operate on an LspSession — the transport is injectable for tests)
# =============================================================================


def _run_lookup(
    session: LspSession,
    language: str,
    kind: str,
    path: str | None,
    line: int,
    character: int,
    symbol: str | None,
) -> dict[str, Any]:
    """Run a read-side lookup against a running server, returning coordinates."""
    if kind == 'workspace-symbol':
        rows = _symbol_rows(session.workspace_symbol(symbol or ''))
    elif kind == 'document-symbol':
        assert path is not None
        session.open(path)
        rows = _symbol_rows(session.document_symbols(path), default_path=str(Path(path).resolve()))
    elif kind == 'definition':
        assert path is not None
        session.open(path)
        rows = _location_rows(session.definition(path, line, character))
    elif kind == 'references':
        assert path is not None
        session.open(path)
        rows = _location_rows(session.references(path, line, character))
    else:  # pragma: no cover - argparse choices prevent this
        raise ValueError(f'unknown lookup kind: {kind}')
    return {
        'status': 'success',
        'state': STATE_OK,
        'language': language,
        'kind': kind,
        'provider_count': 1,
        'location_count': len(rows),
        'locations': rows,
    }


def _edit_failure(language: str, reason: str, footprint: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    """Build the write path's failure payload.

    ⛔ This helper does **not** decide what is on disk. Four reasons reach it,
    each in a different state, and each caller passes whatever ``rolled_back``
    its own state warrants:

    * ``unsupported_resource_operation`` — refused before anything was read, so
      it passes **no** ``rolled_back`` at all and the key is absent from the
      payload. Nothing was written and nothing was rolled back;
    * ``diagnostics_unavailable`` at phase ``before`` — the baseline verdict was
      missing, detected before the first write: ``rolled_back=False`` meaning
      *there was nothing to roll back*;
    * ``diagnostics_unavailable`` at phase ``after`` and ``diagnostics_worsened``
      — written, then restored: ``rolled_back=True``;
    * ``apply_failed`` — restored, unless the tree could not be put back, which
      is the one case that leaves it partly edited and is reported as
      ``rolled_back=False`` **plus** ``restore_error``. That is a statement
      about the tree, re-read from disk: a write refused before it touched
      anything makes its own restore fail too, and reporting *that* would raise
      an alarm over a clean tree.
    """
    payload: dict[str, Any] = {
        'status': 'failed',
        'state': STATE_OK,
        'language': language,
        'provider_count': 1,
        'applied': False,
        'reason': reason,
        'file_count': len(footprint),
        'files': footprint,
    }
    payload.update(extra)
    return payload


def _run_edit(session: LspSession, language: str, path: str, line: int, character: int, new_name: str) -> dict[str, Any]:
    """Rename a symbol via a WorkspaceEdit, capture footprint, apply, re-verify.

    The footprint is captured from the edit; the edit is applied all-or-nothing;
    diagnostics are re-run over exactly the footprint files, each wait requiring
    a push **newer** than the pre-change one; and a file that gained an error
    diagnostic fails the step and rolls the whole change back.

    The verb **fails closed** in three further ways, each of which used to be
    reported as a pass:

    * an edit carrying a create/rename/delete-file resource operation is refused
      whole (``unsupported_resource_operation``) rather than applied minus the
      part this client cannot perform;
    * a failure part-way through the apply loop restores every file already
      written and reports the offending path (``apply_failed``) — and when the
      restore itself fails, ``rolled_back`` is ``False`` and ``restore_error``
      carries the cause, because a partly-edited tree must not read as clean;
    * a file the server returns **no verdict** for is unverified, not clean
      (``diagnostics_unavailable``) — see ``lsp-client/SKILL.md`` § "The write
      side" for what a leaf should do with that.
    """
    session.open(path)
    workspace_edit = session.rename(path, line, character, new_name)
    _changes, notes = normalize_changes(workspace_edit)
    footprint = capture_footprint(workspace_edit)

    if notes:
        # A resource operation cannot be performed here. Applying the text-edit
        # remainder would land a partial refactor reported as a success.
        return _edit_failure(
            language, REASON_UNSUPPORTED_RESOURCE_OPERATION, footprint,
            notes=notes, unapplied_operation_count=len(notes),
        )

    if not footprint:
        return {
            'status': 'success',
            'state': STATE_OK,
            'language': language,
            'provider_count': 1,
            'applied': False,
            'reason': 'no_workspace_edit',
            'file_count': 0,
            'files': [],
        }

    paths = [row['path'] for row in footprint]
    before_by_path: dict[str, list[dict[str, Any]]] = {}
    errors_before = 0
    for target in paths:
        session.open(target)
        diagnostics = session.diagnostics(target)
        if diagnostics is None:
            # No baseline verdict — nothing has been written yet, so there is
            # nothing to roll back, but the edit cannot be verified either.
            return _edit_failure(
                language, REASON_DIAGNOSTICS_UNAVAILABLE, footprint,
                rolled_back=False, unverified_path=target, phase='before',
            )
        before_by_path[target] = diagnostics
        errors_before += count_error_diagnostics(diagnostics)

    try:
        _applied_footprint, originals = apply_workspace_edit(workspace_edit)
    except WorkspaceApplyError as exc:
        payload = _edit_failure(
            language, REASON_APPLY_FAILED, footprint,
            failed_path=exc.path,
            rolled_back=exc.restore_error is None,
            detail=str(exc.cause),
        )
        if exc.restore_error is not None:
            payload['restore_error'] = str(exc.restore_error)
        return payload

    errors_after = 0
    added_by_path: dict[str, list[dict[str, Any]]] = {}
    new_diagnostics: list[dict[str, Any]] = []
    for target in paths:
        seq_before_change = session.change_to_disk(target)
        diagnostics = session.diagnostics(target, after_seq=seq_before_change)
        if diagnostics is None:
            restore_files(originals)
            return _edit_failure(
                language, REASON_DIAGNOSTICS_UNAVAILABLE, footprint,
                rolled_back=True, unverified_path=target, phase='after',
                errors_before=errors_before,
            )
        errors_after += count_error_diagnostics(diagnostics)
        added, _removed = diagnostic_delta(before_by_path[target], diagnostics)
        added_by_path[target] = added
        new_diagnostics.extend(
            {
                'path': target,
                'line': (diag.get('range') or {}).get('start', {}).get('line', 0),
                'message': diag.get('message', ''),
            }
            for diag in added
        )

    verdict = edit_verdict(added_by_path)
    if verdict == 'failed':
        restore_files(originals)
        return _edit_failure(
            language, REASON_DIAGNOSTICS_WORSENED, footprint,
            rolled_back=True,
            errors_before=errors_before,
            errors_after=errors_after,
            new_diagnostic_count=len(new_diagnostics),
            new_diagnostics=new_diagnostics,
        )
    return {
        'status': 'success',
        'state': STATE_OK,
        'language': language,
        'provider_count': 1,
        'applied': True,
        'verdict': verdict,
        'errors_before': errors_before,
        'errors_after': errors_after,
        'file_count': len(footprint),
        'files': footprint,
    }


def _run_diagnose(session: LspSession, language: str, path: str) -> dict[str, Any]:
    """Return diagnostics for ``path`` as a pre-build correctness signal.

    ``answered`` is the field that separates the two outcomes a count cannot:
    ``answered: true`` with ``error_count: 0`` means the server examined the file
    and found nothing, while ``state: unknown`` / ``answered: false`` means it
    published no verdict at all — a server that never pushes diagnostics, or a
    wait that expired. The unknown payload deliberately carries **no**
    ``error_count``, ``warning_count`` or ``diagnostics``: a zero there is the
    false clean signal this verb exists not to emit.
    """
    session.open(path)
    diagnostics = session.diagnostics(path)
    if diagnostics is None:
        return {
            'status': 'success',
            'state': STATE_UNKNOWN,
            'language': language,
            'provider_count': 1,
            'file': path,
            'answered': False,
            'reason': REASON_DIAGNOSTICS_UNANSWERED,
            'boundary_note': DIAGNOSTICS_BOUNDARY_NOTE,
        }
    rows = [
        {
            'severity': diag.get('severity', 0),
            'line': (diag.get('range') or {}).get('start', {}).get('line', 0),
            'character': (diag.get('range') or {}).get('start', {}).get('character', 0),
            'message': diag.get('message', ''),
            'code': str(diag.get('code', '')),
        }
        for diag in diagnostics
    ]
    return {
        'status': 'success',
        'state': STATE_OK,
        'language': language,
        'provider_count': 1,
        'file': path,
        'answered': True,
        'error_count': count_error_diagnostics(diagnostics),
        'warning_count': sum(1 for diag in diagnostics if diag.get('severity') == 2),
        'diagnostics': rows,
        'boundary_note': DIAGNOSTICS_BOUNDARY_NOTE,
    }


# =============================================================================
# Verb entry points (resolve config, spawn the server, degrade fail-soft)
# =============================================================================


def _session(server: dict[str, Any], root: str) -> LspSession:
    """Spawn the configured server and return an initialised session."""
    transport = StdioTransport(server['command'], cwd=root)
    session = LspSession(transport, root)
    session.initialize()
    return session


def cmd_preflight(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether an LSP server is configured and reachable for a language."""
    server = resolve_language_server(args.language)
    if server is None:
        return {
            'status': 'success',
            'state': STATE_NOT_CONFIGURED,
            'language': args.language,
            'configured': False,
            'reachable': False,
        }
    try:
        session = _session(server, str(Path(args.project_path).resolve()))
        session.close()
    except (LspError, OSError) as exc:
        return {
            'status': 'success',
            'state': STATE_UNREACHABLE,
            'language': args.language,
            'configured': True,
            'reachable': False,
            'reason': str(exc),
        }
    return {
        'status': 'success',
        'state': STATE_READY,
        'language': args.language,
        'configured': True,
        'reachable': True,
    }


def _with_session(args: argparse.Namespace, run: Any) -> dict[str, Any]:
    """Resolve config, spawn a session, run ``run(session)``, degrade fail-soft."""
    server = resolve_language_server(args.language)
    if server is None:
        return _degraded(STATE_NOT_CONFIGURED, args.language)
    try:
        session = _session(server, str(Path(args.project_path).resolve()))
    except (LspError, OSError) as exc:
        return _degraded(STATE_UNREACHABLE, args.language, reason=str(exc))
    try:
        result = run(session)
        assert isinstance(result, dict)
        return result
    finally:
        session.close()


def cmd_lookup(args: argparse.Namespace) -> dict[str, Any]:
    """Locate a symbol by coordinate without reading the containing files."""
    path = str(Path(args.file).resolve()) if args.file else None
    if args.kind in ('definition', 'references', 'document-symbol') and path is None:
        return {'status': 'error', 'error': 'missing_file', 'message': f'--file is required for kind={args.kind}'}
    if args.kind == 'workspace-symbol' and not args.symbol:
        return {'status': 'error', 'error': 'missing_symbol', 'message': '--symbol is required for kind=workspace-symbol'}
    return _with_session(
        args,
        lambda session: _run_lookup(session, args.language, args.kind, path, args.line, args.character, args.symbol),
    )


def cmd_edit(args: argparse.Namespace) -> dict[str, Any]:
    """Apply a symbol rename as a verified, footprint-captured WorkspaceEdit."""
    path = str(Path(args.file).resolve())
    return _with_session(
        args,
        lambda session: _run_edit(session, args.language, path, args.line, args.character, args.new_name),
    )


def cmd_diagnose(args: argparse.Namespace) -> dict[str, Any]:
    """Return diagnostics for a file as a pre-build correctness signal."""
    path = str(Path(args.file).resolve())
    return _with_session(args, lambda session: _run_diagnose(session, args.language, path))


# =============================================================================
# CLI
# =============================================================================


def _add_language(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--language', default='python', help='Language key in the run-config language_servers section')
    parser.add_argument('--project-path', default='.', help='Workspace root the server opens (default: cwd)')


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Opt-in LSP client: locate work by coordinate and apply verified edits',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    p_preflight = subparsers.add_parser('preflight', help='Report configured/reachable state', allow_abbrev=False)
    _add_language(p_preflight)
    p_preflight.set_defaults(func=cmd_preflight)

    p_lookup = subparsers.add_parser('lookup', help='Locate a symbol by coordinate', allow_abbrev=False)
    _add_language(p_lookup)
    p_lookup.add_argument(
        '--kind', required=True, choices=['definition', 'references', 'document-symbol', 'workspace-symbol']
    )
    p_lookup.add_argument('--file', help='File to query (required except for workspace-symbol)')
    p_lookup.add_argument('--line', type=int, default=0, help='0-based line for definition/references')
    p_lookup.add_argument('--character', type=int, default=0, help='0-based character for definition/references')
    p_lookup.add_argument('--symbol', help='Symbol name for workspace-symbol')
    p_lookup.set_defaults(func=cmd_lookup)

    p_edit = subparsers.add_parser('edit', help='Apply a verified symbol rename', allow_abbrev=False)
    _add_language(p_edit)
    p_edit.add_argument('--file', required=True, help='File containing the symbol to rename')
    p_edit.add_argument('--line', type=int, required=True, help='0-based line of the symbol')
    p_edit.add_argument('--character', type=int, required=True, help='0-based character of the symbol')
    p_edit.add_argument('--new-name', required=True, help='New symbol name')
    p_edit.set_defaults(func=cmd_edit)

    p_diagnose = subparsers.add_parser('diagnose', help='Diagnostics as a pre-build signal', allow_abbrev=False)
    _add_language(p_diagnose)
    p_diagnose.add_argument('--file', required=True, help='File to diagnose')
    p_diagnose.set_defaults(func=cmd_diagnose)

    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    output_toon(args.func(args))
    return 0


@safe_main
def _main() -> int:
    return main()


if __name__ == '__main__':
    _main()
