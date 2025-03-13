# Usage
# Create alerts: python3 create_alerts.py --grafana_server "<KFUSE_DNS_NAME>/grafana"
# --threshold_values_file ./files/alerts_config.csv

import argparse
import csv
import json
import xxhash
from typing import Dict, List, Tuple
from jinja2 import Environment, BaseLoader
from grafana_client import GrafanaClient, AlertRule, AlertData
from loguru import logger as log
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# List of labels that needs to be customised per customer
SVC_ID_LABELS_AGGR = [
    "availability_zone",
    "cloud_account_id",
    "kf_platform",
    "kube_cluster_name",
    "kube_namespace",
    "project",
    "region",
    "service_name"
]

ALERT_FOLDER_NAME = "apm_services_alerts"

class ExprGen:

    _alerts_config_csv = None
    _matcher_str_dict = {}

    def __init__(self, alerts_config_csv: str) -> None:
        self._extra_data_dict = {
            "error_rate": {
                "apmTriggerType": "ErrorRate",
                "spanType": "http"
            },
            "http_requests": {
                "apmTriggerType": "RequestPerSecond",
                "spanType": "http"
            },
            "http_throughput": {
                "apmTriggerType": "p50",
                "spanType": "http"
            },
            "p50_latency": {
                "apmTriggerType": "p50",
                "spanType": "http"
            },
            "p75_latency": {
                "apmTriggerType": "p75",
                "spanType": "http"
            },
            "p90_latency": {
                "apmTriggerType": "p90",
                "spanType": "http"
            },
            "p95_latency": {
                "apmTriggerType": "p95",
                "spanType": "http"
            },
            "p99_latency": {
                "apmTriggerType": "p99",
                "spanType": "http"
            },
            "min_latency": {
                "apmTriggerType": "min",
                "spanType": "http"
            },
            "max_latency": {
                "apmTriggerType": "max",
                "spanType": "http"
            },
            "average_latency": {
                "apmTriggerType": "average",
                "spanType": "http"
            },
            "apdex": {
                "apmTriggerType": "apdex",
                "spanType": "http"
            }
            
        }
        self._alerts_config_csv = alerts_config_csv

    def __get_anchored_regex_pattern(self, in_regex_pattern: str, in_op: str) -> str:
        regex_ops = ["=~", "!~"]
        if in_op not in regex_ops:
            return in_regex_pattern

        out_regex_pattern = in_regex_pattern
        if not out_regex_pattern.startswith("^"):
            out_regex_pattern = "^" + out_regex_pattern
        if not out_regex_pattern.endswith("$"):
            out_regex_pattern += "$"
        return out_regex_pattern

    def __get_alert_expr(self, row: Dict, alert_tmpls: Dict) -> str:
        tmpl = alert_tmpls.get(row["apm_trigger"], "")
        service_id_labels = row["service_id_labels"].split(";")
        service_name = row["service_name"]
        span_name_op = row["span_name_matcher_op"]
        anchored_span_name_pattern = self.__get_anchored_regex_pattern(
            row["span_name_pattern"],
            span_name_op
        )
        matcher_str = 'service_name="' + service_name + '", ' + ", ".join(
            [kv.split('=')[0] + '="' + kv.split('=')[1] + '"' for kv in service_id_labels]
        )

        if len(anchored_span_name_pattern) > 0:
            matcher_str += ', span_name' + span_name_op + '"' + anchored_span_name_pattern + '"'

        d = {"matcher": matcher_str, "service_id_labels": ",".join(item.split('=')[0] for item in service_id_labels), "service_hash": "service_hash" }

        return Environment(loader=BaseLoader).from_string(tmpl).render(d)
    
    @staticmethod
    def get_alert_folder_name(service_name: str, matcher_dict: dict) -> str:
        # Sort the labels lexicographically.
        labels = sorted(SVC_ID_LABELS_AGGR)
    
        # If a label is missing in matcher_dict, default to an empty string.
        values = [matcher_dict.get(label, "") for label in labels]
        service_idx = labels.index("service_name")
        hash_bytes, json_bytes = calculate_service_hash(labels, values, service_idx)
        
        return f"{service_name}_{hash_bytes.decode('utf-8')}"


    def generate_alert_rules(self, **kwargs) -> Dict:
        alert_tmpls = kwargs.get("alert_tmpls", {})
        alert_rules = {}
        title_counts = {}
        
        with open(self._alerts_config_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['apm_trigger']
                service_name = row['service_name']
                service_id_labels = row['service_id_labels'].split(";")
                service_dict = str_to_dict(row.get("service_id_labels", ""))
                service_dict["service_name"] = row.get("service_name", "")
                service_name_hash = ExprGen.get_alert_folder_name(row.get("service_name", ""),
                                                     service_dict)
                service_hash = service_name_hash.split("_")[1]
                expr = self.__get_alert_expr(row, alert_tmpls)
                contact_points = row["contact_points"].split(";")

                reducer = row["reducer"]
                condition = "$B " + row["threshold_operator"] + " " + row["threshold_value"]
                
                base_title = name + "_" + service_hash

                # Ensure title uniqueness to add alerts in same group
                if base_title in title_counts:
                    title_counts[base_title] += 1
                    unique_title = f"{base_title}_{title_counts[base_title]}"
                else:
                    title_counts[base_title] = 1
                    unique_title = base_title
                group_name = service_name + "_" + service_hash + "_group_1m_1"  
                d = alert_rules.get(group_name, {})
                d.setdefault('exprs', []).append(expr)
                d.setdefault('reducers', []).append(reducer)
                d.setdefault('conditions', []).append(condition)
                d.setdefault('titles', []).append(unique_title)
                d.setdefault('trigger_type', []).append(self._extra_data_dict[name].get("apmTriggerType"))
                d.setdefault('span_type', []).append(self._extra_data_dict[name].get("spanType"))
                d.setdefault('service_hash', []).append(service_hash)
                labels_dict = {item.split('=')[0]: item.split('=')[1] for item in service_id_labels}
                d.setdefault('unique_labels', []).append(labels_dict)
                contact_points_dict = {f"{item}" : "true" for item in contact_points}
                d.setdefault('contact_points', []).append(contact_points_dict)

                d['span_name'] = row["span_name_pattern"]
                d.setdefault('service_name', []).append(service_name)
                alert_rules[group_name] = d

        return alert_rules

class ThresholdExprGen(ExprGen):
    def __init__(self, alerts_config_csv: str) -> None:
        self._alert_type = "threshold"
        self._http_alerts_expr_tmpl = {

            "error_rate": """((sum by ({{ service_hash }}) (rate(edge_latency_count{error="true",{{ matcher }}, kf_source="apm"}[300s]))) OR (sum by ( {{ service_hash }} ) (rate(edge_latency_count{ {{ matcher }}, kf_source="apm"}[300s])) * 0)) * 100.0 / sum by ({{ service_hash }}) (rate(edge_latency_count{ {{ matcher }}, kf_source="apm"}[300s]))""",
            
            "http_requests": """sum by ({{ service_hash }}) (rate(edge_latency_count{ {{ matcher }}, kf_source="apm"}[300s]))""",
            
            "http_throughput": """histogram_quantile(0.50, sum by ({{ service_hash }}, le) (rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm"}[300s])))""",
            
            "apdex": """clamp_max((sum by ({{ service_hash }}) (increase(edge_latency_bucket{ {{ matcher }}, le="2000",error!="true",kf_source="apm",span_type!="db"}[300s])) + sum by ({{ service_hash }}) (increase(edge_latency_bucket{ {{ matcher }}, le="500",error!="true",kf_source="apm",span_type!="db"}[300s])))/(2*sum by ({{ service_hash }}) (increase(edge_latency_count{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s]))),1)""",
            
            "p50_latency": """histogram_quantile(0.50, sum(rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }}, le))""",

            "p75_latency": """histogram_quantile(0.75, sum(rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }}, le))""",

            "p90_latency": """histogram_quantile(0.90, sum(rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }}, le))""",

            "p95_latency": """histogram_quantile(0.95, sum(rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }}, le))""",

            "p99_latency": """histogram_quantile(0.99, sum(rate(edge_latency_bucket{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }}, le))""",

            "max_latency": """max(max_over_time(edge_latency_max{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }})""",

            "min_latency": """min(min_over_time(edge_latency_min{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) by ({{ service_hash }})""",

            "average_latency": """sum by ({{ service_hash }}) (rate(edge_latency_sum{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s])) / sum by ({{ service_hash }}) (rate(edge_latency_count{ {{ matcher }}, kf_source="apm",span_type!="db"}[300s]))""",
        }
        super().__init__(alerts_config_csv)

    def get_alert_expr_tmpls(self) -> Dict:
        return self._http_alerts_expr_tmpl
    
    @staticmethod
    def get_alert_type() -> str:
        return "threshold"

def calculate_service_hash(labels, values, service_idx):

    h = xxhash.xxh64()
    
    # Process the service attribute separately.
    service_label = labels[service_idx]
    service_value = values[service_idx]
    h.update(service_label.encode('utf-8'))
    h.update(service_value.encode('utf-8'))
    json_parts = []
    json_parts.append("\"service_name\":\"" + service_value + "\"")
    
    # Iterate over all other labels.
    for i, label in enumerate(labels):
        if i == service_idx:
            continue
        h.update(label.encode('utf-8'))
        if values[i] == "" or values[i] == "UNKNOWN":
            h.update(b"")  # Writing empty bytes if the value is missing.
            json_parts.append(",\"" + label + "\":\"\"")
        else:
            h.update(values[i].encode('utf-8'))
            escaped_value = json.dumps(values[i])
            json_parts.append(",\"" + label + "\":" + escaped_value)
    
    json_str = "{" + "".join(json_parts) + "}"

    hash_hex = h.hexdigest()
    return hash_hex.encode('utf-8'), json_str.encode('utf-8')

def dict_to_str(d: Dict, exclusion_list: List) -> str:
    return ",".join([f'{k}="{d[k]}"' for k in sorted(d.keys()) 
                     if len(d.get(k, "")) > 0 and k not in exclusion_list])
def str_to_dict(dict_str: str) -> Dict:
    return {kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in dict_str.split(";")}

def generate_alert_rules(alert_rules_dict: Dict, **kwargs) -> Dict:
    alert_rules = {}
    ds_uid = kwargs.get("ds_uid", "")

    for group_name, d in alert_rules_dict.items():
        alert_rules[group_name] = []
        exprs = d.get("exprs", [])
        reducers = d.get("reducers", [])
        conditions = d.get("conditions", [])
        titles = d.get("titles", [])
        apm_trigger_types = d.get("trigger_type")
        span_name = d.get("span_name", "")
        span_types = d.get("span_type", "")
        contact_points = d.get("contact_points", [])
        for i, expr in enumerate(exprs):
            title = titles[i]
            extra_data = {}
            apm_trigger_type = apm_trigger_types[i]
            span_type = span_types[i]
            contact_point = contact_points[i]
            extra_data["apmTriggerType"] = apm_trigger_type
            extra_data["serviceName"] = d.get("service_name")[i]
            extra_data["serviceHash"] = d.get("service_hash")[i]
            extra_data["additionalLabels"] = [f'span_name="{span_name}"', f'span_type="{span_type}"']
            extra_data["uniqueLabels"] = d.get("unique_labels")[i]

            alert_rule = AlertRule(
                alert_rule_annotations={
                    "alertType": "threshold",
                    "forWindow": "5m",
                    "ruleType": "apm",
                    "Summary": title,
                    "extraData": json.dumps(extra_data),
                    "summary": title,
                    "Kloudfuse Source": "{{ reReplaceAll pathPrefix \"\" externalURL }}/#/alerts/details/{{ $labels.__alert_rule_uid__ }}?folderTitle={{ $labels.grafana_folder }}{{ range $key, $value := $labels }}&matcher={{ $key }}%3D{{ $value }}{{ end }}",
                },
                alert_rule_labels={"kfuse_generated": "true", **contact_point},
                alert_rule_expression=expr,
                alert_rule_for_duration="0s",
                alert_rule_interval="1m",
                alert_rule_title=title,
                alert_rule_datasource_uid=ds_uid,
                alert_rule_condition_expression=conditions[i],
                alert_rule_reducer_type=reducers[i]
            )

            alert_rules[group_name].append(alert_rule)

    return alert_rules

def create_alerts_for_services(g: GrafanaClient, alerts_config_csv: str) -> None:
    ds_uid, success = g.get_datasource_uid('KfuseDatasource')
    if not success:
        raise RuntimeError("failed to find datasource uid for KfuseDatasource")
    
    te = ThresholdExprGen(alerts_config_csv)
    csv_alerts = te.generate_alert_rules(alert_tmpls=te.get_alert_expr_tmpls())
    existing_alerts = get_existing_alert_rules(g)
    alerts_to_update, alerts_to_delete = process_alerts_to_delete_and_update(existing_alerts, csv_alerts)
    
    for group_name in alerts_to_delete:
        print(f"Deleting alerts from group {group_name}")
        _, success = g.remove_alerts(ALERT_FOLDER_NAME, group_name)
        if not success:
            print(f"Failed to delete alerts in folder={ALERT_FOLDER_NAME}, group={group_name}")
            raise RuntimeError("Failed to remove alerts")

    alert_rules = generate_alert_rules(alerts_to_update, ds_uid=ds_uid)
    for group_name, rules in alert_rules.items():
        print(f"Creating alerts in group {group_name}")
        alert_data = AlertData(
            alert_name=group_name,
            alert_interval="1m",
            alert_folder=ALERT_FOLDER_NAME,
            alert_rules_list=rules
        )
        create_alerts_on_grafana(g, [alert_data], ALERT_FOLDER_NAME)

    return

def process_alerts_to_delete_and_update(existing_alerts: Dict, csv_alerts: Dict) -> Tuple:
    alerts_to_update = {}
    alerts_to_delete = []

    for group_name, rules_dict in existing_alerts.items():
        # Alert rules are no longer in CSV file - so delete them
        if group_name not in csv_alerts:
            alerts_to_delete.append(group_name)
            continue
        csv_alerts_dict = csv_alerts.get(group_name, {})
        allowed_keys = ["exprs", "reducers", "conditions", "titles"]
        filtered_csv_alerts_dict = {k: v for k, v in csv_alerts_dict.items()
                                    if k in allowed_keys}
        # Something's changed in the alert rule definitions (either expression or threshold value).
        # Whatever the change is, install alerts per metadata defined in the CSV file
        if rules_dict != filtered_csv_alerts_dict:
            alerts_to_update[group_name] = csv_alerts_dict

    # Add alert(s) for new service(s) which haven't been installed yet.
    alerts_to_update.update({k: v for k, v in csv_alerts.items() if k not in existing_alerts})
    return alerts_to_update, alerts_to_delete

def get_existing_alerts_groups(g: GrafanaClient) -> List:
    folder_id, status = g.get_folder_id(ALERT_FOLDER_NAME)
    if not status:
        print(f"Failed to check if folder {ALERT_FOLDER_NAME} exists or not")
        raise RuntimeError("Failed to query alert folders in grafana")
    if not folder_id:
        return []
    resp, status = g.get_alert_rules(ALERT_FOLDER_NAME, None)
    if not status:
        print(f"Failed to query grafana alert groups for folder {ALERT_FOLDER_NAME}")
        raise RuntimeError("Failed to query grafana alert groups")
    if len(resp) == 0:
        return []

    return [gr['name'] for gr in resp[ALERT_FOLDER_NAME]]

def get_existing_alert_rules(g: GrafanaClient) -> Dict:
    existing_alerts = {}
    group_names = get_existing_alerts_groups(g)
    for group in group_names:
        resp, status = g.get_alert_rules(ALERT_FOLDER_NAME, group)
        if not status:
            print(f"Failed to query alerts with folder {ALERT_FOLDER_NAME}, group {group}")
            raise RuntimeError("Failed to query grafana alerts")
        exprs = [e['grafana_alert']['data'][0]['model']['expr']
                 for e in resp['rules']]
        reducers = [e['grafana_alert']['data'][1]['model']['reducer']
                    for e in resp['rules']]
        conditions = [e['grafana_alert']['data'][2]['model']['expression']
                    for e in resp['rules']]
        titles = [e['grafana_alert']['title'] for e in resp['rules']]
        d = {'exprs': exprs, 'reducers': reducers, 'conditions': conditions, 'titles': titles}
        existing_alerts[group] = d
    return existing_alerts

def create_alerts_on_grafana(g: GrafanaClient, alert_data_list: List[AlertData],
                             alert_folder_name: str) -> None:
    for alert_data in alert_data_list:
        ret = g.create_alert(alert_folder_name, alert_data)
        if not ret:
            print(f"failed to create alert {alert_data.alert_name}")
        else:
            print(f"successfully created alert {alert_data.alert_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to create APM alerts for a given service")
    parser.add_argument(
        "-g", "--grafana_server", required=True,
        help="Grafana server address, e.g.: http://<KFUSE_DNS_NAME>/grafana"
    )
    parser.add_argument(
        "-u", "--grafana_username", help="Grafana username", default="admin"
    )
    parser.add_argument(
        "-p", "--grafana_passwd", help="Grafana password", default="password"
    )
    parser.add_argument(
        "-t", "--threshold_values_file", required=True,
        help="CSV file with config for alert rules (absolute path)"
    )
    args = parser.parse_args()
    gc = GrafanaClient(grafana_server=args.grafana_server, grafana_username=args.grafana_username,
                       grafana_password=args.grafana_passwd)
    create_alerts_for_services(gc, args.threshold_values_file)