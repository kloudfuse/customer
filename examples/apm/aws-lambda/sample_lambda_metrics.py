import json
import logging
import os
import random
import time

# OpenTelemetry setup
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up OpenTelemetry Metrics
exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)
meter = metrics.get_meter("lambda_metrics")

# Custom metrics
processing_time_histogram = meter.create_histogram(
    name="processing_time_ms",
    description="Time taken to process events in milliseconds",
    unit="ms"
)

events_counter = meter.create_counter(
    name="events_processed_total",
    description="Total number of events processed",
    unit="1"
)

# Simulate some processing
def process_event(event):
    logger.info("Processing event...")
    start_time = time.time()  # Start time for metric
    time.sleep(random.uniform(0.1, 0.5))  # Simulate processing time
    processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

    # Record custom metrics
    processing_time_histogram.record(processing_time, {"function_name": "lambda_handler"})
    events_counter.add(1, {"function_name": "lambda_handler"})

    return {"status": "processed", "event": event}

# Lambda handler
def lambda_handler(event, context):
    logger.info("Lambda function invoked")

    try:
        # Process the incoming event
        response = process_event(event)

        # Log the response
        logger.info(f"Response: {response}")

        # Return the response
        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
