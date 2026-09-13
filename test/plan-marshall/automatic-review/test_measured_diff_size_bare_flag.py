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


# =============================================================================
# 3 — the documented call sites, transported as the executor transports them
# =============================================================================

#: The KNOWN call sites — the FIND step's participation guard and the pre-merge
#: review-completeness barrier — held as repo-relative paths under :data:`_SKILLS`.
#:
#: ⛔ This is a FLOOR, not the scan population. The population is DERIVED from the
#: bundle tree by :func:`_scan_docs` below, because a hand-named list answers only
#: "did a doc we already knew about stop matching?" and is blind in the other
#: direction: a `check` call added to a THIRD document would sit outside the sweep
#: with nothing reporting the omission. That blindness is not hypothetical —
#: `phase-6-finalize/workflow/create-pr.md` already carries a concrete
#: `review_completeness` invocation (its `size-caps` advance disclosure), so the set
#: of documents invoking this script is demonstrably larger than this pair and
#: demonstrably growing.
#:
#: Deriving the population while KEEPING this floor preserves both directions: the
#: derivation catches a new call site, and the floor assertion below still names a
#: known site that silently stopped matching — which a derived-only population
#: cannot see, since its members are by construction exactly the docs that matched.
_KNOWN_CALL_SITE_DOCS: tuple[str, ...] = (
    'automatic-review/SKILL.md',
    'phase-6-finalize/standards/branch-cleanup.md',
)

_EXEC_CALL = re.compile(r'python3\s+\.plan/execute-script\.py\s+plan-marshall:automatic-review:review_completeness\b')

#: Argparse's own rendering of an optional flag. A block carrying it is the
#: `## Canonical invocations` SPECIFICATION of the surface, not a call, so
#: substituting it would test the substitution rather than the doc.
_ADVERTISED_FORM = re.compile(r'[\[(]\s*-{1,2}[a-zA-Z]')

#: Placeholder values that keep an invocation parseable. Everything else — every
#: bot list, and `{measured_diff_size}` itself — collapses to the empty string,
#: which is what the common path genuinely produces.
_SUBSTITUTIONS = {'plan_id': 'mds-parse-probe'}
_PLACEHOLDER = re.compile(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}')


def _fenced_commands(text: str) -> list[str]:
    """Every fenced code block, with backslash continuations folded to one line."""
    blocks: list[str] = []
    in_fence = False
    current: list[str] = []
    for raw in text.splitlines():
        if raw.lstrip().startswith('```'):
            if in_fence:
                blocks.append(re.sub(r'\\\n\s*', ' ', '\n'.join(current)))
                current = []
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(raw)
    return blocks


def _executor_argv(command: str) -> list[str]:
    """The argv the GENERATED EXECUTOR hands the script for a documented call.

    Two transport steps, in this order, and the second is the one the sibling D3
    sweep omits:

    1. placeholder substitution — an unmeasured size interpolates as empty;
    2. the executor's empty-argument strip (``script_args = [a for a in
       script_args if a]`` in ``.plan/execute-script.py``), which DROPS that empty
       token rather than passing it through as a value.

    The leading ``python3`` / executor path / notation tokens are dropped, leaving
    the verb and its arguments. A block documenting more than one call is cut at the
    next ``python3``, so a following invocation's tokens are never read as this
    call's arguments.

    Returns ``[]`` for a block this module cannot read as a runnable invocation —
    one whose quoting ``shlex`` rejects, or whose notation survives the regex but not
    the split (``…:review_completeness.py`` matches ``\\b`` yet is a different token).
    Both are real boundaries now that the population is the whole bundle tree rather
    than two curated documents: unguarded, either raises at IMPORT and takes every
    test in this module down as a collection error. The caller already treats ``[]``
    as "not a `check` call", so neither can be mistaken for one.
    """
    substituted = _PLACEHOLDER.sub(lambda m: _SUBSTITUTIONS.get(m.group(0)[1:-1], ''), command)
    try:
        tokens = [token for token in shlex.split(substituted) if token]
    except ValueError:
        return []
    notation = 'plan-marshall:automatic-review:review_completeness'
    if notation not in tokens:
        return []
    tail = tokens[tokens.index(notation) + 1 :]
    return tail[: tail.index('python3')] if 'python3' in tail else tail


def _scan_docs() -> list:
    """Every Markdown document under ``_SKILLS``, in deterministic path order.

    The population the sweep runs over is the bundle tree itself, not a list kept by
    hand — the repository convention that a set-guarding detector derives its
    population from the authoritative source rather than restating it, applied to the
    one seam this module previously restated.
    """
    return sorted(_SKILLS.rglob('*.md'))


def _documented_check_invocations() -> tuple[list[tuple[str, list[str]]], list[tuple[str, str]]]:
    """The scanned `check` calls, AND the documents the scan could not read.

    Returns `(found, unreadable)`:

    - `found` — `(relative_doc_path, executor_argv)` per concrete documented `check`
      call. Keyed on the repo-relative path rather than the basename: the scan spans
      the whole bundle tree, where `SKILL.md` is not unique, and a basename key would
      silently merge two documents into one parametrize id and one floor-test member.
    - `unreadable` — `(relative_doc_path, reason)` per document whose read raised.

    ⛔ An unreadable document is REPORTED, never skipped. Dropping it would shrink
    this derived population by exactly the documents nothing looked at: a non-floor
    doc carrying a `check` call would leave the sweep with every downstream
    assertion — the import-time non-emptiness, the non-vacuity probe, the
    parametrized sweep itself — still green, because each is computed over the
    already-shrunken `found`. The floor does not rescue it either; the floor names
    two KNOWN docs, and the case that matters here is the doc nobody named. `found`
    stays the sweep's population and `unreadable` is asserted empty separately, so a
    read failure surfaces as its own named test failure rather than a collection
    error that takes the parser-contract tests down with it.
    """
    found: list[tuple[str, list[str]]] = []
    unreadable: list[tuple[str, str]] = []
    for doc in _scan_docs():
        try:
            text = doc.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append((doc.relative_to(_SKILLS).as_posix(), f'{type(exc).__name__}: {exc}'))
            continue
        if not _EXEC_CALL.search(text):
            continue
        for block in _fenced_commands(text):
            if not _EXEC_CALL.search(block) or _ADVERTISED_FORM.search(block):
                continue
            argv = _executor_argv(block)
            if argv and argv[0] == 'check':
                found.append((doc.relative_to(_SKILLS).as_posix(), argv))
    return found, unreadable


SCANNED_DOC_COUNT = len(_scan_docs())
_DOCUMENTED, _UNREADABLE = _documented_check_invocations()

# Non-emptiness at IMPORT: an empty parametrize is a pytest SKIP, not a failure, so
# a scan that matched nothing would report a clean sweep over nothing. The scanned
# count and the unreadable count ride along so an empty result names WHICH of the
# three zeros it is — a misrooted scan that read nothing, a tree whose documents
# could not be read at all, or a real tree that documents no `check` call.
assert _DOCUMENTED, (
    'no concrete `review_completeness check` invocation was scanned from the '
    f'{SCANNED_DOC_COUNT} markdown documents under {_SKILLS} '
    f'({len(_UNREADABLE)} of them unreadable) — the sweep below would pass over an empty set'
)

#: Published on every run — passing included — by the root conftest's report header.
GUARD_POPULATION_LABEL = 'documented review_completeness check invocations'
GUARD_POPULATION_SIZE = len(_DOCUMENTED)


def _invocation_id(item: tuple[str, list[str]]) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '-', item[0]).strip('-').lower()


def test_no_scanned_document_was_unreadable():
    """COVERAGE: a document the scan could not READ is a gap, never an absence.

    The sweep's whole value is that its population is the bundle tree rather than a
    hand-kept list, so a document silently leaving that population is the one failure
    the derivation cannot absorb: an unreadable doc may carry a `review_completeness
    check` call, and nothing looked.

    Neither sibling guard sees it. `_KNOWN_CALL_SITE_DOCS` names two KNOWN docs and is
    blind to any other; and `test_the_scan_population_is_larger_than_the_known_floor`
    reads `SCANNED_DOC_COUNT`, which counts PATHS from `_scan_docs` without opening
    one — so an unreadable document is counted as scanned there while contributing
    nothing here. Every remaining assertion in this module is computed over the
    already-shrunken `_DOCUMENTED` and would stay green.

    The paths and their reasons are named, because "some document was unreadable" is
    not something a reader can act on.
    """
    assert not _UNREADABLE, (
        f'{len(_UNREADABLE)} of the {SCANNED_DOC_COUNT} documents under {_SKILLS} could not be '
        f'read, so they never entered the derived population of {len(_DOCUMENTED)} `check` '
        'invocations. An unreadable document is a hole in the sweep, not a document without a '
        f'`check` call:\n  ' + '\n  '.join(f'{path} ({reason})' for path, reason in _UNREADABLE)
    )


def test_the_scan_population_is_larger_than_the_known_floor():
    """The sweep really scans the tree, not just the two docs named in the floor.

    Without this, every assertion below would still pass if :func:`_scan_docs`
    silently degenerated to the floor — the exact hard-coded population this
    derivation replaced, restored without anything reporting it.
    """
    assert SCANNED_DOC_COUNT > len(_KNOWN_CALL_SITE_DOCS), (
        f'the scan read {SCANNED_DOC_COUNT} document(s) under {_SKILLS}, which is not more '
        f'than the {len(_KNOWN_CALL_SITE_DOCS)} floor entries — the derivation is not reading '
        'the bundle tree'
    )


def test_every_known_call_site_doc_contributes_an_invocation():
    """Each KNOWN doc yields at least one call — a doc that stopped matching is named.

    This is the direction the derived population cannot see. Its members are exactly
    the docs that matched, so a known site dropping out shrinks the population
    silently; only a floor asserted against it reports the loss. A total-only check
    cannot see it either — the other docs keep the total non-zero.
    """
    matched = {relative_path for relative_path, _argv in _DOCUMENTED}
    silent = sorted(set(_KNOWN_CALL_SITE_DOCS) - matched)

    assert not silent, (
        f'{silent} contributed ZERO concrete `review_completeness check` invocations to a '
        f'derived population of {len(_DOCUMENTED)} (scanned {SCANNED_DOC_COUNT} documents). '
        'The matcher stopped seeing that doc, so its call site is no longer covered by the '
        'sweep below.'
    )


def test_the_strip_actually_produces_a_bare_flag():
    """NON-VACUITY: the transport step under test genuinely fires on a real doc.

    This is what stops the sweep below from being a tautology. If a doc were changed
    to interpolate `--measured-diff-size` conditionally — or to drop it — every
    invocation would parse trivially and the sweep would go green while proving
    nothing about the bare form. The assertion names the condition the sweep's value
    rests on, rather than leaving it to be inferred from a passing run.
    """
    bare_sites = [
        f'{name}: {argv}'
        for name, argv in _DOCUMENTED
        if _FLAG in argv and (argv.index(_FLAG) == len(argv) - 1 or argv[argv.index(_FLAG) + 1].startswith('-'))
    ]

    assert bare_sites, (
        f'no documented call site delivered a BARE {_FLAG} after the executor strip, over a '
        f'population of {len(_DOCUMENTED)}. Either the docs no longer interpolate it '
        'unconditionally, or the strip model above stopped matching — in both cases the sweep '
        'below no longer exercises the rejection this module exists to pin.'
    )


@pytest.mark.parametrize('invocation', _DOCUMENTED, ids=_invocation_id)
def test_documented_invocation_parses_after_the_executor_strip(invocation):
    """The documented call, transported as the executor transports it, parses.

    A `SystemExit` here is the live defect: the doc prescribes a call that a leaf
    quoting it verbatim cannot run, and the rejection routes to an UNKNOWN verdict
    the run has no sanctioned way out of.
    """
    doc_name, argv = invocation

    try:
        parsed = parse_ns(*_SCRIPT, *argv, register=False)
    except SystemExit as exit_code:
        pytest.fail(
            f'{doc_name}: the documented `review_completeness check` call is an argparse '
            f'rejection (exit {exit_code.code}) once the executor strips its empty arguments.\n'
            f'  executor argv: {argv}\n'
            'This is the COMMON path — no size refusal means no measured diff size — and the '
            'rejection routes to the UNKNOWN verdict, whose force-done hatch is unavailable.'
        )

    assert parsed.measured_diff_size == '', (
        f'{doc_name}: the stripped call parsed, but the unmeasured diff size did not read as '
        f'unmeasured (got {parsed.measured_diff_size!r}). An unmeasured size must never be '
        'reported as a measured one.'
    )
