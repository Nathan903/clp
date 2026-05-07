# CLP Telemetry Server

A local OpenTelemetry stack for receiving, validating, storing, and
visualizing CLP deployment metrics.  Uses off-the-shelf components:
nginx, OTel Collector, ClickHouse, and Grafana.

## Architecture

```
CLP components (or mock)
        │
        │  OTLP/HTTP  (:4318)
        ▼
┌───────────────────┐
│   nginx           │  Payload-size limit (5 MB)
│                   │  Per-IP rate limiting (10 r/s)
└───────┬───────────┘
        │  OTLP/HTTP
        ▼
┌───────────────────┐
│  OTel Collector   │  Schema validation (clp.* namespace, required attrs)
│  (contrib 0.110)  │  Global rate limiting (100 items/s backstop)
│                   │  Batching (10s / 1024 items)
└───────┬───────────┘
        │  ClickHouse native protocol
        ▼
┌───────────────────┐
│   ClickHouse      │  Time-series storage (72h TTL, monthly partitions)
│   (24.8)          │  HTTP :8123  /  TCP :9000
└───────┬───────────┘
        │  SQL / HTTP
        ▼
┌───────────────────┐
│   Grafana         │  Dashboards & alerting
│   (11.4)          │  http://localhost:3000  (admin / admin)
└───────────────────┘
```

## Protections

| Layer            | Mechanism                     | Purpose                                           |
|------------------|-------------------------------|---------------------------------------------------|
| nginx            | `client_max_body_size 5m`    | Reject oversized payloads before they reach collector |
| nginx            | `limit_req_zone 10r/s`       | Per-IP rate limiting — one bad deployment can't flood |
| OTel Collector   | `max_request_body_size`       | Defense-in-depth payload limit (5 MiB)            |
| OTel Collector   | `filter/clp_namespace`        | Reject metrics outside `clp.*` namespace          |
| OTel Collector   | `filter/required_attrs`       | Reject metrics missing `clp.deployment.id` or `service.name` |
| OTel Collector   | `rate_limiting`               | Global backstop (100 items/s)                     |
| ClickHouse       | Table schema + materialized cols | Type enforcement; materialized columns for fast lookups |

## Quick start (testing / local development)

### 1. Start the server stack

```bash
cd telemetry_server/
docker compose up -d
```

Wait for all containers to become healthy:

```bash
docker compose ps
```

All four services (nginx, otel-collector, clickhouse, grafana) should show
`healthy` or `running`.

### 2. Send metrics from the mock

```bash
cd ../mock/
./start-mock.sh
```

The mock runs each CLP component in a separate Docker container.  Its OTel
Collector forwards metrics to `host.docker.internal:4318`, which reaches this
server's nginx.  See `../mock/README.md` for details.

Alternatively, use the standalone mock script (no Docker):

```bash
cd ../mock/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python clp_telemetry_mock.py --endpoint http://localhost:4318
```

### 3. Verify data is flowing

Check collector logs for `MetricData` entries:

```bash
docker compose logs otel-collector --tail 50
```

Query ClickHouse directly:

```bash
docker exec clp-clickhouse clickhouse-client \
  --query "SELECT metric_name, service_name, clp_deployment_id, value, time_unix_nano
           FROM otel.otel_metrics ORDER BY time_unix_nano DESC LIMIT 20"
```

### 4. View metrics in Grafana

Open http://localhost:3000 (login: `admin` / `admin`).

The ClickHouse datasource is auto-provisioned.  Create a dashboard with SQL
queries like:

```sql
-- Total bytes ingested by deployment
SELECT
  toStartOfMinute(toDateTime(time_unix_nano / 1e9)) AS minute,
  clp_deployment_id,
  sum(value) AS total_bytes
FROM otel.otel_metrics
WHERE metric_name = 'clp.ingest.bytes_total'
GROUP BY minute, clp_deployment_id
ORDER BY minute
```

```sql
-- Compression ratio over time
SELECT
  toStartOfMinute(toDateTime(time_unix_nano / 1e9)) AS minute,
  sumIf(value, metric_name = 'clp.compression.bytes_input_total') AS input,
  sumIf(value, metric_name = 'clp.compression.bytes_output_total') AS output,
  output / nullIf(input, 0) AS ratio
FROM otel.otel_metrics
WHERE metric_name IN ('clp.compression.bytes_input_total', 'clp.compression.bytes_output_total')
GROUP BY minute
ORDER BY minute
```

### 5. Stop the stack

```bash
docker compose down
```

To also delete stored data:

```bash
docker compose down -v
```

---

## Production deployment

The production CLP telemetry server is hosted at `telemetry.yscope.io:4318`
and runs a hardened OTel Collector behind TLS termination.  The source code
for that server lives in the
[clp-telemetry-server](https://github.com/y-scope/clp-telemetry-server) repo.

### Deploying your own production stack

1. **TLS**: Place nginx behind a reverse proxy (Caddy, cloud load balancer)
   that terminates TLS.  OTLP/HTTP requires HTTPS in production.

   Update nginx's `listen` directive:
   ```nginx
   listen 4318;
   # TLS is handled by the upstream reverse proxy or load balancer.
   ```

2. **ClickHouse credentials**: Set a real password:
   ```yaml
   # docker-compose.yaml
   clickhouse:
     environment:
       CLICKHOUSE_PASSWORD: "<your-strong-password>"

   # otel-collector-config.yaml
   exporters:
     clickhouse:
       password: "<your-strong-password>"
   ```

3. **ClickHouse retention**: Increase TTL for production data retention:
   ```sql
   -- In clickhouse/init.sql, change:
   TTL toDateTime(time_unix_nano / 1e9) + INTERVAL 90 DAY
   ```

4. **Secure Grafana**: Change the default admin password, enable OIDC/LDAP,
   and put Grafana behind your SSO.

5. **Override the endpoint** in your CLP deployment:
   ```yaml
   # Helm values.yaml
   clpConfig:
     telemetry:
       collector_endpoint: "https://your-collector:4318"
   ```
   ```bash
   # Docker Compose .env
   OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector:4318
   ```

6. **Reduce debug logging**: In `otel-collector-config.yaml`, either remove
   the `debug` exporter from the pipeline or set `verbosity: basic`.

---

## Configuration reference

### nginx (`nginx/nginx.conf`)

| Key                    | Default    | Description                              |
|------------------------|------------|------------------------------------------|
| client_max_body_size   | 5m         | Maximum OTLP/HTTP payload size           |
| limit_req_zone rate    | 10r/s      | Per-IP rate limit                        |
| limit_req burst        | 30         | Burst buffer before 429 responses        |

### OTel Collector (`otel-collector-config.yaml`)

| Section    | Key                         | Default           | Description                                    |
|------------|-----------------------------|-------------------|------------------------------------------------|
| receivers   | otlp.http.max_request_body_size | 5 MiB          | Defense-in-depth payload limit                 |
| processors  | filter/clp_namespace        | `clp\..*`         | Allowed metric namespace (regexp)             |
| processors  | filter/required_attrs       | deployment.id, service.name | Attributes that must be present       |
| processors  | rate_limiting.per_second    | 100               | Global pipeline throughput limit               |
| processors  | batch.timeout               | 10s                | Batching window                                |
| exporters   | clickhouse.endpoint         | tcp://clickhouse:9000 | ClickHouse connection                     |
| exporters   | clickhouse.ttl              | 72h                | Data retention in ClickHouse                  |
| exporters   | debug.verbosity             | detailed           | Log verbosity (use `basic` in production)     |

### ClickHouse (`clickhouse/init.sql`)

| Key                | Default                | Description                              |
|--------------------|------------------------|------------------------------------------|
| Database           | otel                   | Database for telemetry data              |
| Table              | otel_metrics           | Table for OTel metric data               |
| TTL                | 72 hours               | Auto-delete data older than 72h          |
| Partition          | Monthly (toYYYYMM)     | Partition by month for efficient queries  |
| Order key          | (metric, deployment, service, time) | Primary sort order for fast lookups |
| Materialized cols  | clp_deployment_id, service_name, clp_version | Fast-filter columns extracted from resource_attributes |

### Grafana

| Key             | Default    | Description                     |
|-----------------|------------|---------------------------------|
| Admin user      | admin      | Grafana login username          |
| Admin password  | admin      | Change this in production!      |
| Data source     | ClickHouse | Auto-provisioned at startup     |

---

## Troubleshooting

**No metrics appear in ClickHouse**

1. Check that the mock or CLP is sending to the right endpoint:
   `http://localhost:4318` (not `https` for local testing).
2. Check nginx logs: `docker compose logs nginx --tail 50`.
   Look for 429 (rate-limited) or 413 (payload too large) responses.
3. Check collector logs: `docker compose logs otel-collector --tail 50`.
   Look for filter/rate-limit messages or ClickHouse connection errors.
4. Check ClickHouse: `docker exec clp-clickhouse clickhouse-client
   --query "SELECT count() FROM otel.otel_metrics"`.
5. Wait 30–45 seconds — the export interval is 30s, plus batching.

**Port already in use**

```bash
# Find what's using port 4318
lsof -i :4318    # macOS/Linux
netstat -ano | findstr 4318   # Windows
```

**Collector fails to start**

Make sure `otel-collector-config.yaml` is valid YAML.  The collector will
refuse to start with a config error and log the problem to stdout.

**429 Too Many Requests in client logs**

The per-IP rate limit (10 r/s) is being exceeded.  This should not happen
with a normally configured CLP deployment (1 request per 30s).  Check that
the client is not re-sending in a tight retry loop.

**413 Payload Too Large**

The OTLP/HTTP batch exceeds 5 MB.  Reduce the batch size or export interval
on the client side.
