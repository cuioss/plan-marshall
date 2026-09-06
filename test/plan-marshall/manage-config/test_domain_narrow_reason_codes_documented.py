#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The documented ``domain-narrow`` reason-code set equals the declared one.

The set is mirrored as prose in more than one document against a single declaring
source, ``_cmd_domain_narrow.py``. Every mirror asserts CLOSURE — "the complete set
the verb can return", "the reason codes are ..." — and closure language raises the
bar on the enumeration beneath it: a stale copy stops being merely incomplete and
becomes actively misleading, because a reader obeying the project's quote-it-verbatim
rule is led to a wrong value and writes a plausible-but-wrong code that downstream
analysis consumes as well-formed.

Re-synchronising the copies by hand does not survive the next edit. This module is the
thing that KEEPS them synchronised: it derives the declared set from the script and
asserts each mirror enumerates exactly that set, so drift fails a build instead of
shipping. The enumerations are deliberately NOT deleted in favour of a bare
cross-reference — a reader at the call site needs them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

_SCRIPT = 'plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py'

#: The mirror that renders the set as a table, keyed by its header row.
_TABLE_DOC = 'plan-marshall/skills/manage-config/SKILL.md'
_TABLE_HEADER = '| `error` | Raised when |'

#: The mirrors that render the set as a single closure sentence.
_SENTENCE_DOCS = (
    'plan-marshall/skills/phase-3-outline/SKILL.md',
    'plan-marshall/skills/phase-3-outline/workflow/light-lane.md',
)

#: Every document that mirrors the whole set. ``manage-config/standards/skill-domains.md``
#: and ``manage-config/standards/api-reference.md`` are deliberately absent: the first
#: delegates the error set to ``SKILL.md`` by cross-reference and the second names two
#: codes as conditions without claiming to enumerate the set, so neither is a mirror.
#: test_no_unguarded_mirror_exists is what keeps this tuple honest.
_MIRROR_DOCS = (_TABLE_DOC, *_SENTENCE_DOCS)

#: A document naming at least this many declared codes is enumerating the set rather
#: than mentioning a condition or two in passing, so it needs to be under guard.
_MIRROR_THRESHOLD = 4

#: One code that must appear in every extraction. A regex that silently stops matching
#: yields an empty set, and an empty-set-equals-empty-set assertion passes while
#: covering nothing — this anchor is what makes that failure visible.
_ANCHOR_CODE = 'task_leg_unreadable'

_ERROR_LITERAL_RE = re.compile(r"'error':\s*'([a-z_]+)'")
_SENTENCE_RE = re.compile(r'The reason codes are (.+?);', re.DOTALL)
_BACKTICKED_TOKEN_RE = re.compile(r'`([a-z_]+)`')


def _read(relative_path: str) -> str:
    """Return the text of a marketplace file addressed relative to the bundles root."""
    path: Path = MARKETPLACE_ROOT / relative_path
    return path.read_text(encoding='utf-8')


def _declared_codes() -> list[str]:
    """Return every reason code ``cmd_domain_narrow`` can return, from the script itself."""
    return _ERROR_LITERAL_RE.findall(_read(_SCRIPT))


def _codes_from_table(text: str) -> list[str]:
    """Return the first-column codes of the reason-code table, in document order."""
    lines = text.splitlines()
    start = lines.index(_TABLE_HEADER)
    codes: list[str] = []
    for line in lines[start + 2 :]:  # +2 skips the markdown separator row
        if not line.startswith('| `'):
            break
        codes.append(line.split('`')[1])
    return codes


def _codes_from_sentence(text: str) -> list[str]:
    """Return the backticked codes of the closure sentence that introduces the set."""
    match = _SENTENCE_RE.search(text)
    if match is None:
        raise AssertionError('no "The reason codes are ..." sentence found; anchor moved')
    return _BACKTICKED_TOKEN_RE.findall(match.group(1))


_EXTRACTORS = {
    _TABLE_DOC: _codes_from_table,
    **dict.fromkeys(_SENTENCE_DOCS, _codes_from_sentence),
}


def test_the_declared_set_is_extracted_and_not_silently_empty():
    """The script-side extraction finds a real set, so the equality below is not vacuous."""
    declared = _declared_codes()

    assert _ANCHOR_CODE in declared
    assert len(declared) == len(set(declared))


@pytest.mark.parametrize('document', _MIRROR_DOCS)
def test_documented_reason_codes_equal_the_declared_set(document):
    """Each mirror enumerates exactly the codes the script can return — no more, no fewer."""
    documented = _EXTRACTORS[document](_read(document))

    assert _ANCHOR_CODE in documented
    assert len(documented) == len(set(documented))
    assert set(documented) == set(_declared_codes())


def test_no_unguarded_mirror_exists():
    """Every document that enumerates the set is under guard, so the list above cannot rot.

    Without this the guarded tuple is itself a hand-maintained mirror with exactly the
    drift problem the module exists to remove: a new document could start restating the
    set and no assertion would ever look at it.
    """
    declared = set(_declared_codes())

    enumerating = {
        str(path.relative_to(MARKETPLACE_ROOT))
        for path in MARKETPLACE_ROOT.rglob('*.md')
        if len(declared & set(_BACKTICKED_TOKEN_RE.findall(path.read_text(encoding='utf-8'))))
        >= _MIRROR_THRESHOLD
    }

    assert enumerating == set(_MIRROR_DOCS)
