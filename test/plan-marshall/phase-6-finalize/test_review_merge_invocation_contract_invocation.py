#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
  curated doc tuple above cannot catch), and every such convention must REACH the
  exit-0-non-``success`` disposition. A third sweep ties each derived ``ci`` call site to one
  of the two discharge arms — the doc-level clause or a call-site positive shape requirement.

  "Reach" rather than "state", because the convention is now single-sourced. The contract
  has exactly ONE body in the tree — :data:`_CANONICAL_STANDARD` — and every consuming doc
  points at it under the widened heading rather than restating it, an arrangement adopted
  because the duplicated paragraph produced two multi-site defects at two consecutive HEADs.
  This suite did not soften to match: it pins the literal AND its disposition body at the
  canonical standard unconditionally, and a referencing doc's obligation is discharged by
  that assertion rather than in place of it. What each doc must show is the same obligation
  as before, reached one hop away — never a hop into a document nobody checked.

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
no machine-readable manifest, so the doc SETS below are named from the plan's own scope
definition rather than derived. They are two distinct sets and this paragraph does not
enumerate either: ``_INVOCATION_DOCS`` is what gets scanned for invocations and
``_CONVENTION_DOCS`` is what must carry the widened convention, the second being the
first plus the dispatcher that orchestrates them. Reading the tuples is the only
reliable way to know their membership — an enumeration written out here drifts from
them silently, which it previously did. What is DERIVED — never hand-listed — is (a) WHERE each script is invoked
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
# The review-and-merge DECISION invocations live in the pre-merge barrier
# (branch-cleanup.md), the FIND + participation guard (automatic-review/SKILL.md),
# and the rebased-HEAD re-review walkthrough (branch-cleanup-rereview.md). The
# dispatcher SKILL.md orchestrates them and carries the same exit-code convention,
# so it is included in the convention-scope check but not scanned for invocations
# (its own calls are the dispatcher's, not the barrier's).
#
# The two tuples below are the authority for their own membership; this comment
# states no count, because a number here restates a tuple that changes and goes
# stale in the direction that hides a doc dropping out of a population.

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
_EXEC_CALL = re.compile(r'python3\s+\.plan/execute-script\.py\s+(?P<notation>plan-marshall:[a-z0-9-]+:[a-z0-9_-]+)')


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


#: The ADVERTISED-FORM marker: argparse renders an optional flag as `[--flag]` /
#: `[--flag VALUE]`, and a choice group as `(--a | --b)`. Such a block is a
#: SPECIFICATION of the surface, not a call, and substituting it would test the
#: substitution rather than the doc.
#:
#: Anchored to a bracket that OPENS A FLAG, never to a bare `[`. A bare-bracket
#: skip drops any real invocation whose arguments happen to contain one — a JSON
#: array value, a glob, a shell index — and it drops it SILENTLY, shrinking the
#: parse population to whatever survived. The narrow form excludes exactly the
#: advertised shapes and nothing else.
#: The opening bracket is ESCAPED. An unescaped ``[`` as the first member of a
#: character class reads as a nested set to ``re``, which warns — and this suite
#: turns warnings into errors, so the unescaped spelling fails at import and
#: takes the whole module's collection with it.
_ADVERTISED_FORM = re.compile(r'[\[(]\s*-{1,2}[a-zA-Z]')


def _command_segments(block: str) -> list[tuple[str, str]]:
    """Split a fenced block into `(notation, command)` per executor invocation.

    A block may document more than one call. Reading only the FIRST match — which
    is what `search` does — parses the first and silently ignores every later
    one, so a bad flag on the second call of a two-call block is invisible to the
    sweep. Each match therefore opens a segment that runs to the next match (or
    to the end of the block), and every segment is returned.
    """
    matches = list(_EXEC_CALL.finditer(block))
    segments: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        segments.append((match.group('notation'), block[match.start() : end].strip()))
    return segments


def _documented_invocations() -> list[tuple[str, str, str]]:
    """Return `(doc_name, notation, command)` for every RUNNABLE documented invocation.

    A runnable invocation is a concrete `execute-script.py` call of one of the three
    review-and-merge surface verbs (see `_is_review_merge_surface`), excluding the
    `## Canonical invocations` advertised forms (see `_ADVERTISED_FORM`). The
    population is derived from the docs, never listed — and EVERY invocation in a
    block is derived, not just the block's first.
    """
    invocations: list[tuple[str, str, str]] = []
    for doc in _INVOCATION_DOCS:
        text = doc.read_text(encoding='utf-8')
        for block in _fenced_commands(text):
            for notation, command in _command_segments(block):
                if not _is_review_merge_surface(command):
                    continue
                if _ADVERTISED_FORM.search(command):
                    continue
                invocations.append((doc.name, notation, command))
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


#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: population, but a population that merely SHRANK still passes it; publishing
#: the size on the green run is what makes that shrink visible.
GUARD_POPULATION_LABEL = 'documented review/merge invocations'
GUARD_POPULATION_SIZE = len(_DOCUMENTED_INVOCATIONS)


def _invocation_id(item: tuple[str, str, str]) -> str:
    doc, notation, _command = item
    return re.sub(r'[^A-Za-z0-9]+', '-', f'{doc}--{notation.split(":")[-1]}').strip('-').lower()


# =============================================================================
# D0 — the exit-code convention covers every invoked script, not only manage-*
# =============================================================================

_WIDE_HEADING = '## Exit-code convention for every script call'
_NARROW_HEADING = '## Exit-code convention for `manage-*` script calls'

#: The convention's exit-0-non-success clause. An `exit_code == 0` return whose `status` is
#: anything other than `success` — OR that carries no parseable `status` at all — is not a
#: usable value and takes the `exit_code != 0` disposition. Matched as a literal because the
#: clause IS the contract.
#:
#: The no-parseable-`status` arm is part of the pinned literal, not a separate optional
#: sentence, because it closes the hole the exit-code-only reading left BEHIND the first
#: one: a return whose stdout is malformed or truncated matches neither `status: success`
#: nor "a `status` other than `success`", so under the narrower wording it fell through
#: every clause and back onto the false-green. Pinning the widened wording is what stops a
#: doc reverting to the narrow form.
#:
#: Deliberately NOT weakened to a prefix match on the narrow wording. A prefix match would
#: pass on BOTH wordings, which is exactly how a doc keeps the superseded contract while the
#: guard stays green — the failure mode this literal exists to make impossible. The cost is
#: that a doc which LINE-WRAPS the clause fails the substring test even though its prose is
#: correct; that is accepted, and the fix is to keep the bolded lead-in on one line.
_NEW_CLAUSE = '- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**'

#: The disposition markers the clause BODY must carry — the part that actually prescribes
#: something. ``_NEW_CLAUSE`` above pins only the bolded lead-in, and a doc can keep that
#: lead-in byte-for-byte while deleting every instruction beneath it: the STOP disposition,
#: the preservation of the full stdout error envelope, and the synthesis of an error TOON
#: from raw stdout when no ``status`` parses. A heading-only assertion passes such a doc,
#: which is the vacuous-guard shape this literal exists to prevent — so the heading is
#: pinned AND the body is required to still prescribe those three things.
#:
#: Each marker is DERIVED from a live clause body, not composed from memory. They were
#: derived from the pool's clause bodies when every obligated doc carried one; under
#: single-sourcing there is exactly one such body left — the canonical standard's — and
#: the markers still hold of it, which the canonical-standard test below asserts
#: unconditionally rather than assuming. The marker SET is
#: unchanged by that migration: single-sourcing moved where the body lives, and softening
#: the set to whatever the surviving body happened to keep would have let the migration
#: quietly drop a disposition, which is the direction this check exists to watch.
#:
#: They are deliberately the SHORT invariant fragments rather than whole sentences, so a
#: re-worded disposition still counts and only a DELETED one fails.
#:
#: This ADDS to the heading assertion; it does not weaken it. The exact-substring
#: ``_NEW_CLAUSE`` check is unchanged, so the standing decision recorded above — not to
#: soften the heading into a prefix match — is preserved and the guard strengthens in the
#: same direction.
_NEW_CLAUSE_REQUIRED_MARKERS: tuple[str, ...] = (
    'STOP',
    '**error envelope**',
    'synthesize the error TOON',
)

#: The per-step positive shape requirement — the stricter, call-site-local discharge.
_SHAPE_MARKER = '**Positive shape requirement.**'

#: The ONE document that states the contract in full. Every consuming doc reaches
#: it by reference, so this is where ``_NEW_CLAUSE`` and its disposition body are
#: pinned — unconditionally, and independently of whether any consuming doc happens
#: to be swept on a given run.
#:
#: It sits OUTSIDE ``_POOL_ROOTS`` (a different skill owns it), so it can never be
#: the doc that discharges itself: the per-doc sweep below never reaches it, and the
#: assertion that does is the one this file states in its own right.
_CANONICAL_STANDARD = _SKILLS / 'tools-script-executor' / 'standards' / 'exit-code-convention.md'

#: The tail of the canonical standard's path that a reference must name. Matching
#: the TAIL is what makes the writing doc's relative prefix (``../``, ``../../``,
#: ``../../../plan-marshall/skills/``) irrelevant — a reference is correct wherever
#: it is written from, and the predicate should not have to know the depth of the
#: document writing it.
_CANONICAL_REFERENCE = 'tools-script-executor/standards/exit-code-convention.md'


def _convention_section(text: str) -> str:
    """Return the doc's exit-code-convention section: the wide heading to the next ``##``.

    Scoped for the same reason :func:`_clause_body` is scoped. A link to the canonical
    standard dropped ANYWHERE else in the doc — a See-Also list, an unrelated step, a
    sentence about some other contract — would otherwise discharge the reference arm
    while the doc's own convention section said nothing at all. That is the whole-document
    search the body-scoping above was introduced to reject, and it would arrive here by
    the back door if the reference arm were matched against the raw text.

    Returns the empty string when the doc carries no widened heading, so a doc missing
    the section reads as reaching nothing rather than raising.
    """
    idx = text.find(_WIDE_HEADING)
    if idx == -1:
        return ''
    tail = text[idx + len(_WIDE_HEADING) :]
    boundary = re.search(r'\n#{1,2} ', tail)
    return tail if boundary is None else tail[: boundary.start()]


def _reaches_the_clause(text: str) -> bool:
    """True when the doc reaches the exit-0-non-``success`` clause by either arm.

    Two arms, and the second is what single-sourcing added:

    * the doc STATES the clause itself — the arrangement before the contract was
      single-sourced, and still the canonical standard's own arrangement; or
    * the doc's convention SECTION references the canonical standard, which is
      asserted separately to carry the clause and its disposition.

    The second arm is not a weakening of the first. It is an obligation reached one
    hop away, and the hop terminates at a document this suite checks unconditionally
    (the canonical-standard test in ``TestExitZeroNonSuccessIsDisposedOf``) rather
    than at a link nobody follows.
    """
    return _NEW_CLAUSE in text or _CANONICAL_REFERENCE in _convention_section(text)


def _clause_body(text: str) -> str:
    """Return the disposition body that follows the clause's bolded lead-in.

    The body runs from the end of the lead-in to whichever comes first: the next
    top-level bullet, the next markdown heading, or end-of-text. Scoping the marker
    assertion to the BODY rather than to the whole document is what stops an unrelated
    occurrence of a marker word elsewhere in the doc from discharging the assertion —
    a whole-document search would let a doc delete the disposition and still pass on
    the strength of prose in some other section.

    Returns the empty string when the clause is absent, so a doc missing the clause
    entirely reports every marker as missing rather than raising.
    """
    idx = text.find(_NEW_CLAUSE)
    if idx == -1:
        return ''
    tail = text[idx + len(_NEW_CLAUSE) :]
    boundary = re.search(r'\n(?:- |#{1,6} )', tail)
    return tail if boundary is None else tail[: boundary.start()]


def _missing_disposition_markers(text: str) -> list[str]:
    """Return the required disposition markers absent from the doc's clause body."""
    body = _clause_body(text)
    return [marker for marker in _NEW_CLAUSE_REQUIRED_MARKERS if marker not in body]


def _undischarged_markers(text: str, canonical_text: str) -> list[str]:
    """Return the disposition markers a doc leaves unprescribed, by whichever arm it uses.

    A doc that STATES the clause is judged on its own body; a doc that REFERENCES the
    standard is judged on the standard's body. The canonical text is a parameter rather
    than a filesystem read so the matched control below can drive this with a GUTTED
    standard — a reference into a document whose disposition has been deleted has to
    fail, and a predicate that read the real standard off disk could never be shown to
    fail for that reason.

    Precondition: :func:`_reaches_the_clause` holds for *text*. A doc reaching neither
    arm is a different failure and is reported by that predicate, not by a marker list.
    """
    return _missing_disposition_markers(text if _NEW_CLAUSE in text else canonical_text)


#: Docs that invoke a non-`manage-*` script yet are deliberately exempt from the widened
#: convention, mapped to the reason. **Empty**: the sweep below found no doc in the pool
#: that needed one. An entry here must name a real, currently-obligated doc — a stale
#: exemption fails `test_no_exemption_is_stale`, so the dict cannot quietly outlive its
#: reason.
_WIDENING_EXEMPTIONS: dict[str, str] = {}


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
        non_manage = sorted(n for n in _invoked_notations(doc.read_text(encoding='utf-8')) if not _is_manage_star(n))
        if non_manage:
            obligated.append((str(doc.relative_to(MARKETPLACE_ROOT)), non_manage))
    return obligated


_WIDENING_OBLIGATED = _widening_obligated()

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
    ci_call = re.compile(r'python3\s+\.plan/execute-script\.py\s+plan-marshall:tools-integration-ci:ci\b')
    found: list[tuple[str, str, bool]] = []
    for doc in _pool_docs():
        text = doc.read_text(encoding='utf-8')
        if not ci_call.search(text):
            continue
        lines = text.splitlines()
        marks = [i for i, ln in enumerate(lines) if re.match(r'^#{2,} ', ln)]
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
    'no `ci` invocation was scanned from the finalize doc pool — the discharge sweep would pass over an empty set'
)


def _obligated_id(item: tuple[str, list[str]]) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '-', item[0]).strip('-').lower()


def _ci_section_id(item: tuple[str, str, bool]) -> str:
    path, heading, _shape = item
    stem = f'{path.rsplit("/", 1)[-1]}--{heading.lstrip("# ")}'
    return re.sub(r'[^A-Za-z0-9]+', '-', stem).strip('-').lower()[:80]


_REVIEW_COMPLETENESS = _SKILLS / 'automatic-review' / 'scripts' / 'review_completeness.py'

_FORM_ROUTE_RE = re.compile(
    r'(?P<fn>_split_bots|parse_stale_participation|parse_participation|parse_causes)'
    r"\(\s*args\.\w+,\s*'(?P<flag>--[a-z-]+)'"
)

_LIST_FLAG_RE = re.compile(r"add_argument\(\s*'(--[a-z-]+)'[^)]*?nargs\s*=\s*'\?'", re.DOTALL)


def _function_body(source: str, name: str) -> str:
    """The text of top-level ``def name`` up to the next top-level ``def``."""
    start = source.index(f'def {name}(')
    end = source.find('\ndef ', start)
    return source[start:] if end == -1 else source[start:end]


def _derive_form_sets() -> tuple[frozenset[str], frozenset[str]]:
    """``(pair_form, bare_form)`` read off ``_parse_bot_observations``'s routing."""
    body = _function_body(_REVIEW_COMPLETENESS.read_text(encoding='utf-8'), '_parse_bot_observations')
    pair: set[str] = set()
    bare: set[str] = set()
    for match in _FORM_ROUTE_RE.finditer(body):
        target = bare if match.group('fn') == '_split_bots' else pair
        target.add(match.group('flag'))
    return frozenset(pair), frozenset(bare)


def _declared_list_flags() -> frozenset[str]:
    """Every bot-list flag the shared adder declares, matched by shape.

    No exclusion set: a flag is a list flag iff its declaration carries
    ``nargs='?'``, which every list flag on this adder has and nothing else on it
    does. The two non-list flags fall out for their own reasons rather than by
    being named — ``--not-triggered`` is a ``store_true`` bool and ``--plan-id`` is
    a ``required=True`` scalar, and neither declares ``nargs``.
    """
    body = _function_body(_REVIEW_COMPLETENESS.read_text(encoding='utf-8'), '_add_bot_observation_flags')
    flags = frozenset(_LIST_FLAG_RE.findall(body))
    assert flags, (
        'No list flag was derived from _add_bot_observation_flags, which declares ten. '
        'The nargs-shape regex stopped matching, so the declared set is empty and every '
        'parity assertion below would compare against nothing and pass vacuously.'
    )
    return flags


PAIR_FORM_FLAGS, BARE_FORM_FLAGS = _derive_form_sets()

_PAIR_MARKER = 'PAIRS'

_BARE_MARKER = 'BARE'

_PROSE_FLAG_RE = re.compile(r'`(--[a-z][a-z-]*)`')

_FORM_PROSE_DOCS = (_BARRIER_DOC, _REVIEW_DOC)


def _form_paragraph(doc) -> str:
    """The single paragraph in *doc* that enumerates the two form sets."""
    # Annotated because `conftest` is an untyped import for mypy, so every path
    # derived from it — and everything read through it — arrives as `Any`.
    paragraphs: list[str] = [block for block in doc.read_text(encoding='utf-8').split('\n\n') if _PAIR_MARKER in block]
    assert len(paragraphs) == 1, (
        f'{doc.name}: expected exactly ONE paragraph carrying the {_PAIR_MARKER!r} form '
        f'marker, found {len(paragraphs)}. The parity check below cannot identify which '
        'paragraph enumerates the form sets, so it would compare the wrong text.'
    )
    return paragraphs[0]


def _named_form_sets(paragraph: str) -> tuple[frozenset[str], frozenset[str]]:
    """The ``(pair, bare)`` flag sets *paragraph* names, split at the BARE marker."""
    marker_at = paragraph.find(_BARE_MARKER)
    assert marker_at != -1, (
        f'The form paragraph carries {_PAIR_MARKER!r} but no {_BARE_MARKER!r} marker, so the '
        'bare-form enumeration cannot be bounded and every flag would read as pair-form.'
    )
    return (
        frozenset(_PROSE_FLAG_RE.findall(paragraph[:marker_at])),
        frozenset(_PROSE_FLAG_RE.findall(paragraph[marker_at:])),
    )


class TestWideningReachesTheWholeFinalizePool:
    """Every finalize doc that invokes a non-``manage-*`` script carries the widened convention.

    The merge-and-review docs above are a semantic scope; this sweep is the mechanical
    one over the whole pool, so a doc that invokes a non-``manage-*`` script under a narrow
    or absent convention fails here even though nobody listed it. That is the property the
    curated ``_CONVENTION_DOCS`` tuple cannot give: a NEW such doc fails on arrival.

    No size is stated for that semantic scope. ``_CONVENTION_DOCS`` holds the membership,
    and the test below already derives ``len(_CONVENTION_DOCS)`` as the floor it reports —
    a numeral here would restate a tuple that has already grown once and contradict the
    derived figure one screen below.
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
        """A future reader can tell a passing sweep from an empty one by the count.

        The floor is DERIVED, not transcribed. A remembered integer is a claim
        about the tree at the moment someone typed it: it goes stale the instant
        a doc gains or loses an invocation, and — being a floor — it goes stale
        SILENTLY in the direction that matters, staying satisfied while the scan
        shrinks toward it. The derived floor is a per-doc obligation instead:
        every doc in the invocation set documents at least one runnable call, so
        a doc that stopped matching is named rather than absorbed into a total
        that still clears a number.
        """
        by_doc: dict[str, list[str]] = {doc.name: [] for doc in _INVOCATION_DOCS}
        for doc_name, notation, _command in _DOCUMENTED_INVOCATIONS:
            by_doc[doc_name].append(notation.split(':')[-1])

        silent = sorted(name for name, found in by_doc.items() if not found)
        assert not silent, (
            f'{silent} contributed ZERO runnable review/merge invocations to a population of '
            f'{len(_DOCUMENTED_INVOCATIONS)} (per doc: {by_doc}). Each doc in the invocation '
            'set documents at least one call of the review-and-merge surface, so an empty '
            'side means the matcher stopped seeing that doc rather than that the doc changed. '
            'A total-only floor cannot see this: the remaining docs keep the total above it.'
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

        result = run_script(_script_path_for(notation), *args, env_overrides={'PATH': ''})

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


@pytest.mark.parametrize('doc', _FORM_PROSE_DOCS, ids=lambda doc: doc.parent.name + '/' + doc.name)
def test_form_paragraph_names_exactly_the_flags_the_parser_routes(doc):
    """Each prose form paragraph enumerates exactly the parser's two form sets.

    Fails when either side gains a flag, loses one, or MOVES one between forms —
    the three ways this paragraph has already drifted. The message names the
    direction so the fix is unambiguous: prose is corrected to the parser, never
    the other way round.
    """
    named_pair, named_bare = _named_form_sets(_form_paragraph(doc))

    assert named_pair == PAIR_FORM_FLAGS, (
        f'{doc.name}: the PAIR-form enumeration disagrees with what the parser routes.\n'
        f'  named but bare-form or unrouted: {sorted(named_pair - PAIR_FORM_FLAGS)}\n'
        f'  routed pair-form but unnamed:    {sorted(PAIR_FORM_FLAGS - named_pair)}\n'
        'A caller quoting this paragraph would send a token argparse rejects.'
    )
    assert named_bare == BARE_FORM_FLAGS, (
        f'{doc.name}: the BARE-form enumeration disagrees with what the parser routes.\n'
        f'  named but pair-form or unrouted: {sorted(named_bare - BARE_FORM_FLAGS)}\n'
        f'  routed bare-form but unnamed:    {sorted(BARE_FORM_FLAGS - named_bare)}\n'
        'This is the arm that already shipped naming five flags where the parser routes six.'
    )
