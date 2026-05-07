"""Mock compression-worker: emits clp.compression.bytes_input_total and
clp.compression.bytes_output_total.

Mirrors the real compression-worker (Rust) which tracks bytes compressed in
and bytes after compression. The mock emits random increments every 10-30s.
"""

import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.telemetry import init_telemetry, get_meter


def main():
    service_name = "compression-worker"
    _provider = init_telemetry(service_name)
    meter = get_meter(service_name)

    input_counter = meter.create_counter(
        "clp.compression.bytes_input_total",
        description="Total bytes compressed",
        unit="By",
    )
    output_counter = meter.create_counter(
        "clp.compression.bytes_output_total",
        description="Total bytes after compression",
        unit="By",
    )

    print(f"[{service_name}] Telemetry initialized. Emitting random metrics...", flush=True)

    while True:
        # Simulate compressing a batch: 10-500MB input, 20-60% compression ratio
        input_bytes = random.randint(10_000_000, 500_000_000)
        ratio = random.uniform(0.20, 0.60)
        output_bytes = int(input_bytes * ratio)

        input_counter.add(input_bytes, attributes={})
        output_counter.add(output_bytes, attributes={})

        print(
            f"[{service_name}] Compressed {input_bytes / 1_000_000:.1f} MB -> "
            f"{output_bytes / 1_000_000:.1f} MB (ratio={ratio:.2f})",
            flush=True,
        )

        time.sleep(random.uniform(10, 30))


if __name__ == "__main__":
    main()
