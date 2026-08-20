#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the persisted denominators and their sampling-point discriminator."""


import json

import pytest
from _denominator_sampling_point_fixtures import (
    _DIVERGENT_OUTLINES,
    _RETIRED_WHOLE_FILE_RE,
    _seed_phases,
    _write_outline,
    _write_references,
    _write_tasks,
    cmd_generate,
    cmd_list_deliverables,
    manage_metrics,
    ns_list_deliverables,
)
from _manage_metrics_fixtures import ns_generate

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

    result = cmd_generate(ns_generate(plan_id))
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

    result = cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))
    assert manage_metrics.read_metrics_raw(plan_id)['files_modified'] == '2'

    # The source becomes unreadable between generations.
    (plan_dir / 'references.json').unlink()
    cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))

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

    cmd_generate(ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert data['deliverable_count'] == '0'
    assert data['deliverable_count_sampling_point'] == 'generate_time'


# =============================================================================
# One deliverable grammar, not two producers of one number
# =============================================================================

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

    result = cmd_generate(ns_generate(plan_id))
    sibling = cmd_list_deliverables(ns_list_deliverables(plan_id))

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
