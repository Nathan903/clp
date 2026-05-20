# Telemetry Guide for Developers

This guide explains how to add new OpenTelemetry metrics to CLP components.

## Adding a New Metric

1. **Define the metric**:
   - Determine the name (e.g., `clp.component.metric_name`).
   - Determine the type (Counter, UpDownCounter, Gauge, Histogram).
   - Determine the description and unit.
   - Decide which service emits it.

2. **Add the counter/gauge in the service's init code**:
   - **Python**: Use `clp_py_utils.telemetry`.
     ```python
     from opentelemetry import metrics
     meter = metrics.get_meter("my-service")
     my_counter = meter.create_counter("clp.my_service.my_metric", description="...", unit="bytes")
     ```
   - **Rust**: Use `clp_rust_utils::telemetry`.
     ```rust
     let meter = opentelemetry::global::meter("my-service");
     let my_counter = meter.u64_counter("clp.my_service.my_metric").with_description("...").init();
     ```

3. **Add increment/observe calls in the business logic**:
   - Add `.add(value, attributes)` in the relevant code path.

4. **Update the documentation table**:
   - Update `docs/src/user-docs/reference-telemetry.md` to list the new metric and its purpose.
   - This ensures users are aware of what is being collected.
