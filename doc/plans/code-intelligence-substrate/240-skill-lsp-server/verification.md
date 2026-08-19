# Verification — 240-skill-lsp-server

**Audited:** `plan.md`, `report-01.md`, `proposal-protocol-surface.md`
**Tree state:** `aff8648` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The plan's six deliverables are present and, with one exception the plan itself sanctions (D3), each
satisfies its literal *Done when*. The shipped surface works when driven for real: `preflight`,
`query` and a full `serve` handshake all answer from the source tree **and** from a synthetic
versioned plugin cache, and an unconfigured project gets `capabilities: {}` with no index built. The
gaps are (a) one demonstrated start-up-class defect the four verification rounds did not reach — an
unhandled exception in a request handler kills the resident server *and* writes a TOON error payload
onto the LSP stdout stream; (b) the `verified` provenance flag over-claiming on 296 of 4 858 verified
reference sites, **and being dropped entirely on the LSP projection**, so the 162 sites the index
itself marks unconfirmed reach an editor as ordinary `Location`s despite two shipped pages promising
they are "never presented as exact"; and (c) a family of stale D3 justifications: the hard gate `230-validate-precision`
**landed on `main` 74 minutes before this plan merged**, and the "≈380 unresolved, ~97 % false
positives" figures shipped into the user, developer, concepts and skill docs are now 61 of 5 081.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0(a) | Re-verify the asserted absence | Done — claim partially refuted, 4 dated searches + 2 fetches | Method and date recorded in `report-01.md` §D0(a); the *conclusion* is reflected in `doc/developer/corpus-language-server-protocol.adoc:56-60`. The external searches themselves cannot be re-run offline | CONFIRMED (method + record); external evidence UNVERIFIABLE |
| D0(b) | Written proposal, not a decision | Done; operator then decided A+D | `proposal-protocol-surface.md` compares A/B/C/D with per-option consequences and E1–E5 evidence; the analysis is authored undecided and the decision is quarantined in a trailing § "Decision (operator, this run)" | CONFIRMED (artifact); the operator escalation itself is UNVERIFIABLE |
| D1 | Measure interactive latency | ≈2.0 s one-shot, ≈1.87 s build, <0.1 ms warm primitives | Re-measured on a quiet machine: 1.80 s build, `definition` 0.51 µs, `hover` 0.94 µs, `references` 20.1 ms first / 4.97 ms 2nd / 2.91 ms 3rd on the 443-edge component (`plan-marshall:manage-logging:manage-logging`, inbound = 443, re-derived as the corpus maximum) | CONFIRMED |
| D2 | definition / references / hover from the index, with provenance | Done; index consumed not edited | `_corpus_index.py:159,171,189`; driven both through `query` **and** through a live `serve` subprocess: definition → `manage-architecture/SKILL.md:0`, hover → description + frontmatter + edge counts, references → 50 sites, 49 verified. Zero files under `tools-marketplace-inventory/` in the landing commit | CONFIRMED (with two provenance defects — precision, and the flag being dropped on the LSP projection; see Correctness review) |
| D3 | Live broken-reference diagnostics | ⛔ NOT DONE — hard gate unmet | Correctly not built (`active_capabilities()` advertises no diagnostic provider, 2 tests pin it). **But the stated gate is no longer unmet**: `230-validate-precision` merged as `3d96e40` at 2026-08-16T08:54Z, this plan as `5edca5a` at 10:08Z | PARTIAL — deliverable correctly deferred, justification stale |
| D4 | Strictly opt-in, documented no-op | Done, verified 3 ways | Reproduced on this real unconfigured repo: `preflight` → `degraded/not_configured/provider_count 0/fallback read_grep`; `serve` handshake with `PYTHONPATH` stripped → `{"capabilities": {}}`, exit 0; `corpus.index is None` | CONFIRMED |
| D5 | Documentation across three trees | Done; cold read passed | `doc/user/corpus-language-server.adoc`, `doc/concepts/code-intelligence.adoc` § "A presentation surface, not a tier", `doc/developer/corpus-language-server-protocol.adoc`; both READMEs updated | CONFIRMED (content), with stale figures — see Report accuracy |

## Per-deliverable detail

### D0(a) — the absence, re-verified

- **Required (plan):** *"the absence is re-verified with its date and method"*.
- **Claimed (report):** four named web queries on 2026-08-15, plus fetches of `markmark` and the
  Claude Code plugin reference; verdict "partially refuted".
- **Found:** the method table is in `report-01.md:57-68`; the substantive conclusion is carried into
  shipped documentation at `doc/developer/corpus-language-server-protocol.adoc:56-60` ("Generic
  Markdown language servers now exist … that is four of the five edge types").
- **Checks run:** I confirmed the conclusion is internally consistent — the corpus has exactly five
  edge types (`script`, `skill`, `import`, `path`, `implements`, per
  `resolve-dependencies.py --dep-types` help), so "off-the-shelf covers ~1 of 5" and "four of the
  five … remain unserved" agree.
- **Verdict:** CONFIRMED as a recorded, dated, method-stated re-check. The external facts themselves
  are not re-derivable in this offline clone — marked UNVERIFIABLE rather than passed.

### D0(b) — a proposal, not a decision

- **Required (plan):** *"a written proposal comparing the options against the actual intended
  consumer exists in the repository"*; and *"a proposal that quietly recommends one option and then
  implements it has not met this deliverable"*.
- **Found:** `proposal-protocol-surface.md` — four options with ✅/❌ consequence lists, E1 (the
  intelligence exists), E2 (nothing consumes it), E3 (latency), E4 (the re-verified absence), E5
  (`lspServers`). § "What the evidence does and does not settle" explicitly names what is left to the
  operator. The decision is in a clearly separated trailing section.
- **Checks run:** read end to end; the analysis body contains no recommendation. § "What this
  analysis, on its own, settles" (line 281) states the fork is left open.
- **Verdict:** CONFIRMED on the artifact. The claim that a live operator was asked, and what they
  answered, exists only as quoted chat inside the run's own prose — UNVERIFIABLE. Note the plan
  premised D0(b) on *"this run has no operator to ask"*; the run's escalation is permitted by the
  lane contract and is disclosed in § Contract check, so this is a disclosed deviation, not a breach.

### D1 — the latency gate

- **Required (plan):** *"the existing verbs are timed and the figures recorded"*, with a re-scope
  trigger if too slow.
- **Claimed (report):** ≈2.0 s one-shot CLI; ≈1.87 s `build_dependency_index`; <0.1 ms warm
  forward/reverse; ≈1.5 ms transitive depth 10; ≈4.0 ms cycle detection. Plus, from verification,
  `references` ≈18–20 ms first call / ≈3 ms repeat at 443 inbound edges.
- **Found / checks run:** re-derived on this clone against the real corpus —

  | Path | Report | Re-measured here (quiet machine, best-of-5 where applicable) |
  |---|---|---|
  | `CorpusIndex` construction | ≈1.87 s | **1.80 s** |
  | `definition`, warm | µs | **0.51 µs** (2 000 iterations) |
  | `hover`, warm | µs | **0.94 µs** (500 iterations) |
  | `references`, 443-edge component, first call | ≈18–20 ms | **20.1 ms** |
  | `references`, same, 2nd / 3rd call | ≈3 ms | **4.97 ms / 2.91 ms** |

- **Verdict:** CONFIRMED, and the report's own figures reproduce closely. ⚠ **An earlier pass of this
  audit recorded 2.50 s build / 2.61 s one-shot / 29.4 ms first-call and attributed the ~30 % excess
  to "this machine". That attribution was wrong**: the excess is contention from the concurrent audit
  agents working in this shared tree, and a re-take under quiet conditions lands on the report's
  numbers. The docs' *"~20 ms at 443 inbound edges"* is exact, and the 443-edge component is
  `plan-marshall:manage-logging:manage-logging` (re-derived as the corpus's most-referenced
  component). The docs' *"answers in under 5 ms thereafter"* holds with little headroom on the second
  call (4.97 ms) and comfortably from the third (2.91 ms). Recorded, not filed as a gap.

### D2 — the surface

- **Required (plan):** *"each of the three answers resolves from the existing index with
  provenance"*, and *"the index is consumed, NOT edited"*.
- **Found:** `_corpus_index.py:159` (`definition`), `:189` (`references`), `:171` (`hover`);
  `corpus_lsp.py:309/321/330` wire them to `textDocument/definition|references|hover`;
  `_corpus_lsp_protocol.py:92-105` advertises the three providers.
- **Checks run:**
  - Live `query --kind definition --notation plan-marshall:manage-architecture` →
    `manage-architecture/SKILL.md`, line 0.
  - Live `--kind hover` → description, frontmatter (`mode`, `scope`, …), `inbound_edges: 50`,
    `outbound_edges: 93`.
  - Live `--kind references` → 50 sites, `verified_count: 49`, each with path + line + type, plus the
    `completeness_note`.
  - "Consumed, not edited": `git show 5edca5a --name-status` lists no file under
    `tools-marketplace-inventory/`. **CONFIRMED.**
  - I reproduced the sub-document design finding on a synthetic corpus: the index cites
    `beta:caller line:5`, `SKILL.md` line 5 is blank, and `resolve_reference_site` correctly relocates
    to `workflow/step.md` (0-based line 4) with `verified=True`.
- **Verdict:** CONFIRMED as specified. See Correctness review for a precision defect in the
  `verified` flag that does not affect the *Done when*.

### D3 — live diagnostics

- **Required (plan):** *"diagnostics stream from the validator and a known false-positive class
  produces none"*, hard-gated on the validator-precision plan.
- **Claimed (report):** not done, correctly; *"`230-validate-precision.md` is still an unexecuted
  plan file"*; 381 unresolved of 5 312, 371 (97.4 %) demonstrable false positives.
- **Found:** no diagnostic provider — `_corpus_lsp_protocol.py:100-105`; pinned by
  `test_corpus_lsp_protocol.py:90` and `test_corpus_lsp_optin.py:157`. Two tests, as claimed.
- **Checks run:**
  - `doc/plans/code-intelligence-substrate/230-validate-precision/` now holds `plan.md` **and**
    `report-01.md`; `git log` dates its landing commit `3d96e40` at **2026-08-16T08:54:13Z**, and this
    plan's `5edca5a` at **10:08:21Z**. The hard gate was met on `main` before this plan merged.
  - Re-derived the validator on this tree, twice — once with the working-tree scripts and once with
    pristine `HEAD` copies of `_dep_detection.py` / `_dep_index.py` / `resolve-dependencies.py`
    (because concurrent audit agents were mutating those files): **308 components, 5 081
    dependencies, 61 unresolved**. Not 380/5 301 and not 381/5 312.
- **Verdict:** PARTIAL. The deliverable is correctly *unbuilt* and correctly *advertised as absent*;
  every artifact that explains **why** now states a superseded reason and a wrong magnitude.

### D4 — opt-in, verified rather than asserted

- **Required (plan):** *"an unconfigured project's behaviour is unchanged, verified rather than
  asserted"*.
- **Found:** switch at `corpus_lsp.py:167-195` (`read_corpus_config`), fail-closed on every failure
  mode; `CorpusLanguageServer.index` (`corpus_lsp.py:244-251`) returns `None` unless enabled;
  `LspServer.capabilities()` (`_corpus_lsp_protocol.py:119-120`) returns `{}` when disabled.
- **Checks run (all on this real, unconfigured repository — `.plan/marshal.json` has no
  `code_intelligence` key):**
  - `python3 .plan/execute-script.py pm-plugin-development:tools-corpus-language-server:corpus_lsp preflight`
    → `status: degraded / state: not_configured / provider_count: 0 / fallback: read_grep`.
  - Real handshake: `serve --project-path /home/user/plan-marshall`, spawned as a subprocess with
    `PYTHONPATH` **removed** → `Content-Length: 59\r\n\r\n{"jsonrpc":"2.0","id":1,"result":{"capabilities":{}}}`,
    exit 0, empty stderr.
  - Same handshake driven from a **synthetic versioned plugin cache**
    (`{bundle}/{0.1.9,0.1.62}/skills/…`, both versions present) → `{}` for this repo and the three
    providers for an enabled temp project. Round 4's crash class does not reproduce, and the numeric
    version preference is exercised.
  - Fail-closed matrix pinned by `test_corpus_lsp_optin.py:48-77` (7 cases incl. `"yes"` → disabled).
- **Verdict:** CONFIRMED — verified, not asserted, and reproduced independently here.

### D5 — documentation across three trees

- **Required (plan):** user page must state plainly that an unconfigured project loses nothing;
  concepts page places it in the tier model; developer page records the protocol decision.
- **Found:** `doc/user/corpus-language-server.adoc` (opening IMPORTANT block: *"You do not need this
  page … If you never read past this box, you have lost nothing."*);
  `doc/concepts/code-intelligence.adoc` § "A presentation surface, not a tier" (*"It adds no tier"*,
  *"an accelerator, never a prerequisite"*); `doc/developer/corpus-language-server-protocol.adoc`
  (residency measurement, options rejected, § "The declaration is documented, not shipped").
  Indexed in `doc/user/README.adoc:23` and `doc/developer/README.adoc:18`. All xref targets resolve.
- **Checks run:** read all three cold; the user page's "you lose nothing" framing is the first thing
  on the page and the cost admonition precedes both config blocks (report finding 58). Verified the
  documented canonical invocation actually runs through the generated executor.
- **Verdict:** CONFIRMED on structure and framing; the D3 paragraph on each page carries stale
  numbers (see Report accuracy / Gaps).

## Correctness review

Read in full: `corpus_lsp.py` (537 lines), `_corpus_index.py` (286), `_corpus_lsp_protocol.py` (167),
plus the four test files and the `plugin_json_gen.py` / `_config_core.py` / `_analyze_sys_path_bootstrap.py`
edits. Defects found:

1. **No exception boundary in the JSON-RPC dispatch loop — a single bad request kills the resident
   server and corrupts the protocol stream.** `LspServer.handle` (`_corpus_lsp_protocol.py:143`)
   calls `result = handler(params)` with no `try`, and `LspServer.serve` (`:148-158`) has none
   either; `cmd_serve` runs under `@safe_main`, which by contract renders an uncaught exception as
   **TOON on stdout** (`file_ops.py:1664-1676`) — the same stdout the LSP frames travel on.
   Reproduced end to end through the documented client-facing entry point: a
   `textDocument/definition` whose `uri` is `file:///tmp/a%00b.md` makes `Path.read_text` raise
   `ValueError: embedded null byte` (not caught — `corpus_lsp.py:299` catches only `OSError` /
   `UnicodeDecodeError`); the server exits **1** and stdout ends with
   `…}}}status: error\nerror: internal_error\nmessage: embedded null byte\n`. The third request in
   the same session was never answered. Consequence: the editor's server dies mid-session, and a
   client still parsing frames is fed non-LSP bytes. Residency is this surface's entire
   justification, so surviving a bad request is load-bearing. → **G1**

2. **`verified: true` can name the wrong file.** `resolve_reference_site`
   (`_corpus_index.py:213-239`) tries the owner's own file first, then its sub-documents, and returns
   the **first** candidate whose line at the cited number contains any `expected_tokens` entry — with
   no tie-break and no ambiguity signal. Reproduced on a synthetic corpus: a decoy line
   `prose about target_script, unrelated` at line 5 of `beta/skills/caller/SKILL.md` beats the true
   citation at line 5 of `workflow/step.md`, and the answer is reported `verified=True`. Scanned the
   real corpus with the resolver's own candidate order and token test: of **4 858** resolved sites,
   **296 (6.1 %)** have more than one candidate file matching at that line, so at most one of each
   pair can be right; and **1 331 (27 %)** win on the tail segment alone rather than the full
   notation. `SKILL.md:120` and the user page call `verified` *"an exact location"*. → **G2**

3. **Neither the index nor its caches are ever invalidated.** `CorpusIndex` is built once
   (`corpus_lsp.py:244-251`) and `_line_cache` / `_candidate_cache` (`_corpus_index.py:150-151`) grow
   monotonically; `did_open` / `did_change` / `did_close` touch only `self.documents`. Nothing resets
   any of the three. In a resident server — which is the whole design — every answer after the first
   edit is computed against a stale snapshot, and the docs' claim that *"every reference site is
   re-read before it is reported"* (`SKILL.md:108`, user page line 182) holds only for the first read
   of each file in the process. Option A's own cost list in the proposal names "incremental re-index
   on change"; it was not built and the limitation is documented nowhere. → **G3**

4. **`initialize.rootUri` / `rootPath` are ignored.** The `initialize` handler
   (`corpus_lsp.py:380`) returns capabilities and discards the params; the project is resolved only
   from `--project-path`, default `.` (`corpus_lsp.py:494`). A client that spawns the server without
   that flag — the ordinary case for Form 2 editor configs — silently resolves from its own cwd, and
   the docs' own words for that outcome are "empty capabilities … indistinguishable from a deliberate
   opt-out". The standard field that would fix it is available and unread. → **G4**

Checked and found sound: the fail-closed config ladder (every branch of `read_corpus_config` returns
`{'enabled': False}`); `notation_at`'s lookbehind/lookahead (a cursor inside `https://…` yields
`None`, verified); the negative-`Content-Length` guard (`_corpus_lsp_protocol.py:60-61`, mutation-
proven live below); the flat/versioned bootstrap and its numeric version key (driven from a real
two-version cache); `no_op_capabilities()` being genuinely empty rather than a subset.

## Test adequacy

78 tests in `test/pm-plugin-development/tools-corpus-language-server/` — all green
(`uv run python -m pytest … -o addopts=""`, 0.93 s). Coverage by deliverable: D2 →
`test_corpus_index.py`; D3 → the two no-diagnostics assertions; D4 → `test_corpus_lsp_optin.py` (incl.
the three full-chain tests) and `test_corpus_lsp_serve.py`; the protocol → `test_corpus_lsp_protocol.py`;
the generator round-trip → `test/marketplace/targets/claude/test_plugin_json_gen.py` (8 tests, green).

**Mutation results** (each mutation applied to the working tree, the single test file run, then the
file restored byte-for-byte from a snapshot in `/tmp/verify-240-mutsweep/`; `md5sum -c` clean and
`git status --porcelain` shows none of these files afterwards):

| # | Mutation | Result |
|---|---|---|
| M1 | delete `if parsed < 0: return None` in `read_message` | **RED** — `test_negative_content_length_yields_none` fails. Guard is real |
| M2 | delete the cache **read** in `CorpusIndex._candidate_files` (walk on every edge) | ⛔ **GREEN — all 78 pass.** The two tests in `TestCandidateFilesAreCached` are vacuous: the cache is still *written*, so `test_repeat_calls_reuse_the_walk` sees a populated dict and `test_walk_runs_once_per_owner_not_once_per_edge`'s `len(walked) < len(calls)` holds regardless. Finding #4's regression — the walk that never warms up — is unguarded |
| M3 | `_version_key` → lexical (`tuple(ord(c) …)`) | **RED** — `test_prefers_the_newest_version` fails (`0.1.9` selected). Finding #47's fix is guarded |
| M4 | remove `'lspServers'` from `PASSTHROUGH_FIELDS` | **RED** — `test_lsp_servers_survive_regeneration` fails. Finding #22's fix is guarded |

**Further test gaps found by reading:**

- `test_negative_content_length_does_not_consume_the_stream` never reads a second frame, so it does
  not test its own docstring ("the next frame must still be readable"). Confirmed by M1: with the
  guard deleted, that test still passes while the stream *is* consumed. → **G6**
- `cmd_query` is exercised in exactly one test, on the **disabled** path
  (`test_corpus_lsp_optin.py:135`). The enabled `query` path — which the run report designates the
  surface's only reachable consumer — and the enabled `preflight` path (`state: ready`, `stats()`)
  have no test at all. → **G7**
- `corpus_path` (a documented config field in `SKILL.md`, the user page and `data-model.md`) is never
  set in any test, and the `resolve_corpus_path` → `None` branch that yields
  `not_configured / reason: configured corpus path does not exist` is untested. → **G8**
- `did_change` and `did_close` are never invoked; no test ever populates `self.documents`, so the
  synced-buffer half of `notation_at_position` is untested (the file-read fallback is covered). → **G9**

## Report accuracy

`report-01.md` is unusually candid — it self-declares the partially-met Goal, the unmet D-half, the
missing fifth verification round, and its own stale-count problem. Claims I re-derived and confirmed:
the 12 `*.py` files in the diff (counted from `git show --name-status`: 6 production + 6 test = 12);
"zero files under `tools-marketplace-inventory/`"; "two tests assert" the absent diagnostic provider;
"17 round-1 rows" (rows 4–20 = 17); the findings table has no numbering gaps (1–58, with 21/21b
placed last); `pm-plugin-development/README.md`'s "(12)" context-loaded count (4 + 12 + 1 = 17 skill
directories, verified). Claims that are false or stale **of the tree now**:

| Claim (quoted) | Correct value |
|---|---|
| §D3: *"`230-validate-precision.md` is still an unexecuted plan file"* | It executed: `doc/plans/…/230-validate-precision/report-01.md` exists, landed `3d96e40` **2026-08-16T08:54:13Z** — 74 minutes before this plan's `5edca5a` (10:08:21Z) |
| §D3: *"381 unresolved edges of 5 312"* and the 371/97.4 % table | **61 unresolved of 5 081** across 308 components, re-derived twice (working tree, and pristine `HEAD` copies of the validator). A large share are still non-references (`lint:js:fix`, `HH:mm:ss`, `project:core:compile`), but the magnitude and the percentage no longer hold |
| §D2: *"the real citation is `step.md` line 4"* | Mixed units in one sentence: the index cites `line:5` (1-based) and the citation is `step.md` line 5 (1-based) = index 4 (0-based). Reproduced |
| §Build gate: *"20 119 passed, 14 skipped"* | The landing commit message states **20 127 passed**. The report itself warns the count goes stale; it did, within its own PR |
| Residue: *"`uv.lock` is stale … lock records `>=0.16.1`"* | **Closed.** `pyproject.toml:28` and `uv.lock:327` both say `>=0.16.2`, and `uv.lock:404-405` pins ruff 0.16.2 |

`proposal-protocol-surface.md`: E1's "306 components / 5 301 forward edges" and § D3's "380
unresolved / 370 (97.4 %)" are likewise superseded (308 / 5 081 / 61); and three markdown links point
at plan **files** that are now plan **directories** — `../220-resolver-configuration.md` (line 239)
and `../230-validate-precision.md` (lines 293, 339) do not exist. `../135-remove-lsp-query-facade/rationale.md`
(line 46) does exist.

Not checkable here, recorded as UNVERIFIABLE rather than passed: the four D0(a) web searches; the
operator conversation quoted under D0(b); the branch name `claude/skill-lsp-server-2oqo3r`, the
per-commit trailers and the wall-clock span (the PR was squash-merged, so branch history is not in
this clone); § Reviewer participation (no network calls were made).

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D3 unbuilt, hard-gated on `230-validate-precision` | **Open, but the gate is discharged** | No diagnostic provider in `active_capabilities()`; `230` landed `3d96e40` 74 min before this plan. Validator now reports 61 unresolved, not 380 |
| The surface has no automatic consumer | **Open** | Tree-wide grep: `lspServers` appears in no `.claude-plugin/plugin.json`; the only 14 files naming this skill are its own source, tests, docs and two config docs. Nothing dispatches it |
| Extension-collision behaviour unverified against a running client | **Open** | Nothing in the tree observes or tests it; it remains a claim sourced from the run's web research |
| Finding 19 — `CLAUDE.md` component counts drifted | **Open** | `CLAUDE.md` says "157 registered components (153 skills, 2 agents, 2 commands)"; re-derived now: **156 skills, 2 agents, 2 commands = 160** |
| Finding 20 — no `manage-config` verb writes `code_intelligence` | **Open** | `code_intelligence` appears in `manage-config` only in `standards/data-model.md` and `scripts/_config_core.py` (canonical key order); no verb writes it. The user page still instructs hand-editing |
| `uv.lock` stale vs `pyproject.toml` | **Closed / moot** | Both now `ruff>=0.16.2`; `uv.lock` pins 0.16.2 |

## Out-of-scope and collateral

Every "Out of scope" clause holds:

- *Building cross-file skill intelligence* — not rebuilt. No file under `tools-marketplace-inventory/`
  is in the landing commit; `_corpus_index.py` imports `build_dependency_index` and reads only.
- *Rebuilding agent-to-code-language-server bridges* — nothing of the sort exists in the diff.
- *Becoming a prerequisite* — verified by exhaustive grep: no workflow, persona, phase skill, command
  or `CLAUDE.md` rule reads this surface. Default is off; disabled means `{}` capabilities and no
  index build.
- *Deciding the protocol* — the proposal's analysis is decision-free; the decision is attributed to
  the operator and quarantined in a trailing section.

Collateral changes, all declared in the report and all defensible: `_config_core.py` (new
`code_intelligence` slot in the canonical key order, + 2 tests), `data-model.md` (new section, plus a
stale-ordering correction), `run-config-standard.md` (a back-reference), `plugin_json_gen.py`
(`lspServers` added to `PASSTHROUGH_FIELDS` + fixture and 2 tests that fix a previously vacuous
passthrough test), `_analyze_sys_path_bootstrap.py` + `rule-provenance.md` (allowlist entry and
category rename). One undeclared inconsistency: `plugin_json_gen.py`'s module docstring still
enumerates the passthrough fields **without** `lspServers` (lines 6-9). → **G14**

## Method and coverage

- Read `plan.md`, `report-01.md`, `proposal-protocol-surface.md`, the epic README, all three shipped
  `.adoc` pages, `SKILL.md`, all three production scripts, all four test files, and every collateral
  diff hunk in `git show 5edca5a`.
- Drove the shipped artifact for real, not only its tests: `preflight` (via the generated executor
  and directly), `query` in all three kinds against the real 308-component corpus, and three
  `serve` handshakes as an LSP client spawns it (`PYTHONPATH` stripped) — source tree unconfigured,
  temp project enabled, and a synthetic **versioned** plugin cache with two versions present.
- Re-derived every number I state: component/edge/unresolved counts (twice, the second time with
  pristine `HEAD` copies of the validator, because concurrent audit agents were mutating
  `_dep_detection.py` / `_dep_index.py` in this shared tree); latencies; skill/agent/command counts;
  the ambiguity scan over 4 858 reference sites.
- Mutation-tested four guards; all mutations restored from byte snapshots in
  `/tmp/verify-240-mutsweep/` and confirmed with `md5sum -c` and `git status --porcelain`. No
  `git checkout`/`restore`/`stash` was used and no file I did not mutate was touched.
- **Not checked:** the full `./pw verify` suite (out of scope per the audit brief — I ran the six
  test files this plan owns or touched); plugin-doctor (needs the executor-backed script tree and was
  not re-run); anything requiring network — the D0(a) searches, the PR #1256 review bodies, and the
  "first registered wins" LSP client behaviour. Each is marked UNVERIFIABLE above rather than assumed.
