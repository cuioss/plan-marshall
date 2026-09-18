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


def test_every_registered_step_is_classified_exactly_once():
    # Arrange
    registered = _registered_steps()
    dispatched = _roster(_DISPATCHED_HEADING)
    inline = _roster(_INLINE_HEADING)

    # Act
    classified = set(dispatched) | set(inline)

    # Assert — no registered step is unclassified, and no roster row is a ghost.
    unclassified = registered - classified
    assert not unclassified, (
        f'Registered finalize steps missing a dispatched/inline classification '
        f'in dispatch-inline-split.md: {sorted(unclassified)}'
    )
    ghosts = classified - registered
    assert not ghosts, f'Roster rows that name no registered finalize step: {sorted(ghosts)}'
    assert classified == registered


def test_both_rosters_are_non_empty():
    # Guards the parser itself: a heading rename that silently yields an empty
    # roster would otherwise make the closure assertions vacuous.
    assert _roster(_DISPATCHED_HEADING)
    assert _roster(_INLINE_HEADING)


def test_skill_dispatch_section_carries_no_step_count_claim():
    text = _SKILL_DOC.read_text(encoding='utf-8')
    section = '\n'.join(section_lines(text, _SKILL_SECTION_HEADING))

    hits = _count_claims(section)

    assert not hits, f'Step-count claim(s) reintroduced into the SKILL.md "{_SKILL_SECTION_HEADING}" section: {hits}'


def test_count_claim_patterns_do_not_fire_on_ordinary_cardinal_prose():
    """Negative control: the widening must not become unconditionally positive.

    Admitting spelled-out cardinals risks turning the detector into one that
    flags any prose containing a number word. These samples carry a cardinal in
    an ordinary sense with no step-count claim — including the replacement prose
    this deliverable actually wrote, so the widening is verified not to condemn
    its own fix.
    """
    benign_samples = [
        'The dispatcher retries three times before escalating to the operator.',
        'Two shapes qualify: a step that records a pass/fail verdict over the '
        'live worktree tree, and a settle-stage step whose edits land in the tree.',
        'The comparison covers all three supersession mechanisms in scope.',
        'Resolve the four required fields before invoking the persist call.',
    ]

    for sample in benign_samples:
        assert not _count_claims(sample), (
            f'Count-claim sweep fired on benign cardinal prose: {sample!r}. A '
            'detector that flags ordinary text must be suppressed to stay green, '
            'which is worse than no detector.'
        )


def test_the_seam_sweep_population_reaches_past_the_skill_document():
    # The population floor for (e). The sweep used to read ONE file and blank
    # everything outside one of its sections, so two real dispatch branches in the
    # executor docs were invisible to it whatever shape they took. These assertions
    # are what redden if the walk silently collapses back to that scope — a shrunken
    # population reports clean, and there is no hardcoded file list to notice it.
    corpus = _seam_sweep_corpus()
    spawn_bearing = _spawn_bearing_documents(corpus)

    assert len(corpus) > 1, (
        f'the (e) walk over {_SKILL_DIR} found {len(corpus)} document(s) — the sweep '
        'has collapsed back to a single file'
    )
    assert spawn_bearing, (
        f'no `Task:` spawn found in ANY of the {len(corpus)} documents under '
        f'{_SKILL_DIR} — both (e) assertions below would be vacuous'
    )
    beyond_skill_doc = [rel for rel in spawn_bearing if rel != 'SKILL.md']
    assert beyond_skill_doc, (
        f'every `Task:` spawn under {_SKILL_DIR} is inside SKILL.md '
        f'(spawn-bearing documents: {spawn_bearing}). The widening past SKILL.md is '
        'what makes an out-of-file dispatch branch visible; if the skill genuinely '
        'has no such branch left, re-derive this floor rather than deleting it — a '
        'silently single-file sweep is exactly the blind spot it replaced.'
    )


def test_the_dispatch_site_roster_is_derived_from_a_real_tree():
    """(h)'s INPUT is published, not assumed.

    Every figure below is derived from this walk, so a root that resolved to the
    wrong place would make the roster a shrunken one while the equality assertion
    stayed green over it.
    """
    assert _PLAN_MARSHALL_SKILLS.is_dir(), f'the plan-marshall skills tree root does not exist: {_PLAN_MARSHALL_SKILLS}'

    walked = _plan_marshall_markdown_docs()

    assert len(walked) > 50, (
        f'the (h) walk over {_PLAN_MARSHALL_SKILLS} opened {len(walked)} markdown '
        'document(s). The plan-marshall skills tree carries far more, so the walk is '
        'reading the wrong root and the derived roster below is not the real one.'
    )


def test_the_dispatch_site_roster_equals_the_seam_emitting_set():
    """(h) The two sets are EQUAL — every document that dispatches also emits.

    A roster member that carries no ``--workflow``-bearing resolve dispatches with no
    audit trail at all: the seam emits the ``[DISPATCH]`` line as a side effect of the
    resolve, so a bare resolve leaves the firing unrecorded and the retrospective audit
    cannot say which variant ran (`dispatch-logging.md` § Placement contract).
    """
    roster = set(_dispatch_site_roster())
    emitting = set(_seam_emitting_dispatch_sites())

    silent = sorted(str(doc.relative_to(_PLAN_MARSHALL_SKILLS)) for doc in roster - emitting)

    assert not silent, (
        f'{len(silent)} of {len(roster)} derived dispatch-site document(s) carry a '
        f'`Task: plan-marshall:` spawn but no `effort resolve-target … --workflow` '
        f'resolve of their own, so every dispatch they document leaves no [DISPATCH] '
        f'record: {silent}'
    )


def test_the_roster_detector_ignores_a_non_execution_context_spawn(tmp_path):
    """Negative control for the roster detector's documented boundary.

    A ``Task:`` naming a non-plan-marshall ``subagent_type`` is not an
    execution-context dispatch, so ``dispatch-logging.md`` does not govern it and it
    must not enter the roster — otherwise (h) would demand a seam resolve from a
    document the seam contract never reached, and the only way back to green would be
    an exclusion list.
    """
    foreign = tmp_path / 'builder_dispatch.md'
    foreign.write_text(
        '```text\nTask:\n  subagent_type: pm-dev-builder:maven-builder\n  prompt: |\n    Execute mvn verify\n```\n',
        encoding='utf-8',
    )

    assert not _TASK_SPAWN.search(foreign.read_text(encoding='utf-8'))


def test_seam_resolve_detector_fires_on_a_bare_resolve_beside_a_decoy_workflow():
    """The discriminating arm: a bare resolve does NOT borrow a neighbour's --workflow.

    This is the shape the window-wide token search could not see. The branch spawns
    under a genuinely bare ``effort resolve-target`` — a pure query that emits no
    ``[DISPATCH]`` line — while an unrelated command earlier in the SAME lookback
    window carries ``--workflow``. Searched independently, both tokens are present
    and the spawn reports paired; read per invocation, the resolve is bare and the
    spawn is unpaired.
    """
    decoyed = '\n'.join(
        [
            '      (1) Compose the manifest (unrelated command, carries --workflow):',
            '          python3 .plan/execute-script.py '
            'plan-marshall:manage-execution-manifest:manage-execution-manifest \\',
            '            compose --plan-id {plan_id} \\',
            '            --workflow plan-marshall:phase-6-finalize/workflow/{other}.md',
            '      (2) Resolve the level-bound target (BARE — no --workflow):',
            '          python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \\',
            '            effort resolve-target --phase phase-6-finalize [--role <subkey>]',
            '      (3) Dispatch:',
            '          Task: plan-marshall:{target}',
        ]
    )

    # Fixture sanity — both tokens ARE in the window, which is precisely why the
    # independent search passed this shape. Stated so the arm cannot silently stop
    # being the discriminating one.
    window = '\n'.join(decoyed.splitlines()[:-1])
    assert _SEAM_RESOLVE.search(window) and _WORKFLOW_FLAG.search(window), (
        'Fixture sanity: the decoy arm must carry BOTH tokens in the lookback '
        'window, or it does not discriminate the per-invocation check from the '
        'window-wide one'
    )

    assert _spawns_missing_seam_resolve(decoyed), (
        'Seam-resolve detector failed to flag a spawn under a BARE resolve whose '
        'lookback window carries an unrelated --workflow-bearing command — the '
        'window-wide blind spot: a pure query emits no [DISPATCH] line, so this '
        'spawn has no dispatch record whatever a neighbouring command passes'
    )

    # Positive control — moving --workflow ONTO the resolve pairs the same spawn, so
    # the per-invocation read is not unconditionally negative.
    paired = decoyed.replace(
        '            effort resolve-target --phase phase-6-finalize [--role <subkey>]',
        '            effort resolve-target --phase phase-6-finalize [--role <subkey>] \\\n'
        '            --workflow plan-marshall:phase-6-finalize/workflow/{name}.md',
    )
    assert not _spawns_missing_seam_resolve(paired)


def test_touched_step_docs_agree_with_the_roster_classification():
    # Arrange — the claims are READ from the docs, not asserted about a named
    # step, so a second doc gaining a self-classification is covered for free.
    #
    # ⛔ A green result here is NOT whole-registry coverage. It says every doc that
    # STATES a classification agrees with the roster, over a comparison population
    # the report header names (see the module docstring, "What (f) actually
    # compares"). Do not size this guard from its name.
    claims, _findings = _step_doc_claims()
    assert claims, (
        'No step doc in the cross-document consistency population declares its own '
        'dispatched/inline classification — the assertion would be vacuous'
    )

    # Act
    mismatches = _classification_mismatches(claims, set(_roster(_DISPATCHED_HEADING)), set(_roster(_INLINE_HEADING)))

    # Assert
    assert not mismatches, (
        f'Step doc(s) whose own classification contradicts dispatch-inline-split.md — '
        f'the roster is the single source of truth and the executor doc states the '
        f'reason, so the two must agree: {mismatches}'
    )


def test_registry_absence_is_collected_rather_than_raised():
    # Mutation guard for the downgrade: drive the pure classifier with a synthetic
    # doc that self-classifies under a name no registry knows. The pre-fix helper
    # raised here; the fixed one returns a finding naming registry absence, and the
    # positive control below shows it still produces a claim for a registered name.
    unregistered = (
        '---\n'
        'name: finalize-step-not-in-any-registry\n'
        'order: 99\n'
        '---\n\n'
        'This step is **inline** because it is cheap to run in the main context.\n'
    )
    registered = {'default:architecture-refresh'}

    claim, finding = _classify_discovered_doc('synthetic.md', unregistered, registered)

    assert claim is None
    assert finding is not None and 'registry absence' in finding, (
        f'a self-classifying doc resolving to no registered key produced {finding!r} '
        'instead of a registry-absence finding'
    )

    # Positive control — a doc whose name DOES resolve still yields a claim and no
    # finding, so the downgrade is not unconditionally a finding.
    known = (
        '---\n'
        'name: architecture-refresh\n'
        '---\n\n'
        'This step is **inline** (executed directly inside the finalize main context).\n'
    )
    claim, finding = _classify_discovered_doc('architecture-refresh.md', known, registered)
    assert claim == ('architecture-refresh.md', 'default:architecture-refresh', 'inline')
    assert finding is None

    # And a doc that states no classification contributes neither.
    silent = '---\nname: architecture-refresh\n---\n\nNo classification sentence here.\n'
    assert _classify_discovered_doc('architecture-refresh.md', silent, registered) == (
        None,
        None,
    )


def test_builtin_dispatch_table_lists_the_previously_missing_steps():
    text = _SKILL_DOC.read_text(encoding='utf-8')

    assert '| `default:pre-push-quality-gate` |' in text
    assert '| `default:finalize-step-preference-emitter` |' in text


def test_step_5c_routes_a_findings_bearing_loop_back_away_from_error():
    """The deliverable itself: which outcome each cause is detected from.

    This is the independent oracle — the routing literals come from the
    specification, not from the document — so a document that renames or reorders
    both of its own surfaces consistently still reddens here.
    """
    text = _SKILL_DOC.read_text(encoding='utf-8')
    rules = dict(_termination_cause_rows(text))

    missing: list[str] = []
    for cause, required_tokens in _TERMINATION_CAUSE_ROUTING.items():
        rule = rules.get(cause)
        if rule is None:
            missing.append(f'{cause}: no detection row at all')
            continue
        for token in required_tokens:
            if token not in rule:
                missing.append(f'{cause}: detection rule does not state {token!r}')

    assert not missing, (
        "item 5c's classification contract no longer routes as specified — a "
        'findings-bearing `loop_back` stamped `error` grades a working gate as a '
        f'defect, which is the silent revert this test exists to catch: {missing}'
    )

    assert _CROSS_LEDGER_SENTENCE in text, (
        f'item 5e no longer states that its `loop_back` outcome is {_CROSS_LEDGER_SENTENCE!r} '
        '— without it the manifest execution log and the dispatch-boundary ledger '
        'agree only by coincidence'
    )


def test_head_dependent_region_carries_no_step_count_claim():
    """(c) No step-count claim survives in the SKILL.md HEAD-dependent region.

    The roster-document sweep cannot see prose that lives in SKILL.md § "Step 3:
    Execute Step Pipeline" — a count claim reintroduced there would pass every
    roster-scoped check while restating the exact shape (c) exists to remove.
    """
    region = _head_dependent_region()
    hits = _count_claims(region)
    assert not hits, f'Step-count claim(s) reintroduced into the HEAD-dependent region: {hits}'


def test_no_unpaired_seam_spawn_survives_on_the_real_corpus():
    """(e) Every ``Task:`` spawn on the real corpus is preceded by its seam resolve.

    The synthetic-shape tests prove the detector fires; this test proves the
    tree is clean — a dispatch branch added without its resolve-target lookup
    reddens here rather than shipping a record-less dispatch.
    """
    corpus = _seam_sweep_corpus()
    assert corpus, 'Seam sweep corpus resolved empty — the check would pass vacuously.'
    unpaired = [f'{rel}: {hit}' for rel, text in corpus for hit in _spawns_missing_seam_resolve(text)]
    assert not unpaired, f'Task spawn(s) with no preceding resolve-target seam lookup: {unpaired}'
