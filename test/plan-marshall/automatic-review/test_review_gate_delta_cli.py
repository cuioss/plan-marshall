#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the review-versus-gate delta signal (plan 130 D2).

*"What did review catch that the in-house gates did not"* is the only direct read
on gate/review parity available, and it arrives free on every PR: the gates run
before review (`pre-push-quality-gate` at order 5, self-review at 7, against
`automatic-review` at 30), so a finding filed against a tree the gates already
passed IS a gate escape. No per-finding gate attribution is needed.

**But "the gates passed" is not "the gates saw this tree".** Source-mutating steps
run between certification and review — `finalize-step-simplify` (8) and
`finalize-step-security-audit` (9), and the gate itself (5), whose own item-5f
commit lands after the tree it just certified — and a forward pass never returns to
order 5 to re-gate their edits, so the escape claim rests on the gate-certified tree
and the reviewed tree being the SAME tree, proven by SHA rather than assumed. No
count is pinned here: membership is whatever each step's declared `mutates_source`
makes it, so a step that declares the fact later is covered by its own declaration.

Three properties make the signal usable rather than harmful, and all are tested
here in the direction that matters:

* **Refusal-PRs are excluded BY CONSTRUCTION.** The bots refuse frequently, so an
  absence of review findings is often an absence of *review*, not of defects. A
  metric that counted a refusal-PR as "zero escapes" would report improving parity
  precisely as reviewer coverage collapsed — this epic's named failure mode. The
  guard is structural: the share is emitted only at FULL coverage, so a collapse
  can only ever move the metric from a number to NO number, never to a better one.

* **Partition before any rate.** The escape set is mixed: some escapes are
  *gate-addressable* (a lint family absent from the select list — a gate
  CONFIGURATION finding), others *gate-structural* (documentation-prose semantics,
  behaviour under un-supplied inputs). A share computed before that partition would
  read a configuration gap as evidence of a structural bot-only class. An
  unpartitioned finding therefore withholds the share rather than being bucketed by
  default.

* **The escape claim is anchored to a tree.** A gate verdict, a gate-certified SHA,
  and a reviewed SHA — each absent or mismatched one excludes the PR, so a finding
  on a line the gates never saw is never counted as a miss they made.
"""

import pytest
from review_gate_delta import (
    PARTITION_GATE_ADDRESSABLE,
    PARTITION_GATE_STRUCTURAL,
    PARTITION_UNPARTITIONED,
    VERDICT_EXCLUDED,
    VERDICT_MEASURED,
    assess_delta,
)

_ROSTER = ['coderabbit', 'cuioss-review-bot', 'sourcery']

#: The tree the gates certified and the tree review reviewed — equal in the
#: measurable case, and the whole subject of the post-gate-mutation exclusion.
_SHA = 'a' * 40


def _finding(hash_id, bot_kind='coderabbit', kind='inline'):
    return {'hash_id': hash_id, 'bot_kind': bot_kind, 'kind': kind}


def _full_coverage(**overrides):
    """A fully-reviewed PR with a complete partition — the only shape that yields a share."""
    kwargs = {
        'findings': [_finding('f1'), _finding('f2'), _finding('f3')],
        'enabled_bots': _ROSTER,
        'reviewed_bots': list(_ROSTER),
        'gates_green': True,
        'gate_head_sha': _SHA,
        'reviewed_head_sha': _SHA,
        'partitions': {
            'f1': PARTITION_GATE_ADDRESSABLE,
            'f2': PARTITION_GATE_STRUCTURAL,
            'f3': PARTITION_GATE_STRUCTURAL,
        },
    }
    kwargs.update(overrides)
    return assess_delta(**kwargs)


# ---------------------------------------------------------------------------
# The measured case
# ---------------------------------------------------------------------------


class TestCLI:
    """The ``assess`` verb's argparse surface and emitted TOON block.

    The pure function above is where the logic lives, but the CLI is what
    `finalize-step-review-retrospective` invokes and what a reader parses. An
    emitter or flag defect ships green if only the pure function is exercised.
    """

    def test_emits_toon_and_zero_exit(self, plan_context):
        from conftest import get_script_path, run_script

        script = get_script_path('plan-marshall', 'automatic-review', 'review_gate_delta.py')
        plan_id = 'rgd-cli'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            script,
            'assess',
            '--plan-id',
            plan_id,
            '--enabled-bots',
            'coderabbit,sourcery',
            '--reviewed-bots',
            'coderabbit,sourcery',
            '--gates-green',
            '--gate-head-sha',
            _SHA,
            '--reviewed-head-sha',
            _SHA,
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'proves: gate_escape_only' in result.stdout
        assert 'gates_merge: false' in result.stdout
        assert 'reviewer_coverage: 2/2' in result.stdout

    def test_omitting_both_gate_flags_excludes_rather_than_assuming_green(self, plan_context):
        """The fail-closed default reaches the CLI, not only the pure function."""
        from conftest import get_script_path, run_script

        script = get_script_path('plan-marshall', 'automatic-review', 'review_gate_delta.py')
        plan_id = 'rgd-cli-nogate'
        plan_context.plan_dir_for(plan_id)

        result = run_script(script, 'assess', '--plan-id', plan_id)

        assert result.success, result.stderr
        assert 'verdict: excluded' in result.stdout
        assert 'gate_state_unsubstantiated' in result.stdout

    def test_gates_red_and_gates_green_are_mutually_exclusive(self):
        """Passing both is a caller error argparse refuses, not a silent last-wins."""
        from review_gate_delta import build_parser

        with pytest.raises(SystemExit):
            build_parser().parse_args(['assess', '--plan-id', 'p', '--gates-green', '--gates-red'])

    def test_bare_list_flags_read_as_empty(self):
        """A caller interpolating an empty variable gets the empty list, not a rejection."""
        from review_gate_delta import build_parser

        args = build_parser().parse_args(
            ['assess', '--plan-id', 'p', '--enabled-bots', '--reviewed-bots', '--partitions']
        )

        assert args.enabled_bots == ''
        assert args.reviewed_bots == ''
        assert args.partitions == ''
        # No gate flag passed at all — the fail-closed sentinel, never False.
        assert args.gates_green is None

    def test_partitions_flag_parses_pairs_and_skips_malformed_tokens(self):
        from review_gate_delta import _parse_partitions

        assert _parse_partitions('a:gate_structural,b:gate_addressable') == {
            'a': 'gate_structural',
            'b': 'gate_addressable',
        }
        # A bare token carries no label; skipping it leaves the finding
        # unpartitioned, which withholds the share — already the fail-closed side.
        assert _parse_partitions('a:gate_structural,bare,,c:') == {'a': 'gate_structural'}
