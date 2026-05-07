#!/usr/bin/env python3
"""
CLP Telemetry Mock Client

Mimics all instrumented CLP components from the telemetry server's perspective.
Each simulated component:

- Initializes its own OTel MeterProvider with the same resource attributes
  the real component would set (service.name, clp.deployment.id, etc.)
- Emits the same counters and gauges at the same 30-second export interval
- Sends random but realistic values so the server sees identical metric payloads

Usage:
    python clp_telemetry_mock.py [--endpoint URL] [--interval SECONDS] [--list]

Components simulated:
    - compression-scheduler  (gauge:  clp.deployment.compression_worker_count)
    - compression-worker    (counter: clp.compression.bytes_input_total,
                                       clp.compression.bytes_output_total)
    - query-scheduler       (gauge:  clp.deployment.query_worker_count,
                                       clp.deployment.reducer_count)
    - query-worker          (counter: clp.query.bytes_scanned_total,
                                       clp.query.bytes_output_total)
    - log-ingestor          (counter: clp.ingest.bytes_total,
                                       clp.ingest.records_total)
"""

from __future__ import annotations

import argparse
import os
import random
import signal
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# ---------------------------------------------------------------------------
# Constants — must match the real CLP components
# ---------------------------------------------------------------------------

DEFAULT_EXPORT_INTERVAL_S = 30
DEFAULT_ENDPOINT = "http://localhost:4318"


# ---------------------------------------------------------------------------
# Resource builder — mirrors clp_rust_utils::telemetry::build_resource
# ---------------------------------------------------------------------------


def _build_resource(service_name: str, instance_id: str) -> Resource:
    """Build an OTel Resource that matches what real CLP components produce."""
    return Resource.create(
        {
            "service.name": service_name,
            "clp.deployment.id": instance_id,
            "clp.version": os.environ.get("CLP_VERSION", "0.12.1-dev"),
            "clp.deployment.method": os.environ.get("CLP_DEPLOYMENT_METHOD", "docker-compose"),
            "clp.storage.engine": os.environ.get("CLP_STORAGE_ENGINE", "clp-s"),
            "os.type": os.environ.get("CLP_HOST_OS", "ubuntu"),
            "os.version": os.environ.get("CLP_HOST_OS_VERSION", "22.04"),
            "host.arch": os.environ.get("CLP_HOST_ARCH", "x86_64"),
        }
    )


# ---------------------------------------------------------------------------
# Meter provider factory — mirrors clp_rust_utils::telemetry::init_telemetry
# ---------------------------------------------------------------------------


def _create_meter_provider(
    service_name: str, instance_id: str, endpoint: str, interval_s: int
) -> MeterProvider:
    metrics_endpoint = endpoint.rstrip("/") + "/v1/metrics"
    exporter = OTLPMetricExporter(endpoint=metrics_endpoint)
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=interval_s * 1000
    )
    resource = _build_resource(service_name, instance_id)
    return MeterProvider(resource=resource, metric_readers=[reader])


# ---------------------------------------------------------------------------
# Shared mutable state for gauge callbacks
# ---------------------------------------------------------------------------

# Observable gauges in the Python SDK use a callback that is invoked each
# export cycle.  We store the current values in a dict so the callbacks can
# read them.
_gauge_values: dict[str, int] = {}


def _make_gauge_callback(metric_name: str):
    """Returns an observable-gauge callback that reads from _gauge_values."""

    def _callback(options):
        val = _gauge_values.get(metric_name, 0)
        yield metrics.Observation(val, attributes={})

    return _callback


# ---------------------------------------------------------------------------
# Component definitions
# ---------------------------------------------------------------------------


@dataclass
class Component:
    """A simulated CLP component that emits metrics."""

    service_name: str
    setup: Any  # callable(meter) -> None; creates instruments once


def _setup_compression_scheduler(meter: metrics.Meter) -> None:
    """Compression scheduler — emits worker-count gauge."""
    count = int(os.environ.get("CLP_COMPRESSION_WORKER_COUNT", "8"))
    _gauge_values["clp.deployment.compression_worker_count"] = count
    meter.create_observable_gauge(
        "clp.deployment.compression_worker_count",
        callbacks=[_make_gauge_callback("clp.deployment.compression_worker_count")],
        description="Number of compression-worker instances",
        unit="{workers}",
    )


def _setup_compression_worker(meter: metrics.Meter) -> None:
    """Compression worker — emits byte counters periodically."""
    meter._mock_bytes_input = meter.create_counter(  # type: ignore[attr-defined]
        "clp.compression.bytes_input_total",
        description="Total bytes compressed",
        unit="By",
    )
    meter._mock_bytes_output = meter.create_counter(  # type: ignore[attr-defined]
        "clp.compression.bytes_output_total",
        description="Total bytes after compression",
        unit="By",
    )


def _setup_query_scheduler(meter: metrics.Meter) -> None:
    """Query scheduler — emits worker-count gauges."""
    qw_count = int(os.environ.get("CLP_QUERY_WORKER_COUNT", "8"))
    r_count = int(os.environ.get("CLP_REDUCER_COUNT", "8"))
    _gauge_values["clp.deployment.query_worker_count"] = qw_count
    _gauge_values["clp.deployment.reducer_count"] = r_count
    meter.create_observable_gauge(
        "clp.deployment.query_worker_count",
        callbacks=[_make_gauge_callback("clp.deployment.query_worker_count")],
        description="Number of query-worker instances",
        unit="{workers}",
    )
    meter.create_observable_gauge(
        "clp.deployment.reducer_count",
        callbacks=[_make_gauge_callback("clp.deployment.reducer_count")],
        description="Number of reducer instances",
        unit="{workers}",
    )


def _setup_query_worker(meter: metrics.Meter) -> None:
    """Query worker — emits byte counters periodically."""
    meter._mock_bytes_scanned = meter.create_counter(  # type: ignore[attr-defined]
        "clp.query.bytes_scanned_total",
        description="Total bytes scanned by queries",
        unit="By",
    )
    meter._mock_bytes_output = meter.create_counter(  # type: ignore[attr-defined]
        "clp.query.bytes_output_total",
        description="Total bytes returned by queries",
        unit="By",
    )


def _setup_log_ingestor(meter: metrics.Meter) -> None:
    """Log ingestor — emits byte and record counters periodically."""
    meter._mock_ingest_bytes = meter.create_counter(  # type: ignore[attr-defined]
        "clp.ingest.bytes_total",
        description="Total bytes ingested",
        unit="By",
    )
    meter._mock_ingest_records = meter.create_counter(  # type: ignore[attr-defined]
        "clp.ingest.records_total",
        description="Total records ingested",
        unit="{records}",
    )


# The full list of components to simulate.
COMPONENTS = [
    Component("compression-scheduler", _setup_compression_scheduler),
    Component("compression-worker", _setup_compression_worker),
    Component("query-scheduler", _setup_query_scheduler),
    Component("query-worker", _setup_query_worker),
    Component("log-ingestor", _setup_log_ingestor),
]


# ---------------------------------------------------------------------------
# Periodic counter ticks — simulate throughput between export intervals
# ---------------------------------------------------------------------------

# Realistic ranges for random counter increments per tick.
# These are per-tick deltas, not absolute values.  A typical compression
# worker processes ~100 MB–1 GB per 30-second interval; we use conservative
# ranges so the numbers look realistic on a small deployment.

_TICK_RANGES = {
    "compression-worker": {
        "bytes_input": (10 * 1024 * 1024, 200 * 1024 * 1024),   # 10–200 MB
        "bytes_output": (1 * 1024 * 1024, 30 * 1024 * 1024),    # 1–30 MB
    },
    "query-worker": {
        "bytes_scanned": (50 * 1024 * 1024, 500 * 1024 * 1024), # 50–500 MB
        "bytes_output": (100 * 1024, 10 * 1024 * 1024),          # 100 KB–10 MB
    },
    "log-ingestor": {
        "ingest_bytes": (5 * 1024 * 1024, 100 * 1024 * 1024),   # 5–100 MB
        "ingest_records": (1000, 50000),                          # 1k–50k records
    },
}


def _tick_counter(meter: metrics.Meter, service_name: str) -> None:
    """Add a random delta to each counter for the given component."""
    rng = _TICK_RANGES.get(service_name, {})
    if not rng:
        return

    if service_name == "compression-worker":
        lo, hi = rng["bytes_input"]
        meter._mock_bytes_input.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]
        lo, hi = rng["bytes_output"]
        meter._mock_bytes_output.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]

    elif service_name == "query-worker":
        lo, hi = rng["bytes_scanned"]
        meter._mock_bytes_scanned.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]
        lo, hi = rng["bytes_output"]
        meter._mock_bytes_output.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]

    elif service_name == "log-ingestor":
        lo, hi = rng["ingest_bytes"]
        meter._mock_ingest_bytes.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]
        lo, hi = rng["ingest_records"]
        meter._mock_ingest_records.add(random.randint(lo, hi), attributes={})  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CLP telemetry mock — sends the same OTel metrics as a real CLP deployment"
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"OTLP/HTTP endpoint (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_EXPORT_INTERVAL_S,
        help=f"Export interval in seconds (default: {DEFAULT_EXPORT_INTERVAL_S})",
    )
    parser.add_argument(
        "--instance-id",
        default=None,
        help="CLP instance ID (default: random UUID)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the simulated components and exit",
    )
    args = parser.parse_args()

    if args.list:
        for comp in COMPONENTS:
            print(f"  {comp.service_name}")
        return 0

    instance_id = args.instance_id or str(uuid.uuid4())
    interval_s = args.interval

    print(f"CLP Telemetry Mock")
    print(f"  Instance ID : {instance_id}")
    print(f"  Endpoint    : {args.endpoint}")
    print(f"  Interval    : {interval_s}s")
    print()

    # --- Create one MeterProvider per component (just like real containers) ---
    providers: list[MeterProvider] = []
    meters: dict[str, metrics.Meter] = {}

    for comp in COMPONENTS:
        provider = _create_meter_provider(
            comp.service_name, instance_id, args.endpoint, interval_s
        )
        meter = provider.get_meter(comp.service_name)
        comp.setup(meter)
        providers.append(provider)
        meters[comp.service_name] = meter
        print(f"  Started {comp.service_name}")

    # Gauge-only components (schedulers) don't need periodic ticks — their
    # observable-gauge callbacks are invoked each export cycle by the reader.
    # Counter components need tick increments.
    counter_components = [
        "compression-worker",
        "query-worker",
        "log-ingestor",
    ]

    # --- Shutdown flag ---
    stop = threading.Event()

    def _signal_handler(signum, frame):
        print("\nShutting down...")
        stop.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # --- Tick loop ---
    print(f"\nEmitting counter increments every {interval_s}s.  Press Ctrl-C to stop.\n")
    while not stop.is_set():
        stop.wait(timeout=interval_s)
        if stop.is_set():
            break
        for name in counter_components:
            _tick_counter(meters[name], name)
        print(f"  [{time.strftime('%H:%M:%S')}] tick — counters incremented")

    # --- Shutdown: flush and close ---
    print("Flushing metrics...")
    for provider in providers:
        provider.shutdown()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
