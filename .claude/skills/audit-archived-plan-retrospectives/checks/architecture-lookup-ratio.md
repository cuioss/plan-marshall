# Check: architecture-lookup-ratio (cross-plan)

Measures, per plan, the ratio between **information lookup** (architecture
orientation / navigation) and **build lookup** (canonical-command resolution) —
both served by the `manage-architecture:architecture` script. It surfaces plans
whose architecture usage is overwhelmingly build-resolution with proportionally
little information lookup, a candidate signal for *navigation that bypassed the
structured-query lever* (`Read` / raw-bash exploration instead of
`architecture find` / `which-module`). This is a cross-plan check: it emits one
aggregate block (per-plan rows + corpus aggregates + derived thresholds).

The deterministic computation lives in `scripts/audit.py`
(`cross_architecture_lookup_ratio` / `emit_architecture_lookup_ratio_block`);
this sub-document is the interpretation guide. It reuses the same
`script-execution.log` call-line grammar (`_SBM_CALL_RE`) and architecture-call
predicate (`_sbm_is_arch`) the `sequence-and-build-minimality` check uses, so the
two never disagree on what an architecture call is.

## Inputs the check reads

Per plan, the script reads the plan-scoped `logs/script-execution.log` and tallies
every `manage-architecture:architecture {sub}` call. No other input is consulted.

## Classification — the three intents of an architecture call

| Bucket | Subcommands | What it is |
|--------|-------------|------------|
| **information lookup** | `find`, `which-module`, `files`, `module`, `modules`, `info`, `overview`, `topology`, `graph`, `commands` | Orientation / navigation: "where is X / which module owns this path / what files / project shape". The structured-query alternative to `Glob`/`Grep`/raw-bash exploration (`token-management.adoc` §4). |
| **build lookup** | `resolve`, `derive-verification` | Resolving the canonical build command + the verification step set per module (`build-management.adoc`). |
| **discovery** | everything else (`discover`, `enrich`, `crawl-*`, …) | One-time architecture CONSTRUCTION, not a per-plan lookup. Counted (and **broken out per verb** — `discover`/`enrich`/`crawl`/`other`) but **excluded** from the ratio. |

> **Discovery is mostly setup-time / ad-hoc.** `discover`/`enrich`/`crawl-*` run
> during `/marshall-steward` architecture construction or manual setup — **outside**
> plan execution — so they land in the global logs, not a plan's
> `logs/script-execution.log`. A plan's per-plan discovery breakdown is therefore
> usually **all-zero**; the corpus-wide discovery volume (e.g. `enrich 88×`) is
> surfaced by the `global-log-analysis` check (high-frequency-caller / error rows),
> not here. The per-plan and corpus breakdown exist for the rare plan that runs
> in-plan discovery and to make the otherwise-lumped count legible.

## Per-plan computation

| Quantity | Definition |
|----------|------------|
| `info_lookups` | count of information-lookup calls |
| `build_lookups` | count of build-lookup calls |
| `discovery_calls` | total count of discovery calls (excluded from the ratio) |
| `discovery_breakdown` | the discovery total split per verb: `discover=N;enrich=M;crawl=K;other=J` |
| `ratio` | `info_lookups / build_lookups`, or `n/a` when `build_lookups == 0` (no defined ratio; the plan cannot be build-dominated) |

## Cross-plan computation + the flag

Corpus aggregates: `corpus_info_lookups`, `corpus_build_lookups`,
`corpus_discovery_calls`, `corpus_discovery` (the per-verb discovery breakdown
summed across the corpus), `corpus_info_build_ratio`. The thresholds are derived
from the LIVE corpus (never hard-coded), over the plans that ran at least one
build lookup: `median_build_lookups` (the build-volume floor) and `ratio_p25`
(the bottom-quartile ratio cut).

`build_dominated_lookup` fires when a plan **(a)** ran a non-trivial number of
build lookups (`build_lookups >= median_build_lookups`) AND **(b)** sits in the
bottom quartile of the info/build ratio (`ratio <= ratio_p25`). A
**degenerate-corpus guard** suppresses the flag unless the ratio distribution has
a real low tail (`ratio_p25 < median_ratio`) — a uniform corpus flags nobody.
`severity` is `genuine` when flagged, `informational` otherwise.

## Emitted columns

```
plans_in_corpus: P
corpus_info_lookups: I
corpus_build_lookups: B
corpus_discovery_calls: D
corpus_discovery: discover=…;enrich=…;crawl=…;other=…
corpus_info_build_ratio: R | n/a
median_build_lookups: M
ratio_p25: Q
median_ratio: MR
genuine_signal_count: G
rows[P]{plan_id,change_type,info_lookups,build_lookups,discovery_calls,discovery_breakdown,total_arch,ratio,flags,severity}
```

## How the orchestrator interprets the rows

EVERY emitted row is adjudicated with a stated verdict and cited evidence; a row
may be dismissed as informational/expected ONLY with a cited reason.

- **`build_dominated_lookup` (genuine)** — the named plan leaned heavily on build
  resolution with proportionally little information lookup. This is a **prompt, not
  a verdict**. Two readings are both legitimate, and the script cannot distinguish
  them — the orchestrator must:
  1. **"No navigation needed"** — a recipe (its deliverables enumerate the exact
     files), a surgical fix (one known file), or an issue-fix (the issue names the
     file) legitimately needs zero orientation. A low ratio here is **expected**,
     not a defect. Dismiss with the plan's `change_type`/scope as the cited reason.
  2. **"Lever bypassed"** — the plan DID navigate, but via `Read` / raw-bash
     (`cat`/`grep`/`ls`) instead of `architecture find`/`which-module`. To confirm,
     cross-read the `global-log-analysis` rows (high `Read`/raw-bash, low
     `architecture find`) or the transcripts. Only THEN is it a real
     structured-query-adoption gap.
- **A high `build_lookups` with no flag** is still worth a glance: repeated
  resolution of the same module's canonical command is a **wall-clock /
  re-resolution** concern (cacheable), tied to the `architecture resolve` perf
  work — but that is a latency signal, **not** a token cost (each resolve is a
  token-cheap script round-trip; see `checks/token-economics.md` measurement
  caveat and `build-management.adoc`).
- **`corpus_info_build_ratio`** — informational corpus shape. A very low corpus
  ratio across many plans is a prompt to ask whether the structured-navigation
  verbs (`find`/`which-module`) are adopted at all in this project.

## Critical rules

- The script is the single source of truth for the parsed calls and the
  classification. Do not re-grep the logs or re-derive the ratio in chat.
- The intent buckets (`_ALR_INFO_SUBS` / `_ALR_BUILD_SUBS`) and the thresholds
  (`median` / `p25`, degenerate-corpus guard) live in `scripts/audit.py`. If a
  subcommand's intent changes, edit the script rather than substituting a reading.
- A LOW ratio is NOT a defect by itself — only a *prompt*. Never file a lesson or
  claim a structured-query-adoption gap without cross-reading the navigation
  evidence (per the orchestrator-interpretation rule above).
- This check is read-only; it never edits `.plan/` files.
