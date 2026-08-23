#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard: the cloud-plan-lane build-gate vocabulary is stated once.

``.claude/skills/cloud-plan-lane/SKILL.md`` states the build gate's rule in more
than one place, and the two tokens it restates do **not** have the same number of
sites. Stating that precisely matters: an earlier draft of this docstring said the
vocabulary appears "twice", which is true of the phrase and false of the glob, and
would have told a maintainer not to look past the two sites this guard then pinned.

* the **skip phrase** appears twice — normatively in the ``## Step 5`` trigger
  table, and restated in the run-report template's ``## Build gate`` block;
* the **trigger glob** appears at the Step 5 table (normative), in the report
  block's ``git diff … -- '<glob>'`` pathspec, and at every prose site that
  declares itself a restatement of the Step 5 predicate.

Nothing inside the document keeps any of them in step, and they have drifted
before. This module extracts every statement *from the document itself* — it
hard-codes no side and no site list — and asserts they agree:

1. the skip phrase the two surfaces quote is identical;
2. the report block's ``git diff … -- '<glob>'`` pathspec is the same glob the
   Step 5 trigger table keys on;
3. every self-declaring restatement of the Step 5 predicate states that same glob.

Assertion 3 is **population-derived, not site-enumerated**: the restatements are
found by the marker phrase they use to point back at Step 5, so a restatement
added later is covered the day it is written. It carries a **cardinality floor**
rather than a mere non-emptiness check, because a self-declared population lets
the document control its own membership and can therefore shrink silently — a
marker rephrased at one of two sites would leave a non-emptiness check green with
that site unguarded, which is this module's own defect reproduced one level out.

A restatement that points back **without** using the marker is outside this
guard's reach. That boundary is real and is stated rather than left to be
discovered: the glob is also mentioned in prose *about* the gate (its
`*.py`-only rationale) at sites carrying no marker, and those are not pinned.

Two properties keep the guard from being vacuous:

* a **population assertion** per surface runs before either comparison, with a
  distinct message per surface, so an unparseable or restructured document fails
  loudly naming the surface that could not be located — instead of comparing two
  empty strings and passing;
* a **matched negative control** runs the same extractors over a synthetic
  document whose two surfaces deliberately disagree, so the guard's ability to
  fire does not depend on the live document's current state.

Deliberately NOT asserted: the surrounding prose, the trigger table's column
order, and the exact diff-command spelling. Step 5 names the bare
``git diff --name-only origin/main...HEAD`` while the report names the
``-- '*.py'``-filtered form; both are correct, so asserting command equality
would only over-fit the guard to today's markdown.

Parsing note: the ``## Build gate`` heading lives **inside** the fenced
``markdown`` report template, not at document top level, so every scan here is
fence-aware — a ``##`` line inside a fenced block is content, never a heading.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

# repo_root/test/pm-plugin-development/cloud-plan-lane/test_build_gate_lockstep.py
#                                                     ^ parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / '.claude' / 'skills' / 'cloud-plan-lane' / 'SKILL.md'

_STEP5_HEADING_PREFIX = '## Step 5'
_REPORT_HEADING = '## Report'
_BUILD_GATE_HEADING = '## Build gate'

# A prose site restates the Step 5 trigger predicate by pointing back at it in
# these words. The marker is what makes assertion 3 population-derived: the sites
# are discovered from the document, never enumerated here by line number.
_STEP5_REFERENCE_MARKER = 'predicate Step 5 uses'

# A floor on that population, not an enumeration of it. A self-declared marker
# population lets the document control its own membership, so it can SHRINK
# without notice: rephrase the marker at one of two sites and a non-emptiness
# check still passes while the rephrased site goes unguarded — the same
# n-1-of-n shape this module exists to catch, one level out. The floor is what
# makes that shrink loud. Removing a site legitimately is expected to fail here
# and be accompanied by lowering this number, which is the point: the decision
# becomes explicit instead of silent.
_MIN_STEP5_REFERRING_SITES = 2

# The token that marks a trigger-table row as the one that RUNS the build. Both
# row identifications key off it — the build row by its presence, the skip row by
# its absence — so the two are symmetric rather than one being positional.
_BUILD_WRAPPER = './pw'

_QUOTED = re.compile(r'"([^"]+)"')
_BACKTICKED = re.compile(r'`([^`]+)`')
# The pathspec the report's git-diff spelling filters on: the quoted token after
# a free-standing ``--``. ``--name-only`` is not matched, because ``--\s+``
# requires whitespace directly after the double dash.
_DIFF_PATHSPEC = re.compile(r"git diff\b[^\n]*?--\s+(['\"])(?P<glob>[^'\"]+)\1")


class Step5Surface(NamedTuple):
    """What the Step 5 trigger table states, or ``None`` where nothing parsed.

    ``quoted_count`` is the number of quoted tokens the skip row offered. It is
    carried so ambiguity is distinguishable from absence: both leave
    ``skip_phrase`` unset, but they are different failures and the population
    assertion says which.
    """

    section_found: bool
    trigger_glob: str | None
    skip_phrase: str | None
    quoted_count: int


class ReportSurface(NamedTuple):
    """What the report template's ``## Build gate`` block states.

    ``quoted_count`` carries the same ambiguity-vs-absence discriminator as
    ``Step5Surface``.
    """

    section_found: bool
    block_found: bool
    diff_pathspec: str | None
    skip_phrase: str | None
    quoted_count: int


class ReferringSite(NamedTuple):
    """One prose site that declares itself a restatement of the Step 5 predicate."""

    line_number: int
    glob: str | None
    text: str


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith('```')


def _top_level_sections(document: str) -> list[tuple[str, list[str]]]:
    """Split ``document`` into ``(heading, body_lines)`` pairs, fence-aware.

    A ``## `` line inside a fenced code block is content, not a heading — which
    is exactly the case the report template presents.
    """
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    heading: str | None = None
    body: list[str] = []

    for line in document.splitlines():
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith('## '):
            if heading is not None:
                sections.append((heading, body))
            heading = line.rstrip()
            body = []
            continue
        if heading is not None:
            body.append(line)

    if heading is not None:
        sections.append((heading, body))
    return sections


def _section_body(document: str, heading_matches: Callable[[str], bool]) -> list[str] | None:
    """Body lines of the first top-level section whose heading matches."""
    for heading, body in _top_level_sections(document):
        if heading_matches(heading):
            return body
    return None


def _fenced_blocks(lines: list[str]) -> list[list[str]]:
    """Contents of each fenced code block in ``lines``, fence markers excluded."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if _is_fence(line):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def _subsection(lines: list[str], heading: str) -> list[str]:
    """Lines under ``heading`` up to the next ``## `` line (heading excluded)."""
    out: list[str] = []
    collecting = False
    for line in lines:
        if line.rstrip() == heading:
            collecting = True
            continue
        if collecting and line.startswith('## '):
            break
        if collecting:
            out.append(line)
    return out


def _paragraph_containing(lines: list[str], pattern: re.Pattern[str]) -> str | None:
    """The blank-line-delimited paragraph whose text matches ``pattern``.

    Scoping to a paragraph is what makes the skip-phrase binding semantic rather
    than positional. The ``## Build gate`` block states two different things in
    two paragraphs — the build verdict and its skip alternative in one, the
    stale-base re-verification in another — and each quotes a phrase. A
    block-wide scan therefore sees two tokens and must either take the first
    (positional, the defect) or refuse (a false ambiguity on a correct
    document). The skip phrase is the alternative outcome of the SAME sentence
    as the diff pathspec, so the paragraph carrying that pathspec is the scope
    that identifies it by what it is.
    """
    paragraph: list[str] = []
    for line in [*lines, '']:
        if line.strip():
            paragraph.append(line)
            continue
        if paragraph:
            text = '\n'.join(paragraph)
            if pattern.search(text):
                return text
            paragraph = []
    return None


def _table_rows(lines: list[str]) -> list[list[str]]:
    """Markdown table rows as stripped cell lists, skipping separator rows."""
    rows: list[list[str]] = []
    in_fence = False
    for line in lines:
        if _is_fence(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if cells and all(re.fullmatch(r':?-{2,}:?', cell) for cell in cells if cell):
            continue
        rows.append(cells)
    return rows


def extract_step5_trigger_surface(document: str) -> Step5Surface:
    """Pure extractor: the Step 5 trigger table's glob and its skip phrase.

    Rows are identified by what they *do*, not by their wording: the build row is
    the one whose outcome cell names the build wrapper, and the skip row is the
    one whose outcome cell quotes a phrase to record while NOT naming it.

    The quoted token is taken only when the skip row offers exactly one. Taking
    the first of several would be a positional binding wearing a semantic label:
    a decoy quoted token would silently become the compared vocabulary. Ambiguity
    is reported through ``quoted_count`` and refused, never guessed.
    """
    body = _section_body(document, lambda heading: heading.startswith(_STEP5_HEADING_PREFIX))
    if body is None:
        return Step5Surface(
            section_found=False, trigger_glob=None, skip_phrase=None, quoted_count=0
        )

    trigger_glob: str | None = None
    quoted: list[str] = []
    for cells in _table_rows(body):
        if len(cells) < 2:
            continue
        trigger_cell, outcome_cell = cells[0], cells[1]
        runs_the_build = _BUILD_WRAPPER in outcome_cell
        if trigger_glob is None and runs_the_build:
            glob_match = _BACKTICKED.search(trigger_cell)
            if glob_match:
                trigger_glob = glob_match.group(1)
        # The skip row is identified by BOTH halves of what it does: it quotes a
        # phrase to record AND it does not run the build. Without the second
        # half the binding is positional in disguise — it would take the first
        # row quoting anything, so a quoted token added to the build row would
        # silently bind skip_phrase to that row while every assertion stayed
        # green. The build row above is already identified by what it does; this
        # keeps the two rows symmetric, which is what the docstring claims.
        if not runs_the_build:
            quoted.extend(_QUOTED.findall(outcome_cell))

    return Step5Surface(
        section_found=True,
        trigger_glob=trigger_glob,
        skip_phrase=quoted[0] if len(quoted) == 1 else None,
        quoted_count=len(quoted),
    )


def extract_report_build_gate_surface(document: str) -> ReportSurface:
    """Pure extractor: the report template's ``## Build gate`` pathspec and phrase.

    The block is located *inside* the ``## Report`` section's fenced template, so
    the fenced block carrying a ``## Build gate`` line is selected explicitly
    rather than by a top-level heading scan.

    The skip phrase is read from the paragraph carrying the diff pathspec — the
    verdict sentence whose alternative outcome it is — and only when that
    paragraph offers exactly one quoted token. This side was the last positional
    binding in the module: taking the first quoted token in the whole block let a
    decoy inserted ahead of the real phrase become the compared vocabulary with
    every assertion still green. Scoping to the block was not enough, because the
    block legitimately quotes a second phrase in its stale-base paragraph.
    """
    body = _section_body(document, lambda heading: heading.rstrip() == _REPORT_HEADING)
    if body is None:
        return ReportSurface(
            section_found=False,
            block_found=False,
            diff_pathspec=None,
            skip_phrase=None,
            quoted_count=0,
        )

    block: list[str] | None = None
    for fenced in _fenced_blocks(body):
        if any(line.rstrip() == _BUILD_GATE_HEADING for line in fenced):
            block = _subsection(fenced, _BUILD_GATE_HEADING)
            break
    if block is None:
        return ReportSurface(
            section_found=True,
            block_found=False,
            diff_pathspec=None,
            skip_phrase=None,
            quoted_count=0,
        )

    block_text = '\n'.join(block)
    pathspec_match = _DIFF_PATHSPEC.search(block_text)
    verdict_paragraph = _paragraph_containing(block, _DIFF_PATHSPEC)
    quoted = _QUOTED.findall(verdict_paragraph) if verdict_paragraph is not None else []
    return ReportSurface(
        section_found=True,
        block_found=True,
        diff_pathspec=pathspec_match.group('glob') if pathspec_match else None,
        skip_phrase=quoted[0] if len(quoted) == 1 else None,
        quoted_count=len(quoted),
    )


def extract_step5_referring_globs(document: str) -> list[ReferringSite]:
    """Pure extractor: every prose site restating the Step 5 trigger predicate.

    Sites are found by the marker phrase they use to point back at Step 5, so the
    population comes from the document rather than from a list maintained here.
    A site whose glob could not be extracted is returned with ``glob=None`` rather
    than dropped — a silently skipped site is exactly the hole this guard closes.
    """
    sites: list[ReferringSite] = []
    for line_number, line in enumerate(document.splitlines(), 1):
        if _STEP5_REFERENCE_MARKER not in line:
            continue
        glob_match = _BACKTICKED.search(line)
        sites.append(
            ReferringSite(
                line_number=line_number,
                glob=glob_match.group(1) if glob_match else None,
                text=line.strip(),
            )
        )
    return sites


def _read_live_document() -> str:
    assert _SKILL_PATH.is_file(), (
        f'The cloud-plan-lane contract is missing from the repository: {_SKILL_PATH}. '
        'This guard pins two surfaces of that document against each other and cannot '
        'run without it.'
    )
    return _SKILL_PATH.read_text(encoding='utf-8')


def _assert_population(step5: Step5Surface, report: ReportSurface, source: str) -> None:
    """Both surfaces located and both tokens extracted — one message per surface."""
    assert step5.section_found, (
        f'Surface 1 NOT LOCATED in {source}: no top-level "{_STEP5_HEADING_PREFIX}" heading. '
        'The build-gate trigger table could not be reached, so nothing was compared.'
    )
    assert step5.trigger_glob, (
        f'Surface 1 token NOT EXTRACTED in {source}: the Step 5 trigger table has no row whose '
        'outcome cell names "./pw" with a backticked glob in its trigger cell.'
    )
    assert step5.quoted_count == 1, (
        f'Surface 1 token AMBIGUOUS in {source}: the Step 5 skip row offers '
        f'{step5.quoted_count} quoted tokens, not exactly one, so which one is the skip phrase '
        'cannot be decided. Taking the first would be a positional binding wearing a semantic '
        'label — a decoy quoted token would silently become the compared vocabulary. Refusing '
        'to guess.'
        if step5.quoted_count > 1
        else f'Surface 1 token NOT EXTRACTED in {source}: the Step 5 trigger table has no row '
        'that quotes a "…" skip phrase to record WITHOUT also naming the build wrapper.'
    )
    assert step5.skip_phrase, (
        f'Surface 1 token NOT EXTRACTED in {source}: the Step 5 skip phrase is unset despite a '
        'unique quoted token — the extractor contract is broken, not the document.'
    )
    assert report.section_found, (
        f'Surface 2 NOT LOCATED in {source}: no top-level "{_REPORT_HEADING}" heading. '
        'The run-report template could not be reached, so nothing was compared.'
    )
    assert report.block_found, (
        f'Surface 2 NOT LOCATED in {source}: no fenced block under "{_REPORT_HEADING}" carries a '
        f'"{_BUILD_GATE_HEADING}" heading. The report template may have been restructured.'
    )
    assert report.diff_pathspec, (
        f'Surface 2 token NOT EXTRACTED in {source}: the "{_BUILD_GATE_HEADING}" block states no '
        "git-diff pathspec of the form -- '<glob>'."
    )
    assert report.quoted_count == 1, (
        f'Surface 2 token AMBIGUOUS in {source}: the verdict paragraph of the '
        f'"{_BUILD_GATE_HEADING}" block offers {report.quoted_count} quoted tokens, not exactly '
        'one, so which one is the skip phrase cannot be decided. A decoy inserted ahead of the '
        'real phrase would otherwise become the compared vocabulary with every assertion still '
        'green. Refusing to guess.'
        if report.quoted_count > 1
        else f'Surface 2 token NOT EXTRACTED in {source}: the "{_BUILD_GATE_HEADING}" block has '
        'no paragraph that carries both the diff pathspec and a quoted "…" skip phrase.'
    )
    assert report.skip_phrase, (
        f'Surface 2 token NOT EXTRACTED in {source}: the report skip phrase is unset despite a '
        'unique quoted token — the extractor contract is broken, not the document.'
    )


# A matched negative control: same structure as the live document, with the two
# surfaces deliberately disagreeing on BOTH couplings this guard asserts.
_DIVERGING_DOCUMENT = '''\
---
name: synthetic-negative-control
---

# Synthetic lane document

## Step 5 — Build gate (conditional)

Two gates, because the quality gate and the test suite have different trigger surfaces:

| Changed | Run |
|---|---|
| Any `*.py` | `./pw verify` (quality gate **and** tests) |
| No `*.py` | Nothing locally — record "alpha phrase, build skipped" |

```bash
./pw verify
```

## Step 6 — Something else

Prose that must not be mistaken for the trigger table.

When a commit touches any `*.md` — the **same** predicate Step 5 uses to decide whether to
build — run the quality gate first.

## Report

```text
doc/plans/{epic}/{plan-name}/report-NN.md
```

```markdown
# Run report

## Skills loaded
…

## Build gate
The `git diff --name-only origin/main...HEAD -- '*.md'` verdict, and the build result — or
"beta phrase, build skipped".

Then the stale-base re-verification: a zero count is recorded as the measurement it is
("base current at the gate").

## Findings
…
```

## Rules that outrank convenience

- Nothing here.
'''


def test_both_build_gate_surfaces_are_located_in_the_live_document() -> None:
    """Population guard: both surfaces parse and both tokens are non-empty."""
    document = _read_live_document()

    step5 = extract_step5_trigger_surface(document)
    report = extract_report_build_gate_surface(document)

    _assert_population(step5, report, str(_SKILL_PATH))


def test_step5_and_report_template_state_the_same_skip_phrase() -> None:
    """The normative Step 5 phrase and its report restatement must be identical."""
    document = _read_live_document()

    step5 = extract_step5_trigger_surface(document)
    report = extract_report_build_gate_surface(document)

    _assert_population(step5, report, str(_SKILL_PATH))
    assert step5.skip_phrase == report.skip_phrase, (
        'The cloud-plan-lane build-gate skip phrase has drifted between its two surfaces in '
        f'{_SKILL_PATH}. Step 5 is normative; the report template restates it, so the report '
        'template is the side that moves.\n'
        f'  Surface 1 — "{_STEP5_HEADING_PREFIX}" trigger table (NORMATIVE): "{step5.skip_phrase}"\n'
        f'  Surface 2 — "{_REPORT_HEADING}" template, "{_BUILD_GATE_HEADING}" block: '
        f'"{report.skip_phrase}"'
    )


def test_report_diff_pathspec_matches_the_step5_trigger_glob() -> None:
    """The report's git-diff pathspec must be the glob Step 5 keys the gate on."""
    document = _read_live_document()

    step5 = extract_step5_trigger_surface(document)
    report = extract_report_build_gate_surface(document)

    _assert_population(step5, report, str(_SKILL_PATH))
    assert report.diff_pathspec == step5.trigger_glob, (
        'The cloud-plan-lane build-gate pathspec has drifted from the trigger glob in '
        f'{_SKILL_PATH}: the report tells a run to derive its verdict from a diff filtered on a '
        'glob the Step 5 table does not key on, so the recorded verdict answers a different '
        'question than the gate asked.\n'
        f'  Surface 1 — "{_STEP5_HEADING_PREFIX}" trigger glob: "{step5.trigger_glob}"\n'
        f'  Surface 2 — "{_BUILD_GATE_HEADING}" diff pathspec: "{report.diff_pathspec}"'
    )


def test_every_step5_referring_site_states_the_same_trigger_glob() -> None:
    """Prose restatements of the Step 5 predicate must state Step 5's own glob.

    The Step 5 table and the report block are pinned to each other by the two
    tests above. This one covers the remaining sites: the prose that says it is
    re-using Step 5's predicate. Without it, widening the glob at Step 5 and the
    report leaves those sites stating the old predicate while the guard stays
    green — the n-1-of-n shape this document exists to prevent.
    """
    document = _read_live_document()

    step5 = extract_step5_trigger_surface(document)
    sites = extract_step5_referring_globs(document)

    assert step5.section_found and step5.trigger_glob, (
        f'Surface 1 NOT LOCATED in {_SKILL_PATH}: the Step 5 trigger glob could not be '
        'extracted, so the referring sites had nothing to be compared against.'
    )
    assert len(sites) >= _MIN_STEP5_REFERRING_SITES, (
        f'Population SHRANK in {_SKILL_PATH}: {len(sites)} line(s) carry the marker '
        f'"{_STEP5_REFERENCE_MARKER}", below the floor of {_MIN_STEP5_REFERRING_SITES}. '
        'A non-emptiness check would have passed here and left the missing site unguarded, so '
        'the floor is what makes this loud. Either the marker wording drifted at a site that '
        'still restates the Step 5 predicate — the likely case, and the site is now unguarded — '
        'or a restatement was deliberately removed, in which case lower the floor in the same '
        'change so the decision is recorded rather than silent.\n'
        + '\n'.join(f'  found line {site.line_number}: {site.text}' for site in sites)
    )

    unextracted = [site for site in sites if not site.glob]
    assert not unextracted, (
        f'Token NOT EXTRACTED in {_SKILL_PATH}: a site declares itself a restatement of the '
        'Step 5 predicate but states no backticked glob, so it could not be compared:\n'
        + '\n'.join(f'  line {site.line_number}: {site.text}' for site in unextracted)
    )

    mismatched = [site for site in sites if site.glob != step5.trigger_glob]
    assert not mismatched, (
        f'The cloud-plan-lane trigger predicate has drifted between its sites in {_SKILL_PATH}. '
        'Step 5 is normative; a prose site claiming to use "the same predicate" must state the '
        'same glob, or it silently sends a run down a different branch than the gate defines.\n'
        f'  Step 5 trigger table (NORMATIVE): "{step5.trigger_glob}"\n'
        + '\n'.join(
            f'  line {site.line_number} states "{site.glob}": {site.text}' for site in mismatched
        )
    )


def test_negative_control_referring_site_divergence_is_detected() -> None:
    """Matched negative control for the referring-site assertion.

    The synthetic document carries a prose site that claims Step 5's predicate
    while stating a different glob. Both values are asserted positively first, so
    the control proves the extractor reached the site rather than passing on a
    pair of ``None``s.
    """
    step5 = extract_step5_trigger_surface(_DIVERGING_DOCUMENT)
    sites = extract_step5_referring_globs(_DIVERGING_DOCUMENT)

    assert step5.trigger_glob == '*.py'
    assert len(sites) == 1
    assert sites[0].glob == '*.md'

    mismatched = [site for site in sites if site.glob != step5.trigger_glob]
    assert mismatched, (
        'Negative control did not fire: the referring-site comparison agreed on a document whose '
        'prose site deliberately states a different glob than its Step 5 table, so the live '
        'referring-site assertion cannot be trusted to fail on real drift.'
    )


# A control for the row-identification asymmetry: the BUILD row carries a quoted
# token. A skip-phrase binding that took the first row quoting anything would
# bind here — to the build row — and stay green, because both surfaces would then
# agree on the wrong value.
_QUOTED_BUILD_ROW_DOCUMENT = _DIVERGING_DOCUMENT.replace(
    '| Any `*.py` | `./pw verify` (quality gate **and** tests) |',
    '| Any `*.py` | `./pw verify` — records "build ran, not skipped" on success |',
)


def test_skip_phrase_binds_to_the_skip_row_even_when_the_build_row_is_quoted() -> None:
    """The skip row is identified by what it does, not by being quoted first.

    Both halves are load-bearing: quoting a phrase AND not running the build. A
    binding that used only the first half would be positional in disguise, and
    this control is the document that exposes it — the build row is quoted and
    appears first, so a positional binding returns the build row's token.
    """
    surface = extract_step5_trigger_surface(_QUOTED_BUILD_ROW_DOCUMENT)

    assert surface.section_found, 'Control document no longer parses; the replace() target drifted.'
    assert surface.trigger_glob == '*.py', (
        'Control document no longer yields the build row; the replace() target drifted.'
    )
    assert surface.skip_phrase == 'alpha phrase, build skipped', (
        'skip_phrase bound to the wrong row: it took a quoted token from a row that RUNS the '
        f'build rather than the row that records a skip. Got "{surface.skip_phrase}". The skip '
        'row must be identified by quoting a phrase AND not naming the build wrapper.'
    )


# Controls for the decoy-token path: an extra quoted token is inserted AHEAD of
# the real skip phrase on each surface. A first-match binding would silently
# return the decoy; the uniqueness rule returns None and reports the count.
_DECOY_IN_SKIP_ROW_DOCUMENT = _DIVERGING_DOCUMENT.replace(
    '| No `*.py` | Nothing locally — record "alpha phrase, build skipped" |',
    '| No `*.py` | Nothing locally (see "the deferral note") — record "alpha phrase, build skipped" |',
)

_DECOY_IN_REPORT_BLOCK_DOCUMENT = _DIVERGING_DOCUMENT.replace(
    '## Build gate\nThe',
    '## Build gate\nSee "the deferral note" first. The',
)


def test_a_decoy_quoted_token_makes_the_skip_row_ambiguous_not_wrong() -> None:
    """A second quoted token in the skip row is refused, not silently preferred."""
    surface = extract_step5_trigger_surface(_DECOY_IN_SKIP_ROW_DOCUMENT)

    assert surface.quoted_count == 2, (
        'Control document drifted: the skip row must offer two quoted tokens to exercise the '
        f'ambiguity path, but {surface.quoted_count} were found.'
    )
    assert surface.skip_phrase is None, (
        'Ambiguity was resolved by guessing: skip_phrase bound to '
        f'"{surface.skip_phrase}" while two quoted tokens were present. A first-match binding '
        'would return the decoy here and every downstream comparison would run on it.'
    )


def test_a_decoy_quoted_token_makes_the_report_block_ambiguous_not_wrong() -> None:
    """A second quoted token in the report block is refused, not silently preferred."""
    surface = extract_report_build_gate_surface(_DECOY_IN_REPORT_BLOCK_DOCUMENT)

    assert surface.block_found, 'Control document drifted: the Build gate block no longer parses.'
    assert surface.quoted_count == 2, (
        'Control document drifted: the report block must offer two quoted tokens to exercise the '
        f'ambiguity path, but {surface.quoted_count} were found.'
    )
    assert surface.skip_phrase is None, (
        'Ambiguity was resolved by guessing: skip_phrase bound to '
        f'"{surface.skip_phrase}" while two quoted tokens were present. This surface was the last '
        'positional binding in the module; a decoy ahead of the real phrase would become the '
        'compared vocabulary with every assertion still green.'
    )


def test_negative_control_a_shrunk_marker_population_is_below_the_floor() -> None:
    """Matched negative control for the cardinality floor.

    A non-emptiness check passes on any population of one, so the floor is only
    meaningful if a shrunk population demonstrably falls below it. The synthetic
    document carries exactly one marker site — the state a marker rephrase at one
    of two live sites would produce — and it is asserted to be under the floor.
    """
    sites = extract_step5_referring_globs(_DIVERGING_DOCUMENT)

    assert len(sites) == 1, (
        'Control document changed: it must carry exactly one marker site to stand in for a '
        f'population that shrank, but {len(sites)} were found.'
    )
    assert len(sites) < _MIN_STEP5_REFERRING_SITES, (
        'Cardinality floor is inert: a one-site population does not fall below the floor of '
        f'{_MIN_STEP5_REFERRING_SITES}, so a marker rephrase that silently dropped a site would '
        'pass the live assertion. The floor must exceed one to catch the shape it targets.'
    )


def test_negative_control_diverging_document_makes_both_comparisons_fail() -> None:
    """Matched negative control: the guard fires on a document that disagrees.

    The same extractors run over a synthetic document whose two surfaces state
    different phrases and different globs. Both are asserted positively — the
    control proves the extractors reached both surfaces — and then the two
    comparisons the live tests make are asserted to be false.
    """
    step5 = extract_step5_trigger_surface(_DIVERGING_DOCUMENT)
    report = extract_report_build_gate_surface(_DIVERGING_DOCUMENT)

    _assert_population(step5, report, 'the synthetic diverging control document')

    assert step5.skip_phrase == 'alpha phrase, build skipped'
    assert report.skip_phrase == 'beta phrase, build skipped'
    assert step5.trigger_glob == '*.py'
    assert report.diff_pathspec == '*.md'

    assert step5.skip_phrase != report.skip_phrase, (
        'Negative control did not fire: the phrase comparison agreed on a document whose two '
        'surfaces deliberately disagree, so the live phrase assertion cannot be trusted to fail '
        'on real drift.'
    )
    assert report.diff_pathspec != step5.trigger_glob, (
        'Negative control did not fire: the pathspec comparison agreed on a document whose two '
        'surfaces deliberately disagree, so the live pathspec assertion cannot be trusted to fail '
        'on real drift.'
    )
