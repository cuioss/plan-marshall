#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-config.py domain-narrow subcommand.

The narrowing counterpart to ``domain-detect``: it removes from a plan's
``references.domains`` the domains its declared footprint does not justify. A
domain is droppable only when all three legs of the safety bound agree — no
resolved task depends on it, ``always_on`` does not claim it, and ``file_globs``
does not claim it against the supplied footprint.

The synthetic ``system`` domain is exempt from that bound rather than judged by it:
both inclusion legs are evaluated over a mapping it is filtered out of, so neither
can ever claim it. It is retained carrying an exemption marker, which is what keeps
an empty ``claimed_by`` meaning "dropped for want of a claim" and nothing else.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_config_fixtures import create_marshal_json

from conftest import load_script_module, parse_ns

# Addressed as three separate module-level constants rather than one unpacked
# tuple: the loader-contract guard resolves a call site statically only when its
# leading positionals are literals or module-level constants, and a `*tuple` at
# the bundle position puts the call in its blind-spot tally.
_BUNDLE = 'plan-marshall'
_SKILL = 'manage-config'
_SCRIPT_NAME = 'manage-config.py'

_mod = load_script_module(
    _BUNDLE, _SKILL, '_cmd_domain_narrow.py', module_name='_cmd_domain_narrow_under_test'
)
cmd_domain_narrow = _mod.cmd_domain_narrow

_mc = load_script_module(_BUNDLE, _SKILL, _SCRIPT_NAME, 'mc_domain_narrow_under_test')

#: The worked example from the design: one domain claimed by ``always_on``, one
#: claimed by ``file_globs``, one claimed by no leg at all.
_DOMAINS_CONFIG = {
    'skill_domains': {
        'system': {'defaults': []},
        'documentation': {'bundle': 'pm-documents'},
        'general-dev': {'bundle': 'pm-general'},
        'python': {'bundle': 'pm-dev-python', 'file_globs': ['**/*.py']},
        'plan-marshall-plugin-dev': {'bundle': 'pm-plugin-development', 'always_on': True},
    }
}

#: Every non-system domain `_DOMAINS_CONFIG` declares, DERIVED from that config
#: rather than restated as a literal. A hand-maintained copy goes stale silently:
#: a domain added to the config above would be missing here, the assertions that
#: compare against this list would omit it, and they would keep passing while no
#: longer covering the case the new domain was added to exercise. The identifier
#: names the set, not its cardinality, for the same reason.
_CONFIGURED_DOMAINS = sorted(d for d in _DOMAINS_CONFIG['skill_domains'] if d != 'system')

_PY_FOOTPRINT = 'marketplace/bundles/plan-marshall/skills/manage-config/scripts/a.py'
_MD_FOOTPRINT = 'doc/user/configuration.adoc'

#: A persisted path whose recorded form carries significant leading and trailing
#: whitespace, paired with a glob anchored on that whitespace. The glob matches the
#: recorded form and NOT its stripped counterpart, which is what makes the pair a
#: discriminating probe for whether the primary path mutates the value it matches.
_PADDED_FOOTPRINT = f' {_PY_FOOTPRINT} '
_PADDED_GLOB_CONFIG = {
    'skill_domains': {
        'system': {'defaults': []},
        'documentation': {'bundle': 'pm-documents'},
        'python': {'bundle': 'pm-dev-python', 'file_globs': [' **/*.py ']},
    }
}


def _ns(plan_id: str, affected_files: str) -> Namespace:
    """Args for ``manage-config domain-narrow``, built by the script's own parser."""
    ns: Namespace = parse_ns(
        _BUNDLE,
        _SKILL,
        _SCRIPT_NAME,
        'domain-narrow',
        '--plan-id',
        plan_id,
        '--affected-files',
        affected_files,
    )
    return ns


def _seed(plan_context, plan_id: str, domains: list[str], *, config: dict | None = None) -> Path:
    """Create the plan dir plus marshal.json and a references.json carrying ``domains``."""
    plan_dir: Path = plan_context.fixture_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    create_marshal_json(plan_context.fixture_dir, config or _DOMAINS_CONFIG)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'domains': domains}), encoding='utf-8'
    )
    return plan_dir


def _seed_with_footprint(
    plan_context,
    plan_id: str,
    domains: list[str],
    affected_files: list[str],
    *,
    config: dict | None = None,
) -> Path:
    """Seed a plan whose references.json also carries a persisted ``affected_files`` list."""
    plan_dir = _seed(plan_context, plan_id, domains, config=config)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'domains': domains, 'affected_files': affected_files}),
        encoding='utf-8',
    )
    return plan_dir


def _ns_without_flag(plan_id: str) -> Namespace:
    """Args for ``domain-narrow`` with the override omitted, so the persisted list is the source."""
    ns: Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT_NAME, 'domain-narrow', '--plan-id', plan_id)
    return ns


def _write_task(plan_dir: Path, number: int, domain: str) -> None:
    """Persist a resolved task whose skill set was resolved against ``domain``."""
    (plan_dir / f'TASK-{number:03d}.json').write_text(
        json.dumps({'number': number, 'domain': domain, 'status': 'done'}), encoding='utf-8'
    )


def _claimed_by(result: dict, domain: str) -> list[str]:
    """Return the provenance legs recorded for ``domain``."""
    return next(e['claimed_by'] for e in result['provenance'] if e['domain'] == domain)


# =============================================================================
# The three legs of the safety bound
# =============================================================================


def test_always_on_domain_is_never_dropped(plan_context):
    """An always_on domain survives a footprint that no glob and no task claims."""
    _seed(plan_context, 'dn-always-on', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-always-on', _MD_FOOTPRINT))

    assert result['status'] == 'success'
    assert 'plan-marshall-plugin-dev' in result['retained']
    assert 'plan-marshall-plugin-dev' not in result['dropped']
    assert _claimed_by(result, 'plan-marshall-plugin-dev') == ['always_on']


@pytest.mark.parametrize(
    ('footprint', 'expect_retained'),
    [(_PY_FOOTPRINT, True), (_MD_FOOTPRINT, False)],
    ids=['footprint-matches-glob', 'footprint-misses-glob'],
)
def test_file_globs_leg_follows_the_declared_footprint(plan_context, footprint, expect_retained):
    """The file_globs leg claims a domain only when the declared footprint matches."""
    _seed(plan_context, 'dn-globs', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-globs', footprint))

    assert ('python' in result['retained']) is expect_retained
    assert ('python' in result['dropped']) is not expect_retained
    assert _claimed_by(result, 'python') == (['file_globs'] if expect_retained else [])


def test_domain_claimed_by_no_leg_is_dropped(plan_context):
    """No task, no always_on, no glob hit — the domain leaves the set."""
    _seed(plan_context, 'dn-unclaimed', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-unclaimed', _PY_FOOTPRINT))

    assert set(result['dropped']) == {'documentation', 'general-dev'}
    assert _claimed_by(result, 'documentation') == []


def test_task_claimed_domain_is_retained_without_an_inclusion_leg(plan_context):
    """A domain a resolved task depends on is retained though no inclusion leg claims it."""
    plan_dir = _seed(plan_context, 'dn-task', _CONFIGURED_DOMAINS)
    _write_task(plan_dir, 1, 'documentation')

    result = cmd_domain_narrow(_ns('dn-task', _PY_FOOTPRINT))

    assert 'documentation' in result['retained']
    assert _claimed_by(result, 'documentation') == ['task']
    # The leg is independent: the sibling with neither task nor inclusion still goes.
    assert result['dropped'] == ['general-dev']


def test_all_three_legs_are_recorded_together(plan_context):
    """A domain several legs claim records every one of them, in leg order."""
    plan_dir = _seed(
        plan_context,
        'dn-multi-leg',
        _CONFIGURED_DOMAINS,
        config={
            'skill_domains': {
                'system': {'defaults': []},
                'python': {
                    'bundle': 'pm-dev-python',
                    'always_on': True,
                    'file_globs': ['**/*.py'],
                },
            }
        },
    )
    _write_task(plan_dir, 1, 'python')

    result = cmd_domain_narrow(_ns('dn-multi-leg', _PY_FOOTPRINT))

    assert _claimed_by(result, 'python') == ['task', 'always_on', 'file_globs']


# =============================================================================
# The synthetic system domain — exempt from the bound, not judged by it
# =============================================================================


def test_system_domain_is_retained_by_exemption_not_by_a_leg(plan_context):
    """A ``system`` entry in the set is retained and records the exemption marker.

    ``system`` is filtered out of the mapping both inclusion legs are evaluated over,
    so neither can ever claim it. Judging it by the bound would drop it because two
    legs were structurally incapable of looking — the marker records that it was
    exempted instead.
    """
    _seed(plan_context, 'dn-system', [*_CONFIGURED_DOMAINS, 'system'])

    result = cmd_domain_narrow(_ns('dn-system', _MD_FOOTPRINT))

    assert 'system' in result['retained']
    assert 'system' not in result['dropped']
    assert _claimed_by(result, 'system') == ['system_exempt']


def test_a_retained_domain_never_carries_an_empty_claimed_by(plan_context):
    """Empty ``claimed_by`` means dropped, exactly — including when ``system`` is present.

    The documented reading of an empty ``claimed_by`` is "no leg claimed the domain,
    which is why it was dropped". A retained domain publishing one would make that
    reading false, which is the failure the exemption marker exists to prevent.
    """
    _seed(plan_context, 'dn-system-reading', [*_CONFIGURED_DOMAINS, 'system'])

    result = cmd_domain_narrow(_ns('dn-system-reading', _MD_FOOTPRINT))

    retained = set(result['retained'])
    assert 'system' in retained
    assert all(e['claimed_by'] for e in result['provenance'] if e['domain'] in retained)
    assert {e['domain'] for e in result['provenance'] if not e['claimed_by']} == set(
        result['dropped']
    )


# =============================================================================
# Set algebra — narrowing never adds
# =============================================================================


@pytest.mark.parametrize(
    'footprint', [_PY_FOOTPRINT, _MD_FOOTPRINT], ids=['glob-hit', 'no-glob-hit']
)
def test_narrowing_is_a_strict_subset(plan_context, footprint):
    """Retained is a subset of the pre-narrowing set, and partitions it with dropped."""
    _seed(plan_context, 'dn-subset', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-subset', footprint))

    retained, dropped = set(result['retained']), set(result['dropped'])
    assert retained <= set(_CONFIGURED_DOMAINS)
    assert retained | dropped == set(_CONFIGURED_DOMAINS)
    assert retained & dropped == set()


def test_retained_covers_the_inclusion_union_intersected_with_the_current_set(plan_context):
    """A claimed domain ALREADY IN the set is retained; the claim alone never adds one.

    The invariant is `retained >= (always_on | glob_matched) & current`, NOT
    `retained >= always_on | glob_matched`. The verb iterates the current set only,
    so a claimed-but-absent domain stays absent — pinned by the sibling
    test_a_domain_outside_the_current_set_is_never_added. This test seeds both
    claimed domains, so it exercises the intersected form and nothing wider.
    """
    _seed(plan_context, 'dn-superset', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-superset', _PY_FOOTPRINT))

    assert {'python', 'plan-marshall-plugin-dev'} <= set(result['retained'])


def test_a_domain_outside_the_current_set_is_never_added(plan_context):
    """An always_on domain absent from references.domains stays absent."""
    _seed(plan_context, 'dn-no-add', ['documentation', 'python'])

    result = cmd_domain_narrow(_ns('dn-no-add', _PY_FOOTPRINT))

    assert 'plan-marshall-plugin-dev' not in result['retained']
    assert [e['domain'] for e in result['provenance']] == ['documentation', 'python']


# =============================================================================
# The three mutually distinguishable outcomes
# =============================================================================


def test_narrowed_outcome_reports_true_with_a_non_empty_dropped_set(plan_context):
    """Narrowing ran and dropped domains."""
    _seed(plan_context, 'dn-narrowed', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-narrowed', _PY_FOOTPRINT))

    assert result['status'] == 'success'
    assert result['narrowed'] is True
    assert result['dropped']


def test_already_minimal_set_reports_not_narrowed_rather_than_an_error(plan_context):
    """Nothing droppable is a valid success, distinguishable from a failure to evaluate."""
    _seed(plan_context, 'dn-minimal', ['python', 'plan-marshall-plugin-dev'])

    result = cmd_domain_narrow(_ns('dn-minimal', _PY_FOOTPRINT))

    assert result['status'] == 'success'
    assert result['narrowed'] is False
    assert result['dropped'] == []
    assert set(result['retained']) == {'python', 'plan-marshall-plugin-dev'}


@pytest.mark.parametrize(
    ('domains', 'footprint', 'expect_narrowed'),
    [(_CONFIGURED_DOMAINS, _PY_FOOTPRINT, True), (['python'], _PY_FOOTPRINT, False)],
    ids=['narrowed', 'nothing-droppable'],
)
def test_report_line_is_emitted_on_both_outcomes(plan_context, domains, footprint, expect_narrowed):
    """The one-line report is emitted whether or not anything was dropped."""
    _seed(plan_context, 'dn-report', domains)

    result = cmd_domain_narrow(_ns('dn-report', footprint))

    assert result['narrowed'] is expect_narrowed
    assert result['report'].startswith('domain-narrow:')
    assert str(len(result['retained'])) in result['report']


@pytest.mark.parametrize(
    ('references_body', 'expected_error'),
    [
        (None, 'domains_unreadable'),
        ('{ not json', 'domains_unreadable'),
        ('{"base_branch": "main"}', 'domains_unreadable'),
        ('{"domains": "python"}', 'domains_unreadable'),
    ],
    ids=['absent', 'malformed', 'key-missing', 'key-not-a-list'],
)
def test_could_not_evaluate_returns_error_not_an_empty_narrowing(
    plan_context, references_body, expected_error
):
    """An unreadable domain set is an error, never a success with nothing dropped."""
    plan_dir: Path = plan_context.fixture_dir / 'plans' / 'dn-unreadable'
    plan_dir.mkdir(parents=True, exist_ok=True)
    create_marshal_json(plan_context.fixture_dir, _DOMAINS_CONFIG)
    if references_body is not None:
        (plan_dir / 'references.json').write_text(references_body, encoding='utf-8')

    result = cmd_domain_narrow(_ns('dn-unreadable', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == expected_error
    assert 'narrowed' not in result
    assert 'dropped' not in result


def test_missing_plan_dir_errors(plan_context):
    """A plan that does not exist cannot be narrowed."""
    create_marshal_json(plan_context.fixture_dir, _DOMAINS_CONFIG)

    result = cmd_domain_narrow(_ns('dn-does-not-exist', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_unconfigured_skill_domains_errors(plan_context):
    """With no configured domain there is no inclusion leg to evaluate."""
    _seed(plan_context, 'dn-no-domains', _CONFIGURED_DOMAINS, config={'skill_domains': {}})

    result = cmd_domain_narrow(_ns('dn-no-domains', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == 'no_skill_domains_configured'


# =============================================================================
# Provenance completeness
# =============================================================================


def test_provenance_covers_every_pre_narrowing_domain(plan_context):
    """One entry per domain in the PRE-narrowing set — retained and dropped alike."""
    _seed(plan_context, 'dn-provenance', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-provenance', _PY_FOOTPRINT))

    recorded = [e['domain'] for e in result['provenance']]
    assert recorded == sorted(_CONFIGURED_DOMAINS)
    assert set(recorded) == set(result['retained']) | set(result['dropped'])


def test_provenance_records_the_absence_of_a_claim(plan_context):
    """A dropped domain carries an empty claimed_by rather than being omitted."""
    _seed(plan_context, 'dn-prov-empty', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns('dn-prov-empty', _PY_FOOTPRINT))

    empty = {e['domain'] for e in result['provenance'] if e['claimed_by'] == []}
    assert empty == set(result['dropped'])


# =============================================================================
# Read-only guarantee
# =============================================================================


def test_verb_writes_nothing(plan_context):
    """marshal.json and references.json are byte-identical across the call.

    The baseline is captured by this test immediately before the invocation, so
    the comparison is against recorded bytes rather than an assumed prior state.
    """
    plan_dir = _seed(plan_context, 'dn-readonly', _CONFIGURED_DOMAINS)
    marshal_path: Path = plan_context.fixture_dir / 'marshal.json'
    references_path = plan_dir / 'references.json'
    marshal_before = marshal_path.read_bytes()
    references_before = references_path.read_bytes()

    result = cmd_domain_narrow(_ns('dn-readonly', _PY_FOOTPRINT))

    assert result['narrowed'] is True  # the call did real work
    assert marshal_path.read_bytes() == marshal_before
    assert references_path.read_bytes() == references_before


# =============================================================================
# One home for the inclusion legs
# =============================================================================


def test_inclusion_legs_are_borrowed_from_the_detector_not_re_implemented():
    """The leg helpers resolve to ``_cmd_domain_detect``, so the semantics have one home.

    This is the durable form of the "``_cmd_domain_detect.py`` is unmodified"
    guarantee. A ``git diff`` assertion cannot carry it: it passes vacuously on
    every clean checkout — which is every CI run and every state after the change
    lands — and fails spuriously the first time someone edits the detector for an
    unrelated reason. Asserting the import instead fails exactly when the
    narrowing module starts carrying its own copy of the inclusion semantics,
    which is the outcome the guarantee exists to prevent.
    """
    assert _mod._always_on_domains.__module__ == '_cmd_domain_detect'
    assert _mod._glob_matched_domains.__module__ == '_cmd_domain_detect'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_main_routes_domain_narrow_to_its_handler(monkeypatch):
    """`main()` reaches cmd_domain_narrow with the parsed namespace.

    The real entry point is driven because nothing weaker observes the routing.
    Asserting that the handler symbol is importable and that the subparser accepts
    the flags leaves every assertion true after the `domain-narrow` dispatch branch
    is deleted — the test would pass over a verb that can no longer be invoked. The
    namespace the handler receives is also the parsed namespace, so the parser
    surface is covered here rather than separately.
    """
    received: list = []

    def _recording_handler(args):
        received.append(args)
        return {'status': 'success'}

    monkeypatch.setattr(_mc, 'cmd_domain_narrow', _recording_handler)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            _SCRIPT_NAME,
            'domain-narrow',
            '--plan-id',
            'dispatch-check',
            '--affected-files',
            'a.py',
        ],
    )

    # main() is safe_main-wrapped, so a clean run leaves through SystemExit(0) —
    # the same shape test_help_lists_both_flags relies on.
    with pytest.raises(SystemExit) as exit_info:
        _mc.main()

    assert exit_info.value.code == 0
    assert len(received) == 1
    assert received[0].noun == 'domain-narrow'
    assert received[0].plan_id == 'dispatch-check'
    assert received[0].affected_files == 'a.py'


def test_affected_files_is_optional_at_the_parser():
    """The flag is an out-of-band override, so omitting it parses and yields None.

    The footprint requirement did not go away — it moved from the parser to the verb,
    which reads references.affected_files and refuses when neither source yields one
    (test_footprint_is_read_from_references / test_missing_footprint_is_refused).
    Keeping it required at the parser would have forced every caller through the lossy
    comma-joined string surface.
    """
    ns = parse_ns(_BUNDLE, _SKILL, _SCRIPT_NAME, 'domain-narrow', '--plan-id', 'dispatch-check')

    assert ns.affected_files is None


def test_footprint_is_read_from_references_when_the_flag_is_absent(plan_context):
    """The primary source is the persisted list, so a comma in a path cannot split it."""
    _seed_with_footprint(
        plan_context,
        'dn-refs-footprint',
        _CONFIGURED_DOMAINS,
        ['marketplace/bundles/plan-marshall/skills/a,b/scripts/x.py'],
    )

    result = cmd_domain_narrow(_ns_without_flag('dn-refs-footprint'))

    assert result['status'] == 'success'
    # The comma-bearing path stayed ONE path, so the .py glob still claims python.
    assert 'python' in result['retained']
    assert _claimed_by(result, 'python') == ['file_globs']


def test_missing_footprint_is_refused(plan_context):
    """No list and no override is a could-not-evaluate error, never a silent full drop."""
    _seed(plan_context, 'dn-no-footprint', _CONFIGURED_DOMAINS)

    result = cmd_domain_narrow(_ns_without_flag('dn-no-footprint'))

    assert result['status'] == 'error'
    assert result['error'] == 'footprint_unreadable'


# =============================================================================
# Footprint fidelity — the persisted path is matched in the form it was recorded
# =============================================================================


def test_a_whitespace_bearing_persisted_path_reaches_the_glob_leg_verbatim(plan_context):
    """A recorded path keeps its significant whitespace all the way to ``file_globs``.

    The glob here matches ONLY the recorded form, so the assertion fails the moment
    the primary path mutates the value: a stripped path misses the glob, ``python``
    lands in ``dropped`` with an empty ``claimed_by``, and the leg that evaluated a
    path the plan never declared reads as a leg that looked and found nothing.
    """
    _seed_with_footprint(
        plan_context,
        'dn-verbatim',
        ['documentation', 'python'],
        [_PADDED_FOOTPRINT],
        config=_PADDED_GLOB_CONFIG,
    )

    result = cmd_domain_narrow(_ns_without_flag('dn-verbatim'))

    assert result['status'] == 'success'
    assert 'python' in result['retained']
    assert _claimed_by(result, 'python') == ['file_globs']


def test_an_all_blank_persisted_footprint_still_refuses_to_narrow(plan_context):
    """Blank-only entries leave no footprint, so the guard refuses rather than narrowing.

    This is the negative control for the sibling above. Keeping the recorded form
    verbatim must not also keep a blank entry: a footprint of ``{'   '}`` is
    non-empty enough to pass the ``footprint_empty`` guard while matching no glob,
    which would drop every glob-only domain on evidence that matches nothing.
    """
    _seed_with_footprint(
        plan_context, 'dn-blank-footprint', _CONFIGURED_DOMAINS, ['   ', '\t', '\n', '']
    )

    result = cmd_domain_narrow(_ns_without_flag('dn-blank-footprint'))

    assert result['status'] == 'error'
    assert result['error'] == 'footprint_empty'
    assert 'dropped' not in result


def test_unreadable_task_file_is_refused_not_skipped(plan_context):
    """A task leg that could not be evaluated must not render as a leg that found nothing."""
    plan_dir = _seed(plan_context, 'dn-bad-task', _CONFIGURED_DOMAINS)
    (plan_dir / 'TASK-001.json').write_text('{not valid json', encoding='utf-8')

    result = cmd_domain_narrow(_ns('dn-bad-task', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == 'task_leg_unreadable'
    # The fail-open this replaces would have returned success with the task's domain
    # dropped and an empty claimed_by — "no leg claimed it" for a leg that never ran.
    assert 'dropped' not in result


@pytest.mark.parametrize(
    'task_body',
    [
        '[]',
        '"plan-marshall-plugin-dev"',
        '{"number": 1}',
        '{"number": 1, "domain": ""}',
        '{"number": 1, "domain": 42}',
    ],
    ids=[
        'not-an-object',
        'a-bare-string',
        'domain-absent',
        'domain-empty',
        'domain-not-a-string',
    ],
)
def test_a_parsed_but_unusable_task_file_is_refused_not_skipped(plan_context, task_body):
    """A task record carrying no usable domain is refused exactly like an unparseable one.

    ``domain`` is a required task field, so a record without a usable string one is
    malformed rather than sparse. Skipping it reopens the same fail-open through a
    different door: the file contributes no claim, the loop moves on, and the domain it
    named is dropped carrying an empty ``claimed_by`` — "no leg claimed it" published for
    a leg that never evaluated the file at all.
    """
    plan_dir = _seed(plan_context, 'dn-unusable-task', _CONFIGURED_DOMAINS)
    (plan_dir / 'TASK-001.json').write_text(task_body, encoding='utf-8')

    result = cmd_domain_narrow(_ns('dn-unusable-task', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == 'task_leg_unreadable'
    assert 'dropped' not in result


def test_a_marshal_read_failure_is_reported_rather_than_raised(plan_context):
    """A read failure that is not absence still returns the documented error.

    The guard used to catch ``FileNotFoundError`` alone, so any other ``OSError`` from
    the read — a permission denial, a path that is a directory — escaped
    ``cmd_domain_narrow`` as a traceback instead of the ``marshal_not_readable`` result
    the contract promises. The two sibling readers in the same module already caught
    ``OSError``; this pins that the config read now agrees with them.
    """
    _seed(plan_context, 'dn-marshal-unreadable', _CONFIGURED_DOMAINS)
    marshal_path: Path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.unlink()
    marshal_path.mkdir()

    result = cmd_domain_narrow(_ns('dn-marshal-unreadable', _PY_FOOTPRINT))

    assert result['status'] == 'error'
    assert result['error'] == 'marshal_not_readable'


def test_help_lists_both_flags(monkeypatch, capsys):
    """`domain-narrow --help` advertises --plan-id and --affected-files."""
    monkeypatch.setattr(sys, 'argv', ['manage-config.py', 'domain-narrow', '--help'])
    with pytest.raises(SystemExit):
        _mc.main()

    out = capsys.readouterr().out
    assert '--plan-id' in out
    assert '--affected-files' in out
