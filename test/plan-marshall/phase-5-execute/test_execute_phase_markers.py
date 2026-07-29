# SPDX-License-Identifier: FSL-1.1-ALv2
"""Producer/consumer contract for the phase-5 execute-phase marker lines.

Two documents must agree about one pair of literals, and neither may be
pinned in this file:

* **Producer** — ``phase-5-execute/SKILL.md`` Step 4 documents the two
  ``[STATUS]`` work-log emissions: ``Starting execute phase`` on the very first
  entry and ``Re-entering execute phase`` on every re-dispatch.
* **Consumer** — ``plan-retrospective/scripts/analyze-logs.py`` counts those
  lines through ``_STARTING_RE`` / ``_RE_ENTERING_RE`` and reports the two
  counts as ``starting_markers`` / ``re_entering_markers``.

The assertions read BOTH sides at test time — the documented message literal
from the SKILL.md, the regex object from the script — and check that the
producer's literal is matched by the consumer's regex. An edit to either side
that breaks the pairing fails here; neither literal nor regex is duplicated
into this file.

**Vacuity guard.** The historical defect was not a mismatched literal: it was a
first-entry discriminator keyed on the ``5-execute`` phase row's
``status == pending``, a value the SAME document states the preceding
``transition --completed 4-plan`` call already set to ``in_progress``. That
branch was unreachable, so the ``Starting`` line was never emitted and
``starting_markers`` read ``0`` on every real plan while the pairing above
stayed perfectly green. ``test_first_entry_discriminator_is_not_keyed_on_phase_row_status``
is the assertion that fails on a regression back to that shape.

Each detector carries a bites-check proving it fails on the pre-fix text, so a
regex typo cannot make the corresponding assertion vacuously green.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines

from conftest import MARKETPLACE_ROOT, load_script_module

_analyze_logs = load_script_module(
    'plan-marshall', 'plan-retrospective', 'analyze-logs.py', 'analyze_logs_marker_contract_mod'
)

_SKILL_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-5-execute' / 'SKILL.md'
)

#: The Step-4 section that owns the first-entry / re-entry discriminator.
_STEP_4_HEADING = '### Step 4: Log Phase Start and Surface Active Worktree (Once per phase)'
_STEP_STOP_PREFIXES = ('### ', '## ', '---')

#: A documented ``manage-logging work ... --message "<literal>"`` emission.
_MESSAGE_LITERAL_RE = re.compile(r'--message\s+"([^"]*)"')

#: The pre-fix discriminator: a branch keyed on the phase row's own status
#: value, which the same document states the 4-plan transition already advanced.
_PHASE_ROW_STATUS_DISCRIMINATOR_RE = re.compile(
    r'status\s*==\s*`?pending`?|`?pending`?\s+on\s+the\s+very\s+first\s+entry',
    re.IGNORECASE,
)

#: The paired metadata write the first-entry branch must carry. The field and its
#: value are BOTH pinned: a bare ``manage-status metadata --set`` anywhere in the
#: Step-4 section would be satisfied by any unrelated metadata write, so the
#: assertion would pass while the first-entry marker itself was never written and
#: every entry re-reported as a first entry.
_METADATA_SET_RE = re.compile(
    r'manage-status\s+metadata\b[\s\S]{0,200}?--set\b[\s\S]{0,200}?'
    r'--field\s+phase_5_first_entry_logged\b[\s\S]{0,80}?--value\s+true\b'
)


def _skill_text() -> str:
    text: str = _SKILL_DOC.read_text(encoding='utf-8')
    return text


def _step_4_section(text: str | None = None) -> str:
    return '\n'.join(
        section_lines(text if text is not None else _skill_text(), _STEP_4_HEADING, _STEP_STOP_PREFIXES)
    )


def _documented_messages(section: str) -> list[str]:
    """Return every ``--message`` literal documented in ``section``."""
    return _MESSAGE_LITERAL_RE.findall(section)


def _messages_matching(section: str, pattern: re.Pattern[str]) -> list[str]:
    """Return the documented message literals the consumer ``pattern`` matches."""
    return [message for message in _documented_messages(section) if pattern.search(message)]


class TestMarkerLiteralsMatchTheConsumerRegexes:
    """The documented emission literals are matched by the analyze-logs regexes."""

    def test_section_and_messages_are_non_degenerate(self):
        # Anchor: an empty section or an empty message population would make
        # every assertion below vacuously green.
        section = _step_4_section()
        assert section.strip(), f'{_STEP_4_HEADING!r} section is empty'
        assert _documented_messages(section), (
            'Step 4 documents no --message literal — the pairing assertions would be vacuous'
        )

    def test_starting_marker_literal_matches_the_consumer_regex(self):
        matched = _messages_matching(_step_4_section(), _analyze_logs._STARTING_RE)

        assert matched, (
            'phase-5-execute/SKILL.md Step 4 documents no emission line matching '
            "analyze-logs._STARTING_RE — the retrospective's starting_markers count "
            'can never observe a first entry'
        )

    def test_re_entering_marker_literal_matches_the_consumer_regex(self):
        matched = _messages_matching(_step_4_section(), _analyze_logs._RE_ENTERING_RE)

        assert matched, (
            'phase-5-execute/SKILL.md Step 4 documents no emission line matching '
            "analyze-logs._RE_ENTERING_RE — the retrospective's re_entering_markers "
            'count can never observe a re-dispatch'
        )

    def test_the_two_markers_are_distinct_literals(self):
        section = _step_4_section()
        starting = set(_messages_matching(section, _analyze_logs._STARTING_RE))
        re_entering = set(_messages_matching(section, _analyze_logs._RE_ENTERING_RE))

        assert not (starting & re_entering), (
            f'A single documented literal matches BOTH consumer regexes '
            f'{sorted(starting & re_entering)} — the two counts could not distinguish '
            f'a first entry from a re-dispatch'
        )

    def test_detectors_bite_when_the_emission_line_is_absent(self):
        # Bites-check: a Step-4 section that documents no marker emission must
        # fail both pairing assertions. Without this a regex typo would leave
        # them vacuously green.
        pre_fix = (
            'Parse the row count from the returned `tasks_table` and substitute it as `{N}`.\n'
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
            '  work --plan-id {plan_id} --level INFO --message "[STATUS] '
            '(plan-marshall:phase-5-execute) Active worktree: {worktree_path}"\n'
            '```\n'
        )

        assert _documented_messages(pre_fix), 'the pre-fix sample must carry a --message literal'
        assert not _messages_matching(pre_fix, _analyze_logs._STARTING_RE)
        assert not _messages_matching(pre_fix, _analyze_logs._RE_ENTERING_RE)


class TestFirstEntryDiscriminatorIsReachable:
    """The first-entry branch must not be keyed on the phase row's own status."""

    def test_first_entry_discriminator_is_not_keyed_on_phase_row_status(self):
        section = _step_4_section()

        hits = _PHASE_ROW_STATUS_DISCRIMINATOR_RE.findall(section)
        assert not hits, (
            f'Step 4 keys its first-entry branch on the 5-execute phase row being '
            f'`pending`, but the same document states the `transition --completed '
            f'4-plan` call already set that row to `in_progress` — the branch is '
            f'unreachable and the Starting marker is never emitted. Offending '
            f'fragments: {hits}'
        )

    def test_first_entry_branch_pairs_the_emission_with_a_metadata_write(self):
        section = _step_4_section()

        assert _METADATA_SET_RE.search(section), (
            'The first-entry branch must pair its emission with a '
            '`manage-status metadata --set --field phase_5_first_entry_logged '
            '--value true` marker write; without that specific write the next '
            'entry re-reports a first entry and the two counts stop meaning '
            'anything'
        )

    def test_metadata_write_detector_rejects_an_unrelated_metadata_set(self):
        # Mutation guard: the assertion above is only meaningful if the detector
        # rejects a metadata write that is NOT the first-entry marker. The
        # pre-fix regex matched any `--set` in the section, so an unrelated write
        # (or a marker write that lost its field/value) satisfied it vacuously.
        unrelated_write = (
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \\\n'
            '  --plan-id {plan_id} --set --field worktree_path --value /some/path\n'
        )

        assert not _METADATA_SET_RE.search(unrelated_write), (
            'The metadata-write detector matched an unrelated `--set` — it must '
            'pin the phase_5_first_entry_logged field and its true value, or the '
            'pairing assertion is vacuous'
        )

        # Positive control — the real documented shape IS accepted, so the
        # detector is not unconditionally negative.
        marker_write = (
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \\\n'
            '  --plan-id {plan_id} --set --field phase_5_first_entry_logged --value true\n'
        )

        assert _METADATA_SET_RE.search(marker_write)

    def test_discriminator_detector_bites_on_the_pre_fix_shape(self):
        # Bites-check: the exact pre-fix prose must be rejected, or the guard
        # above would be vacuous.
        pre_fix = (
            "The 5-execute phase row's `status` is `pending` on the very first entry "
            'and `in_progress` on every subsequent re-dispatch (the `manage-status '
            'transition --completed 4-plan` call sets it to `in_progress`).\n'
            '- If `status == pending` (first entry) -> emit:\n'
        )

        assert _PHASE_ROW_STATUS_DISCRIMINATOR_RE.search(pre_fix), (
            'The discriminator detector failed to fire on the known pre-fix '
            'phase-row-status branch — the reachability guard would be vacuous'
        )
