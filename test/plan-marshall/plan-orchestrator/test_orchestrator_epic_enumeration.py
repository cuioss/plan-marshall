#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``corpus epics`` — the derived enumeration of the epic population.

The one slug-free sub-verb of the ``corpus`` group, and the only one that walks
both store homes rather than a single named epic's tree. It lives apart from
``test_orchestrator_corpus.py`` because its subject is a directory WALK over a
main-anchored store, so its fixtures build store roots rather than the
scaffolded fixture epic the rest of the group shares.

Its controls are fixture-driven for the same reason as the rest of the group:
the live developer store's epic set changes between runs, so an assertion
against it would be untestable rather than merely brittle. Every guarding
assertion publishes the population it was derived from, so no check can pass
vacuously against a fixture that failed to land.

Three properties carry matched controls rather than a single happy path:

- The published counts are derived from the lists actually RETURNED, so a total
  cannot drift away from the population it names, and a slug present in both
  homes separates the row count from the distinct union.
- The two ways a root yields no slugs mean opposite things. An EMPTY root is a
  derived zero that still names the directory it walked; an ABSENT root is a
  different state with its own control. Neither is an error.
- The walk drops nothing. A non-directory entry and an entry whose type cannot
  be read are each proven to be REPORTED, with the row's own scanned count
  checked against the total partition rather than taken on trust.

The main-anchoring pair closes with a discriminator: redirecting only
``resolve_main_anchored_path`` moves both roots, so a root built from the
cwd-relative base path instead would stay put and fail the assertion.
"""

from pathlib import Path

import file_ops

from conftest import get_script_path, load_script_module, parse_ns, run_script

#: The orchestrator script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

_orch = load_script_module(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script'
)

cmd_corpus_epics = _orch.cmd_corpus_epics
SCOPE_ACTIVE = _orch.SCOPE_ACTIVE
SCOPE_ARCHIVED = _orch.SCOPE_ARCHIVED

#: The ``corpus epics`` namespace, built by the orchestrator's OWN parser so it
#: carries every default the production CLI applies — the verb takes no
#: ``--slug``, and the hand-built empty namespace it replaces carried neither the
#: ``command`` / ``corpus_action`` discriminators nor the resolved ``handler``.
#: Hoisted to module scope because ``parse_ns`` re-executes the script module on
#: every call, and ``register=False`` so it cannot displace the explicitly-named
#: registration above.
_EPICS_ARGS = parse_ns(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT,
    'corpus', 'epics',
    register=False,
)

#: The seeded epic population, named rather than inlined so every count
#: assertion below can state the population it was derived from instead of
#: comparing two hand-written numbers that drift apart independently.
_ACTIVE_EPICS = ('fixture-alpha-epic', 'fixture-beta-epic')
_ARCHIVED_EPICS = ('fixture-gamma-epic',)


def _store_roots(plan_context) -> tuple[Path, Path]:
    """The two store-home paths under ``PLAN_BASE_DIR`` isolation."""
    base = Path(plan_context.fixture_dir)
    return base / 'orchestrator', base / 'archived-orchestrators'


def _seed_epic_population(
    plan_context,
    active: tuple = _ACTIVE_EPICS,
    archived: tuple = _ARCHIVED_EPICS,
) -> tuple[Path, Path]:
    """Materialize epic directories in both store homes.

    A home named by an EMPTY tuple is left untouched rather than created empty —
    the absent and empty states are different fixtures with different controls,
    so the builder must never silently collapse one into the other.
    """
    active_root, archived_root = _store_roots(plan_context)
    for slug in active:
        (active_root / slug).mkdir(parents=True, exist_ok=True)
    for slug in archived:
        (archived_root / slug).mkdir(parents=True, exist_ok=True)
    return active_root, archived_root


def _roots_by_scope(result: dict) -> dict:
    """Index the published ``roots[]`` rows by scope, never by list position."""
    return {row['scope']: row for row in result['roots']}


class TestCorpusEpicsPopulation:
    def test_should_report_both_homes_of_a_materialized_population(self, plan_context):
        """Non-empty-population guard: a fixture that did not land must fail loudly."""
        _seed_epic_population(plan_context)

        result = cmd_corpus_epics(_EPICS_ARGS)

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-epics'
        assert result['active'] == sorted(_ACTIVE_EPICS), (
            'the active fixture epics did not materialize'
        )
        assert result['archived'] == sorted(_ARCHIVED_EPICS), (
            'the archived fixture epics did not materialize'
        )

    def test_the_published_total_equals_the_lists_actually_returned(self, plan_context):
        """The count cannot drift from the population it names."""
        _seed_epic_population(plan_context)

        result = cmd_corpus_epics(_EPICS_ARGS)

        # Derived from the RETURNED lists, not from the seeded constants: a total
        # computed independently of its own lists is exactly the drift this pins.
        assert result['active_count'] == len(result['active'])
        assert result['archived_count'] == len(result['archived'])
        assert result['total_count'] == len(result['active']) + len(result['archived'])
        seeded = len(_ACTIVE_EPICS) + len(_ARCHIVED_EPICS)
        assert result['total_count'] == seeded, (
            f'{result["total_count"]} reported over a seeded population of {seeded}'
        )

    def test_a_slug_in_both_homes_separates_total_from_distinct(self, plan_context):
        # A partially relocated epic. The row population and the union disagree
        # here, which is the whole reason both are published.
        both = 'fixture-relocating-epic'
        _seed_epic_population(plan_context, active=(both,), archived=(both,))

        result = cmd_corpus_epics(_EPICS_ARGS)

        assert result['active'] == [both]
        assert result['archived'] == [both]
        assert result['total_count'] == 2, 'the row population must count each home'
        assert result['distinct_count'] == 1, 'the union must collapse the duplicate'


class TestCorpusEpicsDerivedZero:
    """The two ways a root yields no slugs mean opposite things."""

    def test_an_empty_store_root_returns_a_zero_that_names_the_walked_root(self, plan_context):
        """Matched negative control: EMPTY is a derived zero, not an error."""
        active_root, archived_root = _store_roots(plan_context)
        active_root.mkdir(parents=True)
        archived_root.mkdir(parents=True)

        result = cmd_corpus_epics(_EPICS_ARGS)

        rows = _roots_by_scope(result)
        assert result['status'] == 'success', 'an empty store is not a failure'
        assert result['total_count'] == 0
        assert result['entries_scanned'] == 0
        assert len(rows) == 2, f'{len(rows)} root row(s) published, expected both homes'
        for scope, root in ((SCOPE_ACTIVE, active_root), (SCOPE_ARCHIVED, archived_root)):
            # The zero is ADDRESSED — it names the directory it was derived from.
            assert rows[scope]['path'] == str(root)
            assert rows[scope]['exists'] is True
            assert rows[scope]['listed'] is True
            assert rows[scope]['error'] == ''
            assert rows[scope]['entries_scanned'] == 0

    def test_an_absent_store_root_is_distinguished_from_an_empty_one(self, plan_context):
        active_root, _ = _store_roots(plan_context)
        assert not active_root.exists(), (
            'the fixture pre-created the root under test — the absent state is unreachable'
        )

        result = cmd_corpus_epics(_EPICS_ARGS)

        rows = _roots_by_scope(result)
        assert result['status'] == 'success'
        assert result['total_count'] == 0
        assert rows[SCOPE_ACTIVE]['exists'] is False, 'an absent root must not report as present'
        assert rows[SCOPE_ACTIVE]['listed'] is False
        assert rows[SCOPE_ACTIVE]['error'] == '', (
            'an absent root is a derived zero, not a failure to read'
        )
        # Absent, but still named — the caller can see WHICH directory was missing.
        assert rows[SCOPE_ACTIVE]['path'] == str(active_root)


class TestCorpusEpicsDropsNothing:
    """Every entry the walk saw is accounted for in exactly one population."""

    def test_a_non_directory_entry_is_reported_rather_than_dropped(self, plan_context):
        active_root, _ = _seed_epic_population(plan_context, archived=())
        (active_root / '.DS_Store').write_text('', encoding='utf-8')

        result = cmd_corpus_epics(_EPICS_ARGS)

        rows = _roots_by_scope(result)
        assert result['non_directory_count'] == 1
        assert result['non_directory'][0] == {'scope': SCOPE_ACTIVE, 'entry': '.DS_Store'}
        assert result['active'] == sorted(_ACTIVE_EPICS), (
            'a stray file must not disturb the slug list'
        )
        # The partition is TOTAL, so the row's own scanned count is checkable
        # against the three populations rather than taken on trust.
        assert rows[SCOPE_ACTIVE]['entries_scanned'] == len(_ACTIVE_EPICS) + 1
        assert rows[SCOPE_ACTIVE]['entries_scanned'] == (
            result['active_count'] + result['non_directory_count'] + result['unreadable_count']
        )

    def test_an_unreadable_entry_is_reported_rather_than_dropped(self, plan_context, monkeypatch):
        active_root, _ = _seed_epic_population(plan_context, archived=())
        unreadable_name = _ACTIVE_EPICS[0]
        real_is_dir = Path.is_dir

        def _raising_is_dir(self):
            # Scoped to ONE entry so every other stat in the call still resolves
            # normally — a blanket raise would prove nothing about this branch.
            if self.name == unreadable_name and self.parent == active_root:
                raise PermissionError(13, 'Permission denied')
            return real_is_dir(self)

        monkeypatch.setattr(Path, 'is_dir', _raising_is_dir)

        result = cmd_corpus_epics(_EPICS_ARGS)

        assert result['unreadable_count'] == 1, (
            f'{result["unreadable_count"]} unreadable entry reported over a seeded '
            f'population of {len(_ACTIVE_EPICS)} — an entry whose type cannot be '
            'read must never be silently dropped'
        )
        row = result['unreadable'][0]
        assert row['scope'] == SCOPE_ACTIVE
        assert row['entry'] == unreadable_name
        assert 'Permission denied' in row['error']
        # It is reported INSTEAD of being counted as an epic, not in addition.
        assert unreadable_name not in result['active']
        assert result['active_count'] == len(_ACTIVE_EPICS) - 1


class TestCorpusEpicsResolvesMainAnchored:
    """The store is main-anchored, so the walk must not move with the cwd."""

    def test_both_roots_resolve_through_the_main_anchored_resolver(
        self, plan_context, monkeypatch, tmp_path
    ):
        """Discriminator: a cwd-relative root would not follow this stub.

        Redirecting ONLY ``resolve_main_anchored_path`` moves both roots. A root
        built from the cwd-relative ``base_path`` instead would stay put, so this
        fails if the enumeration ever stops routing through the anchored resolver.
        """
        anchored = tmp_path / 'main-anchor'
        monkeypatch.setattr(
            file_ops, 'resolve_main_anchored_path', lambda subpath: anchored / str(subpath)
        )

        result = cmd_corpus_epics(_EPICS_ARGS)

        rows = _roots_by_scope(result)
        assert len(rows) == 2, f'{len(rows)} root row(s) published, expected both homes'
        assert rows[SCOPE_ACTIVE]['path'] == str(anchored / 'orchestrator')
        assert rows[SCOPE_ARCHIVED]['path'] == str(anchored / 'archived-orchestrators')

    def test_the_roots_do_not_move_with_the_working_directory(
        self, plan_context, monkeypatch, tmp_path
    ):
        """A worktree and the main checkout must resolve the SAME store root."""
        _seed_epic_population(plan_context)
        before = cmd_corpus_epics(_EPICS_ARGS)
        worktree = tmp_path / 'checkout' / '.plan' / 'local' / 'worktrees' / 'fixture-worktree'
        worktree.mkdir(parents=True)
        monkeypatch.chdir(worktree)

        after = cmd_corpus_epics(_EPICS_ARGS)

        assert len(after['roots']) == 2
        assert [row['path'] for row in after['roots']] == [
            row['path'] for row in before['roots']
        ], 'the store root moved with the cwd — the enumeration is not main-anchored'
        # The population is non-empty on both sides, so this is two agreeing
        # readings of a real store rather than two agreeing empties.
        assert after['total_count'] == before['total_count'] == len(_ACTIVE_EPICS) + len(
            _ARCHIVED_EPICS
        )


class TestCorpusEpicsCli:
    """One CLI-plumbing smoke — the in-process tests above are authoritative."""

    def test_should_enumerate_epics_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_epic_population(plan_context)

        result = run_script(SCRIPT_PATH, 'corpus', 'epics', env_overrides=env)

        seeded = len(_ACTIVE_EPICS) + len(_ARCHIVED_EPICS)
        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert f'total_count: {seeded}' in result.stdout
        assert f'active_count: {len(_ACTIVE_EPICS)}' in result.stdout
