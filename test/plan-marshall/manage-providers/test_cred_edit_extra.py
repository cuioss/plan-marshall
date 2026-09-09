#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the idempotent ``--extra`` upsert on ``credentials edit``.

Covers the ``_upsert_extra_fields`` helper and the ``run_edit`` flow added to
``_cred_edit.py``: extra ``KEY=VALUE`` fields are upserted into the provider
config under ``credentials_config.{skill}`` in marshal.json, idempotently
(repeating the same pairs yields the same end state) and WITHOUT touching the
credential file that stores the token.

Isolation relies on the autouse ``_plan_base_dir_sandbox`` and
``_credentials_dir_sandbox`` fixtures in ``test/conftest.py``: both redirect
``PLAN_BASE_DIR`` / ``CREDENTIALS_DIR`` (env + in-process module attrs) into a
fresh per-test tmp sandbox, so each test starts with an empty marshal.json and
credential store, and the env redirects propagate to the ``run_script``
subprocesses. No per-test monkeypatching of those paths is required.
"""

import argparse

import _providers_core
import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')

#: The secret-named keys ``apply_extra_passthrough`` refuses, read off the live
#: constant so the sweep below covers a key added to it without an edit here.
SECRET_PLACEHOLDERS = _providers_core.SECRET_PLACEHOLDERS

_SKILL = 'plan-marshall:workflow-integration-sonar'
_TOKEN = 'super-secret-token-value'


def _seed_token_credential(skill: str = _SKILL, token: str = _TOKEN) -> None:
    """Persist a token credential into the per-test sandbox credential store."""
    from _providers_core import save_credential

    save_credential(
        skill,
        {'skill': skill, 'auth_type': 'token', 'token': token},
        'global',
    )


def _edit_args(skill: str = _SKILL, extra: list[str] | None = None) -> argparse.Namespace:
    """Build the argparse Namespace ``run_edit`` consumes for a global-scope edit."""
    return argparse.Namespace(skill=skill, scope='global', url=None, auth_type=None, extra=extra)


class TestUpsertExtraFieldsIdempotent:
    """Direct-import tests for ``_upsert_extra_fields``."""

    @pytest.mark.parametrize(
        ('pairs', 'expected_keys', 'expected_config'),
        [
            (['organization=my-org'], ['organization'], {'organization': 'my-org'}),
            (['project_key=pk', 'organization=org'], ['project_key', 'organization'],
             {'project_key': 'pk', 'organization': 'org'}),
            (['no-equals-here'], [], {}),
            ([], [], {}),
        ],
        ids=[
            'an-absent-key-is-added',
            'several-keys-are-reported-in-the-order-supplied',
            'a-token-lacking-an-equals-sign-is-ignored',
            'an-empty-pair-list-is-a-no-op',
        ],
    )
    def test_a_single_upsert_reports_its_keys_and_persists_exactly_them(
        self, pairs, expected_keys, expected_config
    ):
        """One call reports the keys it accepted, and the config holds those keys alone."""
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import read_provider_config

        # Act
        upserted = _upsert_extra_fields(_SKILL, pairs)

        # Assert
        assert upserted == expected_keys
        assert read_provider_config(_SKILL) == expected_config

    def test_repeated_upsert_same_key_is_idempotent(self):
        """Repeating the same pair leaves the provider config unchanged."""
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import read_provider_config

        # Act
        _upsert_extra_fields(_SKILL, ['organization=my-org'])
        after_first = read_provider_config(_SKILL)
        second_keys = _upsert_extra_fields(_SKILL, ['organization=my-org'])
        after_second = read_provider_config(_SKILL)

        # Assert — same end state, and the second run still reports the key.
        assert after_first == after_second
        assert second_keys == ['organization']

    def test_upsert_replaces_existing_key_in_place(self):
        """A present key is replaced with the new value, not duplicated."""
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import read_provider_config

        # Act
        _upsert_extra_fields(_SKILL, ['organization=old-org'])
        _upsert_extra_fields(_SKILL, ['organization=new-org'])

        # Assert
        assert read_provider_config(_SKILL).get('organization') == 'new-org'

    def test_upsert_preserves_other_extras(self):
        """Upserting one key leaves unrelated existing extras intact."""
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import (
            read_provider_config,
            write_provider_config,
        )

        write_provider_config(_SKILL, {'organization': 'org', 'project_key': 'pk'})

        # Act
        _upsert_extra_fields(_SKILL, ['organization=new-org'])

        # Assert
        config = read_provider_config(_SKILL)
        assert config.get('organization') == 'new-org'
        assert config.get('project_key') == 'pk'


class TestUpsertExtraFieldsValidation:
    """Non-secret key validation guarding ``credentials_config`` writes."""

    @pytest.mark.parametrize(
        ('pairs', 'expected_keys', 'expected_config'),
        [
            (['=orphan-value'], [], {}),
            (['   =value'], [], {}),
            (['  organization  =my-org'], ['organization'], {'organization': 'my-org'}),
            (['token=should-not-persist'], [], {}),
            (['username=alice', 'password=hunter2'], [], {}),
            (['  token  =should-not-persist'], [], {}),
            (
                ['organization=my-org', 'token=secret', 'project_key=pk'],
                ['organization', 'project_key'],
                {'organization': 'my-org', 'project_key': 'pk'},
            ),
            (['organization=first', 'organization=second'], ['organization'],
             {'organization': 'second'}),
        ],
        ids=[
            'an-empty-key-persists-no-blank-entry',
            'a-whitespace-only-key-is-empty-once-stripped',
            'a-padded-key-is-stored-in-its-stripped-form',
            'the-secret-key-token-is-rejected',
            'the-secret-keys-username-and-password-are-both-rejected',
            'a-padded-secret-key-is-rejected-after-stripping',
            'a-secret-is-dropped-while-its-benign-neighbours-still-upsert',
            'a-key-supplied-twice-is-reported-once-and-the-last-value-wins',
        ],
    )
    def test_only_validated_keys_reach_the_provider_config(
        self, pairs, expected_keys, expected_config
    ):
        """Empty and secret-named keys never reach ``marshal.json``; the rest do.

        The config is asserted by exact equality rather than by key absence: the
        sandbox starts each test with an empty provider config, so equality states
        both what was rejected and what survived in one shape.
        """
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import read_provider_config

        # Act
        upserted = _upsert_extra_fields(_SKILL, pairs)

        # Assert
        assert upserted == expected_keys
        assert read_provider_config(_SKILL) == expected_config

    def test_the_secret_placeholder_set_is_not_empty(self):
        """``SECRET_PLACEHOLDERS`` carries at least one key.

        The sweep below is parametrized over that constant, so an emptied
        constant would collect zero rows and report green without having
        rejected anything. This is what makes the zero-row state a failure.
        """
        assert SECRET_PLACEHOLDERS, 'SECRET_PLACEHOLDERS is empty — the sweep below collects no rows'

    @pytest.mark.parametrize(
        'secret_key', sorted(SECRET_PLACEHOLDERS), ids=sorted(SECRET_PLACEHOLDERS)
    )
    def test_every_secret_placeholder_key_is_rejected(self, secret_key):
        """No key ``SECRET_PLACEHOLDERS`` names reaches ``marshal.json``.

        ``_upsert_extra_fields`` delegates the denylist to
        ``apply_extra_passthrough``, which checks that constant — so the rejected
        set is whatever the constant holds, not the three keys the literal rows
        above happen to name. Quantifying over it is what covers a secret key
        added later. The benign neighbour keeps the row from passing on an
        ``_upsert_extra_fields`` that rejected everything indiscriminately.
        """
        # Arrange
        from _cred_edit import _upsert_extra_fields
        from _providers_core import read_provider_config

        # Act
        upserted = _upsert_extra_fields(_SKILL, [f'{secret_key}=value', 'organization=my-org'])

        # Assert
        assert upserted == ['organization']
        assert read_provider_config(_SKILL) == {'organization': 'my-org'}


class TestRunEditPreservesToken:
    """Direct-import tests for ``run_edit`` token preservation across extra upserts."""

    def test_edit_extra_preserves_token(self):
        """Editing extras keeps the stored token untouched."""
        # Arrange
        from _cred_edit import run_edit
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        _seed_token_credential()

        # Act
        rc = run_edit(_edit_args(extra=['organization=my-org']))

        # Assert
        assert rc == 0
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert loaded['token'] == _TOKEN
        assert read_provider_config(_SKILL).get('organization') == 'my-org'

    def test_edit_does_not_write_extras_into_credential_file(self):
        """Extras land in marshal.json, never in the credential file."""
        # Arrange
        from _cred_edit import run_edit
        from _providers_core import load_credential

        _seed_token_credential()

        # Act
        run_edit(_edit_args(extra=['organization=my-org', 'project_key=pk']))

        # Assert — credential file holds only the secret, not the extras.
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert 'organization' not in loaded
        assert 'project_key' not in loaded
        assert loaded['token'] == _TOKEN

    def test_repeated_edit_extra_idempotent_and_token_preserved(self):
        """Two identical extra edits converge and keep the token."""
        # Arrange
        from _cred_edit import run_edit
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        _seed_token_credential()

        # Act
        run_edit(_edit_args(extra=['organization=my-org']))
        first_config = read_provider_config(_SKILL)
        run_edit(_edit_args(extra=['organization=my-org']))
        second_config = read_provider_config(_SKILL)

        # Assert
        assert first_config == second_config
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert loaded['token'] == _TOKEN

    def test_token_preserved_across_sequential_distinct_extra_mutations(self):
        """The token survives a sequence of distinct extra-key mutations."""
        # Arrange
        from _cred_edit import run_edit
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        _seed_token_credential()

        # Act — mutate one extra key per edit, in sequence.
        run_edit(_edit_args(extra=['organization=my-org']))
        run_edit(_edit_args(extra=['project_key=my-project']))

        # Assert — both extras present and the token is intact.
        config = read_provider_config(_SKILL)
        assert config.get('organization') == 'my-org'
        assert config.get('project_key') == 'my-project'
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert loaded['token'] == _TOKEN

    def test_edit_without_extra_leaves_provider_config_untouched(self):
        """An edit with no extras neither adds provider config nor drops the token."""
        # Arrange
        from _cred_edit import run_edit
        from _providers_core import (
            load_credential,
            read_provider_config,
            write_provider_config,
        )

        _seed_token_credential()
        write_provider_config(_SKILL, {'organization': 'org'})

        # Act
        run_edit(_edit_args(extra=None))

        # Assert
        assert read_provider_config(_SKILL) == {'organization': 'org'}
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert loaded['token'] == _TOKEN


class TestEditCliExtra:
    """Subprocess tests exercising the ``edit --extra`` CLI wiring end-to-end."""

    def test_edit_help_documents_extra_upsert(self):
        """``edit --help`` advertises the idempotent extra upsert."""
        # Act
        result = run_script(SCRIPT_PATH, 'edit', '--help')

        # Assert
        assert result.returncode == 0
        assert '--extra' in result.stdout
        assert 'upsert' in result.stdout.lower()

    def test_edit_cli_upserts_extra_and_preserves_token(self):
        """The CLI edit upserts the extra and keeps the credential token."""
        # Arrange — seed a credential the subprocess will resolve via the shared
        # sandbox env (PLAN_MARSHALL_CREDENTIALS_DIR propagated by run_script).
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        _seed_token_credential()

        # Act
        result = run_script(
            SCRIPT_PATH,
            'edit',
            '--skill',
            _SKILL,
            '--extra',
            'organization=my-org',
        )

        # Assert
        assert result.returncode == 0, f'edit failed: {result.stdout}\n{result.stderr}'
        assert 'extras_upserted' in result.stdout
        assert read_provider_config(_SKILL).get('organization') == 'my-org'
        loaded = load_credential(_SKILL, 'global')
        assert loaded is not None
        assert loaded['token'] == _TOKEN

    def test_edit_cli_repeated_extra_is_idempotent(self):
        """Running the CLI edit twice with the same extra converges."""
        # Arrange
        from _providers_core import read_provider_config

        _seed_token_credential()

        # Act
        first = run_script(SCRIPT_PATH, 'edit', '--skill', _SKILL, '--extra', 'organization=my-org')
        config_after_first = read_provider_config(_SKILL)
        second = run_script(SCRIPT_PATH, 'edit', '--skill', _SKILL, '--extra', 'organization=my-org')
        config_after_second = read_provider_config(_SKILL)

        # Assert
        assert first.returncode == 0, f'first edit failed: {first.stdout}\n{first.stderr}'
        assert second.returncode == 0, f'second edit failed: {second.stdout}\n{second.stderr}'
        assert config_after_first == config_after_second
        assert config_after_second.get('organization') == 'my-org'
