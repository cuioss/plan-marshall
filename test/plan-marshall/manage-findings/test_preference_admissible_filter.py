#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``list --preference-admissible`` — the emitter's executable authorship gate.

The per-plan preference emitter was asked to apply the authorship-admissibility
rule as PROSE: a paragraph instructing it to exclude findings that are the
pipeline's own control traffic, with no script behind the instruction and no test
binding it to a result. It now INVOKES the rule through this flag, and this module
is what binds the two together — it drives the same ``cmd_query`` surface the CLI
dispatches to and asserts both exclusions alongside both paired negative controls.

The rule itself is not restated here. It has exactly one implementation, in
``manage-findings/scripts/_preference_admissibility.py``, and the reasoning behind
its shape lives in ``phase-6-finalize/standards/disposition-to-hint-routing.md``
§ "(e) Authorship admissibility".
"""

import json
from argparse import Namespace

from _manage_findings_fixtures import _add_ns, cmd_add, cmd_query

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'pref-adm-mixed-off',
    'pref-adm-mixed-on',
    'pref-adm-missing-bot-kind',
    'pref-adm-non-comment',
    'pref-adm-recognized-bot',
    'pref-adm-unrecognized-bot',
)

#: A ``bot_kind`` value that is NOT a recognized reviewer identity. The registry
#: derives the recognized set from ``automatic-review/standards/{bot_kind}.md``,
#: and Sonar is a findings PRODUCER rather than a reviewer bot, so this value can
#: reach the store on a legacy record but must never clear the gate.
UNRECOGNIZED_BOT_KIND = 'sonarcloud'


def _list_ns(plan_id, *, preference_admissible=False):
    """Build a ``list`` namespace carrying the preference-admissibility opt-in.

    Built here rather than by extending the shared ``_manage_findings_fixtures``
    builder, deliberately: that builder is the namespace every OTHER
    manage-findings test module passes, and its continuing LACK of this attribute
    is what keeps proving that ``cmd_query`` still serves a caller which never
    heard of the flag.
    """
    return Namespace(
        plan_id=plan_id,
        type=None,
        resolution=None,
        promoted=None,
        file_pattern=None,
        include_qgate=False,
        author=None,
        kind=None,
        bot_kind=None,
        preference_admissible=preference_admissible,
    )


def _titles(result):
    """The titles a query returned, sorted so the assertion is order-independent."""
    return sorted(finding['title'] for finding in result['findings'])


def _write_unrecognized_bot_comment(plan_context, plan_id, title, hash_id):
    """Append a pr-comment carrying an UNRECOGNIZED ``bot_kind``, bypassing ``add``.

    ``add_finding`` validates ``bot_kind`` against the live registry and rejects a
    present-but-unrecognized value, so this record cannot be produced through the
    ``add`` verb at all. It nonetheless occurs in the wild — a legacy, de-registered
    or hand-edited record already in the store — and excluding it is precisely what
    distinguishes the admissibility gate from a bare presence check. It is therefore
    written the only way it can occur: straight into the per-type JSONL file the read
    surface merges.
    """
    findings_dir = plan_context.plan_dir_for(plan_id) / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'hash_id': hash_id,
        'timestamp': '2026-01-01T00:00:00Z',
        'type': 'pr-comment',
        'title': title,
        'detail': 'archived record carrying a de-registered bot_kind',
        'resolution': 'suppressed',
        'resolution_detail': None,
        'promoted': False,
        'promoted_to': None,
        'author': UNRECOGNIZED_BOT_KIND,
        'bot_kind': UNRECOGNIZED_BOT_KIND,
    }
    with (findings_dir / 'pr-comment.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')


def _seed_mixed_corpus(plan_context, plan_id):
    """File all four shapes the gate discriminates between into one plan.

    Two inadmissible (a pr-comment with no ``bot_kind`` — the shape of the
    pipeline's own posted comment — and one with an unrecognized ``bot_kind``) and
    two admissible (a recognized-reviewer pr-comment, and a non-comment tool
    finding). One corpus exercised twice, with the flag off and on, is what makes
    the flag itself the only variable between the two outcomes.
    """
    cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='pr-comment',
            title='Pipeline note',
            detail='the pipeline own posted comment: author present, bot_kind absent',
            author='repo-owner-bot',
        )
    )
    cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='pr-comment',
            title='Reviewer claim',
            detail='positively attributed to a recognized reviewer bot',
            author='coderabbitai',
            bot_kind='coderabbit',
        )
    )
    cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='lint-issue',
            title='Unused import',
            detail='tool output: no author, no bot_kind, never pipeline chatter',
        )
    )
    _write_unrecognized_bot_comment(plan_context, plan_id, 'Spurious claim', 'rawunrecog')


# =============================================================================
# Test: the two exclusions
# =============================================================================


def test_missing_bot_kind_pr_comment_is_excluded(plan_context):
    """A pr-comment with no bot_kind is the pipeline's own traffic — not evidence."""
    plan_id = 'pref-adm-missing-bot-kind'
    cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='pr-comment',
            title='Pipeline note',
            detail='d',
            author='repo-owner-bot',
        )
    )

    result = cmd_query(_list_ns(plan_id, preference_admissible=True))

    assert result['status'] == 'success'
    assert result['findings'] == []
    assert result['filtered_count'] == 0
    # The narrowing acts on the filtered slice: the store's own total is unchanged,
    # so a caller can still tell "excluded by the gate" from "the store was empty".
    assert result['total_count'] == 1


def test_unrecognized_bot_kind_pr_comment_is_excluded(plan_context):
    """Presence of bot_kind is not the test — the value must be a recognized one."""
    plan_id = 'pref-adm-unrecognized-bot'
    _write_unrecognized_bot_comment(plan_context, plan_id, 'Spurious claim', 'rawunrecog')

    result = cmd_query(_list_ns(plan_id, preference_admissible=True))

    assert result['status'] == 'success'
    assert result['findings'] == []
    assert result['filtered_count'] == 0
    assert result['total_count'] == 1


# =============================================================================
# Test: the two paired negative controls
# =============================================================================


def test_recognized_bot_pr_comment_is_retained(plan_context):
    """NEGATIVE CONTROL — a recognized reviewer's comment must still come back.

    A gate that also suppressed this has broken the feature to fix the bug.
    """
    plan_id = 'pref-adm-recognized-bot'
    cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='pr-comment',
            title='Reviewer claim',
            detail='d',
            author='coderabbitai',
            bot_kind='coderabbit',
        )
    )

    result = cmd_query(_list_ns(plan_id, preference_admissible=True))

    assert _titles(result) == ['Reviewer claim']
    assert result['filtered_count'] == 1


def test_non_comment_finding_is_retained(plan_context):
    """NEGATIVE CONTROL — the gate is scoped to pr-comment findings.

    A tool finding carries no author and no bot_kind and is never pipeline-authored
    PR chatter; its disposition recurrences are the primary preference signal.
    """
    plan_id = 'pref-adm-non-comment'
    cmd_add(_add_ns(plan_id=plan_id, type='lint-issue', title='Unused import', detail='d'))

    result = cmd_query(_list_ns(plan_id, preference_admissible=True))

    assert _titles(result) == ['Unused import']
    assert result['filtered_count'] == 1


# =============================================================================
# Test: one corpus, flag off vs on
# =============================================================================


def test_flag_off_returns_every_finding(plan_context):
    """Default OFF: the narrowing costs an existing caller nothing.

    The emitter's three ``list`` calls are the only callers that opt in, so this is
    the assertion that every other consumer of ``list`` is unaffected.
    """
    plan_id = 'pref-adm-mixed-off'
    _seed_mixed_corpus(plan_context, plan_id)

    result = cmd_query(_list_ns(plan_id))

    assert _titles(result) == ['Pipeline note', 'Reviewer claim', 'Spurious claim', 'Unused import']
    assert result['filtered_count'] == 4


def test_flag_on_keeps_only_the_admissible_findings(plan_context):
    """Both exclusions and both controls, proved against one corpus in one assertion.

    Off, this same corpus returns all four (the test above). On, exactly the two
    admissible ones survive — so the flag is demonstrably the only thing that moved.
    """
    plan_id = 'pref-adm-mixed-on'
    _seed_mixed_corpus(plan_context, plan_id)

    result = cmd_query(_list_ns(plan_id, preference_admissible=True))

    assert _titles(result) == ['Reviewer claim', 'Unused import']
    assert result['filtered_count'] == 2
    assert result['total_count'] == 4
