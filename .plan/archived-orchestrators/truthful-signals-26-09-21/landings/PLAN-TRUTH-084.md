# Landing Analysis: PLAN-TRUTH-084 — finalize step contract, ordering and re-fire currency

epic: truthful-signals
workstream: WS-01
pr: #1309 — merged as `7566efd95`
cloud-run: `cloud-runs/510-finalize-step-contract-ordering-and-refire-currency/`

> A gap-fix plan authored by the epic audit (PR #1298). It shipped with **no `verification.md` and no
> `gaps.md`** — the post-run verification was performed during ingestion on 2026-08-22. 12 mutations,
> each dirty-checked first, byte-snapshotted to `$TMPDIR`, restored by file copy (never git), every
> restore sha256-identical with `git status --porcelain <path>` empty.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | **8/8 landed** — D3, D4, D6, D8 land complete but leave residue |
| Upstream gaps claimed closed | 36 |
| **Genuinely closed** | **33** |
| Partially closed | 3 — `260/G1`, `280/G2`, `160/G2` |
| Not closed | **0** |
| New gaps filed | 9 (high 2 · medium 3 · low 4) |

**#1309 is the corpus's single largest gap-closer** — it closed gaps across 040, 100, 130, 160, 190,
230, 260, 280, 300, 302, 310, 410 and 440.

## ⛔ Carry-forward — the central mechanism fires on an undocumented magic string

The plan's central new mechanism — the input-table conformance scope that
`ext-point-finalize-step.md` itself calls *"where the contract is actually held"* — **fires only on
tables whose first header cell is the literal string `Prompt-body field`**, a convention stated in **no
normative document**. A matched positive/negative control pair differing only in that header flips the
suite from RED to 19-passed-green. (`G1`, high.)

That is the same shape as the gap it was written to close: a guard whose scope is narrower than the
contract it enforces, and whose narrowness is invisible at the guard.

## ⛔ `190/G6` is closed on its DOCUMENTATION half only — the code path is still live

`phase-6-finalize set --field self_review` **still succeeds and persists a dead key**. D4's own
preamble diagnoses this as *"a shipped false signal on the highest-risk gate the page describes"* —
and then fixes only the documentation half, with **no residue entry**. Carried forward as this plan's
**G2 (high)**, so the chain is unbroken: the ledger records `190/G6` closed for the doc and open for
the code, under `510/G2`.

⚠ **This is why a gap must be re-grounded at HEAD before it is scheduled, not read from `gaps.md`.**
A reader taking `190/G6` as simply "closed" would ship the false-success path forward.

## The three partial upstream closures

| Gap | Why partial |
|---|---|
| `260/G1` | Input-table scope bound to an undocumented header string — its *Done-when* says "any finalize-step doc" and it holds for **one header**. |
| `280/G2` | The "every `resolve-target` carries `--workflow`" clause is unmet at `planning.md:233` — a zero-emission site this plan's Out-of-scope **excludes by name**. The clause overreaches its own gap. |
| `160/G2` | Four "derived" labels retired; a fifth survives as a source comment. The literal "document or docstring" wording **is** met. |

## Gaps filed

| Gap | Sev | Kind | Summary |
|---|---|---|---|
| G1 | **high** | vacuous-guard | Input-table guard reads only tables headed `Prompt-body field`; proven by matched control |
| G2 | **high** | bug | `set --field self_review` still succeeds and persists a dead key |
| G3 | medium | vacuous-guard | Wildcard-free glob guard examines zero globs if all declarations go wildcard-bearing |
| G4 | medium | missing-test | New baseline-reconcile reason/error tables are unbound restatements of the script |
| G5 | medium | incomplete-sweep | Collateral list omits `test_step_records_facts_contract.py` |
| G6 | low | stale-statement | § Cost says 52 findings; the five round tables carry 58 instances / 56 rows |
| G7 | low | stale-statement | Sourcery diff-size figure uses the floating `origin/main` endpoint the report retired |
| G8 | low | stale-statement | `_gate_coverage.py:417` comment still calls the parity population "derived" |
| G9 | low | missing-test | Settle-band occupancy and reader lists restate a population with no binding test |

## Report inconsistencies

§ Cost's "52 across five rounds" contradicts § Findings' own stated rule and its own tables (58
instances) — **and the same 52 shipped in the PR body and the squash commit message**. § Reviewer
participation's `git diff origin/main...HEAD | wc -c → 437,707` reproduces at no endpoint pair
(469,876 / 469,876 / 430,549) — **the exact floating-endpoint defect § Build gate corrects three
sections earlier, committed in the same document**. § Collateral claims completeness after two rounds
and still omits one landed file.

⭐ Everything else reproduced **exactly**: all four populations, nine replayed mutations, and every
§ Build gate / § Cost git figure (28/61 files, 22 commits, 62 files +3377/−443, `db2f61d` not an
ancestor of main).

## What was NOT checked

- No full `./pw verify` — `uv` is absent from this machine's PATH; the affected surface was run with
  the repo's own `.venv-3.14` interpreter (**3528 passed**). Historical 21103/21107/21108 figures are
  point-in-time and un-re-derivable eight commits later.
- PR #1309 review-thread state — no GitHub API queries. The one behavioural CodeRabbit finding is
  visible in the shipped `branch-cleanup.md` text and its guard-widening consequence is verified.
- The five verification rounds and four cold reads as events (no transcripts committed); each round's
  *fixes* were checked individually.
- The operator merge authorisation — a conversation event. That `f07f0ea` is the merged head and is
  **not** an ancestor of main IS verified.
- The mutating half of `190/G6`'s Done-when — the `set` commands write the repo's `.plan/marshal.json`,
  so only the `get` half plus an isolated-temp-dir probe of the `set` code path was run.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1309`
- [x] row `landing` = `landings/PLAN-TRUTH-084.md`
- [x] `verification.md` + `gaps.md` authored at ingestion and retained under `cloud-runs/510-…/`
- [x] upstream closure re-derived: 33 closed / 3 partial / 0 not-closed
