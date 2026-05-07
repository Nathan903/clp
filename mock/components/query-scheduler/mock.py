"""Mock query-scheduler: emits clp.deployment.query_worker_count and
clp.deployment.reducer_count gauges.

Mirrors the real query-scheduler (Python) which reads CLP_QUERY_WORKER_COUNT
and CLP_REDUCER_COUNT from the environment and emits observable gauges that
report the counts on each export cycle.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opentelemetry import metrics as otel_metrics

from common.telemetry import init_telemetry, get_meter

# Current gauge values — read by observable-gauge callbacks each export cycle.
_query_worker_count = int(os.environ.get("CLP_QUERY_WORKER_COUNT", "8"))
_reducer_count = int(os.environ.get("CLP_REDUCER_COUNT", "8"))


def _query_worker_count_callback(options):
    yield otel_metrics.Observation(_query_worker_count, attributes={})


def _reducer_count_callback(options):
    yield otel_metrics.Observation(_reducer_count, attributes={})


def main():
    service_name = "query-scheduler"
    _provider = init_telemetry(service_name)
    meter = get_meter(service_name)

    meter.create_observable_gauge(
        "clp.deployment.query_worker_count",
        callbacks=[_query_worker_count_callback],
        description="Number of query-worker instances",
        unit="{workers}",
    )

    meter.create_observable_gauge(
        "clp.deployment.reducer_count",
        callbacks=[_reducer_count_callback],
        description="Number of reducer instances",
        unit="{workers}",
    )

    print(
        f"[{service_name}] Telemetry initialized. "
        f"query_worker_count={_query_worker_count}, "
        f"reducer_count={_reducer_count}",
        flush=True,
    )

    # Keep running — the SDK exports metrics periodically (every 30s).
    import time
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
