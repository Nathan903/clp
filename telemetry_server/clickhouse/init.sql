-- ClickHouse init script for the CLP telemetry server.
--
-- Creates the otel database and the otel_metrics table.
-- The OTel Collector's ClickHouse exporter can auto-create the table
-- (create_schema: true in otel-collector-config.yaml), but an explicit
-- schema gives us:
--   - Strong type enforcement (schema validation at the database level)
--   - Materialized columns for fast lookups on resource attributes
--   - Appropriate TTL and partitioning for time-series data

CREATE DATABASE IF NOT EXISTS otel;

CREATE TABLE IF NOT EXISTS otel.otel_metrics
(
    -- Metric identity
    metric_name       LowCardinality(String),
    metric_type       LowCardinality(String),
    metric_unit       Nullable(String),
    metric_description Nullable(String),

    -- Time
    start_time_unix_nano UInt64,
    time_unix_nano     UInt64,

    -- Value (covers Gauge, Counter, Summary, Histogram)
    value              Float64,

    -- Flags (e.g., exemplar, zero-value)
    flags              UInt32,

    -- OTel attributes (stored as a Map for flexibility)
    attributes         Map(String, String),

    -- Resource attributes (the deployment/service metadata)
    resource_attributes Map(String, String),

    -- Materialized columns for fast filtering on required fields.
    -- These also act as schema enforcement: if a metric is missing
    -- clp.deployment.id or service.name, the materialized column will
    -- be empty, making it easy to spot and query for invalid data.
    clp_deployment_id  LowCardinality(String) MATERIALIZED resource_attributes['clp.deployment.id'],
    service_name       LowCardinality(String) MATERIALIZED resource_attributes['service.name'],
    clp_version        LowCardinality(String) MATERIALIZED resource_attributes['clp.version'],

    -- Instrumentation scope
    scope_name         String,
    scope_version      String,
    scope_attributes   Map(String, String)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(toDateTime(time_unix_nano / 1e9))
ORDER BY (metric_name, clp_deployment_id, service_name, time_unix_nano)
TTL toDateTime(time_unix_nano / 1e9) + INTERVAL 72 HOUR
SETTINGS index_granularity = 8192;
