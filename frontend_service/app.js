const express = require("express");
const axios = require("axios");
const { MeterProvider } = require('@opentelemetry/sdk-metrics-base');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const { NodeTracerProvider } = require('@opentelemetry/node');
const { SimpleSpanProcessor, ConsoleSpanExporter, JaegerExporter } = require('@opentelemetry/tracing');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { GraphQLInstrumentation } = require('@opentelemetry/instrumentation-graphql');

const app = express();

const port = 5000;
const backendServiceUrl = "http://backend_service:8080/books";

const meterProvider = new MeterProvider({
  interval: 1000,
});

const exporter = new PrometheusExporter({
  startServer: true,
});

meterProvider.addExporter(exporter);

const tracerProvider = new NodeTracerProvider({
  serviceName: 'frontend_service',
});

tracerProvider.addSpanProcessor(new SimpleSpanProcessor(new JaegerExporter({
  serviceName: 'frontend_service',
  host: 'jaeger',
  port: 6831,
})));

registerInstrumentations({
  tracerProvider,
  instrumentations: [
    new ExpressInstrumentation(),
    new HttpInstrumentation(),
    new GraphQLInstrumentation(),
  ],
});

const meter = meterProvider.getMeter('frontend_service');

const totalRequestsCounter = meter.createCounter("frontend_service_total_requests", {
  description: "Total number of requests to the frontend service",
});

const responseTimeMeasure = meter.createValueRecorder("frontend_service_response_time", {
  description: "Response time of the frontend service",
  boundaries: [0, 50, 100, 200, 500, 1000, 2000],
  valueType: 'double',
});

app.get("/", async (req, res) => {
  console.log(`Received GET request to /`)
  console.log(`Sending GET request to ${backendServiceUrl} ...`)
  const startTime = Date.now();
  totalRequestsCounter.add(1);
  const response = await axios.get(backendServiceUrl);
  const endTime = Date.now();
  const responseTime = endTime - startTime;
  responseTimeMeasure.record(responseTime, {
    http_status_code: response.status,
  });
  console.log(`Received GET response from ${backendServiceUrl}`)
  res.send(response.data);
});

app.listen(port, () => {
  console.log(`frontend-service listening at http://localhost:${port}`);
});
