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
  post-application diagnostic set can be **rolled back** (``restore_files``).
  The apply loop is all-or-nothing: a failure part-way through restores every
  file already written and raises :class:`WorkspaceApplyError` naming the file
  that failed. A caller observes a half-applied edit in exactly one case — the
  restore itself failed — and the exception says so in ``restore_error`` rather
  than presenting the tree as clean;
* the pre/post error **sets** — per file, keyed by
  ``(severity, code, message, line, character)`` — drive an explicit
  ``edit_verdict``: a file that *gained* an error diagnostic fails the step.
  A set rather than a count, because summed counts net to zero when an error is
  swapped for a different one in the same file, or moves between two files in
  the same footprint.

LSP positions are 0-based ``{line, character}`` where ``character`` is a UTF-16
code-unit offset. For the BMP (all identifiers and virtually all source text)
that equals a Python ``str`` index; astral-plane characters inside an edited
line would diverge — a documented, accepted limitation for code edits.

Stdlib only.
"""

from __future__ import annotations

from collections import Counter
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


class WorkspaceApplyError(Exception):
    """A workspace edit failed part-way through; the caller must not see a partial write.

    Raised by :func:`apply_workspace_edit` **after** it has attempted to restore
    every file it wrote — including the one the failing write itself damaged.
    Whether the TREE is back as it was is exactly what ``restore_error`` reports:
    it is ``None`` when every captured path holds its captured content, and
    non-``None`` only when some file really is left modified, which the caller
    must surface rather than swallow. ⛔ It is derived from re-reading the
    footprint, **not** from whether the restore call raised — a write refused
    before it touched anything (EACCES, EPERM, an immutable file) makes that
    path's restore fail for the same reason, over a file nothing modified, and
    reporting it would raise an alarm about a clean tree. Read the attribute,
    not this sentence: "has been restored" is the intent, and only
    ``restore_error is None`` is the fact.
    """

    def __init__(self, path: str, cause: BaseException, restore_error: BaseException | None = None) -> None:
        super().__init__(f'failed to apply edits to {path}: {cause}')
        self.path = path
        self.cause = cause
        self.restore_error = restore_error


def path_to_uri(path: str | Path) -> str:
    """Return the ``file://`` URI for an absolute filesystem path."""
    return 'file://' + pathname2url(str(Path(path).resolve()))


def uri_to_path(uri: str) -> str:
    """Return the filesystem path for a ``file://`` URI (or ``uri`` verbatim).

    ⛔ The result is **resolved**, matching :func:`path_to_uri`, so that two
    spellings of one document — ``/t/a.py`` and ``/t/./a.py``, or a symlink and
    its target — normalise to the same key. They used not to, and the cost was a
    false clean: ``normalize_changes`` produced two entries for one file, the
    second entry's captured "original" was the first entry's *output*, and
    rolling back therefore restored the file to a state it had never been in
    while the payload reported ``rolled_back: true``. Aliasing is a server
    defect, but a false clean is the one outcome this write path may never
    produce, whatever the server does.

    A path that cannot be resolved (it does not exist, or the filesystem refuses
    the walk) falls back to the unresolved form: the apply loop then fails on it
    and reports which path, which is a legible failure rather than a swallowed
    one.
    """
    if not uri.startswith('file:'):
        return uri
    parsed = urlparse(uri)
    raw = unquote(parsed.path)
    try:
        return str(Path(raw).resolve())
    except OSError:
        return raw


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
    """Convert an LSP ``{line, character}`` position to an absolute offset.

    ⛔ An over-long ``character`` clamps to the END OF ITS OWN LINE, which is
    what LSP 3.17 requires of ``Position.character``: *"If the character value
    is greater than the line length it defaults back to the line length."*
    Clamping to the length of the whole FILE instead — which this did — turns
    the standard end-of-line idiom ``[line, 0]-[line, 2147483647]`` into a range
    covering everything from that line to EOF, so replacing one line silently
    replaced the rest of the file. The write path's diagnostics gate catches
    most such truncations because the wreckage gains errors, but a tail of
    comments or data adds no NEW error diagnostic and the edit is accepted.
    """
    if line < 0:
        return 0
    if line >= len(line_starts):
        return text_length
    # The LINE LENGTH excludes the terminator: the next line starts one past the
    # '\n', so the content ends one before it. The last line has no terminator
    # and ends at EOF. Clamping to the terminator instead would let the
    # end-of-line idiom swallow the newline and join two lines.
    line_end = line_starts[line + 1] - 1 if line + 1 < len(line_starts) else text_length
    return min(line_starts[line] + max(character, 0), line_end)


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

    **All-or-nothing.** If any file fails to read, transform or write — a
    malformed ``TextEdit`` with no ``range``, an unwritable path, an I/O error —
    every file already rewritten is restored and
    :class:`WorkspaceApplyError` is raised naming the offending path. Without
    that boundary an exception on the second of three files escapes with file
    one rewritten and ``originals`` discarded, leaving a partial edit on disk
    and no footprint in the output.

    Raises:
        WorkspaceApplyError: the edit failed part-way; see ``restore_error`` on
            the exception for whether the rollback itself also failed.
    """
    changes, _notes = normalize_changes(workspace_edit)
    originals: dict[str, str] = {}
    footprint: list[dict[str, Any]] = []
    for path in sorted(changes):
        file_path = Path(path)
        try:
            original = file_path.read_text(encoding='utf-8')
            new_text = apply_text_edits(original, changes[path])
            originals[path] = original
            file_path.write_text(new_text, encoding='utf-8')
        except Exception as exc:  # noqa: BLE001 — re-raised as WorkspaceApplyError below
            # ⛔ The failing path stays IN ``originals``. It is recorded before
            # the write, so a write that failed part-way — ENOSPC, EIO — has
            # already truncated or partly rewritten it, and it is the one file
            # that most needs restoring. Discarding it here left exactly that
            # file modified while ``restore_error`` stayed ``None``, i.e. the
            # payload reported a clean rollback over a damaged tree. When the
            # read or the transform failed instead, nothing was written and the
            # entry is simply absent, so there is nothing to discard either.
            restore_error: BaseException | None = None
            try:
                restore_files(originals)
            except OSError as restore_exc:
                # ⛔ A failed restore is not the same as an unrestored tree, and
                # only the second one may set ``restore_error``. A write that
                # fails at ``open()`` — EACCES, EPERM, EROFS, an immutable file —
                # never truncates anything, so the "restore" of that path is a
                # rewrite of content already on disk: it fails for the same
                # reason the write did, over a file that was never modified.
                # Reporting that as ``restore_error`` raises a false alarm about
                # a clean tree, which is the mirror of the false clean this
                # boundary exists to prevent and just as misleading. So the
                # claim is CHECKED rather than inferred from the exception.
                restore_error = restore_exc if _still_modified(originals) else None
            raise WorkspaceApplyError(path, exc, restore_error) from exc
        footprint.append({'path': path, 'edit_count': len(changes[path])})
    return footprint, originals


def restore_files(originals: dict[str, str]) -> None:
    """Restore each path to the content captured before the edit was applied."""
    for path, content in originals.items():
        Path(path).write_text(content, encoding='utf-8')


def _still_modified(originals: dict[str, str]) -> bool:
    """Report whether any path's content on disk differs from what was captured.

    The question ``restore_error`` is supposed to answer, asked of the disk
    instead of inferred from an exception. A path that cannot be read back is
    counted as modified: the honest answer under an unreadable file is "I cannot
    show you this tree is clean", and the fail-closed direction here is to warn.
    """
    for path, content in originals.items():
        try:
            if Path(path).read_text(encoding='utf-8') != content:
                return True
        except OSError:
            return True
    return False


def count_error_diagnostics(diagnostics: list[dict[str, Any]]) -> int:
    """Count diagnostics of severity Error (the only severity the gate counts)."""
    return sum(1 for diag in diagnostics if diag.get('severity') == DIAGNOSTIC_SEVERITY_ERROR)


def diagnostic_key(diagnostic: dict[str, Any]) -> tuple[Any, ...]:
    """Return the identity of one diagnostic within a file.

    Two diagnostics are the same diagnostic when they agree on severity, code,
    message and start position. The file is *not* part of the key: keys are only
    ever compared within one file's before/after pair, and folding the path in
    would make an error that moved between files look like two unrelated ones.
    """
    start = (diagnostic.get('range') or {}).get('start') or {}
    return (
        diagnostic.get('severity'),
        str(diagnostic.get('code', '')),
        diagnostic.get('message', ''),
        start.get('line', 0),
        start.get('character', 0),
    )


def error_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the Error-severity diagnostics — the gate's severity scope."""
    return [diag for diag in diagnostics if diag.get('severity') == DIAGNOSTIC_SEVERITY_ERROR]


def diagnostic_delta(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(added, removed)`` Error diagnostics between two reads of one file.

    Compared as multisets of :func:`diagnostic_key`, so three identical errors
    becoming four yields one ``added`` row rather than none. ``added`` is what
    the verdict gates on and what the failure payload reports as new — built by
    diffing, never by re-listing the whole post-edit set, which would present
    every pre-existing error as newly introduced.
    """
    before_keys = Counter(diagnostic_key(diag) for diag in error_diagnostics(before))
    after_keys = Counter(diagnostic_key(diag) for diag in error_diagnostics(after))
    added = _select_by_key(error_diagnostics(after), after_keys - before_keys)
    removed = _select_by_key(error_diagnostics(before), before_keys - after_keys)
    return added, removed


def _select_by_key(diagnostics: list[dict[str, Any]], wanted: Counter[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Pick ``wanted[key]`` diagnostics per key out of ``diagnostics``, in order."""
    remaining = Counter(wanted)
    selected: list[dict[str, Any]] = []
    for diag in diagnostics:
        key = diagnostic_key(diag)
        if remaining[key] > 0:
            remaining[key] -= 1
            selected.append(diag)
    return selected


def edit_verdict(added_by_path: dict[str, list[dict[str, Any]]]) -> str:
    """Return ``'failed'`` when any file gained an error diagnostic, else ``'success'``.

    A worsened diagnostic **set** fails the step: an edit nobody read is at
    minimum an edit the parser re-checked, and a re-check that finds *new* errors
    is a rejection, not a pass.

    The gate is per file and set-based, not a footprint-wide count, because a
    count cannot see the two cases that matter: one error swapped for a
    different one in the same file, and an error moving from one file in the
    footprint to another. Both net to zero and both used to pass.

    Args:
        added_by_path: per touched file, the Error diagnostics present after the
            edit that were not present before it (see :func:`diagnostic_delta`).
    """
    return 'failed' if any(added_by_path.values()) else 'success'
