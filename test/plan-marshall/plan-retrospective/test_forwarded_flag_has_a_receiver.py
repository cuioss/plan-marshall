# SPDX-License-Identifier: FSL-1.1-ALv2
"""A ``forwarded_to_*`` flag must have a producer that actually reads it.

``check-artifact-consistency`` downgrades a ``status: warn`` to ``severity: info``
whenever it sets ``forwarded_to_manifest``, on the premise that a sibling producer
picks the finding up. For as long as no sibling read the flag, that premise made
the downgrade a DROP: the finding was softened on the strength of a handoff that
never happened, and nothing anywhere failed. The forward is a claim about another
producer's behaviour, and a claim about behaviour nobody implements is exactly the
shape this plan exists to remove.

This is the structural guard for the whole class rather than for that one flag. A
flag mentioned by exactly one producer script is a flag with no receiver: whatever
sets it is also the only thing that knows it exists. A flag mentioned by two or
more has a sibling on the other end of the handoff.

⛔ The population is DERIVED by scanning the producer scripts, never pinned as a
list here. A pinned list turns this guard into a test of its own literal: a new
``forwarded_to_*`` flag added tomorrow would be absent from the list and therefore
absent from the check, which is the failure mode the guard is for. Both the number
of scripts scanned and the number of flags found are published and asserted
non-zero, so "scanned the producers and every flag has a receiver" stays
distinguishable from "scanned nothing" and from "found no flag to check".
"""

from __future__ import annotations

import re

from conftest import MARKETPLACE_ROOT

_SCRIPTS_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts'

#: The flag shape. Matched as a whole identifier so ``forwarded_to_manifest`` and
#: a future ``forwarded_to_routing`` are both picked up without either being named.
_FORWARDED_FLAG_RE = re.compile(r'\bforwarded_to_[a-z0-9_]+\b')


def _scan_producers() -> tuple[list[str], dict[str, set[str]]]:
    """Return ``(scripts_scanned, {flag: {script names mentioning it}})``.

    Every ``.py`` under the aspect's ``scripts/`` directory is a producer or a
    helper a producer imports, and either is a legitimate place for the receiving
    rule to live — so the scan is over all of them rather than over a curated
    subset that would have to be maintained beside the tree.
    """
    scripts: list[str] = []
    mentions: dict[str, set[str]] = {}
    for path in sorted(_SCRIPTS_DIR.glob('*.py')):
        scripts.append(path.name)
        for flag in _FORWARDED_FLAG_RE.findall(path.read_text(encoding='utf-8')):
            mentions.setdefault(flag, set()).add(path.name)
    return scripts, mentions


def test_the_scan_has_a_population_to_check():
    """⛔ Vacuity guard — both halves of the population, published.

    A guard that scanned no file, and a guard that scanned every file and found
    no flag, both leave the assertion below iterating an empty mapping and
    passing. They are different facts and neither is the clean result this
    module reports, so each is refused explicitly rather than allowed to look
    like one.
    """
    scripts, mentions = _scan_producers()

    assert scripts, f'no producer scripts found under {_SCRIPTS_DIR} — the scan itself is what broke'
    assert mentions, (
        f'scanned {len(scripts)} producer script(s) and found no forwarded_to_* flag at all. '
        'If the forward mechanism was genuinely retired, retire this guard with it; '
        'until then an empty population means the check below asserts nothing.'
    )


def test_every_forwarded_flag_is_read_by_a_sibling_producer():
    """A flag only one script mentions has nobody on the receiving end.

    The failure message names the orphan flag and the single script that knows
    about it, because those two facts are the whole remedy: either the receiving
    rule is written, or the downgrade that leans on the forward is removed.
    """
    scripts, mentions = _scan_producers()

    orphans = {flag: sorted(where) for flag, where in mentions.items() if len(where) < 2}

    assert not orphans, (
        f'forwarded_to_* flag(s) mentioned by a single producer and read by no sibling: {orphans}. '
        f'A forward flag is a claim that another producer receives the finding; with no reader, '
        f'setting it downgrades the finding into silence. '
        f'(population: {len(mentions)} flag(s) over {len(scripts)} script(s))'
    )
