# APM Alerts Creation Scripts
These Python scripts are provided for creating the apm alerts and contact points using the CSV files. These scripts can be used to convert NRQL alerts to Grafana alerts. The CSV files follow a fixed format which needs to be configured properly.  

## Prerequisites
- Python 3.x
- Required Python packages: Use the requirements.txt file to install all the packages `pip3 install -r requirements.txt`
- Access to the Grafana instance 
- CSV file for create_alerts.py: sample_alerts_config.csv
- CSV file for create_contact_points.py: sample_contact_points.csv
- SERVICE_ID_LABELS_AGGR (["availability_zone", "cloud_account_id", "kf_platform", "kube_cluster_name", "kube_namespace", "project", "region", "service_name"]) : List of labels that needs to be customised per customer

## Command Arguments
Arguments definitions:

- `-a, --grafana-server` : Grafana server address, e.g.: https://<KFUSE_DNS_NAME>grafana
- `-u, --grafana-username` : Grafana username (default: `admin`)
- `-p, --grafana-passwd` : Grafana password (default: `password`)
- `-t, --threshold_values_file` : CSV file with config for alert rules (absolute path)
- `-c, --contact_points_file` : CSV file with config for contact points (absolute path)

---

### Create APM Alerts
```sh
python3 create_alerts.py --grafana_server "https://<KFUSE_DNS_NAME>/grafana" \
  --threshold_values_file ./files/sample_alerts_config.csv \
  --grafana_username admin -p <your-password>
```

#### CSV Configuration File (sample_alerts_config.csv) for create_alerts.py
The script uses a CSV file to define alert rules. NRQL alerts can be converted to Grafana alerts using the CSV file.
#### Example structure of sample_alerts_config.csv:
```sh
apm_trigger,service_name,span_name_pattern,span_name_matcher_op,threshold_operator,threshold_value,reducer,service_id_labels
http_requests,frontendproxy,ingress,=~,<,5,max,availability_zone=us-west1-a;cloud_account_id=12345
```
#### Field Descriptions for sample_alerts_config.csv:
- `apm_trigger`:          Type of alert (e.g., http_requests, error_rate, apdex).
- `service_name`:         The name of the service generating the alert.
- `span_name_pattern`:    Defines which span to monitor.
- `span_name_matcher_op`: How to match the span (=, =~ for regex, etc.).
- `threshold_operator`:   Alert threshold comparison (<, >, =).
- `threshold_value`:      The value at which an alert is triggered.
- `reducer`:              Function applied to metric values (max, min, etc.).
- `service_id_labels`:    Key-value pairs identifying the service separated by semicolon. (e.g., availability_zone=us-west1-a;        cloud_account_id=12345). This can be found from the APM services page for each service. 

---

### Create Contact Points
```sh
python3 create_contact_points.py -g "https://<KFUSE_DNS_NAME>/grafana"
-c ./files/sample_contact_points.csv
```

#### CSV Configuration File (sample_contact_points.csv) for create_contact_points.py
The script uses a CSV file to define contact points. 
```sh
contact_point_name,type,receiver,template_title_file,template_body_file
alerts-webui,slack,https://hooks.slack.com/services/xxxx/yyyy/zzzz,default_slack_template_title,default_slack_template_body
incore,email,sample_email@email.com,default_email_template_title,default_email_template_body
```

The CSV file defines the contact point name, type, and receiver. The template title and body files are used to define the title and body of the alert.

#### Field Descriptions for sample_contact_points.csv:
- `contact_point_name`: Identifier for the contact point (e.g., alerts-webui, incore)
- `type`: The type of contact point (e.g., slack, email)
- `receiver`: The recipient endpoint (e.g., Slack webhook URL or email address)
- `template_title_file`:  The file name for the title template used in notifications (present in files folder)
- `template_body_file`:  The file name for the body template used in notifications (present in files folder)

# Converting the NRQL alerts to Grafana alerts using the sample_alerts_config.csv file

Trigger types available in KFUSE: `http_requests`, `error_rate`, `http_throughput`,`apdex`, `average_latency`, `max_latency`, `min_latency`, `p50_latency`, `p75_latency`, `p90_latency`, `p95_latency`, `p99_latency`.
`Note:` Trigger types from NRQL should be mapped equivalently to one of the trigger types available in KFUSE.


1. Sample NRQL alert json:
```sh
{
  "entity_name": "ACI-PROD-LMS-LIVE",
  "type": "apm_app_metric",
  "condition_scope": "application",
  "enabled": true,
  "policies": [
    {
      "policy_name": "NOC",
      "terms": [
        {
          "name": "ACI-PROD-LMS-LIVE Response Time",
          "duration": "5",
          "operator": "above",
          "priority": "critical",
          "threshold": "3",
          "time_function": "all",
          "metric": "response_time_web"
        }
      ]
    },
  ]
}
```
- `entity_name` : Maps to `service_name` in the CSV. This represents the service generating the alert.

- `policies[0].policy_name.name` : Contains the `service_name` followed by the `apm_trigger`. 
  `Note:` Sometimes you need to use both  the `operator` and `apm_trigger` together to determine the apm_trigger type. For ex - `Response Time` corresponds to `latency` but there are different types of latency available. You need to choose one of them. 

- `policies[0].terms.operator`  : Corresponds to `threshold_operator` in the CSV.  

- `policies[0].terms.threshold` : Maps to `threshold_value` in the CSV. This is the value at which the alert is triggered.


2. Another type of NRQL alert json:
```sh
{
  "nrql_conditions": [
    {
      "policy_name":"NOC",
      "type": "static",
      "name": "ACAC-PROD-FACETS-LMS-LIVE nrql ohs_getuserclient average apm_service_transaction_duration",
      "enabled": true,
      "value_function": "single_value",
      "violation_time_limit_seconds": 259200,
      "terms": [
        {
          "duration": "10",
          "operator": "above",
          "priority": "warning",
          "threshold": "0.015",
          "time_function": "all"
        },
        {
          "duration": "10",
          "operator": "above",
          "priority": "critical",
          "threshold": "0.070",
          "time_function": "all"
        }
      ],
      "nrql": {
        "query": "SELECT average(apm.service.transaction.duration) as value FROM Metric WHERE appName = 'ACAC-PROD-FACETS-LMS-LIVE' and transactionName like 'WebTransaction/Expressjs/POST//ohs/get-user-client'",
        "since_value": "10"
      },
      "signal": {
        "aggregation_window": "60",
        "evaluation_offset": "3",
        "fill_option": "static",
        "fill_value": "0"
      },
      "expiration": {
        "expiration_duration": "3900",
        "open_violation_on_expiration": false,
        "close_violations_on_expiration": true
      },
    }
  ]
}
```

- `nrql.query.appName` : Maps to `service_name` in the CSV. This represents the service generating the alert.

- `nrql.query.transactionName` : Maps to `spanname` in the CSV. This defines the specific transaction being monitored.

- In nrql query, `average(apm.service.transaction.duration)` : Corresponds to the `average_latency` trigger type in KFUSE. This metric represents the average transaction duration for a specific service or span.

- `terms[].threshold` : Maps to `threshold_value` in the CSV. This is the numerical value at which the alert triggers.

Another example of nrql query type:
```sh
 "nrql": {
        "query": "SELECT percentile(duration,99) as value FROM Transaction WHERE appName = 'ACAC-PROD-FACETS-LMS-LIVE' and name = 'WebTransaction/Expressjs/POST//users/sessionv2'",
        "since_value": "60"
      },
```

- In nrql query, `percentile(duration,99)` : Corresponds to the `p99_latency` trigger type in KFUSE. This metric represents the 99th percentile of transaction duration, indicating the latency experienced by the slowest 1% of requests.
