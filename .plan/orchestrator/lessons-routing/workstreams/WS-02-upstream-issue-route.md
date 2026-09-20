# WS-02: The upstream route — a refusal must become a destination

epic: lessons-routing
status: active

## Charter

Give the upstream class a place to go. Today `manage-lessons add` offers exactly two outcomes for a
`plan-marshall:*` component filed in a consumer repo — **refuse** (`wrong_store`, the finding is lost)
or **`--allow-foreign-store`** (the finding is stranded where nobody can act on it). ⛔ **A guard that
refuses without routing converts a finding into a dead end**, and three such dead ends already exist on
disk in `cui-jsf-test-basic`.

The transport is decided: **issues**, via the existing `plan-marshall:tools-integration-ci:ci issue`
surface. This workstream owns the route, not a new integration.

## In scope

- Emitting an upstream finding as an issue against the plan-marshall repository.
- What the issue body must carry to be actionable without the originating machine — the lesson body,
  the component, the producing plan, and the version/commit the client was running.
- Deduplication: the same finding raised by three client repos must not open three issues.
- The failure path: what happens when the issue cannot be filed (offline, no permission, rate limit).
  ⛔ **It must not silently fall back to the local store** — that reproduces the stranding this
  workstream exists to end.

## Out of scope

- Client-local findings (WS-03).
- Any change to the classification axis (WS-01 owns it).

## Done when

An upstream finding raised in a consumer repo reaches plan-marshall as an issue, or fails loudly with
its content preserved and its failure named.
