# Plan-ID Rename Map — `PLAN-NN` → `PLAN-CIS-NNN`

slug: code-intelligence-substrate

> Companion to `epic.md`. This document exists because the rename is NOT retroactive: the
> append-only records — `logs/decision.log`, `inbox/archive/`, and both other epics' ledgers — still
> carry the OLD ids by design, and rewriting an audit trail to match a later naming decision would
> destroy the evidence it exists to hold. **This table is the resolver between the two vocabularies.**
> Read it whenever a pre-rename document names a plan id you cannot find in the queue.

## What changed, and what deliberately did not

`PLAN-CIS-{NNN}-{slug}.md` is the naming form for every plan in this epic from now on. `CIS` is the
epic's code slug; `{NNN}` is a zero-padded three-digit ordinal that **is** the launch position.

- **Renamed: the 17 `staged` specs only.** Nothing else.
- **NOT renamed: `PLAN-01`, `PLAN-10` (shipped) and `PLAN-02`, `PLAN-11` (running).** Renaming any of
  the four would dangle a pointer nothing re-derives — the two running plans' `request.md` `source_id`
  names their spec path on disk, and the two shipped plans are referenced from `landings/PLAN-01.md`,
  `landings/PLAN-10.md` and their archived plan directories.
- **Ordinals follow the `status.json` `plans[]` array order** — the order the `next` verb actually
  walks — not the old `epic.md` table order. Those two had drifted apart before the rename
  (`PLAN-12`/`PLAN-13` sat at table positions 13/14 but array positions 8/9); assigning ordinals from
  the authority collapsed table position, array position, and id into one number.

## The mapping

`Pre-move id` is the id the plan carried in `truthful-signals` before the eight-plan move on
2026-07-29 — the id that `inbox/archive/` and that epic's `logs/decision.log` still use.

| New id | New filename | Old id | Old filename | Pre-move id |
|---|---|---|---|---|
| `PLAN-CIS-001` | `PLAN-CIS-001-content-search-seam.md` | `PLAN-03` | `PLAN-03-content-search-seam.md` | — |
| `PLAN-CIS-002` | `PLAN-CIS-002-lsp-shaped-query-api.md` | `PLAN-08` | `PLAN-08-lsp-shaped-query-api.md` | — |
| `PLAN-CIS-003` | `PLAN-CIS-003-marketplace-dependency-resolver.md` | `PLAN-04` | `PLAN-04-marketplace-dependency-resolver.md` | — |
| `PLAN-CIS-004` | `PLAN-CIS-004-native-coordinate-resolvers.md` | `PLAN-05` | `PLAN-05-native-coordinate-resolvers.md` | — |
| `PLAN-CIS-005` | `PLAN-CIS-005-resolver-configuration.md` | `PLAN-09` | `PLAN-09-resolver-configuration.md` | — |
| `PLAN-CIS-006` | `PLAN-CIS-006-validate-precision.md` | `PLAN-06` | `PLAN-06-validate-precision.md` | — |
| `PLAN-CIS-007` | `PLAN-CIS-007-skill-lsp-server.md` | `PLAN-07` | `PLAN-07-skill-lsp-server.md` | — |
| `PLAN-CIS-008` | `PLAN-CIS-008-scope-estimate-vocabulary-closure.md` | `PLAN-12` | `PLAN-12-scope-estimate-vocabulary-closure.md` | — |
| `PLAN-CIS-009` | `PLAN-CIS-009-documented-enum-diverges-from-argparse-choices.md` | `PLAN-13` | `PLAN-13-documented-enum-diverges-from-argparse-choices.md` | — |
| `PLAN-CIS-010` | `PLAN-CIS-010-finalize-dispatch-evidence-is-missing.md` | `PLAN-120` | `PLAN-120-finalize-dispatch-evidence-is-missing.md` | `PLAN-104` |
| `PLAN-CIS-011` | `PLAN-CIS-011-finalize-dispatch-manifest-observability.md` | `PLAN-121` | `PLAN-121-finalize-dispatch-manifest-observability.md` | `PLAN-64` |
| `PLAN-CIS-012` | `PLAN-CIS-012-footprint-read-outside-its-window.md` | `PLAN-122` | `PLAN-122-footprint-read-outside-its-window.md` | `PLAN-106` |
| `PLAN-CIS-013` | `PLAN-CIS-013-chat-signal-provenance-filter-under-inclusive.md` | `PLAN-123` | `PLAN-123-chat-signal-provenance-filter-under-inclusive.md` | `PLAN-78` |
| `PLAN-CIS-014` | `PLAN-CIS-014-aggregate-cost-invisible-to-per-call-ceiling.md` | `PLAN-124` | `PLAN-124-aggregate-cost-invisible-to-per-call-ceiling.md` | `PLAN-77` |
| `PLAN-CIS-015` | `PLAN-CIS-015-outline-plan-scope-derivation-integrity.md` | `PLAN-125` | `PLAN-125-outline-plan-scope-derivation-integrity.md` | `PLAN-61` |
| `PLAN-CIS-016` | `PLAN-CIS-016-auditor-detector-integrity.md` | `PLAN-126` | `PLAN-126-auditor-detector-integrity.md` | `PLAN-76` |
| `PLAN-CIS-017` | `PLAN-CIS-017-freshness-gate-cannot-distinguish-test-authored-evidence.md` | `PLAN-127` | `PLAN-127-freshness-gate-cannot-distinguish-test-authored-evidence.md` | `PLAN-82` |

### Unchanged rows

| Id | Filename | Why it kept its id |
|---|---|---|
| `PLAN-01` | `PLAN-01-inventory-blind-spot.md` | shipped #1056 — `landings/PLAN-01.md` + archived plan dir point at it |
| `PLAN-10` | `PLAN-10-end-phase-replace-not-accumulate.md` | shipped #1059 — `landings/PLAN-10.md` + archived plan dir point at it |
| `PLAN-02` | `PLAN-02-resolver-ext-point-seam.md` | shipped #1067 — `landings/PLAN-02.md` + archived plan dir point at it |
| `PLAN-11` | `PLAN-11-audit-report-path-ignores-plan-dir.md` | shipped #1063 — `landings/PLAN-11.md` + archived plan dir point at it |

⭐ **All four unrenamed plans have now SHIPPED.** The "never rename a launched or shipped plan" rule
still binds on all four — the reason simply changed from *a live worktree points at the spec* to *a
landing record and an archived plan dir point at it*. The rule is now permanent for these four rather
than conditional on a running plan.

## Reverse lookup — old id → new id

`PLAN-03`→`001` · `PLAN-04`→`003` · `PLAN-05`→`004` · `PLAN-06`→`006` · `PLAN-07`→`007` ·
`PLAN-08`→`002` · `PLAN-09`→`005` · `PLAN-12`→`008` · `PLAN-13`→`009` · `PLAN-120`→`010` ·
`PLAN-121`→`011` · `PLAN-122`→`012` · `PLAN-123`→`013` · `PLAN-124`→`014` · `PLAN-125`→`015` ·
`PLAN-126`→`016` · `PLAN-127`→`017`

⚠ **The old ids `03`–`09` and `12`–`13` are NOT a contiguous remap.** `PLAN-08` became `002`, not
`006`, because the ordinal follows queue order rather than the old numeric sequence. Do not infer a
new id arithmetically — look it up.

## What was rewritten, and what was left alone

| Surface | Action |
|---|---|
| `plans/*.md` filenames (17) | renamed |
| `plans/*.md` bodies (all 21, incl. the 4 unrenamed) | cross-references rewritten |
| `epic.md` | references rewritten; queue table reordered to the new ordinals; band section rewritten |
| `status.json` `plans[].id` | rewritten (the `slug` field was already the descriptive name and did not change) |
| `landings/PLAN-01.md`, `landings/PLAN-10.md` | forward-references to staged plans rewritten; the records' own ids kept |
| `logs/decision.log` | ⛔ **untouched** — append-only audit trail |
| `inbox/archive/*.md` (33) | ⛔ **untouched** — append-only audit trail |
| `truthful-signals` ledger | ⛔ **not edited** — another epic's tree; notified by inbox message instead |

## Allocating the next id

⭐ **Next free ordinal: `PLAN-CIS-023`.** Allocate by incrementing past the highest existing
`PLAN-CIS-*`, never by counting staged rows — that under-counts as soon as a plan ships.

⚠ **The ordinal is no longer the launch position.** `PLAN-CIS-018`…`-022` were staged from landings
rather than from `decompose`, so they sit at the queue TAIL while their subject matter belongs with the
WS-04 measurement cluster. The `#` column still equals the `plans[]` array position; it no longer
implies priority. ⛔ **Do not "fix" this by renumbering** — the ids are already cited in landing records
and in two sibling epics' inboxes.

⛔ **UPPERCASE is mandatory.** `orchestrator inbox detect` matches the code slug as `[A-Z0-9]{2,8}`.
A lowercase `plan-cis-018-x.md` classifies as `unrecognised_id`, and the plan then writes NO inbox
message at finalize — the failure is silent at the orchestrator end. The three accepted id forms
(`PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, `{SLUG}-{DIGITS}`) shipped in PR #1057.
