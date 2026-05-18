# Plan Marshall

<img align="right" width="300" src="doc/resources/planmarshall.png" alt="Plan Marshall">

> [!CAUTION]
> **Under Development. Not released yet. Alpha-Version**

[![Python Verify](https://github.com/cuioss/plan-marshall/actions/workflows/python-verify.yml/badge.svg)](https://github.com/cuioss/plan-marshall/actions/workflows/python-verify.yml)
[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg)](LICENSE.md)

### What is it?

Plan Marshall is an orchestration layer for AI coding assistants (currently Claude Code) that enforces consistency, reliability, and more predictable outputs. It packages a phase-driven planning workflow, a library of domain skills, and a marketplace of ten production bundles covering Java, JavaScript, Python, OCI containers, requirements, and plugin development.

## Prerequisites

> [!IMPORTANT]
> **Python 3 is required** and must be available as `python3` in your PATH.
>
> Verify with:
> ```bash
> python3 --version
> ```

## Installation (Claude Code)

Plan Marshall is distributed via a `dist-claude` orphan branch (snapshot, tracks `main`) and immutable `claude/v{x.y.z}` dist tags (pinned releases).

### Snapshot (tracks main)

```bash
/plugin marketplace add cuioss/plan-marshall@dist-claude
/plugin install plan-marshall@plan-marshall
/reload-plugins
```

Refresh later with `/plugin marketplace update plan-marshall` followed by `/reload-plugins`.

### Pinned release

```bash
/plugin marketplace add cuioss/plan-marshall@claude/v{x.y.z}
/plugin install plan-marshall@plan-marshall
/reload-plugins
```

Substitute `{x.y.z}` with the desired version. The `claude/v*` tag is immutable.

Install additional bundles (e.g. `/plugin install pm-dev-java@plan-marshall`) per Claude Code's plugin tooling.

The full distribution contract — publish triggers, versioning, source-vs-dist tag semantics, multi-target architecture — lives in [Developer Documentation › Distribution](doc/developer/distribution.adoc).

## Getting Started

### 1. Configure the project

After installing the marketplace, run the setup wizard once per project:

```bash
/marshall-steward
```

The wizard configures `.gitignore`, generates the script executor, discovers project modules, initializes `marshal.json`, configures skill domains, and detects CI tools.

### 2. Create your first plan

The simplest way is to invoke `/plan-marshall` with no arguments and pick "Create new plan" from the interactive menu:

```bash
/plan-marshall
```

If you prefer a one-liner, pass `action=init` together with a free-form task description:

```bash
/plan-marshall action=init task="Add user authentication"
```

Or seed the plan from a GitHub issue:

```bash
/plan-marshall action=init issue="https://github.com/cuioss/plan-marshall/issues/42"
```

`/plan-marshall` drives the six-phase lifecycle (init → refine → outline → plan → execute → finalize). Resume an existing plan with `/plan-marshall plan="<plan-id>"` — it auto-detects the current phase.

See [User Guide › Getting Started](doc/user/getting-started.adoc) for the full first-run walkthrough and [User Guide › Commands](doc/user/commands.adoc) for the complete `/plan-marshall` parameter reference.

## Documentation

| Section | Purpose |
|---|---|
| [Concepts](doc/concepts/index.adoc) | How Plan Marshall is built and why — architecture, planning workflow, the execution-context dispatcher, the per-role model system. |
| [User Guide](doc/user/index.adoc) | Operating Plan Marshall in a target project — installation, configuration, commands, terminal-title integration. |
| [Developer Guide](doc/developer/index.adoc) | Working on Plan Marshall itself — build system, marketplace generation pipeline, distribution, testing, workflow verification. |

The canonical source of truth for every skill, standard, and extension point is co-located with the code under `marketplace/bundles/`. The `doc/` tree is a thin navigational surface over it.

## Available Bundles

| Bundle | Purpose |
|---|---|
| [plan-marshall](marketplace/bundles/plan-marshall/README.md) | Core infrastructure, permissions, script execution, and the 6-phase planning workflow with task execution |
| [pm-dev-java](marketplace/bundles/pm-dev-java/README.md) | Java development standards and agents |
| [pm-dev-java-cui](marketplace/bundles/pm-dev-java-cui/README.md) | CUI-specific Java development standards covering CuiLogger, test generators, value object contracts, and HTTP client patterns |
| [pm-dev-frontend](marketplace/bundles/pm-dev-frontend/README.md) | JavaScript/CSS standards and tooling |
| [pm-dev-frontend-cui](marketplace/bundles/pm-dev-frontend-cui/README.md) | CUI-specific JavaScript project standards covering Maven integration, Quarkus DevUI, NiFi, and SonarQube |
| [pm-dev-oci](marketplace/bundles/pm-dev-oci/README.md) | OCI container standards and security best practices |
| [pm-dev-python](marketplace/bundles/pm-dev-python/README.md) | Python domain extension with pyprojectx build operations |
| [pm-documents](marketplace/bundles/pm-documents/README.md) | AsciiDoc documentation standards |
| [pm-plugin-development](marketplace/bundles/pm-plugin-development/README.md) | Marketplace component development |
| [pm-requirements](marketplace/bundles/pm-requirements/README.md) | Requirements engineering standards |

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0-only)](LICENSE.md).

For organizations that cannot comply with the AGPL's copyleft requirements (e.g., proprietary or closed-source deployments), commercial licenses are available. [Request a commercial license](https://github.com/cuioss/plan-marshall/issues/new?template=commercial-licensing.yml).

## Support

- Report issues: https://github.com/cuioss/plan-marshall/issues
- Bundle documentation: `marketplace/bundles/*/README.md`
