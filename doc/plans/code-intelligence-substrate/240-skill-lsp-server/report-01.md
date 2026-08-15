# Run report — 240-skill-lsp-server (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/skill-lsp-server-2oqo3r`    **PR:** _(opened after this report is committed — see Contract check)_    **Outcome:** completed

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` — the first action of the run |
| `plan-marshall:ref-code-quality` | Bundle path (always-load) |
| `pm-plugin-development:plugin-script-architecture` | Bundle path (always-load), plus `standards/test-scaffolding.md` |

Read as working references rather than loaded whole, because the surface reached them directly:
`plan-marshall:lsp-client` (SKILL.md and all three scripts — the sibling contract this surface reuses),
`pm-plugin-development:tools-marketplace-inventory` (the index consumed), `manage-config`
`data-model.md` and `_config_core.py`, and the `plugin-doctor` `sys-path-bootstrap` analyzer.

Not loaded, because the run's surface did not reach them: `persona-security-expert` (no
security-relevant surface), `pm-documents:ref-asciidoc` (the three `.adoc` edits follow the
conventions of the files they sit in), `ref-workflow-architecture` (no workflow-doc or dispatch
change). Recorded rather than claimed.

## Deliverables

| # | Deliverable | Outcome | Commits |
|---|---|---|---|
| D0(a) | GATE — re-verify the asserted absence | **Done — claim partially REFUTED** | `c0d0209` |
| D0(b) | GATE — protocol proposal, not a decision | **Done; operator then decided** | `c0d0209`, `24cb133` |
| D1 | GATE — measure interactive latency | **Done — gate reframed, not tripped** | `c0d0209` |
| D2 | The surface | Done | `ebde4ea`, `25f42ef` |
| D3 | Live broken-reference diagnostics | ⛔ **NOT DONE — hard gate unmet** | — |
| D4 | Strictly opt-in, documented no-op | Done | `ebde4ea`, `25f42ef` |
| D5 | Documentation across three trees | Done | `eb5dc05`, `25f42ef` |

### D0(a) — the absence, re-verified

⛔ The plan named this its highest-risk claim, because an unverified absence sends the plan to build
something that exists.

**Method — stated here because the proposal delegates it to this report.** Four web searches on
**2026-08-15**, followed by two source fetches:

| # | Query |
|---|---|
| 1 | `language server for Claude Code SKILL.md agent skills go-to-definition` |
| 2 | `"agent skills" OR "SKILL.md" language server protocol LSP validator VS Code extension 2026` |
| 3 | `agent skills validator SKILL.md frontmatter lint cross-file references find-references hover` |
| 4 | `"language server" markdown skill corpus "go to definition" skill notation plugin marketplace LSP server agent skills` |

Fetched and read: the `markmark` repository (to establish its actual feature set rather than infer it
from a search snippet) and the Claude Code plugins reference (to establish the `lspServers` schema).

**Verdict: partially refuted, and the refutation changed the plan.**

- *Holds:* nothing in the ecosystem understands a **skill corpus**. The agent-skills tooling that
  exists is file-local spec-conformance linting (`agent-skills-lint`, `skillcheck`, `hermes skills
  lint`) against the agentskills.io specification. One such project states the gap itself: the
  specification *"only validates frontmatter basics but has no concept of verifying related_skills
  against the actual skill index."*
- *No longer true as stated:* generic **Markdown** language servers now exist. `markmark` provides
  go-to-definition, find-references, link completion and link validation; the `mdbase` server adds
  hover and frontmatter handling. ⚠ Neither understands `bundle:skill:script` notation, `skills:` /
  `implements:` frontmatter, or the Python-import edges — about **one of five edge types** covered.
  The absence claim survives where it matters and should simply stop being phrased as "nothing
  exists."
- *Confirmed:* the mature "language server for agents" projects (`lsp-skill`/LSAP, `lsp-validation`,
  `setup-lsp`, `claude-code-lsps`, `claude-languages`) all run the **opposite** direction, bridging
  per-language code servers to agents with no documentation-corpus support. ⛔ Not rebuilt.

⭐ **One finding was not available at the plan's research date and reframed D0(b) entirely:** Claude
Code's plugin schema accepts an `lspServers` declaration, starts declared servers automatically when
the plugin is enabled, and routes definition/reference lookups through them. An editor protocol is
therefore **also** an agent protocol on this platform, which is precisely the premise the plan's fork
assumed was false.

### D0(b) — a proposal, and then an operator decision

`proposal-protocol-surface.md` compares four options (A: a real LSP server; B: a tool-calling/MCP
surface; C: extending the existing `lsp-client` seam; D: create a consumer first) with per-option
consequences and the consumer evidence bearing on each.

⛔ **The run did not decide.** The analysis is authored undecided and left the fork open.

**This run had a reachable operator** — it executed in an interactive session, which the lane contract
permits to escalate a plan's re-scope rather than take the autonomous fallback. The fork was put to the
operator, who asked for Option C to be elaborated first and then **decided A + D**. Both the question
and the answer are recorded here because a conversation event is not a committed artifact:

> **Operator:** "i tend to a + d. but elaborate on c" → then, after the elaboration: "do „b) also
> implement D2/D4 under an A+D decision this run"

⭐ **E5 is what makes A + D coherent rather than contradictory.** D exists to prevent a third
zero-adoption surface after the `130`→`135` build-and-remove cycle; on Claude Code a plugin-declared
server is consumed by the agent automatically, so *declaring* it creates the first consumer instead of
waiting for one. The two halves partially collapse into one step here.

The deepened Option C analysis (`24cb133`) is a finding in its own right: C's degradation contract is
genuinely reusable, but its **store** is a direction error — a machine-local binding for a
*third-party-installed* binary, keyed by *language*, on a switch the standard already documents as
overloaded — and its hosting model is explicitly short-lived-subprocess-per-call, which is the same
2 s shape D1 rules out. C was therefore resolved *into* A: the vocabulary was copied, the store was not.

### D1 — the latency gate, measured

| Path | Measured |
|---|---|
| One-shot CLI query (`deps` / `rdeps` / `validate`), end to end | ≈ 2.0 s |
| `build_dependency_index` alone, in-process | ≈ 1.87 s |
| `get_forward_deps` / `get_reverse_deps`, warm | < 0.1 ms |
| `resolve_transitive_deps` depth 10, warm | ≈ 1.5 ms |
| `detect_circular_deps` (whole graph), warm | ≈ 4.0 ms |

3 runs each, median reported, measured against `marketplace/bundles/` on this clone.

⭐ **The gate's warning fired, but not in the shape the plan anticipated.** D1 was written as *if the
verbs are too slow, an incremental or cached index becomes a deliverable*. The measurement says
something narrower and more useful: the index does not need to be incremental or cached — **it needs
to be resident.** Essentially the entire cost is construction, paid per process. That eliminates the
one-shot shape for *any* protocol and is what actually decided the surface's form.

**A second latency finding arrived from verification, not from this gate**, and is recorded under
Findings: `references()` was not in fact a warm-index lookup.

### D2 — the surface

`definition`, `references` and `hover` answer from the existing index. ⛔ **The index is consumed, not
edited** — confirmed by the verification pass: zero files under `tools-marketplace-inventory/` appear
in `git diff --name-only origin/main...HEAD`.

⭐ **One design finding shaped the implementation, and it was found by running the thing rather than by
reading it.** The index attributes an edge cited in a skill's *sub-document* to the owning skill, whose
own file is `SKILL.md`, while the recorded line number belongs to the sub-document. Following that
pairing naively sends an editor to that line number in the wrong file. Probed on a synthetic corpus:
the index cites `beta:caller` `line:5`, where `SKILL.md` line 5 is **blank** and the real citation is
`step.md` line 4. Every reference site is therefore re-read before it is reported, and carries a
`verified` flag; an unconfirmed site is shown but never presented as exact.

A **real-corpus** run then exposed a defect in that verification itself: matching on the notation alone
can never confirm a `path` or `import` edge, whose citing line carries a relative path or a bare module
name rather than a notation. Verified count on a 49-edge component went from a handful to **48/49**
once the check accepted the target's discriminating final segment as well.

### D3 — not done, and correctly so

⛔ **The hard gate is unmet.** `230-validate-precision.md` is still an unexecuted plan file. No
diagnostic provider is advertised, asserted by two tests.

Re-derived on this branch as evidence for the gate — 381 unresolved edges of 5 312:

| Class | Count | Share |
|---|---:|---:|
| Documentation placeholder — not a reference at all (`groupId:artifactId:scope`, `bundle:skill:script`) | 56 | 14.7 % |
| Foreign namespace — build command, Maven GAV, lint target (`default:verify:compile`, `lint:js:fix`) | 116 | 30.4 % |
| Real component; third segment is a verb or module, not a script | 199 | 52.2 % |
| Residue — plausibly a genuine broken reference | 10 | 2.6 % |

**371 of 381 (97.4 %) are demonstrable false positives.** Streaming that into an editor would ship
roughly 370 confident-wrong diagnostics at this epic's most visible surface.

⚠ These counts move as the corpus grows — this branch's own prose raised the total from 380 to 381 —
so user-facing docs state them as ranges, and exact figures appear only here with their measurement
point named.

### D4 — opt-in, verified rather than asserted

⭐ **Opt-in could not live in the manifest**, because a plugin-declared LSP server starts
automatically when its plugin is enabled. The switch is
`code_intelligence.corpus_language_server.enabled` in the project's version-controlled
`.plan/marshal.json`; every unreadable or ambiguous configuration fails closed to disabled.

Verified on unconfigured projects, three ways:

1. `preflight` run against **this real, unconfigured repository** → `status: degraded`,
   `state: not_configured`, `provider_count: 0`, `fallback: read_grep`.
2. A real LSP handshake against `serve` on this repository, spawned as a client does (no
   `PYTHONPATH`) → `capabilities: {}`.
3. Tests driving the whole chain — unconfigured tree → `find_project_root` → `read_corpus_config` →
   `build_server` → `initialize` → `{}` capabilities, and `index is None` (so the ~1.9 s build is not
   paid either).

### D5 — three trees

User `doc/user/corpus-language-server.adoc`, concepts `doc/concepts/code-intelligence.adoc`
§ "A presentation surface, not a tier", developer
`doc/developer/corpus-language-server-protocol.adoc` (which records the protocol decision and its
rationale, per the deliverable). All three indexed.

**The user page's cold read passed** — see Findings.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (7 files: 3 scripts, 4 test
files, plus `_config_core.py` and `_analyze_sys_path_bootstrap.py`), so the full gate was owed and run.

`./pw verify` — **SUCCESS**: `ruff` all checks passed, `mypy` clean over 408 production and 754 test
sources, SPDX-header check passed, plugin-doctor `issues[0]`, **20 117 passed, 14 skipped**.

Run three times in total. The two earlier runs each failed and were fixed, both in the
`test-compile` step that neither `quality-gate` nor `module-tests` performs — the exact class the lane
contract warns about: 5 unused `type: ignore` comments, then one `no-any-return`.

## Findings

Per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Own real-corpus run | `path` and `import` edges could never verify — their citing line carries a path or module name, not the notation, so the `verified` flag was noise for two of five edge types | **Fixed** — `expected_tokens` accepts the target's discriminating final segment; 48/49 verified on the probe component |
| 2 | Own sweep of #1 | The fix falsified an existing test's assertion (`test_verified_reference_points_at_the_citing_line` required the notation literally) | **Fixed** — assertion re-expressed against `expected_tokens` |
| 3 | Own sweep of #1 | Two `SKILL.md` statements and one user-page sentence restated "the line contains the notation" | **Fixed** — all three restated, with the reason the notation alone is insufficient |
| 4 | Sub-agent | `references()` was **not** a warm-index lookup: the per-owner directory walk ran once per reverse edge, uncached — ~125 ms for a 443-edge component, and **unchanged on repeat**, so residency bought it nothing | **Fixed** — walk cached per owner; repeat 125 ms → 2.6 ms |
| 5 | Sub-agent | Four sites claimed "a warm index answers **every verb** in under 5 ms" — false for `references` | **Fixed at all four** (`SKILL.md`, `_corpus_index.py`, `corpus_lsp.py`, concepts page) — restated with the ~20 ms first-call cost named, and a row added to the developer table |
| 6 | Sub-agent | ⛔ `serve` invoked as `SKILL.md` canonically documented it **cannot work**: the executor dispatches with `capture_output=True` (buffers until exit) and `text=True` (rewrites `\r\n\r\n` as `\n\n`) | **Fixed** — `serve` removed from Canonical invocations, § "How `serve` is launched" added, and a subprocess test now asserts CRLF framing survives a real pipe |
| 7 | Sub-agent | ⛔ No `lspServers` declaration existed, so the surface had **zero consumers** — the exact condition D's half of the decision exists to prevent, with three passages describing a manifest state that did not exist | **Fixed** — bundle declares the server; script bootstraps its own `sys.path` (allowlisted as a pre-executor entry point); handshake verified with no `PYTHONPATH` |
| 8 | Sub-agent | The RPC-level no-op tests built an unconfigured tree and then discarded it, stipulating `{'enabled': False}` — the composition the plan asks to be *verified* was untested | **Fixed** — three full-chain tests added |
| 9 | Sub-agent | `report-01.md` did not exist; the proposal's two links to it were dangling and D0(a)'s method was unverifiable | **Fixed** — this report |
| 10 | Sub-agent | The proposal's opening said the run "implemented no protocol", contradicted by the appended Decision section | **Fixed** — opening reconciled |
| 11 | Sub-agent | § "What this run did NOT do" claimed D2/D4/D5 still awaited the decision | **Fixed** — restated as the analysis-only position, with the separation made explicit |
| 12 | Sub-agent | The block comment above `CANONICAL_TOP_LEVEL_KEY_ORDER` still said `credentials_config` sits "between `build` and `project`" | **Fixed** |
| 13 | Sub-agent | The same stale ordering claim in `data-model.md` § credentials_config | **Fixed** |
| 14 | Sub-agent | `data-model.md` § "Complete Structure" omitted the new `code_intelligence` section | **Fixed** |
| 15 | Sub-agent | No test asserted `code_intelligence`'s presence or placement in the canonical order | **Fixed** — two tests added |
| 16 | Sub-agent | User page hard-coded "380 unresolved references"; this branch's own prose moved it to 381 | **Fixed** — restated as a range; exact figures live here with their measurement point |
| 17 | Sub-agent | Developer page said "306 components"; measured 308 on this branch | **Fixed** — restated as a range |
| 18 | Sub-agent | The `language_servers` docs gained no back-reference to the new sibling config surface (cross-referencing was one-directional) | **Fixed** — § "A sibling surface lives elsewhere, deliberately" added |
| 19 | Sub-agent | `CLAUDE.md` component counts ("157 registered components (153 skills…)") are drifted; re-derived from git, `origin/main` carries **155** `SKILL.md` files and this branch **156** | **DEFERRED, not fixed** — the drift is **pre-existing and larger than the doc suggests**: against 156 skills + 2 agents + 2 commands the true total is **160**, not the 157 claimed and correcting it requires settling what "components" counts, which is a separate question this plan does not own. Recorded so it is visible rather than silently inherited |
| 20 | Sub-agent (noted, not a defect) | No `manage-config` verb writes the new section; the user page instructs hand-editing, unlike every other marshal.json section | **Accepted as-is** — D4 requires the path be *documented*, not scripted. Recorded as an asymmetry for a future plan |
| 21 | CI | _(none at time of writing — see Contract check)_ | — |

**Verification sub-agent, round 1 verdict: NOT READY**, on three substantive defects (#6 blocking, #4
and #7 high) plus documentation gaps. All were fixed and a second round dispatched.

### The cold read (a required D5 verification)

The plan requires the user page be read cold and to produce *"you lose nothing if you don't"* rather
than *"you must wire this up."* The sub-agent's verdict was **(ii), the correct reading**, citing the
opening block:

> *"You do not need this page."* … *"Plan Marshall works exactly the same whether you turn this on or
> not."* … *"If you never read past this box, you have lost nothing."*

It noted the only sentence pulling the other way (*"What was missing is a way to follow one in an
editor"*) is immediately defused and sits below the admonition.

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | _pending_ | — | PR not yet opened at the time this report was committed |
| `cuioss-review-bot` | _pending_ | — | PR not yet opened at the time this report was committed |
| `sourcery-ai` | _pending_ | — | PR not yet opened at the time this report was committed |

⚠ This table is **necessarily incomplete in this file**, and the reason is structural, not an
omission: the lane contract requires the report to be committed as the **last pre-merge commit**,
before the PR is armed — so no review has happened when it is written. The coverage figure and the
§ Step 8 shortfall disclosure are reported to the operator in-session, where they can still be acted
on.

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no token counter to the
  running agent, so no figure is stated rather than an estimate being presented as a measurement.
- **Wall-clock:** at least 2 h 32 min — the interval between the first commit (`8795719`,
  18:44:44Z) and the report commit — and necessarily longer, since the run's first `git status`
  precedes that commit by an unrecorded margin. Stated as a lower bound rather than a point
  estimate, because the start instant was never recorded. Includes four full `./pw verify` runs
  (~5 min each, from the runs' own pytest summaries) and two verification sub-agents (~9 min and
  ~10 min, from the task-completion durations).
- **Population:** this single Claude Code cloud session's interactive usage. ⛔ **Not comparable to a
  plan-marshall `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary. This run has no dispatch tree (one sub-agent aside)
  and no such boundary, so the two figures count different things and are not made comparable here.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done** — named above, including those deliberately not loaded |
| 2 Branch | **Done** — harness-assigned `claude/skill-lsp-server-2oqo3r` kept as-is and pushed to `origin` **before any edit** |
| 3 Plan directory | **Done** — `plan.md` in place; first-instruction block verified **present** on arrival, no repair needed |
| 4 Implement | **Done** — every commit on the branch carries the trailer (verified across all of them); the count is not restated here because it moved after this table was first written |
| 4 Per-commit gate | **Done** — every `*.py`-touching commit preceded by a clean gate (`ruff` passed, `mypy` clean, SPDX passed, plugin-doctor `issues[0]`) |
| 4 Pushed | **Done** — pushed after every commit; no unpushed commit remains |
| 5 Build gate | **Done** — Python changes present, so owed; `./pw verify` SUCCESS (20 117 passed) |
| 6 Verification sub-agent | **Done** — round 1 NOT READY with 18 findings; all fixed or explicitly deferred; round 2 dispatched |
| 7 PR cycle | See § Reviewer participation — the PR is opened after this commit, so participation is reported to the operator in-session |
| 8 Merge gate | Conditions 1–3 driven after this commit; disclosure per § Step 8 condition 4 |
| 8 Bridge | **Clean** — every write landed inside `doc/plans/code-intelligence-substrate/240-skill-lsp-server/`; no status file, ledger, or other plan's directory touched |
| 9 This check | **Done** — this table |
| 9 What have we learned | **Done** — below |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a machine-local build step a cloud run never performs.

⚠ **One deviation from the contract, recorded rather than glossed.** The lane contract writes the
D0(b)-style fork as something a headless run resolves by its autonomous fallback. This run had a
**reachable operator** and escalated instead, which the contract explicitly permits. The plan's own
autonomous fallback — ship the proposal alone — remained available and was the stated default; the
operator chose otherwise.

## What have we learned (Step 9)

⭐ **One contract change is proposed, and this run produced the evidence twice.**

**The problem.** Step 5's build gate and Step 6's sub-agent both read *committed* state, and the
contract is explicit about that. But neither reaches the defect class that cost this run the most: a
surface that passes every static gate and every synthetic-fixture test, and is **broken the moment
anything real drives it**. Two of this run's three most serious findings were exactly that shape:

- `references()` verified almost nothing for `path` and `import` edges. 55 green tests, clean
  `./pw verify` — found only by running the verb against the real corpus and *looking at the output*.
- `serve`, invoked the way its own `SKILL.md` documented, could never have worked. The in-process
  protocol tests passed **because** the server's lenient reader round-tripped its own corrupted
  output — the test structurally could not fail.

Both were caught by executing the shipped entry point against real data, not by any gate the contract
names.

**The proposed change.** Add to Step 5, after the build gate: *when a run ships an executable surface
(a script verb, a server, an entry point), drive that surface end to end against real repository data,
through the same invocation its own documentation gives, before dispatching the verification
sub-agent — and paste the actual output into the report.* A synthetic fixture answers "does the code
do what the test says"; only the real corpus answers "does the documented invocation produce a real
answer".

⚠ **This is a proposal, not a change.** ⛔ It is not self-approved and has not been applied — the
operator has not been asked, because the contract requires that ask to be a separate `chore/` PR that
must not be coupled to this plan's landing. It is recorded here as the evidence-bearing candidate.

**Also learned, not proposed as a contract change:** the contract's warning that `test-compile` catches
what `quality-gate` and `module-tests` cannot is *correct and load-bearing* — it fired twice in this
run, on two different error classes. No amendment needed; it worked as written.

## Residue

- ⛔ **D3 remains unbuilt**, hard-gated on `230-validate-precision`. When that lands, the diagnostic
  capability is a small addition here: advertise the provider and stream the validator's set. The
  97.4 % false-positive measurement above is the baseline it must improve on.
- ⚠ **The `lspServers` declaration is verified by handshake but not in a deployed plugin cache.** The
  `sys.path` bootstrap is layout-derived and resolves in both the source tree and a sibling-bundle
  cache layout, and was proven with no `PYTHONPATH` — but this clone has no `target/` or
  `~/.claude/plugins/cache`, so the deployed path is reasoned, not observed. First local install
  should confirm it.
- ⚠ **`.md` extension collision** is a real risk the design mitigates by defaulting off; no client was
  observed arbitrating two Markdown servers.
- **Finding 19** (`CLAUDE.md` component counts) is deferred and unowned — it predates this plan.
- **Finding 20**: no `manage-config` verb writes `code_intelligence`, unlike every other section.
- ⚠ **`uv.lock` is stale relative to `pyproject.toml` on `main`, and this run did not fix it.** `pyproject.toml` declares `ruff>=0.16.2` while the committed `uv.lock` records `>=0.16.1`, so every `./pw` run rewrites the lockfile as a side effect. It was backed out of every commit here rather than shipped, per the lane contract's rule against sweeping generated-file churn into a deliverable commit — an unrelated dependency-specifier change does not belong in a plan PR. Recorded because it is a real pre-existing inconsistency that will keep surfacing in every branch until someone re-syncs the lockfile deliberately.
