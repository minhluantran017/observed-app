import logging
from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    PrometheusMetricsExporter,
)

app = Flask(__name__)

# Logging setup
log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

# Tracing setup
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "backend_service"}),
    )
)

span_processor = BatchExportSpanProcessor(jaeger_exporter)

trace.get_tracer_provider().add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)

RequestsInstrumentor().instrument()

# Prometheus metrics setup
metrics = PrometheusMetrics(app=app)

meter_provider = MeterProvider()
meter = meter_provider.get_meter(__name__)

total_requests_counter = meter.create_metric(
    "backend_service_total_requests",
    "Total number of requests to the backend service",
    "requests",
    int,
    Counter,
)

response_time_measure = meter.create_metric(
    "backend_service_response_time",
    "Response time of the backend service",
    "ms",
    float,
)

@app.route("/books")
def books():
    log.debug("Received request to /books")
    books = [
        {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
        {"id": 2, "title": "To Kill a Mockingbird", "author": "Harper Lee"},
        {"id": 3, "title": "1984", "author": "George Orwell"},
    ]
    response_time_start = trace.get_tracer(__name__).start_span("books-request")
    response = jsonify(books)
    response_time_end = trace.get_tracer(__name__).end_span(response_time_start)
    response_time = response_time_end.end_time - response_time_start.start_time
    response_time_measure.record(response_time, {"http_status_code": response.status_code})
    total_requests_counter.add(1)
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
