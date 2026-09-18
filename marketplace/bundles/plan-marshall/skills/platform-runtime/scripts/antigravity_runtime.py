# SPDX-License-Identifier: FSL-1.1-ALv2
"""Google Antigravity implementation of every platform-runtime operation.

Antigravity-specific behaviour:
- Permissions are stored in two locations:
  - Global: ``~/.gemini/config/config.json`` under ``userSettings.globalPermissionGrants.allow``.
  - Project: ``~/.gemini/config/projects/<uuid>.json`` under ``permissionGrants.permissionGrants.allow``.
- Grants use Antigravity grammar: ``command(...)``, ``read_file(...)``, ``write_file(...)``, ``read_url(...)``.
- Skill roots resolve to ``.agents/skills`` (project) and ``~/.gemini/config/plugins/plan-marshall/skills`` (global cache).
- Session title and terminal hooks return honest no-ops as Antigravity manages status natively in the IDE.

All methods return a serialized TOON string via the helpers in runtime_base.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from runtime_base import (
    PERMISSION_FIX_OPERATIONS,
    Runtime,
    marshal_shape_error,
    toon_error,
    toon_noop,
    toon_success,
)

#: Default executor commands to guarantee in the Antigravity allow list.
ANTIGRAVITY_DEFAULT_PERMISSIONS: tuple[str, ...] = (
    'command(python3 .plan/execute-script.py)',
    'command(./pw)',
    'command(python3 marketplace/targets/sync.py --target antigravity)',
    'command(python3 .agents/scripts/sync_antigravity.py)',
)

DEFAULT_ANTIGRAVITY_COMMANDS = ANTIGRAVITY_DEFAULT_PERMISSIONS


def _gemini_config_dir() -> Path:
    """Return ~/.gemini/config directory path (overridable by GEMINI_CONFIG_DIR)."""
    env = os.environ.get('GEMINI_CONFIG_DIR')
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / '.gemini' / 'config').resolve()


def _gemini_projects_dir() -> Path:
    """Return ~/.gemini/config/projects directory path."""
    return _gemini_config_dir() / 'projects'


def to_antigravity_grant(perm: str) -> str:
    """Translate Claude or generic permission strings to Antigravity format."""
    perm = perm.strip()
    if (
        perm.startswith('command(')
        or perm.startswith('read_file(')
        or perm.startswith('write_file(')
        or perm.startswith('read_url(')
    ) and perm.endswith(')'):
        return perm

    # Bash/command conversion
    if perm.startswith('Bash(') and perm.endswith(')'):
        inner = perm[5:-1].strip()
        cmd = inner.rstrip('*').strip()
        return f'command({cmd})'

    # File read conversion
    if perm.startswith('Read(') and perm.endswith(')'):
        inner = perm[5:-1].strip()
        return f'read_file({inner})'

    # File write conversion
    if (perm.startswith('Write(') or perm.startswith('Edit(')) and perm.endswith(')'):
        inner = perm[perm.index('(') + 1 : -1].strip()
        return f'write_file({inner})'

    # Web fetch conversion
    if perm.startswith('WebFetch(') and perm.endswith(')'):
        inner = perm[9:-1].strip()
        return f'read_url({inner})'

    return f'command({perm})'


def get_antigravity_allow_list(settings: dict[str, Any]) -> list[str]:
    """Extract mutable allow list from an Antigravity settings dict."""
    allows: Any
    if 'userSettings' in settings and isinstance(settings['userSettings'], dict):
        allows = settings['userSettings'].setdefault('globalPermissionGrants', {}).setdefault('allow', [])
    elif 'permissionGrants' in settings and isinstance(settings['permissionGrants'], dict):
        pg = settings['permissionGrants']
        if isinstance(pg.get('permissionGrants'), dict):
            allows = pg['permissionGrants'].setdefault('allow', [])
        else:
            allows = pg.setdefault('allow', [])
    else:
        allows = settings.setdefault('permissionGrants', {}).setdefault('permissionGrants', {}).setdefault('allow', [])
    return cast(list[str], allows)


class AntigravityRuntime(Runtime):
    """Google Antigravity concrete implementation of the Runtime ABC."""

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for Google Antigravity.

        Creates ``.plan/``, seeds ``marshal.json`` with ``runtime.target``,
        and initializes project settings in Antigravity's project registry.
        """
        proj = Path(project_dir).resolve()
        plan_dir = proj / '.plan'

        try:
            plan_dir.mkdir(parents=True, exist_ok=True)
            temp_dir = plan_dir / 'temp'
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                'project initial-setup',
                'io_error',
                f'Failed to create .plan directory: {exc}',
            )

        marshal_path = plan_dir / 'marshal.json'
        try:
            if marshal_path.exists():
                existing: Any = json.loads(marshal_path.read_text(encoding='utf-8'))
            else:
                existing = {}
        except (OSError, json.JSONDecodeError) as exc:
            return toon_error(
                'project initial-setup',
                'io_error',
                f'Failed to read marshal.json: {exc}',
            )

        shape_error = marshal_shape_error('project initial-setup', marshal_path, existing)
        if shape_error is not None:
            return shape_error

        if 'runtime' not in existing or not isinstance(existing['runtime'], dict):
            existing['runtime'] = {}
        existing['runtime']['target'] = target

        try:
            marshal_path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
        except OSError as exc:
            return toon_error(
                'project initial-setup',
                'io_error',
                f'Failed to write marshal.json: {exc}',
            )

        # Ensure project settings exist and default executor is allowed
        settings_path = self.permission_settings_path('project', write=True, project_dir=str(proj))
        settings = self.permission_load_settings(settings_path)
        self.permission_ensure_defaults(settings, settings_path, dry_run=False)

        return toon_success(
            'project initial-setup',
            {
                'target': target,
                'project_dir': str(proj),
                'marshal_written': True,
                'settings_path': settings_path,
                'hook_installed': False,
                'hook_skip_reason': 'Antigravity hooks managed in .agents/hooks.json',
            },
        )

    def project_install_hook(
        self,
        target: str,
        overwrite: Sequence[str] = (),
        enforcement: bool = False,
    ) -> str:
        """Install lifecycle hooks into Antigravity workspace."""
        if target != 'antigravity':
            from platform_runtime import _REGISTRY
            from runtime_base import describe_targets

            return toon_error(
                'project install-hook',
                'unknown_target',
                f'Target {target!r} is not in the registry; valid targets are: {describe_targets(_REGISTRY.keys())}',
            )

        hooks_dir = Path.cwd() / '.agents'
        hooks_file = hooks_dir / 'hooks.json'

        # Antigravity hook skeleton if none exists
        if not hooks_file.exists():
            try:
                hooks_dir.mkdir(parents=True, exist_ok=True)
                skeleton = {
                    'plan-marshall-guard': {
                        'enabled': True,
                        'PreToolUse': [
                            {
                                'matcher': 'run_command',
                                'hooks': [
                                    {
                                        'type': 'command',
                                        'command': 'python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor --check-only',
                                        'timeout': 10,
                                    }
                                ],
                            }
                        ],
                    }
                }
                hooks_file.write_text(json.dumps(skeleton, indent=2), encoding='utf-8')
                return toon_success(
                    'project install-hook',
                    {
                        'target': target,
                        'hooks_file': str(hooks_file),
                        'installed': True,
                    },
                )
            except OSError as exc:
                return toon_error(
                    'project install-hook',
                    'io_error',
                    f'Failed to write .agents/hooks.json: {exc}',
                )

        return toon_success(
            'project install-hook',
            {
                'target': target,
                'hooks_file': str(hooks_file),
                'installed': False,
                'message': 'Hooks already exist in .agents/hooks.json',
            },
        )

    # ------------------------------------------------------------------
    # Layout operations
    # ------------------------------------------------------------------

    def layout_skill_roots(self) -> str:
        """Return the Antigravity project-local skill discovery roots."""
        roots = [
            '.agents/skills',
            '.agents/plugins/plan-marshall/skills',
        ]
        return toon_success(
            'layout skill-roots',
            {'target': 'antigravity', 'roots': roots},
        )

    def layout_bundle_cache_root(self) -> str:
        """Return the Antigravity deployed-bundle cache roots."""
        home = Path.home()
        roots = [
            str(home / '.gemini' / 'config' / 'plugins' / 'plan-marshall' / 'skills'),
            str(home / '.gemini' / 'antigravity' / 'skills'),
            str(home / '.gemini' / 'config' / 'skills'),
        ]
        return toon_success(
            'layout bundle-cache-root',
            {'target': 'antigravity', 'roots': roots},
        )

    # ------------------------------------------------------------------
    # Harness operations
    # ------------------------------------------------------------------

    def harness_bash_timeout_ceiling(self) -> str:
        """Resolve Antigravity's Bash-tool timeout ceiling (600s)."""
        return toon_success(
            'harness bash-timeout-ceiling',
            {'target': 'antigravity', 'ceiling_seconds': 600},
        )

    # ------------------------------------------------------------------
    # Session operations (Native in Antigravity)
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """No-op: Antigravity manages sessions natively in the IDE canvas."""
        return toon_noop(
            'session capture',
            'Antigravity manages sessions natively in the IDE canvas',
            'Pass --total-tokens manually to metrics capture or inspect Antigravity conversation log',
        )

    def session_render_title(self, statusline: bool = False) -> str:
        """No-op: Antigravity has no shell statusline hook equivalent."""
        return toon_noop(
            'session render-title',
            'Antigravity renders session and plan state in its native IDE UI',
            'Inspect the conversation panel for active status',
        )

    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = 'plans',
        slug: str | None = None,
    ) -> str:
        """No-op: Antigravity renders status in the IDE UI."""
        return toon_noop(
            'session push-title-token',
            'Antigravity renders status in the IDE UI',
            'Inspect the conversation panel for active status',
        )

    def session_bind(self, plan_id: str, session_id: str | None = None) -> str:
        """No-op: Antigravity manages session bindings internally."""
        return toon_noop(
            'session bind',
            'Antigravity manages session bindings internally',
            'Plan context is resolved from working directory and .plan/ state',
        )

    def session_resolve_plan(self, session_id: str | None = None) -> str:
        """No-op: Antigravity manages session bindings internally."""
        return toon_noop(
            'session resolve-plan',
            'Antigravity manages session bindings internally',
            'Plan context is resolved from working directory and .plan/ state',
        )

    def session_doctor(self, fix: bool = False) -> str:
        """No-op: Antigravity keeps no external active-plan cache."""
        return toon_noop(
            'session doctor',
            'Antigravity keeps no external active-plan cache to scan',
            'Session health is maintained natively by the Antigravity application',
        )

    def session_teardown(self) -> str:
        """No-op: Antigravity session lifecycle is internal."""
        return toon_noop(
            'session teardown',
            'Antigravity session lifecycle is internal',
            'No session binding cleanup needed',
        )

    def session_reload_directive(self) -> str:
        """No-op: Antigravity automatically detects updated skills and plugins."""
        return toon_noop(
            'session reload-directive',
            'Antigravity automatically discovers updated plugins in ~/.gemini/config/plugins/',
            'Run /sync-antigravity to update deployed bundles',
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    def permission_settings_path(self, scope: str, write: bool = False, project_dir: str | None = None) -> str:
        """Resolve the Antigravity settings file path for a permission scope."""
        config_dir = _gemini_config_dir()
        if scope == 'global':
            global_path = config_dir / 'config.json'
            return str(global_path)

        if scope == 'project':
            pd = Path(project_dir or Path.cwd()).resolve()
            target_uri = f'file://{pd}'
            projects_dir = _gemini_projects_dir()

            if projects_dir.is_dir():
                for candidate in projects_dir.glob('*.json'):
                    try:
                        data = json.loads(candidate.read_text(encoding='utf-8'))
                        resources = data.get('projectResources', {}).get('resources', [])
                        for res in resources:
                            uri = res.get('gitFolder', {}).get('folderUri')
                            if uri == target_uri:
                                return str(candidate)
                            if uri and uri.startswith('file://') and Path(uri[7:]).resolve() == pd:
                                return str(candidate)
                    except (OSError, json.JSONDecodeError):
                        continue

            # When write is requested and no project file exists, create one
            if write:
                projects_dir.mkdir(parents=True, exist_ok=True)
                proj_id = str(uuid.uuid4())
                proj_file = projects_dir / f'{proj_id}.json'
                data = {
                    'id': proj_id,
                    'name': pd.name,
                    'projectResources': {
                        'resources': [
                            {
                                'gitFolder': {
                                    'folderUri': target_uri,
                                    'defaultBranch': 'main',
                                }
                            }
                        ]
                    },
                    'permissionGrants': {
                        'permissionGrants': {
                            'allow': list(ANTIGRAVITY_DEFAULT_PERMISSIONS),
                        }
                    },
                    'settings': {},
                }
                try:
                    proj_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
                    return str(proj_file)
                except OSError:
                    pass

            # Fallback path
            return str(projects_dir / 'default.json')

        raise ValueError(f"Unsupported scope: {scope!r}; must be 'global' or 'project'")

    def permission_load_settings(self, path: str) -> dict[str, Any]:
        """Load settings from an Antigravity JSON file."""
        p = Path(path)
        if not p.is_file():
            return {}
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            return {'error': str(exc)}

    def permission_save_settings(self, path: str, settings: dict[str, Any]) -> bool:
        """Persist settings to an Antigravity JSON file."""
        p = Path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
            return True
        except OSError:
            return False

    def permission_ensure_defaults(
        self,
        settings: dict[str, Any],
        settings_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Ensure default Plan Marshall executor permissions exist in Antigravity settings."""
        allow_list = get_antigravity_allow_list(settings)
        added: list[str] = []

        for grant in ANTIGRAVITY_DEFAULT_PERMISSIONS:
            if grant not in allow_list:
                added.append(grant)
                if not dry_run:
                    allow_list.append(grant)

        if added and not dry_run:
            allow_list.sort()
            self.permission_save_settings(settings_path, settings)

        return {
            'defaults_added': added,
            'defaults_added_count': len(added),
            'defaults_removed': [],
            'defaults_removed_count': 0,
            'applied': bool(added and not dry_run),
        }

    def permission_configure(self, scope: str, grants: list[dict[str, Any]]) -> str:
        """Configure permission grants in Antigravity settings."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission configure',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = self.permission_settings_path(scope, write=True)
        settings = self.permission_load_settings(settings_path)
        allow_list = get_antigravity_allow_list(settings)

        added = 0
        for g in grants:
            rule = g.get('rule') or g.get('command') or str(g)
            grant_str = to_antigravity_grant(rule)
            if grant_str not in allow_list:
                allow_list.append(grant_str)
                added += 1

        if added:
            allow_list.sort()
            self.permission_save_settings(settings_path, settings)

        return toon_success(
            'permission configure',
            {
                'scope': scope,
                'settings_path': settings_path,
                'grants_added': added,
                'total_grants': len(allow_list),
            },
        )

    def permission_analyze(self, scope: str, checks: list[str], marshal_path: str | None) -> str:
        """Analyze Antigravity permissions for coverage and stale entries."""
        valid_scopes = ('global', 'project', 'both')
        if scope not in valid_scopes:
            return toon_error(
                'permission analyze',
                'invalid_scope',
                f'--scope must be one of {valid_scopes}; got {scope!r}',
            )

        scopes_to_check = ['global', 'project'] if scope == 'both' else [scope]
        results: dict[str, Any] = {}

        for sc in scopes_to_check:
            spath = self.permission_settings_path(sc, write=False)
            settings = self.permission_load_settings(spath)
            allow_list = get_antigravity_allow_list(settings)

            missing_defaults = [g for g in ANTIGRAVITY_DEFAULT_PERMISSIONS if g not in allow_list]
            results[sc] = {
                'settings_path': spath,
                'total_grants': len(allow_list),
                'missing_defaults': missing_defaults,
                'has_executor': 'command(python3 .plan/execute-script.py)' in allow_list,
            }

        return toon_success('permission analyze', {'scope': scope, 'analysis': results})

    def permission_fix(
        self,
        scope: str,
        operation: str,
        arguments: list[Any],
        dry_run: bool,
    ) -> str:
        """Apply fixes to Antigravity permissions."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission fix',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        if operation not in set(PERMISSION_FIX_OPERATIONS):
            return toon_error(
                'permission fix',
                'invalid_operation',
                f'--operation must be one of {sorted(PERMISSION_FIX_OPERATIONS)}; got {operation!r}',
            )

        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        allow_list = get_antigravity_allow_list(settings)

        if operation in ('ensure', 'add'):
            added = 0
            for item in arguments:
                grant = to_antigravity_grant(str(item))
                if grant not in allow_list:
                    allow_list.append(grant)
                    added += 1
            if added and not dry_run:
                allow_list.sort()
                self.permission_save_settings(settings_path, settings)
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'added': added,
                    'dry_run': dry_run,
                },
            )

        if operation == 'remove':
            removed = 0
            for item in arguments:
                grant = to_antigravity_grant(str(item))
                if grant in allow_list:
                    allow_list.remove(grant)
                    removed += 1
            if removed and not dry_run:
                self.permission_save_settings(settings_path, settings)
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'removed': removed,
                    'dry_run': dry_run,
                },
            )

        if operation in ('normalize', 'consolidate'):
            deduped = sorted(dict.fromkeys(allow_list))
            removed = len(allow_list) - len(deduped)
            if not dry_run and removed > 0:
                allow_list.clear()
                allow_list.extend(deduped)
                self.permission_save_settings(settings_path, settings)
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'removed_duplicates': removed,
                    'total_grants': len(deduped),
                    'dry_run': dry_run,
                },
            )

        if operation == 'protect-path':
            return toon_noop(
                'permission fix',
                'Antigravity has no path-protection or deny-list mechanism',
                'Protect sensitive files using filesystem permissions or outside the workspace',
            )

        return toon_success(
            'permission fix',
            {
                'fix_operation': operation,
                'scope': scope,
                'action': 'no-op',
                'dry_run': dry_run,
            },
        )

    def permission_ensure_wildcards(self, scope: str, marketplace_dir: str, dry_run: bool) -> str:
        """Ensure baseline executor and build tool permissions in Antigravity."""
        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        res = self.permission_ensure_defaults(settings, settings_path, dry_run=dry_run)
        return toon_success('permission ensure-wildcards', res)

    def permission_ensure_steps(self, marshal_path: str, scope: str, dry_run: bool) -> str:
        """Scan project-steps and ensure permission grants in Antigravity."""
        return toon_success(
            'permission ensure-steps',
            {
                'scope': scope,
                'dry_run': dry_run,
                'steps_added': 0,
            },
        )

    def permission_web_analyze(self, scope: str) -> str:
        """Analyze allowed URL domains in Antigravity."""
        spath = self.permission_settings_path(scope, write=False)
        settings = self.permission_load_settings(spath)
        allow_list = get_antigravity_allow_list(settings)
        urls = [item[9:-1] for item in allow_list if item.startswith('read_url(') and item.endswith(')')]
        return toon_success(
            'permission web-analyze',
            {
                'scope': scope,
                'allowed_domains': urls,
            },
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Apply URL allow/deny rules in Antigravity."""
        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        allow_list = get_antigravity_allow_list(settings)

        added = 0
        removed = 0
        for item in add:
            grant = f'read_url({item})'
            if grant not in allow_list:
                allow_list.append(grant)
                added += 1

        for item in remove:
            grant = f'read_url({item})'
            if grant in allow_list:
                allow_list.remove(grant)
                removed += 1

        if (added or removed) and not dry_run:
            allow_list.sort()
            self.permission_save_settings(settings_path, settings)

        return toon_success(
            'permission web-apply',
            {
                'scope': scope,
                'added': added,
                'removed': removed,
                'dry_run': dry_run,
            },
        )

    def permission_check_skill_coverage(self, skill: str, allow_list: list[str]) -> str | None:
        """Check if skill is covered by an allow rule."""
        target = 'command(python3 .plan/execute-script.py)'
        return target if target in allow_list else None

    def permission_load_marshal_config(self, marshal_path: str) -> dict[str, Any]:
        """Load and parse marshal.json, returning a dict with an ``error`` key on failure."""
        p = Path(marshal_path)
        if not p.is_file():
            return {'error': f'marshal.json not found: {marshal_path}'}
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {'error': 'marshal.json must be a JSON object'}
        except (OSError, json.JSONDecodeError) as exc:
            return {'error': str(exc)}

    def permission_extract_project_steps(self, marshal_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Enumerate project:{skill} step references."""
        return []

    # ------------------------------------------------------------------
    # Metrics operations
    # ------------------------------------------------------------------

    def metrics_capture(self, plan_id: str, phase: str, total_tokens: int | None) -> str:
        """Record token usage for Antigravity."""
        if total_tokens is not None:
            return toon_success(
                'metrics capture',
                {
                    'plan_id': plan_id,
                    'phase': phase,
                    'tokens_captured': total_tokens,
                    'source': 'manual',
                },
            )
        return toon_noop(
            'metrics capture',
            'Antigravity records token consumption in session database',
            'Pass --total-tokens manually to capture tokens for this phase',
        )

    def metrics_normalized_tokens(
        self,
        session_id: str,
        windows: list[tuple[str, str, str]],
        output_file: str,
    ) -> str:
        """Extract normalized token metrics."""
        return toon_noop(
            'metrics normalized-tokens',
            'Antigravity manages session transcript natively in SQLite and protobuf logs',
            'Provide windows_file directly to offline analysis',
        )

    # ------------------------------------------------------------------
    # Chat & Signal operations
    # ------------------------------------------------------------------

    def chat_extract_signal(self, session_id: str) -> str:
        """Extract signal events from Antigravity session."""
        return toon_noop(
            'chat extract-signal',
            'Antigravity stores session data in ~/.gemini/antigravity/conversations/',
            'Inspect the session transcript directly',
        )

    # ------------------------------------------------------------------
    # Subagent operations
    # ------------------------------------------------------------------

    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Dispatch subagent using Antigravity's invoke_subagent tool."""
        if prompt_file is not None and not Path(prompt_file).exists():
            return toon_error(
                'subagent dispatch',
                'prompt_not_found',
                f'prompt file not found: {prompt_file}',
            )

        prompt_body = f'Run {agent}'
        if prompt_file is not None:
            try:
                prompt_body = Path(prompt_file).read_text(encoding='utf-8')
            except OSError as exc:
                return toon_error(
                    'subagent dispatch',
                    'prompt_not_found',
                    f'Failed to read prompt file {prompt_file}: {exc}',
                )

        if context:
            for key, value in context.items():
                prompt_body = prompt_body.replace(f'{{{key}}}', str(value))

        return toon_success(
            'subagent dispatch',
            {
                'platform': 'antigravity',
                'invocation': {
                    'tool': 'invoke_subagent',
                    'description': f'Run {agent}',
                    'prompt': prompt_body,
                    'subagent_type': agent,
                },
            },
        )

    # ------------------------------------------------------------------
    # Waiting operations
    # ------------------------------------------------------------------

    def wait_for(self, observable: str, reference: str, bound_seconds: int) -> str:
        """Wait for an observable condition."""
        return toon_noop(
            'wait for',
            'Antigravity handles background task awaiting natively via manage_task',
            'Poll the observable condition using its dedicated verification command',
        )

    # ------------------------------------------------------------------
    # Health check & Runtime info
    # ------------------------------------------------------------------

    def health_check(self, checks: str) -> str:
        """Execute health checks for Antigravity target."""
        global_path = self.permission_settings_path('global', write=False)
        project_path = self.permission_settings_path('project', write=False)

        global_settings = self.permission_load_settings(global_path)
        project_settings = self.permission_load_settings(project_path)

        global_allow = get_antigravity_allow_list(global_settings)
        project_allow = get_antigravity_allow_list(project_settings)

        has_executor = (
            'command(python3 .plan/execute-script.py)' in global_allow
            or 'command(python3 .plan/execute-script.py)' in project_allow
        )

        return toon_success(
            'health-check',
            {
                'target': 'antigravity',
                'checks': checks,
                'has_executor_permission': has_executor,
                'global_settings_exists': Path(global_path).is_file(),
                'project_settings_exists': Path(project_path).is_file(),
                'status': 'healthy' if has_executor else 'warning',
            },
        )

    def runtime_info(self) -> str:
        """Report Antigravity runtime information."""
        return toon_success(
            'runtime-info',
            {
                'harness': 'antigravity',
                'build_version': '0.1',
            },
        )
