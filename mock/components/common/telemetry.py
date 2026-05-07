"""Common telemetry utilities for mock CLP components.

Mirrors clp_py_utils.clp_telemetry: initializes the OTel SDK with the same
resource attributes, same consent checks, and same export interval (30s).
"""

import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# Same as the real CLP (clp-rust-utils/src/telemetry.rs, clp_py_utils/clp_telemetry.py).
METRIC_EXPORT_INTERVAL_SECONDS = 30
DEFAULT_OTEL_EXPORTER_OTLP_ENDPOINT = "https://telemetry.yscope.io:4318"


def is_telemetry_disabled() -> bool:
    val = os.environ.get("CLP_DISABLE_TELEMETRY", "").lower()
    if val in ("true", "1"):
        return True
    dnt = os.environ.get("DO_NOT_TRACK", "").lower()
    return dnt in ("1", "true", "yes")


def _build_resource(service_name: str) -> Resource:
    attributes = {
        "service.name": service_name,
        "clp.deployment.id": os.environ.get("CLP_INSTANCE_ID", "unknown"),
        "clp.version": os.environ.get("CLP_VERSION", "unknown"),
        "clp.deployment.method": os.environ.get("CLP_DEPLOYMENT_METHOD", "unknown"),
        "clp.storage.engine": os.environ.get("CLP_STORAGE_ENGINE", "unknown"),
        "os.type": os.environ.get("CLP_HOST_OS", "unknown"),
        "os.version": os.environ.get("CLP_HOST_OS_VERSION", "unknown"),
        "host.arch": os.environ.get("CLP_HOST_ARCH", "unknown"),
    }
    return Resource.create(attributes)


def init_telemetry(service_name: str) -> MeterProvider | None:
    """Initialize OTel SDK with the same logic as the real CLP components.

    - If CLP_DISABLE_TELEMETRY=true or DO_NOT_TRACK=1: no-op (telemetry off)
    - Otherwise: export via OTLP/HTTP to OTEL_EXPORTER_OTLP_ENDPOINT every 30s
    """
    if is_telemetry_disabled():
        metrics.set_meter_provider(metrics.NoOpMeterProvider())
        return None

    resource = _build_resource(service_name)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTEL_EXPORTER_OTLP_ENDPOINT)
    metrics_endpoint = endpoint.rstrip("/") + "/v1/metrics"

    exporter = OTLPMetricExporter(endpoint=metrics_endpoint)
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=METRIC_EXPORT_INTERVAL_SECONDS * 1000,
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


def get_meter(name: str) -> metrics.Meter:
    return metrics.get_meter(name)
