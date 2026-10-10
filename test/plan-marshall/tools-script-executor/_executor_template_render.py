# SPDX-License-Identifier: FSL-1.1-ALv2
"""The one renderer of ``execute-script.py.template`` for this test directory.

Every test module under ``test/plan-marshall/tools-script-executor/`` that
renders the real executor template does so through
:func:`render_executor_template`, so a placeholder the template gains is
substituted in ONE place instead of in each module's private loader.

The render fails on any ``{{UPPER_CASE}}`` token it leaves behind. An
unsubstituted placeholder does not fail on its own: it compiles as a literal
string, and the test then exercises an executor no generator produces. Per-task
quality-gate and test-compile validate the template in isolation, so before this
guard a desynced renderer surfaced only in a whole-tree module-tests run, if at
all.

Each caller passes only the substitutions its test depends on — a pinned
bootstrap directory, an extra script dir, the empty version sentinel — and every
other placeholder takes an inert default.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_scripts_dir, load_script_module

#: The real executor template every caller renders.
TEMPLATE_PATH: Path = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates' / 'execute-script.py.template'
)

#: The real manage-logging scripts dir, so the rendered executor's module-level
#: ``plan_logging`` import resolves.
LOGGING_DIR: Path = get_scripts_dir('plan-marshall', 'manage-logging')

#: The shape of a template placeholder token.
PLACEHOLDER_RE = re.compile(r'\{\{[A-Z][A-Z0-9_]*\}\}')

_gen = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_template_render'
)

#: The value ``generate_executor`` substitutes for ``{{BOOTSTRAP_BUNDLE}}``,
#: read from the generator rather than restated.
BOOTSTRAP_BUNDLE: str = _gen.BOOTSTRAP_BUNDLE

#: A target-aware resolver that never resolves, so resolution falls through to
#: the embedded mapping and the cwd walk.
INERT_TARGET_AWARE_RESOLVER = 'def _resolve_notation_by_target(notation):\n    return None\n'

#: An empty directory block — a comment, so the surrounding literal stays valid.
NO_DIRS = '# (none in test)'


def format_script_mappings(mappings: Mapping[str, str | Path]) -> str:
    """Render ``mappings`` as the body of the template's ``SCRIPTS`` dict."""
    return ''.join(f'    "{notation}": "{path}",\n' for notation, path in mappings.items())


def render_executor_template(
    script_mappings: str = '',
    script_surfaces: str = '',
    *,
    logging_dir: str | Path = LOGGING_DIR,
    shared_module_dirs: str = NO_DIRS,
    cache_recovery_roots: str = NO_DIRS,
    extra_script_dirs: str = '',
    plan_dir_name: str = '.plan',
    executor_target: str = 'claude',
    bootstrap_bundle: str = BOOTSTRAP_BUNDLE,
    generated_version: str = '0.0.0-test',
    mappings_fingerprint: str = 'test-fingerprint',
    template_sha256: str = 'test-template-sha256',
    target_aware_resolver: str = INERT_TARGET_AWARE_RESOLVER,
) -> str:
    """Render the executor template with every placeholder substituted.

    Args:
        script_mappings: The body of the ``SCRIPTS`` mapping
            (see :func:`format_script_mappings`).
        script_surfaces: The body of the ``SCRIPT_SURFACES`` mapping; empty
            means no notation carries a surface.
        logging_dir: The directory ``plan_logging`` is imported from.
        shared_module_dirs: The ``(skill, pinned_dir)`` entries of the shared
            bootstrap dirs.
        cache_recovery_roots: The entries of the cache-recovery roots.
        extra_script_dirs: The entries of the baked extra script dirs.
        plan_dir_name: The plan directory name.
        executor_target: The target the executor was generated for.
        bootstrap_bundle: The bundle the bootstrap skills belong to.
        generated_version: The stamped version; ``''`` is the fresh-install
            sentinel.
        mappings_fingerprint: The stamped mappings fingerprint; ``''`` is the
            fresh-install sentinel.
        template_sha256: The stamped template digest.
        target_aware_resolver: The source of ``_resolve_notation_by_target``.

    Returns:
        The rendered executor source.
    """
    substitutions = {
        '{{SCRIPT_MAPPINGS}}': script_mappings,
        '{{SCRIPT_SURFACES}}': script_surfaces,
        '{{LOGGING_DIR}}': str(logging_dir),
        '{{SHARED_MODULE_DIRS}}': shared_module_dirs,
        '{{CACHE_RECOVERY_ROOTS}}': cache_recovery_roots,
        '{{EXTRA_SCRIPT_DIRS}}': extra_script_dirs,
        '{{PLAN_DIR_NAME}}': plan_dir_name,
        '{{EXECUTOR_TARGET}}': executor_target,
        '{{BOOTSTRAP_BUNDLE}}': bootstrap_bundle,
        '{{GENERATED_VERSION}}': generated_version,
        '{{MAPPINGS_FINGERPRINT}}': mappings_fingerprint,
        '{{TEMPLATE_SHA256}}': template_sha256,
        '{{TARGET_AWARE_RESOLVER}}': target_aware_resolver,
    }
    code: str = TEMPLATE_PATH.read_text(encoding='utf-8')
    for placeholder, value in substitutions.items():
        code = code.replace(placeholder, value)
    residue = sorted(set(PLACEHOLDER_RE.findall(code)))
    assert not residue, f'Executor template placeholders left unsubstituted by the test renderer: {residue}'
    return code
