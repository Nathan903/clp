#!/usr/bin/env bash
# Mimics start-clp.sh: generates instance ID, sets env vars, and starts Docker Compose.
set -o errexit
set -o nounset
set -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# --- Generate instance ID on first run (mirrors controller.py) ---
instance_id_file="$script_dir/var/instance-id"
mkdir -p "$(dirname "$instance_id_file")"
if [[ ! -f "$instance_id_file" ]]; then
    instance_id="$(uuidgen | tr '[:upper:]' '[:lower:]')"
    echo "$instance_id" > "$instance_id_file"
    echo "Generated new instance ID: $instance_id"
else
    instance_id="$(cat "$instance_id_file")"
    echo "Using existing instance ID: $instance_id"
fi

# --- Host OS detection (mirrors start-clp.sh) ---
export CLP_HOST_OS
CLP_HOST_OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
export CLP_HOST_OS_VERSION
if [[ -f /etc/os-release ]]; then
    CLP_HOST_OS_VERSION="$(. /etc/os-release && echo "${ID:-unknown}-${VERSION_ID:-unknown}")"
else
    CLP_HOST_OS_VERSION="unknown"
fi
export CLP_HOST_ARCH
CLP_HOST_ARCH="$(uname -m)"

# --- Telemetry env vars (mirrors controller.py set_up_env) ---
export CLP_INSTANCE_ID="$instance_id"
export CLP_VERSION="0.12.1-mock"
export CLP_DEPLOYMENT_METHOD="docker-compose"
export CLP_STORAGE_ENGINE="clp-s"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"
export CLP_COMPRESSION_WORKER_COUNT="8"
export CLP_QUERY_WORKER_COUNT="8"
export CLP_REDUCER_COUNT="8"

# --- Consent passthrough (mirrors start-clp.sh) ---
# If set on the host, these will be picked up by Docker Compose.
# Unset by default so telemetry is enabled.

# --- Stop any previous run ---
docker compose -f "$script_dir/docker-compose.yaml" down --remove-orphans 2>/dev/null || true

# --- Start all mock components ---
echo "Starting mock CLP telemetry components..."
docker compose -f "$script_dir/docker-compose.yaml" up --build -d

echo ""
echo "Mock CLP is running. Telemetry is being emitted to the OTel Collector."
echo "  Instance ID: $CLP_INSTANCE_ID"
echo "  Collector:   $OTEL_EXPORTER_OTLP_ENDPOINT"
echo ""
echo "To view logs:  docker compose -f $script_dir/docker-compose.yaml logs -f"
echo "To stop:       $script_dir/stop-mock.sh"
