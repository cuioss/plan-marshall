#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""`--measured-diff-size` survives the executor's empty-argument strip.

The defect: both documented `review_completeness check` call sites interpolate
`--measured-diff-size "{measured_diff_size}"` UNCONDITIONALLY, while the producer
measures the diff **only** when a size refusal was actually seen. The generated
executor strips every empty-string argument before argparse sees it, so on the
COMMON path — no size refusal — the documented call arrives as a bare
`--measured-diff-size`. The flag declared no `nargs='?'`/`const=''`, unlike every
sibling list flag on the same command, so that call was an argparse rejection
(exit 2). Both call sites route a rejected predicate to their **UNKNOWN** verdict,
and UNKNOWN is the one verdict whose force-done / authorization hatch is explicitly
unavailable — so the documented happy path deadlocked the step. Observed live twice
in one finalize run, worked around both times by omitting the flag by hand.

⛔ **Why the existing D3 guard could not see this.**
`test_review_merge_invocation_contract.py` already parses every documented
review/merge invocation against its real parser, and it passed throughout. It
substitutes an unknown placeholder with `''` and then `shlex.split`s, which yields
`['--measured-diff-size', '']` — an empty-string VALUE, which a value-required flag
accepts. The executor does not deliver that: it DROPS the empty token, leaving a
bare flag. The gap that module misses is therefore a missing TRANSPORT step, which
is what this module models.

The call population it models the transport over is DERIVED from the bundle tree,
never listed: a hand-named pair reports a known doc that stopped matching but is
blind to a `check` call added in a third document, which would then sit outside the
sweep with nothing saying so. A two-element floor is still asserted, because that
blind spot runs both ways — see `_KNOWN_CALL_SITE_DOCS`.

Three layers, and the middle one is what keeps the outer two honest:

1. **The parser accepts the bare form, and bare means the same as omitted.** A
   matched pair — bare vs. omitted — rather than a lone positive, so "the flag
   parses" cannot pass while quietly meaning something else than unmeasured.
2. **The relaxation did not make the flag greedy.** `nargs='?'` must not swallow a
   following flag as its value; asserted against a real sibling flag.
3. **The documented calls survive the strip.** The population is derived by
   scanning every Markdown document under the bundle's `skills/` tree; each
   invocation is stripped as the executor strips and parsed by the real parser —
   with a NON-VACUITY assertion that the strip genuinely produced a bare flag, so a
   doc that stopped interpolating the flag unconditionally fails here instead of
   silently emptying the population this sweep runs over. A document the scan could
   not READ is a HOLE in that population rather than an absence from it — it might
   carry a `check` call and nothing looked — so it is recorded and fails the guard
   by path, never skipped.
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

    This is the exact argv the executor delivers on the common path, and the exact
    argv that was an argparse rejection before the flag declared an optional value.
    """
    assert _parse(_FLAG).measured_diff_size == ''


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
