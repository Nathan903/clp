import os
from typing import Optional

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Counter, ObservableGauge, MeterProvider, Meter
from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from clp_py_utils.clp_config import Telemetry

TELEMETRY_DISABLE_VALUES = ("1", "true", "yes", "y")


def init_telemetry(telemetry_config: Telemetry) -> Optional[MeterProvider]:
    """
    Initialize the OTel metrics pipeline.
    - Reads OTEL_RESOURCE_ATTRIBUTES and OTEL_SERVICE_NAME env vars automatically (SDK-native).
    - If telemetry.disable is true or CLP_DISABLE_TELEMETRY is set, returns a no-op MeterProvider (None here, or NoOp).
    - Configures the OTLP/HTTP exporter pointing at OTEL_EXPORTER_OTLP_ENDPOINT.
    - Returns the MeterProvider (caller stores it for the process lifetime).
    """
    if telemetry_config.disable or os.getenv("CLP_DISABLE_TELEMETRY", "").lower() in TELEMETRY_DISABLE_VALUES or os.getenv("DO_NOT_TRACK", "").lower() in TELEMETRY_DISABLE_VALUES:
        return None

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", telemetry_config.endpoint)
    
    # We explicitly let the SDK pull Resource attrs from env vars
    exporter = OTLPMetricExporter(endpoint=endpoint)
    reader = PeriodicExportingMetricReader(exporter)
    
    # The default Resource automatically includes attributes from OTEL_RESOURCE_ATTRIBUTES and OTEL_SERVICE_NAME
    provider = SdkMeterProvider(metric_readers=[reader], resource=Resource.create())
    metrics.set_meter_provider(provider)
    return provider


def init_telemetry_for_celery_worker(telemetry_config: Telemetry) -> None:
    """
    Initialize telemetry in a Celery worker process.
    Must be called from a worker_init signal handler (post-fork),
    NOT at import time. Celery prefork workers share state before
    the fork — initializing the SDK at import time produces duplicate
    and incorrect metrics.
    """
    init_telemetry(telemetry_config)


def shutdown_telemetry(provider: Optional[MeterProvider] = None) -> None:
    """Gracefully shut down the meter provider, flushing pending exports."""
    if isinstance(provider, SdkMeterProvider):
        provider.shutdown()
    else:
        # Try to shutdown the global provider if one wasn't passed explicitly
        p = metrics.get_meter_provider()
        if isinstance(p, SdkMeterProvider):
            p.shutdown()


def get_u64_counter(meter: Meter, name: str, description: str, unit: str = "") -> Counter:
    """Create a u64 counter on the given meter."""
    return meter.create_counter(name, description=description, unit=unit)


def get_f64_gauge(meter: Meter, name: str, description: str, unit: str = "") -> ObservableGauge:
    """Create an f64 observable gauge on the given meter."""
    # We will use the synchronous gauge if available, otherwise fallback.
    # The signature requested ObservableGauge but the use case implies we might set it synchronously.
    # OpenTelemetry python added synchronous Gauge recently.
    if hasattr(meter, "create_gauge"):
        return meter.create_gauge(name, description=description, unit=unit)
    return meter.create_observable_gauge(name, description=description, unit=unit)

