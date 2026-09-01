#!/usr/bin/env bash
# Usage:
#   ./deploy.sh            fast path: just apply config/ and restart the service
#   ./deploy.sh --update   fetch the latest QLDS build from GitHub Actions first, then apply config/ and restart
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$HOME/ql-server-data"
QLDS_DIR="$DATA_DIR/qlds"

UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

if [ ! -d "$QLDS_DIR" ] || [ "$UPDATE" = "1" ]; then
  echo "==> Finding latest successful QLDS build"
  RUN_ID=$(gh run list --workflow=fetch-qlds.yml --status success --limit 1 --json databaseId -q '.[0].databaseId')
  if [ -z "$RUN_ID" ]; then
    echo "No successful fetch-qlds run found. Run: gh workflow run fetch-qlds.yml"
    exit 1
  fi
  echo "    using run $RUN_ID"

  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT
  gh run download "$RUN_ID" -n qlds -D "$TMP_DIR"

  echo "==> Stopping service (if running)"
  sudo systemctl stop qlds 2>/dev/null || true

  echo "==> Installing server files to $QLDS_DIR"
  mkdir -p "$DATA_DIR"
  rm -rf "$QLDS_DIR"
  tar xzf "$TMP_DIR/qlds.tar.gz" -C "$DATA_DIR"
else
  echo "==> QLDS already installed at $QLDS_DIR, skipping download (use --update to fetch fresh game files)"
fi

echo "==> Applying config overlay from repo"
cp "$REPO_DIR/config/server.cfg" "$QLDS_DIR/baseq3/server.cfg"
cp "$REPO_DIR/config/access.txt" "$QLDS_DIR/baseq3/access.txt"
cp "$REPO_DIR/config/workshop.txt" "$QLDS_DIR/baseq3/workshop.txt"
cp "$REPO_DIR/config/mappool.txt" "$QLDS_DIR/baseq3/mappool.txt"

echo "==> Installing systemd unit"
sudo cp "$REPO_DIR/systemd/qlds.service" /etc/systemd/system/qlds.service
sudo systemctl daemon-reload
sudo systemctl restart qlds
sudo systemctl enable qlds >/dev/null

echo "==> Done. Status:"
sleep 2
systemctl status qlds --no-pager -l | head -15
