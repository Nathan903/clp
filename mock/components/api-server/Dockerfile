FROM python:3.12-slim

WORKDIR /app
COPY components/common/ /app/common/
COPY components/api-server/mock.py /app/mock.py

RUN pip install --no-cache-dir \
    opentelemetry-api>=1.31.1 \
    opentelemetry-sdk>=1.31.1 \
    opentelemetry-exporter-otlp-proto-http>=1.31.1

CMD ["python3", "-u", "mock.py"]
