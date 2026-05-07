"""Mock api-server: initializes OTel SDK (no specific metrics yet).

Mirrors the real api-server (Rust) which calls init_telemetry("api-server")
and holds a TelemetryGuard for the process lifetime. Currently the api-server
has no component-specific metrics, but it reports resource attributes.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.telemetry import init_telemetry


def main():
    service_name = "api-server"
    _provider = init_telemetry(service_name)

    print(f"[{service_name}] Telemetry initialized. Reporting resource attributes.", flush=True)

    # Keep running — the SDK exports metrics periodically (every 30s).
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
