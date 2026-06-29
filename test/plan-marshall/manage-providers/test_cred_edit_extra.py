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

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')

_SKILL = 'plan-marshall:workflow-integration-sonar'
_TOKEN = 'super-secret-token-value'


def _seed_token_credential(skill: str = _SKILL, token: str = _TOKEN) -> None:
    """Persist a token credential into the per-test sandbox credential store."""
    from _providers_core import save_credential  # type: ignore[import-not-found]

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

    def test_upsert_adds_new_key(self):
        """An absent key is added to the provider config."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

        # Act
        upserted = _upsert_extra_fields(_SKILL, ['organization=my-org'])

        # Assert
        assert upserted == ['organization']
        assert read_provider_config(_SKILL).get('organization') == 'my-org'

    def test_repeated_upsert_same_key_is_idempotent(self):
        """Repeating the same pair leaves the provider config unchanged."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

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
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

        # Act
        _upsert_extra_fields(_SKILL, ['organization=old-org'])
        _upsert_extra_fields(_SKILL, ['organization=new-org'])

        # Assert
        assert read_provider_config(_SKILL).get('organization') == 'new-org'

    def test_upsert_preserves_other_extras(self):
        """Upserting one key leaves unrelated existing extras intact."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
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

    def test_pairs_without_equals_are_ignored(self):
        """A token lacking ``=`` is skipped and triggers no write."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

        # Act
        upserted = _upsert_extra_fields(_SKILL, ['no-equals-here'])

        # Assert — nothing upserted, config stays empty.
        assert upserted == []
        assert read_provider_config(_SKILL) == {}

    def test_empty_pairs_returns_empty(self):
        """An empty pair list is a no-op returning no keys."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

        # Act
        upserted = _upsert_extra_fields(_SKILL, [])

        # Assert
        assert upserted == []
        assert read_provider_config(_SKILL) == {}

    def test_upsert_returns_keys_in_supplied_order(self):
        """Multiple pairs are reported in the order supplied."""
        # Arrange
        from _cred_edit import _upsert_extra_fields  # type: ignore[import-not-found]

        # Act
        upserted = _upsert_extra_fields(_SKILL, ['project_key=pk', 'organization=org'])

        # Assert
        assert upserted == ['project_key', 'organization']


class TestRunEditPreservesToken:
    """Direct-import tests for ``run_edit`` token preservation across extra upserts."""

    def test_edit_extra_preserves_token(self):
        """Editing extras keeps the stored token untouched."""
        # Arrange
        from _cred_edit import run_edit  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
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
        from _cred_edit import run_edit  # type: ignore[import-not-found]
        from _providers_core import load_credential  # type: ignore[import-not-found]

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
        from _cred_edit import run_edit  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
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
        from _cred_edit import run_edit  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
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
        from _cred_edit import run_edit  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
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
        from _providers_core import (  # type: ignore[import-not-found]
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
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

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
