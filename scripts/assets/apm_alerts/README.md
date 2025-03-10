# APM Alerts Creation Scripts

python3 create_alerts.py --grafana_server "<KFUSE_DNS_NAME>/grafana" \
  --threshold_values_file ./files/alerts_config.csv \
  --grafana_username admin -p <your-password>

#### Provide the threshold values file (CSV format) that contains alert configurations.
#### Replace <KFUSE_DNS_NAME> with your Grafana server address.

## Configuration File (alerts_config.csv)
The script uses a CSV file to define alert rules.
### Example structure:

apm_trigger,service_name,span_name_pattern,span_name_matcher_op,threshold_operator,threshold_value,reducer,service_id_labels
http_requests,frontendproxy,ingress,=~,<,5,max,availability_zone=us-west1-a;cloud_account_id=12345

### Field Descriptions:
apm_trigger – Type of alert (e.g., http_requests, error_rate).
service_name – The name of the service generating the alert.
span_name_pattern – Defines which span to monitor.
span_name_matcher_op – How to match the span (=, =~ for regex, etc.).
threshold_operator – Alert threshold comparison (<, >, =).
threshold_value – The value at which an alert is triggered.
reducer – Function applied to metric values (max, min, etc.).
service_id_labels – Key-value pairs identifying the service.
