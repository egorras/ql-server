#!/usr/bin/env bash
# Publish (or update) a custom map pk3 as a Steam Workshop item for Quake Live (appid 282440).
#
# Why this exists: this QLDS build has zero download cvars (see config/workshop-maps.md) —
# Steam Workshop is the *only* way to get new map content onto a real player's client. And
# the dedicated server box itself can't run SteamCMD at all (ARM64, see top-level README) —
# so publishing has to happen from an x86_64 machine with SteamCMD and a Steam login.
#
# One-time setup: log in interactively once so SteamCMD caches the session next to the
# binary (its config/ dir) — you'll need this again whenever the cached login expires:
#   steamcmd.exe +login <your_steam_username> +quit
#
# Usage (run from Git Bash / any POSIX-ish shell that has `unzip` and `cygpath`):
#   STEAMCMD=/c/path/to/steamcmd.exe STEAM_USER=<your_steam_username> \
#     ./publish.sh <pk3 path> "<title>" "<description>" [existing published_file_id]
#
# Omit the 4th argument to create a brand-new Workshop item (prints the new item's
# published file ID on success — add it to config/workshop.txt). Pass it to push an
# update to an item this script (or you) already created.
set -euo pipefail

PK3="${1:?usage: publish.sh <pk3 path> <title> <description> [published_file_id]}"
TITLE="${2:?title required}"
DESCRIPTION="${3:?description required}"
PUBLISHED_FILE_ID="${4:-}"

: "${STEAMCMD:?Set STEAMCMD to the path of steamcmd(.exe)}"
: "${STEAM_USER:?Set STEAM_USER to your Steam login name}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

CONTENT_DIR="$WORKDIR/content"
mkdir -p "$CONTENT_DIR"
cp "$PK3" "$CONTENT_DIR/"

PREVIEW="$WORKDIR/preview.jpg"
# Prefer the full-size levelshot over the smaller levelshots/preview/ thumbnail.
PREVIEW_ENTRY="$(unzip -Z1 "$PK3" 2>/dev/null | grep -iE '^levelshots/[^/]+\.jpg$' | head -1)"
if [ -z "$PREVIEW_ENTRY" ]; then
  echo "No top-level levelshots/*.jpg found in $PK3 — drop a preview.jpg into $WORKDIR yourself and re-run, or edit this script." >&2
  exit 1
fi
unzip -p "$PK3" "$PREVIEW_ENTRY" > "$PREVIEW"

VDF="$WORKDIR/item.vdf"
sed \
  -e "s|{{CONTENT_FOLDER}}|$(cygpath -w "$CONTENT_DIR" | sed 's/\\/\\\\/g')|g" \
  -e "s|{{PREVIEW_FILE}}|$(cygpath -w "$PREVIEW" | sed 's/\\/\\\\/g')|g" \
  -e "s|{{TITLE}}|$TITLE|g" \
  -e "s|{{DESCRIPTION}}|$DESCRIPTION|g" \
  -e "s|{{CHANGENOTE}}|$([ -n "$PUBLISHED_FILE_ID" ] && echo "Update via publish.sh" || echo "Initial upload")|g" \
  "$SCRIPT_DIR/item.vdf.template" > "$VDF"

if [ -n "$PUBLISHED_FILE_ID" ]; then
  sed -i "s|{{PUBLISHED_FILE_ID}}|$PUBLISHED_FILE_ID|g" "$VDF"
else
  sed -i '/{{PUBLISHED_FILE_ID}}/d' "$VDF"
fi

echo "==> Content: $PK3"
echo "==> Preview: $PREVIEW_ENTRY"
if [ -n "$PUBLISHED_FILE_ID" ]; then
  echo "==> Updating item $PUBLISHED_FILE_ID"
else
  echo "==> Creating new item"
fi
"$STEAMCMD" +login "$STEAM_USER" +workshop_build_item "$(cygpath -w "$VDF")" +quit
