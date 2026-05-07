"""Mock query-worker: emits clp.query.bytes_scanned_total and
clp.query.bytes_output_total.

Mirrors the real query-worker (Rust) which tracks bytes scanned and bytes
returned by queries. The mock emits random increments every 5-20s.
"""

import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.telemetry import init_telemetry, get_meter


def main():
    service_name = "query-worker"
    _provider = init_telemetry(service_name)
    meter = get_meter(service_name)

    scanned_counter = meter.create_counter(
        "clp.query.bytes_scanned_total",
        description="Total bytes scanned by queries",
        unit="By",
    )
    output_counter = meter.create_counter(
        "clp.query.bytes_output_total",
        description="Total bytes returned by queries",
        unit="By",
    )

    print(f"[{service_name}] Telemetry initialized. Emitting random metrics...", flush=True)

    while True:
        # Simulate a query: scan 1-100MB, return 1-10% of scanned bytes
        scanned_bytes = random.randint(1_000_000, 100_000_000)
        ratio = random.uniform(0.01, 0.10)
        output_bytes = int(scanned_bytes * ratio)

        scanned_counter.add(scanned_bytes, attributes={})
        output_counter.add(output_bytes, attributes={})

        print(
            f"[{service_name}] Scanned {scanned_bytes / 1_000_000:.1f} MB, "
            f"returned {output_bytes / 1_000:.1f} KB",
            flush=True,
        )

        time.sleep(random.uniform(5, 20))


if __name__ == "__main__":
    main()
