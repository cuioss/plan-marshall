#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``read_previous_surfaces`` reports HOW it failed, and guard 5 acts on it.

The fail-open guard asks one question: *"did the previous executor carry
surfaces this write is about to strip?"* A bare ``dict`` return answered both
"no, it verifiably carried none" and "unknown, it could not be read" with the
same empty mapping — so the guard read the second as the first and passed an
unreadable previous straight through, writing a surfaces-less executor. That is
precisely the fail-open it exists to refuse, reintroduced through its own input.

The partition that matters is MEASURED vs NOT MEASURED, not empty vs non-empty:

- ``absent`` / ``no_block`` — measurements that legitimately yield no surfaces
  (a fresh install; an executor generated before the map existed). A
  zero-surface generation against either is a normal first build.
- ``read`` — the block was found and parsed; the mapping is what it held.
- ``unreadable`` — the file EXISTS and its surfaces could not be established.
  Nothing was measured, so the empty mapping is not evidence of anything.

Every ``unreadable`` shape is driven here rather than one standing in for the
rest, because each reaches the verdict through a different branch: the read
raising, the block having no terminating brace, the literal refusing to parse,
and the literal parsing to something that is not a dict.

The stats-line cases pin the emission contract stated in
``format_surface_stats_line``: the line is a VALUE a consumer reads, never an
absence it infers from.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'tools-script-executor')
GENERATE_SCRIPT = SCRIPTS_DIR / 'generate_executor.py'


def load_module():
    """Load generate_executor as a standalone module (the file's own convention)."""
    code = GENERATE_SCRIPT.read_text(encoding='utf-8')
    module = types.ModuleType('generate_executor_failure_modes')
    module.__dict__['__file__'] = str(GENERATE_SCRIPT)
    exec(code, module.__dict__)
    return module


# --- previous-executor fixtures, one per outcome -----------------------------

#: A previous executor whose SCRIPT_SURFACES block parses and holds one entry.
_WITH_ONE_SURFACE = """#!/usr/bin/env python3
SCRIPTS = {
}
SCRIPT_SURFACES = {
    "a:b:c": {"digest": "d0", "surface": {"root": {"children": {}}}},
}
"""

#: Read in full, carries no block at all — a pre-SCRIPT_SURFACES executor.
_WITHOUT_BLOCK = '#!/usr/bin/env python3\nSCRIPTS = {\n}\n'

#: The block opens and the file ends — no terminating ``\n}`` to bound the literal.
_UNTERMINATED_BLOCK = '#!/usr/bin/env python3\nSCRIPT_SURFACES = {\n    "a:b:c": {"digest": "d0"},\n'

#: The block is bounded but its body is not a Python literal at all.
_MALFORMED_LITERAL = '#!/usr/bin/env python3\nSCRIPT_SURFACES = {\n    "a:b:c": <<<not python>>>,\n}\n'

#: The literal parses — to a SET, not a mapping. ``{1, 2}`` is valid Python.
_NON_DICT_LITERAL = '#!/usr/bin/env python3\nSCRIPT_SURFACES = {\n    1,\n    2,\n}\n'


@pytest.fixture
def generator(tmp_path, monkeypatch):
    """A loaded generator whose executor destination is an isolated tmp tree."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    module = load_module()
    return module, plan_dir / 'execute-script.py'


def _stage(executor: Path, text: str | None) -> None:
    """Write (or deliberately omit) the previous executor."""
    if text is not None:
        executor.write_text(text, encoding='utf-8')


def _zero_derivation(module, monkeypatch, registered: int = 1) -> None:
    """Force the generation to emit ZERO surfaces, without a real script set.

    Patched at ``derive_script_surfaces`` so the guard's INPUT is the only
    variable across the cases below — the reason nothing derived is held fixed,
    and only the previous-executor state changes.
    """
    stats = dict(module._EMPTY_SURFACE_STATS)
    stats['scripts_registered'] = registered
    stats['surfaces_not_derivable'] = registered
    monkeypatch.setattr(module, 'derive_script_surfaces', lambda *a, **k: ({}, dict(stats)))


def _generate(module):
    return module.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='claude')


# =============================================================================
# read_previous_surfaces — the four outcomes
# =============================================================================


class TestOutcomeIsReported:
    def test_absent_file_is_absent_not_unreadable(self, generator):
        module, executor = generator
        previous = module.read_previous_surfaces(executor)
        assert previous.outcome == 'absent'
        assert previous.surfaces == {}
        assert previous.detail == ''

    def test_file_without_the_block_is_no_block(self, generator):
        module, executor = generator
        _stage(executor, _WITHOUT_BLOCK)
        previous = module.read_previous_surfaces(executor)
        assert previous.outcome == 'no_block'
        assert previous.surfaces == {}

    def test_parsed_block_is_read_and_carries_its_entries(self, generator):
        module, executor = generator
        _stage(executor, _WITH_ONE_SURFACE)
        previous = module.read_previous_surfaces(executor)
        assert previous.outcome == 'read'
        assert set(previous.surfaces) == {'a:b:c'}

    def test_an_empty_but_parsed_block_is_read_not_absent(self, generator):
        """``{}`` is a MEASUREMENT of zero, distinct from every non-read outcome."""
        module, executor = generator
        _stage(executor, '#!/usr/bin/env python3\nSCRIPT_SURFACES = {\n}\n')
        previous = module.read_previous_surfaces(executor)
        assert previous.outcome == 'read'
        assert previous.surfaces == {}

    @pytest.mark.parametrize(
        ('text', 'id_'),
        [
            pytest.param(_UNTERMINATED_BLOCK, 'no_terminating_brace', id='unterminated'),
            pytest.param(_MALFORMED_LITERAL, 'would not parse', id='malformed_literal'),
            pytest.param(_NON_DICT_LITERAL, 'not a dict', id='non_dict'),
        ],
    )
    def test_each_unreadable_shape_reports_unreadable_with_a_detail(self, generator, text, id_):
        """Every branch that cannot establish the surfaces says so, and says why."""
        module, executor = generator
        _stage(executor, text)

        previous = module.read_previous_surfaces(executor)

        assert previous.outcome == 'unreadable'
        assert previous.surfaces == {}
        assert str(executor) in previous.detail, previous.detail

    def test_an_unreadable_read_error_reports_unreadable(self, generator, monkeypatch):
        """An ``OSError`` on the read is unreadable, not absent.

        The file exists — ``is_file()`` passed — so the empty mapping here would
        otherwise be indistinguishable from a fresh install.
        """
        module, executor = generator
        _stage(executor, _WITH_ONE_SURFACE)

        def _boom(*_a, **_k):
            raise OSError('permission denied')

        monkeypatch.setattr(Path, 'read_text', _boom)

        previous = module.read_previous_surfaces(executor)

        assert previous.outcome == 'unreadable'
        assert 'permission denied' in previous.detail

    def test_every_outcome_is_in_the_declared_vocabulary(self, generator):
        """The vocabulary is CLOSED — a consumer may branch on it exhaustively."""
        module, executor = generator
        seen = set()
        for text in (None, _WITHOUT_BLOCK, _WITH_ONE_SURFACE, _MALFORMED_LITERAL):
            if text is None:
                executor.unlink(missing_ok=True)
            else:
                _stage(executor, text)
            seen.add(module.read_previous_surfaces(executor).outcome)

        assert seen == {'absent', 'no_block', 'read', 'unreadable'}
        assert seen <= module.PREVIOUS_SURFACE_OUTCOMES


# =============================================================================
# Guard 5 acts on the outcome, not on the emptiness
# =============================================================================


class TestGuardFiveReadsTheOutcome:
    @pytest.mark.parametrize(
        'text',
        [
            pytest.param(_UNTERMINATED_BLOCK, id='unterminated'),
            pytest.param(_MALFORMED_LITERAL, id='malformed_literal'),
            pytest.param(_NON_DICT_LITERAL, id='non_dict'),
        ],
    )
    def test_zero_surfaces_against_an_unreadable_previous_refuses(self, generator, monkeypatch, text):
        """THE regression: an unreadable previous is not proof that none are lost."""
        module, executor = generator
        _stage(executor, text)
        before = executor.read_text(encoding='utf-8')
        _zero_derivation(module, monkeypatch)

        result = _generate(module)

        assert result['status'] == 'error', result
        assert 'could not be read' in result['error'], result['error']
        assert result['previous_surfaces_outcome'] == 'unreadable'
        assert executor.read_text(encoding='utf-8') == before, 'a refusing generation must write nothing'

    def test_zero_surfaces_against_a_populated_previous_still_refuses(self, generator, monkeypatch):
        """The counted arm is unchanged — this is the case the guard always had."""
        module, executor = generator
        _stage(executor, _WITH_ONE_SURFACE)
        _zero_derivation(module, monkeypatch)

        result = _generate(module)

        assert result['status'] == 'error', result
        assert 'carried 1 derived surface' in result['error'], result['error']
        assert result['previous_surfaces_outcome'] == 'read'

    @pytest.mark.parametrize(
        ('text', 'outcome'),
        [
            pytest.param(None, 'absent', id='fresh_install'),
            pytest.param(_WITHOUT_BLOCK, 'no_block', id='pre_map_executor'),
        ],
    )
    def test_zero_surfaces_against_a_verifiably_empty_previous_is_written(self, generator, monkeypatch, text, outcome):
        """A previous that verifiably carried none is not a regression.

        This is the discriminating half: without it, the refusals above would
        also pass on a guard that rejected EVERY zero-surface generation, and the
        ``status: error`` assertions would be measuring the patched derivation
        rather than the guard's input.
        """
        module, executor = generator
        _stage(executor, text)
        _zero_derivation(module, monkeypatch)

        result = _generate(module)

        assert result['status'] == 'success', result
        assert executor.is_file(), 'a first build with no previous surfaces is written normally'

    def test_an_unreadable_previous_does_not_refuse_when_surfaces_ARE_emitted(self, generator, monkeypatch):
        """Only a ZERO-surface write can strip anything.

        A generation that emits surfaces replaces the unreadable executor with a
        validating one, so the unknown previous state cannot make it a
        regression. Without this the guard would refuse every regeneration that
        followed a corrupt executor, with no way forward.
        """
        module, executor = generator
        _stage(executor, _MALFORMED_LITERAL)
        stats = dict(module._EMPTY_SURFACE_STATS)
        stats['scripts_registered'] = 1
        stats['surfaces_derived'] = 1
        entry = {'digest': 'd1', 'surface': {'root': {'children': {}}}}
        monkeypatch.setattr(module, 'derive_script_surfaces', lambda *a, **k: ({'a:b:c': entry}, dict(stats)))

        result = _generate(module)

        assert result['status'] == 'success', result
        assert module.read_previous_surfaces(executor).outcome == 'read'


# =============================================================================
# The surface-stats line, on every return path
# =============================================================================


class TestStatsLineEmission:
    def test_the_line_is_emitted_on_the_success_path(self, generator, monkeypatch, capsys):
        module, executor = generator
        _zero_derivation(module, monkeypatch)

        _generate(module)

        out = capsys.readouterr().out
        assert module._SURFACE_STATS_LINE_PREFIX in out
        assert 'surfaces_derived=0' in out

    def test_the_line_is_emitted_on_the_fail_open_refusal(self, generator, monkeypatch, capsys):
        """The refusal path carries IDENTICAL counts — the line is unconditional."""
        module, executor = generator
        _stage(executor, _WITH_ONE_SURFACE)
        _zero_derivation(module, monkeypatch)

        result = _generate(module)
        out = capsys.readouterr().out

        assert result['status'] == 'error'
        assert module._SURFACE_STATS_LINE_PREFIX in out
        assert 'surfaces_derived=0' in out
        assert 'surfaces_reused=0' in out

    def test_the_line_is_emitted_on_the_unreadable_previous_refusal(self, generator, monkeypatch, capsys):
        module, executor = generator
        _stage(executor, _MALFORMED_LITERAL)
        _zero_derivation(module, monkeypatch)

        result = _generate(module)
        out = capsys.readouterr().out

        assert result['status'] == 'error'
        assert module._SURFACE_STATS_LINE_PREFIX in out

    def test_no_line_before_the_derivation_outcome_is_known(self, generator, monkeypatch, capsys):
        """Guard 1 refuses ahead of derivation, so there is no outcome to report.

        The line reports the derivation outcome; printing one where nothing was
        derived — and nothing could have been — would publish a zero that
        describes no run at all.
        """
        module, executor = generator
        monkeypatch.setattr(module, '_SUPPORTED_TEMPLATE_FORMAT_VERSION', 999)

        result = _generate(module)
        out = capsys.readouterr().out

        assert result['status'] == 'error'
        assert 'Template format skew' in result['error']
        assert module._SURFACE_STATS_LINE_PREFIX not in out

    def test_a_dry_run_emits_no_stats_line(self, generator, capsys):
        """A preview derives nothing, so it reports no derivation outcome."""
        module, _executor = generator

        result = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=True, target='claude')
        out = capsys.readouterr().out

        assert result['status'] == 'success'
        assert result['dry_run'] is True
        assert module._SURFACE_STATS_LINE_PREFIX not in out
