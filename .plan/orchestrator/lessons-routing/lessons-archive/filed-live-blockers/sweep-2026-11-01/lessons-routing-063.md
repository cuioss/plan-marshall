# Domain content (`pm-dev-java`): two Java gaps found in a Quarkus native-image project

Severity: **medium** (item 1), **low** (item 2). Bundle: `pm-dev-java`. Domain-bundle content, filed under the `ingest` ruling at any severity.
Source: 2 lessons from the TokenSheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/TokenSheriff/`. Checked at this sweep: `architecture search --content` over the bundles finds `SecureRandom` only in `persona-security-expert/standards/cryptography-key-management.md`, and no match for `U+2028`, `u2028` or `S2479` in any Java standard. Item content otherwise rests on the lesson text.

## 1. `SecureRandom` in native-image code (`2026-10-29-23-001`, medium, `java-quarkus`)

A `static final SecureRandom` is initialized at image build time and the GraalVM native-image build rejects it; the local `verify -Ppre-commit` does not catch it, only the native-image CI job does. Creating one per call trips Sonar `java:S2119`. Rule: a per-instance `final` field, created at construction. `java-quarkus/standards/quarkus-native.md` is the natural home.

## 2. U+2028 / U+2029 in Java source (`2026-10-29-23-003`, low, `java-core` / `junit-core`)

Raw U+2028/U+2029 (and other invisible or bidi characters such as U+200B, U+202E) in test data trip Sonar `java:S2479` and cannot be reliably matched or inserted by the Edit tool. Write them as Unicode escapes in literals; but never write CR/LF as `\u000d` / `\u000a` (they break compilation even inside a literal) — use `\r` / `\n`.
