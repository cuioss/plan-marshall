# Maven Profile Classification Reference

## Canonical Classifications

| Canonical | Description | Example Profile IDs |
|-----------|-------------|---------------------|
| `integration-tests` | Integration/E2E tests | `it`, `e2e`, `local-integration-tests` |
| `coverage` | Code coverage | `jacoco`, `istanbul` |
| `benchmark` | Benchmarks | `jmh`, `perf`, `stress` |
| `quality-gate` | Quality checks | `pre-commit`, `lint`, `checkstyle` |
| `skip` | Exclude from command generation | Internal profiles |

## Multiple Profiles to One Canonical

When multiple profiles map to the same canonical:

- Only ONE command is generated
- First discovered profile becomes primary
- All profiles listed in `all_profiles`

**User override**: Add unwanted profiles to skip list.

## Storage

Configuration stored in `marshal.json` under `extension_defaults`:

```json
{
  "extension_defaults": {
    "build.maven.profiles.skip": "itest,native",
    "build.maven.profiles.map.canonical": "local-integration-tests:integration-tests,perf:benchmark"
  }
}
```

**Key Formats**:
- `build.maven.profiles.skip` - Comma-separated profile IDs to exclude
- `build.maven.profiles.map.canonical` - Comma-separated `profile:canonical` pairs

Skip list and profile mappings are read during architecture discovery to classify profiles.

## Common NO-MATCH-FOUND Profiles

Most NO-MATCH-FOUND profiles are **correctly unmatched**:
- `apache-release` — Release process, not a build command
- `skip-unit-tests` — Test skipping, not a positive command
- `use-apache-snapshots` — Repository config, not a command
