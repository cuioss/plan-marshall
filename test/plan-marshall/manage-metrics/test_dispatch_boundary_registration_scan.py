#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The boundary-registration scan reads BOTH documented continuation styles.

``scan_boundary_registrations`` decides whether a ``record-dispatch-boundary``
occurrence is a dispatch or prose by testing whether the executor notation stands
immediately before the verb on the same LOGICAL line. The scan enters at the
physical line carrying the verb, so the logical line must be reconstructed in both
directions: forward for the arguments, backward for the notation. This repository
writes executor invocations in both shapes — notation and verb together, and
notation alone with the verb on the next line after a trailing backslash.

A miss in the backward direction is invisible at the call site. The occurrence is
filed under ``prose_mentions``, a bucket no consumer asserts over, and the derived
``registering_classes`` set silently loses a class. The only property computed over
that set is disjointness against the declared exclusion tuple, and a SMALLER set
satisfies disjointness more easily — so a dropped registration fails toward GREEN
inside the very scan written to make the declaration checkable. These tests assert
over the classification itself, which is what no other test reads.
"""

# ruff: noqa: I001
import importlib.util

from _manage_metrics_fixtures import SCRIPT_PATH

# kebab-case filename — load via importlib under a unique module name.
_spec = importlib.util.spec_from_file_location('manage_metrics_registration_scan', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)


_NOTATION = 'python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics'

#: The shape every live ``record-dispatch-boundary`` call site uses today: the
#: executor notation and the verb on one physical line.
_VERB_ON_NOTATION_LINE = (
    '```bash\n'
    f'{_NOTATION} record-dispatch-boundary \\\n'
    '  --plan-id {plan_id} --phase 5-execute --termination-cause completed\n'
    '```\n'
)

#: The repository's other documented style — notation, trailing backslash, verb on
#: the NEXT physical line. No boundary call site uses it today, which is exactly
#: why nothing else in the suite exercises it.
_VERB_ON_CONTINUATION_LINE = (
    '```bash\n'
    f'{_NOTATION} \\\n'
    '  record-dispatch-boundary --plan-id {plan_id} --phase 5-execute \\\n'
    '  --termination-cause completed\n'
    '```\n'
)

#: A sentence naming the verb without dispatching it.
_PROSE_MENTION = (
    'The orchestrator calls `record-dispatch-boundary` once per dispatch, after\n'
    'the returned envelope has been classified.\n'
)


def _scan(tmp_path, body: str) -> dict:
    """Scan a synthetic one-document bundles root holding ``body``.

    The document count is asserted here so every arm below carries its
    anti-vacuity precondition: a scan that walked nothing would make each
    ``registering_classes`` equality trivially decidable from an empty tree.
    """
    (tmp_path / 'skill').mkdir()
    (tmp_path / 'skill' / 'SKILL.md').write_text(body, encoding='utf-8')

    scan: dict = manage_metrics.scan_boundary_registrations(tmp_path)

    assert scan['documents_scanned'] == 1, scan
    return scan


class TestBothContinuationStylesAreRead:
    """A call site is derived as a registration in either continuation style."""

    def test_verb_on_the_continuation_line_is_derived_as_a_registration(self, tmp_path):
        """Notation on one line, verb on the next: still a dispatch, not prose."""
        scan = _scan(tmp_path, _VERB_ON_CONTINUATION_LINE)

        assert scan['registering_classes'] == ('phase-5-execute',), scan
        assert scan['invocations_found'] == 1, scan
        assert not scan['prose_mentions'], scan['prose_mentions']
        assert not scan['unparsed'], scan['unparsed']

    def test_verb_on_the_notation_line_is_derived_as_a_registration(self, tmp_path):
        """CHARACTERIZATION arm: the style every live call site uses, pinned."""
        scan = _scan(tmp_path, _VERB_ON_NOTATION_LINE)

        assert scan['registering_classes'] == ('phase-5-execute',), scan
        assert scan['invocations_found'] == 1, scan
        assert not scan['prose_mentions'], scan['prose_mentions']


class TestProseIsStillToldApartFromADispatch:
    """The matched negative control for the arms above.

    Reaching the notation cannot be achieved by loosening the dispatch test until
    every occurrence of the verb counts: prose naming the verb must stay out of the
    registering set, and must still be told apart from a real call site sitting in
    the same document.
    """

    def test_prose_naming_the_verb_stays_out_of_the_registering_set(self, tmp_path):
        scan = _scan(tmp_path, _PROSE_MENTION)

        assert scan['registering_classes'] == (), scan
        assert scan['invocations_found'] == 0, scan
        assert len(scan['prose_mentions']) == 1, scan['prose_mentions']

    def test_a_call_site_and_a_prose_mention_in_one_document_are_told_apart(self, tmp_path):
        scan = _scan(tmp_path, _PROSE_MENTION + '\n' + _VERB_ON_CONTINUATION_LINE)

        assert scan['registering_classes'] == ('phase-5-execute',), scan
        assert len(scan['registering']) == 1, scan['registering']
        assert len(scan['prose_mentions']) == 1, scan['prose_mentions']
