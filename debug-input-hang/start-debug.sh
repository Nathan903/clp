#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Mimic .common-env.sh — set up the Docker image ref and interactivity flags
# shellcheck source=.common-env.sh
source "$script_dir/.common-env.sh"

docker compose -f "$script_dir/docker-compose.debug.yaml" \
    run --rm "${CLP_COMPOSE_RUN_EXTRA_FLAGS[@]}" debug-runtime \
    python3 -m debug_input.main \
    "$@"
