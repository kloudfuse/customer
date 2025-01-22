import json
import logging
import os
import random
import time

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Simulate some processing
def process_event(event):
    logger.info("Processing event...")
    time.sleep(random.uniform(0.1, 0.5))  # Simulate processing time
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