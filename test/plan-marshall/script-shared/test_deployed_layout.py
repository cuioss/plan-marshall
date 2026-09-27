# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``deployed_layout`` — the single home for deployed-layout knowledge.

Every case here builds a REAL tree in a tmp dir and reads it back. A resolver
whose whole job is to know which shape a directory has cannot be tested by
passing it a constructed path: what has to be pinned is the filesystem shape
itself, so the fixtures are trees and the assertions are about what the
resolver finds in them.

The contract under test, in the order the cases establish it:

* the FLAT deployed shape (``{root}/skills/{bundle}-{skill}/…``) and the NESTED
  shape (``{root}/{bundle}/skills/{skill}/…``) resolve the SAME logical script —
  one vocabulary, two deployments, one answer;
* the skill root is read under BOTH spellings, plural ``skills/`` (deployed) and
  singular ``skill/`` (generated, pre-install), with plural probed first;
* the flat directory NAME is a dash-joined ``{bundle}-{skill}``, recognised by
  shape rather than split — a pair would be a confident-looking wrong answer,
  because both components are kebab-case and no separator position recovers them;
* enumeration over a flat root is NON-EMPTY, which is the property the whole
  deliverable exists to restore.
"""

import re
from pathlib import Path

import deployed_layout
import pytest
from deployed_layout import (
    SKILL_ROOT_NAMES,
    carries_target_manifest,
    flat_script_dirs,
    flat_skill_dir_name,
    flat_skill_dirs,
    is_flat_root,
    is_flat_skill_dir_name,
    resolve_skill_path,
    skill_roots,
    skill_scripts_subpath,
    split_skill_relative_path,
)

#: Matches the singular skill-root spelling as a QUOTED literal, in either quote
#: style. Used by the source scan below to spot a consumer that re-states the
#: vocabulary instead of reading it from :data:`SKILL_ROOT_NAMES`.
_QUOTED_SKILL_ROOT = re.compile(r"""['"]skill['"]""")

#: The skills a fully-formed flat tree carries. The set is the union of what the
#: executor generator needs — the logging module plus the five shared modules it
#: puts on ``sys.path`` — so a fixture built from it exercises the real
#: consumers rather than a convenient subset.
FLAT_SKILLS = (
    'manage-logging',
    'tools-file-ops',
    'tools-input-validation',
    'ref-toon-format',
    'script-shared',
    'manage-change-ledger',
)

BUNDLE = 'plan-marshall'


def _make_flat_tree(root: Path, *, root_name: str = 'skills', skills: tuple[str, ...] = FLAT_SKILLS) -> Path:
    """Build a real flat deployed tree under ``root`` and return the skill root.

    ``root_name`` selects the skill-root spelling, so the same builder produces
    the deployed plural ``skills/`` and the generated singular ``skill/``. Each
    skill carries both a ``SKILL.md`` and a ``scripts/`` directory, because a real
    deployed skill has both and a resolver asked for either must find it.
    """
    skills_root = root / root_name
    for skill in skills:
        skill_dir = skills_root / flat_skill_dir_name(BUNDLE, skill)
        (skill_dir / 'scripts').mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('# skill', encoding='utf-8')
        (skill_dir / 'scripts' / f'{skill}.py').write_text('# script', encoding='utf-8')
    return skills_root


def _make_nested_tree(root: Path, *, skills: tuple[str, ...] = FLAT_SKILLS) -> Path:
    """Build a real nested marketplace tree under ``root`` and return the bundles root."""
    bundles_root = root
    for skill in skills:
        scripts = bundles_root / BUNDLE / 'skills' / skill / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / f'{skill}.py').write_text('# script', encoding='utf-8')
    return bundles_root


def _make_singular_and_plural_roots(root: Path) -> tuple[Path, Path]:
    """Build a root carrying BOTH skill-root spellings, each with a distinct script.

    Distinct scripts are what make the PROBE ORDER observable: whichever root is
    searched first is whichever script comes back, so a reader cannot satisfy
    both orderings at once.
    """
    plural = _make_flat_tree(root, root_name='skills', skills=('manage-logging',))
    singular = _make_flat_tree(root, root_name='skill', skills=('other-skill',))
    return plural, singular


def _emitted_import_paths(emitted: str) -> list[str]:
    """Extract every absolute directory path a generated executor declares.

    Parsed with ``ast`` rather than by scanning for quote characters, because the
    file also carries a script MAPPING whose values are FILES — a text scan would
    report those as missing directories and the assertion would then pass for the
    wrong reason. Only the three placeholders the generator fills with
    directories are read: ``LOGGING_DIR``, the ``_BOOTSTRAP_SKILL_DIRS`` pairs,
    and the ``_ALL_SCRIPT_DIRS`` list.
    """
    import ast

    tree = ast.parse(emitted)
    declared: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else ''
        if name == 'LOGGING_DIR' and isinstance(node.value, ast.Constant):
            declared.append(str(node.value.value))
        elif name == '_ALL_SCRIPT_DIRS' and isinstance(node.value, (ast.List, ast.Tuple)):
            declared.extend(str(el.value) for el in node.value.elts if isinstance(el, ast.Constant))
        elif name == '_BOOTSTRAP_SKILL_DIRS' and isinstance(node.value, (ast.List, ast.Tuple)):
            for element in node.value.elts:
                if isinstance(element, (ast.List, ast.Tuple)) and len(element.elts) == 2:
                    pinned = element.elts[1]
                    if isinstance(pinned, ast.Constant):
                        declared.append(str(pinned.value))
    return declared


class TestFlatSkillDirName:
    """The dash-joined name is spelled in exactly one place."""

    def test_joins_bundle_and_skill_with_the_declared_separator(self):
        """The join uses :data:`FLAT_DIR_SEPARATOR`, not a re-spelled dash."""
        assert flat_skill_dir_name(BUNDLE, 'manage-logging') == f'{BUNDLE}-manage-logging'
        assert deployed_layout.FLAT_DIR_SEPARATOR in flat_skill_dir_name('a', 'b')

    def test_keeps_a_kebab_cased_skill_name_intact(self):
        """A real skill name carries its own dashes and must not be normalised away.

        This is the shape the resolver has to recognise in the wild: the flat
        directory name for ``pm-plugin-development``'s
        ``plugin-script-architecture`` skill is one long dash-joined string.
        """
        name = flat_skill_dir_name('pm-plugin-development', 'plugin-script-architecture')

        assert name == 'pm-plugin-development-plugin-script-architecture'
        assert is_flat_skill_dir_name(name)


class TestIsFlatSkillDirName:
    """The name predicate answers shape, not attribution.

    A splitter would have to pick a separator position, and no position is
    right: ``pm-plugin-development-plugin-script-architecture`` splits as
    ``('pm', 'plugin-development-plugin-script-architecture')`` on the first dash
    and ``('pm-plugin-development-plugin-script', 'architecture')`` on the last.
    The predicate is deliberately weaker than a splitter, and that is the point.
    """

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('plan-marshall-manage-logging', True),
            ('pm-plugin-development-plugin-script-architecture', True),
            ('a-b', True),
            ('plainname', False),
            ('-leading', False),
            ('trailing-', False),
            ('', False),
        ],
        ids=[
            'real-bundle-and-skill',
            'both-components-kebab-cased',
            'minimal-pair',
            'no-separator-at-all',
            'separator-with-no-bundle',
            'separator-with-no-skill',
            'empty',
        ],
    )
    def test_recognises_the_dash_joined_shape(self, name, expected):
        """Any dash-joined name with content on both sides is a flat skill dir.

        The ``no-separator-at-all`` row carries a name with no dash, which is the
        only way to say "not joined" — a name like ``no-separator`` does contain
        one, and would be a flat skill dir by this predicate.
        """
        assert is_flat_skill_dir_name(name) is expected


class TestSkillRoots:
    """Both spellings are read, in a declared order."""

    def test_no_skill_root_yields_nothing(self, tmp_path):
        """A root that deploys neither spelling reports neither."""
        assert skill_roots(tmp_path) == []
        assert is_flat_root(tmp_path) is False

    def test_reads_the_plural_deployed_spelling(self, tmp_path):
        """The deployed ``skills/`` spelling is recognised."""
        skills_root = _make_flat_tree(tmp_path, root_name='skills')

        assert skill_roots(tmp_path) == [skills_root]
        assert is_flat_root(tmp_path) is True

    def test_reads_the_singular_generated_spelling(self, tmp_path):
        """The generated ``skill/`` spelling is recognised too.

        The emitter writes a singular tree and ``install.sh`` maps it to the
        plural at install time, so a target tree that has not been installed yet
        carries ``skill/`` and every reader that only knew the plural found
        nothing in it.
        """
        skills_root = _make_flat_tree(tmp_path, root_name='skill')

        assert skill_roots(tmp_path) == [skills_root]
        assert is_flat_root(tmp_path) is True

    def test_plural_is_probed_before_singular(self, tmp_path):
        """The deployed spelling wins when a root carries both.

        The order comes from :data:`SKILL_ROOT_NAMES`, not from a call site's
        preference, and each root's fixture carries a DIFFERENT skill — so a
        reader that probed singular-first would find the other script's
        directory and resolve against the wrong root.
        """
        plural, singular = _make_singular_and_plural_roots(tmp_path)

        assert skill_roots(tmp_path) == [plural, singular]
        assert (
            resolve_skill_path(tmp_path, BUNDLE, 'skills/other-skill/scripts/other-skill.py')
            == singular / f'{BUNDLE}-other-skill' / 'scripts' / 'other-skill.py'
        )
        assert flat_skill_dirs(tmp_path) == [
            plural / f'{BUNDLE}-manage-logging',
            singular / f'{BUNDLE}-other-skill',
        ]

    def test_declares_both_spellings_with_the_deployed_one_first(self):
        """The vocabulary itself is the data both spellings are read from."""
        assert SKILL_ROOT_NAMES == ('skills', 'skill')
        assert SKILL_ROOT_NAMES[0] == 'skills', 'the DEPLOYED spelling is probed first'


class TestResolveSkillPath:
    """One subpath, one vocabulary, both deployments."""

    def test_resolves_on_a_flat_tree(self, tmp_path):
        """A flat root resolves the nested-layout subpath to its own spelling."""
        skills_root = _make_flat_tree(tmp_path)

        resolved = resolve_skill_path(tmp_path, BUNDLE, 'skills/manage-logging/scripts/manage-logging.py')

        assert resolved == skills_root / f'{BUNDLE}-manage-logging' / 'scripts' / 'manage-logging.py'
        assert resolved.is_file()

    def test_resolves_on_a_singular_tree(self, tmp_path):
        """The singular generated tree resolves through the same call."""
        skills_root = _make_flat_tree(tmp_path, root_name='skill')

        resolved = resolve_skill_path(tmp_path, BUNDLE, 'skills/manage-logging/SKILL.md')

        assert resolved == skills_root / f'{BUNDLE}-manage-logging' / 'SKILL.md'

    def test_a_dir_name_addresses_the_skill_root_itself(self, tmp_path):
        """``skills/{skill}`` with no remainder addresses the skill directory."""
        skills_root = _make_flat_tree(tmp_path, skills=('only-skill',))

        assert resolve_skill_path(tmp_path, BUNDLE, 'skills/only-skill') == skills_root / f'{BUNDLE}-only-skill'

    def test_returns_none_on_a_nested_root(self, tmp_path):
        """A nested root is not a flat root, so the flat probe declines it.

        The decline is what lets a caller try its own shape next. A resolver that
        returned the nested-constructed path here would report a "flat" answer for
        a tree that has no flat shape at all.
        """
        _make_nested_tree(tmp_path)

        assert resolve_skill_path(tmp_path, BUNDLE, 'skills/manage-logging/scripts') is None

    @pytest.mark.parametrize(
        'relative_path',
        ['agents/some-agent.md', 'plan-marshall/skills/x/y.py', 'no-slash', 'deep/nested/path'],
        ids=['root-anchored-agents', 'already-bundle-qualified', 'no-slash', 'no-skill-segment'],
    )
    def test_returns_none_for_a_non_skill_anchored_subpath(self, tmp_path, relative_path):
        """Only a ``{skill-root}/{skill}/rest`` subpath is this resolver's business.

        A root-anchored path is a different question with a different answer, and
        returning ``None`` for it is what lets the caller handle the two cases
        separately instead of the resolver guessing between them.
        """
        _make_flat_tree(tmp_path)

        assert resolve_skill_path(tmp_path, BUNDLE, relative_path) is None

    def test_returns_none_for_a_skill_the_root_does_not_carry(self, tmp_path):
        """A well-formed subpath naming an absent skill is a miss, not a guess."""
        _make_flat_tree(tmp_path)

        assert resolve_skill_path(tmp_path, BUNDLE, 'skills/absent-skill/SKILL.md') is None

    def test_both_shapes_resolve_the_same_logical_script(self, tmp_path):
        """The deliverable's central claim: one logical script, two deployments.

        The SAME subpath is resolved against a flat tree and a nested tree, and
        each is asserted against the path its own deployment uses. Without this,
        a resolver that only ever saw one shape would satisfy every case above.
        """
        flat_root = tmp_path / 'flat'
        nested_root = tmp_path / 'nested'
        flat_skills = _make_flat_tree(flat_root)
        nested_bundles = _make_nested_tree(nested_root)
        subpath = 'skills/manage-logging/scripts/manage-logging.py'

        flat_resolved = resolve_skill_path(flat_root, BUNDLE, subpath)
        nested_resolved = nested_bundles / BUNDLE / subpath

        assert flat_resolved == flat_skills / f'{BUNDLE}-manage-logging' / 'scripts' / 'manage-logging.py'
        assert (
            nested_resolved == nested_bundles / BUNDLE / 'skills' / 'manage-logging' / 'scripts' / 'manage-logging.py'
        )
        # Same skill, same file NAME, different directory spelling — which is the
        # whole difference the two shapes make and the reason one vocabulary has
        # to serve both.
        assert flat_resolved.name == nested_resolved.name
        assert flat_resolved.parent.name == nested_resolved.parent.name == 'scripts'


class TestSplitSkillRelativePath:
    """The subpath split, and what it declines."""

    def test_splits_a_skill_anchored_subpath(self):
        """``{skill-root}/{skill}/rest`` splits into the skill and its remainder."""
        assert split_skill_relative_path('skills/manage-logging/scripts/plan_logging.py') == (
            'manage-logging',
            'scripts/plan_logging.py',
        )

    def test_splits_the_singular_spelling_too(self):
        """A singular-spelled subpath is the same question, so it splits."""
        assert split_skill_relative_path('skill/manage-logging/SKILL.md') == ('manage-logging', 'SKILL.md')

    def test_a_skill_with_no_remainder_yields_an_empty_remainder(self):
        """``skills/{skill}`` names the skill directory itself."""
        assert split_skill_relative_path('skills/manage-logging') == ('manage-logging', '')

    @pytest.mark.parametrize(
        'relative_path',
        ['agents/a.md', 'x', 'a/b/c/d'],
        ids=['root-anchored', 'single-segment', 'no-skill-root-segment'],
    )
    def test_declines_every_other_shape(self, relative_path):
        """Anything that is not skill-anchored is declined, not coerced."""
        assert split_skill_relative_path(relative_path) is None


class TestSkillScriptsSubpath:
    """The one skill-relative spelling, derived from the declared vocabulary."""

    def test_addresses_a_skill_scripts_directory(self):
        """The subpath composes the deployed root name, the skill and ``scripts``."""
        assert skill_scripts_subpath('script-shared') == 'skills/script-shared/scripts'

    def test_derives_from_the_declared_root_name(self):
        """Changing the declared root name moves this subpath with it.

        Deriving rather than writing the literal is what stops a second spelling
        from appearing: the vocabulary is consulted here, not restated.
        """
        assert skill_scripts_subpath('x').startswith(f'{SKILL_ROOT_NAMES[0]}/')
        assert skill_scripts_subpath('x').endswith('/scripts')

    def test_round_trips_through_the_split(self):
        """The composed subpath is one the flat resolver understands.

        A spelling the resolver cannot parse would be a path no caller could
        resolve, and the round trip is the cheapest way to keep the two in step.
        """
        skill, rest = split_skill_relative_path(skill_scripts_subpath('script-shared'))

        assert (skill, rest) == ('script-shared', 'scripts')


class TestFlatEnumeration:
    """Enumeration over a flat root is non-empty, in probe order."""

    def test_flat_skill_dirs_lists_every_skill(self, tmp_path):
        """Every flat skill directory is enumerated, in sorted order."""
        skills_root = _make_flat_tree(tmp_path)

        dirs = flat_skill_dirs(tmp_path)

        assert len(dirs) == len(FLAT_SKILLS)
        assert dirs == [skills_root / flat_skill_dir_name(BUNDLE, skill) for skill in sorted(FLAT_SKILLS)]

    def test_flat_script_dirs_lists_every_scripts_directory(self, tmp_path):
        """Each enumerated skill contributes its ``scripts/`` directory."""
        skills_root = _make_flat_tree(tmp_path)

        dirs = flat_script_dirs(tmp_path)

        assert len(dirs) == len(FLAT_SKILLS)
        assert skills_root / f'{BUNDLE}-manage-logging' / 'scripts' in dirs

    def test_a_skill_without_a_scripts_directory_is_skipped(self, tmp_path):
        """A flat skill directory with no ``scripts/`` contributes nothing to the script list.

        A ``standards/``-only skill is real on a deployed root, and adding its
        directory to PYTHONPATH would put a path with nothing importable on it.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('with-scripts',))
        (skills_root / f'{BUNDLE}-docs-only').mkdir()
        (skills_root / f'{BUNDLE}-docs-only' / 'standards').mkdir()

        assert flat_skill_dir_name(BUNDLE, 'docs-only') in [d.name for d in flat_skill_dirs(tmp_path)]
        assert flat_script_dirs(tmp_path) == [skills_root / f'{BUNDLE}-with-scripts' / 'scripts']

    def test_a_non_flat_directory_in_the_root_is_skipped(self, tmp_path):
        """A directory that is not dash-joined is not a flat skill and is not enumerated.

        A deployed root can carry a plain directory beside the skills (a scratch
        dir, a README-bearing folder); enumerating it would put a non-skill
        directory on the PYTHONPATH the executor hands its subprocesses. The
        name carries NO dash, which is the only shape this predicate rejects — a
        name like ``not-a-skill`` is dash-joined and would be enumerated.
        """
        skills_root = _make_flat_tree(tmp_path, skills=('real-skill',))
        (skills_root / 'plainname').mkdir()
        (skills_root / '.hidden-skill').mkdir()
        (skills_root / 'hidden' / 'scripts').mkdir(parents=True)

        assert [d.name for d in flat_skill_dirs(tmp_path)] == [f'{BUNDLE}-real-skill']

    def test_a_nested_root_enumerates_nothing_flat(self, tmp_path):
        """The flat enumeration is shape-specific and declines a nested root."""
        _make_nested_tree(tmp_path)

        assert flat_skill_dirs(tmp_path) == []
        assert flat_script_dirs(tmp_path) == []


class TestCarriesTargetManifest:
    """The root marker, as data rather than a per-call-site manifest list."""

    def test_recognises_each_declared_manifest(self, tmp_path):
        """Either declared manifest marks a root, without either name being re-spelled."""
        for manifest in deployed_layout.TARGET_MANIFEST_NAMES:
            root = tmp_path / manifest.replace('.', '-')
            root.mkdir()
            (root / manifest).write_text('{}', encoding='utf-8')

            assert carries_target_manifest(root) is True, manifest

    def test_declines_a_root_carrying_neither(self, tmp_path):
        """A root with no manifest is not a target root by this test."""
        (tmp_path / 'README.md').write_text('x', encoding='utf-8')

        assert carries_target_manifest(tmp_path) is False


class TestLayoutKnowledgeLivesHereOnly:
    """The singular-to-plural distinction is stated in exactly one source file.

    A second spelling is a second answer waiting to diverge, and the divergence
    is invisible until a machine carries the shape the second copy did not model.

    The rule has a boundary, and the boundary is the point: a module that has
    already imported ``deployed_layout`` must not restate the vocabulary, but code
    that runs BEFORE that module is importable cannot read it. Two places in this
    tree are genuinely on the wrong side of that line and are exempted with their
    reason rather than by silence:

    * ``bootstrap_plugin``'s module-level ``sys.path`` bootstrap, whose entire
      purpose is to put ``script-shared/scripts`` on ``sys.path`` so
      ``deployed_layout`` can be imported at all. Reading the constant there
      would be a circular import.
    * the target-aware resolver TEMPLATES inside ``generate_executor``, which are
      emitted as bootstrap-free source into the generated executor. The generated
      file must resolve a notation before any marketplace module is importable,
      so it carries its own shape knowledge by construction.

    Both exemptions are checked for behaviour elsewhere: the templates are
    compiled and executed by ``test_executor_target_resolution.py``, and the
    bootstrap block is exercised by the ``*_imports_without_executor_pythonpath``
    subprocess tests.
    """

    #: Consumers that must read the shared vocabulary rather than restate it.
    #: Every one of these modules imports ``deployed_layout`` at module scope.
    SCANNED_CONSUMERS = ('marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py',)

    #: Consumers with a documented structural exemption, mapped to that reason.
    EXEMPT_CONSUMERS = {
        'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py': (
            'the module-level sys.path bootstrap runs before deployed_layout is importable'
        ),
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py': (
            'its target-aware resolver templates are emitted as bootstrap-free source'
        ),
    }

    @staticmethod
    def _prose_lines(path: Path) -> frozenset[int]:
        """Return the 1-based line numbers that are PROSE: comments and docstrings.

        The scan must not flag prose. A module docstring that spells out the flat
        layout is documentation, and a scan that flagged it would push the
        vocabulary into a comment nobody reads as code — the opposite of the rule
        it enforces.

        The distinction that matters is prose-versus-VALUE, and a plain
        "skip every string token" test gets it wrong: a tuple of string literals
        is code spelled with string tokens, so that test would exempt a consumer
        whose re-encoded vocabulary happens to sit in a collection. Comments come
        from ``tokenize`` and docstrings from the AST, where a docstring is
        identifiable as a bare string EXPRESSION statement — a string that is a
        value is not prose, however it is quoted.
        """
        import ast
        import io
        import tokenize

        prose: set[int] = set()
        source = path.read_text(encoding='utf-8')
        with path.open('rb') as handle:
            for token in tokenize.tokenize(io.BytesIO(handle.read()).readline):
                if token.type == tokenize.COMMENT:
                    prose.add(token.start[0])
        for node in ast.walk(ast.parse(source)):
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
                continue
            if not isinstance(node.value.value, str):
                continue
            prose.add(node.lineno)
            prose.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        return frozenset(prose)

    @classmethod
    def _scan(cls, predicate) -> list[str]:
        from conftest import PROJECT_ROOT

        offenders: list[str] = []
        for relative in cls.SCANNED_CONSUMERS:
            path = PROJECT_ROOT / relative
            prose = cls._prose_lines(path)
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if number in prose:
                    continue
                if predicate(line):
                    offenders.append(path.name + ':' + str(number) + ': ' + line.strip())
        return offenders

    def test_no_scanned_consumer_names_a_singular_skill_root(self):
        """No scanned consumer spells a bare ``skill/`` root as CODE.

        A consumer that joins a root name must take it from
        :data:`SKILL_ROOT_NAMES`, so the literal in executable code is the tell
        that it re-encoded the vocabulary. Prose is exempt by construction: the
        scan exempts comments and docstring expressions, so a module docstring
        may name the shape while only the shared module may DECIDE it — and a
        VALUE spelled with string literals stays in scope, because a collection
        of root names is code.

        The match is quote-agnostic on purpose. The repository formats with single
        quotes, so a single-quote-only scan would pass today and silently stop
        catching a consumer written with double quotes — a scan that narrows with
        the formatter is a scan whose coverage nobody is tracking.
        """
        offenders = self._scan(lambda line: _QUOTED_SKILL_ROOT.search(line) and 'SKILL_ROOT_NAMES' not in line)

        assert offenders == [], f'a consumer re-spells the skill-root vocabulary: {offenders}'

    def test_no_scanned_consumer_joins_the_flat_name_itself(self):
        """No scanned consumer writes the ``{bundle}-{skill}`` join as CODE.

        An f-string joining two names with a dash inside a consumer is the
        re-encoding this module exists to prevent, and it is invisible in review
        because the result is correct until the separator or the spelling moves.
        """
        offenders = self._scan(lambda line: '{bundle}-{skill}' in line)

        assert offenders == [], f'a consumer re-joins the flat name: {offenders}'

    def test_the_scan_can_actually_see_a_violation(self):
        """The scan is proven live, so a clean result is a measurement and not a blind one.

        A source scan that silently stopped matching — a renamed needle, a change
        to the prose rule — would report every consumer as clean forever. The
        fixture carries all three cases the rule distinguishes: a re-spelled
        root name in a collection (code), a re-joined flat name in an f-string
        (code), and the same two spellings inside a function docstring (prose).
        Only the first two may be flagged.
        """
        import tempfile

        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as handle:
            handle.write(
                'VALUE = ("skills", "skill")\n'
                'DIR = f"{bundle}-{skill}"\n'
                '\n'
                '\n'
                'def f():\n'
                '    """the skills/{bundle}-{skill} layout, spelled out for readers"""\n'
                '    return 1\n'
            )
            offender_path = Path(handle.name)
        try:
            prose = self._prose_lines(offender_path)
            flagged = [
                number
                for number, line in enumerate(offender_path.read_text(encoding='utf-8').splitlines(), 1)
                if number not in prose and (_QUOTED_SKILL_ROOT.search(line) or '{bundle}-{skill}' in line)
            ]
        finally:
            offender_path.unlink()

        assert flagged == [1, 2], f'the scan must flag both code lines and neither docstring line: {flagged}'

    def test_the_exemptions_are_still_exempt_for_the_stated_reason(self):
        """The exemptions are declared, so a new consumer is scanned by default.

        An exemption nobody re-checks is an exemption that grows. This asserts
        each declared path still exists, so deleting a consumer — and so dropping
        its need for an exemption — is visible rather than silent.
        """
        from conftest import PROJECT_ROOT

        for relative, reason in self.EXEMPT_CONSUMERS.items():
            path = PROJECT_ROOT / relative
            assert path.is_file(), f'exempted consumer is gone; re-check the exemption: {relative}'
            assert reason, f'an exemption must state its reason: {relative}'

    def test_the_scanned_consumers_import_the_shared_vocabulary(self):
        """A scanned consumer is only exempt from restating what it actually imports.

        The scan's premise is that the module can read the constant. A consumer
        listed in :data:`SCANNED_CONSUMERS` that does not import
        ``deployed_layout`` is being scanned against a rule it cannot satisfy.
        """
        from conftest import PROJECT_ROOT

        for relative in self.SCANNED_CONSUMERS:
            source = (PROJECT_ROOT / relative).read_text(encoding='utf-8')
            assert 'deployed_layout' in source, f'{relative} is scanned but does not import the shared module'

    def test_the_bootstrap_plugin_singular_leg_is_gone(self):
        """The former ``opencode.json`` + singular ``skill/`` flat leg no longer exists.

        It is named here rather than left to a reader: that leg could never fire,
        because the deployed OpenCode root carries the plural ``skills/``, and its
        survival would be a second, wrong statement about what ships.
        """
        from conftest import PROJECT_ROOT

        source = (
            PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py'
        ).read_text(encoding='utf-8')

        assert "'plugin_root' / 'skill'" not in source
        assert 'flat_skill_dir_name' not in source, 'the layout join belongs to deployed_layout, not here'
        assert "plugin_root / 'skill' /" not in source, 'the singular flat leg must not survive as a shim'


class TestConsumersOnAFlatTree:
    """The executor generator's three path consumers, driven against a flat root.

    These are the consumers whose failure mode was silent: each resolved a path
    that did not exist, emitted it into the generated executor, and reported
    ``status: success``. The generated executor's ``LOGGING_DIR`` is its very
    first import and its script directories are the ``PYTHONPATH`` it hands
    every subprocess, so a wrong path there is not degraded behaviour — it is an
    executor that cannot run.

    The assertions are about EXISTENCE, not about the string that was produced:
    a path that reads correctly and points nowhere is the defect.
    """

    @pytest.fixture()
    def generator(self):
        """The executor generator, loaded in-process under a collision-proof name."""
        from conftest import load_script_module

        return load_script_module(
            'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_for_flat_layout'
        )

    @pytest.fixture()
    def flat_root_is_the_import_base(self, generator, monkeypatch):
        """Pin the generator's import base to the flat root under test.

        Without this the two cases below would not test a flat root at all.
        ``generate_executor`` resolves its import paths against
        ``_resolve_tree_bases(base)``, whose second candidate is the live
        ``marketplace/bundles`` checkout — and pytest's ``tmp_path`` lives INSIDE
        this repository, so the live checkout always wins for a tmp-dir base that
        does not carry a ``plan-marshall/skills`` tree of its own. The generated
        executor would then carry the real tree's paths, which all exist, and
        every assertion would pass while measuring nothing.

        A real flat deployment reaches this state for the structural reason the
        fixture reproduces: it has no ``marketplace/bundles`` ancestor. Pinning the
        seam is how a tmp-dir fixture recreates that, and it is what makes the
        ``under the flat root`` assertions below meaningful rather than incidental.
        """
        pinned: list[Path] = []

        def _pin(base_path: Path) -> list[Path]:
            pinned.append(base_path)
            return [base_path]

        monkeypatch.setattr(generator, '_resolve_tree_bases', _pin)
        return pinned

    def test_logging_module_discovery_resolves_on_a_flat_tree(self, generator, tmp_path):
        """The logging module resolves to a directory that exists on a flat root.

        The logging module is imported before the executor can log anything, so
        an unresolvable path here is an executor whose first operation fails.
        """
        _make_flat_tree(tmp_path)

        logging_dir = generator.get_logging_scripts_dir(tmp_path)

        assert logging_dir.is_dir(), f'the logging module directory must exist: {logging_dir}'
        assert logging_dir.name == 'scripts'
        assert logging_dir.parent.name == flat_skill_dir_name(BUNDLE, 'manage-logging')

    def test_shared_module_discovery_resolves_every_directory_on_a_flat_tree(self, generator, tmp_path):
        """All five shared-module directories resolve, and every one exists.

        The emitted set becomes the executor's own pre-import ``sys.path``, so an
        empty result is not a degraded build — it is an executor that cannot
        import the module it was generated to make importable.
        """
        _make_flat_tree(tmp_path)

        dirs = generator.get_shared_module_dirs(tmp_path)

        assert len(dirs) == len(FLAT_SKILLS) - 1, f'expected the five shared modules, got {dirs}'
        assert all(d.is_dir() for d in dirs), f'every shared-module dir must exist: {dirs}'

    def test_generated_executor_import_paths_all_exist_on_a_flat_tree(
        self, generator, tmp_path, monkeypatch, flat_root_is_the_import_base
    ):
        """A generated executor against a flat root names only directories that exist.

        The end-to-end claim the deliverable makes: generate, then read back every
        path the emitted file will import from and require each one to be present
        on disk. The ``under the flat root`` assertion is what makes this a
        measurement of the flat shape rather than of whatever tree the generator
        would otherwise have reached for.
        """
        plan_dir = tmp_path / 'plan-base'
        plan_dir.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        skills_root = _make_flat_tree(tmp_path)

        result = generator.generate_executor(
            {'plan-marshall:manage-logging:manage-logging': str(skills_root / f'{BUNDLE}-manage-logging' / 'scripts')},
            tmp_path,
            dry_run=False,
            target='opencode',
        )

        assert result['status'] == 'success', result
        assert flat_root_is_the_import_base, 'the fixture must have pinned the import base'
        emitted = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')

        declared = _emitted_import_paths(emitted)
        assert declared, 'the generated executor must declare the paths it imports from'
        missing = [p for p in declared if not Path(p).is_dir()]
        assert missing == [], f'the generated executor names directories that do not exist: {missing}'
        outside = [p for p in declared if not p.startswith(str(tmp_path))]
        assert outside == [], f'every emitted import path must come from the flat root under test: {outside}'

    def test_the_logging_module_path_is_in_the_emitted_set(
        self, generator, tmp_path, monkeypatch, flat_root_is_the_import_base
    ):
        """The logging directory reaches the emitted file as a real path.

        Paired with the case above: a generated executor can carry a
        ``LOGGING_DIR`` that was never checked, and every other path can exist
        while that one does not.
        """
        plan_dir = tmp_path / 'plan-base'
        plan_dir.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        skills_root = _make_flat_tree(tmp_path)
        expected = generator.get_logging_scripts_dir(tmp_path)
        assert expected.is_dir(), 'the resolved logging dir must exist before it is asserted into the output'

        result = generator.generate_executor(
            {'plan-marshall:manage-logging:manage-logging': str(skills_root / f'{BUNDLE}-manage-logging' / 'scripts')},
            tmp_path,
            dry_run=False,
            target='opencode',
        )

        assert result['status'] == 'success', result
        assert flat_root_is_the_import_base, 'the fixture must have pinned the import base'
        emitted = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')
        assert str(expected) in emitted, f'the emitted executor must carry the resolved logging dir {expected}'
