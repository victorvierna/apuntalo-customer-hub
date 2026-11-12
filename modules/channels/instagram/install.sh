#!/usr/bin/env bash
# Installs instagram-cli with the patches the Instagram adapter needs.
#
# Usage (from any folder):
#   modules/channels/instagram/install.sh
#
# Installs under ~/.local without sudo (~/.local/bin must be in the PATH).
# Another folder: INSTAGRAM_CLI_PREFIX=/some/folder modules/channels/instagram/install.sh
#
# Safe to run again, e.g. after reinstalling or updating instagram-cli (which
# removes our patch): it always ends with the patch applied, or fails loudly.
# See docs/modules/instagram.md.

set -euo pipefail

VERSION="2.1.0"
PREFIX="${INSTAGRAM_CLI_PREFIX:-$HOME/.local}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="$HERE/patches/instagram-private-api-send-fix.patch"
PACKAGE="$PREFIX/lib/node_modules/@i7m/instagram-cli"
LIBRARY="$PACKAGE/node_modules/instagram-private-api"
PATCHED_FILE="$LIBRARY/dist/repositories/direct-thread.repository.js"
MARKER="// apuntalo:"   # same marker the adapter looks for (send_patch.py)

fail() {
  echo "Error: $*" >&2
  exit 1
}

command -v node >/dev/null || fail "Node.js 22 or newer is required."
node_major="$(node -p 'process.versions.node.split(".")[0]')"
((node_major >= 22)) || fail "Node.js 22 or newer is required (found $(node --version))."
command -v npm >/dev/null || fail "npm is required."
command -v patch >/dev/null || fail "the 'patch' program is required."

echo "1/3 Installing @i7m/instagram-cli@$VERSION in $PREFIX"
npm install -g --prefix "$PREFIX" "@i7m/instagram-cli@$VERSION"

# Recent npm versions block the package's install script, which applies
# instagram-cli's own patches (one updates the Instagram app version it reports).
echo "2/3 Applying instagram-cli's own patches"
(cd "$PACKAGE" && npx --yes patch-package)

echo "3/3 Applying our send fix"
[[ -f "$PATCHED_FILE" ]] || fail "$PATCHED_FILE not found: instagram-cli changed, the patch must be redone."
if patch -p1 -R --dry-run -s -d "$LIBRARY" <"$PATCH_FILE" >/dev/null 2>&1; then
  echo "    already applied"
else
  patch -p1 -N -s -d "$LIBRARY" <"$PATCH_FILE" ||
    fail "the patch does not apply to this version. Check whether instagram-cli fixed the bug (#349) or redo the patch."
fi
grep -qF "$MARKER" "$PATCHED_FILE" || fail "the patch is not applied to $PATCHED_FILE."

echo "Done: instagram-cli $("$PREFIX/bin/instagram-cli" --version) with our send fix."
case ":$PATH:" in
  *":$PREFIX/bin:"*) ;;
  *) echo "Note: add $PREFIX/bin to your PATH." ;;
esac
