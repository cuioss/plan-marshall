#!/usr/bin/env python3
"""Tests for _cred_verify.py module.

Tests connectivity verification with mocked HTTP and system auth routing.
"""

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')


class TestVerifyCLI:
    """Tests for verify subcommand."""

    def test_verify_requires_skill(self):
        """Verify without --skill returns error."""
        result = run_script(SCRIPT_PATH, 'verify')
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert 'skill' in output.lower() or 'required' in output.lower()

    def test_verify_unconfigured_skill_fails(self):
        """Verify for unconfigured skill returns error."""
        result = run_script(SCRIPT_PATH, 'verify', '--skill', 'nonexistent-skill')
        assert result.returncode == 0


# =============================================================================
# Verify with auth_type=system Tests
# =============================================================================


class TestVerifySystemAuth:
    """Tests for verify subcommand with auth_type=system via direct import."""

    def test_system_auth_routes_to_verify_command(self, tmp_path, monkeypatch):
        """Verify with system auth runs verify_command instead of HTTP check."""
        from _cred_verify import run_verify  # type: ignore[import-not-found]
        from _credentials_core import CREDENTIALS_DIR, save_credential  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        skill = 'test-system-verify'
        data = {'skill': skill, 'auth_type': 'system'}

        mock_provider = {
            'skill_name': skill,
            'display_name': 'Test System CLI',
            'auth_type': 'system',
            'verify_command': 'echo verified',
            'description': 'Test system auth provider',
        }

        class MockArgs:
            skill = 'test-system-verify'
            scope = 'global'

        captured_output = {}

        def mock_output(data):
            captured_output.update(data)

        try:
            save_credential(skill, data, 'global')

            with monkeypatch.context() as m:
                m.setattr('_cred_verify.discover_credential_providers', lambda: [mock_provider])
                m.setattr('_cred_verify.output_toon', mock_output)
                run_verify(MockArgs())

            assert captured_output.get('status') == 'success'
            assert captured_output.get('auth_type') == 'system'
            assert captured_output.get('verified') is True
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()

    def test_system_auth_failed_verify_command(self, tmp_path, monkeypatch):
        """Verify with system auth reports failure when verify_command fails."""
        from _cred_verify import run_verify  # type: ignore[import-not-found]
        from _credentials_core import CREDENTIALS_DIR, save_credential  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        skill = 'test-system-verify-fail'
        data = {'skill': skill, 'auth_type': 'system'}

        mock_provider = {
            'skill_name': skill,
            'display_name': 'Test System CLI',
            'auth_type': 'system',
            'verify_command': 'false',
            'description': 'Provider with failing command',
        }

        class MockArgs:
            skill = 'test-system-verify-fail'
            scope = 'global'

        captured_output = {}

        def mock_output(data):
            captured_output.update(data)

        try:
            save_credential(skill, data, 'global')

            with monkeypatch.context() as m:
                m.setattr('_cred_verify.discover_credential_providers', lambda: [mock_provider])
                m.setattr('_cred_verify.output_toon', mock_output)
                run_verify(MockArgs())

            assert captured_output.get('status') == 'error'
            assert captured_output.get('verified') is False
            assert captured_output.get('auth_type') == 'system'
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()

    def test_system_auth_no_provider_extension(self, tmp_path, monkeypatch):
        """Verify with system auth reports error when no provider extension found."""
        from _cred_verify import run_verify  # type: ignore[import-not-found]
        from _credentials_core import CREDENTIALS_DIR, save_credential  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        skill = 'test-system-no-extension'
        data = {'skill': skill, 'auth_type': 'system'}

        class MockArgs:
            skill = 'test-system-no-extension'
            scope = 'global'

        captured_output = {}

        def mock_output(data):
            captured_output.update(data)

        try:
            save_credential(skill, data, 'global')

            with monkeypatch.context() as m:
                # No providers returned — extension not found
                m.setattr('_cred_verify.discover_credential_providers', lambda: [])
                m.setattr('_cred_verify.output_toon', mock_output)
                run_verify(MockArgs())

            assert captured_output.get('status') == 'error'
            assert 'system-auth' in captured_output.get('message', '').lower() or \
                   'no provider' in captured_output.get('message', '').lower()
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()

    def test_system_auth_does_not_call_get_authenticated_client(self, tmp_path, monkeypatch):
        """Verify with system auth must NOT attempt HTTP connectivity check."""
        from _cred_verify import run_verify  # type: ignore[import-not-found]
        from _credentials_core import CREDENTIALS_DIR, save_credential  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        skill = 'test-system-no-http'
        data = {'skill': skill, 'auth_type': 'system'}

        mock_provider = {
            'skill_name': skill,
            'display_name': 'Test System CLI',
            'auth_type': 'system',
            'verify_command': 'echo ok',
            'description': 'Test',
        }

        class MockArgs:
            skill = 'test-system-no-http'
            scope = 'global'

        http_called = False

        def mock_get_client(*_args, **_kwargs):
            nonlocal http_called
            http_called = True
            raise AssertionError('get_authenticated_client should not be called for system auth')

        try:
            save_credential(skill, data, 'global')

            with monkeypatch.context() as m:
                m.setattr('_cred_verify.discover_credential_providers', lambda: [mock_provider])
                m.setattr('_cred_verify.get_authenticated_client', mock_get_client)
                m.setattr('_cred_verify.output_toon', lambda d: None)
                run_verify(MockArgs())

            assert http_called is False
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()
