CREATE DATABASE IF NOT EXISTS clp_telemetry;

CREATE TABLE IF NOT EXISTS clp_telemetry.otel_metrics
(
    timestamp DateTime64(9),
    metric_name String,
    metric_type String,
    value Float64,
    attributes Map(String, String),
    resource_attributes Map(String, String),
    service_name String MATERIALIZED resource_attributes['service.name'],
    deployment_id String MATERIALIZED resource_attributes['clp.deployment.id'],
    service_version String MATERIALIZED resource_attributes['service.version'],
    storage_engine String MATERIALIZED resource_attributes['clp.storage.engine']
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (deployment_id, service_name, metric_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY;
