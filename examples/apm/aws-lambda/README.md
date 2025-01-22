**Lambda Config**

***Layer name*** 

opentelemetry-python-0_11_0

***Version ARN***

arn:aws:lambda:us-west-2:184161586896:layer:opentelemetry-python-0_11_0:1

**Sample Env Variable Configuration**

AWS_LAMBDA_EXEC_WRAPPER = /opt/otel-instrument

OTEL_EXPORTER_OTLP_HEADERS = kf-api-key=[REDACTED_KEY]

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT={http(s)://KLOUDFUSE_ENDPOINT}/ingester/otlp/traces

OTEL_LOG_LEVEL = debug