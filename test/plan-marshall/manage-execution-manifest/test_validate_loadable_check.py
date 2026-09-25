# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_validate_loadable_fixtures import (
    _EMITTER,
    _mem,
    _validate_loadable_ns,
    cmd_validate_loadable,
)

# =============================================================================
# Seed-order guard (--check-seed) — reads marshal.json directly
# =============================================================================


class TestCheckSeedMode:
    def test_inverted_seed_returns_seed_order_inversion(self, plan_context, monkeypatch):
        """A seed whose phase-6-finalize steps are inverted returns seed_order_inversion."""
        # An inversion: sync-plugin-cache (85) precedes deploy-target (80).
        inverted = [
            'default:push',
            'project:finalize-step-sync-plugin-cache',
            'project:finalize-step-deploy-target',
        ]
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: inverted)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-inverted', check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'seed_order_inversion'
        assert 'project:finalize-step-deploy-target' in result['message']
        assert 'project:finalize-step-sync-plugin-cache' in result['message']

    def test_correct_seed_passes(self, plan_context, monkeypatch):
        """A seed with ascending phase-6-finalize order returns success."""
        ascending = [
            'default:push',
            'default:create-pr',
            'project:finalize-step-deploy-target',
            'project:finalize-step-sync-plugin-cache',
        ]
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: ascending)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-ok', check_seed=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_count'] == len(ascending)
        assert 'error' not in result

    def test_unreadable_seed_returns_seed_unreadable(self, plan_context, monkeypatch):
        """When the seed cannot be read, the mode returns seed_unreadable."""
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: None)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-missing', check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'seed_unreadable'

    def test_check_seed_reads_phase_6_finalize_key(self, plan_context, monkeypatch):
        """--check-seed sources steps from the phase-6-finalize marshal key."""
        seen: list[str] = []

        def _spy(phase_key):
            seen.append(phase_key)
            return ['default:push']

        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', _spy)
        cmd_validate_loadable(_validate_loadable_ns('vl-seed-key', check_seed=True))
        assert seen == ['phase-6-finalize']

    def test_check_seed_reads_keyed_map_keys_from_real_marshal(self, plan_context):
        """--check-seed reads ordered step ids from the keyed-map marshal.json (real read).

        Exercises _read_marshal_phase_steps against an actual on-disk marshal.json
        carrying the id-keyed steps map (not a monkeypatched list). The reader must
        return the map's keys in insertion order, so an ascending keyed map passes
        the seed-order guard.
        """
        import json

        marshal_path = plan_context.fixture_dir / 'marshal.json'
        # keyed-map steps with ascending frontmatter order; key insertion order
        # is the execution order. branch-cleanup carries nested params (ignored by
        # the seed-order guard, which only inspects ordering).
        data = {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:create-pr': {},
                        'project:finalize-step-deploy-target': {},
                        'project:finalize-step-sync-plugin-cache': {},
                    }
                }
            }
        }
        marshal_path.write_text(json.dumps(data), encoding='utf-8')

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-real-map', check_seed=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_count'] == 4

    def test_read_marshal_phase_steps_returns_keyed_map_keys(self, plan_context):
        """_read_marshal_phase_steps returns the keyed map's keys in insertion order."""
        import json

        marshal_path = plan_context.fixture_dir / 'marshal.json'
        data = {
            'plan': {
                'phase-5-execute': {
                    'verification_steps': {
                        'default:verify:quality-gate': {},
                        'default:verify:module-tests': {},
                        'default:verify:coverage': {},
                    }
                }
            }
        }
        marshal_path.write_text(json.dumps(data), encoding='utf-8')

        steps = _mem._read_marshal_phase_steps('phase-5-execute')
        assert steps == [
            'default:verify:quality-gate',
            'default:verify:module-tests',
            'default:verify:coverage',
        ]

    def test_read_marshal_phase_steps_rejects_list_shape(self, plan_context):
        """_read_marshal_phase_steps rejects the LIST shape — the keyed map is the sole form.

        The canonical on-disk shape is the keyed map; a list value is not a valid
        on-disk form, so the reader returns ``None`` (no dual-form tolerance).
        """
        import json

        marshal_path = plan_context.fixture_dir / 'marshal.json'
        data = {
            'plan': {
                'phase-6-finalize': {
                    'steps': [
                        'default:push',
                        {'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 300}},
                    ]
                }
            }
        }
        marshal_path.write_text(json.dumps(data), encoding='utf-8')

        assert _mem._read_marshal_phase_steps('phase-6-finalize') is None

    def test_check_seed_is_mutually_exclusive_with_step_id(self, plan_context):
        """Supplying both --step-id and --check-seed is an invalid_arguments error."""
        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-both', step_id='push', check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'

    def test_check_seed_is_mutually_exclusive_with_all(self, plan_context):
        """Supplying both --all and --check-seed is an invalid_arguments error."""
        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-all', use_all=True, check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'



class TestCheckEmittedStepsAscendingOrder:
    """The post-compose gate over the FINAL composed ``phase_6.steps``."""

    def test_ascending_list_returns_none(self):
        assert _mem.check_emitted_steps_ascending_order(['push', 'create-pr', 'archive-plan']) is None

    def test_inversion_names_both_steps_of_the_pair(self):
        offender = _mem.check_emitted_steps_ascending_order(['create-pr', 'push'])
        assert offender is not None
        assert offender['reason'] == 'order_inversion'
        assert offender['step_id'] == 'push'
        assert 'push' in offender['message']
        assert 'create-pr' in offender['message']

    def test_bundle_skill_step_is_skipped_without_complaint(self):
        # Orderless by design — it neither breaks nor satisfies ascending order.
        assert (
            _mem.check_emitted_steps_ascending_order(['push', 'plan-marshall:plan-retrospective', 'archive-plan'])
            is None
        )

    def test_non_string_entries_are_left_to_the_schema_checks(self):
        assert _mem.check_emitted_steps_ascending_order(['push', 42, 'archive-plan']) is None

    def test_unresolvable_order_builtin_is_an_offence(self, monkeypatch):
        """The arm that closes the vacuous green.

        With the emitter's ``order:`` unreadable, the sort pins it at whatever
        index the candidate list gave it — a position nothing verified — and
        ``_check_ascending_order`` skips the pinned entry and reports NO offender:
        the exact silent pass. This gate must report it.
        """
        import _manifest_validation as _mv

        real_read = _mv._read_frontmatter_order
        monkeypatch.setattr(
            _mv,
            '_read_frontmatter_order',
            lambda path: None if path.name == f'{_EMITTER}.md' else real_read(path),
        )
        pinned = _mv._sort_steps_by_frontmatter_order(['push', 'branch-cleanup', _EMITTER])
        # Reproduce the silent-pass precondition: the entry stays pinned at its
        # candidate-list index AND the legacy walk sees nothing wrong.
        assert pinned.index(_EMITTER) > pinned.index('branch-cleanup')
        assert _mv._check_ascending_order(pinned) is None

        offender = _mv.check_emitted_steps_ascending_order(pinned)
        assert offender is not None
        assert offender['reason'] == 'unresolvable_order'
        assert offender['step_id'] == _EMITTER
        assert 'no resolvable frontmatter `order`' in offender['message']
        assert 'declares no integer `order:` key' in offender['message']

    def test_unresolvable_source_reports_the_other_cause(self):
        offender = _mem.check_emitted_steps_ascending_order(['push', 'ghost-step-that-does-not-exist'])
        assert offender is not None
        assert offender['reason'] == 'unresolvable_order'
        assert 'source file could not be resolved' in offender['message']

    def test_first_offender_wins_in_list_order(self):
        offender = _mem.check_emitted_steps_ascending_order(['archive-plan', 'push', 'ghost-step-that-does-not-exist'])
        assert offender is not None
        # The inversion at index 1 precedes the unresolvable entry at index 2.
        assert offender['reason'] == 'order_inversion'
        assert offender['step_id'] == 'push'
