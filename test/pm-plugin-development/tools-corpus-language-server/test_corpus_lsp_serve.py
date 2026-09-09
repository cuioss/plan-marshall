#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end tests for `serve` as an LSP CLIENT actually spawns it.

These drive the real script as a subprocess with **no `PYTHONPATH`**, which is
the environment any `lspServers` declaration produces — this bundle ships none,
so the declaration is operator-added, but either way the client spawns the
script directly and there is no executor to inject one.

⚠ The in-process protocol tests cannot catch what these catch. They drive
`LspServer.serve()` against `BytesIO`, so they never exercise the import
bootstrap, and the server's own lenient `read_message` round-trips its own
output — which would hide a corrupted `\\r\\n\\r\\n` header terminator from a
test that only replays it through the same reader.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from test_corpus_index import build_corpus

from conftest import get_script_path, load_script_module

corpus_lsp = load_script_module('pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py')

SCRIPT = get_script_path('pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py')

ENABLED = {'code_intelligence': {'corpus_language_server': {'enabled': True}}}


def _framed(payload: dict) -> bytes:
    body = json.dumps(payload).encode('utf-8')
    return b'Content-Length: %d\r\n\r\n' % len(body) + body


def _handshake(project_path: Path) -> subprocess.CompletedProcess[bytes]:
    """Spawn `serve` the way a client does — no PYTHONPATH — and initialize."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    stdin = _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}) + _framed(
        {'jsonrpc': '2.0', 'method': 'exit'}
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), 'serve', '--project-path', str(project_path)],
        input=stdin,
        capture_output=True,
        env=env,
        timeout=120,
    )


def _capabilities(stdout: bytes) -> dict:
    assert b'\r\n\r\n' in stdout, f'header terminator must be CRLFCRLF, got: {stdout[:60]!r}'
    message = json.loads(stdout.split(b'\r\n\r\n', 1)[1])
    capabilities: dict = message['result']['capabilities']
    return capabilities


def _messages(stdout: bytes) -> list[dict]:
    """Split a framed byte stream into JSON-RPC messages, in order."""
    out: list[dict] = []
    rest = stdout
    while rest:
        header, _, remainder = rest.partition(b'\r\n\r\n')
        length = int(header.split(b':', 1)[1].strip())
        out.append(json.loads(remainder[:length]))
        rest = remainder[length:]
    return out


def _project(root: Path, marshal: dict | None) -> Path:
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    if marshal is not None:
        (root / '.plan').mkdir(parents=True, exist_ok=True)
        (root / '.plan' / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
    return root


class TestServeWithoutPythonPath:
    """The import bootstrap must carry the script when no executor set PYTHONPATH."""

    def test_starts_and_answers_initialize(self, tmp_path: Path) -> None:
        result = _handshake(_project(tmp_path, ENABLED))
        assert result.returncode == 0, result.stderr.decode()
        assert result.stderr == b'', f'a clean start must emit nothing on stderr: {result.stderr!r}'

    def test_enabled_project_advertises_the_three_verbs(self, tmp_path: Path) -> None:
        capabilities = _capabilities(_handshake(_project(tmp_path, ENABLED)).stdout)
        assert capabilities['definitionProvider'] is True
        assert capabilities['referencesProvider'] is True
        assert capabilities['hoverProvider'] is True

    def test_unconfigured_project_advertises_nothing(self, tmp_path: Path) -> None:
        """The no-op path, driven through the real client-facing entry point."""
        assert _capabilities(_handshake(_project(tmp_path, None)).stdout) == {}


class TestFramingSurvivesTheRealPipe:
    """A real pipe is where newline translation would corrupt the LSP header."""

    def test_header_terminator_is_crlfcrlf(self, tmp_path: Path) -> None:
        stdout = _handshake(_project(tmp_path, ENABLED)).stdout
        assert b'\r\n\r\n' in stdout
        assert b'Content-Length:' in stdout

    def test_body_is_parseable_json_rpc(self, tmp_path: Path) -> None:
        stdout = _handshake(_project(tmp_path, ENABLED)).stdout
        message = json.loads(stdout.split(b'\r\n\r\n', 1)[1])
        assert message['jsonrpc'] == '2.0'
        assert message['id'] == 1


class TestBootstrapResolvesBothLayouts:
    """The deployed cache is versioned; the source tree is flat.

    `~/.claude/plugins/cache/{marketplace}/{bundle}/{version}/skills/...`
    interposes a version segment that `marketplace/bundles/{bundle}/skills/...`
    does not. A resolver that assumes either shape finds nothing in the other,
    and because the imports it feeds are module-level that is a start-up crash,
    not a degraded answer — the first implementation was flat-only and died with
    `ModuleNotFoundError` in every installed project.
    """

    @staticmethod
    def _bundle_stub(root: Path, bundle: str, skills: list[str]) -> None:
        (root / bundle / '.claude-plugin').mkdir(parents=True, exist_ok=True)
        (root / bundle / '.claude-plugin' / 'plugin.json').write_text('{"name": "x"}', encoding='utf-8')
        for skill in skills:
            (root / bundle / 'skills' / skill / 'scripts').mkdir(parents=True, exist_ok=True)

    def test_resolves_a_flat_layout(self, tmp_path: Path) -> None:
        self._bundle_stub(tmp_path, 'plan-marshall', ['tools-file-ops'])
        resolved = corpus_lsp._resolve_script_dir(tmp_path, 'plan-marshall', 'tools-file-ops')
        assert resolved == tmp_path / 'plan-marshall' / 'skills' / 'tools-file-ops' / 'scripts'

    def test_resolves_a_versioned_layout(self, tmp_path: Path) -> None:
        versioned = tmp_path / 'plan-marshall' / '0.1.62'
        (versioned / 'skills' / 'tools-file-ops' / 'scripts').mkdir(parents=True)
        resolved = corpus_lsp._resolve_script_dir(tmp_path, 'plan-marshall', 'tools-file-ops')
        assert resolved == versioned / 'skills' / 'tools-file-ops' / 'scripts'

    def test_prefers_the_newest_version(self, tmp_path: Path) -> None:
        for version in ('0.1.9', '0.1.62'):
            (tmp_path / 'plan-marshall' / version / 'skills' / 'tools-file-ops' / 'scripts').mkdir(parents=True)
        resolved = corpus_lsp._resolve_script_dir(tmp_path, 'plan-marshall', 'tools-file-ops')
        assert resolved is not None
        assert resolved.parents[2].name == '0.1.62'

    def test_absent_skill_resolves_to_none(self, tmp_path: Path) -> None:
        self._bundle_stub(tmp_path, 'plan-marshall', [])
        assert corpus_lsp._resolve_script_dir(tmp_path, 'plan-marshall', 'tools-file-ops') is None

    def test_own_bundle_root_is_found_from_a_script_path(self) -> None:
        """Anchoring works from this repository's own real layout."""
        own = corpus_lsp._own_bundle_root(SCRIPT.resolve())
        assert own is not None
        assert own.name == 'pm-plugin-development'
        assert (own / '.claude-plugin' / 'plugin.json').is_file()


CURSOR_LINE = 'See Skill: alpha:target-skill for details.'
"""The corpus fixture's reference line. Character 15 lands inside the notation."""

NOTATION_COLUMN = 15


def _corpus_project(root: Path) -> Path:
    """A project whose ``marketplace/bundles`` holds the synthetic corpus."""
    (root / 'marketplace').mkdir(parents=True, exist_ok=True)
    corpus_root = build_corpus(root)
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    for child in corpus_root.iterdir():
        child.rename(root / 'marketplace' / 'bundles' / child.name)
    (root / '.plan').mkdir(parents=True, exist_ok=True)
    (root / '.plan' / 'marshal.json').write_text(json.dumps(ENABLED), encoding='utf-8')
    return root


class TestDocumentSyncIsWiredToResolution:
    """The synced-buffer branch, driven through the registered LSP methods.

    ``active_capabilities`` advertises ``textDocumentSync: 1``, and
    ``notation_at_position`` prefers ``self.documents`` over reading the file —
    but until these cases existed nothing sent ``didOpen`` / ``didChange`` /
    ``didClose``, so every resolution in the suite took the file-read fallback
    and the branch the capability advertises never ran. Deleting the whole
    ``documents`` lookup left the directory green.

    Each case drives ``rpc.handle`` rather than calling ``corpus.did_open`` and
    friends directly, so the METHOD REGISTRATION is under test too: unregistering
    ``textDocument/didOpen`` would leave a direct-call test green while every
    real client silently fell back to disk.

    The buffer is deliberately given a shape the file does not have — the
    reference line at line 0, where the file carries its heading — so a
    resolution at that position can only come from the buffer. The matched
    negative is asserted in the same cases: before ``didOpen`` and after
    ``didClose``, the same position resolves to nothing.
    """

    @staticmethod
    def _params(uri: str, line: int) -> dict:
        return {'textDocument': {'uri': uri}, 'position': {'line': line, 'character': NOTATION_COLUMN}}

    @staticmethod
    def _caller(root: Path) -> Path:
        return root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'

    def test_initialize_advertises_full_document_sync(self, tmp_path: Path) -> None:
        """The precondition the cases below rest on.

        Asserted separately so a capability withdrawn later is reported as a
        withdrawn capability rather than as a broken resolution.
        """
        capabilities = _capabilities(_handshake(_corpus_project(tmp_path)).stdout)

        assert capabilities['textDocumentSync'] == 1

    def test_an_opened_buffer_answers_instead_of_the_file(self, tmp_path: Path) -> None:
        """A buffer differing from disk is what the resolution reads."""
        root = _corpus_project(tmp_path)
        rpc, _corpus = corpus_lsp.build_server(root, {'enabled': True})
        uri = self._caller(root).as_uri()
        params = self._params(uri, 0)

        before = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'textDocument/definition', 'params': params})
        rpc.handle(
            {
                'jsonrpc': '2.0',
                'method': 'textDocument/didOpen',
                'params': {'textDocument': {'uri': uri, 'text': f'{CURSOR_LINE}\n'}},
            }
        )
        after = rpc.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition', 'params': params})

        assert before is not None and before['result'] is None, (
            'line 0 of the FILE carries no notation; a hit here would mean the '
            'position is resolvable from disk and the buffer proves nothing'
        )
        assert after is not None and after['result'] is not None
        assert after['result']['uri'].endswith('alpha/skills/target-skill/SKILL.md')

    def test_a_changed_buffer_replaces_what_the_open_one_said(self, tmp_path: Path) -> None:
        """``didChange`` must be honoured, not merely accepted.

        A handler that dropped the change would keep answering from the opened
        text, which is indistinguishable from a correct answer unless the two
        texts disagree — so they do.
        """
        root = _corpus_project(tmp_path)
        rpc, _corpus = corpus_lsp.build_server(root, {'enabled': True})
        uri = self._caller(root).as_uri()
        params = self._params(uri, 0)

        rpc.handle(
            {
                'jsonrpc': '2.0',
                'method': 'textDocument/didOpen',
                'params': {'textDocument': {'uri': uri, 'text': f'{CURSOR_LINE}\n'}},
            }
        )
        rpc.handle(
            {
                'jsonrpc': '2.0',
                'method': 'textDocument/didChange',
                'params': {
                    'textDocument': {'uri': uri},
                    'contentChanges': [{'text': 'the operator deleted the reference\n'}],
                },
            }
        )
        after = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'textDocument/definition', 'params': params})

        assert after is not None and after['result'] is None

    def test_closing_a_buffer_resumes_the_file_read_fallback(self, tmp_path: Path) -> None:
        """``didClose`` drops the buffer, and the FILE answers again.

        Both halves are asserted because they fail differently: a handler that
        never dropped the buffer keeps answering at line 0, and a handler that
        dropped the fallback along with the buffer answers nowhere at all.
        """
        root = _corpus_project(tmp_path)
        rpc, _corpus = corpus_lsp.build_server(root, {'enabled': True})
        caller = self._caller(root)
        uri = caller.as_uri()
        file_line = caller.read_text(encoding='utf-8').split('\n').index(CURSOR_LINE)

        rpc.handle(
            {
                'jsonrpc': '2.0',
                'method': 'textDocument/didOpen',
                'params': {'textDocument': {'uri': uri, 'text': f'{CURSOR_LINE}\n'}},
            }
        )
        rpc.handle(
            {
                'jsonrpc': '2.0',
                'method': 'textDocument/didClose',
                'params': {'textDocument': {'uri': uri}},
            }
        )
        at_buffer_line = rpc.handle(
            {'jsonrpc': '2.0', 'id': 1, 'method': 'textDocument/definition', 'params': self._params(uri, 0)}
        )
        at_file_line = rpc.handle(
            {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition', 'params': self._params(uri, file_line)}
        )

        assert file_line != 0, 'the fixture must place the reference away from line 0'
        assert at_buffer_line is not None and at_buffer_line['result'] is None
        assert at_file_line is not None and at_file_line['result'] is not None


class TestCorpusPathResolvesThroughTheRealClient:
    """D6-S05 — ``corpus_path`` driven end to end through the ``serve`` entry point.

    Every other e2e test in this module builds its corpus at the DEFAULT
    location (``marketplace/bundles``), so none of them exercise
    ``resolve_corpus_path`` reading a configured ``corpus_path`` at all — a
    resolver that silently fell back to the default on any custom value would
    still pass every other test here. This class configures a location the
    default would never find, and proves the answer comes from THAT tree.
    """

    @staticmethod
    def _project_with_custom_corpus(root: Path) -> Path:
        corpus_root = build_corpus(root)  # root/bundles/{alpha,beta}
        custom = root / 'my-corpus'
        custom.mkdir(parents=True, exist_ok=True)
        for child in corpus_root.iterdir():
            child.rename(custom / child.name)
        (root / '.plan').mkdir(parents=True, exist_ok=True)
        marshal = {'code_intelligence': {'corpus_language_server': {'enabled': True, 'corpus_path': 'my-corpus'}}}
        (root / '.plan' / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
        return root

    def test_definition_resolves_from_the_configured_path(self, tmp_path: Path) -> None:
        root = self._project_with_custom_corpus(tmp_path)
        skill = root / 'my-corpus' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index(CURSOR_LINE)
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        stdin = (
            _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
            + _framed(
                {
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'textDocument/definition',
                    'params': {
                        'textDocument': {'uri': skill.as_uri()},
                        'position': {'line': line_no, 'character': NOTATION_COLUMN},
                    },
                }
            )
            + _framed({'jsonrpc': '2.0', 'method': 'exit'})
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPT), 'serve', '--project-path', str(root)],
            input=stdin,
            capture_output=True,
            env=env,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr.decode()
        definition_response = next(m for m in _messages(result.stdout) if m.get('id') == 2)
        assert definition_response['result'] is not None, 'the configured corpus_path was not resolved'
        assert definition_response['result']['uri'].endswith('my-corpus/alpha/skills/target-skill/SKILL.md')

    def test_the_same_tree_answers_nothing_once_corpus_path_is_pointed_away(self, tmp_path: Path) -> None:
        """The control: re-pointing ``corpus_path`` off the built tree must lose the answer.

        Same corpus on disk as the positive test above, only ``corpus_path``
        changes. Without this, the positive test could pass for the wrong
        reason — e.g. a resolver that always finds the corpus some other way
        (cwd, a cached root) regardless of what ``corpus_path`` says.
        """
        root = self._project_with_custom_corpus(tmp_path)
        marshal = {
            'code_intelligence': {'corpus_language_server': {'enabled': True, 'corpus_path': 'no/such/directory'}}
        }
        (root / '.plan' / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
        skill = root / 'my-corpus' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index(CURSOR_LINE)
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        stdin = (
            _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
            + _framed(
                {
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'textDocument/definition',
                    'params': {
                        'textDocument': {'uri': skill.as_uri()},
                        'position': {'line': line_no, 'character': NOTATION_COLUMN},
                    },
                }
            )
            + _framed({'jsonrpc': '2.0', 'method': 'exit'})
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPT), 'serve', '--project-path', str(root)],
            input=stdin,
            capture_output=True,
            env=env,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr.decode()
        definition_response = next(m for m in _messages(result.stdout) if m.get('id') == 2)
        assert definition_response['result'] is None


class TestMissingCorpusDegradesWithoutCorruptingTheSession:
    """D6-S05 — enabled, but the configured ``corpus_path`` does not exist.

    ``cmd_preflight``/``cmd_query`` report this as a ``degraded`` payload (see
    ``test_corpus_lsp_optin.py``), but nothing drove the SAME misconfiguration
    through the resident ``serve`` loop: ``CorpusLanguageServer.index`` returns
    ``None`` in this case, and every handler above it must fold that into a
    clean empty answer rather than raising and corrupting the frame stream.
    """

    @staticmethod
    def _project_with_missing_corpus(root: Path) -> Path:
        (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
        (root / '.plan').mkdir(parents=True, exist_ok=True)
        marshal = {'code_intelligence': {'corpus_language_server': {'enabled': True, 'corpus_path': 'no/such/corpus'}}}
        (root / '.plan' / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
        return root

    def test_definition_answers_null_rather_than_erroring(self, tmp_path: Path) -> None:
        root = self._project_with_missing_corpus(tmp_path)
        doc = root / 'doc.md'
        doc.write_text('Run alpha:target-skill here.\n', encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        stdin = (
            _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
            + _framed(
                {
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'textDocument/definition',
                    'params': {
                        'textDocument': {'uri': doc.as_uri()},
                        'position': {'line': 0, 'character': 5},
                    },
                }
            )
            + _framed({'jsonrpc': '2.0', 'method': 'exit'})
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPT), 'serve', '--project-path', str(root)],
            input=stdin,
            capture_output=True,
            env=env,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr.decode()
        assert result.stderr == b'', f'a missing corpus must degrade quietly, not log a defect: {result.stderr!r}'
        definition_response = next(m for m in _messages(result.stdout) if m.get('id') == 2)
        assert 'error' not in definition_response, (
            f'a missing corpus must not surface as a handler error: {definition_response}'
        )
        assert definition_response['result'] is None
