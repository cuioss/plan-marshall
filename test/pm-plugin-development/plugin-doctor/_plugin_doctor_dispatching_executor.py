#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The one synthetic dispatching ``execute-script.py`` the plugin-doctor tests probe.

Every plugin-doctor cluster that consumes a help-derived accept-set
(``_analyze_argument_naming``, ``_analyze_manage_invocation``) reads the
executor TWO ways, and a fixture that serves only the first turns every
finding-expecting test into a vacuous pass:

- ``load_registered_notations`` regex-parses the ``SCRIPTS = { ... }`` literal,
  so the dict keeps its one-quoted-notation-per-line shape;
- the shared ``argparse_surface`` derivation runs each script's own ``--help``
  THROUGH this executor, so it must actually DISPATCH rather than stand in as a
  lookup stub. A lookup-only stub satisfies the first read and silently empties
  the second, leaving the cluster with no accept-set and no findings to assert.

Resolution mirrors the real executor: ``bundle:skill:script`` maps to
``{root}/marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``,
computed at DISPATCH time rather than baked in at write time. That ordering
matters — several callers write the executor BEFORE the script it will dispatch
to, so a path resolved eagerly would point at a file that does not exist yet.

Dispatch is in-process via ``runpy.run_path`` under redirected streams: the
derivation already spawns this executor as a subprocess, and an inner spawn
would double the interpreter cold-start of every probe.

This module is the single definition on purpose. Two near-identical copies
previously lived in ``test_analyze.py`` and
``test_analyze_argument_naming_workflow_scope.py``, differing only in one local
binding; a later fix to dispatch semantics in one copy would have left the other
cluster probing a materially different executor while both suites still passed.

``seed_notation_registry`` is the second entry point: the one-call substrate a
quality-gate fixture needs so its tree is EXAMINABLE rather than merely empty.
See that function for why a fixture without an executor is not a clean tree.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

#: The single notation a seeded fixture registry declares.
#:
#: One entry, because one is the minimum that makes the registry USABLE and the
#: minimum is what keeps the seed cheap. An executor whose ``SCRIPTS`` literal
#: parses to nothing is ``registry_empty`` — still a ``could_not_look`` outcome,
#: still a finding — so an empty literal would not seed anything; and
#: ``build_script_index`` spawns one ``--help`` probe per registered notation, so
#: every additional entry is another subprocess per fixture that uses the seed.
#:
#: The notation deliberately resolves to no script in a fixture tree, so the
#: probe fails fast and the cluster derives no accept-set for it. That is the
#: correct answer rather than a shortcoming: a substrate-seeded fixture documents
#: no invocations, so there is nothing for an accept-set to judge.
FIXTURE_NOTATION = 'qg-fixture:fixture-skill:fixture-script'

_PREAMBLE: tuple[str, ...] = (
    '#!/usr/bin/env python3',
    'import contextlib',
    'import io',
    'import runpy',
    'import sys',
    'from pathlib import Path',
    '',
    'SCRIPTS = {',
)

_BODY: tuple[str, ...] = (
    '}',
    '',
    '',
    'def _resolve(notation):',
    '    parts = notation.split(":", 2)',
    '    if len(parts) != 3:',
    '        return None',
    '    bundle, skill, script = parts',
    '    root = Path(__file__).parent.parent',
    '    candidate = (',
    '        root / "marketplace" / "bundles" / bundle / "skills" / skill',
    '        / "scripts" / (script + ".py")',
    '    )',
    '    return candidate if candidate.is_file() else None',
    '',
    '',
    'def main():',
    '    if len(sys.argv) < 2:',
    '        sys.exit(2)',
    '    notation = sys.argv[1]',
    '    target = _resolve(notation)',
    '    if target is None:',
    '        sys.stderr.write("Unknown notation: " + notation + "\\n")',
    '        sys.exit(2)',
    '    out_buf = io.StringIO()',
    '    err_buf = io.StringIO()',
    '    rc = 0',
    '    saved_argv = sys.argv',
    '    sys.argv = [str(target), *sys.argv[2:]]',
    '    try:',
    '        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):',
    '            runpy.run_path(str(target), run_name="__main__")',
    '    except SystemExit as exc:',
    '        code = exc.code',
    '        rc = 0 if code is None else (code if isinstance(code, int) else 1)',
    '    finally:',
    '        sys.argv = saved_argv',
    '    sys.stdout.write(out_buf.getvalue())',
    '    sys.stderr.write(err_buf.getvalue())',
    '    sys.stdout.flush()',
    '    sys.stderr.flush()',
    '    sys.exit(rc)',
    '',
    '',
    'if __name__ == "__main__":',
    '    main()',
)


def write_dispatching_executor(plan_dir: Path, notations: list[str]) -> Path:
    """Write the dispatching ``execute-script.py`` into ``plan_dir``.

    ``plan_dir`` is the scratch tree's ``.plan/`` directory (created when
    absent); ``notations`` are the ``bundle:skill:script`` keys to register in
    the ``SCRIPTS`` literal. Returns the executor path.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    lines = [
        *_PREAMBLE,
        *(f'    "{notation}": "resolved-at-dispatch",' for notation in notations),
        *_BODY,
    ]
    executor.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return executor


def seed_notation_registry(
    temp_root: Path, notations: Sequence[str] = (FIXTURE_NOTATION,)
) -> Path:
    """Give a fixture marketplace the notation-registry substrate a real tree has.

    ``temp_root`` is the directory that CONTAINS ``marketplace/`` — the anchor
    ``analyze_argument_naming`` resolves its registry from
    (``marketplace_root.parent / '.plan' / 'execute-script.py'``). Every
    quality-gate fixture in this suite builds ``{temp_root}/marketplace/bundles``,
    so the executor belongs one level up at ``{temp_root}/.plan/``.

    Why fixtures need this at all: a tree with no executor is UNEXAMINABLE, not
    clean, and ``ARGUMENT_NAMING_SUBSTRATE_ABSENT`` says so. Seeding a real
    substrate is what restores "clean" as an examinable state, so the suite's
    clean-tree assertions keep their full strength as the NEGATIVE control
    against an always-fires rule. Silencing the rule in fixtures would reinstate
    the defect one surface over, and relaxing the clean-tree assertions would
    retire the only check that can catch a rule which fires on everything. The
    matched POSITIVE control is the deliberately unseeded fixture in
    ``_plugin_doctor_fixtures.build_fixture_corpus``.

    Returns the executor path.
    """
    return write_dispatching_executor(temp_root / '.plan', list(notations))
