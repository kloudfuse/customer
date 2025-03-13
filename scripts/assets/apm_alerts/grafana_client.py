import os
import re
import json
from typing import Dict
from typing import Tuple
import requests
from jinja2 import Environment, FileSystemLoader
from requests.auth import HTTPBasicAuth
from datetime import timedelta

CONTACT_POINT_NAME_SUFFIX = "__kfuse_script_managed"

class AlertRule:

    alert_rule_for_duration = None
    alert_rule_title = None
    alert_rule_datasource_uid = None
    alert_rule_interval_ms = None
    alert_rule_condition_expression = None
    alert_rule_condition_params = None
    alert_rule_condition_type = None
    alert_rule_annotations = {}
    alert_rule_labels = {}
    alert_rule_expression = None
    alert_rule_reducer_type = None

    def op_to_words(self, op):
        if op == '>':
            return 'gt'
        elif op == '>=':
            return 'gte'
        elif op == '<':
            return 'lt'
        elif op == '<=':
            return 'lte'

    def parse_time(self, time_str):
        duration_regex = re.compile(
            r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
        parts = duration_regex.match(time_str)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for name, param in parts.items():
            if param:
                time_params[name] = int(param)
        return timedelta(**time_params)

    def __init__(self, **kwargs) -> None:
        self.alert_rule_annotations = kwargs.get("alert_rule_annotations")
        self.alert_rule_labels = kwargs.get("alert_rule_labels")
        self.alert_rule_expression = kwargs.get("alert_rule_expression")
        self.alert_rule_for_duration = kwargs.get("alert_rule_for_duration")
        self.alert_rule_interval = kwargs.get("alert_rule_interval")
        self.alert_rule_interval_ms = self.parse_time(
            self.alert_rule_interval).seconds * 1000
        self.alert_rule_title = kwargs.get("alert_rule_title")
        self.alert_rule_datasource_uid = kwargs.get(
            "alert_rule_datasource_uid")
        operator = kwargs.get("alert_rule_condition_operator")
        operator_shorthand = self.op_to_words(operator)
        threshold = kwargs.get("alert_rule_condition_threshold")
        condition_variable = kwargs.get("alert_rule_condition_variable", "$B")
        self.alert_rule_condition_expression = kwargs.get("alert_rule_condition_expression",
                                                    f"{condition_variable} {operator} {threshold}")
        self.alert_rule_condition_params = threshold
        self.alert_rule_condition_type = operator_shorthand
        # reducer_type is only used in non-anomaly alerts
        self.alert_rule_reducer_type = kwargs.get(
            "alert_rule_reducer_type", "last")

    def as_dict(self) -> Dict:
        return {
            "for_duration": self.alert_rule_for_duration,
            "annotations": json.dumps(self.alert_rule_annotations),
            "labels": json.dumps(self.alert_rule_labels),
            "title": self.alert_rule_title,
            "datasourceUid": self.alert_rule_datasource_uid,
            "expr": json.dumps(self.alert_rule_expression),
            "interval": self.alert_rule_interval,
            "intervalMs": self.alert_rule_interval_ms,
            "expression": self.alert_rule_condition_expression,
            "params": self.alert_rule_condition_params,
            "condition_type": self.alert_rule_condition_type,
            "reducer_type": self.alert_rule_reducer_type
        }


class AlertData:

    alert_interval = None
    alert_name = None
    alert_folder = None
    alert_rules = []

    def __init__(self, **kwargs) -> None:
        self.alert_interval = kwargs.get("alert_interval")
        self.alert_name = kwargs.get("alert_name")
        self.alert_rules_list = kwargs.get("alert_rules_list")
        self.alert_folder = kwargs.get("alert_folder")

    def as_dict(self) -> Dict:
        return {
            "name": self.alert_name,
            "folder": self.alert_folder,
            "interval": self.alert_interval,
            "rules": [r.as_dict() for r in self.alert_rules_list]
        }

class GrafanaClient:
    def __init__(self, **kwargs):
        self._server = kwargs.get("grafana_server", "")
        self._verify = kwargs.get("verify_ssl", True)
        if self._server.startswith("https://"):
            self._server = self._server.removeprefix("https://")
            self._scheme = "https"
        else:
            self._server = self._server.removeprefix("http://")
            self._scheme = "http"

        self._username = kwargs.get("grafana_username")
        self._password = kwargs.get("grafana_password")
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        file_dir = os.path.dirname(__file__)
        env = Environment(loader=FileSystemLoader(
            os.path.join(file_dir, "./files")))
        self._template = env.get_template("alert_template.json")

    def _get_alert_data_json(self, alert_data: AlertData) -> str:
        return self._template.render(alert_data.as_dict())

    def _handle_http_request_to_grafana(self, **kwargs) -> Tuple:
        path = kwargs.get("path", "")
        request_fn = kwargs.get("request_fn", None)
        if request_fn is None:
            return {'status': 'invalid request function'}, False
        request_type = kwargs.get("request_type", "")
        request_body = kwargs.get("request_body", None)
        full_url = f"{self._scheme}://{self._server}{path}"
        auth = HTTPBasicAuth(self._username, self._password)
        success = True
        response = request_fn(full_url, auth=auth, data=request_body,
                              headers=self._headers, timeout=30, verify=self._verify)
        if int(response.status_code / 100) != 2:
            print("http {0} returned an error for url {1}; status = {2}, content={3}".format(
                request_type,
                full_url,
                response.status_code,
                response.content)
            )
            success = False
        return response, success

    def _http_delete_request_to_grafana(self, path) -> Tuple:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.delete,
                                                                 path=path,
                                                                 request_type="delete")
        return {'status': response.status_code}, success

    def _http_get_request_to_grafana(self, path) -> Tuple:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.get,
                                                                 path=path,
                                                                 request_type="get")
        if not success:
            return {'status': response.status_code}, success
        return response.json(), success

    def _http_post_request_to_grafana(self, path, post_data=None) -> bool:
        _, success = self._handle_http_request_to_grafana(request_fn=requests.post,
                                                          path=path,
                                                          request_type="post",
                                                          request_body=post_data)
        return success

    def _create_alert_folder(self, folder) -> Tuple:
        path = "/api/folders"
        data = json.dumps({"title": f"{folder}"})
        status = self._http_post_request_to_grafana(path=path, post_data=data)
        if not status:
            print(f"Failed to create folder; folder_id = {folder}")
            return None, status
        return self.get_folder_id(folder)

    def _upload_alert_to_grafana(self, folder: str, alert_group_json: str) -> bool:
        folder_id, status = self.get_folder_id(folder)
        if not status:
            return status
        if not folder_id:
            folder_id, status = self._create_alert_folder(folder=folder)
            if not status:
                return status

        if not folder_id:
            print(f"Failed to find valid folder id for folder {folder}")
        path = f"/api/ruler/grafana/api/v1/rules/{folder_id}?subtype=cortex"
        return self._http_post_request_to_grafana(path=path, post_data=alert_group_json)

    def get_datasource_uid(self, datasource) -> Tuple:
        path = "/api/datasources"
        ds_list, success = self._http_get_request_to_grafana(path=path)
        if not success:
            print(
                f"Datasource API returned an error; datasource={datasource}")
            return "", False
        ds_uid = next((ds for ds in ds_list if ds["name"] == datasource), None)
        if ds_uid is None:
            return None, False
        return ds_uid["uid"], True

    def get_folder_id(self, folder) -> Tuple:
        path = "/api/folders"
        folder_list, status = self._http_get_request_to_grafana(path=path)
        if not status:
            print(f"Folder API returned an error for folder {folder}")
            return False, False
        folder_id = next((f.get("uid", None) for f in folder_list if f["title"] == folder), None)
        return folder_id, True

    def create_alert(self, folder, alert_data: AlertData) -> bool:
        alert_data_json = self._get_alert_data_json(alert_data=alert_data)
        return self._upload_alert_to_grafana(folder, alert_data_json)

    def remove_alerts(self, folder, name) -> Tuple:
        folder_id, status = self.get_folder_id(folder)
        if not status:
            return status
        if not folder_id:
            print(f"Failed to find valid folder id for folder {folder}")
            return False, False
        path = f"/api/ruler/grafana/api/v1/rules/{folder_id}/{name}"
        return self._http_delete_request_to_grafana(path)

    def get_alert_rules(self, folder, name) -> Tuple:
        folder_id, found = self.get_folder_id(folder)
        if not found:
            return None, found
        if name is None:
            path = f"/api/ruler/grafana/api/v1/rules/{folder_id}"
        else:
            path = f"/api/ruler/grafana/api/v1/rules/{folder_id}/{name}"
        return self._http_get_request_to_grafana(path)

    def get_alertmanager_config(self) -> Tuple:
        path = "/api/alertmanager/grafana/config/api/v1/alerts"
        return self._http_get_request_to_grafana(path)

    def update_alertmanager_config(self, alert_config_json) -> bool:
        path = "/api/alertmanager/grafana/config/api/v1/alerts"
        return self._http_post_request_to_grafana(path=path, post_data=alert_config_json)
