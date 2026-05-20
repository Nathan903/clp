from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from clp_py_utils.core import read_yaml_config_file
from clp_py_utils.clp_config import CLPConfig
import os

from job_orchestration.executor.query import celeryconfig
from opentelemetry import metrics

app = Celery("query")
app.config_from_object(celeryconfig)

@worker_process_init.connect
def on_worker_init(**kwargs):
    from clp_py_utils.telemetry import init_telemetry_for_celery_worker
    clp_config_path = os.getenv("CLP_CONFIG_PATH")
    if clp_config_path:
        clp_config = CLPConfig.parse_obj(read_yaml_config_file(clp_config_path))
        init_telemetry_for_celery_worker(clp_config.telemetry)

    meter = metrics.get_meter("query-worker")
    service_event_counter = meter.create_counter("clp.service.event")
    service_event_counter.add(1, attributes={"type": "start"})

@worker_process_shutdown.connect
def on_worker_shutdown(**kwargs):
    from clp_py_utils.telemetry import shutdown_telemetry
    meter = metrics.get_meter("query-worker")
    service_event_counter = meter.create_counter("clp.service.event")
    service_event_counter.add(1, attributes={"type": "stop"})
    shutdown_telemetry()

if "__main__" == __name__:
    app.start()
