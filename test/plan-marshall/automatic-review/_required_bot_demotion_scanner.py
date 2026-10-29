#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract scanner — no shipped document offers demoting a REQUIRED reviewer.

The operator's standing policy for a required reviewer is that it is mandatory and is
never demoted to ``optional_bots``; the only ruling that covers its silence is a
recorded, HEAD-bound merge authorization
(``automatic-review/standards/coderabbit.md`` § "Operator review policy"). That policy is
worth exactly as much as the corpus is consistent with it: a single stray sentence
telling a run to "move the bot to `optional_bots`" re-introduces, as a documented
remedy, the one move the policy forbids outright — and it does so for the bot whose
silence the quorum exists to catch.

This module is the DETERMINISTIC half of that contract. It scans every shipped
document under ``marketplace/bundles/`` for a sentence that OFFERS a demotion, and
reports each one. It is a test-side scanner (it ships nothing into the product), so the
product corpus stays free of a check nobody runs.

What counts as an offer, stated exactly:

* a DEMOTION VERB (``move``/``demote``/``reclassify``/``drop`` and inflections) whose
  destination is ``optional`` or ``optional_bots``; and
* the sentence is about a REQUIRED bot — it names ``required`` / ``required_bots``; and
* the sentence does not NEGATE the offer (``never``, ``not``, ``no``, ``withdrawn``,
  ``forbidden``, …).

The negation arm is load-bearing in both directions. Every policy statement in this
corpus is written as a prohibition ("a required bot is **never** demoted to
`optional_bots`"), so a scanner that flagged the phrase itself would flag the rule
alongside its violation. And a sentence about an ALREADY-OPTIONAL bot is not a
demotion at all: reclassifying an optional bot as optional changes nothing, so it
carries no ``required`` qualifier and is not reported.
"""

from __future__ import annotations

import re
from pathlib import Path

#: The shipped-document root the contract covers.
BUNDLES_ROOT = Path(__file__).resolve().parents[3] / 'marketplace' / 'bundles'

#: Inflections of the reclassification verb. Includes the bare ``drop`` so "drop the
#: bot to `optional_bots`" is caught; the registry keeps a required bot's comments
#: ingested even when unclassified, so a "drop" is still a demotion offer.
_DEMOTION_VERB = (
    r'(?:mov(?:e|es|ed|ing)|demot(?:e|es|ed|ing)|reclassif(?:y|ies|ied|ying)|drop(?:s|ped|ping)?|'
    r'downgrad(?:e|es|ed|ing))'
)
#: Where a demotion lands. ``optional`` alone is the short form shipped docs used.
_DESTINATION = r'`?optional(?:_bots)?`?'
#: Verb … within at most a few words … destination, or destination … verb.
_DEMOTION_OFFER = re.compile(
    rf'{_DEMOTION_VERB}\b[^.;\n]{{0,80}}?\b(?:to|into)\s+{_DESTINATION}'
    rf'|{_DESTINATION}\s*(?:,|—|-)?\s*(?:as|instead|rather)[^.;\n]{{0,40}}?{_DEMOTION_VERB}\b',
    re.IGNORECASE,
)
#: The sentence must be about a REQUIRED bot. ``required_bots`` counts: it is the
#: roster the demotion would move the bot out of.
_REQUIRED_SIGNAL = re.compile(r'\brequired\b', re.IGNORECASE)
#: A prohibition. Only NEGATION LOCAL TO THE OFFER counts: a sentence can state an
#: offer and a separate prohibition at once ("move it to `optional`, never another
#: trigger"), and letting any ``never`` anywhere in the sentence launder the offer is
#: exactly how the shipped defect survives a scanner. The clause window around a match
#: is what makes the negation the offer's rather than a neighbour's.
_NEGATION = re.compile(
    r'\b(?:never|not|no|none|nor|neither|withdrawn|forbidden|prohibited|cannot|'
    r"can't|doesn't|don't|isn't|aren't|won't|mustn't)\b",
    re.IGNORECASE,
)
#: How far around an offer match its own clause reaches. Asymmetric on purpose: a
#: prohibition is stated BEFORE or immediately AFTER the demotion ("is never offered
#: here", "— is withdrawn"), never a clause later, which is where a separate remedy
#: begins.
_NEGATION_BEFORE_CHARS = 40
_NEGATION_AFTER_CHARS = 25
#: Sentence boundaries that matter for reading one claim at a time. A markdown table
#: row or a bullet is its own claim, so the newline is a boundary too.
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+|\s+[|]\s+')
#: A newline that WRAPS a prose line rather than starting a new markdown block. It is
#: joined into a space before the sentence split, because a negation the author wrapped
#: onto the next line ("... is\nnot offered") is still part of the same claim — and
#: splitting there is how a laundered offer hides from the clause window.
_WRAP_JOIN = re.compile(r'\n(?!\s*(?:[-*+]\s|\d+\.\s|#{1,6}\s|\|))')

DEMOTION_KEYWORD = 'optional_bots'


def sentences(text: str) -> list[str]:
    """Split shipped text into claim-sized sentences.

    Newlines are boundaries as well as sentence punctuation when they START a new block
    (a bullet, a numbered item, a heading, a table row): a bullet or table row is one
    claim, and joining it to its neighbour is what lets a prohibition beside an offer
    launder the offer. A newline that merely WRAPS a prose line is joined into a space
    first, so a negation the author wrapped onto the next line stays in its clause.
    """
    joined = _WRAP_JOIN.sub(' ', text)
    return [part.strip() for part in _SENTENCE_SPLIT.split(joined) if part.strip()]


def offered_demotions(text: str) -> list[str]:
    """Every sentence in ``text`` that OFFERS demoting a required bot."""
    offenders: list[str] = []
    for sentence in sentences(text):
        if not _REQUIRED_SIGNAL.search(sentence):
            # An already-optional bot being called optional is not a demotion.
            continue
        for match in _DEMOTION_OFFER.finditer(sentence):
            window = sentence[max(0, match.start() - _NEGATION_BEFORE_CHARS) : match.end() + _NEGATION_AFTER_CHARS]
            if _NEGATION.search(window):
                continue
            offenders.append(sentence)
            break
    return offenders


def shipped_documents(root: Path = BUNDLES_ROOT) -> list[Path]:
    """Every shipped document under ``root`` — the scanner's population."""
    return sorted(path for path in root.rglob('*.md') if path.is_file())


def scan(root: Path = BUNDLES_ROOT) -> list[tuple[Path, str]]:
    """Every (document, offending sentence) pair under ``root``."""
    findings: list[tuple[Path, str]] = []
    for document in shipped_documents(root):
        text = document.read_text(encoding='utf-8')
        for sentence in offered_demotions(text):
            findings.append((document, sentence))
    return findings
