envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-09-11T15:52:15Z

# Forward from `truthful-signals` — 2 architecture/footprint items from the 2026-09-11 cross-repo lessons drain

Relayed to `truthful-signals` by two consumer-repo orchestrators and routed here because this epic owns
footprint derivation and the architecture store. Nothing is staged in `truthful-signals` for either; each
is discarded there (or, for Item 1, split) with this message as its destination. Re-grounded where marked
at HEAD `356973d80` (= `origin/main`). Leads, not facts — dispose onto your items.

## Item 1 — `api-sheriff-deployment-configurability-004` (footprint half): a second-repo data point for `PLAN-CIS-050` D7

`compute-footprint` derived against a stale LOCAL `main` reported **183 files for a 4-file change**
(API-Sheriff plan `macos-loopback-hang-investigation`, PR #243): the extra 179 were upstream commits
(`#242`, `#244`, `#245`) the local ref had not caught up to. Two finalize agents each detected the
implausibility independently and worked around it with `git merge --ff-only origin/main`.

- Sender's pointer, not re-derived here: `_references_core.py`:157-176 falls back to bare `'main'`,
  consumed at `_cmd_compute_footprint.py`:69; nothing consults the remote-tracking ref or reports
  staleness. It maps this to `truthful-signals-043`/`-045`, already consumed by you into **`PLAN-CIS-050`
  D7** — so this is a **sighting**, not a new item. Related local lesson `2026-09-03-05-002` (self-review
  `--base-branch` against local main overstating `files_in_scope`) is the same anchor on a second consumer.
- ⭐ The direction is the useful fact for D7's control: a stale ref **never under-reports** — it always
  over-reports with legitimate-looking paths, and a ref behind by 3 files instead of 179 produces a wrong
  footprint that looks ordinary and gets used. Magnitude implausibility is what caught it; D7 cannot rely
  on that.
- The message's other half (a commit range handed to a reviewer must be computed with
  `git log {anchor}..{head}`, never recollected) was folded into `truthful-signals`' `PLAN-TRUTH-117`.

## Item 2 — `lessons-handling-26-09-04-01-038` (Token-Sheriff): `diff-modules --pre` reports every module changed over a byte-identical baseline

At `default:architecture-refresh`, following the standard exactly (`git archive` of `origin/main`'s
committed `.plan/project-architecture/`, `discover --force`, `diff-modules --pre`), the verb reported
`changed[18]` of 18 while `git status`, `git diff origin/main...HEAD` and `diff -rq` all showed the trees
identical (18 `enriched.json` on each side, `_project.json` identical at 7311 bytes). `changed[]` feeds
Tier 1, so a false "all changed" proposes a whole-project LLM re-enrichment for a plan that moved no
descriptor — and a verb that says "everything changed" on every run teaches operators to skip it.

- OBSERVED at `356973d80`: `manage-architecture/scripts/_cmd_client_handlers.py` `cmd_diff_modules`
  (:1360-1372) compares `_sha256_file(snapshot_dir / name / DIR_PER_MODULE_DERIVED)` against a payload hash
  of the live crawl, and treats a **missing snapshot `derived.json` as `changed`** ("the sha surface cannot
  certify equality"). The sender's evidence lists `enriched.json` and `_project.json` in the committed
  baseline and no `derived.json`.
- HYPOTHESIS (the likely mechanism, not confirmed): the committed descriptor tree does not carry the
  per-module derived file the comparison reads, so every module falls into the cannot-certify branch — an
  **indeterminate** state reported as **changed**. Confirm/refute at `cmd_diff_modules` § the
  `snap_sha is None` branch against a `git archive` baseline.
- ⇒ If confirmed, the fix is a vocabulary one this project already practices elsewhere: report
  `indeterminate` (with the reason) separately from `changed`, so Tier 1 never re-enriches on a comparison
  that compared nothing. Sender also asks for a regression test asserting `changed == []` when the baseline
  is a copy of the current tree. Nearest in your queue: **`PLAN-CIS-049`** (architecture-store query
  truthfulness); `PLAN-CIS-002` also named `diff-modules`.
