#!/usr/bin/env bash
# Invoked ONLY via the forced command on the ql-server-ci SSH key (see authorized_keys).
# Pulls the latest config from git and applies it. Does not fetch new game files
# (that stays a manual "./deploy.sh --update" step, or add fetch-qlds.yml on its own schedule).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
git pull --ff-only
./deploy.sh
