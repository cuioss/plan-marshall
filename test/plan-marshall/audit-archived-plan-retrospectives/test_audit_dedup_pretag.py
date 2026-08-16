#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The dedup pre-tagger — a finding is tagged ``novel`` or ``covered_by:{lesson_id}``
against the existing lesson corpus.
"""

from _audit_fixtures import audit


class TestDedupPretag:
    """``_dedup_pretag`` is the Gate-1 PRE-filter: ``novel`` when no filed lesson
    covers the signature, ``covered_by:{lesson_id}`` when one does — using the
    same substring containment match as the body's adjudication."""

    def test_empty_signature_is_novel(self):
        assert audit._dedup_pretag('', ['lesson-x\tsome title']) == 'novel'
        assert audit._dedup_pretag('   ', ['lesson-x\tsome title']) == 'novel'

    def test_uncovered_signature_is_novel(self):
        # corpus title shares no containment with the signature
        corpus = ['lesson-2026-06-01-12-001\tflaky network retry']

        assert audit._dedup_pretag('scope estimate drift', corpus) == 'novel'

    def test_covered_signature_names_the_lesson_id(self):
        # corpus entry is `lesson_id\ttitle`; substring containment fires
        corpus = ['lesson-2026-06-01-12-001\tdisproportionate token usage in finalize']

        tag = audit._dedup_pretag('disproportionate token usage', corpus)

        # names the covering lesson id parsed from the corpus filename stem
        assert tag == 'covered_by:lesson-2026-06-01-12-001'

    def test_existing_substring_of_signature_also_covers(self):
        # symmetric containment: corpus title is a substring of the sig
        corpus = ['lesson-99\ttoken drift']

        tag = audit._dedup_pretag('recurring token drift signature', corpus)

        assert tag == 'covered_by:lesson-99'

    def test_tab_prefixed_entry_with_empty_lesson_id_returns_bare_covered(self):
        # a leading-tab entry yields an empty lesson_id, so there is no
        # id to qualify the tag with; the title still drives containment.
        corpus = ['\tdisproportionate token usage']

        tag = audit._dedup_pretag('disproportionate token usage in finalize', corpus)

        # covered, but no id available to qualify it
        assert tag == 'covered'

    def test_bare_title_entry_uses_title_as_lesson_id(self):
        # a corpus entry with no tab → the whole string is the
        # lesson_id (and also the containment title via the `title or lesson_id`
        # fallback), so the tag is qualified with that string.
        corpus = ['disproportionate token usage']

        tag = audit._dedup_pretag('disproportionate token usage in finalize', corpus)

        assert tag == 'covered_by:disproportionate token usage'

    def test_case_insensitive_containment(self):
        # match must be case-insensitive
        corpus = ['lesson-7\tTOKEN Drift Pattern']

        tag = audit._dedup_pretag('token drift pattern', corpus)

        assert tag == 'covered_by:lesson-7'
