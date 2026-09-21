# PLAN-TRUTH-070: Runtime edge paths that crash or silently lose data

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from `doc/review-26-07-04.md`, which is being retired. Re-verified at HEAD.

## Objective

Six defects in the error and edge paths of the plan-marshall runtime scripts: three crash on input the
happy path never sees, and three **silently return a wrong result**, which is worse. Each is a few
lines; none is reachable by the linters (the review ran with `ruff` + `mypy` + `plugin-doctor` fully
green, so every one of these is semantic).

⚠ **THIS PLAN IS TASK-GROUPED, NOT COMPONENT-GROUPED, AND THAT IS A DELIBERATE EXCEPTION.** It spans
`manage-providers`, `tools-file-ops`, `manage-findings`, `tools-integration-ci` and
`manage-architecture`. The epic's standing preference is component grouping **because that is what
makes plans parallel-safe** — but each fix here is 1–5 lines in a distinct function, so the blast
radius is small even though the component count is high, and the alternative is five one-finding
plans. ⛔ **The trade is real and stated: this plan collides cheaply with many others.** Sequence it
against anything touching those five components rather than pairing it.

## Deliverables

**The silent-wrong-result half — this epic's actual subject:**

1. **[R5] `get_metadata_content_split` returns overlapping metadata and body — *Medium*.**
   `body_start` defaults to `0` and is only reassigned on a blank line or heading. For content that is
   **entirely metadata**, the loop never breaks, so `body` is the whole file *including* the metadata
   lines **while `metadata_block` also contains them**. ✅ Re-verified at HEAD: no `for…else`.
   The sibling `update_markdown_metadata` handles it correctly with exactly that construct.
2. **[R6] Bulk finding-resolve erases `resolution_detail` — *Low*.**
   `updates = {'resolution': to_resolution, 'resolution_detail': detail}` writes
   `resolution_detail: None` whenever `detail` is omitted, **wiping stored detail on every bulk
   resolve**. ✅ Re-verified at HEAD. Single-finding `resolve_finding` only sets it when truthy —
   **two verbs, two semantics, and the destructive one is the bulk path.**
3. **[R10] Root-module path collapses to an empty string — *Low*.**
   `rel = Path(module_rel).as_posix().lstrip('./')`. For a repo-root module (`'.'`) this collapses to
   `''`, so downstream `startswith`/`==` checks compare against an empty path — **which matches
   everything.** ✅ Re-verified at HEAD.
4. **[R10b / G3] Retire `lstrip('./')` as a prefix-strip, marketplace-wide.**
   `lstrip('./')` treats `'./'` as a **character set**: `'./.hidden/x'` → `'hidden/x'`, and `'../x'`
   → `'x'` — **a traversal silently mangled rather than rejected.** ✅ Re-verified: 1 site in
   `_cmd_manage.py`, **2 in `marketplace/targets/opencode/emitter.py`**. ⭐ The review found 6 more in
   `opencode/plugin_discover.py`; **those are now gone** — so this is a partially-retired class, and
   D4 finishes it. Replace every instance with `removeprefix('./')` and reject `..` explicitly.
   ⛔ **Population-derive the sweep** — do not fix the three known sites and call the class closed.

**The crash half:**

5. **[R2] `Retry-After` as an HTTP-date crashes the REST retry loop — *Medium*.**
   `delay = int(retry_after) if retry_after else (2**attempt)`. Per HTTP spec `Retry-After` may be an
   HTTP-date; `int()` then raises `ValueError`, which is **outside** the caught
   `(ConnectionError, TimeoutError, OSError)` and propagates uncaught. ✅ Re-verified at HEAD.
6. **[R3] Empty basic-auth password produces a half-configured header — *Low*.**
   Basic auth validates the username and rejects a placeholder password but **never rejects an empty
   one** — it base64-encodes `f'{username}:'` and emits a broken header. ✅ Re-verified: no
   `if not password` guard. Token auth rejects an empty token; **make basic auth symmetric.**
7. **[R7] `compute_total_elapsed` subtracts outside its guard — *Low*.**
   The `try` wraps only `datetime.fromisoformat`; the final
   `int((now - earliest).total_seconds())` sits **outside** it, so a naive/aware mismatch raises
   `TypeError` uncaught. ✅ Re-verified at HEAD — the return line is outside the loop's `try`. The
   sibling `compute_elapsed` guards its subtraction.
8. **D8 — tests, each verified to FAIL pre-fix**, one per finding, exercising the specific edge path.
   ⛔ The review notes most of these paths are **currently unexercised** — so a test that passes
   before the fix means the wrong path was tested.

Eight deliverables — under the raised cap of 12.

## Claim Labels

- **OBSERVED, re-verified at HEAD 2026-08-09 by symbol**: R2, R3, R5, R6, R7, R10, and the
  `lstrip('./')` population (1 + 2 sites).
- ✅ **[R4] IS FIXED and is NOT in this plan** — `verify_system_auth` no longer reports the missing
  binary via a naive `str.split`. Recorded so it is not re-filed.
- **HYPOTHESIS**: the `lstrip('./')` sweep finds no further sites. **Derive it** — the review's own
  count for `plugin_discover.py` (6) is now 0, which proves the population moves.
- ⚠ Line numbers in the source review are 5 weeks stale — **verify by symbol, never by line.**

## Expected Surface

- **OBSERVED**: `manage-providers/scripts/_providers_core.py`,
  `tools-file-ops/scripts/file_ops.py`, `manage-findings/scripts/_findings_core.py`,
  `tools-integration-ci/scripts/ci_base.py`, `manage-architecture/scripts/_cmd_manage.py`,
  `marketplace/targets/opencode/emitter.py`

## Dependencies and Sequencing

- ⛔⛔ **`manage-providers` is the surface of `PLAN-TRUTH-011`, which is RUNNING.** R2 and R3 touch
  `_providers_core.py`. **This plan CANNOT start until 011 lands.** ⭐ Recorded before the fact this
  time — a file-level check, not a subject-level one.
- ⚠ `marketplace/targets/opencode/emitter.py` is also `PLAN-TRUTH-071`'s surface (D4's `lstrip` sites).
  **Serialize against 071, or hand D4's opencode sites to 071 and keep this plan to the bundles.**
  Decide at outline and record it.
- ⚠ `ci_base.py` is adjacent to `PLAN-TRUTH-004`'s `tools-integration-ci` surface — check at outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-070-runtime-edge-paths-crash-or-silently-lose-data.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
