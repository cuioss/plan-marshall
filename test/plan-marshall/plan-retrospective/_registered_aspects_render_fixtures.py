# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``registered aspects render`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import re
from pathlib import Path

import retro_sections as _rs

from conftest import MARKETPLACE_ROOT, load_script_module

_cr = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_render_guard_mod')


_cf = load_script_module('plan-marshall', 'plan-retrospective', 'collect-fragments.py', 'cf_render_guard_mod')


_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective'


_SKILL_MD_PATH = _SKILL_DIR / 'SKILL.md'


# A numbered row of the Step-3 aspect-order table. The row's cells name the
# aspect and the Reference document that owns its dispatch; the aspect
# population is derived from these rows rather than hand-listed.
_ASPECT_TABLE_ROW_RE = re.compile(r'^\|\s*\d+\s*\|(?P<cells>.*)\|\s*$', re.MULTILINE)


# A reference/standards document path named in an aspect row's Reference cell.
_ASPECT_DOC_RE = re.compile(r'((?:references|standards)/[a-z0-9-]+\.md)')


# Matches ``--aspect <key>`` where <key> is a concrete hyphenated aspect
# identifier. The leading ``[a-z]`` anchor excludes ``{name}`` / ``{aspect}``
# placeholder templates (they begin with ``{``), so only literal dispatched
# aspect keys are captured.
_ASPECT_DISPATCH_RE = re.compile(r'--aspect\s+([a-z][a-z0-9-]*)')


# The aspect-table header, asserted verbatim before the Key column is read by
# position. Reading a fixed cell index without anchoring the header is how a
# column reorder silently starts scanning the wrong column and the guard keeps
# passing against the wrong data.
_ASPECT_TABLE_HEADER = '| Order | Aspect | Key | Script(s) | Reference |'


# Zero-based index of the Key cell once a table row is split on ``|``.
# ``_ASPECT_TABLE_ROW_RE`` already consumes the leading ``| N |``, so ``cells``
# begins AFTER the Order column; re-wrapping it in ``|`` and splitting yields
# ``['', Aspect, Key, Script(s), Reference, '']``. Verified by running the split
# against the live table, not inferred from the row shape.
_KEY_CELL_INDEX = 2


def _scan_aspect_table_keys(skill_text: str | None = None) -> list[str]:
    """Return the canonical key each Step-3 aspect-table row declares.

    Read by COLUMN POSITION from the numbered rows, not by pattern-matching
    backticked spans: the Script(s) and Reference cells are backticked too, so a
    span-based scan would sweep script names and document paths into the key
    population and the correspondence assertion would be checking the wrong set.

    ``skill_text`` defaults to the live ``SKILL.md``. It is a parameter so the
    bite test can run this exact parser over a DELIBERATELY corrupted table —
    without it a "the guard bites" test can only do set arithmetic on a literal,
    which exercises neither the parse nor the correspondence check.
    """
    if skill_text is None:
        skill_text = _SKILL_MD_PATH.read_text(encoding='utf-8')
    assert _ASPECT_TABLE_HEADER in skill_text, (
        f'The Step-3 aspect table no longer carries the expected header '
        f'{_ASPECT_TABLE_HEADER!r} — the Key column is read by position, so a '
        f'reordered or renamed column must fail here rather than silently '
        f'scanning a different cell'
    )
    keys: list[str] = []
    for row in _ASPECT_TABLE_ROW_RE.finditer(skill_text):
        cells = ('|' + row.group('cells') + '|').split('|')
        if len(cells) <= _KEY_CELL_INDEX:
            continue
        keys.append(cells[_KEY_CELL_INDEX].strip().strip('`').strip())
    return keys


def _spec_fragment_keys() -> set[str]:
    """Return the set of every ``fragment_key`` declared in ``SECTION_SPEC``."""
    return {fragment_key for _heading, fragment_key, _trigger in _rs.SECTION_SPEC}


def _build_doc_with_aspect(aspect_key: str) -> str:
    """Build a retrospective document from a synthetic single-aspect bundle.

    The bundle carries only ``_meta`` and the one ``aspect_key``, so the section
    (when it appears) can only have come from either a ``SECTION_SPEC`` row or the
    generic fallback in ``build_document()``.
    """
    fragments = {
        '_meta': {'mode': 'live'},
        aspect_key: {'status': 'success', 'summary': f'synthetic body for {aspect_key}'},
    }
    content, _written, _omitted, _dropped = _cr.build_document('p', 'live', Path('/tmp/plan'), None, fragments)
    return content


def _aspect_reference_docs() -> list[Path]:
    """Return the reference/standards docs the Step-3 aspect-order table names.

    The population is derived from the table itself — every numbered row's
    Reference cell — so an aspect added to the roster brings its owning document
    into the scan automatically.

    A row naming a document that does not exist on disk FAILS LOUDLY rather than
    being skipped. Silently dropping it would shrink the scanned population, so
    every aspect registered inside that document would vanish from the
    enumeration and the completeness sweep downstream would pass vacuously — a
    renamed or mistyped Reference cell would read as "no aspects to check"
    instead of as the roster drift it is.
    """
    skill_text = _SKILL_MD_PATH.read_text(encoding='utf-8')
    docs: list[Path] = []
    missing: list[str] = []
    for row in _ASPECT_TABLE_ROW_RE.finditer(skill_text):
        for rel in _ASPECT_DOC_RE.findall(row.group('cells')):
            path = _SKILL_DIR / rel
            if not path.is_file():
                if rel not in missing:
                    missing.append(rel)
                continue
            if path not in docs:
                docs.append(path)

    assert not missing, (
        f'Step-3 aspect-order table names Reference document(s) that do not exist on '
        f'disk: {sorted(missing)} — a missing reference silently shrinks the scanned '
        f'population and makes the completeness sweep vacuous, so the roster must be '
        f'corrected (or the document restored) rather than the row ignored'
    )
    return docs


def _scan_dispatched_aspects() -> set[str]:
    """Enumerate the literal aspect keys the plan-retrospective workflow dispatches.

    Source-independent of ``SECTION_SPEC``: the population is derived from the
    Step-3 aspect-order table in ``SKILL.md`` — every numbered row contributes
    the Reference document it names — and every literal
    ``add --aspect <key>`` command is then extracted from ``SKILL.md`` PLUS each
    of those documents. Placeholder templates (``{name}`` / ``{aspect}``) are
    excluded by the regex anchor.

    Scanning the referenced documents (not just ``SKILL.md``) is what makes this
    a producer enumeration rather than a file-scoped sample: an aspect whose
    registration command lives in its own reference doc — ``SKILL.md`` dispatches
    only a pre-pass and delegates fragment synthesis and registration — is a
    normal shape, not an exception. ``chat-history-analysis``,
    ``direct-gh-glab-usage``, and ``execution-context-dispatch-audit`` are all
    that shape, and all three are now enumerated here.
    """
    texts = [_SKILL_MD_PATH.read_text(encoding='utf-8')]
    texts.extend(path.read_text(encoding='utf-8') for path in _aspect_reference_docs())
    keys: set[str] = set()
    for text in texts:
        keys.update(_ASPECT_DISPATCH_RE.findall(text))
    return keys


_CHAT_HISTORY_KEY = 'chat-history-analysis'


_CHAT_HISTORY_HEADING = 'Chat History Analysis'


_TIER2_WARNING = 'transcript unavailable — chat-history analysis skipped'
