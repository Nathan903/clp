# CLP Telemetry Server

This directory contains the server-side infrastructure for receiving and visualizing anonymous telemetry from CLP deployments.

## Architecture

* **OTel Collector**: Receives OTLP/HTTP metrics from client deployments and writes them to ClickHouse.
* **ClickHouse**: High-performance columnar database optimized for time-series and analytical queries.
* **Grafana**: Dashboard platform for visualizing metrics.
* **Caddy**: Reverse proxy that handles automatic TLS provisioning via Let's Encrypt.

## Setup

1. Configure your DNS to point `telemetry.yscope.io` to this server's IP address.
2. Ensure ports `80` and `443` are open on your firewall for Caddy to fetch certificates and serve traffic.
3. Start the stack:
   ```bash
   docker compose up -d
   ```

## Accessing Grafana

Once the stack is running, you can access Grafana at `http://<server-ip>:3000`.
* Default username: `admin`
* Default password: `admin` (You will be prompted to change it on first login).

The ClickHouse data source and a basic CLP Overview dashboard are provisioned automatically.
