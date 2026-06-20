# 03 — Add the OpenCode distribution target

## Objective

Publish the OpenCode artifact tree the same way the Claude tree is already published —
through the existing target-parametrized CI matrix. This workstream is small because the
distribution design already anticipated it.

## Already in place (foundation)

- The `opencode` entry exists in the `claude-distribute.yml` `strategy.matrix`
  (`target_name: opencode`, `--target opencode`, publish dir `target/opencode`, branch
  `dist-opencode`, tag prefix `opencode/`). A push to `main` updates the `dist-opencode`
  snapshot branch; a `v{x.y.z}` source tag produces an immutable `opencode/v{x.y.z}` dist
  tag. Versioning stays unified — one source tag drives every target.
- A generation gate (`.github/workflows/opencode-generate-check.yml`) runs
  `generate.py --target opencode` on every PR touching `marketplace/bundles/**` or
  `marketplace/targets/**` and fails on any emitter error, so a broken emit never publishes.

The retired plan's distribution design (move `marketplace.json` to the repo root, GitHub
Pages hosting, release tarballs, `opencode-marketplace install` from a Pages URL) is
obsolete — do not implement it.

## Open work

**Confirm the OpenCode consumption path on a live client.** It is not yet verified which
install path against the published `dist-opencode` ref actually works — git-ref add,
`opencode-marketplace install <ref>`, or a deploy into `~/.config/opencode/`. The old
plan's assumption that `opencode-marketplace` accepts static URLs is unverified. Test on a
live OpenCode client, then pin and document the working path as the primary one (in
[05](05-opencode-documentation.md)). Confirm the generated tree's root holds whatever
manifest the chosen "add marketplace" path expects.

## Acceptance

- The documented OpenCode install path is verified end-to-end on a live client and recorded
  in [05](05-opencode-documentation.md).

## Dependencies

- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) — do not pin an
  installable path for a runtime that has not been proven.
