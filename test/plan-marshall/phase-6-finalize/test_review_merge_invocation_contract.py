#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Population-derived contract over the finalize merge-and-review script invocations.

Two invariants, each derived from the tree at run time rather than a curated list of
call sites — a curated list is the artifact this plan exists to retire:

* **D0 — the exit-code convention covers every invoked script.** The observed
  swallowed-rejection failures reached ``github_pr``, ``review_completeness`` and
  ``ci`` — none of which is ``manage-*`` — yet the merge-and-review docs carried an
  exit-code convention scoped to ``manage-*`` only, so a non-zero exit from exactly
  those three fell outside the rule and could be read as an empty-but-clean result.
  This suite derives the NON-``manage-*`` invocation population from the merge-and-review
  docs and fails unless each doc's exit-code convention is widened past ``manage-*``.

* **D2 — the widening reaches the whole pool, and the convention disposes of the exit-0
  non-``success`` return.** Keying the convention on the exit code alone left a second hole
  behind the first: ``ci_base.output_error`` prints ``status: error`` and returns exit 0, and
  both provider ``main()`` functions return 0 without branching on the result's ``status``, so
  a FAILED call satisfies an exit-code-only ``exit_code == 0`` clause. Two sweeps close it,
  both derived from the tree: every doc under the two skills that invokes a non-``manage-*``
  script must carry the widened convention (so a NEW such doc fails on arrival, which the
  curated doc tuple above cannot catch), and every such convention must state the
  exit-0-non-``success`` disposition. A third sweep ties each derived ``ci`` call site to one
  of the two discharge arms — the doc-level clause or a call-site positive shape requirement.

* **D3 — every documented review-and-merge invocation parses against its own parser.**
  A workflow doc that prescribes a flag on a parser which does not DECLARE it — the
  observed case is ``--enabled-bots`` written onto a ``github_pr fetch_findings`` call —
  or a flag in a position the parser rejects (``--plan-id`` after a router verb), makes
  a dispatched leaf that quotes the doc verbatim fail with an argparse rejection
  (exit 2). The mismatch is PER-PARSER, never global: ``--enabled-bots`` is a real,
  legitimately declared flag on ``review_gate_delta assess``, so what is wrong is the
  PAIRING of flag and script and not the flag itself — a guard phrased as "a flag no
  script declares" would be false of this tree and would go looking for the wrong thing.
  This suite derives the documented invocation population from the docs, substitutes the
  placeholders, runs each against its REAL parser, and fails on any argparse rejection —
  so an ``--enabled-bots`` reintroduced onto a parser that does not declare it fails
  here, where it previously only failed a dispatched agent at merge time.

Both populations are asserted NON-EMPTY before anything is swept over them (an empty
parametrize is a pytest SKIP, not a failure) and publish their size in the failure
message, so a scan that silently matched nothing fails loudly rather than reporting a
healthy sweep over an empty set. The derivation follows the runtime-derived /
non-empty-first / size-published DISCIPLINE the plan points at in ``_dispatch_roster``;
it reimplements a fenced-block walk locally rather than reusing that module's
heading-bounded LIST-roster walk (``_dispatch_roster`` parses ``- `key` `` list rows,
a different shape from a fenced code block).

Scope, stated honestly. "The finalize merge-and-review path" is a SEMANTIC scope with
no machine-readable manifest, so the doc SET below (the barrier, the FIND/participation
step, and the dispatcher that orchestrates them) is named from the plan's own scope
definition. What is DERIVED — never hand-listed — is (a) WHERE each script is invoked
within those docs, and (b) each doc's widening OBLIGATION, read off its own non-manage-*
invocations rather than asserted. D3's runnable surface is the three participation verbs
the plan names (``fetch_findings`` / ``review_completeness check`` / ``ci checks
pull-request-runs``); the re-review / completion-poll / CI-wait verbs are excluded
because their choice-constrained and value-required flags have no doc-derivable valid
value, so a placeholder-substituted parse would test the substitution, not the doc. A
bad flag reintroduced on one of those excluded verbs is therefore outside this sweep —
an accepted narrowing, recorded here rather than hidden.
"""

from __future__ import annotations

import re
import shlex

import pytest

from conftest import MARKETPLACE_ROOT, get_script_path, run_script

# =============================================================================
# The finalize merge-and-review docs — the population source
# =============================================================================
#
# These two documents carry the review-and-merge DECISION invocations: the
# pre-merge barrier (branch-cleanup.md) and the FIND + participation guard
# (automatic-review/SKILL.md). The dispatcher SKILL.md orchestrates them and
# carries the same exit-code convention, so it is included in the convention-scope
# check but not scanned for invocations (its own calls are the dispatcher's, not the
# barrier's).

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_BARRIER_DOC = _SKILLS / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
_REVIEW_DOC = _SKILLS / 'automatic-review' / 'SKILL.md'
_DISPATCHER_DOC = _SKILLS / 'phase-6-finalize' / 'SKILL.md'
#: The rebased-HEAD re-review walkthrough. It invokes `github_re_review re-review` and
#: `github_pr fetch_findings` — neither `manage-*` — and is reached from the barrier's own
#: flow, so it belongs in both populations below.
_REREVIEW_DOC = _SKILLS / 'phase-6-finalize' / 'standards' / 'branch-cleanup-rereview.md'

#: The docs scanned for the invocation population.
_INVOCATION_DOCS = (_BARRIER_DOC, _REVIEW_DOC, _REREVIEW_DOC)
#: The docs whose exit-code convention must be widened past manage-*.
_CONVENTION_DOCS = (_BARRIER_DOC, _REVIEW_DOC, _DISPATCHER_DOC, _REREVIEW_DOC)

#: The whole finalize doc pool the widening sweep walks. The merge-and-review doc SET above
#: is a semantic scope; THIS is the mechanical one — every markdown file under the two
#: skills — so a doc added later is swept without anyone remembering to list it.
_POOL_ROOTS = (_SKILLS / 'phase-6-finalize', _SKILLS / 'automatic-review')

#: A canonical `bundle:skill:script` executor notation.
_NOTATION = re.compile(r'\bplan-marshall:[a-z0-9-]+:[a-z0-9_-]+\b')
#: An `execute-script.py` invocation opening (up to and including the notation).
_EXEC_CALL = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+(?P<notation>plan-marshall:[a-z0-9-]+:[a-z0-9_-]+)'
)

#: The review-and-merge participation SURFACE D3 parses: the three (script, verb)
#: pairs the plan names — the producer FIND (`github_pr fetch_findings`), the
#: participation predicate (`review_completeness check`), and the PR-wide
#: `not_triggered` read (`ci checks pull-request-runs`). This is a definition of the
#: SURFACE, not a list of call sites — WHERE each is invoked is still derived from
#: the docs. It is deliberately narrower than "every runnable call": the re-review /
#: completion-poll / CI-wait verbs (`bot_completion`, `re-review`,
#: `pr wait-for-comments`) carry choice-constrained or value-required flags whose
#: valid values are not derivable from the doc text, so a placeholder-substituted
#: parse of them tests the substitution, not the doc. The plan's flag/script mismatch
#: lives entirely on the three surface verbs below.
def _is_review_merge_surface(command: str) -> bool:
    """True for a concrete invocation of one of the three review-and-merge surface verbs."""
    if 'automatic-review:review_completeness' in command and re.search(r'\bcheck\b', command):
        return True
    if 'workflow-integration-github:github_pr' in command and 'fetch_findings' in command:
        return True
    if 'tools-integration-ci:ci' in command and 'pull-request-runs' in command:
        return True
    return False

#: Placeholder substitutions that keep an invocation PARSEABLE. A bot-list value's
#: shape is irrelevant to argparse (the malformed-value rejection is a post-parse
#: caller error, exit 1, not an argparse rejection, exit 2), so an unknown placeholder
#: collapses to the empty string — the empty-list form every list flag accepts.
_SUBSTITUTIONS = {
    'plan_id': 'rmi-parse-probe',
    'pr_number': '1',
    'worktree_path': '.',
}
_PLACEHOLDER = re.compile(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}')


def _fenced_commands(doc_text: str) -> list[str]:
    """Return every fenced code block, backslash-continuations folded to one line each."""
    blocks: list[str] = []
    in_fence = False
    current: list[str] = []
    for raw in doc_text.splitlines():
        if raw.lstrip().startswith('```'):
            if in_fence:
                blocks.append(re.sub(r'\\\n\s*', ' ', '\n'.join(current)))
                current = []
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(raw)
    return blocks


def _invoked_notations(doc_text: str) -> set[str]:
    """Every distinct executor notation invoked in a doc's fenced blocks."""
    notations: set[str] = set()
    for block in _fenced_commands(doc_text):
        for match in _EXEC_CALL.finditer(block):
            notations.add(match.group('notation'))
    return notations


def _is_manage_star(notation: str) -> bool:
    """True when the notation's skill segment is a manage-* skill."""
    _bundle, skill, _script = notation.split(':')
    return skill.startswith('manage-')


def _script_path_for(notation: str):
    """Resolve a `bundle:skill:script` notation to its script file path."""
    bundle, skill, script = notation.split(':')
    return get_script_path(bundle, skill, f'{script}.py')


def _substitute(command: str) -> str:
    """Replace every `{placeholder}` with a parseable value (unknowns -> empty)."""
    return _PLACEHOLDER.sub(lambda m: _SUBSTITUTIONS.get(m.group(0)[1:-1], ''), command)


def _documented_invocations() -> list[tuple[str, str, str]]:
    """Return `(doc_name, notation, command)` for every RUNNABLE documented invocation.

    A runnable invocation is a concrete `execute-script.py` call of one of the three
    review-and-merge surface verbs (see `_is_review_merge_surface`), excluding the
    `## Canonical invocations` advertised forms (which carry argparse's
    `[--flag [VALUE]]` optional-bracket notation and are specifications, not calls).
    The population is derived from the docs, never listed.
    """
    invocations: list[tuple[str, str, str]] = []
    for doc in _INVOCATION_DOCS:
        text = doc.read_text(encoding='utf-8')
        for block in _fenced_commands(text):
            match = _EXEC_CALL.search(block)
            if not match:
                continue
            if not _is_review_merge_surface(block):
                continue
            # Skip an advertised form: argparse renders optional flags as
            # `[--flag [VALUE]]`, which is a spec, not a runnable call.
            if '[' in block:
                continue
            invocations.append((doc.name, match.group('notation'), block.strip()))
    return invocations


_DOCUMENTED_INVOCATIONS = _documented_invocations()

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it — an empty
# parametrize is a pytest SKIP, not a failure, so a scan that matched nothing would
# report a clean sweep over nothing. The size travels in the message so a silently
# shrunken scan is visible as a number.
assert _DOCUMENTED_INVOCATIONS, (
    'no runnable review/merge invocation was scanned from the finalize merge-and-review '
    f'docs {[d.name for d in _INVOCATION_DOCS]} — the D3 population is vacuous and the '
    'parse sweep would pass over an empty set'
)


def _invocation_id(item: tuple[str, str, str]) -> str:
    doc, notation, _command = item
    return re.sub(r'[^A-Za-z0-9]+', '-', f'{doc}--{notation.split(":")[-1]}').strip('-').lower()


# =============================================================================
# D0 — the exit-code convention covers every invoked script, not only manage-*
# =============================================================================

_WIDE_HEADING = '## Exit-code convention for every script call'
_NARROW_HEADING = '## Exit-code convention for `manage-*` script calls'

#: The convention's exit-0-non-success clause. An `exit_code == 0` return whose `status` is
#: anything other than `success` is not a usable value and takes the `exit_code != 0`
#: disposition. Matched as a literal because the clause IS the contract.
_NEW_CLAUSE = '- **`exit_code == 0` with a `status` other than `success`**'

#: The per-step positive shape requirement — the stricter, call-site-local discharge.
_SHAPE_MARKER = '**Positive shape requirement.**'

#: Docs that invoke a non-`manage-*` script yet are deliberately exempt from the widened
#: convention, mapped to the reason. **Empty**: the sweep below found no doc in the pool
#: that needed one. An entry here must name a real, currently-obligated doc — a stale
#: exemption fails `test_no_exemption_is_stale`, so the dict cannot quietly outlive its
#: reason.
_WIDENING_EXEMPTIONS: dict[str, str] = {}


class TestExitCodeConventionCoversEveryScript:
    """Each merge-and-review doc's exit-code convention is scoped past ``manage-*``.

    The defect this pins: the convention was scoped to ``manage-*`` script calls,
    which structurally excluded the ``github_pr`` / ``review_completeness`` / ``ci``
    calls that gate the merge-and-review path and were the swallowed-rejection sites.
    """

    def test_the_invocation_population_is_non_empty_and_reaches_non_manage_star(self):
        """The derivation found real invocations, including the non-manage-* ones.

        Published as a size, and asserted to REACH the non-manage-* scripts — a
        population of only manage-* calls could not demonstrate the widening this
        suite exists to enforce.
        """
        all_notations: set[str] = set()
        for doc in _INVOCATION_DOCS:
            all_notations |= _invoked_notations(doc.read_text(encoding='utf-8'))

        assert all_notations, (
            f'no executor notation was scanned from {[d.name for d in _INVOCATION_DOCS]} '
            '— the population is vacuous'
        )
        non_manage = {n for n in all_notations if not _is_manage_star(n)}
        assert non_manage, (
            f'the merge-and-review docs invoke only manage-* scripts across '
            f'{len(all_notations)} notations, so the widening past manage-* cannot be '
            f'demonstrated: {sorted(all_notations)}'
        )
        # The three families the plan names must all be present, derived from the scan.
        skills = {n.split(':')[1] for n in non_manage}
        assert {'workflow-integration-github', 'automatic-review', 'tools-integration-ci'} <= skills, (
            f'the scan reached non-manage-* skills {sorted(skills)} but not all three of '
            'github / review_completeness / ci — the swallowed-rejection families'
        )

    @pytest.mark.parametrize('doc', _CONVENTION_DOCS, ids=lambda d: d.parent.name + '-' + d.name)
    def test_convention_is_widened_wherever_a_non_manage_star_script_is_invoked(self, doc):
        """The widening OBLIGATION is DERIVED from the doc's own non-manage-* invocations.

        The 'why must this doc be widened?' is not asserted by fiat — it is read off the
        doc's invocations. A doc that invokes only manage-* scripts would not need the
        widening; this asserts the widened convention exactly where the doc's derived
        non-manage-* invocations demand it, so the check tracks the tree rather than a
        curated claim about which docs matter.

        Mutation-proof in both directions: reverting the heading to the manage-* form
        fails the wide-heading assertion, and leaving the manage-*-scoped heading in place
        alongside the wide one fails the narrow-heading assertion.
        """
        text = doc.read_text(encoding='utf-8')
        non_manage = {n for n in _invoked_notations(text) if not _is_manage_star(n)}

        assert non_manage, (
            f'{doc.name} was expected to invoke a non-manage-* script — that is what makes '
            'widening the convention obligatory here — but the scan found none. The '
            'merge-and-review doc set has drifted, or the invocation scan regressed.'
        )
        assert _WIDE_HEADING in text, (
            f'{doc.name} invokes non-manage-* scripts {sorted(non_manage)} yet its exit-code '
            f'convention is not widened to {_WIDE_HEADING!r}. A manage-*-scoped convention '
            'leaves exactly those calls uncovered — the swallowed-rejection gap.'
        )
        assert _NARROW_HEADING not in text, (
            f'{doc.name}: the manage-*-scoped convention heading {_NARROW_HEADING!r} '
            'survives, so the widening did not fully land'
        )


# =============================================================================
# D2 — the widening reaches the WHOLE finalize pool, and the convention disposes
#      of the exit-0 non-success return
# =============================================================================


def _pool_docs() -> list:
    """Every markdown file under the finalize + automatic-review skills."""
    docs = []
    for root in _POOL_ROOTS:
        docs.extend(sorted(root.rglob('*.md')))
    return docs


def _widening_obligated() -> list[tuple[str, list[str]]]:
    """Return `(relative_path, non_manage_notations)` for every doc the sweep obligates.

    The obligation is READ OFF each doc's own fenced invocations: a doc that invokes a
    non-`manage-*` script needs the widened convention, and a doc that invokes only
    `manage-*` scripts does not. Nothing here is curated.
    """
    obligated: list[tuple[str, list[str]]] = []
    for doc in _pool_docs():
        non_manage = sorted(
            n for n in _invoked_notations(doc.read_text(encoding='utf-8'))
            if not _is_manage_star(n)
        )
        if non_manage:
            obligated.append((str(doc.relative_to(MARKETPLACE_ROOT)), non_manage))
    return obligated


_WIDENING_OBLIGATED = _widening_obligated()

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it.
assert _WIDENING_OBLIGATED, (
    'no doc under '
    f'{[str(r.name) for r in _POOL_ROOTS]} was found to invoke a non-manage-* script — the '
    'widening population is vacuous and the sweep would pass over an empty set'
)


def _ci_invocation_sections() -> list[tuple[str, str, bool]]:
    """Return `(relative_path, section_heading, has_shape_requirement)` per `ci`-invoking section.

    A "section" is a ``##``-or-deeper heading and the lines up to the next heading. The
    population is derived from the pool, so a `ci` call added to any finalize doc is swept
    without being listed.
    """
    ci_call = re.compile(
        r'python3\s+\.plan/execute-script\.py\s+plan-marshall:tools-integration-ci:ci\b'
    )
    found: list[tuple[str, str, bool]] = []
    for doc in _pool_docs():
        text = doc.read_text(encoding='utf-8')
        if not ci_call.search(text):
            continue
        lines = text.splitlines()
        marks = [i for i, ln in enumerate(lines) if re.match(r'^#{2,4} ', ln)]
        marks.append(len(lines))
        for start, end in zip(marks, marks[1:], strict=False):
            blob = '\n'.join(lines[start:end])
            if ci_call.search(blob):
                found.append(
                    (
                        str(doc.relative_to(MARKETPLACE_ROOT)),
                        lines[start].strip(),
                        _SHAPE_MARKER in blob,
                    )
                )
    return found


_CI_SECTIONS = _ci_invocation_sections()

assert _CI_SECTIONS, (
    'no `ci` invocation was scanned from the finalize doc pool — the discharge sweep '
    'would pass over an empty set'
)


def _obligated_id(item: tuple[str, list[str]]) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '-', item[0]).strip('-').lower()


def _ci_section_id(item: tuple[str, str, bool]) -> str:
    path, heading, _shape = item
    stem = f'{path.rsplit("/", 1)[-1]}--{heading.lstrip("# ")}'
    return re.sub(r'[^A-Za-z0-9]+', '-', stem).strip('-').lower()[:80]


class TestWideningReachesTheWholeFinalizePool:
    """Every finalize doc that invokes a non-``manage-*`` script carries the widened convention.

    The three merge-and-review docs above are a semantic scope; this sweep is the mechanical
    one over the whole pool, so a doc that invokes a non-``manage-*`` script under a narrow
    or absent convention fails here even though nobody listed it. That is the property the
    curated ``_CONVENTION_DOCS`` tuple cannot give: a NEW such doc fails on arrival.
    """

    def test_the_obligated_population_is_non_empty_and_published(self):
        """The sweep found real obligations, and says how many it covered."""
        assert len(_WIDENING_OBLIGATED) >= len(_CONVENTION_DOCS), (
            f'the pool sweep obligated only {len(_WIDENING_OBLIGATED)} doc(s), fewer than the '
            f'{len(_CONVENTION_DOCS)} merge-and-review docs already known to need the widening '
            f'— the scan regressed: {[p for p, _ in _WIDENING_OBLIGATED]}'
        )

    @pytest.mark.parametrize('obligated', _WIDENING_OBLIGATED, ids=_obligated_id)
    def test_obligated_doc_carries_the_widened_convention(self, obligated):
        """A doc invoking a non-manage-* script carries the wide heading, not the narrow one."""
        rel, non_manage = obligated
        if rel in _WIDENING_EXEMPTIONS:
            pytest.skip(f'{rel} is an enumerated exemption: {_WIDENING_EXEMPTIONS[rel]}')
        text = (MARKETPLACE_ROOT / rel).read_text(encoding='utf-8')

        assert _WIDE_HEADING in text, (
            f'{rel} invokes non-manage-* scripts {non_manage} yet carries no widened exit-code '
            f'convention ({_WIDE_HEADING!r}). Widen it, or add it to _WIDENING_EXEMPTIONS with '
            'a reason. Population swept: '
            f'{len(_WIDENING_OBLIGATED)} obligated doc(s).'
        )
        assert _NARROW_HEADING not in text, (
            f'{rel}: the manage-*-scoped heading {_NARROW_HEADING!r} survives alongside the '
            'widened one, so the widening did not fully land'
        )

    def test_no_exemption_is_stale(self):
        """An exemption must name a doc the sweep currently obligates.

        Without this, an exemption outlives the doc (or the invocation) that justified it and
        silently suppresses a case nobody re-examined.
        """
        obligated_paths = {p for p, _ in _WIDENING_OBLIGATED}
        stale = sorted(set(_WIDENING_EXEMPTIONS) - obligated_paths)
        assert not stale, (
            f'_WIDENING_EXEMPTIONS names {stale}, which the sweep does not obligate — the doc '
            'no longer invokes a non-manage-* script, or its path changed. Remove the entry.'
        )
        blank = sorted(k for k, v in _WIDENING_EXEMPTIONS.items() if not v.strip())
        assert not blank, f'_WIDENING_EXEMPTIONS entries {blank} carry no reason'


class TestExitZeroNonSuccessIsDisposedOf:
    """The widened convention states a disposition for an exit-0 non-``success`` return.

    The defect this pins: keying the convention on the exit code ALONE. ``ci_base.output_error``
    prints ``status: error`` and returns exit 0, and both provider ``main()`` functions return 0
    without branching on the result's ``status`` — so a FAILED call satisfies an exit-code-only
    ``exit_code == 0`` clause and its payload fields are then read off a return that has none.
    """

    @pytest.mark.parametrize('obligated', _WIDENING_OBLIGATED, ids=_obligated_id)
    def test_widened_convention_carries_the_exit_zero_non_success_clause(self, obligated):
        """A widened convention without the clause is the exit-0 hole left open."""
        rel, _non_manage = obligated
        if rel in _WIDENING_EXEMPTIONS:
            pytest.skip(f'{rel} is an enumerated exemption: {_WIDENING_EXEMPTIONS[rel]}')
        text = (MARKETPLACE_ROOT / rel).read_text(encoding='utf-8')

        assert _NEW_CLAUSE in text, (
            f"{rel} carries the widened convention but states no disposition for an exit-0 "
            f"return whose status is not `success` (expected the clause {_NEW_CLAUSE!r}). "
            'Keying on the exit code alone is exactly how a failed call reads as usable.'
        )

    @pytest.mark.parametrize('section', _CI_SECTIONS, ids=_ci_section_id)
    def test_ci_invocation_is_discharged(self, section):
        """Every documented ``ci`` invocation is discharged by one of the two arms.

        The two arms are the convention's exit-0-non-success clause (doc-level) and a
        per-step positive shape requirement (call-site-level). Stated honestly: the
        convention arm currently discharges EVERY invocation, because the sweep above
        requires that clause of every obligated doc — so this assertion's force lives in
        that sweep, and this test is what ties each concrete ``ci`` call site to it. The
        per-arm split is published below so a future reader can see which arm carried
        which call rather than inferring it from a green run.
        """
        rel, heading, has_shape = section
        text = (MARKETPLACE_ROOT / rel).read_text(encoding='utf-8')
        by_convention = _NEW_CLAUSE in text

        assert by_convention or has_shape, (
            f'{rel} § {heading} invokes `ci` but the call is discharged by neither arm: its '
            f'doc states no exit-0-non-success clause and the section states no '
            f'{_SHAPE_MARKER!r}. A failed `ci` call there is read as a usable value.'
        )

    def test_the_discharge_split_is_visible(self):
        """The per-arm split over the derived `ci` population is asserted, not merely implied.

        A shape requirement that is deleted while the convention clause survives would leave
        `test_ci_invocation_is_discharged` green, so the shape-marked count is pinned here
        against the sites that carry one.
        """
        shape_marked = sorted(f'{rel} § {head}' for rel, head, shape in _CI_SECTIONS if shape)
        assert len(shape_marked) >= 2, (
            f'only {len(shape_marked)} of {len(_CI_SECTIONS)} derived `ci` sections carry a '
            f'{_SHAPE_MARKER!r}. The PR-creating call and the pre-merge checks snapshot each '
            f'consume a named field off the return and MUST state the shape that makes it '
            f'readable: {shape_marked}'
        )


# =============================================================================
# D3 — every documented review-and-merge invocation parses against its own parser
# =============================================================================


class TestDocumentedReviewMergeInvocationsParse:
    """Every documented review/merge invocation parses against its live argparse.

    A flag prescribed on a parser that does not DECLARE it — the observed case is
    ``--enabled-bots`` written onto a ``github_pr fetch_findings`` call — or a
    ``--plan-id`` placed after a router verb is an argparse rejection (exit 2) when a
    leaf quotes the doc verbatim. The mismatch is PER-PARSER: ``--enabled-bots`` IS
    declared, on ``review_gate_delta assess``, so what fails is the flag/script
    PAIRING rather than the flag. Running each documented invocation against its REAL
    parser is what catches the pairing without this suite having to know which flags
    belong where.
    """

    def test_the_population_size_is_published(self):
        """A future reader can tell a passing sweep from an empty one by the count."""
        assert len(_DOCUMENTED_INVOCATIONS) >= 1
        # The floor is derived-not-guessed: the barrier and the FIND step each carry at
        # least a fetch_findings and a review_completeness check invocation (four), and
        # the re-review walkthrough carries a fetch_findings of its own (one), so the
        # honest floor of the scan is five. A scan that silently dropped below it means
        # the matcher stopped seeing real invocations.
        assert len(_DOCUMENTED_INVOCATIONS) >= 5, (
            f'only {len(_DOCUMENTED_INVOCATIONS)} runnable invocations were scanned from '
            f'{[d.name for d in _INVOCATION_DOCS]}; the barrier and the FIND step each '
            'document a fetch_findings and a review_completeness check and the re-review '
            'walkthrough documents a fetch_findings, so the floor is 5 '
            f'— the matcher likely stopped matching: {[i[1] for i in _DOCUMENTED_INVOCATIONS]}'
        )

    @pytest.mark.parametrize('invocation', _DOCUMENTED_INVOCATIONS, ids=_invocation_id)
    def test_documented_invocation_parses(self, invocation):
        """The documented flags parse against the script's real argparse (no exit 2).

        Placeholders are substituted with parseable values, and provider scripts run
        with an emptied ``PATH`` so they fail at the provider boundary (an argparse
        rejection would happen BEFORE that boundary, so it is still observed). A
        malformed VALUE is a post-parse caller error (exit 1), not an argparse
        rejection (exit 2), so only exit 2 — an unrecognized or mispositioned flag —
        fails this test.
        """
        doc_name, notation, command = invocation
        substituted = _substitute(command)
        tokens = shlex.split(substituted)
        # Drop `python3`, `.plan/execute-script.py`, and the notation; keep the rest
        # (verb + args) for the direct script invocation.
        try:
            notation_idx = tokens.index(notation)
        except ValueError:  # pragma: no cover - notation always present by construction
            pytest.fail(f'{doc_name}: notation {notation} vanished from {tokens}')
        args = tokens[notation_idx + 1 :]

        result = run_script(
            _script_path_for(notation), *args, env_overrides={'PATH': ''}
        )

        assert result.returncode != 2, (
            f'{doc_name}: the documented invocation `{command}` is an argparse rejection '
            f'(exit 2) against {notation.split(":")[-1]}.py — a flag it prescribes is not '
            f'declared by that parser, or is placed where the parser rejects it.\n'
            f'stderr: {result.stderr.strip()}'
        )
        assert 'unrecognized arguments' not in result.stderr, (
            f'{doc_name}: `{command}` names a flag {notation.split(":")[-1]}.py does not '
            f'declare.\nstderr: {result.stderr.strip()}'
        )
