# Anonymous Telemetry via OpenTelemetry

## Overview

CLP collects anonymous operational metrics via OpenTelemetry (OTel) to help improve the software. This document describes the architecture, data flow, and implementation of the telemetry system.

## Goals

- Understand how much data CLP deployments are processing
- Measure compression efficiency across real-world workloads
- Gauge how actively CLP is being queried
- Correlate performance and usage patterns with deployment configurations
- Understand how users scale their deployments (replica counts, concurrency)
- Prioritize platform support and build target decisions

## Non-Goals

- Collecting log content, query content, or any personally identifiable information
- Per-tenant or per-dataset metrics (only aggregate counters per deployment)
- Tracking individual users or organizations

## Architecture

The telemetry system consists of three layers:

1. **Consent Layer** — Determines whether telemetry should be enabled
2. **Configuration Layer** — Passes telemetry settings and deployment info to all containers
3. **Instrumentation Layer** — Emits metrics from CLP components

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Environment                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │ CLP_DISABLE_    │    │ DO_NOT_TRACK    │    │ clp-config.yaml         │ │
│  │ TELEMETRY=true  │    │ =1              │    │ telemetry.disable: true │ │
│  └────────┬────────┘    └────────┬────────┘    └───────────┬─────────────┘ │
│           │                      │                         │               │
│           └──────────────────────┼─────────────────────────┘               │
│                                  ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     start-clp.sh / start_clp.py                       │  │
│  │  • Checks env vars (priority 1)                                       │  │
│  │  • Checks config file (priority 2)                                   │  │
│  │  • First-run interactive prompt (priority 3, persists to config)      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Docker Compose / Helm                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     controller.py                                     │  │
│  │  Writes env vars to .env (Docker Compose) or ConfigMap (Helm):        │  │
│  │  • CLP_INSTANCE_ID                                                    │  │
│  │  • CLP_VERSION                                                        │  │
│  │  • CLP_DEPLOYMENT_METHOD                                              │  │
│  │  • CLP_STORAGE_ENGINE                                                 │  │
│  │  • CLP_HOST_OS, CLP_HOST_OS_VERSION, CLP_HOST_ARCH                   │  │
│  │  • OTEL_EXPORTER_OTLP_ENDPOINT                                        │  │
│  │  • CLP_DISABLE_TELEMETRY / CLP_TELEMETRY_DEBUG (passthrough)         │  │
│  │  • CLP_COMPRESSION_WORKER_COUNT                                       │  │
│  │  • CLP_QUERY_WORKER_COUNT                                              │  │
│  │  • CLP_REDUCER_COUNT                                                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌───────────┐   │
│  │log-      │ │api-      │ │compression-  │ │query-worker │ │ ... other │   │
│  │ingestor  │ │server    │ │worker        │ │             │ │ containers│   │
│  │(Rust)    │ │(Rust)    │ │(Rust)        │ │(Rust)       │ │           │   │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └─────┬─────┘   │
│       │            │             │                │              │          │
│       └────────────┴─────────────┴────────────────┴──────────────┘          │
│                                    │                                         │
│                                    ▼ OTLP/HTTP                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              OpenTelemetry Collector (telemetry.yscope.io:4318)       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Configuration Schema

### Python (clp_py_utils.clp_config)

```python
class Telemetry(BaseModel):
    disable: bool | None = None
    collector_endpoint: str = "https://telemetry.yscope.io:4318"
```

### Rust (clp_rust_utils::clp_config::package)

```rust
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct Telemetry {
    pub disable: Option<bool>,
    pub collector_endpoint: String,
}

impl Default for Telemetry {
    fn default() -> Self {
        Self {
            disable: None,
            collector_endpoint: "https://telemetry.yscope.io:4318".to_owned(),
        }
    }
}
```

## Consent Priority Order

Telemetry is disabled if ANY of the following conditions are met, checked in this order:

1. **Environment variables**: `CLP_DISABLE_TELEMETRY=true` or `DO_NOT_TRACK=1`
2. **Config file**: `telemetry.disable: true` in `clp-config.yaml`
3. **First-run prompt**: Interactive terminal prompts user; answering `n` persists `telemetry.disable: true`

## Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `CLP_INSTANCE_ID` | Generated UUIDv4, stored in `$CLP_HOME/var/log/instance-id` | Deployment identifier for deduplication |
| `CLP_VERSION` | `$CLP_HOME/VERSION` file | CLP version string |
| `CLP_DEPLOYMENT_METHOD` | Controller | `docker-compose` or `helm` |
| `CLP_STORAGE_ENGINE` | Config | `clp` or `clp-s` |
| `CLP_HOST_OS` | start-clp.sh | Host OS (e.g., `ubuntu`) |
| `CLP_HOST_OS_VERSION` | start-clp.sh | Host OS version (e.g., `22.04`) |
| `CLP_HOST_ARCH` | start-clp.sh | Host architecture (e.g., `x86_64`, `aarch64`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Config | OTLP collector endpoint |
| `CLP_DISABLE_TELEMETRY` | Passthrough | Disables telemetry if `true` |
| `CLP_TELEMETRY_DEBUG` | Passthrough | Enables ConsoleExporter for debugging |
| `DO_NOT_TRACK` | Passthrough | Standard opt-out (treated same as `CLP_DISABLE_TELEMETRY`) |
| `CLP_COMPRESSION_WORKER_COUNT` | Controller | Number of compression-worker processes deployed |
| `CLP_QUERY_WORKER_COUNT` | Controller | Number of query-worker processes deployed |
| `CLP_REDUCER_COUNT` | Controller | Number of reducer processes deployed |

## Metrics

Each CLP component emits OpenTelemetry counters for its core operations:

| Component | Metric | Type | Description |
|-----------|--------|------|-------------|
| log-ingestor | `clp.ingest.bytes_total` | Counter | Total bytes ingested |
| log-ingestor | `clp.ingest.records_total` | Counter | Total records ingested |
| query-worker | `clp.query.bytes_scanned_total` | Counter | Total bytes scanned by queries |
| query-worker | `clp.query.bytes_output_total` | Counter | Total bytes returned by queries |
| compression-worker | `clp.compression.bytes_input_total` | Counter | Total bytes compressed |
| compression-worker | `clp.compression.bytes_output_total` | Counter | Total bytes after compression |

### Component Replica Counts

Each scheduler emits gauge metrics for the number of worker instances it manages. These are
deployment-topology metrics — they describe how the deployment is scaled, not individual process
throughput. Combined with the throughput counters above, they enable per-worker efficiency
analysis (e.g., bytes compressed per compression-worker).

| Emitting Component | Metric | Type | Description |
|--------------------|--------|------|-------------|
| compression-scheduler | `clp.deployment.compression_worker_count` | Gauge | Number of compression-worker instances |
| query-scheduler | `clp.deployment.query_worker_count` | Gauge | Number of query-worker instances |
| query-scheduler | `clp.deployment.reducer_count` | Gauge | Number of reducer instances |

Why the schedulers emit these: The schedulers are the natural owners of worker topology — they
dispatch work to workers and know how many are registered. For Docker Compose, the count equals
`replicas × concurrency` for each worker service (the controller writes this as
`CLP_*_WORKER_COUNT` in `.env`). For Helm, the scheduler reads the count from the
`CLP_*_WORKER_COUNT` environment variable injected by the chart from `values.yaml`.

The schedulers emit these gauges once at startup and re-emit whenever the set of registered
workers changes (e.g., during scale-out in Kubernetes).

## Resource Attributes

Every metric carries these resource attributes:

| Attribute | Example | Purpose |
|-----------|---------|---------|
| `clp.deployment.id` | `550e8400-e29b-41d4-a716-446655440000` | Deduplicate metrics from same deployment |
| `clp.version` | `0.9.1` | Track version adoption |
| `clp.deployment.method` | `docker-compose` or `helm` | Understand deployment preferences |
| `clp.storage.engine` | `clp-s` or `clp` | Track feature adoption |
| `os.type` | `linux` | Inform platform support |
| `os.version` | `ubuntu-22.04` | Inform platform support |
| `host.arch` | `x86_64`, `aarch64` | Inform build target priorities |
| `service.name` | `log-ingestor`, `query-worker`, etc. | Identify emitting component |

The `clp.deployment.id` is a random UUIDv4 generated on first run and stored locally at
`$CLP_HOME/var/log/instance-id`. It is never derived from hardware identifiers. One installation
directory equals one deployment ID. Separate `$CLP_HOME` directories on the same machine produce
separate IDs.

## What We Do NOT Collect

- **Log content or query content** — never, under any circumstances
- **Personally identifiable information** — no usernames, emails, or organization names
- **IP addresses** — visible during network communication but **not logged or stored** in the
  telemetry backend
- **Credentials and secrets** — no passwords, API keys, or connection strings
- **Hostnames** — no server or container hostnames
- **Local timezone** — all timestamps are UTC; no timezone information is collected as it could
  reveal geographic region
- **Per-tenant or per-dataset metrics** — only aggregate counters per deployment

## Telemetry Endpoint

Metrics are exported via the [OpenTelemetry Protocol
(OTLP)](https://opentelemetry.io/docs/specs/otlp/) to:

`https://telemetry.yscope.io:4318`

This is the standard OTLP/HTTP port. System administrators who do not want telemetry leaving their
network can block this endpoint at the firewall or proxy level.

## How to Disable Telemetry

Any **one** of the following methods is sufficient:

### Environment variable

```bash
export CLP_DISABLE_TELEMETRY=true
```

Or use the [Console Do Not Track](https://consoledonottrack.com/) standard:

```bash
export DO_NOT_TRACK=1
```

### Configuration file

Add to your `clp-config.yaml`:

```yaml
telemetry:
  disable: true
```

You can also override the collector endpoint:

```yaml
telemetry:
  disable: false
  collector_endpoint: "https://your-own-otel-collector:4318"
```

### First-run prompt

When running `start-clp.sh` for the first time in an interactive terminal, you will see a
consent prompt. Answering `n` will automatically set `telemetry.disable: true` in your config.

### Helm chart

Set in your `values.yaml`:

```yaml
clpConfig:
  telemetry:
    disable: true
```

### Network-level blocking

Block `telemetry.yscope.io` (port 4318) at your firewall or proxy. This is the simplest way to
disable telemetry for an entire organization.

### Interaction when multiple opt-out mechanisms are set

| Env var | Config file | First-run prompt | Network blocked | Telemetry sent? |
|---|---|---|---|---|
| not set | not set | Y (or default) | no | **Yes** |
| not set | not set | N | no | **No** — prompt wrote `telemetry.disable: true` to config |
| `true` | `false` | — | no | **No** — env var overrides config |
| `false` | `true` | — | no | **No** — config disables it |
| not set | `false` | — | **yes** | **No** — requests fail silently at the network level |
| `true` | `true` | — | no | **No** — both agree |
| not set | not set | Y | **yes** | **No** — network blocking is independent of software settings |

## Debug Mode

To inspect exactly what metrics would be sent without actually sending them:

```bash
export CLP_TELEMETRY_DEBUG=true
```

When enabled, each component uses an OpenTelemetry `ConsoleExporter` that prints metrics to its
standard output (visible in container logs) instead of transmitting them to the remote endpoint.

## Implementation Components

### start-clp.sh

The shell entrypoint performs host OS detection (parses `/etc/os-release`), architecture detection
(`uname -m`), and exports `CLP_HOST_OS`, `CLP_HOST_OS_VERSION`, `CLP_HOST_ARCH`. It then delegates
to `start_clp.py` for consent handling and service startup.

### start_clp.py

The Python script handles the consent layer: checks `CLP_DISABLE_TELEMETRY` and `DO_NOT_TRACK`
environment variables, checks `telemetry.disable` in config, runs the first-run interactive consent
prompt (with TTY detection), and persists consent choices to the config file via atomic tempfile
writes.

### controller.py

The orchestration controller generates the UUIDv4 instance ID on first run, reads the `VERSION`
file for `CLP_VERSION`, computes worker counts as `replicas × concurrency`, and writes all
telemetry and deployment-info env vars to `.env` so that every container receives them — not just
the API server.

### Rust components

Each instrumented component reads config from `.clp-config.yaml` (generated by the controller),
initializes the OTel SDK with resource attributes from environment variables, and creates meters
and counters for its operations. If `CLP_DISABLE_TELEMETRY=true`, it uses `NoopMeterProvider`. If
`CLP_TELEMETRY_DEBUG=true`, it uses `ConsoleExporter` instead of the OTLP exporter.

The schedulers additionally read `CLP_*_WORKER_COUNT` from their environment and emit the
corresponding gauge metrics for component replica counts.

## Source Code

The telemetry implementation is fully open source:

- **Component instrumentation**:
  [components/log-ingestor/](https://github.com/y-scope/clp/tree/DOCS_VAR_CLP_GIT_REF/components/log-ingestor/),
  [components/api-server/](https://github.com/y-scope/clp/tree/DOCS_VAR_CLP_GIT_REF/components/api-server/)
  (and other Rust components with `opentelemetry` in their `Cargo.toml`)
- **Consent prompt**:
  [components/clp-package-utils/clp_package_utils/scripts/start_clp.py](https://github.com/y-scope/clp/blob/DOCS_VAR_CLP_GIT_REF/components/clp-package-utils/clp_package_utils/scripts/start_clp.py)
- **Configuration**: `telemetry` section in `clp-config.yaml`
- **Server**:
  [clp-telemetry-server](https://github.com/y-scope/clp-telemetry-server)
