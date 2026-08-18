# Gaps — 070-marshalld-self-reload-on-version-signal

**Source:** verification.md (same directory)   **Open items:** 6

Re-derived after adversarial review: G1, G2, G3, G4, G5, G7 are open; G6 is refuted (see the last
section) and its number is retired rather than reused.

## G1 — Stop treating an absent in-flight count as an idle daemon

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:669` — `run_status`; and `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py:108-112` — `decide`
- **What is wrong:** `run_status` writes `'in_flight': int(response.get('in_flight', 0) or 0)` (and the same for `queued`), so a ping response that carries **no** count is indistinguishable from one that reports zero. The population that carries no count is any daemon pinned to a marshalld copy predating `8f3c7fe0`: that copy's `Daemon._ping` returns exactly `{'status','pid','version'}` (confirmed at `git show 8f3c7fe0^:…/marshalld.py` — the pre-image body is a one-line return of those three keys), and `manage_build_server._ping` (`:238-265`) applies no version gate, so the handshake still succeeds and the counts silently become `0`.
  Executed end-to-end rather than read — `run_status` with `_ping` stubbed to a countless pre-`8f3c7fe0` response and `_running_binary_path` stubbed to an older path returns `{'in_flight': 0, 'queued': 0, 'binary_diverges': True}`, and feeding that exact dict to `decide` returns `ReconcileDecision(action='upgrade', reason='idle_and_stale')`. `upgrade` is `run_drain` (SIGTERM + `_DRAIN_GRACE_SECONDS = 30.0`, in-flight job marked `killed` and replayed) then `_start_daemon`.
- **Why it matters:** a post-sync reconcile against a **busy** daemon that predates the counts extension drains a live build. That is the single outcome D1's ⛔ STOP CONDITION exists to prevent, and it is reached by the exact mechanism the condition forbids — idleness inferred rather than read from the daemon's own count. It also makes `report-01.md`'s claim "Idleness is read from the daemon's own scheduler count, never inferred from anything else" false for that population. **Scope, stated precisely:** the exposed population is *stale daemons older than the counts extension*, not every stale daemon — a daemon pinned to any post-`8f3c7fe0` version does report the counts, so the hole closes as the fleet rolls forward. It is open for exactly the transition this feature was built to heal, which is when the first reconcile fires.
- **Fix:** in `run_status`, emit the counts only when the ping response actually contains them; when either key is absent, emit `in_flight: unknown` / `queued: unknown` (a sentinel, mirroring `_UNKNOWN_PROVENANCE`) rather than `0`. In `decide`, add a branch before the busy check: if `in_flight` or `queued` is missing or not an integer, return `ReconcileDecision(ACTION_DEFER, 'counts_unknown')` — fail closed, exactly as `provenance_unknown` already does.
- **Done when:** `test_reconcile_daemon.py` contains a case feeding a `running ∧ binary_diverges` status with `in_flight`/`queued` absent and asserts `decide(...).action == ACTION_DEFER` with reason `counts_unknown`; `test_manage_build_server.py` contains a case where `_ping` returns a response without the counts and asserts `run_status` does **not** report `0`; and mutating the new guard away turns both red.
- **Module/topic:** `plan-marshall:manage-build-server` + project-local `sync-plugin-cache` reconcile

## G2 — Verify the reconcile actually happened before reporting success and clearing the owed marker

- **Kind:** bug
- **Severity:** medium
- **Where:** `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py:211-215` — `reconcile`
- **What is wrong:** on `UPGRADE`/`START` the orchestration records `summary['reconcile_result'] = str(result.get('status', 'unknown'))` and then calls `clear_marker(marker)` unconditionally (`:210-215`). `result['status']` cannot be anything but `success`: `run_upgrade` (`manage_build_server.py:597-618`) returns a hard-coded `'status': 'success'` whatever `run_drain` did, and `_start_daemon` (`:495-524`) returns `'status': 'success', 'already_running': True` when a daemon is still live. So a drain that times out at `_DRAIN_GRACE_SECONDS` leaves the old stale daemon running while the reconcile reports success and deletes any accumulated `reconcile-owed` marker.
- **Why it matters:** a failed heal is rendered as a clean line and the accumulated `defer_count` evidence is destroyed — the epic's own archetype reproduced inside the fix, and a direct contradiction of D3's "a skipped reconcile is **reported, not swallowed**".
- **Depends on:** G7. `run_upgrade`'s current return carries **no** field that distinguishes a completed upgrade from a failed one, so this gap cannot be closed in `reconcile_daemon.py` alone — G7 must add the signal first.
- **Fix:** two parts, in order. (1) Land G7 so `upgrade` returns `drain_exited` and `already_running`. (2) In `reconcile_daemon.reconcile`, gate the success path on those fields instead of on `status`: for `upgrade`, treat `drain_exited is False` **or** `already_running is True` as a failed reconcile; for `start`, treat `already_running is True` as a failed reconcile. On failure set `summary['reconcile_result'] = 'failed'`, **write** (do not clear) the owed marker with `reason='reconcile_failed'` carrying the same `running_binary_path`/`resolved_binary_path` fields the defer branch records, and extend `_display_detail` with a `reconcile_failed` line. Clear the marker only on a verified success.
- **Done when:** `test_reconcile_daemon.py` drives `reconcile` with an `action_runner` returning `{'status': 'success', 'drain_exited': False, 'already_running': True}` for `upgrade`, and asserts `summary['reconcile_result'] == 'failed'` and that the marker exists with `reason == 'reconcile_failed'`; a second test with `{'status': 'success', 'drain_exited': True, 'already_running': False}` asserts the marker is cleared; and reverting the new gate turns the first test red.
- **Module/topic:** project-local `sync-plugin-cache` reconcile
- ⚠ **Correction (adversarial review).** The Fix originally read "treat `drained == False` while the daemon was running, or `running == False`, as a failed reconcile". Both criteria are inert. `run_upgrade`'s `drained` key is literally `drain_result.get('was_running')` — it says whether a daemon was there to drain, **not** whether the drain succeeded — and `running` is copied from `_start_daemon`, which returns `running: True` on the `already_running` path. Executed on the failing case (`_running_pid → 9999`, `_wait_for_exit → False`, `_spawn_detached` asserting it is never called): `run_upgrade` returns `{'status': 'success', 'action': 'upgrade', 'drained': True, 'running': True, 'binary_path': None, 'version': '1'}`. The old Done-when's fixture (`{'drained': False, 'running': True}`) describes a state `run_upgrade` never produces for this failure. Superseded by the Fix above.

## G3 — Correct the `status` sub-parser help string, which still names the removed `binary_path` key

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:872` — `_build_arg_parser`
- **What is wrong:** the line reads `sub.add_parser('status', help='Report running version + binary path.', ...)`. The `status` verb no longer emits a `binary_path` key at all; it emits `running_binary_path`, `resolved_binary_path` and `binary_diverges`. The module docstring, the `run_status` docstring, `manage-build-server/SKILL.md` prose and its verb table were all updated by this plan; this string was not.
- **Why it matters:** `--help` is the surface an operator reads before running the verb, and the singular "binary path" is precisely the ambiguity D4 exists to abolish — it reads as *"which binary is running?"* while promising nothing of the kind.
- **Fix:** change the help text to `'Report running version, in-flight/queued counts, and running vs resolved binary provenance.'`, matching the SKILL.md verb table at `manage-build-server/SKILL.md:177`.
- **Done when:** `grep -rn "Report running version + binary path" marketplace/` returns nothing.
- **Module/topic:** `plan-marshall:manage-build-server`

## G4 — Update the `_ping` docstring's documented response shape

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:249-250` — `_ping`
- **What is wrong:** the Returns block still documents the decoded ping response as ``{'status': 'ok', 'pid': int, 'version': str}``. Since `8f3c7fe0` the daemon also returns `in_flight` and `queued`, and `run_status` depends on them.
- **Why it matters:** the docstring of the function that reads the handshake is where an implementer looks to learn what the handshake carries — and G1's whole failure mode is a reader assuming those keys are always present. The docstring currently implies the opposite (they are never present).
- **Fix:** extend the Returns block to name `in_flight` and `queued`, and state explicitly that a daemon older than the counts extension omits them.
- **Done when:** the `_ping` docstring names all five keys and the omission case.
- **Module/topic:** `plan-marshall:manage-build-server`

## G5 — Make the steward health-check pointer surface `binary_diverges`

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md:260-268` — "Build Server Status (read-only pointer)"
- **What is wrong:** the Health Check is told to run `manage-build-server status` and report "the returned `running` / `version` / `registered` fields". Those three fields are all still valid, so nothing here is factually wrong — but a stale daemon reports `running: true` with a plausible `version`, so the steward health check renders exactly the clean line the plan's problem statement calls the flagship archetype, while `binary_diverges: true` and the `note` sit unread in the same payload.
- **Why it matters:** D4 made the divergence visible in `status`; the one operator-facing health surface that consumes `status` does not relay it, so the drift stays hidden on the surface an operator actually consults.
- **Fix:** add `binary_diverges` (and the `note` when present) to the named field list in that section, with one sentence saying a `true` value means the running daemon is executing an older pinned copy and a reconcile is owed.
- **Done when:** `marshall-steward/SKILL.md` names `binary_diverges` in the Build Server Status section.
- **Module/topic:** `plan-marshall:marshall-steward`

*(G6 was refuted during adversarial review — see the Refuted section below. The number is retired, not reused.)*

## G7 — Give `upgrade` a return field that can express a failed upgrade

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py:597-618` — `run_upgrade`
- **What is wrong:** `run_upgrade` calls `run_drain` and then `_start_daemon`, and discards the only two fields either of them produces that can report failure. `run_drain` returns `exited` (False when the daemon did not exit within `_DRAIN_GRACE_SECONDS = 30.0`) — `run_upgrade` drops it. `_start_daemon` returns `already_running` (True when it refused to launch because a daemon is still live) — `run_upgrade` drops that too. What survives is `drained`, which is `drain_result.get('was_running')` — whether there was a daemon to drain, not whether the drain worked — and `running`, which `_start_daemon` sets to `True` on the `already_running` path as well. Executed on the failing case (`_running_pid → 9999`, `_wait_for_exit → False`, `_spawn_detached` asserting it is never called): `run_upgrade` returns `{'status': 'success', 'action': 'upgrade', 'drained': True, 'running': True, 'binary_path': None, 'version': '1'}`. The only trace of the failure is `binary_path: None` — an incidental artefact of `_start_daemon` omitting the key on its `already_running` return, not a declared signal.
- **Why it matters:** an operator running `manage-build-server upgrade` on a wedged daemon is told `status: success` and `running: true` while the old binary is still the one executing — the same substitution D4 abolished in `status`, still live in the verb that is supposed to *fix* it. It is also the reason G2 cannot be closed in the project-local reconcile alone: there is no field there to read.
- **Fix:** in `run_upgrade`, add two keys to the returned dict: `'drain_exited': drain_result.get('exited', True)` and `'already_running': start_result.get('already_running', False)`, and set `'status': 'error'` with `'reason': 'drain_timeout'` (or `'daemon_still_running'`) when `drain_exited` is False or `already_running` is True. Name both keys in the `run_upgrade` docstring and in the `upgrade` row of `manage-build-server/SKILL.md`'s verb table.
- **Done when:** `test_manage_build_server.py` contains a case that stubs `_running_pid` to a live pid and `_wait_for_exit` to `False`, calls `run_upgrade`, and asserts `result['drain_exited'] is False`, `result['already_running'] is True` and `result['status'] != 'success'`; a companion case with a drain that exits asserts `drain_exited is True` and `status == 'success'`; and reverting the new keys turns the first case red.
- **Module/topic:** `plan-marshall:manage-build-server`

## Refuted during adversarial review

### G6 (refuted) — "Fold the build-server client's own repeated degradation WARNINGs into the D5 escalation"

- **Original claim:** `run_submit` / `run_wait` in `build-server-client/scripts/build_server.py` each
  call `_audit_log(plan_id, 'WARNING', 'build-server {submit,wait} degraded: reason=unreachable …')`
  **on every build**, so for a daemon that dies mid-run those identical WARNINGs accumulate build after
  build outside the D5 streak — leaving "a one-off fallback" and "the daemon has been gone all run"
  indistinguishable in the work log. Filed `low`, kind `incomplete-sweep`.
- **Verdict:** **refuted.** The "on every build" premise does not hold.
- **Evidence:** `_build_execute_factory._route_to_daemon` (`:546-605`) calls
  `client.run_preflight(...)` **on every build** and returns
  `(None, reason)` at `:571-573` whenever the result is not `ready` — *before* `run_submit` is ever
  reached. `run_submit`'s own degraded paths (`:438-456`, `:470-478`) are guarded by
  `_handshake(_socket_path())`, the same probe `run_preflight` uses (`build_server.py:590`), so a
  daemon that is down for a sustained period is caught by the per-build preflight and the client's
  submit/wait WARNINGs are never emitted at all. The `run_wait` loop (`_build_execute_factory:600-605`)
  returns on the first `degraded` result, so it cannot emit more than one WARNING per build either.
  The maximum exposure is therefore **one** client WARNING on the single build during which the daemon
  transitions from reachable to unreachable — not a repeat, and not the condition D5 exists to end.
  That transition build's `_record_resolution` call does count toward the streak: its reason
  (`unreachable`) is a member of `_DEGRADED_ROUTING_REASONS` (`_build_execute_factory:208-210`).
- **Residue (not filed as a gap):** a narrow path does survive — `run_submit` degrading while
  `run_preflight` still reports `ready`, i.e. a `_call_daemon` timeout at `_CONNECT_TIMEOUT_SECONDS`
  or a daemon answering `submit` with neither `queued` nor `refused` (`build_server.py:470-478`), both
  repeated across many builds. That is a hypothetical daemon-side malfunction, not the
  daemon-dies-mid-run scenario G6 described, and no evidence of it was found in the tree. Recorded so
  a third reviewer does not re-derive it as new.
- **Consequence:** D5 is a clean pass on both of its escalation sites; `verification.md`'s
  "D5 — one escalation site of two" narrative has been corrected accordingly.
