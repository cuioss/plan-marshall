#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""`--measured-diff-size` reads as unmeasured in every form an empty size arrives in.

Both documented `review_completeness check` call sites interpolate
`--measured-diff-size "{measured_diff_size}"` UNCONDITIONALLY, while the producer
measures the diff **only** when a size refusal was actually seen. On the COMMON
path — no size refusal — the placeholder is empty, and it reaches the parser in
one of two forms:

- an EMPTY VALUE, `['--measured-diff-size', '']` — the quoted placeholder through
  the generated executor, which keeps an empty string that is the value of the
  option before it;
- a BARE flag, `['--measured-diff-size']` — an unquoted placeholder the shell
  removes, or a direct invocation.

A value-required flag rejects the bare form (exit 2), and both call sites route a
rejected predicate to their **UNKNOWN** verdict, whose force-done / authorization
hatch is explicitly unavailable. The flag therefore declares `nargs='?'` with
`const=''`, and this module pins that parser contract:

1. **Bare, empty-valued and omitted are the SAME reading.** A matched set rather
   than a lone positive, so "the flag parses" cannot pass while quietly meaning
   something else than unmeasured.
2. **The relaxation did not make the flag greedy.** `nargs='?'` must not swallow a
   following flag as its value; asserted against a real sibling flag.

The documented call sites themselves are swept, transported as the executor
transports them, by `test_measured_diff_size_bare_flag_scan.py`.
"""

from __future__ import annotations

import re
import shlex

import pytest

from conftest import MARKETPLACE_ROOT, parse_ns

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: The flag under test.
_FLAG = '--measured-diff-size'

#: ``register=False`` throughout: sibling suites import ``review_completeness``
#: plainly, and registering a second copy makes which one a test sees depend on
#: collection order.
_SCRIPT = ('plan-marshall', 'automatic-review', 'review_completeness.py')

#: The minimum argv ``check`` needs before any flag under test is appended.
_BASE_ARGV = ('check', '--plan-id', 'mds-parse-probe')


def _parse(*argv: str):
    """Return the ``argparse.Namespace`` the script's OWN parser builds for ``argv``.

    Never a hand-built namespace: a hand-built one carries only the attributes its
    author remembered, so a flag whose DEFAULT is the thing under test would keep
    passing while production broke.
    """
    return parse_ns(*_SCRIPT, *_BASE_ARGV, *argv, register=False)


# =============================================================================
# 1 + 2 — the parser contract for the bare form
# =============================================================================


def test_the_bare_flag_is_accepted_and_reads_as_unmeasured():
    """POSITIVE: a bare `--measured-diff-size` parses, and reads as unmeasured.

    This is the argv an unquoted empty placeholder or a direct invocation delivers,
    and the argv a value-required flag rejects.
    """
    assert _parse(_FLAG).measured_diff_size == ''


def test_an_empty_value_reads_the_same_as_the_bare_flag():
    """The empty VALUE the executor delivers means what the bare flag means.

    The quoted empty placeholder arrives as `--measured-diff-size ''`. If the two
    forms read differently, the documented call would report something other than
    unmeasured depending on how its placeholder was quoted.
    """
    assert _parse(_FLAG, '').measured_diff_size == _parse(_FLAG).measured_diff_size == ''


def test_bare_and_omitted_are_the_SAME_reading():
    """MATCHED CONTROL: bare is not merely accepted — it means what omitted means.

    Without this pair, the test above would pass on a relaxation that accepted the
    bare form while giving it some other value (a sentinel, the flag's own name),
    and an unmeasured diff would then be reported as a measured one.
    """
    assert _parse(_FLAG).measured_diff_size == _parse().measured_diff_size == ''


def test_a_supplied_value_still_arrives_intact():
    """NEGATIVE control on the relaxation: it widened the empty case only.

    A flag that now accepts nothing at all would satisfy both assertions above.
    """
    assert _parse(_FLAG, '1240 changed lines').measured_diff_size == '1240 changed lines'


def test_the_bare_flag_does_not_swallow_a_following_flag():
    """The `nargs='?'` hazard: an optional value must not consume the next flag.

    Asserted against a real sibling on the same subcommand rather than a synthetic
    token, because the failure would be silent in exactly this shape — the run would
    report a measured diff size of `--triage-ran` AND lose the triage-state input
    that decides whether a pending finding blocks.
    """
    parsed = _parse(_FLAG, '--triage-ran')

    assert parsed.measured_diff_size == ''
    assert parsed.triage_ran is True
