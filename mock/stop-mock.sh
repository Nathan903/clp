#!/usr/bin/env bash
# Stops the mock CLP telemetry components.
set -o errexit
set -o nounset

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
echo "Stopping mock CLP telemetry components..."
docker compose -f "$script_dir/docker-compose.yaml" down --remove-orphans
echo "Stopped."
