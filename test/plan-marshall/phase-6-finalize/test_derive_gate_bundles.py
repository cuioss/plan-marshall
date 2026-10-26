#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the ``derive_gate_bundles`` pre-push-quality-gate seam.

The seam at ``phase-6-finalize/scripts/derive_gate_bundles.py`` replaces the
former four-rule prose in ``standards/pre-push-quality-gate.md`` "Derive unique
bundle set" section. These tests pin the deliverable's Success Criteria against
the **real** ``marketplace/bundles/`` tree (via ``conftest.MARKETPLACE_ROOT``)
so the "is a real bundle directory" predicate is exercised, not stubbed:

* The exact reported path shape ``test/marketplace/targets/test_frontmatter.py``
  derives **no** ``marketplace`` bundle and contributes exactly one
  ``unresolved[]`` entry — the phantom-bundle regression (D1).
* ``test/plan-marshall/…`` → ``plan-marshall`` (the second segment names a real
  bundle).
* ``marketplace/bundles/plan-marshall/…`` → ``plan-marshall``.
* A mixed footprint yields a sorted, de-duplicated bundle set.
* A path matching no build_map glob contributes nothing (neither a bundle nor
  an ``unresolved[]`` entry).
* A path that DID match a build_map glob but is of any other shape — the
  consumer-layout case — lands in ``unresolved[]`` rather than being dropped
  (rule 4). That contrast with the bullet above is the point: "matched no glob"
  and "matched a glob but resolves to no bundle" are different answers, and
  only the second is diagnosable.
* The ``--files-file`` hand-off: the file form derives exactly what the inline
  CSV form derives over the same paths (a transport, not a second derivation),
  its reader skips blank lines and ``#`` comments without dropping the real
  paths around them, it preserves order and duplicates, an **absent file
  raises** rather than deriving an empty population (an empty list iterates the
  per-bundle loop zero times and reads as a green gate over nothing), and the
  two input forms are mutually exclusive and jointly required.

This module is the **sole owner** of the rule-4 behavioural pair — the
consumer-shaped negative AND its matched positive control. The control is not
optional: a test asserting only the negative would pass just as well against a
seam that routed *everything* to ``unresolved``. The sibling
``test_gate_derivation_diagnosability.py`` covers the disjoint contract-text
dimension and must not re-assert this pair.

The module lives alongside the 14 pre-existing non-package test modules in
``test/plan-marshall/phase-6-finalize/`` — no ``__init__.py`` is added, and a
guard test pins that the directory remains a non-package directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import (
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    get_script_path,
    load_script_module,
    run_script,
)

_mod = load_script_module('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')
derive_gate_bundles = _mod.derive_gate_bundles
read_files_file = _mod.read_files_file

# Globs broad enough to admit both a bundle-rooted path and a test-rooted path.
# fnmatch ``*`` spans ``/``, so these match any depth beneath the prefix.
_ALL_GLOBS = ['marketplace/bundles/*', 'test/*']


def _as_list(value) -> list:
    """Coerce a TOON-parsed scalar-or-list field into a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ---------------------------------------------------------------------------
# Pure-function tests against the real marketplace/bundles/ tree
# ---------------------------------------------------------------------------


def test_test_marketplace_path_yields_no_bundle_and_one_unresolved():
    # Arrange — the exact reported phantom-bundle path shape.
    files = ['test/marketplace/targets/test_frontmatter.py']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['test/*'], MARKETPLACE_ROOT)

    # Assert — no phantom ``marketplace`` bundle; the path is diagnosable, not dropped.
    assert bundles == []
    assert unresolved == ['test/marketplace/targets/test_frontmatter.py']


def test_test_plan_marshall_path_resolves_to_plan_marshall():
    files = ['test/plan-marshall/phase-6-finalize/test_ci_verify.py']

    bundles, unresolved = derive_gate_bundles(files, ['test/*'], MARKETPLACE_ROOT)

    assert bundles == ['plan-marshall']
    assert unresolved == []


def test_marketplace_bundles_path_resolves_to_bundle():
    files = ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foo.py']

    bundles, unresolved = derive_gate_bundles(files, ['marketplace/bundles/*'], MARKETPLACE_ROOT)

    assert bundles == ['plan-marshall']
    assert unresolved == []


def test_mixed_footprint_yields_sorted_deduplicated_set():
    # Arrange — two distinct real bundles across both path shapes, plus a
    # duplicate ``plan-marshall`` contribution that must collapse.
    files = [
        'marketplace/bundles/pm-dev-java/skills/java-core/scripts/foo.py',
        'test/plan-marshall/phase-6-finalize/test_bar.py',
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/baz.py',
        'test/plan-marshall/phase-6-finalize/test_qux.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    # Assert — sorted and de-duplicated ('plan-marshall' < 'pm-dev-java').
    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert bundles == sorted(bundles)
    assert unresolved == []


def test_non_matching_glob_entry_contributes_nothing():
    files = ['doc/developer/build.adoc']

    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    assert bundles == []
    assert unresolved == []


def test_full_mixed_footprint_partitions_correctly():
    # Arrange — one of each class: real bundle-rooted, real test-rooted,
    # phantom test-rooted (unresolved), and non-matching (dropped).
    files = [
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py',
        'test/pm-dev-java/junit-core/test_y.py',
        'test/marketplace/targets/test_frontmatter.py',
        'README.md',
    ]

    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert unresolved == ['test/marketplace/targets/test_frontmatter.py']


# ---------------------------------------------------------------------------
# Rule 4 — the consumer-layout shape is REPORTED, not dropped.
#
# This section owns the behavioural pair. Each negative below is stated
# together with a positive control, because a seam that routed every path to
# ``unresolved`` would satisfy the negatives alone.
# ---------------------------------------------------------------------------


def test_consumer_shaped_glob_matching_path_lands_in_unresolved():
    # Arrange — a consumer project's source path. It matches the project's own
    # registered build_map glob, so the project declared it build-relevant, but
    # it is neither ``marketplace/bundles/<b>/…`` nor ``test/<b>/…``.
    files = ['src/main/java/com/example/Foo.java']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['src/*'], MARKETPLACE_ROOT)

    # Assert — no bundle, and the path is REPORTED rather than silently dropped.
    # An empty ``unresolved`` here is the defect: it left the gate's per-bundle
    # loop with nothing to iterate and nothing to say about why.
    assert bundles == []
    assert unresolved == ['src/main/java/com/example/Foo.java']


def test_whole_consumer_footprint_is_reported_not_silently_green():
    # Arrange — the real-world shape: a consumer project whose every build-
    # relevant path is of a layout this seam cannot resolve.
    files = [
        'src/main/java/com/example/Foo.java',
        'src/main/java/com/example/Bar.java',
        'lib/widget.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['*'], MARKETPLACE_ROOT)

    # Assert — the pre-fix seam returned ([], []) here, so the gate's per-bundle
    # loop iterated zero times and reported green. Every path is now accounted
    # for, in footprint order.
    assert bundles == []
    assert unresolved == files


def test_tests_plural_root_is_unresolved_not_a_phantom_bundle():
    # Arrange — ``tests/`` is NOT ``test/``; the prefix must not match loosely
    # and must not derive ``foo`` as a bundle from segment 1.
    files = ['tests/foo/test_bar.py']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['tests/*'], MARKETPLACE_ROOT)

    # Assert
    assert bundles == []
    assert unresolved == ['tests/foo/test_bar.py']


def test_rule_four_negative_with_matched_positive_control():
    # Arrange — the pair in ONE act, which is what makes each half falsifiable:
    # a consumer-shaped path, a real bundle-rooted path, and a real test-rooted
    # path whose bundle directory exists on disk.
    files = [
        'src/main/java/com/example/Foo.java',
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py',
        'test/pm-dev-java/junit-core/test_y.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['src/*', 'marketplace/bundles/*', 'test/*'], MARKETPLACE_ROOT)

    # Assert — POSITIVE CONTROL: both resolvable shapes still resolve, and
    # neither leaked into ``unresolved``. Without this half, a seam that routed
    # everything to ``unresolved`` would pass the negative above.
    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert 'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py' not in unresolved
    assert 'test/pm-dev-java/junit-core/test_y.py' not in unresolved

    # Assert — NEGATIVE: only the consumer-shaped path is reported.
    assert unresolved == ['src/main/java/com/example/Foo.java']


def test_unmatched_glob_and_rule_four_are_different_answers():
    # Arrange — two paths of the same unresolvable shape. Only one is admitted
    # by the globs, so the glob filter (rule 1) and rule 4 must be visibly
    # distinguishable rather than collapsing into one silent outcome.
    files = ['src/main/java/com/example/Foo.java', 'doc/developer/build.adoc']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['src/*'], MARKETPLACE_ROOT)

    # Assert — the glob-matching path is diagnosable; the non-matching one is
    # genuinely out of remit and stays absent from BOTH lists.
    assert bundles == []
    assert unresolved == ['src/main/java/com/example/Foo.java']
    assert 'doc/developer/build.adoc' not in unresolved


# ---------------------------------------------------------------------------
# CLI / TOON output-contract smoke against the executor entry point
# ---------------------------------------------------------------------------


def test_cli_emits_toon_bundles_and_unresolved():
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--files',
        'test/marketplace/targets/test_frontmatter.py,'
        'test/plan-marshall/test_bar.py,'
        'marketplace/bundles/pm-dev-java/skills/foo.py',
        '--globs',
        'test/*,marketplace/bundles/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert _as_list(data['bundles']) == ['plan-marshall', 'pm-dev-java']
    assert _as_list(data['unresolved']) == ['test/marketplace/targets/test_frontmatter.py']


# ---------------------------------------------------------------------------
# --files-file: the faithful hand-off (the retyped-CSV defect class)
# ---------------------------------------------------------------------------


def test_files_file_derives_the_same_bundles_as_the_inline_form(tmp_path):
    """The file form is a transport, not a different derivation.

    Both inputs carry the same paths, so both must yield the same bundle set and
    the same ``unresolved`` list. A difference would mean the file path silently
    gates a different population than the caller believes it gated.
    """
    paths = [
        'test/marketplace/targets/test_frontmatter.py',
        'test/plan-marshall/test_bar.py',
        'marketplace/bundles/pm-dev-java/skills/foo.py',
    ]
    listed = tmp_path / 'footprint.txt'
    listed.write_text(''.join(f'{p}\n' for p in paths), encoding='utf-8')

    from_file, unresolved_file = derive_gate_bundles(
        read_files_file(listed),
        ['test/*', 'marketplace/bundles/*'],
        MARKETPLACE_ROOT,
    )
    from_csv, unresolved_csv = derive_gate_bundles(
        paths,
        ['test/*', 'marketplace/bundles/*'],
        MARKETPLACE_ROOT,
    )

    assert from_file == from_csv == ['plan-marshall', 'pm-dev-java']
    assert unresolved_file == unresolved_csv == [paths[0]]


def test_files_file_skips_blank_lines_and_comments_but_keeps_every_path(tmp_path):
    """A comment-tolerant reader is only safe if it drops comments, not paths.

    Blank lines and ``#`` comments are noise; a real path that happens to sit
    next to them is not, so the reader must not drop the tail of the file after
    it starts skipping.
    """
    listed = tmp_path / 'footprint.txt'
    listed.write_text(
        '# live footprint\n'
        '\n'
        'test/plan-marshall/test_bar.py\n'
        '   \n'
        '   # indented comment\n'
        'test/plan-marshall/test_baz.py\n',
        encoding='utf-8',
    )

    assert read_files_file(listed) == [
        'test/plan-marshall/test_bar.py',
        'test/plan-marshall/test_baz.py',
    ]


def test_files_file_preserves_duplicates_and_file_order(tmp_path):
    """A repeated path must not be collapsed on the way in.

    The seam de-duplicates the derived bundle SET, so collapsing duplicates in
    the reader would be redundant at best; it would also make the reader
    disagree with the producer's list, and the producer's list is the
    authoritative record of what was gated over.
    """
    listed = tmp_path / 'footprint.txt'
    listed.write_text(
        'test/plan-marshall/test_b.py\ntest/plan-marshall/test_a.py\ntest/plan-marshall/test_b.py\n',
        encoding='utf-8',
    )

    assert read_files_file(listed) == [
        'test/plan-marshall/test_b.py',
        'test/plan-marshall/test_a.py',
        'test/plan-marshall/test_b.py',
    ]


def test_missing_files_file_raises_rather_than_deriving_nothing(tmp_path):
    """An unreadable file is an error, never an empty population.

    This is the load-bearing negative: an empty list would derive no bundles,
    the per-bundle loop would iterate zero times, and the gate would report
    green over a population it never saw — the exact false green the file form
    exists to prevent.
    """
    with pytest.raises(OSError):
        read_files_file(tmp_path / 'absent.txt')


def test_cli_reports_an_unreadable_files_file_as_a_typed_error(tmp_path):
    """The failure must be a branchable envelope, not a stack trace.

    The caller is a gate reading a step record, so an unreadable input has to
    arrive as ``status: error`` with a named code — a traceback on stderr leaves
    the failure legible only to someone reading the console, and a
    ``status: success`` with an empty bundle list would be the false green the
    option exists to prevent.
    """
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--files-file',
        str(tmp_path / 'absent.txt'),
        '--globs',
        'test/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'files_file_unreadable'
    assert 'bundles' not in data


def test_cli_reports_invalid_utf8_as_the_same_typed_error(tmp_path):
    """A non-UTF-8 file is the same failure as an absent one.

    ``UnicodeDecodeError`` is a ``ValueError`` subclass, so an ``except OSError``
    handler lets it escape as a traceback. From the gate's side the two are
    indistinguishable — the list could not be read — so they must return the
    same code rather than one of them crashing.
    """
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')
    listed = tmp_path / 'footprint.txt'
    listed.write_bytes(b'test/plan-marshall/test_bar.py\n\xff\xfe not utf-8\n')

    result = run_script(
        script,
        'derive',
        '--files-file',
        str(listed),
        '--globs',
        'test/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'files_file_unreadable'
    assert 'bundles' not in data


def test_cli_accepts_files_file(tmp_path):
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')
    listed = tmp_path / 'footprint.txt'
    listed.write_text(
        'test/plan-marshall/test_bar.py\ntest/marketplace/targets/test_frontmatter.py\n',
        encoding='utf-8',
    )

    result = run_script(
        script,
        'derive',
        '--files-file',
        str(listed),
        '--globs',
        'test/*,marketplace/bundles/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert _as_list(data['bundles']) == ['plan-marshall']
    assert _as_list(data['unresolved']) == ['test/marketplace/targets/test_frontmatter.py']


def test_cli_refuses_both_files_forms_together():
    """The two forms are mutually exclusive, so the safe path cannot be half-used."""
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--files',
        'test/plan-marshall/test_bar.py',
        '--files-file',
        '/dev/null',
        '--globs',
        'test/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    assert not result.success
    assert 'not allowed with argument' in result.stderr


def test_cli_refuses_neither_files_form():
    """Omitting both is a refusal too — the footprint is not optional."""
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--globs',
        'test/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    assert not result.success
    assert 'one of the arguments' in result.stderr


# ---------------------------------------------------------------------------
# Architecture-backed module resolution for a non-marketplace layout (D3)
# ---------------------------------------------------------------------------
#
# A consumer project is not a marketplace layout: its sources live under module
# directories a Maven reactor names, not under ``marketplace/bundles/<b>``. Before
# the fallback every such path reached rule 4 and landed in ``unresolved``, so the
# gate iterated zero bundles and read as green over a population it never saw. The
# seam now accepts a resolver — the architecture's ``which-module`` reader in
# production — and the CLI supplies one only when the root carries no
# ``marketplace/bundles`` directory.

_MAVEN_GLOBS = ['**/*.java', '**/pom.xml', '**/*.md']


def _prefix_resolver(prefixes: dict[str, str]):
    """Stand-in for ``architecture which-module``: the longest matching prefix wins."""
    ordered = sorted(prefixes.items(), key=lambda entry: len(entry[0]), reverse=True)

    def resolve(path: str) -> str | None:
        for prefix, name in ordered:
            if prefix and (path == prefix or path.startswith(prefix + '/')):
                return name
        return None

    return resolve


def test_two_maven_modules_are_the_gate_population(tmp_path):
    """Changes in two reactor modules yield exactly those two as the population."""
    bundles, unresolved = derive_gate_bundles(
        ['alpha/src/main/java/Alpha.java', 'beta/src/main/java/Beta.java'],
        _MAVEN_GLOBS,
        tmp_path / 'marketplace' / 'bundles',
        module_resolver=_prefix_resolver({'alpha': 'alpha', 'beta': 'beta'}),
    )

    assert bundles == ['alpha', 'beta']
    assert unresolved == []


def test_a_path_no_module_owns_is_still_reported(tmp_path):
    """A path the architecture cannot place is reported, never dropped."""
    bundles, unresolved = derive_gate_bundles(
        ['alpha/src/main/java/Alpha.java', 'docs/notes.md'],
        _MAVEN_GLOBS,
        tmp_path / 'marketplace' / 'bundles',
        module_resolver=_prefix_resolver({'alpha': 'alpha'}),
    )

    assert bundles == ['alpha']
    assert unresolved == ['docs/notes.md']


def test_without_a_resolver_a_consumer_path_stays_unresolved(tmp_path):
    """The marketplace rule is unchanged where no resolver is supplied."""
    bundles, unresolved = derive_gate_bundles(
        ['alpha/src/main/java/Alpha.java'],
        _MAVEN_GLOBS,
        tmp_path / 'marketplace' / 'bundles',
    )

    assert bundles == []
    assert unresolved == ['alpha/src/main/java/Alpha.java']


def test_the_resolver_is_never_consulted_for_a_classified_marketplace_path():
    """Bundle-rooted and test-rooted paths are classified by the seam, not the architecture."""
    calls: list[str] = []

    def resolver(path: str) -> str | None:
        calls.append(path)
        return 'marketplace'

    bundles, unresolved = derive_gate_bundles(
        ['test/marketplace/targets/test_frontmatter.py', 'marketplace/bundles/plan-marshall/x.py'],
        _ALL_GLOBS,
        MARKETPLACE_ROOT,
        module_resolver=resolver,
    )

    assert bundles == ['plan-marshall']
    assert unresolved == ['test/marketplace/targets/test_frontmatter.py']
    assert calls == []


def test_cli_answers_unresolved_when_no_architecture_is_available(tmp_path):
    """A consumer root with no architecture data reports the path, never a green zero."""
    (tmp_path / 'alpha').mkdir()
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--files',
        'alpha/src/main/java/Alpha.java',
        '--globs',
        '**/*.java',
        '--marketplace-root',
        str(tmp_path),
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert _as_list(data['bundles']) == []
    assert _as_list(data['unresolved']) == ['alpha/src/main/java/Alpha.java']


def _write_reactor(root: Path) -> None:
    """Two-module Maven reactor: modules ``alpha`` and ``beta`` under a root POM."""
    (root / 'pom.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        '    <modelVersion>4.0.0</modelVersion>\n'
        '    <groupId>com.example</groupId>\n'
        '    <artifactId>parent-project</artifactId>\n'
        '    <version>1.0.0-SNAPSHOT</version>\n'
        '    <packaging>pom</packaging>\n'
        '    <modules><module>alpha</module><module>beta</module></modules>\n'
        '</project>\n',
        encoding='utf-8',
    )
    for name in ('alpha', 'beta'):
        module = root / name
        (module / 'src' / 'main' / 'java').mkdir(parents=True)
        (module / 'src' / 'main' / 'java' / 'Thing.java').write_text('class Thing {}\n', encoding='utf-8')
        (module / 'pom.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
            '    <modelVersion>4.0.0</modelVersion>\n'
            '    <groupId>com.example</groupId>\n'
            f'    <artifactId>{name}</artifactId>\n'
            '    <version>1.0.0-SNAPSHOT</version>\n'
            '    <packaging>jar</packaging>\n'
            '</project>\n',
            encoding='utf-8',
        )


def test_a_fixture_reactor_reaches_the_population_through_the_architecture_resolver(tmp_path, monkeypatch):
    """The PRODUCTION resolver joins a real Maven reactor to the gate population.

    The architecture READER is the boundary here (its own rung logic is
    ``manage-architecture``'s test surface), but it answers from the fixture's own
    module directories — so the fixture drives the population: remove it and the
    test fails. Everything this plan adds — the resolver factory, the per-path
    call and the join into ``bundles`` — runs for real.
    """
    from conftest import add_skill_scripts_to_path

    add_skill_scripts_to_path('plan-marshall', 'manage-architecture')
    import _cmd_client_handlers

    _write_reactor(tmp_path)

    def fake_which_module(args):
        project = Path(args.project_dir)
        owners = sorted(
            (child.name for child in project.iterdir() if child.is_dir() and (child / 'pom.xml').is_file()),
            key=len,
            reverse=True,
        )
        for name in owners:
            if args.path == name or args.path.startswith(name + '/'):
                return {'status': 'success', 'module': name}
        return {'status': 'success', 'module': None}

    monkeypatch.setattr(_cmd_client_handlers, 'cmd_which_module', fake_which_module)

    resolver = _mod.architecture_module_resolver(tmp_path)
    bundles, unresolved = _mod.derive_gate_bundles(
        ['alpha/src/main/java/Thing.java', 'beta/src/main/java/Thing.java', 'docs/notes.md'],
        _MAVEN_GLOBS,
        tmp_path / 'marketplace' / 'bundles',
        module_resolver=resolver,
    )

    assert bundles == ['alpha', 'beta']
    assert unresolved == ['docs/notes.md']


def test_a_consumer_test_root_path_resolves_through_the_resolver(tmp_path):
    """A consumer project's ``test/<pkg>/…`` is a module path, not a phantom bundle."""
    bundles, unresolved = derive_gate_bundles(
        ['test/pkg/test_thing.py', 'test/nobody/test_orphan.py'],
        ['**/*.py'],
        tmp_path / 'marketplace' / 'bundles',
        module_resolver=_prefix_resolver({'test/pkg': 'pkg'}),
    )

    assert bundles == ['pkg']
    assert unresolved == ['test/nobody/test_orphan.py']


def test_cli_builds_the_resolver_only_for_a_non_marketplace_root(tmp_path, monkeypatch, capsys):
    """The factory is consulted for a consumer root, and never for a marketplace one."""
    import argparse

    from toon_parser import parse_toon

    calls: list[Path] = []

    def fake_factory(root: Path):
        calls.append(root)

        def resolve(path: str) -> str | None:
            return 'alpha' if path.startswith('alpha/') else None

        return resolve

    monkeypatch.setattr(_mod, 'architecture_module_resolver', fake_factory)
    args = argparse.Namespace(
        files='alpha/src/main/java/Thing.java',
        files_file=None,
        globs='**/*.java',
        marketplace_root=str(tmp_path),
    )

    _mod.cmd_derive(args)
    consumer = parse_toon(capsys.readouterr().out)

    assert consumer['bundles'] == ['alpha']
    assert calls == [tmp_path]

    monkeypatch.setattr(_mod, 'architecture_module_resolver', lambda root: pytest.fail('resolver built'))
    marketplace_args = argparse.Namespace(
        files='test/plan-marshall/test_x.py',
        files_file=None,
        globs='test/*',
        marketplace_root=str(PROJECT_ROOT),
    )

    _mod.cmd_derive(marketplace_args)
    marketplace = parse_toon(capsys.readouterr().out)

    assert marketplace['bundles'] == ['plan-marshall']


# ---------------------------------------------------------------------------
# Non-package directory guard
# ---------------------------------------------------------------------------


def test_test_directory_remains_non_package():
    # The directory is an established non-package test directory; adding an
    # ``__init__.py`` would change collection semantics for its 14+ siblings.
    test_dir = Path(__file__).parent
    assert not (test_dir / '__init__.py').exists()
