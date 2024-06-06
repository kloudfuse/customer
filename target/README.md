# OpenTelemetry agent setup

To enable Kloudfuse to debug customer issues telemetry from otel agent should be enabled. Otherwise only the customer will be able to view the otel telemtry metrics (sent span count, sent metrics etc)

The following config needs to be enabled:


```
service
  telemetry:
    metrics:
      address: ${MY_POD_IP}:8888
```
```
receivers:
  prometheus:
    config:
      scrape_configs:
        - job_name: opentelemetry-collector
          scrape_interval: 10s
          static_configs:
            - targets:
                - ${env:MY_POD_IP}:8888
```

```
pipelines:
  metrics/telemetry:
    exporters:
      - otlphttp/customer
      - otlphttp/kfendpoint
    processors:
      - memory_limiter
      - batch
      - resourcedetection
    receivers:
      - prometheus
```

This configuration is already present in sample-collector-values.yaml
