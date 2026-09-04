#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every documented ``display_detail`` variant fits the ceiling once it expands.

``standards/pre-push-quality-gate.md`` documents one ``--display-detail`` string
per path that reaches Mark Step Complete. Each is a TEMPLATE, so the length that
matters is not the literal's — it is what the literal becomes once every
placeholder expands. A variant that fits as written and breaches at expansion
hands its author two jointly unsatisfiable instructions: compose this string,
and stay inside a ceiling it cannot stay inside.

**The variant population is DERIVED from the document**, not listed here: it is
every ``--display-detail "..."`` payload the gate document carries, with the
Branch B failure MENU split into its individual alternatives (that payload is a
brace-wrapped ``|``-separated choice, not one string an author emits whole).
Deriving it is what closes the class rather than the instance — a variant added
later is sized without editing this file, and a hand-written roster would keep
passing over the variants it still named. The derived size is published in every
failure message and in the session report header, so a derivation that silently
collapsed is visible on a GREEN run rather than only on a red one.

**Every bound is read from a document, never asserted here**: the ceiling from
``external-step-contract.md`` § "Required termination", and the count / truncated
-name budgets from the gate document's own § "Worst-case expansion, defined". A
budget restated in this file could report a healthy number for a rule the
document no longer states.

What the sweeps assert, per derived variant:

* **Ceiling** — the worst-case expansion is within the documented ceiling.
* **Budget completeness** — every placeholder the variant interpolates falls in
  one of the three declared classes. An unclassified placeholder FAILS rather
  than expanding to nothing, because a placeholder nobody budgeted is exactly
  the unmeasured variant this module exists to prevent.
* **No unexpanded construct** — nothing brace-shaped survives expansion, so a
  placeholder whose spelling the identifier pattern cannot match is caught
  rather than silently treated as zero-width.

Each detector is paired with a mutation guard that runs it against a synthetic
breaching shape, so a detector typo fails here instead of making the sweep
vacuously green.
"""

from __future__ import annotations

import re

import pytest

from conftest import MARKETPLACE_ROOT

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_GATE_DOC = _SKILL_DIR / 'standards' / 'pre-push-quality-gate.md'
_CONTRACT_DOC = _SKILL_DIR / 'standards' / 'external-step-contract.md'

#: A documented variant, as the gate document writes one. Anchored on the flag
#: rather than on a fence, so a variant moved between a ``bash`` and a ``text``
#: block stays in the population. Prose that merely discusses ``display_detail``
#: carries no ``--display-detail "`` and is therefore not a variant.
_DISPLAY_DETAIL = re.compile(r'--display-detail\s+"([^"]*)"')

#: A placeholder, restricted to a bare identifier. The Branch B payload wraps
#: its alternatives in an outer brace pair that is NOT a placeholder, and this
#: pattern must not consume it.
_IDENTIFIER_PLACEHOLDER = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')

#: What separates the alternatives inside the Branch B failure menu.
_ALTERNATION_SEPARATOR = ' | '

_CEILING_RE = re.compile(r'≤\s*(\d+)\s*characters')
_COUNT_BUDGET_RE = re.compile(r'expands to at most (\d+) digits')
_TRUNCATION_RE = re.compile(r'truncated to at most (\d+) characters')


def _sole_int(pattern: re.Pattern[str], text: str, label: str, source: str) -> int:
    """Return the one integer ``pattern`` finds in ``text``, or fail loudly.

    Sole-match rather than first-match: a second occurrence means the bound is
    stated twice and the two could disagree, and a zero-match means the document
    no longer states it at all. Either way a first-match read would carry on with
    a number nothing backs.
    """
    matches = pattern.findall(text)
    assert len(matches) == 1, (
        f'{label} must be stated exactly once in {source} for this sweep to '
        f'derive it; found {len(matches)} occurrence(s) of {pattern.pattern!r}'
    )
    return int(matches[0])


_GATE_TEXT: str = _GATE_DOC.read_text(encoding='utf-8')
_CONTRACT_TEXT: str = _CONTRACT_DOC.read_text(encoding='utf-8')

#: The ceiling every ``display_detail`` obeys, owned by the external-step
#: contract and read from it rather than restated.
CEILING = _sole_int(
    _CEILING_RE, _CONTRACT_TEXT, 'The display_detail character ceiling', _CONTRACT_DOC.name
)

#: The two placeholder budgets the gate document declares for its own variants.
COUNT_BUDGET = _sole_int(
    _COUNT_BUDGET_RE, _GATE_TEXT, 'The count-placeholder digit budget', _GATE_DOC.name
)
TRUNCATED_NAME_BUDGET = _sole_int(
    _TRUNCATION_RE, _GATE_TEXT, 'The truncated-name width', _GATE_DOC.name
)

#: The width a SINGLE untruncated module name can reach, derived from the real
#: bundle set rather than assumed. Branch B interpolates one such name per
#: alternative; the gate document permits that because one name is bounded in a
#: way a SET of names is not, and this is the bound.
LONGEST_MODULE_NAME = max(
    (len(path.name) for path in MARKETPLACE_ROOT.iterdir() if path.is_dir()), default=0
)

#: Placeholder classification. The WIDTHS above are derived from the documents;
#: what lives here is only which class each placeholder belongs to, and its
#: completeness is derived — a placeholder in no class fails the sweep below
#: rather than expanding to nothing.
_COUNT_PLACEHOLDERS = frozenset({'N', 'G', 'S', 'K'})
_TRUNCATED_NAME_PLACEHOLDERS = frozenset({'B'})
_SINGLE_NAME_PLACEHOLDERS = frozenset({'bundle', 'recommended_target'})


def _budget(name: str) -> int | None:
    """Return the worst-case width of placeholder ``name``, or ``None`` if unbudgeted."""
    if name in _COUNT_PLACEHOLDERS:
        return COUNT_BUDGET
    if name in _TRUNCATED_NAME_PLACEHOLDERS:
        return TRUNCATED_NAME_BUDGET
    if name in _SINGLE_NAME_PLACEHOLDERS:
        return LONGEST_MODULE_NAME
    return None


def _expand(variant: str) -> tuple[str, list[str]]:
    """Return ``(worst_case_expansion, unbudgeted_placeholder_names)``.

    An unbudgeted placeholder is left in place rather than dropped, so it cannot
    quietly shorten the string it should have failed.
    """
    unbudgeted: list[str] = []

    def _substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        width = _budget(name)
        if width is None:
            unbudgeted.append(name)
            return match.group(0)
        return 'X' * width

    return _IDENTIFIER_PLACEHOLDER.sub(_substitute, variant), unbudgeted


def _alternatives(payload: str) -> list[str]:
    """Split a brace-wrapped ``|``-menu into its alternatives; pass others through.

    Branch B's payload is a CHOICE of five failure strings, never one string an
    author emits whole, so measuring it unsplit would report a breach the
    document does not have. Splitting is therefore load-bearing rather than a way
    to dodge the ceiling — each alternative is measured on its own.
    """
    if (
        payload.startswith('{')
        and payload.endswith('}')
        and _ALTERNATION_SEPARATOR in payload
    ):
        return [alt.strip() for alt in payload[1:-1].split(_ALTERNATION_SEPARATOR)]
    return [payload]


_PAYLOADS: list[str] = _DISPLAY_DETAIL.findall(_GATE_TEXT)
_VARIANTS: list[str] = [alt for payload in _PAYLOADS for alt in _alternatives(payload)]

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it — an empty
# parametrize is a pytest SKIP, not a failure, so a derivation that matched
# nothing would report a clean sweep over nothing.
assert _VARIANTS, (
    f'No --display-detail variant was derived from {_GATE_DOC.name} — the ceiling '
    f'sweep would pass over an empty set'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: population; publishing the size is what makes a SHRUNKEN one visible on the
#: green run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'pre-push-quality-gate display_detail variants'
GUARD_POPULATION_SIZE = len(_VARIANTS)

_VARIANT_IDS = [
    f'{index}-' + (re.sub(r'[^A-Za-z0-9]+', '-', variant).strip('-').lower()[:40] or 'empty')
    for index, variant in enumerate(_VARIANTS)
]


# ---------------------------------------------------------------------------
# The derived bounds are real
# ---------------------------------------------------------------------------


def test_every_derived_bound_is_positive():
    """A bound of zero would silently pass every variant it is supposed to size."""
    assert CEILING > 0, f'The ceiling derived from {_CONTRACT_DOC.name} is not positive'
    assert COUNT_BUDGET > 0, 'The count-placeholder digit budget is not positive'
    assert TRUNCATED_NAME_BUDGET > 0, 'The truncated-name width is not positive'
    assert LONGEST_MODULE_NAME > 0, (
        f'No bundle directory was found under {MARKETPLACE_ROOT}, so the '
        f'single-name budget is zero and Branch B is measured against nothing'
    )


# ---------------------------------------------------------------------------
# Per-variant sweeps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('variant', _VARIANTS, ids=_VARIANT_IDS)
def test_every_placeholder_carries_a_size_budget(variant):
    _expanded, unbudgeted = _expand(variant)

    assert not unbudgeted, (
        f'Variant {variant!r} interpolates placeholder(s) {sorted(set(unbudgeted))} '
        f'that belong to no declared size class, so the variant ships unmeasured '
        f'against the {CEILING}-character ceiling. Classify it as a count, a '
        f'truncated name, or a single name — or, if it stands for a SET, it is '
        f'inadmissible in a display_detail (population: {len(_VARIANTS)} variant(s))'
    )


@pytest.mark.parametrize('variant', _VARIANTS, ids=_VARIANT_IDS)
def test_no_variant_leaves_an_unexpanded_brace_construct(variant):
    """A brace construct the identifier pattern cannot match must not pass as zero-width."""
    residue = _IDENTIFIER_PLACEHOLDER.sub('', variant)

    assert '{' not in residue and '}' not in residue, (
        f'Variant {variant!r} carries a brace construct that is not a bare '
        f'identifier placeholder, so its width is unknown and the expansion below '
        f'would measure it as nothing (population: {len(_VARIANTS)} variant(s))'
    )


@pytest.mark.parametrize('variant', _VARIANTS, ids=_VARIANT_IDS)
def test_every_variant_fits_the_ceiling_at_worst_case_expansion(variant):
    expanded, _unbudgeted = _expand(variant)

    assert len(expanded) <= CEILING, (
        f'Variant {variant!r} expands to {len(expanded)} characters at its worst '
        f'case, over the {CEILING}-character ceiling. Worst case is the measure '
        f'that matters: the literal is {len(variant)} characters, which is why a '
        f'variant that "fits as written" can still be impossible to compose. '
        f'Expanded: {expanded!r} (population: {len(_VARIANTS)} variant(s))'
    )


# ---------------------------------------------------------------------------
# Mutation guards — each detector must fail on the shape it exists to catch
# ---------------------------------------------------------------------------


def test_payload_detector_fires_on_a_call_and_not_on_prose():
    call = '  --display-detail "{N} bundles green, whole-tree gates green" \\'
    prose = (
        'The same discipline governs this step\'s own display_detail: see the '
        'degraded detail variant under Mark Step Complete below.'
    )

    assert _DISPLAY_DETAIL.findall(call), (
        'The payload detector did not fire on a real --display-detail call, so '
        'the derived population would be empty and every sweep vacuous'
    )
    assert not _DISPLAY_DETAIL.findall(prose), (
        'The payload detector fires on PROSE that merely names display_detail, so '
        'sentences would be measured as if they were variants'
    )


def test_ceiling_detector_rejects_an_oversized_worst_case():
    """A variant that fits as a literal but breaches on expansion must be caught."""
    assert TRUNCATED_NAME_BUDGET > len('{B}'), (
        'Fixture drift: a truncated-name budget no wider than its own placeholder '
        'cannot lengthen a string, so this guard cannot construct a breaching case'
    )
    prefix = '{B} skipped: '
    oversized = prefix + 'x' * (CEILING - len(prefix) - 1)
    expanded, unbudgeted = _expand(oversized)

    assert not unbudgeted, 'Fixture drift: the synthetic variant must be fully budgeted'
    assert len(oversized) < CEILING, (
        'Fixture drift: the synthetic variant must FIT as a literal, or it does '
        'not exercise the literal-versus-expansion distinction at all'
    )
    assert len(expanded) > CEILING, (
        'The ceiling detector accepted a variant whose worst-case expansion '
        'breaches, so the per-variant sweep would be vacuously green'
    )


def test_budget_completeness_detector_fires_on_an_unbudgeted_placeholder():
    _expanded, unbudgeted = _expand('{G} bundles green, {skipped_bundle_list} skipped')

    assert unbudgeted == ['skipped_bundle_list'], (
        f'The budget-completeness detector did not report an unclassified '
        f'placeholder, so a new variant could ship unmeasured. Reported: {unbudgeted}'
    )


def test_brace_residue_detector_fires_on_a_non_identifier_construct():
    residue = _IDENTIFIER_PLACEHOLDER.sub('', '{G} bundles, {each skipped bundle}')

    assert '{' in residue, (
        'The brace-residue detector treated a non-identifier construct as an '
        'expanded placeholder, so an unmeasurable interpolation would pass'
    )


def test_alternation_splitter_is_load_bearing_for_the_failure_menu():
    """The menu breaches unsplit and fits per alternative — so the split is required."""
    menu = (
        '{quality-gate failed for {bundle} | whole-tree quality-gate red | '
        'test-compile red}'
    )

    unsplit, _unbudgeted = _expand(menu)
    assert len(unsplit) > CEILING, (
        'Fixture drift: the synthetic menu no longer breaches when measured '
        'whole, so it does not exercise why splitting is necessary'
    )

    alternatives = _alternatives(menu)
    assert len(alternatives) == 3, (
        f'The alternation splitter did not separate the menu into its individual '
        f'alternatives; got {alternatives}'
    )
    for alternative in alternatives:
        expanded, _unbudgeted = _expand(alternative)
        assert len(expanded) <= CEILING, (
            f'Alternative {alternative!r} expands to {len(expanded)} characters, '
            f'over the {CEILING}-character ceiling'
        )


def test_alternation_splitter_leaves_an_ordinary_variant_whole():
    variant = '{N} bundles + whole-tree gates green, module-tests skipped (no module)'

    assert _alternatives(variant) == [variant], (
        'The alternation splitter altered an ordinary single-string variant, so '
        'the population would be measured in fragments rather than as authored'
    )
