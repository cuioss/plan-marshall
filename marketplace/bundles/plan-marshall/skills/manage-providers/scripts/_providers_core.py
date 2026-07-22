# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Core credential management infrastructure.

Provides path resolution, credential file I/O, provider loading,
authenticated REST client, and the RestClient class.

Security constraints:
- Credentials never appear in stdout, stderr, or TOON output
- File creation uses atomic os.open() with 0o600 permissions
- Path resolution validates against CREDENTIALS_DIR via os.path.realpath()
- Project names sanitized to prevent path traversal
- RestClient enforces HTTPS when auth headers are present
"""

import base64
import errno
import hashlib
import http.client
import json
import os
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from file_ops import get_marshal_path
from marketplace_paths import ensure_home_root, home_root, resolve_home

# === Constants ===

# Credentials live under the machine-global home root by default
# (``home_root()/credentials``). The explicit ``PLAN_MARSHALL_CREDENTIALS_DIR``
# override keeps highest precedence so the conftest test sandbox and operator
# overrides still win.
CREDENTIALS_DIR = (
    Path(os.environ['PLAN_MARSHALL_CREDENTIALS_DIR'])
    if os.environ.get('PLAN_MARSHALL_CREDENTIALS_DIR')
    else home_root() / 'credentials'
)
# Pre-home-root credentials location, retained ONLY as the lazy-migration source.
_OLD_CREDENTIALS_DIR = resolve_home() / '.plan-marshall-credentials'
VALID_AUTH_TYPES = ('none', 'token', 'basic', 'system')
SECRET_PLACEHOLDERS = {
    'token': 'REPLACE_WITH_YOUR_TOKEN',
    'username': 'REPLACE_WITH_YOUR_USERNAME',
    'password': 'REPLACE_WITH_YOUR_PASSWORD',
}
# Canonical keys managed on a dedicated validation/saving path — reject from --extra
# so they cannot be overwritten by a passthrough pair.
RESERVED_EXTRA_KEYS = {'url'}
_PROJECT_NAME_PATTERN = re.compile(r'[^a-zA-Z0-9._-]')


# === Marshal.json Provider Config ===
# marshal.json is tracked in the repo under .plan/; resolved via file_ops.


def _marshal_path() -> Path:
    return get_marshal_path()


def canonical_credentials_key(skill_name: str) -> str:
    """Return the canonical ``credentials_config`` storage key for a skill name.

    The canonical form is the bundle-prefix-stripped spelling — the same form
    ``resolve_credential_path`` uses for the credential filename — so the
    git-tracked ``credentials_config`` key and the credential file agree.

    Args:
        skill_name: Skill name, either bundle-prefixed
            (``plan-marshall:workflow-integration-sonar``) or bare
            (``workflow-integration-sonar``).

    Returns:
        The segment after the first ``':'`` when one is present, otherwise the
        supplied name verbatim.
    """
    if ':' in skill_name:
        return skill_name.split(':', 1)[1]
    return skill_name


def read_provider_config(skill_name: str) -> dict[str, Any]:
    """Read provider configuration from marshal.json.

    Provider config is stored under ``credentials_config.{canonical_key}``, but
    reads accept either spelling: an exact ``skill_name`` match is tried first,
    then a canonical-equality scan matches a key stored under the other
    spelling.

    Returns:
        Dict with provider config fields, or empty dict if not found.
    """
    marshal_path = _marshal_path()
    if not marshal_path.exists():
        return {}
    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
        credentials_config: dict[str, Any] = config.get('credentials_config', {})
        if skill_name in credentials_config:
            exact: dict[str, Any] = credentials_config[skill_name]
            return exact
        canonical = canonical_credentials_key(skill_name)
        for key, value in credentials_config.items():
            if canonical_credentials_key(key) == canonical:
                matched: dict[str, Any] = value
                return matched
        return {}
    except (json.JSONDecodeError, KeyError):
        return {}


def write_provider_config(skill_name: str, provider_config: dict[str, Any]) -> None:
    """Write provider configuration to marshal.json.

    Stores non-secret fields under ``credentials_config.{canonical_key}`` — the
    prefix-stripped spelling. Any pre-existing key whose canonical form equals
    the same value is removed first, so a re-configure never leaves two shadow
    blocks for one provider. Creates or updates the marshal.json file,
    preserving existing content.
    """
    marshal_path = _marshal_path()
    config: dict[str, Any] = {}
    if marshal_path.exists():
        try:
            config = json.loads(marshal_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            config = {}

    if 'credentials_config' not in config:
        config['credentials_config'] = {}
    credentials_config: dict[str, Any] = config['credentials_config']
    canonical = canonical_credentials_key(skill_name)
    for existing_key in [k for k in credentials_config if canonical_credentials_key(k) == canonical]:
        del credentials_config[existing_key]
    credentials_config[canonical] = provider_config

    # Route the top-level key order through the single authority in _config_core
    # so a freshly created ``credentials_config`` block lands in its canonical
    # slot rather than appended at end-of-object — otherwise the committed
    # marshal.json drifts out of the order ``save_config`` enforces and the next
    # save produces a spurious reorder diff. Imported lazily (executor sets the
    # cross-skill PYTHONPATH); no import cycle — _config_core never imports this
    # module.
    from _config_core import order_config_keys

    config = order_config_keys(config)

    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )


def apply_extra_passthrough(provider_config: dict[str, Any], extra_pairs: list[str]) -> list[str]:
    """Apply ``--extra KEY=VALUE`` passthrough into a provider config in place.

    This is the single guard shared by the ``configure`` and ``edit`` credential
    commands so the two accept and reject ``--extra`` keys identically. Because
    ``credentials_config`` is git-tracked and non-secret by intent, each pair is
    validated before it is written:

    - a pair without ``=`` is ignored,
    - the key is whitespace-stripped and an empty key is skipped,
    - a key naming a secret field (any key whose lower-cased form is in
      ``SECRET_PLACEHOLDERS`` — ``token``, ``username``, ``password``) is
      rejected case-insensitively, so neither ``token`` nor ``Token`` nor
      ``TOKEN`` can persist a secret into the git-tracked ``marshal.json`` via
      ``--extra``.

    The supplied ``provider_config`` is mutated in place; persistence
    (``write_provider_config``) is the caller's responsibility.

    Args:
        provider_config: The provider-config dict to update in place.
        extra_pairs: Repeatable ``KEY=VALUE`` strings.

    Returns:
        The deduplicated list of keys that were applied, in supplied order.
    """
    applied_keys: list[str] = []
    for pair in extra_pairs:
        if '=' not in pair:
            continue
        key, value = pair.split('=', 1)
        key = key.strip()
        if not key:
            continue
        normalized_key = key.lower()
        if normalized_key in SECRET_PLACEHOLDERS or normalized_key in RESERVED_EXTRA_KEYS:
            continue
        provider_config[key] = value
        if key not in applied_keys:
            applied_keys.append(key)
    return applied_keys


# === Path Resolution ===


def get_project_name() -> str:
    """Derive project name from marshal.json or cwd.

    When a version-control provider URL resolves, the name is the URL-derived
    repo name — UNCHANGED, so every existing ``{project_name}/`` credential
    subdir migrates verbatim. On the cwd-fallback branch (no version-control URL
    resolves), the bare ``Path.cwd().name`` is disambiguated with a short stable
    hash of the absolute cwd (``{name}-{hash8}``) so two different directories
    that happen to share a basename get distinct credential subdirs instead of
    silently colliding on one.

    Sanitizes the name to prevent path traversal attacks.
    """
    marshal_path = _marshal_path()

    repo_url = ''
    if marshal_path.exists():
        try:
            config = json.loads(marshal_path.read_text(encoding='utf-8'))
            # Find version-control provider for repo URL
            for p in config.get('providers', []):
                if p.get('category') == 'version-control':
                    repo_url = p.get('url', '')
                    break
        except (json.JSONDecodeError, KeyError):
            repo_url = ''

    if repo_url:
        # URL-derived branch — output UNCHANGED (last path segment, strip .git).
        name = repo_url.rstrip('/').rsplit('/', 1)[-1]
        if name.endswith('.git'):
            name = name[:-4]
        return _PROJECT_NAME_PATTERN.sub('', name)

    # cwd-fallback branch — disambiguate the bare basename with a short stable
    # hash of the absolute cwd path so distinct dirs sharing a basename do not
    # collide on one credential subdir.
    cwd = Path.cwd()
    digest = hashlib.sha256(str(cwd.resolve()).encode('utf-8')).hexdigest()[:8]
    return _PROJECT_NAME_PATTERN.sub('', f'{cwd.name}-{digest}')


def resolve_credential_path(skill: str, scope: str = 'global', project_name: str | None = None) -> Path:
    """Resolve credential file path with symlink protection.

    Args:
        skill: Skill name (used as filename)
        scope: 'global' or 'project'
        project_name: Project name for project-scoped credentials

    Returns:
        Resolved path under CREDENTIALS_DIR

    Raises:
        ValueError: If resolved path escapes CREDENTIALS_DIR
    """
    # Strip bundle prefix for filesystem path (skill_name may be "plan-marshall:workflow-integration-sonar")
    skill = canonical_credentials_key(skill)

    if scope == 'project':
        if not project_name:
            project_name = get_project_name()
        path = CREDENTIALS_DIR / project_name / f'{skill}.json'
    else:
        path = CREDENTIALS_DIR / f'{skill}.json'

    # Symlink protection: ensure resolved path is under CREDENTIALS_DIR
    real_cred_dir = os.path.realpath(str(CREDENTIALS_DIR))
    real_path = os.path.realpath(str(path))
    if not real_path.startswith(real_cred_dir + os.sep) and real_path != real_cred_dir:
        raise ValueError('Credential path escapes credentials directory')

    return path


def _migrate_credentials_home_if_needed() -> str:
    """Lazily migrate the pre-home-root credentials dir to the home-root path.

    Idempotent and best-effort — safe to call on every credential access.
    Returns a status literal ``'migrated' | 'already_migrated' | 'conflict'``
    (no secrets) so the ``migrate-home`` subcommand can report deterministically:

    - **Explicit override** — when ``PLAN_MARSHALL_CREDENTIALS_DIR`` is set the
      credentials location is operator/test-specified and authoritative; never
      migrate into or out of it (this also keeps the conftest sandbox inert).
      Reports ``already_migrated``.
    - **No-op** — when the new ``CREDENTIALS_DIR`` already exists (already
      migrated) or the old ``~/.plan-marshall-credentials`` is absent (nothing
      to migrate). Reports ``already_migrated``.
    - **Conflict** — when BOTH the old and new dirs exist, keep the new dir and
      never merge; emit a one-line stderr notice (paths only, no secrets) so an
      operator can remove the stale old dir manually. Reports ``conflict``.
    - **Migrate** — when only the old dir exists, ensure ``home_root()`` exists
      at 0700, then ``os.rename`` the old dir to the new path. A lost race with
      a concurrent migrator is swallowed and reports ``already_migrated``:
      ``FileNotFoundError`` (the old dir was moved first) and
      ``FileExistsError`` / ``OSError`` with ``errno`` in ``(EEXIST, ENOTEMPTY)``
      (a sibling created or populated the new dir between the ``exists()`` check
      and the rename). A cross-filesystem rename (``EXDEV``) falls back to
      ``shutil.move``, which copies then unlinks the source only after a
      successful copy and carries the same lost-race handling. Reports
      ``migrated``.
    """
    # The explicit override is authoritative — do not migrate.
    if os.environ.get('PLAN_MARSHALL_CREDENTIALS_DIR'):
        return 'already_migrated'

    new_dir = CREDENTIALS_DIR
    old_dir = _OLD_CREDENTIALS_DIR

    if new_dir.exists():
        # Already migrated, or a conflict where both are present. Never merge —
        # keep the new dir; flag the lingering old dir for manual cleanup.
        if old_dir.exists():
            print(
                f'WARNING: credentials migration conflict — both {old_dir} and '
                f'{new_dir} exist; keeping {new_dir} and leaving the old dir for '
                'manual review (no merge performed).',
                file=sys.stderr,
            )
            return 'conflict'
        return 'already_migrated'

    if not old_dir.exists():
        return 'already_migrated'  # nothing to migrate

    # Only the old dir exists → migrate it to the home-root location.
    ensure_home_root()
    try:
        os.rename(str(old_dir), str(new_dir))
    except FileNotFoundError:
        # Lost race: a concurrent migrator already moved the old dir.
        return 'already_migrated'
    except OSError as exc:
        if getattr(exc, 'errno', None) == errno.EXDEV:
            # Cross-filesystem: shutil.move copies then removes the source only
            # after a successful copy. The move itself carries the same lost-race
            # exposure as os.rename, so mirror the handling here.
            try:
                shutil.move(str(old_dir), str(new_dir))
            except FileNotFoundError:
                # Lost race: a concurrent migrator already moved the old dir.
                return 'already_migrated'
            except OSError as move_exc:
                if getattr(move_exc, 'errno', None) in (errno.EEXIST, errno.ENOTEMPTY):
                    # Lost race: a sibling migrator created/populated new_dir
                    # between our exists() check and this move.
                    return 'already_migrated'
                raise
        elif getattr(exc, 'errno', None) in (errno.EEXIST, errno.ENOTEMPTY):
            # Lost race: a sibling migrator created CREDENTIALS_DIR (possibly
            # empty, then started populating it) between our new_dir.exists()
            # check and this os.rename. FileExistsError (errno EEXIST) and a
            # non-empty-target rename (errno ENOTEMPTY) both mean the new dir
            # is already claimed — treat identically to the FileNotFoundError
            # lost-race case rather than crashing.
            return 'already_migrated'
        else:
            raise
    return 'migrated'


def ensure_credentials_dir(scope: str = 'global', project_name: str | None = None) -> Path:
    """Ensure credentials directory exists with correct permissions.

    Lazily migrates the pre-home-root credentials dir first, then creates
    ``CREDENTIALS_DIR`` (``home_root()/credentials`` by default) with chmod 700.
    For project scope, also creates the project subdirectory.
    """
    _migrate_credentials_home_if_needed()
    # Harden the home root itself before creating the leaf: mkdir's mode applies
    # only to the leaf, so a parents=True creation of CREDENTIALS_DIR would give
    # ~/.plan-marshall umask-default permissions. Skipped under the explicit
    # PLAN_MARSHALL_CREDENTIALS_DIR override (test sandbox / operator path).
    if not os.environ.get('PLAN_MARSHALL_CREDENTIALS_DIR'):
        ensure_home_root()
    CREDENTIALS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Verify permissions (in case directory already existed with wrong perms)
    current_mode = CREDENTIALS_DIR.stat().st_mode & 0o777
    if current_mode != 0o700:
        os.chmod(str(CREDENTIALS_DIR), 0o700)

    if scope == 'project':
        if not project_name:
            project_name = get_project_name()
        project_dir = CREDENTIALS_DIR / project_name
        project_dir.mkdir(mode=0o700, exist_ok=True)
        return project_dir

    return CREDENTIALS_DIR


# === Credential File I/O ===


def load_credential(skill: str, scope: str = 'global', project_name: str | None = None) -> dict | None:
    """Load credential from file.

    Resolution order for scope='auto': project-scoped first, then global.

    Returns:
        Credential dict or None if not found.
        Never includes file content in error messages.
    """
    if scope == 'auto':
        # Try project first, then global
        result = load_credential(skill, 'project', project_name)
        if result:
            return result
        return load_credential(skill, 'global', project_name)

    try:
        path = resolve_credential_path(skill, scope, project_name)
        if not path.exists():
            return None
        data: dict = json.loads(path.read_text(encoding='utf-8'))
        return data
    except json.JSONDecodeError:
        # Never expose file content in error messages
        return None
    except ValueError:
        return None


def save_credential(skill: str, data: dict, scope: str = 'global', project_name: str | None = None) -> Path:
    """Save credential to file with atomic creation and correct permissions.

    Uses os.open() with O_WRONLY|O_CREAT|O_TRUNC and mode 0o600 to
    eliminate umask race window.

    Returns:
        Path to the created credential file

    Raises:
        OSError: If file creation or permission verification fails
    """
    ensure_credentials_dir(scope, project_name)
    path = resolve_credential_path(skill, scope, project_name)

    # Atomic file creation with explicit permissions (no umask race)
    content = json.dumps(data, indent=2).encode('utf-8')
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)

    # Post-write verification
    actual_mode = os.stat(str(path)).st_mode & 0o777
    if actual_mode != 0o600:
        raise OSError(f'Permission verification failed: expected 0600, got {oct(actual_mode)}')

    return path


def remove_credential(skill: str, scope: str = 'global', project_name: str | None = None) -> bool:
    """Remove credential file.

    Returns:
        True if file was removed, False if not found
    """
    try:
        path = resolve_credential_path(skill, scope, project_name)
        if path.exists():
            path.unlink()
            return True
        return False
    except ValueError:
        return False


def check_credential_completeness(skill: str, scope: str = 'global', project_name: str | None = None) -> dict:
    """Check if a credential file exists and has all secrets filled in.

    Returns:
        Dict with keys: exists, complete, path, placeholders
    """
    try:
        path = resolve_credential_path(skill, scope, project_name)
    except ValueError:
        return {'exists': False, 'complete': False, 'path': '', 'placeholders': []}

    if not path.exists():
        return {'exists': False, 'complete': False, 'path': str(path), 'placeholders': []}

    data = load_credential(skill, scope, project_name)
    if data is None:
        return {'exists': True, 'complete': False, 'path': str(path), 'placeholders': []}

    placeholder_values = set(SECRET_PLACEHOLDERS.values())
    found_placeholders = [key for key, val in data.items() if isinstance(val, str) and val in placeholder_values]

    # Also check for missing or empty required fields based on auth type
    auth_type = data.get('auth_type', 'none')
    if auth_type == 'token':
        if not data.get('token') and 'token' not in found_placeholders:
            found_placeholders.append('token')
    elif auth_type == 'basic':
        if not data.get('username') and 'username' not in found_placeholders:
            found_placeholders.append('username')
        if not data.get('password') and 'password' not in found_placeholders:
            found_placeholders.append('password')

    return {
        'exists': True,
        'complete': len(found_placeholders) == 0,
        'path': str(path),
        'placeholders': found_placeholders,
    }


def touch_verified_at(skill: str, scope: str = 'global', project_name: str | None = None) -> None:
    """Update verified_at timestamp inside the credential file itself.

    Loads the credential JSON, sets verified_at to the current UTC timestamp,
    and rewrites the file via save_credential (preserves atomic 0o600 semantics).
    No-op if the credential file does not exist.
    """
    data = load_credential(skill, scope, project_name)
    if not isinstance(data, dict):
        return
    data['verified_at'] = datetime.now(UTC).isoformat()
    save_credential(skill, data, scope, project_name)


# === Provider Loading (from marshal.json) ===


def load_declared_providers() -> list[dict[str, Any]]:
    """Load provider declarations from marshal.json.

    Reads the 'providers' list persisted by the discover-and-persist
    command. No filesystem scanning at runtime.

    Returns:
        List of provider declaration dicts, or empty list if not found.
    """
    marshal_path = _marshal_path()
    if not marshal_path.exists():
        return []
    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
        result: list[dict[str, Any]] = config.get('providers', [])
        return result
    except (json.JSONDecodeError, KeyError):
        return []


# === RestClient ===


class RestClientError(Exception):
    """HTTP error with status code and redacted response body."""

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body
        super().__init__(f'HTTP {status}: {body[:200]}')


class RestClient:
    """Pre-authenticated REST client. Credentials never leave this object.

    Security hardening:
    - HTTPS-only when auth headers present (rejects http://)
    - Tracebacks sanitized: _headers never appears in exception context
    - Error responses redacted to prevent token echo-back
    - Connection properly closed on errors
    """

    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    USER_AGENT = 'plan-marshall-rest/1.0'
    _SENSITIVE_PATTERN = re.compile(r'(token|bearer|password|secret|key)["\s:=]+\S+', re.IGNORECASE)

    def __init__(self, base_url: str, headers: dict) -> None:
        parsed = urllib.parse.urlparse(base_url)
        self.scheme = parsed.scheme

        # Security: reject HTTP when auth headers are present
        if self.scheme != 'https' and any(k.lower() == 'authorization' for k in headers):
            raise ValueError('HTTPS required when authentication is configured')

        self.host = parsed.hostname or 'localhost'
        self.port = parsed.port or (443 if self.scheme == 'https' else 80)
        self.base_path = (parsed.path or '').rstrip('/')
        self._headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
            **headers,
        }
        self._ssl_context = ssl.create_default_context()
        self._conn: http.client.HTTPSConnection | http.client.HTTPConnection | None = None
        self.url = base_url  # Expose base URL (no secrets)

    def _get_connection(self) -> http.client.HTTPSConnection | http.client.HTTPConnection:
        """Get or create connection with reuse."""
        if self._conn is None:
            if self.scheme == 'https':
                self._conn = http.client.HTTPSConnection(
                    self.host,
                    self.port,
                    context=self._ssl_context,
                    timeout=self.DEFAULT_TIMEOUT,
                )
            else:
                self._conn = http.client.HTTPConnection(
                    self.host,
                    self.port,
                    timeout=self.DEFAULT_TIMEOUT,
                )
        return self._conn

    def _close_connection(self) -> None:
        """Close connection properly."""
        conn = getattr(self, '_conn', None)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
            self._conn = None

    @staticmethod
    def _redact_body(body: str) -> str:
        """Redact potential credentials from error response bodies."""
        return RestClient._SENSITIVE_PATTERN.sub('[REDACTED]', body)

    def request(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        """Make authenticated request with retry on 429/5xx.

        Security: all exceptions are caught and re-raised without
        local variable context to prevent _headers leakage in tracebacks.
        """
        url = self.base_path + path
        if params:
            url += '?' + urllib.parse.urlencode(params, doseq=True)

        req_headers = dict(self._headers)
        encoded_body = None
        if body is not None:
            encoded_body = json.dumps(body).encode('utf-8')
            req_headers['Content-Type'] = 'application/json; charset=utf-8'

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                conn = self._get_connection()
                conn.request(method, url, body=encoded_body, headers=req_headers)
                resp = conn.getresponse()
                resp_body = resp.read()

                if resp.status == 429 or resp.status >= 500:
                    retry_after = resp.getheader('Retry-After')
                    delay = int(retry_after) if retry_after else (2**attempt)
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(delay)
                        self._close_connection()
                        continue

                if resp.status >= 400:
                    error_text = resp_body.decode('utf-8', errors='replace')
                    raise RestClientError(resp.status, self._redact_body(error_text))

                if not resp_body:
                    return {}
                result: dict = json.loads(resp_body)
                return result

            except RestClientError:
                raise
            except (ConnectionError, TimeoutError, OSError) as e:
                last_error = str(e)
                self._close_connection()
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                    continue
                # Re-raise without original context to prevent _headers leakage
                raise RestClientError(0, f'Connection failed after {self.MAX_RETRIES} attempts: {last_error}') from None

        return {}  # Unreachable, satisfies type checker

    def get(self, path: str, params: dict | None = None) -> dict:
        return self.request('GET', path, params=params)

    def post(self, path: str, body: dict | None = None) -> dict:
        return self.request('POST', path, body=body)

    def close(self) -> None:
        self._close_connection()

    def __del__(self) -> None:
        self._close_connection()


# === Authenticated Client Factory ===


def get_authenticated_client(skill_name: str, project_name: str | None = None) -> RestClient:
    """Return a pre-configured RestClient with auth headers injected.

    This is the primary API for consuming scripts. Credentials stay
    in-process and never appear in stdout/TOON.

    Args:
        skill_name: Skill name matching credential file
        project_name: Optional project name for scoped credentials

    Returns:
        RestClient with auth headers configured

    Raises:
        FileNotFoundError: If no credential file found
        ValueError: If credential file is invalid
    """
    try:
        credential = load_credential(skill_name, 'auto', project_name)
        if not credential:
            raise FileNotFoundError(
                f'No credentials configured for {skill_name}. Run: credentials configure --skill {skill_name}'
            )

        # Read URL from marshal.json provider config (preferred) or credential file (fallback)
        provider_config = read_provider_config(skill_name)
        url = provider_config.get('url', '') or credential.get('url', '')
        auth_type = credential.get('auth_type', 'none')
        headers: dict[str, str] = {}

        placeholder_values = set(SECRET_PLACEHOLDERS.values())

        if auth_type == 'token':
            header_name = credential.get('header_name', 'Authorization')
            template = credential.get('header_value_template', 'Bearer {token}')
            token = credential.get('token', '')
            if not token:
                raise ValueError(f'Token missing in credentials for {skill_name}')
            if token in placeholder_values:
                path = resolve_credential_path(skill_name, 'auto', project_name)
                raise ValueError(
                    f'Credential for {skill_name} still has placeholder token. '
                    f'Edit {path} and replace the placeholder with your actual token.'
                )
            headers[header_name] = template.format(token=token)
        elif auth_type == 'basic':
            username = credential.get('username', '')
            password = credential.get('password', '')
            if not username:
                raise ValueError(f'Username missing in credentials for {skill_name}')
            if username in placeholder_values:
                path = resolve_credential_path(skill_name, 'auto', project_name)
                raise ValueError(
                    f'Credential for {skill_name} still has placeholder username. '
                    f'Edit {path} and replace the placeholder with your actual username.'
                )
            if password in placeholder_values:
                path = resolve_credential_path(skill_name, 'auto', project_name)
                raise ValueError(
                    f'Credential for {skill_name} still has placeholder password. '
                    f'Edit {path} and replace the placeholder with your actual password.'
                )
            encoded = base64.b64encode(f'{username}:{password}'.encode()).decode()
            headers['Authorization'] = f'Basic {encoded}'
        elif auth_type == 'system':
            # System auth: no secrets, no HTTP headers.
            # The tool is authenticated at the OS level (e.g., gh, git).
            # Return a RestClient only if URL is provided; otherwise raise.
            if not url:
                raise ValueError(
                    f'System-authenticated provider {skill_name} has no URL configured. '
                    f'Use verify_system_auth() instead of RestClient for system providers.'
                )
        # auth_type == 'none': no headers needed

        return RestClient(url, headers)

    except (FileNotFoundError, ValueError):
        raise
    except Exception:
        # Generic catch: never expose credential content in error messages
        raise ValueError(f'Failed to load credentials for {skill_name}') from None


def verify_system_auth(provider: dict[str, Any]) -> dict[str, Any]:
    """Verify system-authenticated provider by running its verify_command.

    System providers (gh, git) are authenticated at the OS level.
    Verification runs the provider's declared command and checks the exit code.

    Args:
        provider: Provider declaration dict with 'verify_command' and 'skill_name'

    Returns:
        Dict with keys: success, skill, command, exit_code, output
    """
    skill_name = provider.get('skill_name', 'unknown')
    verify_command = provider.get('verify_command', '')

    if not verify_command:
        return {
            'success': False,
            'skill': skill_name,
            'command': '',
            'exit_code': -1,
            'output': 'No verify_command defined for provider',
        }

    try:
        result = subprocess.run(
            shlex.split(verify_command),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            'success': result.returncode == 0,
            'skill': skill_name,
            'command': verify_command,
            'exit_code': result.returncode,
            'output': (result.stdout or result.stderr or '').strip()[:500],
        }
    except FileNotFoundError:
        return {
            'success': False,
            'skill': skill_name,
            'command': verify_command,
            'exit_code': -1,
            'output': f'Command not found: {verify_command.split()[0]}',
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'skill': skill_name,
            'command': verify_command,
            'exit_code': -1,
            'output': 'Command timed out after 30 seconds',
        }
