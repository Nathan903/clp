"""Mock compression-scheduler: emits clp.deployment.compression_worker_count gauge.

Mirrors the real compression-scheduler (Python) which reads
CLP_COMPRESSION_WORKER_COUNT from the environment and emits an observable gauge
that reports the worker count on each export cycle.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opentelemetry import metrics as otel_metrics

from common.telemetry import init_telemetry, get_meter

# Current gauge value — read by the observable-gauge callback each export cycle.
_worker_count = int(os.environ.get("CLP_COMPRESSION_WORKER_COUNT", "8"))


def _compression_worker_count_callback(options):
    yield otel_metrics.Observation(_worker_count, attributes={})


def main():
    service_name = "compression-scheduler"
    _provider = init_telemetry(service_name)
    meter = get_meter(service_name)

    meter.create_observable_gauge(
        "clp.deployment.compression_worker_count",
        callbacks=[_compression_worker_count_callback],
        description="Number of compression-worker instances",
        unit="{workers}",
    )

    print(
        f"[{service_name}] Telemetry initialized. "
        f"compression_worker_count={_worker_count}",
        flush=True,
    )

    # Keep running — the SDK exports metrics periodically (every 30s).
    import time
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
