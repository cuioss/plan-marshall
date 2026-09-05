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

import inspect
import json
from argparse import Namespace

import pytest
from _manage_findings_fixtures import (
    _add_ns,
    _qgate_add_ns,
    cmd_add,
    cmd_qgate_add,
    cmd_query,
    query_findings_unified,
)

#: The globals of the core module ``cmd_query`` actually dispatches into, reached
#: through a function the fixtures module already exports rather than by importing
#: the module again. The tests below patch the once-per-query registry resolver,
#: and a second import is not reliably the same module object: the surface modules
#: are registered through ``conftest.load_script_module``, so a plain ``import
#: _findings_core`` can bind a different instance than the one the query executes
#: in — a patch applied there would be invisible and the test would silently
#: assert the unpatched behaviour. A function's ``__globals__`` IS its module's
#: namespace, so patching here cannot miss.
_CORE_GLOBALS = query_findings_unified.__globals__

#: The two query surfaces, taken from that same namespace for the same reason.
_QUERY_FINDINGS = _CORE_GLOBALS['query_findings']
_QUERY_FINDINGS_UNIFIED = _CORE_GLOBALS['query_findings_unified']

#: The ``bot_registry`` module's OWN namespace, reached the same way — a function's
#: ``__globals__`` IS its module's namespace, and ``_registry_bot_kinds`` is that
#: module's ``bot_kinds``. Reaching it through the already-bound function rather
#: than through ``import bot_registry`` or ``sys.modules`` keeps the identity
#: argument above intact: this is provably the module object the lazy ``import
#: bot_registry`` inside ``recognized_bot_kinds`` resolves to, because it is the
#: one whose function ``_findings_core`` already holds. Patching ``bot_kinds``
#: HERE therefore drives the REAL ``recognized_bot_kinds`` derivation — which is
#: what the empty-registry controls below need, since patching
#: ``_recognized_bot_kinds`` itself would bypass the very derivation under test.
_REGISTRY_GLOBALS = _CORE_GLOBALS['_registry_bot_kinds'].__globals__

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'pref-adm-mixed-off',
    'pref-adm-mixed-on',
    'pref-adm-missing-bot-kind',
    'pref-adm-non-comment',
    'pref-adm-recognized-bot',
    'pref-adm-unrecognized-bot',
    'pref-adm-basis-recognized',
    'pref-adm-basis-degraded',
    'pref-adm-basis-flag-off',
    'pref-adm-basis-unified',
    'pref-adm-basis-degraded-self',
    'pref-adm-basis-unified-off',
    'pref-adm-basis-empty-registry',
    'pref-adm-basis-nonempty-registry',
)

#: The payload key carrying the two-state disclosure of WHICH authorship check
#: ran. Named once here so every assertion below reads the same key the payload
#: publishes.
BASIS_KEY = 'preference_admissibility_basis'

#: The realistic legacy value this module's negative control prefers. The registry
#: derives the recognized set from ``automatic-review/standards/{bot_kind}.md``, and
#: Sonar is a findings PRODUCER rather than a reviewer bot, so this value can reach
#: the store on a legacy, de-registered or hand-edited record but must never clear
#: the gate. It is a PREFERENCE, not the control itself — see below.
_LEGACY_PRODUCER_BOT_KIND = 'sonarcloud'

#: The recognized reviewer identity the shared corpus attributes its admissible
#: pr-comment to. Named once so the corpus and the registry-shape controls below
#: cannot drift onto two different values — a control that stocks the registry
#: with a bot_kind the corpus never seeded would assert nothing. It is a literal
#: rather than a derivation because ``cmd_add`` validates ``bot_kind`` against the
#: live registry: if this identity were ever de-registered the seeding itself
#: fails loudly, so the value cannot silently rot the way an unchecked one would.
_RECOGNIZED_REVIEWER_BOT_KIND = 'coderabbit'


def _derive_unrecognized_bot_kind():
    """Return a ``bot_kind`` derived to be absent from the LIVE recognized set.

    The control asserts a fact about the COMPLEMENT of the registry-derived reviewer
    set, so it is derived from that set rather than asserted against it: a hardcoded
    value stops being a control the moment the registry grows to contain it. The
    realistic legacy story is preferred (:data:`_LEGACY_PRODUCER_BOT_KIND`) and only
    mutated, deterministically, if the registry ever recognizes it. The resolver is
    the one ``_findings_core`` derives ``BOT_KINDS`` from, reached through that
    module's namespace so the control and the gate read one set.
    """
    recognized = frozenset(str(kind) for kind in _CORE_GLOBALS['_registry_bot_kinds']())
    candidate = _LEGACY_PRODUCER_BOT_KIND
    while candidate in recognized:
        candidate = f'{candidate}-deregistered'
    return candidate


#: A ``bot_kind`` value that is NOT a recognized reviewer identity, derived from the
#: live registry so it cannot silently stop being one.
UNRECOGNIZED_BOT_KIND = _derive_unrecognized_bot_kind()


def _list_ns(plan_id, *, preference_admissible=False, include_qgate=False):
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
        include_qgate=include_qgate,
        author=None,
        kind=None,
        bot_kind=None,
        preference_admissible=preference_admissible,
    )


def _titles(result):
    """The titles a query returned, sorted so the assertion is order-independent."""
    return sorted(finding['title'] for finding in result['findings'])


def _write_unrecognized_bot_comment(plan_context, plan_id, title):
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
        'hash_id': 'rawunrecog',
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
            bot_kind=_RECOGNIZED_REVIEWER_BOT_KIND,
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
    _write_unrecognized_bot_comment(plan_context, plan_id, 'Spurious claim')


#: The Q-Gate phase the slice below is seeded under. Any phase in ``QGATE_PHASES``
#: would do — the unified read merges pending records across every phase — so one
#: is named here rather than spread across the assertions.
_QGATE_PHASE = '5-execute'


def _seed_qgate_slice(plan_id):
    """File one inadmissible and one admissible finding into the Q-GATE slice.

    ``_seed_mixed_corpus`` stocks only the per-plan store, so a unified read over
    it exercises the Q-Gate narrowing against an EMPTY slice — the narrowing runs
    over nothing and every assertion downstream holds whether or not it ran at
    all. This seeds the other half so the Q-Gate slice is non-empty and its
    narrowing is observable in both directions.

    Both shapes are ones the ``qgate add`` verb actually produces. That bounds
    what the Q-Gate slice can demonstrate: ``add_qgate_finding`` accepts and
    persists no ``bot_kind``, so a bot-ATTRIBUTED Q-Gate pr-comment is not a
    record this system can write, and fabricating one would pin the gate to a
    shape it will never meet. The admissible member here is therefore a
    non-comment tool finding — the same admissible class the per-plan corpus
    carries — while the inadmissible member is the pr-comment-without-``bot_kind``
    shape that IS the threat the gate exists to stop.
    """
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=plan_id,
            phase=_QGATE_PHASE,
            type='pr-comment',
            title='Q-Gate pipeline note',
            detail='a Q-Gate pr-comment with no bot_kind: indistinguishable from pipeline traffic',
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=plan_id,
            phase=_QGATE_PHASE,
            type='lint-issue',
            title='Q-Gate lint finding',
            detail='tool output in the Q-Gate slice: no author, never pipeline chatter',
        )
    )


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
    _write_unrecognized_bot_comment(plan_context, plan_id, 'Spurious claim')

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


# =============================================================================
# Test: the degrade is real, and it is disclosed
# =============================================================================


class TestPreferenceAdmissibilityBasis:
    """The gate publishes WHICH of its two checks ran.

    The recognized reviewer set is re-derived from the live registry, and that
    derivation can fail. When it does, the rule degrades to a presence-only
    check rather than rejecting every bot-attributed comment — a rejection would
    hand preference learning a clean zero over a population it never read. The
    degrade is therefore kept, and made non-silent: the payload carries
    ``preference_admissibility_basis``.

    The registry is made unresolvable by patching ``_recognized_bot_kinds`` in
    ``_findings_core`` — the module-global the once-per-query resolver looks up —
    to return ``None``, which is exactly the value the real resolver returns on
    an import or parse failure. Patching the resolver rather than breaking the
    import keeps the fixture pinned to the contract's own ``None`` sentinel.
    """

    def test_basis_is_recognized_when_the_registry_resolves(self, plan_context):
        plan_id = 'pref-adm-basis-recognized'
        _seed_mixed_corpus(plan_context, plan_id)

        result = cmd_query(_list_ns(plan_id, preference_admissible=True))

        assert result[BASIS_KEY] == 'recognized'
        # POSITIVE CONTROL for the degrade test below: under the full check the
        # unrecognized `bot_kind` is excluded.
        assert _titles(result) == ['Reviewer claim', 'Unused import']

    def test_degraded_registry_reports_presence_only_and_admits_more(
        self, plan_context, monkeypatch
    ):
        # Both halves in one assertion set: the basis SAYS `presence_only`, and
        # the result set DEMONSTRATES it — the unrecognized-`bot_kind` comment,
        # excluded under the full check above, is now retained. Asserting the
        # label alone would pass against a build that relabelled without
        # degrading, and asserting the set alone would pass against a silent
        # degrade — which is the defect this field exists to close.
        plan_id = 'pref-adm-basis-degraded'
        _seed_mixed_corpus(plan_context, plan_id)
        monkeypatch.setitem(_CORE_GLOBALS, '_recognized_bot_kinds', lambda: None)

        result = cmd_query(_list_ns(plan_id, preference_admissible=True))

        assert result[BASIS_KEY] == 'presence_only'
        assert _titles(result) == ['Reviewer claim', 'Spurious claim', 'Unused import']

    def test_pipeline_authored_comment_stays_excluded_under_the_degrade(
        self, plan_context, monkeypatch
    ):
        # The threat the gate actually defends against is untouched by the
        # degrade: the pipeline's own posted comment carries an ABSENT
        # `bot_kind`, and the presence check runs before the registry check, so
        # it is excluded on BOTH paths. Without this the degrade could not be
        # kept at all.
        plan_id = 'pref-adm-basis-degraded-self'
        cmd_add(
            _add_ns(
                plan_id=plan_id,
                type='pr-comment',
                title='Pipeline note',
                detail='d',
                author='repo-owner-bot',
            )
        )
        monkeypatch.setitem(_CORE_GLOBALS, '_recognized_bot_kinds', lambda: None)

        result = cmd_query(_list_ns(plan_id, preference_admissible=True))

        assert result[BASIS_KEY] == 'presence_only'
        assert result['findings'] == []
        assert result['total_count'] == 1

    def test_basis_is_absent_when_the_flag_is_off(self, plan_context):
        # An absent key is UNDECLARED, never a default. Emitting a basis for a
        # gate that did not run would assert something about a check that never
        # happened — the same absence-read-as-measurement defect the field
        # exists to prevent.
        plan_id = 'pref-adm-basis-flag-off'
        _seed_mixed_corpus(plan_context, plan_id)

        result = cmd_query(_list_ns(plan_id))

        assert BASIS_KEY not in result

    def test_unified_read_reports_one_basis_for_both_slices(self, plan_context, monkeypatch):
        # `--include-qgate` narrows two slices. The registry is resolved ONCE for
        # the whole query, so the single basis the payload carries describes both
        # — two independent resolutions could disagree and leave the caller with
        # no way to tell which slice each applied to.
        #
        # That property needs THREE things observed, and the count assertion is
        # the load-bearing one: `qgate_included` is a literal constant in the
        # payload, and `basis == 'recognized'` is what per-slice resolution would
        # produce too, so neither can fail under the regression this test names.
        # Counting the resolver calls can: move the resolution back inside each
        # slice and the count becomes 2.
        plan_id = 'pref-adm-basis-unified'
        _seed_mixed_corpus(plan_context, plan_id)
        _seed_qgate_slice(plan_id)

        resolver_calls = []
        real_resolver = _CORE_GLOBALS['_recognized_bot_kinds']

        def _counting_resolver():
            resolver_calls.append(1)
            return real_resolver()

        monkeypatch.setitem(_CORE_GLOBALS, '_recognized_bot_kinds', _counting_resolver)

        result = cmd_query(_list_ns(plan_id, preference_admissible=True, include_qgate=True))

        assert result['qgate_included'] is True
        assert result[BASIS_KEY] == 'recognized'
        # ONE resolution for the whole query — the property the docstring names.
        assert len(resolver_calls) == 1
        # And both slices were demonstrably narrowed, in both directions: each
        # shed its inadmissible member and kept its admissible one. Without this
        # the count above could be satisfied by a query that resolved once and
        # then narrowed only half of what it returned.
        assert result['plan_count'] == 2
        assert result['qgate_count'] == 1
        assert _titles(result) == ['Q-Gate lint finding', 'Reviewer claim', 'Unused import']
        # `total_count` spans both slices UNNARROWED (4 per-plan + 2 Q-Gate), so
        # the two counts above are readable as narrowings rather than as totals.
        assert result['total_count'] == 6

    def test_unified_read_narrows_nothing_when_the_flag_is_off(self, plan_context):
        # The matched control for the assertion set above: the same two seeded
        # slices, flag OFF, return every member. It is what makes the counts above
        # attributable to the narrowing rather than to the seeding.
        plan_id = 'pref-adm-basis-unified-off'
        _seed_mixed_corpus(plan_context, plan_id)
        _seed_qgate_slice(plan_id)

        result = cmd_query(_list_ns(plan_id, include_qgate=True))

        assert result['plan_count'] == 4
        assert result['qgate_count'] == 2
        assert result['filtered_count'] == 6
        assert BASIS_KEY not in result


# =============================================================================
# Test: an empty derived registry is UNRESOLVED, not resolved-and-empty
# =============================================================================


class TestEmptyRegistryIsTreatedAsUnresolved:
    """An EMPTY derived reviewer set degrades, exactly as an unloadable one does.

    ``bot_registry`` reaches an empty set WITHOUT raising — its loader returns
    early when the standards dir is absent, and skips a doc it cannot read — so
    emptiness at this seam is a failure to resolve the population, never a
    population that was read and found empty. Handing the empty ``frozenset`` on
    would publish basis ``recognized`` while every bot-attributed pr-comment
    failed the membership test: the strong check reported over a population
    nothing ever read.

    Both tests below patch ``bot_kinds`` in the REGISTRY's own namespace rather
    than ``_recognized_bot_kinds`` in the core's. The sibling class above patches
    the latter because its subject is the consumer's handling of the ``None``
    sentinel; here the subject is the DERIVATION that decides whether to produce
    that sentinel at all, so patching it away would bypass the code under test.

    The two differ in exactly one input — an empty vs a non-empty registry — and
    the non-empty case is what stops the empty one from passing vacuously: the
    same patch seam must still yield the strong check when the registry has
    content, so the degrade is attributable to EMPTINESS and not to the patching.
    """

    def test_empty_registry_reports_presence_only_and_admits_present_bot_kinds(
        self, plan_context, monkeypatch
    ):
        plan_id = 'pref-adm-basis-empty-registry'
        _seed_mixed_corpus(plan_context, plan_id)
        monkeypatch.setitem(_REGISTRY_GLOBALS, 'bot_kinds', lambda: [])

        result = cmd_query(_list_ns(plan_id, preference_admissible=True))

        assert result[BASIS_KEY] == 'presence_only'
        # The degrade admits any PRESENT `bot_kind` — including 'Spurious claim',
        # the de-registered value the strong check excludes. 'Pipeline note' is
        # absent from this list because its `bot_kind` is ABSENT: the threat the
        # gate actually defends against stays excluded on the degraded path too.
        assert _titles(result) == ['Reviewer claim', 'Spurious claim', 'Unused import']

    def test_non_empty_registry_still_reports_recognized(self, plan_context, monkeypatch):
        plan_id = 'pref-adm-basis-nonempty-registry'
        _seed_mixed_corpus(plan_context, plan_id)
        monkeypatch.setitem(
            _REGISTRY_GLOBALS, 'bot_kinds', lambda: [_RECOGNIZED_REVIEWER_BOT_KIND]
        )

        result = cmd_query(_list_ns(plan_id, preference_admissible=True))

        assert result[BASIS_KEY] == 'recognized'
        # The strong check runs: the de-registered 'Spurious claim' is excluded.
        assert _titles(result) == ['Reviewer claim', 'Unused import']


# =============================================================================
# Test: the flag cannot bind positionally
# =============================================================================


class TestPreferenceAdmissibleIsKeywordOnly:
    """``preference_admissible`` is keyword-only on both query functions.

    Both are consumed across skills (``automatic-review``, ``phase-6-finalize``,
    ``workflow-integration-github`` / ``-gitlab`` / ``-sonar``), and the flag sits
    beside ``any_checkout`` — two adjacent booleans that a positional call could
    silently swap, turning a request to read another checkout into a request to
    narrow the result set. Keyword-only closes that off at the signature instead
    of leaving it to caller discipline, and ``any_checkout`` keeps the positional
    slot it held before the flag was added.
    """

    @pytest.mark.parametrize(
        'fn',
        [_QUERY_FINDINGS, _QUERY_FINDINGS_UNIFIED],
        ids=['query_findings', 'query_findings_unified'],
    )
    def test_flag_is_keyword_only_and_any_checkout_keeps_its_slot(self, fn):
        params = list(inspect.signature(fn).parameters.values())

        assert params[8].name == 'any_checkout'
        assert params[8].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert (
            inspect.signature(fn).parameters['preference_admissible'].kind
            is inspect.Parameter.KEYWORD_ONLY
        )

    @pytest.mark.parametrize(
        'fn',
        [_QUERY_FINDINGS, _QUERY_FINDINGS_UNIFIED],
        ids=['query_findings', 'query_findings_unified'],
    )
    def test_a_tenth_positional_argument_is_rejected(self, fn):
        # The binding hazard stated as behaviour, not just as a signature shape:
        # a caller that positionally supplies one argument past `any_checkout`
        # is refused outright rather than quietly enabling the narrowing.
        with pytest.raises(TypeError):
            fn('some-plan', None, None, None, None, None, None, None, False, True)
