#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the module-content rules of doctor-test-conventions.

Two warning-severity rules govern what a collected module contains:
`test-module-preamble-boilerplate` (an import preamble resolving a module by
the test file's own location) and `test-docstring-historical-prose` (a
historical citation in a docstring or comment). Each has a positive fixture
that fires it and a negative control that does not."""

import textwrap
from pathlib import Path

from conftest import load_script_module

_analyze_test_conventions = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_test_conventions.py', '_analyze_test_conventions'
)

analyze_test_module_preamble = _analyze_test_conventions.analyze_test_module_preamble
analyze_test_docstring_prose = _analyze_test_conventions.analyze_test_docstring_prose


def _write(test_root: Path, rel_path: str, content: str) -> Path:
    """Materialize one module under the scratch test root."""
    target = test_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content), encoding='utf-8')
    return target


# ---------------------------------------------------------------------------
# test-module-preamble-boilerplate
# ---------------------------------------------------------------------------


def test_spec_from_file_location_is_flagged(tmp_path):
    """A spec_from_file_location preamble is flagged."""
    _write(
        tmp_path,
        'test_preamble.py',
        """
        import importlib.util

        def test_x():
            spec = importlib.util.spec_from_file_location('m', '/tmp/m.py')
            assert spec is not None
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-module-preamble-boilerplate'
    assert findings[0]['details']['kind'] == 'spec_from_file_location'


def test_deep_parent_chain_is_flagged(tmp_path):
    """A Path(__file__) chain of depth three or more is flagged with its depth."""
    _write(
        tmp_path,
        'test_chain.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).parent.parent.parent

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['kind'] == 'parent_chain'
    assert findings[0]['details']['parent_chain_depth'] == 3


def test_shallow_parent_chain_is_not_flagged(tmp_path):
    """A two-deep .parent hop is ordinary path work and is not flagged."""
    _write(
        tmp_path,
        'test_shallow.py',
        """
        from pathlib import Path

        HERE = Path(__file__).parent.parent

        def test_x():
            assert HERE
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_conftest_helpers_are_not_flagged(tmp_path):
    """The sanctioned conftest helpers produce no finding."""
    _write(
        tmp_path,
        'test_clean.py',
        """
        from conftest import get_scripts_dir, load_script_module

        MODULE = load_script_module('bundle', 'skill', 'script.py', 'script')

        def test_x():
            assert get_scripts_dir('bundle', 'skill')
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_resolve_does_not_break_the_chain(tmp_path):
    """A `.resolve()` hop between Path(__file__) and the chain is still flagged.

    `.resolve()` returns an equivalent path, so the chain counts directories
    exactly as a bare one does.
    """
    _write(
        tmp_path,
        'test_resolved.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).resolve().parent.parent.parent

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert [f['details']['parent_chain_depth'] for f in findings] == [3]


def test_parents_index_is_flagged(tmp_path):
    """`parents[N]` is the indexed spelling of an N-deep chain and is flagged as one.

    Without this the rule's count is gameable: respelling a flagged chain as
    `parents[N]` would clear the finding while changing nothing.
    """
    _write(
        tmp_path,
        'test_parents.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[3]

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['parent_chain_depth'] == 3


def test_mixed_chain_and_index_compose(tmp_path):
    """A `.parent` chain feeding `parents[N]` counts as their sum.

    Measuring only the pure spellings would leave the mixed form as an escape
    from the rule's own count.
    """
    _write(
        tmp_path,
        'test_mixed.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).parent.parents[2]

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['parent_chain_depth'] == 3


def test_negative_and_non_constant_index_are_not_flagged(tmp_path):
    """A negative or computed `parents[...]` index is not a directory count."""
    _write(
        tmp_path,
        'test_dynamic.py',
        """
        from pathlib import Path

        def test_x(n=3):
            assert Path(__file__).resolve().parents[n]
            assert Path(__file__).resolve().parents[-1]
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_shallow_parents_index_is_not_flagged(tmp_path):
    """`parents[2]` is below the threshold, matching the `.parent.parent` case."""
    _write(
        tmp_path,
        'test_shallow_parents.py',
        """
        from pathlib import Path

        HERE = Path(__file__).resolve().parents[2]

        def test_x():
            assert HERE
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_one_chain_yields_one_finding(tmp_path):
    """A single deep chain reports once, not once per .parent link."""
    _write(
        tmp_path,
        'test_once.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).parent.parent.parent.parent

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['parent_chain_depth'] == 4


# ---------------------------------------------------------------------------
# test-docstring-historical-prose
# ---------------------------------------------------------------------------


def test_lesson_id_in_docstring_is_flagged(tmp_path):
    """A lesson id cited in a test docstring is flagged."""
    _write(
        tmp_path,
        'test_prose.py',
        '''
        def test_x():
            """Pins the fallback (closes lesson 2026-07-09-04-001)."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-docstring-historical-prose'
    assert findings[0]['severity'] == 'warning'


def test_pr_reference_in_docstring_is_flagged(tmp_path):
    """A PR reference cited in a test docstring is flagged."""
    _write(
        tmp_path,
        'test_pr.py',
        '''
        def test_x():
            """Retains bot review on large plans (PR #551 reviewer finding)."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']


def test_plan_deliverable_id_in_comment_is_flagged(tmp_path):
    """A deliverable id cited in a comment is flagged — comments are prose too."""
    _write(
        tmp_path,
        'test_comment.py',
        """
        def test_x():
            # TASK-004 introduced this guard
            assert True
        """,
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['plan_deliverable_id']


def test_unlettered_deliverable_ordinal_is_flagged(tmp_path):
    """A deliverable cited by bare ordinal is flagged like the lettered spelling."""
    _write(
        tmp_path,
        'test_unlettered.py',
        '''
        def test_x():
            """Retains the guard Deliverable 2 introduced."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['plan_deliverable_id']
    assert findings[0]['details']['matched'] == 'Deliverable 2'


def test_bare_record_number_is_flagged(tmp_path):
    """A record number cited without a ``PR`` prefix is flagged."""
    _write(
        tmp_path,
        'test_bare.py',
        '''
        def test_x():
            """Retains bot review on large plans (reviewer finding in #551)."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']
    assert findings[0]['details']['matched'] == '#551'


def test_spelled_out_pull_request_reference_is_flagged(tmp_path):
    """The ``pull request #NNN`` spelling is flagged like the ``PR #NNN`` one.

    The prefixed alternative accepts both words, and only one of them had a case.
    An untested alternative is one nobody notices losing: this spelling carries no
    digit bound, so a regression narrowing it would be invisible to the bare-form
    cases above, which do.
    """
    _write(
        tmp_path,
        'test_spelled_out.py',
        '''
        def test_x():
            """Keeps the ordering pull request #849 established."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']
    assert findings[0]['details']['matched'] == 'pull request #849'


def test_single_digit_bare_number_is_not_flagged(tmp_path):
    """A one-digit bare number is intra-document enumeration, not a record id."""
    _write(
        tmp_path,
        'test_enumerate.py',
        """
        def test_x():
            # Mis-attribution #1: the caller's own frame is skipped.
            assert True
        """,
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_prefixed_single_digit_record_is_still_flagged(tmp_path):
    """The digit bound is local to the bare form — an explicit ``PR`` prefix still fires.

    Pinning this alongside the bare-form bound is what keeps a later widening from
    "simplifying" the two alternatives into one and silently losing the short
    unambiguous spelling.
    """
    _write(
        tmp_path,
        'test_short_pr.py',
        '''
        def test_x():
            """Retains the guard PR #7 introduced."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']


def test_number_inside_a_hyphenated_compound_is_not_flagged(tmp_path):
    """A number embedded in a hyphenated compound names a state, not a record.

    ``pre-<n>`` and ``post-<n>`` are how this corpus names schema and code eras it
    asserts on, so the number is the test's own data.
    """
    _write(
        tmp_path,
        'test_compound.py',
        """
        def test_x():
            # A pre-#812 record carries neither marker of the pair.
            assert True
        """,
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_record_number_opening_a_docstring_is_flagged(tmp_path):
    """A citation at the very first character of a docstring is flagged.

    The bound that keeps a comment's own ``#`` delimiter from reading as a citation
    must not also silence a docstring that opens with one — the two look identical
    to a lookbehind, and only one of them is punctuation.
    """
    _write(
        tmp_path,
        'test_opening.py',
        '''
        def test_x():
            """#1014 regression: the refusal is seen only because it is filed as data."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']
    assert findings[0]['details']['matched'] == '#1014'


def test_comment_delimiter_does_not_read_as_a_record_number(tmp_path):
    """A comment whose text begins with digits is not a citation of that number.

    Comment segments arrive from ``tokenize`` with the ``#`` delimiter attached, so
    without the preceding-character bound the delimiter itself would open a match.
    """
    _write(
        tmp_path,
        'test_delimiter.py',
        """
        def test_x():
            #551 rows are emitted before the summary.
            assert True
        """,
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_present_tense_docstring_is_not_flagged(tmp_path):
    """A docstring stating the invariant in the present tense produces no finding."""
    _write(
        tmp_path,
        'test_clean_prose.py',
        '''
        def test_x():
            """An uninventoried test path resolves through the paths.tests fallback."""
            assert True
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_citation_shape_as_string_data_is_not_flagged(tmp_path):
    """A lesson id used as test DATA is not a citation and is not flagged.

    This is the rule's structural discriminator: the same textual shapes appear
    far more often as the corpus a test operates on than as prose, so the scan
    reaches docstrings and comments only.
    """
    _write(
        tmp_path,
        'test_data.py',
        '''
        LESSON_IDS = ['2026-07-09-04-001', '2026-05-02-01-001']

        def test_x():
            """Every seeded lesson id round-trips through the validator."""
            assert all(validate(i) for i in LESSON_IDS)
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_backticked_id_named_as_a_value_is_not_flagged(tmp_path):
    """An id inside an inline literal names a value and is not a citation.

    Prose has to name values as well as cite records, and the two are told apart
    by formatting rather than by shape: the contract a test pins is often an
    exact id, so flagging it would force the docstring to omit the very thing
    the test asserts.
    """
    _write(
        tmp_path,
        'test_value.py',
        '''
        def test_x():
            """``get_next_id`` returns ``2025-01-01-02-001`` when no prior lesson exists."""
            assert True
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_quoted_id_named_as_a_value_is_not_flagged(tmp_path):
    """Single and double quotes mark a named value exactly as backticks do."""
    _write(
        tmp_path,
        'test_quoted.py',
        '''
        def test_x():
            """The cross-ref group key is '2025-02-01-01-001', so it sorts first."""
            # the command writes "TASK-001.json" into the tasks dir
            assert True
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_bare_id_beside_a_backticked_one_is_still_flagged(tmp_path):
    """The exemption is per-occurrence, not per-segment.

    A docstring that names a value AND cites a record must still report the
    citation, or backticking anything would launder the whole segment.
    """
    _write(
        tmp_path,
        'test_mixed.py',
        '''
        def test_x():
            """Returns ``2025-01-01-02-001``; added for lesson 2026-07-09-04-001."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['matched'] == 'lesson 2026-07-09-04-001'


def test_possessive_apostrophe_does_not_open_a_literal_span(tmp_path):
    """An apostrophe in ordinary prose must not exempt the rest of the docstring.

    A prose segment reaches the matcher as ONE multi-line string, so a quote
    alternative that crossed newlines would let a possessive on one line and a
    contraction further down open a single span swallowing every citation
    between them. That is a false negative, which is the direction that matters:
    the rule would report clean over prose it never actually examined.
    """
    _write(
        tmp_path,
        'test_possessive.py',
        '''
        def test_x():
            """The resolver's exact-match guard runs first.

            It doesn't fall through to the prefix scan, so the cache tree stays
            addressable. Regression for PR #515.
            """
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']


def test_two_apostrophes_on_one_line_do_not_open_a_literal_span(tmp_path):
    """The same-line case, which the newline bound alone does NOT cover.

    A possessive and a contraction in one sentence sit on the same line, so
    bounding literals to a single line leaves them free to span the citation
    between them. What separates an apostrophe from a quote delimiter is
    adjacency: a possessive or contraction always sits against a word character,
    an opening delimiter never does.
    """
    _write(
        tmp_path,
        'test_same_line.py',
        '''
        def test_x():
            """The resolver's PR #515 guard doesn't fall through."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']


def test_double_backticked_lesson_citation_is_still_flagged(tmp_path):
    """``lesson ``<id>`` `` is a citation: the prose word sits OUTSIDE the span.

    The house convention is RST double backticks, so a narrative-citation guard
    that understood only the single-backtick form would hand every such citation
    to the inline-literal exemption and report clean.
    """
    _write(
        tmp_path,
        'test_double.py',
        '''
        def test_x():
            """Lesson ``2026-05-02-01-001`` documents the originating incident."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['kind'] == 'lesson_id_backtick'


def test_finding_reports_the_citation_line_not_the_declaration(tmp_path):
    """The reported line is the citation's own line inside a multi-line docstring.

    The finding exists to be navigated to, so anchoring it on the `def` line
    would send the reader to the wrong place in every long docstring.
    """
    _write(
        tmp_path,
        'test_deep.py',
        '''
        def test_x():
            """Line one of the docstring.

            Line three, still fine.

            Closes lesson 2026-07-09-04-001.
            """
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert len(findings) == 1
    # The docstring literal opens on line 3; the citation sits on line 7.
    assert findings[0]['line'] == 7


def test_one_finding_per_prose_segment(tmp_path):
    """A docstring carrying two citation shapes reports once, not once per shape."""
    _write(
        tmp_path,
        'test_multi.py',
        '''
        def test_x():
            """Guard added in PR #551 for lesson 2026-07-09-04-001."""
            assert True
        ''',
    )

    assert len(analyze_test_docstring_prose(tmp_path)) == 1


def test_missing_test_root_is_a_noop(tmp_path):
    """Both module-content rules return no findings when the test root is absent."""
    absent = tmp_path / 'no-such-tree'

    assert analyze_test_module_preamble(absent) == []
    assert analyze_test_docstring_prose(absent) == []
