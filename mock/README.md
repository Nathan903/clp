# CLP Telemetry Mock Client

Mimics the CLP telemetry architecture from the server's perspective. The mock
sends the same OTLP/HTTP metric payloads (at the same 30-second export interval,
with the same resource attributes) so you can develop and test the server side
without running a full CLP deployment.

Two modes are available:

1. **Docker Compose** — runs separate containers for each CLP component and an
   OTel Collector, mirroring the real deployment architecture. This is the
   recommended mode for integration testing.

2. **Standalone script** — a single Python process that simulates all components.
   Useful for quick local testing without Docker.

## Metrics emitted

Each component creates its own `MeterProvider` with a `Resource` matching what
the real component would produce, and emits the same metrics:

| Component              | Metric                                    | Type    |
|------------------------|-------------------------------------------|---------|
| compression-scheduler  | `clp.deployment.compression_worker_count` | Gauge   |
| compression-worker     | `clp.compression.bytes_input_total`        | Counter |
| compression-worker     | `clp.compression.bytes_output_total`       | Counter |
| query-scheduler        | `clp.deployment.query_worker_count`        | Gauge   |
| query-scheduler        | `clp.deployment.reducer_count`             | Gauge   |
| query-worker           | `clp.query.bytes_scanned_total`            | Counter |
| query-worker           | `clp.query.bytes_output_total`             | Counter |
| log-ingestor           | `clp.ingest.bytes_total`                   | Counter |
| log-ingestor           | `clp.ingest.records_total`                 | Counter |

Every metric carries these resource attributes (matching real CLP):

```
service.name, clp.deployment.id, clp.version, clp.deployment.method,
clp.storage.engine, os.type, os.version, host.arch
```

## Docker Compose mode (recommended)

This mode mirrors the real CLP deployment architecture: each component runs in
its own container, all send metrics to an OTel Collector, and the collector
forwards them to the telemetry server.

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  log-ingestor    │  │ compression-worker│  │   query-worker   │
│  api-server      │  │ compression-sched │  │   query-sched    │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         │   OTLP/HTTP        │                      │
         ▼                     ▼                      ▼
   ┌──────────────────────────────────────────────────────┐
   │              Mock OTel Collector (:4318)              │
   └──────────────────────────┬───────────────────────────┘
                              │  OTLP/HTTP
                              ▼
                   ┌────────────────────┐
                   │  Telemetry Server  │
                   │  (host machine)    │
                   └────────────────────┘
```

### Start the mock

```bash
cd mock/
./start-mock.sh
```

The script generates a UUID instance ID on first run (stored in `var/instance-id`),
detects the host OS/arch, and starts all containers.

### Point at the telemetry server

By default, the mock OTel Collector forwards metrics to
`host.docker.internal:4318` (the host machine). If the telemetry server is
running elsewhere, set the environment variable before starting:

```bash
export TELEMETRY_SERVER_HOST=192.168.1.100
./start-mock.sh
```

### View logs

```bash
docker compose -f docker-compose.yaml logs -f
```

### Stop the mock

```bash
./stop-mock.sh
```

### Environment variable overrides

The mock containers read the same environment variables as the real CLP
components. Override them in `start-mock.sh` or export before running:

```bash
export CLP_VERSION=0.12.1
export CLP_DEPLOYMENT_METHOD=helm
export CLP_STORAGE_ENGINE=clp-s
export CLP_COMPRESSION_WORKER_COUNT=16
export CLP_QUERY_WORKER_COUNT=16
export CLP_REDUCER_COUNT=8
```

To disable telemetry (same consent mechanism as real CLP):

```bash
export CLP_DISABLE_TELEMETRY=true
```

## Standalone script mode

A single Python process that simulates all components. Useful for quick testing
without Docker.

### Quick start

```bash
cd mock/

# Create a venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run against a local OTel collector (default: http://localhost:4318)
python clp_telemetry_mock.py
```

### Options

```
  --endpoint URL         OTLP/HTTP endpoint (default: http://localhost:4318)
  --interval SECONDS     Export interval in seconds (default: 30)
  --instance-id UUID     CLP instance ID (default: random UUID)
  --list                 List simulated components and exit
```

### Environment variable overrides

The standalone script reads the same env vars as the real CLP components:

```bash
export CLP_VERSION=0.12.1
export CLP_DEPLOYMENT_METHOD=helm
export CLP_STORAGE_ENGINE=clp-s
export CLP_HOST_OS=ubuntu
export CLP_HOST_OS_VERSION=22.04
export CLP_HOST_ARCH=x86_64
export CLP_COMPRESSION_WORKER_COUNT=16
export CLP_QUERY_WORKER_COUNT=16
export CLP_REDUCER_COUNT=8
```

## Example: test against a local telemetry server

1. Start the telemetry server stack (see `../telemetry_server/README.md`).

2. Start the mock:

   **Docker mode:**
   ```bash
   ./start-mock.sh
   ```

   **Standalone mode:**
   ```bash
   python clp_telemetry_mock.py --endpoint http://localhost:4318
   ```

3. Open Grafana at http://localhost:3000 and query the `clp_` metrics.
