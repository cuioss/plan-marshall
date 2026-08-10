#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure ``WorkspaceEdit`` helpers — the D2 footprint-capturing apply path.

This module holds every operation that turns a language server's
``WorkspaceEdit`` into a change on disk, with **no** live server dependency, so
the write side's core logic is deterministically testable offline:

* the **footprint is captured from the edit itself** (``capture_footprint``),
  never derived from a later ``git diff`` — the binding design rule the plan
  requires D2 to ship rather than assert;
* the edit is **applied** bottom-up to preserve positions (``apply_text_edits`` /
  ``apply_workspace_edit``), returning the original file contents so a worsened
  post-application diagnostic set can be **rolled back** (``restore_files``);
* the pre/post error counts drive an explicit ``edit_verdict`` — a *worsened*
  set fails the step.

LSP positions are 0-based ``{line, character}`` where ``character`` is a UTF-16
code-unit offset. For the BMP (all identifiers and virtually all source text)
that equals a Python ``str`` index; astral-plane characters inside an edited
line would diverge — a documented, accepted limitation for code edits.

Stdlib only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import pathname2url

# LSP DiagnosticSeverity.Error — the only severity a "worsened set" gate counts.
DIAGNOSTIC_SEVERITY_ERROR = 1

# WorkspaceEdit resource-operation kinds we do NOT apply (create/rename/delete
# file). A rename refactor produces only text edits; a resource op is surfaced
# in notes rather than silently dropped.
_RESOURCE_OP_KINDS = frozenset({'create', 'rename', 'delete'})


def path_to_uri(path: str | Path) -> str:
    """Return the ``file://`` URI for an absolute filesystem path."""
    return 'file://' + pathname2url(str(Path(path).resolve()))


def uri_to_path(uri: str) -> str:
    """Return the filesystem path for a ``file://`` URI (or ``uri`` verbatim)."""
    if not uri.startswith('file:'):
        return uri
    parsed = urlparse(uri)
    return unquote(parsed.path)


def normalize_changes(workspace_edit: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Normalise a ``WorkspaceEdit`` into ``{path: [textEdit, ...]}`` plus notes.

    Handles both the ``documentChanges`` (versioned) and legacy ``changes``
    encodings. Resource operations (create/rename/delete file) are not applied
    here; each is reported as a note so the footprint stays honest rather than
    silently discarding part of the edit.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    notes: list[str] = []

    document_changes = workspace_edit.get('documentChanges')
    if isinstance(document_changes, list):
        for change in document_changes:
            if not isinstance(change, dict):
                continue
            kind = change.get('kind')
            if kind in _RESOURCE_OP_KINDS:
                notes.append(f'unapplied resource operation: {kind}')
                continue
            text_document = change.get('textDocument')
            edits = change.get('edits')
            if isinstance(text_document, dict) and isinstance(edits, list):
                path = uri_to_path(text_document.get('uri', ''))
                result.setdefault(path, []).extend(edits)
        return result, notes

    changes = workspace_edit.get('changes')
    if isinstance(changes, dict):
        for uri, edits in changes.items():
            if isinstance(edits, list):
                result.setdefault(uri_to_path(uri), []).extend(edits)
    return result, notes


def capture_footprint(workspace_edit: dict[str, Any]) -> list[dict[str, Any]]:
    """Capture the edit's file footprint **from the edit itself**.

    Returns one ``{path, edit_count}`` row per touched file, sorted by path.
    This is the recorded footprint-capturing path: the caller records exactly
    these files as the change's footprint, never a set derived from a later diff.
    """
    changes, _notes = normalize_changes(workspace_edit)
    return [{'path': path, 'edit_count': len(edits)} for path, edits in sorted(changes.items())]


def _line_start_offsets(text: str) -> list[int]:
    """Return the absolute character offset at which each line begins."""
    offsets = [0]
    for index, char in enumerate(text):
        if char == '\n':
            offsets.append(index + 1)
    return offsets


def _position_to_offset(line_starts: list[int], text_length: int, line: int, character: int) -> int:
    """Convert an LSP ``{line, character}`` position to an absolute offset."""
    if line < 0:
        return 0
    if line >= len(line_starts):
        return text_length
    return min(line_starts[line] + max(character, 0), text_length)


def apply_text_edits(text: str, edits: list[dict[str, Any]]) -> str:
    """Apply a list of LSP ``TextEdit`` objects to ``text``.

    Edits are applied highest-offset-first so each edit's offsets — computed
    once against the original text — stay valid as later (lower) edits are
    spliced in. LSP guarantees text edits within one document do not overlap.
    """
    line_starts = _line_start_offsets(text)
    text_length = len(text)

    def _start_key(edit: dict[str, Any]) -> tuple[int, int]:
        start = edit['range']['start']
        return (start['line'], start['character'])

    for edit in sorted(edits, key=_start_key, reverse=True):
        edit_range = edit['range']
        start = _position_to_offset(line_starts, text_length, edit_range['start']['line'], edit_range['start']['character'])
        end = _position_to_offset(line_starts, text_length, edit_range['end']['line'], edit_range['end']['character'])
        text = text[:start] + edit.get('newText', '') + text[end:]
    return text


def apply_workspace_edit(workspace_edit: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Apply every text edit in ``workspace_edit`` to disk.

    Returns ``(footprint, originals)`` where ``footprint`` is the captured
    ``{path, edit_count}`` list and ``originals`` maps each touched path to its
    pre-edit content, so :func:`restore_files` can roll the whole change back if
    the post-application diagnostics come back worse.
    """
    changes, _notes = normalize_changes(workspace_edit)
    originals: dict[str, str] = {}
    footprint: list[dict[str, Any]] = []
    for path in sorted(changes):
        file_path = Path(path)
        original = file_path.read_text(encoding='utf-8')
        originals[path] = original
        file_path.write_text(apply_text_edits(original, changes[path]), encoding='utf-8')
        footprint.append({'path': path, 'edit_count': len(changes[path])})
    return footprint, originals


def restore_files(originals: dict[str, str]) -> None:
    """Restore each path to the content captured before the edit was applied."""
    for path, content in originals.items():
        Path(path).write_text(content, encoding='utf-8')


def count_error_diagnostics(diagnostics: list[dict[str, Any]]) -> int:
    """Count diagnostics of severity Error (the only severity the gate counts)."""
    return sum(1 for diag in diagnostics if diag.get('severity') == DIAGNOSTIC_SEVERITY_ERROR)


def edit_verdict(errors_before: int, errors_after: int) -> str:
    """Return ``'failed'`` when the edit worsened the error set, else ``'success'``.

    A worsened diagnostic set fails the step: an edit nobody read is at minimum
    an edit the parser re-checked, and a re-check that finds *new* errors is a
    rejection, not a pass.
    """
    return 'failed' if errors_after > errors_before else 'success'
