import json
import sys
from typing import List, Optional
from typing import Tuple

import requests
from loguru import logger as log
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

# Set logging level to INFO
log.remove()
log.add(sink=sys.stderr, level="INFO")


class GrafanaClient:
    def __init__(self, grafana_server, grafana_username, grafana_password):
        parsed_url = urlparse(grafana_server)
        self._scheme = parsed_url.scheme or "https"  # Default to HTTPS if no scheme provided
        self._server = parsed_url.netloc 
        self._base_path = parsed_url.path.rstrip("/") if parsed_url.path else "" 
        self._server = self._server + self._base_path
        self._username = grafana_username
        self._password = grafana_password
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

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
        response = request_fn(full_url, auth=auth, data=request_body, headers=self._headers, timeout=30)
        if response.status_code >= 300:
            log.error("http {0} returned an error for url {1}; status = {2}, content={3}".format(
                request_type,
                full_url,
                response.status_code,
                response.content)
            )
            success = False
        return response, success

    def _http_get_request_to_grafana(self, path: str) -> Tuple:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.get,
                                                                 path=path,
                                                                 request_type="get")
        if not success:
            return {'status': response.status_code}, success
        return response.json(), success

    def _http_post_request_to_grafana(self, path: str, post_data: str = None) -> bool:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.post,
                                                                 path=path,
                                                                 request_type="post",
                                                                 request_body=post_data)
        log.debug("POST response={0}, success={1}".format(response, success))
        return success

    def _check_if_folder_exists(self, folder: str) -> Tuple:
        path = "/api/folders"
        folder_list, status = self._http_get_request_to_grafana(path=path)
        if not status:
            log.error("Folder API returned an error; folder = {0}".format(folder))
            return None, False
        log.debug("FolderList={0}".format(folder_list))
        folder_info = next((f for f in folder_list if f["title"] == folder), None)
        return folder_info, folder_info is not None

    def _create_alert_folder_if_not_exists(self, folder: str):
        """
        Create a new alert folder and returns the automatically created internal folderID

        :param folder: name of the folder to be created
        :return
            bool: True: if folder was created/exists, False otherwise
            FolderUID: In case successful, else None
        """
        folder_info, exists = self._check_if_folder_exists(folder)
        if exists:
            log.debug("Folder already exists; folder = {0}".format(folder_info))
            return True, folder_info["uid"]

        path = "/api/folders"
        data = json.dumps({"title": f"{folder}"})
        status = self._http_post_request_to_grafana(path=path, post_data=data)
        if not status:
            log.error("Failed to create folder; folder = {0}".format(folder))
            return status, None

        log.debug("Folder={0} created...".format(folder))
        return True, self._get_alert_folder_uid(folder)

    def _get_alert_folder_uid(self, folder_name):
        """
        Create a new folder or return existing folder's UID

        :param folder_name: Name of the folder to create/retrieve
        :return: Folder UID or None
        """
        # First, try to find existing folder
        find_folder_api = "/api/folders"
        folders_response = self._http_get_request_to_grafana(find_folder_api)
        for f in folders_response[0]:
            if f['title'] == folder_name or f["title"] is None:
                return f['uid']

        return None

    def create_alert(self, folder, alert_data_json) -> bool:
        """Create alert using sample data for testing.

        Returns
            True: Success
            False: Failure
        """
        log.debug("Alert data={0}".format(alert_data_json))
        created, folder_uid = self._create_alert_folder_if_not_exists(folder)
        if not created:
            log.error("Failed to create folder={0}".format(folder))
            return False

        log.debug("Folder UID={0}, Name={1}".format(folder_uid, folder))
        path = f"/api/ruler/grafana/api/v1/rules/{folder_uid}"
        return self._http_post_request_to_grafana(path=path, post_data=alert_data_json)

    def _list_alerts(self, folder_name: str) -> tuple[Optional[List], Optional[str]]:
        """List all alerts in a Grafana folder.
        
        Args:
            folder_name: Name of the folder to list alerts from
            
        Returns:
            tuple: (alerts_list, error_message)
                - alerts_list: List of alerts if successful, None if failed
                - error_message: Error description if failed, None if successful
        """
        folder_uid = self._get_alert_folder_uid(folder_name)
        if not folder_uid:
            return None, f"Folder not found: {folder_name}"

        log.debug("[ListAlert] Folder UID={0}, Name={1}".format(folder_uid, folder_name))
        path = f"/api/ruler/grafana/api/v1/rules/{folder_uid}"
        response = self._http_get_request_to_grafana(path)
        log.debug("Response=\n{}", json.dumps(response, indent=2, sort_keys=True))
        if not response:
            return None, f"Failed to fetch alerts from folder: {folder_name}"

        return response, None

    def delete_alert(self, folder_name, alert_name, delete_all=False):
        """Delete alert using sample data for testing."""
        log.debug("Name={0} from folder={1}. DeleteAll={2}".format(
            alert_name,
            folder_name,
            delete_all
        ))
        folder_uid = self._get_alert_folder_uid(folder_name)
        if folder_uid is None:
            log.error("Folder not found: {0}".format(folder_name))
            return False
        existing_alerts, error = self._list_alerts(folder_name)
        if error:
            log.error(error)
            return False

        log.debug("ExistingAlerts: {0}".format(json.dumps(existing_alerts[0], indent=2)))
        if existing_alerts is None or existing_alerts[0] == {}:
            log.debug("No alerts found in folder: {0}".format(folder_name))
            return True
        new_rules = []
        if delete_all is False:
            rules = existing_alerts[0][folder_name][0]["rules"]
            for r in rules:
                rule_title = r["grafana_alert"]["title"]
                if rule_title != alert_name:
                    log.debug("Keeping alert: {0}".format(rule_title))
                    new_rules.append(r)
                    continue
                else:
                    log.debug("Deleting alert: {0}".format(rule_title))

        existing_alerts[0][folder_name][0]["rules"] = new_rules
        final_payload = json.dumps(existing_alerts[0][folder_name][0])
        return self.create_alert(folder_name, final_payload)

    def download_alert(self, folder_name, alert_name, all_alerts=False):
        """Download alert."""
        log.debug("Download alert: {0} from folder={1}".format(
            alert_name,
            folder_name,
        ))
        folder_uid = self._get_alert_folder_uid(folder_name)
        if folder_uid is None:
            log.error("Folder not found: {0}".format(folder_name))
            return None, False
        existing_alerts, error = self._list_alerts(folder_name)
        if error:
            log.error(error)
            return None, False

        new_rules = []
        try:
            rules = existing_alerts[0][folder_name][0]["rules"]
        except KeyError:
            # Skip this if the key does not exist
            rules = None
            log.debug("KeyError: Skipping folder_name={} as it does not exist in existing_alerts", folder_name)
            return None, False
        for r in rules:
            rule_title = r["grafana_alert"]["title"]
            if all_alerts or rule_title == alert_name:
                log.debug("Keeping alert: {0}".format(rule_title))
                new_rules.append(r)
            else:
                log.debug("Skipping alert: {0}".format(rule_title))

        if len(new_rules) == 0:
            log.warning("Alert not found: {0}".format(alert_name))
            return None, False

        existing_alerts[0][folder_name][0]["rules"] = new_rules
        return existing_alerts[0][folder_name][0], True
