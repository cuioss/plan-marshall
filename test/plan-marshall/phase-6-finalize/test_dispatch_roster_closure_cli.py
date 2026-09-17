#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Roster-vs-registry closure regression for the finalize dispatched/inline split.

``standards/dispatch-inline-split.md`` is the single source of truth for which
finalize steps dispatch under ``Task: execution-context-{level}`` and which run
inline. It is hand-maintained prose with nothing structurally linking it to the
authoritative registry (``marshal.json`` → ``plan.phase-6-finalize.steps``), so
it drifted: the roster classified a subset of the registered steps while
claiming hardcoded counts that no longer matched.

These tests pin the closure invariant and the count-free rewrite:

(a) Every registered step is classified **exactly once** across the two rosters.
(b) The dispatched and inline rosters are **disjoint**.
(c) **No** step-count claim survives anywhere in ``dispatch-inline-split.md`` or
    in the ``SKILL.md`` § "Dispatched workflows vs inline steps" section. The
    sweep covers the whole document / section rather than two headline
    sentences, so every count claim is covered — a partial removal fails.
(d) Every row under ``## Dispatched steps`` declares the ``effort
    resolve-target`` lookup it resolves under — the roster's resolver-lookup
    completeness invariant.
(e) Every dispatch branch in the finalize skill emits its ``[DISPATCH]`` line from
    the **resolve seam**, not by hand: every ``Task:`` spawn is preceded by an
    ``effort resolve-target … --workflow`` call (the resolve that emits the line per
    firing, so a re-fire that re-resolves re-emits), and NO hand-written
    ``--message "[DISPATCH] …"`` step survives (it would double-emit and reintroduce
    the per-role blind spot the seam closes). The population is EVERY markdown file
    under the skill directory, walked — not ``SKILL.md`` alone. See "The (e)
    population is the whole skill directory" below for why the single-file scope was
    a blind spot and what the per-file scoping still narrows.
(f) Every step doc in the finalize-step registry that **self-classifies** (asserts
    "This step is \\*\\*inline\\*\\*" / "\\*\\*dispatched\\*\\*" in its own body)
    agrees with the roster: an inline-asserting doc's step appears under
    ``## Inline steps`` and NOT under ``## Dispatched steps``, and vice versa. This
    is the cross-document **correctness** check — closure/disjointness (a)-(b) prove
    each step carries exactly one classification, never that the classification is
    RIGHT, because they never read the step's own doc. The roster and the executor
    doc are two sources that can disagree, and ``default:architecture-refresh`` is
    the case that did: its executor doc asserted inline while the roster classified
    it dispatched. ⛔ Read "What (f) actually compares" below before crediting it
    with whole-registry coverage — it does not have it.
(g) ``SKILL.md`` item 5c's dispatch-boundary **classification contract** still routes
    a findings-bearing ``loop_back`` to ``returned_with_findings`` rather than to
    ``error``, and its five termination causes agree between the ``--termination-cause``
    command string, the detection table, and item 5e's cross-ledger sentence. Anchored
    on the ``record-dispatch-boundary`` command string and on the cause ORDER, never on
    a heading: no test in this directory read that table, so editing it back to the
    pre-fix four-cause routing reverted the deliverable with every test green.
(h) **The dispatch-site roster is corpus-wide and DERIVED.** Every markdown document
    under the ``plan-marshall`` skills tree that carries a ``Task: plan-marshall:``
    spawn IS a dispatch site, and that set must EQUAL the set of documents emitting
    through the resolve seam (one carrying an ``effort resolve-target`` invocation that
    itself passes ``--workflow``). The roster's size rides the session report header on
    every run, passing included. (e) above is the per-spawn form of the same property
    and stays scoped to the finalize skill directory; (h) is per-DOCUMENT, and the
    difference is load-bearing rather than stylistic — see "Why (h) is per-document and
    (e) is per-spawn" below.

Steps are named in the roster by their exact registry key (``default:`` /
``project:`` / ``bundle:skill`` prefix included), so the comparison is a plain
set equality with no normalisation heuristics.

The (d), (e) and (f) populations are **derived, never hardcoded**: (d) iterates
the rows the roster parser finds under ``## Dispatched steps``, (e) walks the
markdown files under the finalize skill directory and iterates the ``Task:`` spawns
found in each (pairing every one with its seam resolve) rather than a hardcoded
emit-site list, and (f) reads each step doc's OWN self-classification sentence over
a population DISCOVERED from the finalize-step registry (``find_implementors``)
rather than a pinned file list or a ``default:architecture-refresh`` literal. A
hardcoded roster or emit-site list would pass vacuously the moment a row or a
dispatch branch is added, which is precisely the drift these tests exist to
catch — and an ``assert 'default:architecture-refresh' in inline`` literal would
pass vacuously the instant the pair is fixed, detecting nothing else ever again.
Each detector carries a mutation guard asserting it fires on the exact
pre-fix shape, so a regex typo cannot make it vacuously green.

The (e) population is the whole skill directory
-----------------------------------------------
The seam sweep used to read ONE file — ``SKILL.md`` — and blank every line outside
one section of it. The detector itself was alive (mutating an in-section line did
redden it), but two real dispatch branches sat OUTSIDE that file entirely, in
``standards/finalize-step-simplify.md`` and ``workflow/pre-submission-self-review.md``,
and no shape they could take was visible to it. The population is now every
``*.md`` under the skill directory, discovered by walk.

The **per-file section scoping is kept**, and it is now per-file rather than global:
``_SECTION_SCOPED_DOCS`` narrows a named document to a named section, and every other
document is swept whole. Only ``SKILL.md`` is narrowed, for its documented reason —
a ``dispatch-logging.md`` citation in unrelated prose (the trailing ``## Related``
table) must not be read as an emit site. An executor doc has no such section
structure to scope against and carries its dispatch branch inline in its own
workflow, so sweeping it whole is what makes its spawn visible at all; its
``## Related`` table carries neither a ``Task:`` spawn line nor a
``--message "[DISPATCH]`` emit, so the false positive the SKILL.md scoping avoids
cannot arise there.

What (f) actually compares
--------------------------
(f)'s population is the WHOLE finalize-step registry, DERIVED from
``find_implementors`` — not a hardcoded file list. Every registered step's own
authoritative doc is read for a self-classification sentence, so a step that gains
one is covered for free and a doc that moves is followed by the registry rather
than dropping out of a pinned tuple. Closing this with a second hand-written pin (a
per-step ``assert '…' in inline`` literal) is exactly the
hand-maintained-mirror-of-a-derived-set archetype these tests exist to prevent, so
the population is discovered, never enumerated.

⛔ **The comparison is far narrower than the discovery, and this check does not
close that gap.** A doc contributes a comparison only when it carries the bold
self-classification sentence, and almost none of them do — so (f) discovers the
whole registry and then compares a small fraction of it. That fraction is
PUBLISHED (see "Published coverage" below) rather than asserted away: the number of
registered steps that contribute a comparison is reported on every run, including a
passing one, and no test asserts that it equals the registered-step count. Do not
read a green (f) as "every registered step's classification was checked" — read it
as "every step that states a classification agrees with the roster", which is a
strictly weaker claim over a population the header names.

Closing the gap needs a decision this test suite must not make on its own: the
preferred remedy adds a REQUIRED machine-readable classification fact to the
finalize-step extension-point frontmatter contract, and that contract reaches
implementor docs in CONSUMER projects outside this repository. A contract change
with that reach is escalated to the operator, not self-approved by a run. The
proposal — both options, the migration hazard, and the state of the
discovered-but-unregistered doc — is recorded in the plan's decision log and carried
in the PR body.

⛔ **The figures once quoted for this gap are stale, and were re-derived here by
calling the helpers above rather than trusted.** The lead said "26 implementor docs
against 25 registered steps"; the two sets are now the same size and the same
membership, so no discovered doc is unregistered today. That is a property of the
tree at this moment, not a guarantee — which is exactly why the registry-absence
finding below is reported rather than asserted empty.

Registry absence is REPORTED, never asserted
--------------------------------------------
A discovered doc that self-classifies but whose frontmatter ``name:`` resolves to no
registered key used to raise a hard ``AssertionError`` about frontmatter resolution.
That is the wrong failure: the real condition is REGISTRY ABSENCE — the doc exists
and declares a classification, and nothing registers it — and the assertion reported
neither that nor the doc. It is downgraded to a collected finding naming registry
absence, carried in the published coverage line and asserted for its CONTENT rather
than for its emptiness. ⛔ A silent skip would not be the fix: the reported finding
is the load-bearing half, and a doc that drops out of the comparison without saying
so is the same invisible-shrink defect this module exists to prevent.

The finding list is EMPTY in the tree as it stands (see the re-derivation above), and
nothing asserts that it stays that way. The assertion this replaced was dormant for
the same reason — the unregistered doc of the day did not self-classify — and would
have fired, with a message about the wrong condition, the moment it did.

Why (h) is per-document and (e) is per-spawn
--------------------------------------------
(e) pairs each spawn with a seam resolve inside a 25-line lookback, which is what lets
it name WHICH branch lost its resolve. That window is calibrated to a dispatch branch
written as a procedure — resolve, extract the target, dispatch. It is NOT calibrated to
a narrated worked example: ``dispatch-walkthrough.md`` § Example A puts its resolve 36
lines above its spawn, with the returned TOON, the emitted log line and the prompt body
narrated in between. Widening the window to reach that would erode the property that one
branch's resolve can never satisfy another branch's spawn, and naming the document in an
exclusion list would be the hand-maintained mirror of a derived set this module exists to
prevent.

So the corpus-wide direction is asserted per DOCUMENT: a document that dispatches must
also resolve with the dispatch context. That is strictly weaker than (e) — it cannot say
which spawn — and it is the strongest form that holds over narrated prose without a
suppression list. Both are kept, and neither subsumes the other: (e) keeps its precision
where its window is calibrated, (h) keeps the reach.

⛔ **The roster is spawns spelled ``Task: plan-marshall:``** — the execution-context
dispatch surface ``dispatch-logging.md`` governs. ``phase-5-execute/standards/operations.md``
carries three line-start ``Task:`` spawns naming ``subagent_type: pm-dev-builder:*``
agents instead. Those are not execution-context dispatches, so the seam contract does not
reach them and this roster does not claim to cover them — stated here so the boundary is
legible rather than inferred from a regex.

Published coverage
------------------
The (f) coverage figures ride the session report header
(``GUARD_POPULATION_LABEL`` / ``GUARD_POPULATION_SIZE`` below, rendered by the root
conftest's ``pytest_report_header``), so a comparison population that quietly shrank
is visible on the GREEN run. A ``print`` cannot publish it: this repository's
``addopts`` carry neither ``-s`` nor ``-rA``, so a passing test's stdout is captured
and discarded, and under the ``-n auto`` xdist run the canonical build performs, even
a capture-suspended write is swallowed at the worker boundary. The header is rendered
by the CONTROLLER before collection and is the one channel a pass surfaces.

⛔ **Stated rather than left implied**: the (e) sweep's per-document spawn counts do
NOT ride that channel. The header carries the (f) coverage line and the (h) dispatch-site
roster size; (e)'s population floors are asserted by their own tests, whose messages carry
the counts.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import NamedTuple

from _dispatch_roster import parse_roster, parse_roster_rows, section_lines
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT
from extension_discovery import find_implementors

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'

#: The (h) corpus root — the WHOLE plan-marshall skills tree. (e) reads one skill
#: directory inside it; (h) reads all of it, because "is a dispatch site" is not a
#: property of the finalize skill, and a roster bounded to that directory reports
#: clean over every dispatch site outside it without saying so.
_PLAN_MARSHALL_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

_ROSTER_DOC = _SKILL_DIR / 'standards' / 'dispatch-inline-split.md'
_SKILL_DOC = _SKILL_DIR / 'SKILL.md'
_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'

_DISPATCHED_HEADING = '## Dispatched steps'
_INLINE_HEADING = '## Inline steps'
_SKILL_SECTION_HEADING = '## Dispatched workflows vs inline steps'

#: The one ``SKILL.md`` section that carries every dispatch branch IN THAT FILE.
#: The (e) sweep narrows ``SKILL.md`` to it so a ``dispatch-logging.md`` link in
#: unrelated prose (e.g. the trailing ``## Related`` table) is not read as an emit
#: site — the exact false positive raised in review. The scoping drops no dispatch
#: branch from ``SKILL.md``: every ``Task: plan-marshall:`` spawn and every
#: emission-contract citation in THAT document lies inside this section. It never
#: bounded the sweep's population, which is the whole skill directory — see
#: ``_SECTION_SCOPED_DOCS``.
_SKILL_STEP3_HEADING = '### Step 3: Execute Step Pipeline (Manifest-Driven, Resumable, Timeout-Wrapped)'

#: Terminate the Step-3 scope at the next ``### `` step heading as well as at
#: the next ``## `` heading. The bare ``('## ',)`` default does NOT stop at
#: ``### Step 4`` (``'### Step 4'.startswith('## ')`` is ``False``), which would
#: silently run the section to EOF and make the scoping a no-op. ``#### ``
#: sub-headings inside Step 3 correctly do not terminate it, for the same
#: prefix-comparison reason.
_SKILL_SECTION_STOP_PREFIXES = ('## ', '### ')

#: Per-file section scoping for the (e) seam sweep, as
#: ``path -> (heading, stop_prefixes)``. A document listed here is swept ONLY
#: inside the named section; every other markdown file under the skill directory
#: is swept WHOLE. The map is what keeps the widened population from
#: reintroducing the ``## Related``-link false positive in ``SKILL.md`` while
#: still reaching the executor docs, which carry their dispatch branch inline in
#: their own workflow and have no equivalent section to scope against.
_SECTION_SCOPED_DOCS: dict[Path, tuple[str, tuple[str, ...]]] = {
    _SKILL_DOC: (_SKILL_STEP3_HEADING, _SKILL_SECTION_STOP_PREFIXES),
}

#: Spelled-out cardinals a step-count claim can use instead of a digit. ``one``
#: is deliberately EXCLUDED: "one step" is overwhelmingly ordinary singular prose
#: ("dispatch one step at a time"), not a cardinality claim about a set, so
#: including it would make the detector fire on legitimate text and force
#: suppressions — and a detector that must be suppressed to stay green is worse
#: than none.
_SPELLED_CARDINALS = (
    'two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|'
    'fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty'
)

#: Count-bearing prose patterns. Each matched the pre-fix text:
#:   "Of the 17 default + project finalize steps"  -> _COUNT_BEFORE_STEPS
#:   "all six steps follow the HEAD-only table"    -> _COUNT_BEFORE_STEPS (spelled)
#:   "**6 dispatch**" / "**11 run inline**"        -> _COUNT_BOLD_CLASSIFIER
#:   "is not counted in the 6/17 roster above"     -> _COUNT_RATIO
#:
#: The numeral branch accepts a digit OR a spelled-out cardinal. The digit branch
#: is unchanged; the alternation is what closes the blind spot that let BOTH
#: newly-covered HEAD-dependent sites survive every previous sweep — they spelled
#: their count as "six", and ``\b\d+`` cannot see a word.
_COUNT_BEFORE_STEPS = re.compile(rf'\b(?:\d+|{_SPELLED_CARDINALS})\s[\w\s+]{{0,40}}?\bsteps?\b', re.IGNORECASE)
_COUNT_BOLD_CLASSIFIER = re.compile(r'\d+\s+(?:dispatch|run\s+inline|inline)\b', re.IGNORECASE)
_COUNT_RATIO = re.compile(r'\b\d+\s*/\s*\d+\s+roster\b', re.IGNORECASE)

_COUNT_CLAIM_PATTERNS = (
    ('count-before-steps', _COUNT_BEFORE_STEPS),
    ('bold-count-classifier', _COUNT_BOLD_CLASSIFIER),
    ('count-ratio-roster', _COUNT_RATIO),
)

#: A roster row declares its resolver lookup as a backticked ``phase-6-finalize``
#: token, optionally carrying the ``--role`` sub-key it resolves under. Rows that
#: track ``phase-6-finalize.default`` spell the bare phase token plus an explicit
#: "no ``--role``" note, so the bare form is a legitimate declaration.
_RESOLVER_LOOKUP = re.compile(r'`phase-6-finalize(?:\s+--role\s+[\w-]+)?`')

#: A seam-emitting resolve. The ``[DISPATCH]`` line is a side effect of
#: ``effort resolve-target`` when the caller passes ``--workflow`` (the resolve
#: seam — ``dispatch-logging.md`` § Placement contract), emitted per firing so the
#: record survives a re-fire that re-resolves. A bare resolve WITHOUT
#: ``--workflow`` is a pure query and emits nothing.
#:
#: ⛔ The two tokens are required IN THE SAME INVOCATION, never merely both
#: somewhere in the lookback window. Searched independently over the window, a
#: genuinely bare resolve sitting immediately before a spawn PASSES whenever any
#: unrelated earlier command in the window happens to carry ``--workflow`` — so the
#: sweep would report clean over the exact bare-resolve regression it exists to
#: catch. ``--workflow`` is therefore matched against the backslash-continued
#: command block the ``effort resolve-target`` token belongs to (see
#: :func:`_continued_command_span`), the same continuation join the sibling scans in
#: this directory use to tell a real flag from one on a neighbouring command.
_SEAM_RESOLVE = re.compile(r'effort resolve-target\b')
_WORKFLOW_FLAG = re.compile(r'--workflow\b')

#: A hand-written ``[DISPATCH]`` emit — the FORBIDDEN pre-seam shape. Now that the
#: resolve seam emits the line, a hand-written ``manage-logging work "[DISPATCH]"``
#: step double-emits AND, placed once per role, reintroduces the per-role blind
#: spot the seam closes. No dispatch branch may carry one.
#:
#: ⛔ BOTH shell quote styles are accepted. The pattern used to anchor on the
#: double quote alone, and ``--message '[DISPATCH] …'`` is equally shell-valid — so
#: a duplicate hand-written emission written in single quotes evaded the sweep
#: entirely and the whole-corpus scan passed over the very double-emit the seam was
#: introduced to remove.
_HAND_WRITTEN_DISPATCH_EMIT = re.compile(r'--message\s+["\']\[DISPATCH\]')

#: A dispatch branch's ``Task:`` spawn line. ``MULTILINE`` so the same pattern
#: anchors per-line both when matched line-by-line and when swept over the whole
#: document by the vacuity guard.
_TASK_SPAWN = re.compile(r'^\s*Task:\s+plan-marshall:', re.MULTILINE)

#: How far back from a ``Task:`` spawn the paired seam resolve may sit. The widest
#: real gap is the project/skill branch (~18 lines: the multi-line resolve block,
#: the resolver-lookup paragraph, and the item-(2) preamble); 25 leaves headroom
#: while staying far below the ~300-line distance between distinct branches, so one
#: branch's resolve can never satisfy another branch's spawn.
_EMIT_LOOKBACK_LINES = 25

#: (f) The cross-document consistency population is DERIVED from the finalize-step
#: registry, never a pinned file list. Every implementor of this ext-point is a
#: registered finalize step whose OWN authoritative doc is discovered here; the
#: check reads each doc's self-classification and compares it to the roster, so a
#: step that gains (or loses) a self-classification sentence — or whose doc moves —
#: is followed by the registry rather than going stale in a hardcoded list. A
#: hardcoded mirror of the registry is exactly the drift archetype these tests
#: exist to prevent, so the population is discovered through the same
#: ``find_implementors`` path the dispatcher and the head-dependence derivation use.
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: A step doc's own classification claim. The wording is the canonical
#: self-classification sentence (``architecture-refresh.md`` § "This step is
#: **inline** …"). The bold marker is load-bearing: it distinguishes a
#: *classification assertion* from narrative uses of the words — "This step runs
#: as inline orchestration …" (``sonar-roundtrip.md``, ``automatic-review``) and
#: "the dispatched prompt loads …" (``finalize-step-simplify.md``) are prose
#: about HOW the step behaves, not a roster classification. That distinction
#: matters more now the population is the whole registry: only a doc making an
#: explicit **bold** self-classification contributes a claim, so narrative prose in
#: any discovered doc is never misread as a disagreement with the roster.
_SELF_CLASSIFICATION = re.compile(r'\bThis step is \*\*(inline|dispatched)\*\*')

#: A step doc's frontmatter ``name:`` value. Searched inside the frontmatter
#: block only — the body carries ``name: <step-name>`` lines inside dispatch
#: prompt examples that must not be mistaken for the doc's own identity.
_FRONTMATTER_NAME = re.compile(r'^name:\s*(.+?)\s*$', re.MULTILINE)

#: Registry-key prefixes a bare frontmatter ``name:`` may resolve under.
_REGISTRY_KEY_PREFIXES = ('', 'default:', 'project:', 'plan-marshall:')

#: (g) The item-5c dispatch-boundary classification contract. Anchored on the
#: ``--termination-cause`` alternation of the ``record-dispatch-boundary`` command —
#: a command string, deliberately NOT a heading and NOT an item number, both of
#: which move with ordinary editing while the invocation does not.
_TERMINATION_CAUSE_FLAG = re.compile(r'--termination-cause\s+\{([^}]+)\}')

#: The boundary-recording invocation the ``--termination-cause`` flag belongs to.
#: Asserted present so a renamed verb fails loudly rather than leaving the sweep
#: reading an alternation that no longer governs anything.
_BOUNDARY_RECORD_COMMAND = 'plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary'

#: The five causes, in the order the contract declares them. This tuple is the
#: INDEPENDENT oracle — it is copied from the specification, not derived from the
#: document, so a document that renames or reorders its own two surfaces
#: consistently still reddens. The two in-document surfaces (the command's
#: alternation and the detection table) are additionally compared to EACH OTHER,
#: which catches the half-edit the oracle alone would not localise.
_TERMINATION_CAUSES = (
    'step_complete',
    'returned_with_findings',
    'blocked_user_review',
    'blocked_session_restart',
    'error',
)

#: The routing each cause's detection rule MUST state — the deliverable this
#: contract locks. ``returned_with_findings`` exists precisely so a findings-bearing
#: ``loop_back`` is NOT stamped ``error``; before it, a multi-round self-review was
#: graded a defect, so the more thoroughly a gate worked the worse its plan looked.
#: Editing the table back to that routing is the silent revert (g) exists to catch.
_TERMINATION_CAUSE_ROUTING = {
    'step_complete': ('`outcome: done`',),
    'returned_with_findings': ('`outcome: loop_back`', 'never `error`'),
    'error': ('`outcome: failed`',),
}

#: Item 5e's cross-ledger sentence: the manifest execution log's ``loop_back``
#: outcome and item 5c's ``returned_with_findings`` cause must be documented as the
#: SAME event, or the two ledgers agree only by coincidence.
_CROSS_LEDGER_SENTENCE = 'the SAME event item 5c stamps `returned_with_findings` for'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registered_steps() -> set[str]:
    """Return the authoritative registered finalize-step key set."""
    data = json.loads(_MARSHAL_JSON.read_text(encoding='utf-8'))
    steps = data['plan']['phase-6-finalize']['steps']
    return set(steps.keys())


def _roster(heading: str) -> list[str]:
    """Parse the step keys out of one roster section, preserving order.

    Delegates to the shared ``_dispatch_roster`` parser (``test/_shared/``) so
    the row population is identical to the one
    ``test_step_termination_contract.py``'s reachability check reads — the
    two suites cannot silently drift apart one heading-walk at a time.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    return parse_roster(text, heading)


def _count_claims(text: str) -> list[str]:
    """Return every count-bearing fragment found in ``text``."""
    hits: list[str] = []
    for label, pattern in _COUNT_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(f'{label}: {match.group(0)!r}')
    return hits


def _roster_rows(heading: str) -> list[tuple[str, str]]:
    """Return ``(step_key, full_row_line)`` for one roster section.

    Delegates to the shared ``_dispatch_roster`` parser, so the row
    population is identical to the one ``_roster`` reads.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    return parse_roster_rows(text, heading)


def _row_declares_resolver_lookup(row: str) -> bool:
    """Whether a roster row declares the resolve-target lookup it resolves under."""
    return bool(_RESOLVER_LOOKUP.search(row))


def _blank_outside_section(text: str, heading: str, stop_prefixes: tuple[str, ...]) -> str:
    """Return ``text`` with every line outside the named section blanked.

    Blanking rather than slicing keeps the line count — and therefore every
    index the (e) detectors report — identical to the real document, so a
    reported ``line N`` still names the actual line in the file. The detectors
    themselves keep taking raw text, so their mutation guards can go on feeding
    them synthetic snippets; the scoping lives here, at the call sites.

    Raises:
        AssertionError: via ``section_lines`` when the heading is renamed —
        a loud failure rather than a silently empty (vacuous) sweep.
    """
    lines = text.splitlines()
    section = section_lines(text, heading, stop_prefixes=stop_prefixes)
    heading_index = next(index for index, line in enumerate(lines) if line.strip() == heading)
    start = heading_index + 1
    scoped = [''] * len(lines)
    scoped[start : start + len(section)] = section
    return '\n'.join(scoped)


def _finalize_skill_markdown_docs() -> list[Path]:
    """Every markdown file under the finalize skill directory, discovered by walk.

    The (e) population. Walked rather than listed: a hand-written file tuple would
    go stale the moment a dispatch branch moved into a new document, which is the
    single-file blind spot this widening removes — and it would do so silently,
    because a sweep over a shrunken file set reports clean.
    """
    return sorted(_SKILL_DIR.rglob('*.md'))


def _seam_sweep_corpus() -> list[tuple[str, str]]:
    """Return ``(relative_path, scoped_text)`` for every document in the (e) population.

    ``scoped_text`` is the whole file, except for the documents named in
    ``_SECTION_SCOPED_DOCS``, which are narrowed to their declared section (line
    numbering preserved — see :func:`_blank_outside_section`).
    """
    docs = _finalize_skill_markdown_docs()
    assert docs, (
        f'no markdown file found under {_SKILL_DIR} — the seam sweep would be '
        'vacuous, and there would be no failure to say so'
    )
    corpus: list[tuple[str, str]] = []
    for path in docs:
        text = path.read_text(encoding='utf-8')
        scope = _SECTION_SCOPED_DOCS.get(path)
        if scope is not None:
            heading, stop_prefixes = scope
            text = _blank_outside_section(text, heading, stop_prefixes)
        corpus.append((path.relative_to(_SKILL_DIR).as_posix(), text))
    return corpus


def _spawn_bearing_documents(corpus: list[tuple[str, str]]) -> list[str]:
    """Relative paths of the corpus documents that carry at least one ``Task:`` spawn."""
    return [rel for rel, text in corpus if _TASK_SPAWN.search(text)]


def _termination_causes_in_command(text: str) -> list[str]:
    """Return the causes the ``--termination-cause`` alternation accepts, in order.

    Pure over ``text`` so the mutation guard can drive it with the pre-fix block.
    """
    alternations = _TERMINATION_CAUSE_FLAG.findall(text)
    assert len(alternations) == 1, (
        f'expected exactly one `--termination-cause {{…}}` alternation, found '
        f'{len(alternations)}: {alternations} — the sweep cannot tell which one '
        'governs'
    )
    return [cause.strip() for cause in alternations[0].split('|')]


def _termination_cause_rows(text: str) -> list[tuple[str, str]]:
    """Return ``(cause, detection_rule)`` for each classification-table row, in order.

    The row population is DERIVED from the command's alternation rather than
    matched by table position or heading: a two-cell markdown row whose first cell
    backticks one of the accepted causes is a classification row. Restricting to
    two-cell rows is what keeps the wider three- and four-column tables in the same
    document (the resolver-outcome mappings) out of the population.
    """
    causes = set(_termination_causes_in_command(text))
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith('|') and stripped.endswith('|')):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if len(cells) != 2:
            continue
        name = cells[0].strip('`')
        if name in causes:
            rows.append((name, cells[1]))
    return rows


#: The HEAD-dependent prose region inside § "Step 3: Execute Step Pipeline".
#: Both count claims this sweep newly covers lived here — OUTSIDE § "Dispatched
#: workflows vs inline steps", which is the only section the existing SKILL.md
#: sweep reads. That is why they survived every previous pass.
#:
#: The region is deliberately narrow: two small blocks, NOT the whole of Step 3.
#: Step 3 legitimately says things like "applies to all five built-in
#: agent-suitable steps", which the widened spelled-out pattern WOULD flag. A
#: sweep that had to be suppressed to stay green would be worse than no sweep, so
#: the scope is drawn to the prose that actually makes head-dependence claims.
_HEAD_DEP_BLOCK_START = '**Special case — HEAD-dependent steps**'
_HEAD_DEP_BLOCK_END = 'applies only to steps declaring'
_HEAD_DEP_NOTE_MARKER = '**HEAD-dependent step set**'


def _head_dependent_region() -> str:
    """Return the SKILL.md HEAD-dependent prose region, guarded loudly.

    Scoped inside § "Step 3: Execute Step Pipeline" via the shared
    ``section_lines`` helper (whose own guard fails loudly on a heading rename),
    then narrowed to the two head-dependence blocks. Every marker lookup asserts,
    so a reworded marker fails the test rather than silently sweeping nothing —
    a vacuously-empty sweep is the failure mode this guard exists to prevent.
    """
    text = _SKILL_DOC.read_text(encoding='utf-8')
    section = section_lines(text, _SKILL_STEP3_HEADING, stop_prefixes=_SKILL_SECTION_STOP_PREFIXES)
    assert section, (
        f'SKILL.md section {_SKILL_STEP3_HEADING!r} parsed empty — the HEAD-dependent sweep would be vacuous.'
    )

    start = next((i for i, line in enumerate(section) if _HEAD_DEP_BLOCK_START in line), None)
    assert start is not None, (
        f'Marker {_HEAD_DEP_BLOCK_START!r} not found in § {_SKILL_STEP3_HEADING!r}. '
        'The HEAD-dependent special-case block was renamed or removed — fix the '
        'marker rather than letting the sweep silently cover nothing.'
    )
    end = next(
        (i for i, line in enumerate(section) if i > start and _HEAD_DEP_BLOCK_END in line),
        None,
    )
    assert end is not None, (
        f'Closing marker {_HEAD_DEP_BLOCK_END!r} not found after '
        f'{_HEAD_DEP_BLOCK_START!r} — the special-case block lost its closing '
        'sentence, so the swept region is unbounded.'
    )
    special_case_block = section[start : end + 1]

    note = [line for line in section if _HEAD_DEP_NOTE_MARKER in line]
    assert note, (
        f'Marker {_HEAD_DEP_NOTE_MARKER!r} not found in § {_SKILL_STEP3_HEADING!r}. '
        'The item-1 HEAD-dependent step-set note was renamed or removed.'
    )

    region = '\n'.join(special_case_block + note)
    assert region.strip(), 'HEAD-dependent region resolved empty — sweep would be vacuous.'
    return region


def _continued_command_span(lines: list[str], index: int) -> str:
    """Return the whole backslash-continued command block ``lines[index]`` belongs to.

    Walks BOTH ways from the anchor line: backwards while the preceding line ends
    in ``\\`` (the invocation's ``python3 …`` head and any earlier argument lines),
    and forwards while the current line ends in ``\\`` (its remaining arguments).
    The result is one invocation's full argument list and nothing else, which is
    what makes "this flag belongs to THIS command" answerable at all.

    The join is the one the sibling scans in this directory already use to tell a
    real flag from a mention on a neighbouring command (see
    ``test_step_completion_emission.py::_block_suppresses_via_mark_step_done``).
    """
    start = index
    while start > 0 and lines[start - 1].rstrip().endswith('\\'):
        start -= 1
    end = index
    while end + 1 < len(lines) and lines[end].rstrip().endswith('\\'):
        end += 1
    return '\n'.join(lines[start : end + 1])


def _seam_resolve_sites(lines: list[str]) -> list[tuple[int, str]]:
    """Return ``(line_index, whole_invocation_text)`` per ``effort resolve-target`` call."""
    return [
        (index, _continued_command_span(lines, index)) for index, line in enumerate(lines) if _SEAM_RESOLVE.search(line)
    ]


def _spawns_missing_seam_resolve(text: str) -> list[str]:
    """Return every ``Task:`` spawn not preceded by a ``--workflow`` seam resolve.

    The population is derived from the spawn sites present in ``text``; nothing
    about how many dispatch branches exist is assumed. A spawn is paired when an
    ``effort resolve-target`` invocation **that itself carries** ``--workflow`` sits
    within the lookback window before it — that resolve is the seam that emitted the
    ``[DISPATCH]`` line and its paired decision-log record for this firing. A spawn
    under a bare (no ``--workflow``) resolve leaves no dispatch record.

    ⛔ ``--workflow`` is read off the resolve's OWN continued command block, never
    off the window as a whole. The two tokens searched independently made a bare
    resolve pass on the strength of an unrelated ``--workflow``-bearing command
    earlier in the same 25-line window — the guard's own comment names one
    invocation, so a window-wide search is weaker than the property it claims.
    """
    lines = text.splitlines()
    seam_sites = _seam_resolve_sites(lines)
    unpaired: list[str] = []
    for index, line in enumerate(lines):
        if not _TASK_SPAWN.match(line):
            continue
        window_start = max(0, index - _EMIT_LOOKBACK_LINES)
        paired = any(
            window_start <= site_index < index and _WORKFLOW_FLAG.search(invocation)
            for site_index, invocation in seam_sites
        )
        if not paired:
            unpaired.append(f'line {index + 1}: {line.strip()!r}')
    return unpaired


def _hand_written_dispatch_emits(text: str) -> list[str]:
    """Return every hand-written ``[DISPATCH]`` emit line — the forbidden shape.

    Once the resolve seam emits the ``[DISPATCH]`` line, a hand-written
    ``manage-logging work "[DISPATCH]"`` step double-emits and, placed once per
    role, reintroduces the per-role blind spot the seam exists to close.
    """
    return [
        f'line {index + 1}: {line.strip()!r}'
        for index, line in enumerate(text.splitlines())
        if _HAND_WRITTEN_DISPATCH_EMIT.search(line)
    ]


# ---------------------------------------------------------------------------
# (h) the corpus-wide DERIVED dispatch-site roster
# ---------------------------------------------------------------------------


@functools.cache
def _plan_marshall_markdown_docs() -> tuple[Path, ...]:
    """Every markdown document under the plan-marshall skills tree — (h)'s INPUT.

    Published by the assertions below rather than assumed: everything (h) claims is
    derived from this walk, so a root that resolved wrong would shrink the roster
    while every later assertion stayed green.
    """
    return tuple(sorted(_PLAN_MARSHALL_SKILLS.rglob('*.md')))


@functools.cache
def _dispatch_site_roster() -> tuple[Path, ...]:
    """The DERIVED dispatch-site roster: docs carrying a ``Task: plan-marshall:`` spawn.

    Walked, never listed. A hardcoded roster passes vacuously the moment a dispatch
    site is added to a document nobody enumerated — which is the single-file blind
    spot (e) already had to grow out of once, at one directory's scale.
    """
    return tuple(doc for doc in _plan_marshall_markdown_docs() if _TASK_SPAWN.search(doc.read_text(encoding='utf-8')))


def _emits_through_the_seam(text: str) -> bool:
    """Whether a document carries a seam-emitting resolve.

    ``--workflow`` is read off the resolve's OWN continued command block via
    :func:`_seam_resolve_sites`, never off the document as a whole — the same
    same-invocation rule (e) enforces. Searched document-wide, a bare resolve would
    pass on the strength of an unrelated ``--workflow``-bearing command elsewhere in
    the file, which is the weaker property wearing the stronger one's name.
    """
    return any(_WORKFLOW_FLAG.search(invocation) for _index, invocation in _seam_resolve_sites(text.splitlines()))


def _seam_emitting_dispatch_sites() -> tuple[Path, ...]:
    """The roster members that emit through the seam — the set (h) compares against."""
    return tuple(doc for doc in _dispatch_site_roster() if _emits_through_the_seam(doc.read_text(encoding='utf-8')))


def _dispatch_site_roster_line() -> str:
    """Render (h)'s population figures as the report-header clause.

    A ratio, not a bare count: "0 of 0" and "11 of 11" are the same green to a
    count alone, and only the first means the walk found nothing to check.
    """
    roster = _dispatch_site_roster()
    emitting = _seam_emitting_dispatch_sites()
    return (
        f'{len(emitting)} of {len(roster)} derived dispatch-site document(s) emit '
        f'through the resolve seam ({len(_plan_marshall_markdown_docs())} markdown '
        'document(s) walked)'
    )


def _frontmatter_name(text: str) -> str | None:
    """Return the ``name:`` value from a doc's YAML frontmatter block, if present."""
    if not text.startswith('---'):
        return None
    end = text.find('\n---', 3)
    if end == -1:
        return None
    match = _FRONTMATTER_NAME.search(text[3:end])
    return match.group(1).strip() if match else None


def _registry_key(frontmatter_name: str, registered: set[str]) -> str | None:
    """Resolve a doc's frontmatter ``name:`` to its registry key, or ``None``.

    A step doc spells its own name bare (``architecture-refresh``,
    ``finalize-step-plugin-doctor``) or already prefixed
    (``default:architecture-refresh``); the registry keys carry the prefix. Try
    each accepted prefix against the authoritative key set rather than guessing.
    """
    for prefix in _REGISTRY_KEY_PREFIXES:
        candidate = f'{prefix}{frontmatter_name}'
        if candidate in registered:
            return candidate
    return None


def _finalize_step_doc_paths() -> list[Path]:
    """Return the doc :class:`Path` of every discovered finalize-step implementor.

    The population is the finalize-step registry, discovered through the same
    ``find_implementors`` path the dispatcher and the head-dependence derivation
    use — never a hardcoded file list — so a step added, removed, or relocated is
    followed automatically rather than going stale in a pinned tuple here.
    """
    return [Path(str(record['path'])) for record in find_implementors(_FINALIZE_STEP_EXT_POINT)]


def _classify_discovered_doc(
    doc_path: str, text: str, registered: set[str]
) -> tuple[tuple[str, str, str] | None, str | None]:
    """Return ``(claim, finding)`` for ONE discovered step doc — at most one is set.

    Pure over its three inputs so the mutation guard can drive it with a synthetic
    document, and the single place the registry-absence disposition lives.

    A doc that carries no self-classification sentence contributes NEITHER: the
    check is about *disagreement* between two sources, so a doc that asserts nothing
    cannot disagree with the roster.

    A doc that DOES self-classify but resolves to no registered key contributes a
    **finding naming registry absence**, never an exception. The hard assertion this
    replaced reported "frontmatter resolution" — which is not the condition. The doc
    exists, declares a classification, and nothing registers it; that is the fact
    worth reporting, and it is reported rather than raised so an unregistered doc
    gaining the sentence does not fail the suite with a message about the wrong
    thing. ⛔ It is NOT skipped silently: the finding is the load-bearing half.
    """
    match = _SELF_CLASSIFICATION.search(text)
    if not match:
        return None, None
    claim = match.group(1)
    name = _frontmatter_name(text)
    if not name:
        return None, (
            f'{doc_path}: self-classifies **{claim}** but declares no frontmatter '
            '`name:`, so it resolves to no registered finalize-step key (registry '
            'absence) and contributes no comparison'
        )
    key = _registry_key(name, registered)
    if key is None:
        return None, (
            f'{doc_path}: self-classifies **{claim}** under frontmatter name '
            f'{name!r}, which resolves to no registered finalize-step key (registry '
            'absence) — the doc is discovered but unregistered, so it contributes no '
            'comparison'
        )
    return (doc_path, key, claim), None


def _step_doc_claims(
    paths: list[Path] | None = None,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Return ``(claims, findings)`` over the registry-DERIVED (f) population.

    ``claims`` are ``(doc_path, registry_key, claim)`` triples the correctness check
    compares; ``findings`` name every discovered self-classifying doc that resolves
    to no registered key. Both are products of the same walk, so the comparison
    population and the reported shortfall can never be read from different sets.

    ``paths`` defaults to a fresh ``find_implementors`` discovery; the coverage
    helper passes the discovery it already performed so one call site does not walk
    the registry twice.
    """
    registered = _registered_steps()
    claims: list[tuple[str, str, str]] = []
    findings: list[str] = []
    for path in _finalize_step_doc_paths() if paths is None else paths:
        claim, finding = _classify_discovered_doc(str(path), path.read_text(encoding='utf-8'), registered)
        if claim is not None:
            claims.append(claim)
        if finding is not None:
            findings.append(finding)
    return claims, findings


class _RosterCoverage(NamedTuple):
    """The three (f) coverage figures plus the registry-absence findings.

    A NamedTuple rather than a ``dict[str, int | list[str]]``: the heterogeneous
    mapping typed every lookup as the union of ALL its value types, so ``len()``
    over the findings list could not be checked without narrowing the read back
    down at each call site. Naming the fields gives each one its own type, which
    is what lets the checker verify these figures instead of the call sites
    asserting them.
    """

    #: Implementor docs ``find_implementors`` discovered — the walked population.
    discovered_docs: int
    #: Steps ``marshal.json`` registers — the denominator the ratio is against.
    registered_steps: int
    #: Distinct registered keys that actually contributed a comparison.
    compared: int
    #: One message per discovered doc that self-classifies under no registered key.
    unregistered_self_classifiers: list[str]


def _roster_correctness_coverage() -> _RosterCoverage:
    """The (f) coverage figures, derived by calling this module's own helpers.

    Nothing here is transcribed: ``discovered_docs`` comes from
    ``find_implementors``, ``registered_steps`` from ``marshal.json``, and
    ``compared`` from the claims the walk actually produced. Publishing the three
    together is what makes "discovered the whole registry, compared a fraction of
    it" legible instead of implied.
    """
    paths = _finalize_step_doc_paths()
    claims, findings = _step_doc_claims(paths)
    return _RosterCoverage(
        discovered_docs=len(paths),
        registered_steps=len(_registered_steps()),
        compared=len({key for _path, key, _claim in claims}),
        unregistered_self_classifiers=findings,
    )


def _coverage_line(coverage: _RosterCoverage) -> str:
    """Render the (f) coverage figures as the one line the report header carries."""
    return (
        f'{coverage.compared} of {coverage.registered_steps} registered steps '
        f'compared ({coverage.discovered_docs} implementor docs discovered, '
        f'{len(coverage.unregistered_self_classifiers)} unregistered '
        'self-classifier(s))'
    )


#: The separator joining the two clauses ``GUARD_POPULATION_SIZE`` publishes — the
#: (f) coverage line and the (h) dispatch-site roster line. Named once, and used by
#: BOTH the join below and the assertion that reads the header back apart, so the
#: two cannot drift: a hardcoded separator at the reading end would go stale the
#: moment the join changed, and the read would then compare a clause against the
#: whole string again — the exact shape that made the equality unsatisfiable when
#: the (h) clause was appended.
_GUARD_CLAUSE_SEPARATOR = '; '

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. See the module docstring's "Published coverage"
#: section for why this channel and not a ``print``, and for what it does and does
#: not carry. The value is a rendered LINE rather than a bare integer because the
#: figure that matters is a RATIO: a bare "1" would report the comparison count as
#: if it were the coverage, which is the over-crediting this publication exists to
#: stop.
#:
#: TWO clauses ride it, in this order: (f)'s coverage line, then (h)'s dispatch-site
#: roster line. Each is guarded against the live derivation SEPARATELY below — a
#: second clause must not leave the first unchecked, and it must not leave itself
#: unchecked either.
GUARD_POPULATION_LABEL = 'finalize roster self-classification coverage + dispatch-site roster'
GUARD_POPULATION_SIZE = _GUARD_CLAUSE_SEPARATOR.join(
    (_coverage_line(_roster_correctness_coverage()), _dispatch_site_roster_line())
)


def _classification_mismatches(
    claims: list[tuple[str, str, str]],
    dispatched: set[str],
    inline: set[str],
) -> list[str]:
    """Return one message per step doc whose self-claim contradicts the roster.

    Kept pure over its three inputs so the mutation guard can drive it with the
    exact pre-fix roster text and claim, without touching the real documents.
    """
    mismatches: list[str] = []
    for rel, key, claim in claims:
        expected, opposite = (inline, dispatched) if claim == 'inline' else (dispatched, inline)
        if key in expected and key not in opposite:
            continue
        mismatches.append(
            f'{rel}: the step doc asserts **{claim}** for {key!r}, but the roster '
            f'has dispatched={key in dispatched} inline={key in inline}'
        )
    return mismatches


# ---------------------------------------------------------------------------
# (a) + (b) closure and disjointness
# ---------------------------------------------------------------------------


def test_roster_rows_carry_no_duplicates():
    for heading in (_DISPATCHED_HEADING, _INLINE_HEADING):
        keys = _roster(heading)
        duplicates = {key for key in keys if keys.count(key) > 1}
        assert not duplicates, f'Duplicate rows under {heading!r}: {sorted(duplicates)}'


def test_roster_document_carries_no_step_count_claim():
    text = _ROSTER_DOC.read_text(encoding='utf-8')

    hits = _count_claims(text)

    assert not hits, (
        f'Step-count claim(s) reintroduced into dispatch-inline-split.md — the '
        f'roster is deliberately count-free: {hits}'
    )


def test_count_claim_patterns_detect_the_pre_fix_prose():
    # Mutation guard: the sweeps above are only meaningful if these patterns
    # actually fire on the exact prose this deliverable removed. Without this,
    # a typo in the regexes would make every sweep vacuously green.
    pre_fix_samples = [
        'Of the 17 default + project finalize steps, **6 dispatch** and **11 run inline**.',
        'is not counted in the 6/17 roster above',
        'The 11 inline steps (`finalize-step-sync-baseline`, `push`) are pure scripts.',
        # The two spelled-out claims removed from the HEAD-dependent region. A
        # widened pattern that silently failed to match these would leave the new
        # sweep green while covering nothing.
        'A dirty tree at any re-entry indicates an upstream contract violation '
        'rather than a re-fire trigger; all six steps follow the HEAD-only table.',
        'All other finalize steps keep the general rule above verbatim; this '
        'special case applies only to the six steps named in `HEAD_DEPENDENT_STEPS`.',
    ]

    for sample in pre_fix_samples:
        assert _count_claims(sample), f'Count-claim sweep failed to detect known pre-fix prose: {sample!r}'


def test_roster_row_population_matches_the_closure_parser():
    # Guards the new parser against silently reading a different population than
    # the closure assertions do — a divergence would make (d) cover a subset.
    assert [key for key, _ in _roster_rows(_DISPATCHED_HEADING)] == _roster(_DISPATCHED_HEADING)


def test_no_hand_written_dispatch_emit_survives():
    # The resolve seam owns the `[DISPATCH]` emission; a hand-written
    # `manage-logging work "[DISPATCH]"` step double-emits and reintroduces the
    # per-role blind spot the seam closes. No dispatch branch may carry one.
    corpus = _seam_sweep_corpus()

    hand_written = [f'{rel}: {hit}' for rel, text in corpus for hit in _hand_written_dispatch_emits(text)]

    assert not hand_written, (
        f'Hand-written `--message "[DISPATCH] …"` emit(s) under the finalize skill '
        f'— the resolve seam owns the emission now, so a hand-written line '
        f'double-emits and reintroduces the per-role blind spot: {hand_written}'
    )


def test_the_roster_reaches_past_the_finalize_skill_directory():
    """The floor: (h) must cover dispatch sites (e) structurally cannot see.

    (e) is bounded to the finalize skill directory. If the roster ever collapsed back
    inside that boundary, (h) would be a more expensive restatement of (e) and the
    orchestrator dispatch sites — which live in `plan-marshall/workflow/` — would be
    covered by nothing here.
    """
    roster = _dispatch_site_roster()
    beyond = [doc for doc in roster if _SKILL_DIR not in doc.parents]

    assert beyond, (
        f'Every one of the {len(roster)} derived dispatch-site document(s) lies inside '
        f'{_SKILL_DIR}, so (h) reaches nothing (e) does not already cover. Either the '
        'walk collapsed to that directory, or the spawn detector stopped matching the '
        'orchestrator workflow docs.'
    )


def test_the_roster_and_seam_detectors_fire_on_the_pre_seam_shape(tmp_path):
    """Matched control pair for (h): a bare-resolve site is detected, a seam one is not.

    Both fixtures are dispatch sites by the roster detector — that is what makes the
    split attributable to the seam detector alone. The bare fixture additionally puts a
    ``--workflow``-bearing command immediately BEFORE its bare resolve: read
    document-wide instead of per-invocation, that neighbour would make the bare resolve
    pass, which is the weaker property this control forbids.
    """
    bare = tmp_path / 'bare_resolve.md'
    bare.write_text(
        'Unrelated neighbour:\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\\n'
        '  effort read --workflow plan-marshall:phase-2-refine/SKILL.md\n'
        '```\n\n'
        'Resolve:\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\\n'
        '  effort resolve-target --role phase-2-refine\n'
        '```\n\n'
        '```text\n'
        'Task: plan-marshall:{target}\n'
        '```\n',
        encoding='utf-8',
    )
    seam = tmp_path / 'seam_resolve.md'
    seam.write_text(
        'Resolve:\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\\n'
        '  effort resolve-target --role phase-2-refine \\\n'
        '  --workflow plan-marshall:phase-2-refine/SKILL.md --plan-id {plan_id} \\\n'
        '  --caller plan-marshall:plan-marshall\n'
        '```\n\n'
        '```text\n'
        'Task: plan-marshall:{target}\n'
        '```\n',
        encoding='utf-8',
    )

    for fixture in (bare, seam):
        assert _TASK_SPAWN.search(fixture.read_text(encoding='utf-8')), (
            f'{fixture.name} was not read as a dispatch site, so the split below would '
            'not be attributable to the seam detector.'
        )

    assert not _emits_through_the_seam(bare.read_text(encoding='utf-8')), (
        'The seam detector accepted a BARE resolve. Either it reads `--workflow` '
        'document-wide instead of off the continued command block the resolve itself '
        'belongs to, or it no longer fires at all — in both cases (h) reports clean '
        'over the exact regression it exists to catch.'
    )
    assert _emits_through_the_seam(seam.read_text(encoding='utf-8')), (
        'The seam detector rejected a resolve that DOES carry `--workflow`. A detector '
        'that fires on a conformant site is a false positive, and (h) would have to be '
        'suppressed to stay green.'
    )


def test_seam_resolve_detectors_fire_on_the_pre_fix_shape():
    # Mutation guard: reproduce the pre-fix dispatch branch — a BARE resolve (no
    # --workflow), a hand-written `[DISPATCH]` emit, then the `Task:` spawn.
    pre_fix = '\n'.join(
        [
            '      (1) Resolve the level-bound target via the resolver:',
            '          python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\',
            '            effort resolve-target --phase phase-6-finalize [--role <subkey>]',
            '      (2) Emit the standardized `[DISPATCH]` work-log line:',
            '          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\',
            '            work --plan-id {plan_id} --level INFO \\',
            '            --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} '
            'level={level} role={role} workflow={workflow} plan_id={plan_id}"',
            '      (3) Dispatch:',
            '          Task: plan-marshall:{target}',
        ]
    )

    assert _spawns_missing_seam_resolve(pre_fix), (
        'Seam-resolve detector failed to flag a `Task:` spawn preceded only by a '
        'bare resolve (no --workflow) — the pre-fix shape'
    )
    assert _hand_written_dispatch_emits(pre_fix), (
        'Hand-written-emit detector failed to flag the known pre-fix `[DISPATCH]` line'
    )

    # Positive control — the post-fix shape (a --workflow resolve, no hand-written
    # emit, then the spawn) clears BOTH detectors, so neither is unconditionally
    # positive.
    post_fix = '\n'.join(
        [
            '      (1) Resolve the target, passing the dispatch context so the seam emits:',
            '          python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\',
            '            effort resolve-target --phase phase-6-finalize [--role <subkey>] \\',
            '            --workflow plan-marshall:phase-6-finalize/workflow/{name}.md \\',
            '            --plan-id {plan_id} --caller plan-marshall:phase-6-finalize',
            '      (2) Dispatch:',
            '          Task: plan-marshall:{target}',
        ]
    )

    assert not _spawns_missing_seam_resolve(post_fix)
    assert not _hand_written_dispatch_emits(post_fix)


def test_finalize_step_registry_population_is_non_empty_and_readable():
    # Guards the DERIVED population: find_implementors must discover finalize-step
    # docs, and every discovered doc must exist on disk — a discovery that returns
    # nothing (or a phantom path) would make the cross-document sweep vacuous, and
    # there is no hardcoded list to notice the shrinkage.
    paths = _finalize_step_doc_paths()

    assert paths, (
        'find_implementors discovered no finalize-step docs — the cross-document consistency sweep would be vacuous'
    )
    missing = [str(path) for path in paths if not path.exists()]
    assert not missing, f'Discovered finalize-step doc(s) do not exist on disk: {missing}'


def test_unregistered_self_classifying_docs_are_reported_as_registry_absence():
    """A discovered doc that resolves to no registered key is a FINDING, not a raise.

    The helper used to hard-assert registry resolution, so the moment the
    discovered-but-unregistered doc gained a self-classification sentence the suite
    would fail with a message about frontmatter resolution rather than about the real
    condition. The finding is what carries the condition, so its CONTENT is what this
    test pins — and its count rides the published coverage line, so a doc that drops
    out of the comparison says so on a green run.

    ⛔ This test does not assert the finding list is empty. An empty list and a
    reported one are both valid states of the tree; what is not valid is the
    condition going unreported.
    """
    _claims, findings = _step_doc_claims()

    for finding in findings:
        assert 'registry absence' in finding, f'registry-absence finding does not name the condition: {finding!r}'
        assert 'contributes no comparison' in finding, (
            f'registry-absence finding does not name its consequence: {finding!r}'
        )
    assert f'{len(findings)} unregistered self-classifier(s)' in GUARD_POPULATION_SIZE, (
        'the registry-absence count is not carried on the published coverage line, so '
        'a reported finding would be invisible on a passing run'
    )


def test_cross_document_consistency_detector_fires_on_the_pre_fix_shape():
    # Mutation guard (comparison half): reproduce the exact pre-fix pair — the
    # `default:architecture-refresh` row sitting under `## Dispatched steps` with
    # its "hybrid, classified dispatched" rationale, against
    # architecture-refresh.md's inline self-assertion.
    pre_fix_roster = '\n'.join(
        [
            '## Dispatched steps',
            '',
            '- `default:sonar-roundtrip` — → `phase-6-finalize` (no `--role`)',
            '- `default:architecture-refresh` — hybrid, classified dispatched: its '
            'Tier 0 discover + diff is deterministic inline script work, and its Tier 1 '
            're-enrichment fans out under `phase-6-finalize` per affected module — the '
            'only per-iteration parallel dispatch in the contract. The dispatching tier '
            'governs the classification, so the step carries exactly one roster row.',
            '',
            '## Inline steps',
            '',
            '- `default:push` — the single push barrier',
        ]
    )
    dispatched = set(parse_roster(pre_fix_roster, _DISPATCHED_HEADING))
    inline = set(parse_roster(pre_fix_roster, _INLINE_HEADING))
    assert 'default:architecture-refresh' in dispatched, (
        'Fixture sanity: the pre-fix roster must place architecture-refresh under '
        'the dispatched heading, or the guard proves nothing'
    )

    claims = [
        (
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md',
            'default:architecture-refresh',
            'inline',
        )
    ]

    assert _classification_mismatches(claims, dispatched, inline), (
        'Cross-document consistency detector failed to flag the known pre-fix pair '
        '(dispatched roster row vs inline executor-doc assertion)'
    )

    # Positive control — the post-fix rosters clear the detector, so it is not
    # unconditionally positive.
    post_fix_dispatched = dispatched - {'default:architecture-refresh'}
    post_fix_inline = inline | {'default:architecture-refresh'}
    assert not _classification_mismatches(claims, post_fix_dispatched, post_fix_inline)

    # And a doc classified on BOTH rosters is still a mismatch — the check is
    # "exactly one, and the right one", not merely "present somewhere".
    both = inline | {'default:architecture-refresh'}
    assert _classification_mismatches(claims, dispatched, both)


def test_step_5c_classification_table_matches_the_command_string():
    """The detection table and the command's alternation are one contract.

    The table is the routing a reader follows; the alternation is what the script
    accepts. A half-edit that changes one and not the other leaves the document
    self-contradicting, and no test read either surface before this one.
    """
    text = _SKILL_DOC.read_text(encoding='utf-8')

    rows = _termination_cause_rows(text)
    table_causes = [cause for cause, _rule in rows]

    duplicates = {cause for cause in table_causes if table_causes.count(cause) > 1}
    assert not duplicates, f"item 5c's classification table carries duplicate cause row(s): {sorted(duplicates)}"
    assert table_causes == _termination_causes_in_command(text), (
        f"item 5c's classification table lists {table_causes}, while its "
        f'`--termination-cause` alternation accepts {_termination_causes_in_command(text)} '
        '— the two surfaces are one contract and must agree in membership AND order'
    )
