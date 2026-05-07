"""Mock log-ingestor: emits clp.ingest.bytes_total and clp.ingest.records_total.

Mirrors the real log-ingestor (Rust) which increments these counters in
ClpIngestionState::ingest_s3_object_metadata every time objects are ingested.
The mock emits random increments every 5-15 seconds.
"""

import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.telemetry import init_telemetry, get_meter


def main():
    service_name = "log-ingestor"
    _provider = init_telemetry(service_name)
    meter = get_meter(service_name)

    bytes_counter = meter.create_counter(
        "clp.ingest.bytes_total",
        description="Total bytes ingested",
        unit="By",
    )
    records_counter = meter.create_counter(
        "clp.ingest.records_total",
        description="Total records ingested",
        unit="{records}",
    )

    print(f"[{service_name}] Telemetry initialized. Emitting random metrics...", flush=True)

    while True:
        # Simulate an ingestion batch: 1-50 S3 objects, each 100KB-50MB
        num_records = random.randint(1, 50)
        total_bytes = sum(random.randint(100_000, 50_000_000) for _ in range(num_records))

        bytes_counter.add(total_bytes, attributes={})
        records_counter.add(num_records, attributes={})

        print(
            f"[{service_name}] Ingested {num_records} records, {total_bytes / 1_000_000:.1f} MB",
            flush=True,
        )

        # Real log-ingestor ingests as S3 objects arrive; mock with random intervals.
        time.sleep(random.uniform(5, 15))


if __name__ == "__main__":
    main()
