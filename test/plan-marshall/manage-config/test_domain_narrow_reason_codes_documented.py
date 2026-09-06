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

#: The mirror population is DISCOVERED, never restated. A hand-written tuple here would
#: itself be a mirror of the set this module exists to keep from drifting: a document that
#: started enumerating the codes would be found by the scan but never parametrized, so its
#: contents would go unchecked until someone remembered to add it. Deriving the population
#: from the same scan that polices it removes the second registry entirely.
#:
#: ``manage-config/standards/skill-domains.md`` and ``manage-config/standards/api-reference.md``
#: fall below the threshold by construction: the first delegates the error set to ``SKILL.md``
#: by cross-reference, the second names two codes as conditions without enumerating the set.

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


def _discover_mirror_docs() -> list[str]:
    """Return every markdown file that ENUMERATES the declared set, by scanning for it.

    This is the single population: the parametrized equality test and the no-unguarded-mirror
    test both consume it, so a newly-added mirror is checked the moment it appears rather
    than when someone remembers to register it.
    """
    declared = set(_declared_codes())
    return sorted(
        str(path.relative_to(MARKETPLACE_ROOT))
        for path in MARKETPLACE_ROOT.rglob('*.md')
        if len(declared & set(_BACKTICKED_TOKEN_RE.findall(path.read_text(encoding='utf-8'))))
        >= _MIRROR_THRESHOLD
    )


def _extractor_for(document: str, text: str):
    """Select the extractor from the document's own FORMAT, not from a path registry.

    A path-keyed map is the same second registry the discovered population removes: a new
    mirror would have no entry and raise KeyError, which reads as a test-harness fault
    rather than as the unguarded mirror it is. Dispatching on the shape actually present
    means a recognised format is parsed and an unrecognised one fails saying so.
    """
    if _TABLE_HEADER in text:
        return _codes_from_table
    if _SENTENCE_RE.search(text) is not None:
        return _codes_from_sentence
    raise AssertionError(
        f'{document} enumerates the reason codes in a format this module cannot parse; '
        'add an extractor for it rather than dropping it from the guarded population'
    )


def test_the_declared_set_is_extracted_and_not_silently_empty():
    """The script-side extraction finds a real set, so the equality below is not vacuous."""
    declared = _declared_codes()

    assert _ANCHOR_CODE in declared
    assert len(declared) == len(set(declared))


@pytest.mark.parametrize('document', _discover_mirror_docs())
def test_documented_reason_codes_equal_the_declared_set(document):
    """Each mirror enumerates exactly the codes the script can return — no more, no fewer."""
    text = _read(document)
    documented = _extractor_for(document, text)(text)

    assert _ANCHOR_CODE in documented
    assert len(documented) == len(set(documented))
    assert set(documented) == set(_declared_codes())


def test_every_discovered_mirror_is_parseable_and_the_population_is_not_empty():
    """The discovered population is non-empty and every member has a usable extractor.

    Two failures this catches that the equality test above cannot. An EMPTY population
    parametrizes zero cases, so the suite would report all-green while checking no mirror
    at all — the vacuous pass this module's anchor assertion exists to prevent, one level
    up. And a mirror written in an unrecognised format would raise inside the extractor
    selector; asserting it here names it as an unguarded mirror rather than surfacing it
    as a parametrization error.
    """
    discovered = _discover_mirror_docs()

    assert discovered, 'no document enumerates the reason codes; the scan or threshold is wrong'
    for document in discovered:
        assert _extractor_for(document, _read(document)) is not None
