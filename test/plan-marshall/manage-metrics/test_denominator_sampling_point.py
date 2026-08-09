#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the persisted denominators and their sampling-point discriminator.

``metrics.toon`` otherwise persists NUMERATORS only, so a script reading it
supports exactly one verdict: "this got more expensive". Every denominator a
ratio needs lived outside the record and was re-derived at render time — a
figure nobody can check.

Each denominator is also a MOVING quantity (``affected_files`` grows during
execute, the task count grows as triage appends fix-tasks, the deliverable count
can change on a Q-Gate re-entry), so the same numerator over the same plan
yields a different ratio depending on WHEN the denominator was read. That is why
these tests pin the PAIR — count plus ``{denominator}_sampling_point`` — and why
the absent case is pinned as hard as the present one: a denominator whose source
cannot be read is absent from the record, never a guessed ``0``.
"""

import importlib.util
import json
import re
from argparse import Namespace
from pathlib import Path

import _plan_parsing
import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics_denominators', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)

cmd_generate = manage_metrics.cmd_generate

# The SIBLING producer of the same count. Loaded as the real command function so
# the agreement test below exercises `manage-solution-outline list-deliverables`
# end-to-end (`extract_deliverables` → `split_deliverable_blocks`) rather than
# re-evaluating the metrics side's own expression.
_OUTLINE_SCRIPT_PATH = get_script_path('plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py')
_outline_spec = importlib.util.spec_from_file_location('manage_solution_outline_denominators', _OUTLINE_SCRIPT_PATH)
assert _outline_spec is not None and _outline_spec.loader is not None
manage_solution_outline = importlib.util.module_from_spec(_outline_spec)
_outline_spec.loader.exec_module(manage_solution_outline)

cmd_list_deliverables = manage_solution_outline.cmd_list_deliverables


def _ns_generate(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _ns_list_deliverables(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, command='list-deliverables', func=cmd_list_deliverables)


def _recorded_row() -> dict:
    """A closed phase row — enough for `generate` to produce a report."""
    return {
        'start_time': '2020-01-01T00:00:00+00:00',
        'end_time': '2020-01-01T00:10:00+00:00',
        'duration_seconds': 600,
        'total_tokens': 1000,
    }


def _seed_phases(plan_id: str) -> Path:
    """Materialise the plan directory with a closed six-phase metrics.toon.

    ``status.json`` is seeded because ``cmd_generate``'s ``_guard_plan_exists``
    refuses a plan directory without one — and a refused generate writes
    nothing, which would make every denominator assertion below fail for a
    reason unrelated to denominators.
    """
    phases = {name: _recorded_row() for name in manage_metrics.PHASE_NAMES}
    manage_metrics.write_metrics(plan_id, {'phases': phases})
    plan_dir = Path(manage_metrics.get_plan_dir(plan_id))
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return plan_dir


def _write_outline(plan_dir: Path, deliverables: int) -> None:
    """Write a solution_outline.md carrying *deliverables* countable headings.

    The headings live under a ``## Deliverables`` H2, which is where the
    solution-outline standard puts them and the only place the authoritative
    extractor looks. Two decoys are written into every fixture so the count is
    never satisfied by a laxer grammar: a bare ``### Notes`` (level-3 but not
    numbered) inside the section, and a fully well-formed ``### 99. Decoy``
    under a DIFFERENT H2 — the out-of-section case that a whole-file scan
    counts and the authoritative extractor does not.
    """
    lines = ['# Solution: fixture', '', '## Deliverables', '']
    for index in range(1, deliverables + 1):
        lines.append(f'### {index}. Deliverable {index}')
        lines.append('')
        lines.append('### Notes')
        lines.append('')
    lines += ['## Approach', '', '### 99. Decoy heading outside Deliverables', '']
    (plan_dir / 'solution_outline.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _write_references(plan_dir: Path, files: list[str]) -> None:
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'affected_files': files}), encoding='utf-8'
    )


def _write_tasks(plan_dir: Path, statuses: list[str]) -> None:
    tasks = plan_dir / 'tasks'
    tasks.mkdir(parents=True, exist_ok=True)
    for index, status in enumerate(statuses, start=1):
        (tasks / f'TASK-{index:03d}.json').write_text(
            json.dumps({'number': index, 'status': status}), encoding='utf-8'
        )


# =============================================================================
# The pair: a count is never persisted without its sampling point
# =============================================================================


def test_each_denominator_is_persisted_with_its_sampling_point(plan_context):
    """All three denominators land as top-level pairs in metrics.toon.

    RED against pre-fix code, where `generate` persisted numerators only and the
    record carried no denominator at all.
    """
    plan_id = 'denom-all-three'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 4)
    _write_references(plan_dir, ['a.py', 'b.py', 'c.md'])
    _write_tasks(plan_dir, ['done', 'done', 'pending'])

    result = cmd_generate(_ns_generate(plan_id))
    assert result['status'] == 'success', result

    data = manage_metrics.read_metrics_raw(plan_id)
    # The counts are the real ones, not placeholders: 4 `### N. Title` headings
    # inside the Deliverables section (the interleaved `### Notes` headings and
    # the `### 99.` decoy under `## Approach` do NOT count), 3 affected files,
    # 2 of 3 tasks done.
    #
    # They read back as STRINGS: `read_metrics_raw` numeric-coerces per-phase
    # block values only, so every plan-level key round-trips as text — the same
    # shape `session_message_count` and the end_time-presence keys have. The
    # assertion is on the literal so the record's real format is pinned rather
    # than a coercion the reader does not perform.
    assert data['deliverable_count'] == '4'
    assert data['files_modified'] == '3'
    assert data['tasks_completed'] == '2'

    # Every count carries its sampling point, from the closed vocabulary.
    for name in ('deliverable_count', 'files_modified', 'tasks_completed'):
        point = data[f'{name}_sampling_point']
        assert point == manage_metrics.SAMPLING_POINT_GENERATE_TIME
        assert point in manage_metrics.SAMPLING_POINTS

    # One shared instant names WHEN the call counted them.
    assert data['denominators_sampled_at']


def test_generate_return_echoes_each_pair(plan_context):
    """The return TOON carries the same pairs the record does."""
    plan_id = 'denom-return'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 2)
    _write_references(plan_dir, ['only.py'])
    _write_tasks(plan_dir, ['done'])

    result = cmd_generate(_ns_generate(plan_id))

    assert result['deliverable_count'] == 2
    assert result['deliverable_count_sampling_point'] == 'generate_time'
    assert result['files_modified'] == 1
    assert result['files_modified_sampling_point'] == 'generate_time'
    assert result['tasks_completed'] == 1
    assert result['tasks_completed_sampling_point'] == 'generate_time'
    assert result['denominators_sampled_at']


# =============================================================================
# Two generations at different sampling points are distinguishable
# =============================================================================


def test_two_generations_of_the_same_plan_are_distinguishable_by_the_field(plan_context):
    """The moving denominator moves, and the record says which read it holds.

    This is the whole point of the sampling point: `affected_files` grows during
    execute, so the SAME numerator divides differently on a later read. The
    record must present the count that was current at a NAMED moment, and two
    generations must be tellable apart.
    """
    plan_id = 'denom-moving'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 1)
    _write_references(plan_dir, ['a.py'])
    _write_tasks(plan_dir, ['done', 'pending'])

    cmd_generate(_ns_generate(plan_id))
    first = manage_metrics.read_metrics_raw(plan_id)
    first_count = first['files_modified']
    first_sampled_at = first['denominators_sampled_at']

    # The plan advances: two more files are declared and the pending task closes.
    _write_references(plan_dir, ['a.py', 'b.py', 'c.py'])
    _write_tasks(plan_dir, ['done', 'done'])
    cmd_generate(_ns_generate(plan_id))
    second = manage_metrics.read_metrics_raw(plan_id)

    # The counts genuinely moved — otherwise the distinguishability below would
    # be vacuous. (Plan-level keys round-trip as text; see the note in
    # `test_each_denominator_is_persisted_with_its_sampling_point`.)
    assert first_count == '1'
    assert first['tasks_completed'] == '1'
    assert second['files_modified'] == '3'
    assert second['tasks_completed'] == '2'

    # Both reads name the same moment CLASS, and the record carries the second
    # read's instant — so a consumer can tell which read it is holding.
    assert first['files_modified_sampling_point'] == 'generate_time'
    assert second['files_modified_sampling_point'] == 'generate_time'
    assert second['denominators_sampled_at'] >= first_sampled_at


# =============================================================================
# Absent is not zero, and not a guess
# =============================================================================


def test_denominator_with_no_readable_source_is_absent_not_zero(plan_context):
    """No outline / references / tasks ⇒ no count and no sampling point.

    A `0` would read as "this plan had no deliverables", which is a claim.
    Absence reads as "this record does not carry that count", which is the truth.
    """
    plan_id = 'denom-absent'
    _seed_phases(plan_id)

    result = cmd_generate(_ns_generate(plan_id))
    assert result['status'] == 'success', result

    data = manage_metrics.read_metrics_raw(plan_id)
    for name in ('deliverable_count', 'files_modified', 'tasks_completed'):
        assert name not in data, name
        assert f'{name}_sampling_point' not in data, name
        assert name not in result, name
    assert 'denominators_sampled_at' not in data
    assert 'denominators_sampled_at' not in result


def test_partially_determinable_denominators_persist_only_what_was_counted(plan_context):
    """One readable source does not manufacture the other two.

    The pair is atomic PER denominator, not per call — a plan carrying an
    outline but no references.json persists the deliverable count alone.
    """
    plan_id = 'denom-partial'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 3)

    result = cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert data['deliverable_count'] == '3'
    assert data['deliverable_count_sampling_point'] == 'generate_time'
    # The shared instant IS written, because at least one denominator landed.
    assert data['denominators_sampled_at']
    for name in ('files_modified', 'tasks_completed'):
        assert name not in data, name
        assert f'{name}_sampling_point' not in data, name
        assert name not in result, name


def test_malformed_source_is_absent_rather_than_defaulted(plan_context):
    """An unparseable references.json yields no count, not a 0."""
    plan_id = 'denom-malformed'
    plan_dir = _seed_phases(plan_id)
    (plan_dir / 'references.json').write_text('{ not json', encoding='utf-8')

    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert 'files_modified' not in data
    assert 'files_modified_sampling_point' not in data


def test_stale_pair_is_removed_when_its_source_becomes_unreadable(plan_context):
    """A count from an earlier run never survives beside a fresh timestamp.

    Without the removal the record would present a stale `files_modified` next
    to a `denominators_sampled_at` naming a moment at which that count was NOT
    what the plan held — precisely the unstated-sampling-point defect, one layer
    down.
    """
    plan_id = 'denom-stale'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 2)
    _write_references(plan_dir, ['a.py', 'b.py'])

    cmd_generate(_ns_generate(plan_id))
    assert manage_metrics.read_metrics_raw(plan_id)['files_modified'] == '2'

    # The source becomes unreadable between generations.
    (plan_dir / 'references.json').unlink()
    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert 'files_modified' not in data
    assert 'files_modified_sampling_point' not in data
    # The still-readable denominator is untouched — removal is per-denominator.
    assert data['deliverable_count'] == '2'


def test_zero_completed_tasks_over_a_real_population_is_counted_as_zero(plan_context):
    """A measured zero is NOT the absent case.

    A plan whose tasks are all pending legitimately counts `0` completed against
    a real population; only an absent task store means the count was never
    taken. Collapsing the two would make "nothing finished yet" and "we never
    looked" the same record.
    """
    plan_id = 'denom-zero-tasks'
    plan_dir = _seed_phases(plan_id)
    _write_tasks(plan_dir, ['pending', 'pending'])

    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    # A MEASURED zero is on the record as `0` — distinct from the absent case
    # asserted above, where the key is not present at all.
    assert data['tasks_completed'] == '0'
    assert data['tasks_completed_sampling_point'] == 'generate_time'


def test_empty_affected_files_list_is_counted_as_zero(plan_context):
    """A readable references.json with an EMPTY list is a measured `0`.

    `scope_estimate: none` is a documented plan state — pure analysis, no
    affected files — so an empty `affected_files` list is a legitimate answer
    to a question that WAS asked. Returning absence for it would tell a reader
    that `references.json` could not be read when it was read fine, which is
    the "unmeasured means could-not-be-read" contract stated in
    `data-format.md`, `plan-efficiency.md`, and the counter's own docstring.
    """
    plan_id = 'denom-empty-files'
    plan_dir = _seed_phases(plan_id)
    _write_references(plan_dir, [])

    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert data['files_modified'] == '0'
    assert data['files_modified_sampling_point'] == 'generate_time'


def test_references_json_without_an_affected_files_list_is_absent(plan_context):
    """The matched negative control for the measured zero above.

    An empty list and a MISSING list are different facts: the first was
    counted, the second never existed. Without this case the measured-zero
    assertion would be satisfied by a counter that returns `0` for both — which
    is the same conflation in the opposite direction.
    """
    plan_id = 'denom-no-files-key'
    plan_dir = _seed_phases(plan_id)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )

    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert 'files_modified' not in data
    assert 'files_modified_sampling_point' not in data


@pytest.mark.parametrize(
    ('label', 'outline'),
    [
        (
            'section-present-but-empty',
            '# Solution: fixture\n\n## Deliverables\n\nNone — pure analysis.\n',
        ),
        (
            'no-deliverables-section-at-all',
            '# Solution: fixture\n\n## Approach\n\nProse only.\n',
        ),
    ],
)
def test_readable_outline_with_no_deliverable_heading_is_counted_as_zero(
    plan_context, label, outline
):
    """A readable outline yielding no heading is a measured `0`, not absence.

    The count was taken and the answer was zero. Only an outline that could not
    be READ — absent, or an OSError — is absent from the record.
    """
    plan_id = f'denom-zero-deliverables-{label}'
    plan_dir = _seed_phases(plan_id)
    (plan_dir / 'solution_outline.md').write_text(outline, encoding='utf-8')

    cmd_generate(_ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert data['deliverable_count'] == '0'
    assert data['deliverable_count_sampling_point'] == 'generate_time'


# =============================================================================
# One deliverable grammar, not two producers of one number
# =============================================================================

# The grammar `_count_deliverables` used to carry privately: unscoped to any
# section, and satisfied by a numbered heading with no title at all.
_RETIRED_WHOLE_FILE_RE = re.compile(r'^###\s+\d+\.\s')

# Outlines chosen so that retired grammar and the authoritative section-scoped
# extractor give DIFFERENT answers. If `_count_deliverables` ever reverts to a
# private grammar, the agreement assertion below fails on these — which is what
# makes it non-vacuous.
_DIVERGENT_OUTLINES = {
    'numbered-heading-under-approach': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '## Approach\n\n'
        '### 2. Not a deliverable\n'
    ),
    'numbered-heading-inside-a-fenced-example': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '## Notes\n\n'
        'Deliverable headings look like this:\n\n'
        '```markdown\n'
        '### 7. Example heading in a fenced block\n'
        '```\n'
    ),
    'degenerate-heading-with-no-title': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '### 2. \n'
    ),
    'headings-only-outside-the-section': (
        '# Solution: fixture\n\n## Approach\n\n### 1. Not a deliverable\n'
    ),
}


@pytest.mark.parametrize('label', sorted(_DIVERGENT_OUTLINES))
def test_deliverable_count_agrees_with_the_sibling_producer(plan_context, label):
    """The metrics counter and `manage-solution-outline` return ONE number.

    Two producers of one denominator is the defect this module exists to
    close: `metrics.toon`'s `deliverable_count` and
    `manage-solution-outline list-deliverables` are read by different
    consumers, and a reader handed two different figures has no way to tell
    which is right.

    The two reach the count by DIFFERENT functions — `generate` calls
    `extract_deliverable_headings`, `list-deliverables` calls the sibling
    `extract_deliverables` → `split_deliverable_blocks` — and agree only
    because both match through the one shared
    `_plan_parsing.DELIVERABLE_HEADING_PATTERN`. So this test invokes the real
    `cmd_list_deliverables` rather than re-evaluating `generate`'s own
    expression: re-deriving the production side would leave a divergence
    introduced in `split_deliverable_blocks` — the exact way the two can drift
    apart — passing green.
    """
    outline = _DIVERGENT_OUTLINES[label]
    plan_id = f'denom-agreement-{label}'
    plan_dir = _seed_phases(plan_id)
    (plan_dir / 'solution_outline.md').write_text(outline, encoding='utf-8')

    result = cmd_generate(_ns_generate(plan_id))
    sibling = cmd_list_deliverables(_ns_list_deliverables(plan_id))

    if sibling['status'] == 'success':
        assert result['deliverable_count'] == sibling['deliverable_count']
        counted = sibling['deliverable_count']
    else:
        # The one shape the two producers legitimately express differently: with
        # no `## Deliverables` H2 at all, `list-deliverables` reports
        # `section_not_found` while the metrics counter records a MEASURED 0
        # (§ "could-not-be-read is the ONLY trigger"). Pin both halves — an
        # unexpected error code here is a real disagreement, not a carve-out.
        assert sibling['error'] == 'section_not_found'
        assert result['deliverable_count'] == 0
        counted = 0

    # Non-vacuity: the RETIRED grammar — a whole-file scan for `^###\s+\d+\.\s`,
    # unscoped and not requiring a title — gives a DIFFERENT answer on this
    # outline. So the agreement above is a real constraint, not two
    # implementations that happen to coincide on the input chosen.
    retired = len([line for line in outline.splitlines() if _RETIRED_WHOLE_FILE_RE.match(line)])
    assert retired != counted, (
        f'{label} no longer distinguishes the two grammars — pick a divergent outline'
    )


def test_the_two_deliverable_extractors_share_one_heading_pattern(monkeypatch):
    """The agreement above is by construction, not by two matching literals.

    `extract_deliverable_headings` (what `generate` counts with) and
    `split_deliverable_blocks` (what `list-deliverables` counts through) used to
    each compile a private copy of the heading regex. Byte-identical copies
    agree until someone edits one, so the "cannot disagree" claim in
    `data-format.md` and in `_count_deliverables`' docstring rested on a
    coincidence. This pins the collapse: exactly one compiled pattern object,
    referenced by both.

    The guard is over the module's compiled OBJECTS, not over its source text. A
    `source.count("re.compile(r'^###")` scan matches one exact spelling, so a
    reintroduced private copy written with double quotes, with the prefix on the
    next line, or with leading whitespace inside the pattern would leave the
    count at 1 and the test would pass while the two extractors again held
    separate objects — a guard that cannot fail against the very thing it
    watches for.

    Counting the module's objects is still only half the claim. `vars()` sees
    module-level bindings, so an extractor that compiles a FUNCTION-LOCAL copy
    is invisible to it: the population stays at one, the count assertion stays
    green, and the two extractors are once more on separate objects. The
    substitution below closes that half — it swaps the shared object for a
    sentinel grammar and calls both extractors, so "each extractor matches
    through THIS object" is asserted by identity rather than inferred from an
    inventory.
    """
    pattern = _plan_parsing.DELIVERABLE_HEADING_PATTERN

    # Population-derived rather than text-derived: every compiled pattern the
    # module holds, not one spelling of one call site.
    heading_patterns = [
        value
        for value in vars(_plan_parsing).values()
        if isinstance(value, re.Pattern) and value.pattern.startswith('^###')
    ]

    assert heading_patterns == [pattern], (
        'the deliverable heading regex is compiled more than once — the two '
        'extractors are back to private copies that agree only by convention'
    )
    assert pattern.pattern == r'^###\s+(\d+)\.\s+(.+)$'

    # The reference, not the inventory. With the module attribute replaced by a
    # grammar that recognises `@@@ N. Title` and NOT `### N. Title`, an
    # extractor that genuinely dereferences `DELIVERABLE_HEADING_PATTERN`
    # follows the substitution and reports only the sentinel heading; one
    # holding any private copy keeps reporting the `###` heading instead. The
    # probe carries one heading of each grammar so both directions are pinned
    # by a single expected list — a stale extractor yields `['Stale grammar']`,
    # never a silently-equal count.
    sentinel = re.compile(r'^@@@\s+(\d+)\.\s+(.+)$', re.MULTILINE)
    monkeypatch.setattr(_plan_parsing, 'DELIVERABLE_HEADING_PATTERN', sentinel)

    probe = '### 1. Stale grammar\n\nbody\n\n@@@ 2. Substituted grammar\n\nbody\n'

    headings = _plan_parsing.extract_deliverable_headings(probe)
    assert [item['title'] for item in headings] == ['Substituted grammar'], (
        'extract_deliverable_headings does not match through '
        'DELIVERABLE_HEADING_PATTERN — it holds a copy of its own'
    )

    blocks = _plan_parsing.split_deliverable_blocks(probe)
    assert [item['title'] for item in blocks] == ['Substituted grammar'], (
        'split_deliverable_blocks does not split on DELIVERABLE_HEADING_PATTERN '
        '— it holds a copy of its own'
    )


# =============================================================================
# One vocabulary, not two
# =============================================================================


def test_sampling_point_reuses_the_modules_single_discriminator_vocabulary():
    """Every value vocabulary the module publishes is a closed tuple of strings.

    Deliverable 3 is forbidden from introducing a second, parallel discriminator
    vocabulary. The guard that enforces that MUST be population-derived: a
    hand-listed trio stops covering a FOURTH vocabulary the moment one is added,
    which is precisely the drift it exists to catch — the check would keep
    passing while the new vocabulary bypassed the shape contract entirely.

    The population is therefore read off the module — every public module-level
    tuple whose members are all strings — and the three known discriminators are
    asserted to be IN it, so the derivation cannot silently shrink past them
    either.

    The derivation deliberately does NOT filter on truthiness. An `and value`
    term in the comprehension reads like a harmless type narrowing, but it
    excludes exactly the specimen the loop below exists to reject: a public
    vocabulary declared as `()`. Filtered out at derivation, an empty tuple
    could never reach the per-member assertions, so "no vocabulary is empty"
    would hold over a population from which every empty vocabulary had already
    been removed. Emptiness is therefore asserted, not selected away.
    """
    vocabularies = {
        name: value
        for name, value in vars(manage_metrics).items()
        if not name.startswith('_')
        and isinstance(value, tuple)
        and all(isinstance(item, str) for item in value)
    }

    # Non-vacuity: the derived population is non-empty AND covers the three named
    # discriminators. Without this the per-member loop below would pass trivially
    # against an empty dict.
    assert vocabularies, 'no module-level value vocabulary was discovered'
    for required in ('SAMPLING_POINTS', 'TOKEN_POPULATIONS', 'VALUE_SCOPES'):
        assert required in vocabularies, (
            f'{required} is no longer a public closed value tuple '
            f'(population size {len(vocabularies)}: {sorted(vocabularies)})'
        )

    # Total over the derived population, not over a hand-listed subset of it.
    # Two distinct shapes are rejected here: a vocabulary that offers NO value
    # at all, and one that offers an empty string as a value. Both would let a
    # write site persist a discriminator that discriminates nothing.
    for name, vocabulary in vocabularies.items():
        assert vocabulary, f'{name} is an empty vocabulary — it admits no value'
        assert all(value for value in vocabulary), f'{name} carries an empty value'
