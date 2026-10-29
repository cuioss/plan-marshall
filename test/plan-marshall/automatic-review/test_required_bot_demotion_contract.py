#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""No shipped document offers demoting a required reviewer (D3).

The operator's policy is that a REQUIRED reviewer is mandatory and is never moved to
``optional_bots``; the only ruling that covers its silence is a recorded, HEAD-bound
merge authorization (``automatic-review/standards/coderabbit.md`` § "Operator review
policy"). The corpus used to contradict that in four places — the barrier and the
``automatic-review`` step each told a run to "move it to `optional`" for a ``declined``
or ``refused_hard`` required bot — and prose is exactly the surface a later edit
re-introduces it on.

The scanner (``_required_bot_demotion_scanner``) is pinned in both directions:

* the REAL tree must report nothing, and
* a planted document that offers the demotion must be reported, so the green above is
  a fact about the corpus rather than about a scanner that never fires;
* and it must tell a required bot apart from one that is ALREADY optional — reclassifying
  an optional bot as optional is not a demotion, and flagging it would make the scanner
  unusable.
"""

from __future__ import annotations

from pathlib import Path

import _required_bot_demotion_scanner as scanner
import pytest


class TestTheShippedCorpusOffersNoDemotion:
    def test_the_population_is_non_empty_and_reaches_every_deliverable_site(self):
        """⛔ Vacuity guard, asserted FIRST — an empty population makes every sweep pass."""
        documents = scanner.shipped_documents()

        assert documents, f'no shipped documents found under {scanner.BUNDLES_ROOT}'
        relative = {str(path.relative_to(scanner.BUNDLES_ROOT)) for path in documents}
        # The four sites the deliverable names, pinned as POPULATION members rather
        # than as literals the scanner would have to know about: if the scan stops
        # covering one of them, that has to fail here instead of passing silently.
        for site in (
            Path('plan-marshall/skills/automatic-review/SKILL.md'),
            Path('plan-marshall/skills/automatic-review/standards/coderabbit.md'),
            Path('plan-marshall/skills/automatic-review/standards/bot-participation-contract.md'),
            Path('plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md'),
        ):
            assert str(site) in relative, f'{site} is not in the scanned population'

    def test_no_shipped_document_offers_demoting_a_required_bot(self):
        findings = scanner.scan()

        assert not findings, '\n'.join(
            f'{document.relative_to(scanner.BUNDLES_ROOT)}: {sentence}' for document, sentence in findings
        )

    def test_the_declined_remedy_is_a_recorded_authorization(self):
        """The demotion that shipped was the ``declined`` remedy; its replacement is pinned.

        A tree that merely DELETED the sentence would pass the scan above while leaving
        the ``declined`` member's remedy unnamed, which is the state the policy exists
        to prevent. Both consumer docs must name the recorded merge authorization.
        """
        for relative in (
            Path('plan-marshall/skills/automatic-review/SKILL.md'),
            Path('plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md'),
        ):
            text = (scanner.BUNDLES_ROOT / relative).read_text(encoding='utf-8')
            declined = [paragraph for paragraph in text.split('\n') if 'a required bot on `declined`' in paragraph]
            assert declined, f'{relative} no longer names the declined member'
            assert any('merge authorization' in paragraph for paragraph in declined), (
                f'{relative}: the declined member names no recorded merge authorization'
            )


class TestTheScannerCanFail:
    def test_a_planted_offer_is_reported(self):
        """⛔ Negative control: the green above must be able to turn red."""
        text = 'When a required bot keeps refusing, move it to `optional_bots` and continue with the merge.\n'

        assert scanner.offered_demotions(text)

    def test_the_real_corpus_offers_none(self):
        """Matched positive control: the same rule ACCEPTS the corpus."""
        for document in scanner.shipped_documents():
            assert not scanner.offered_demotions(document.read_text(encoding='utf-8')), document

    def test_a_prohibition_is_not_an_offer(self):
        text = 'A required bot is never demoted to `optional_bots`; record a merge authorization instead.\n'

        assert scanner.offered_demotions(text) == []

    def test_a_prohibition_later_in_the_same_sentence_does_not_launder_the_offer(self):
        """⛔ The shipped defect's exact shape: the offer, then a 'never'.

        "accept the decline (move it to `optional`, or record a merge authorization),
        never another trigger" states a demotion AND a prohibition in one sentence. A
        sentence-level negation test reads the second and acquits the first, which is
        why the negation is scoped to the offer's own clause.
        """
        text = (
            'A required bot on `declined` engaged but declined: the productive action is to accept '
            'the decline (move it to `optional`, or record a merge authorization), never another '
            'trigger.\n'
        )

        assert scanner.offered_demotions(text)

    def test_an_already_optional_bot_is_not_a_demotion(self):
        """The required-vs-optional distinction the deliverable asks for, both arms.

        A sentence about a bot that is ALREADY optional is not offered as a demotion,
        even when it uses the same verb and destination. The paired sentence names a
        required bot and IS reported — so the acceptance above is the distinction, not
        a rule that accepts everything.
        """
        optional = (
            'An optional bot already in `optional_bots` that goes quiet may be moved to '
            '`optional_bots` a second time with no effect.\n'
        )
        required = 'A required bot that goes quiet should be moved to `optional_bots`.\n'

        assert scanner.offered_demotions(optional) == []
        assert scanner.offered_demotions(required)

    def test_the_roster_token_form_is_seen(self):
        """``required_bots`` must be seen: ``\\brequired\\b`` does not match it.

        ``_`` is a word character, so a word boundary does not exist between
        ``required`` and ``_bots``. A sentence phrased only in roster tokens is the
        form a demotion instruction is most likely to take, and a scanner blind to it
        reports a clean corpus over the very defect it exists to catch.
        """
        text = 'Move the bot from `required_bots` to `optional_bots` when it keeps declining.\n'

        assert scanner.offered_demotions(text)

    def test_an_offer_that_names_only_a_reviewer_is_seen(self):
        """The shipped defect that survived the first sweep said "the reviewer", not "required"."""
        text = 'The barrier records a remedy that moves the reviewer to `optional_bots`.\n'

        assert scanner.offered_demotions(text)

    def test_the_disable_this_reviewer_label_is_seen(self):
        """The withdrawn arm's own label names no roster, and is the same demotion."""
        text = 'A required bot that keeps refusing can be handled by disabling this reviewer for this PR.\n'

        assert scanner.offered_demotions(text)

    def test_a_semicolon_ends_the_negation_clause(self):
        """A `not` after a semicolon prohibits the NEXT claim, not the demotion."""
        text = 'Move a required bot to `optional_bots`; do not trigger it again.\n'

        assert scanner.offered_demotions(text)

    def test_a_short_form_destination_is_caught(self):
        """``optional`` without the ``_bots`` suffix is the form the shipped defect used."""
        assert scanner.offered_demotions('If a required bot keeps declining, move it to `optional` instead.\n')

    def test_a_table_row_is_read_as_its_own_claim(self):
        """A row beside a prohibition must not borrow it.

        The contract is a markdown table, so a demotion offer in one cell shares a
        physical line with policy text in the others. Treating the line as one claim
        would let any nearby ``never`` launder it.
        """
        text = '| `declined` | Blocking. | The remedy is to move a required bot to `optional_bots` | never wait. |\n'

        assert scanner.offered_demotions(text)


class TestTheFixtureRootIsHonoured:
    def test_scan_reads_only_the_tree_it_is_given(self, tmp_path):
        """``scan`` is rooted, so a control is a real fixture tree rather than a monkeypatch."""
        fixture = tmp_path / 'bundles' / 'bundle' / 'skill'
        fixture.mkdir(parents=True)
        (fixture / 'doc.md').write_text(
            'A required bot that declines may be moved to `optional_bots`.\n', encoding='utf-8'
        )

        findings = scanner.scan(root=tmp_path / 'bundles')

        assert len(findings) == 1
        assert findings[0][0].name == 'doc.md'
