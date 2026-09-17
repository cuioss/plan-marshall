#!/usr/bin/env bash
# SPDX-License-Identifier: FSL-1.1-ALv2
set -euo pipefail

REPO="cuioss/plan-marshall"
DEFAULT_REF="dist-opencode"
DEFAULT_GLOBAL_DIR="${HOME}/.config/opencode"
DEFAULT_WORKSPACE_DIR="${PWD}/.opencode"

SCOPE="global"
TARGET_DIR=""
REF="${DEFAULT_REF}"
UNINSTALL=false

show_help() {
  cat <<'EOF'
Plan Marshall - OpenCode Component Installer

Usage:
  curl -fsSL https://raw.githubusercontent.com/cuioss/plan-marshall/dist-opencode/install.sh | bash
  ./install.sh [OPTIONS]

Options:
  -g, --global           Install globally to ~/.config/opencode (default)
  -w, --workspace        Install locally to <cwd>/.opencode
  -t, --target-dir PATH  Install to a custom directory
  -r, --ref REF          Branch or tag to install (default: dist-opencode)
  -u, --uninstall        Remove only Plan Marshall components
  -h, --help             Show this help message
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -g|--global)
      SCOPE="global"
      shift
      ;;
    -w|--workspace)
      SCOPE="workspace"
      shift
      ;;
    -t|--target-dir)
      if [ -z "${2:-}" ]; then
        echo "Error: --target-dir requires an argument" >&2
        exit 1
      fi
      TARGET_DIR="$2"
      shift 2
      ;;
    -r|--ref)
      if [ -z "${2:-}" ]; then
        echo "Error: --ref requires an argument" >&2
        exit 1
      fi
      REF="$2"
      shift 2
      ;;
    -u|--uninstall)
      UNINSTALL=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help >&2
      exit 1
      ;;
  esac
done

if [ -z "$TARGET_DIR" ]; then
  if [ "$SCOPE" = "workspace" ]; then
    TARGET_DIR="${DEFAULT_WORKSPACE_DIR}"
  else
    TARGET_DIR="${DEFAULT_GLOBAL_DIR}"
  fi
fi

prune_managed_components() {
  local base_dir="$1"
  if [ -d "${base_dir}/skills" ]; then
    for d in "${base_dir}/skills"/plan-marshall*; do
      if [ -d "$d" ]; then
        rm -rf "$d"
      fi
    done
  fi
  if [ -d "${base_dir}/agents" ]; then
    for f in "${base_dir}/agents"/plan-marshall*; do
      if [ -e "$f" ]; then
        rm -rf "$f"
      fi
    done
  fi
  if [ -d "${base_dir}/commands" ]; then
    for f in "${base_dir}/commands"/plan-marshall*; do
      if [ -e "$f" ]; then
        rm -rf "$f"
      fi
    done
  fi
}

if [ "$UNINSTALL" = true ]; then
  if [ -d "$TARGET_DIR" ]; then
    echo "Uninstalling Plan Marshall components from: $TARGET_DIR"
    prune_managed_components "$TARGET_DIR"
    echo "Plan Marshall components uninstalled cleanly (non-Plan Marshall components preserved)."
  else
    echo "No directory found at: $TARGET_DIR"
  fi
  exit 0
fi

# Detect whether running locally or remotely
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

CLEANUP_TMP=false
TMP_DIR=""

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/opencode.json" ] && [ -d "$SCRIPT_DIR/skill" ]; then
  SOURCE_DIR="$SCRIPT_DIR"
  echo "Installing Plan Marshall OpenCode components from local source: $SOURCE_DIR"
else
  TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'plan-marshall-opencode')"
  CLEANUP_TMP=true
  trap 'if [ "$CLEANUP_TMP" = true ] && [ -d "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi' EXIT

  if [[ "$REF" =~ ^v[0-9] ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/opencode/${REF}.tar.gz"
  elif [[ "$REF" =~ ^opencode/v ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/${REF}.tar.gz"
  else
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${REF}.tar.gz"
  fi

  echo "Downloading Plan Marshall (${REF}) from ${ARCHIVE_URL}..."
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR" --strip-components=1
  SOURCE_DIR="$TMP_DIR"
fi

if [ ! -f "$SOURCE_DIR/opencode.json" ]; then
  echo "Error: opencode.json not found in source directory ($SOURCE_DIR)." >&2
  exit 1
fi

echo "Installing OpenCode components to: $TARGET_DIR"
mkdir -p "${TARGET_DIR}/skills"
mkdir -p "${TARGET_DIR}/agents"
mkdir -p "${TARGET_DIR}/commands"

# Clean prior managed components before installing new version
prune_managed_components "$TARGET_DIR"

# Singular-to-plural mapping: skill/ -> skills/, agent/ -> agents/, command/ -> commands/
if [ -d "$SOURCE_DIR/skill" ]; then
  for item in "$SOURCE_DIR/skill"/*; do
    if [ -d "$item" ]; then
      cp -R "$item" "${TARGET_DIR}/skills/"
    fi
  done
fi

if [ -d "$SOURCE_DIR/agent" ]; then
  for item in "$SOURCE_DIR/agent"/*; do
    if [ -f "$item" ]; then
      cp "$item" "${TARGET_DIR}/agents/"
    fi
  done
fi

if [ -d "$SOURCE_DIR/command" ]; then
  for item in "$SOURCE_DIR/command"/*; do
    if [ -f "$item" ]; then
      cp "$item" "${TARGET_DIR}/commands/"
    fi
  done
fi

if [ -f "$SOURCE_DIR/README.adoc" ]; then
  cp "$SOURCE_DIR/README.adoc" "${TARGET_DIR}/plan-marshall-README.adoc"
fi

echo "Plan Marshall OpenCode components successfully installed to: $TARGET_DIR"
echo ""
echo "OpenCode discovers skills, agents, and commands in ${TARGET_DIR} automatically."
