# SPDX-License-Identifier: FSL-1.1-ALv2
"""Operator-provenance classification tests (``_chat_provenance``).

The predicate decides whether a `user` turn is operator-authored, and every
operator-signal counter downstream rests on it. It is positive and structural:
a turn survives only when prose remains after every harness envelope is
stripped, so an envelope shape nobody enumerated classifies as synthetic
rather than inflating the count.

These tests hold both directions — harness injections must not read as
operator signal, and genuine operator prose must not be refused.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import (  # noqa: E402
    OPERATOR_TEXT,
    REENTRY_NOTICE,
    SKILL_LOAD_TEXT,
    SLASH_COMMAND,
    STOP_HOOK_NOTICE,
    SYSTEM_REMINDER,
    TASK_NOTIFICATION,
    WAKE_ENVELOPE,
)

from conftest import load_script_module  # noqa: E402

_mod = load_script_module('plan-marshall', 'plan-retrospective', '_chat_provenance.py')


class TestSyntheticClasses:
    def test_operator_prose_is_operator_authored(self):
        """Free-form operator text is the signal the reduction exists to keep."""
        assert _mod.is_operator_authored(OPERATOR_TEXT) is True

    def test_whole_harness_envelope_is_not_operator_authored(self):
        """A turn that is nothing but a harness envelope carries no operator prose."""
        for injected in (SYSTEM_REMINDER, TASK_NOTIFICATION, WAKE_ENVELOPE):
            assert _mod.is_operator_authored(injected) is False

    def test_unrecognised_wrapper_fails_toward_synthetic(self):
        """A wrapper nobody enumerated still classifies as synthetic.

        This is the whole point of the positive predicate. An enumeration of
        known synthetic shapes fails toward "operator" for a wrapper the
        harness adds later, which inflates the survivor count and manufactures
        a falsely healthy verdict; residue-based classification fails the other
        way.
        """
        unknown = '<a-wrapper-invented-later>\ntext\n</a-wrapper-invented-later>'
        assert _mod.is_operator_authored(unknown) is False

    def test_self_closing_envelope_is_synthetic(self):
        """A self-closing tag is an envelope with no body, not prose."""
        assert _mod.is_operator_authored('<harness-ping />') is False

    def test_nested_same_name_envelope_is_fully_stripped(self):
        """Same-name nesting must pair innermost-to-outermost.

        Pairing a close tag against the OUTERMOST open of that name would
        leave the surplus close tag in the residue, so a wholly-enveloped turn
        would read as operator.
        """
        assert _mod.strip_harness_envelopes('<a><a>x</a></a>').strip() == ''
        assert _mod.is_operator_authored('<a><a>x</a></a>') is False

    def test_stacked_envelopes_leave_no_residue(self):
        """Several concatenated envelopes are still wholly synthetic."""
        assert _mod.is_operator_authored(f'{SYSTEM_REMINDER}\n\n{TASK_NOTIFICATION}') is False

    def test_skill_body_and_empty_remain_synthetic(self):
        """The two originally-enumerated classes still classify as synthetic."""
        assert _mod.is_operator_authored(SKILL_LOAD_TEXT) is False
        assert _mod.is_operator_authored('   \n\t ') is False


class TestEnvelopelessNotices:
    def test_reentry_notice_is_not_operator_authored(self):
        assert _mod.is_operator_authored(REENTRY_NOTICE) is False

    def test_stop_hook_notice_is_not_operator_authored(self):
        """A tagless harness notice is the class the structural rule cannot see.

        It carries no envelope, so only its words identify it. Left
        unrecognised it lands in `operator_turn_count` and can carry the
        verdict on its own.
        """
        assert _mod.is_operator_authored(STOP_HOOK_NOTICE) is False

    def test_notice_matching_is_anchored_at_the_start(self):
        """A notice IS the turn; an operator QUOTING one is still signal.

        Matching the phrase anywhere would drop a genuine operator turn that
        merely refers to it.
        """
        quoted = f'why did I get this? {REENTRY_NOTICE}'
        assert _mod.is_harness_notice(quoted) is False
        assert _mod.is_operator_authored(quoted) is True


class TestOperatorProseSurvives:
    def test_operator_prose_with_attached_envelope_survives(self):
        """The harness attaches reminders to genuine operator turns.

        Presence of an envelope is not the test — emptiness of the residue is —
        so an operator turn does not become synthetic by being annotated.
        """
        assert _mod.is_operator_authored(f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}') is True

    def test_operator_quoting_markup_survives(self):
        """Markup inside operator prose leaves residue, so the turn is kept."""
        assert _mod.is_operator_authored('replace <div>x</div> with a span') is True

    def test_unmatched_open_tag_does_not_swallow_operator_prose(self):
        """Only a MATCHED pair is an envelope.

        If an unmatched `<tag>` opened an envelope that ran to end-of-turn,
        operator prose following it would be stripped and the turn silently
        reclassified as synthetic.
        """
        assert _mod.strip_harness_envelopes('<unclosed> keep this prose') == (
            '<unclosed> keep this prose'
        )
        assert _mod.is_operator_authored('<unclosed> please revert that change') is True

    def test_unmatched_close_tag_is_ordinary_text(self):
        """A close tag with no open tag is prose, not an envelope."""
        assert _mod.is_operator_authored('the build printed </error> — why?') is True

    def test_prose_after_a_trailing_envelope_survives(self):
        """Text following the LAST envelope must reach the residue.

        The commonest real shape is a harness reminder prepended to what the
        operator wrote. If the tail after the final envelope were dropped, that
        entire turn class would vanish — under-counting operator signal, which
        is this plan's headline failure direction.
        """
        text = f'{SYSTEM_REMINDER}\nplease revert that change'
        residue = _mod.strip_harness_envelopes(text)
        assert residue.strip() == 'please revert that change'
        assert _mod.is_operator_authored(text) is True

    def test_heading_must_follow_the_skill_load_marker(self):
        """A heading BEFORE the marker does not make the turn a skill body.

        An operator writing notes under a heading and then asking about the
        marker line is real signal.
        """
        text = '# My notes\n\nWhat does "Base directory for this skill:" mean?'
        assert _mod.is_synthetic_skill_load(text) is False
        assert _mod.is_operator_authored(text) is True

    def test_a_surplus_close_tag_does_not_crash_the_walk(self):
        """More closes than opens must not abort the reduction.

        An unbalanced turn is ordinary malformed input; raising here would take
        the whole transcript down through `safe_main` as `internal_error`,
        losing every operator turn in it.
        """
        text = '<a></a></a> please revert that change'
        assert _mod.is_operator_authored(text) is True

    def test_a_self_closing_operator_bearing_tag_recovers_nothing(self):
        """`<command-args/>` has no body, so there is no instruction to recover."""
        residue, recovered = _mod.partition_turn('<command-args/>')
        assert recovered == ''
        assert _mod.is_operator_authored('<command-args/>') is False

    def test_a_malformed_open_tag_does_not_pair(self):
        """A tag whose attributes contain `<` is not a well-formed envelope.

        Pairing it would empty the residue and reclassify operator prose as
        synthetic.
        """
        assert _mod.is_operator_authored('<a<b>x</a>') is True

    def test_stray_open_tag_does_not_suppress_a_later_envelope(self):
        """An unmatched tag must not turn off stripping for the rest of the turn.

        Only the outermost MATCHED pair is removed, so a stray `<Integer>` in
        operator prose cannot keep a well-formed reminder in the residue — a
        fail-toward-operator path, the direction that manufactures the false
        clean verdict.
        """
        text = f'List<Integer>\n{SYSTEM_REMINDER}'
        residue = _mod.strip_harness_envelopes(text)
        assert 'List<Integer>' in residue
        assert 'claudeMd' not in residue
        assert _mod.is_operator_authored(text) is True


class TestOperatorBearingEnvelopes:
    def test_slash_command_carries_operator_intent(self):
        """A slash command is the operator's primary channel in this project.

        The envelope is the harness's, but the words inside `<command-args>`
        are the operator's. Dropping the block wholesale zeroes the channel
        through which runs are actually driven — a false refusal, the mirror
        of the defect this reduction fixes.
        """
        assert _mod.is_operator_authored(SLASH_COMMAND) is True
        residue = _mod.strip_harness_envelopes(SLASH_COMMAND)
        assert 'fix the provenance filter' in residue
        assert 'plan-marshall is running' not in residue

    def test_argumentless_command_carries_no_operator_prose(self):
        """A bare `/clear` is session management, not analysable operator signal.

        Only `<command-args>` is operator-bearing, so a command invocation with
        no arguments leaves no residue and cannot carry the verdict by itself.
        """
        assert _mod.OPERATOR_BEARING_TAGS == frozenset({'command-args'})
        assert _mod.is_operator_authored('<command-name>/clear</command-name>') is False

    def test_command_args_nested_in_a_harness_envelope_stays_synthetic(self):
        """Operator-bearing tags are only honoured at the top level."""
        nested = '<system-reminder><command-args>x</command-args></system-reminder>'
        assert _mod.is_operator_authored(nested) is False

    def test_a_notice_prefix_does_not_veto_a_recovered_instruction(self):
        """A turn can open with a harness notice AND carry an operator command.

        The notice check runs on the residue, and the residue carries the text
        recovered from `<command-args>`. Without partitioning the two apart, a
        notice sitting at the front of the turn discards an instruction the
        operator explicitly typed — and every prefix added to the backstop
        widens that window.
        """
        for notice in _mod.HARNESS_NOTICE_PREFIXES:
            text = f'{notice} …\n<command-args>rewrite the provenance filter</command-args>'
            assert _mod.is_operator_authored(text) is True, notice

    def test_partition_returns_only_recovered_text_in_the_second_half(self):
        """The second half is the recovered text ALONE, not the whole residue.

        A turn mixing prose, a harness envelope and a command block separates
        three ways. If the second half were merely the residue again, the early
        return in `is_operator_authored` would fire on plain prose — admitting
        any turn whose residue is a harness notice but which happens to carry
        an envelope pair.
        """
        text = f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}\n<command-args>rerun verify</command-args>'
        residue, recovered = _mod.partition_turn(text)

        assert recovered.strip() == 'rerun verify'
        assert OPERATOR_TEXT not in recovered
        assert OPERATOR_TEXT in residue
        assert 'claudeMd' not in residue

    def test_partition_recovers_nothing_when_no_command_block_is_present(self):
        """The pairs loop runs, strips an envelope, and recovers nothing."""
        residue, recovered = _mod.partition_turn(f'keep this {SYSTEM_REMINDER} and this')
        assert recovered == ''
        assert 'keep this' in residue
        assert 'claudeMd' not in residue

    def test_a_notice_alone_is_still_synthetic(self):
        """The notice veto still applies when nothing was recovered."""
        for notice in _mod.HARNESS_NOTICE_PREFIXES:
            assert _mod.is_operator_authored(f'{notice} and then some body text') is False

    def test_a_notice_is_matched_after_envelopes_are_stripped(self):
        """The notice check reads the RESIDUE, not the raw turn.

        The harness attaches envelopes ahead of its own notices, so a turn that
        does not begin with a notice can still be one once the envelopes are
        removed.
        """
        assert _mod.is_operator_authored(f'{SYSTEM_REMINDER}\n{STOP_HOOK_NOTICE}') is False

    def test_whitespace_only_command_args_is_not_operator_signal(self):
        """Recovered text must be non-whitespace, not merely present.

        `/compact ` yields an args block holding only whitespace. Admitting a
        turn on the mere presence of the block would let a harness notice
        carrying an empty command block read as operator — fail-toward-
        operator, the direction this predicate exists to close.
        """
        assert _mod.is_operator_authored('<command-args>   </command-args>') is False
        assert _mod.is_operator_authored(
            f'{STOP_HOOK_NOTICE}\n<command-args>  </command-args>'
        ) is False

    def test_a_skill_body_carrying_a_command_block_is_still_synthetic(self):
        """The skill-load check runs BEFORE the recovered-text early return.

        An injected skill body that quotes a command block must not be admitted
        by the operator-bearing allow-list.
        """
        text = f'{SKILL_LOAD_TEXT}\n<command-args>do the thing</command-args>'
        assert _mod.is_operator_authored(text) is False


class TestEnvelopeStrippingIsLinear:
    def test_unmatched_markup_does_not_blow_up_the_pre_pass(self):
        """A transcript of unmatched `<` markup must not hang the reduction.

        Pairing each open tag with a scan to end-of-text is quadratic: measured
        at 0.5 s for 0.06 MB, which extrapolates to minutes at the 2 MiB read
        budget. The budget below is deliberately loose; it fails on a return to
        quadratic behaviour, not on ordinary machine variance.
        """
        import time

        text = '<unclosed> filler text here ' * 80_000
        assert len(text) > 2 * 1024 * 1024
        started = time.perf_counter()
        _mod.is_operator_authored(text)
        assert time.perf_counter() - started < 10.0
