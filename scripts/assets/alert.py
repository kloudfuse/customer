#!/usr/bin/python

import argparse
import json
import os
import sys
from typing import Optional, Union, Tuple

from loguru import logger as log

from common.grafana_client import GrafanaClient


def parse_args():
    """Grafana Alert Management Tool

    Common Arguments:
        -f, --alert-folder-name  Alert folder name in Grafana
        -a, --grafana-address    Grafana server address
        -u, --grafana-username   Grafana username (default: admin)
        -p, --grafana-password   Grafana password (default: password)

    Examples:
        # Upload Alerts Operations
        # ----------------
        # Upload single alert file to a folder named "My Alert Folder":
        python alert.py upload -s /path/to/alert.json \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload all alerts from directory to a folder named "My Alert Folder":
        python alert.py upload -d /path/to/alerts/directory \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload alerts from all folders (only one level down) within a root directory:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the upload.
        python alert.py upload -m /path/to/root_directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "placeholder"

        # Download Alerts Operations
        # ----------------
        # Download single alert named "Alert Name" from a folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py download -s "Alert Name" \
            -o /path/to/alert.json \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download all alerts from a folder named "My Alert Folder" in Grafana/Alerts tab to alerts_file_name.json:
        python alert.py download -d -o /path/to/alerts/download/directory/ \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download alerts from all Grafana folders:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the download.
        python alert.py download -m -o /path/to/alerts/download/directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "placeholder"

        # Delete Operations
        # ----------------
        # Delete single alert named "Alert Name" from a folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py delete -s "Alert Name" \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Delete all alerts in folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py delete -d -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password
    """
    # Create parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parent_parser.add_argument(
        "-f",
        "--alert-folder-name",
        required=True,
        help="Alert folder name in Grafana"
    )
    parent_parser.add_argument(
        "-a",
        "--grafana-address",
        required=True,
        help="Grafana server address (e.g., http://grafana.example.com)"
    )
    parent_parser.add_argument(
        "-u",
        "--grafana-username",
        default="admin",
        help="Grafana username"
    )
    parent_parser.add_argument(
        "-p",
        "--grafana-password",
        default="password",
        help="Grafana password"
    )
    parent_parser.add_argument(
        "-v",
        "--verify-ssl",
        action='store_false',
        help="Verify SSL certificate (default: True)"
    )

    # Main parser
    parser = argparse.ArgumentParser(
        description="Grafana Alert Management Tool"
    )

    # Create command subparsers
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        help='Command to execute (upload/download/delete)'
    )

    # Upload command
    upload_parser = subparsers.add_parser(
        'upload',
        help='Upload alerts to Grafana',
        parents=[parent_parser]
    )
    upload_mode = upload_parser.add_mutually_exclusive_group(
        required=True
    )
    upload_mode.add_argument(
        '-s',
        '--single-file',
        help='Upload alert(s) from a single JSON file'
    )
    upload_mode.add_argument(
        '-d',
        '--directory',
        help='Upload all JSON files from directory'
    )
    upload_mode.add_argument(
        '-m',
        '--multi-directory',
        help='Directory containing multiple subdirectories with alerts'
    )

    # Download command (similar structure)
    download_parser = subparsers.add_parser(
        'download',
        help='Download alerts from Grafana',
        parents=[parent_parser]
    )
    # Add required output file argument
    download_parser.add_argument(
        '-o',
        '--output',
        required=True,
        help='Output file path to save alert configuration'
    )
    download_mode = download_parser.add_mutually_exclusive_group(
        required=True
    )
    download_mode.add_argument(
        '-s',
        '--alert-name',
        metavar='ALERT_NAME',
        help='Download single alert to file'
    )
    download_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Download all alerts to directory'
    )
    download_mode.add_argument(
        '-m',
        '--multi-directory',
        action='store_true',
        help='Download alerts from all Grafana folders'
    )

    # Delete command (similar structure)
    delete_parser = subparsers.add_parser(
        'delete',
        help='Delete alerts from Grafana',
        parents=[parent_parser]
    )
    delete_mode = delete_parser.add_mutually_exclusive_group(
        required=True
    )
    delete_mode.add_argument(
        '-s',
        '--alert-name',
        metavar='ALERT_NAME',
        help='Name of single alert to delete'
    )
    delete_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Delete all alerts in folder'
    )

    return parser.parse_args()


class AlertManager(object):
    from common.grafana_client import GrafanaClient

    def __init__(
            self,
            grafana_client: Optional[GrafanaClient] = None,
            alert_folder_name: Optional[str] = None,
    ):
        self.gc = grafana_client
        self.alert_folder_name = alert_folder_name

    def _valid_single_file_arg(self, file_path: str) -> Tuple[Union[dict, None], Union[int, None]]:
        """Validate and load alert configuration from a JSON file.

        Args:
            file_path (str): Path to the JSON file containing alert configuration

        Returns:
            tuple: A tuple containing:
                - dict | None: Alert configuration if successful, None if failed
                - int | None: Error code (1) if failed, None if successful

        Example:
            >>> content, err = valid_single_file_arg("path/to/alert.json")
            >>> if err:
            >>>     print(f"Failed to load alert config: {err}")
        """
        if not os.path.isfile(file_path):
            log.error("File not found: {}", file_path)
            return None, 1
        try:
            with open(file_path, "r") as f:
                alert_content = json.load(f)
                log.debug(
                    "Successfully loaded alert configuration from {}",
                    file_path)
                return alert_content, None
        except json.JSONDecodeError as e:
            log.error("Invalid JSON in file {}: {}", file_path, str(e))
            return None, 1
        except IOError as e:
            log.error("Error reading file {}: {}", file_path, str(e))
            return None, 1


class UploadAlert(AlertManager):
    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )

    def process_args(self, single_file, directory, multi_directory):
        if single_file:
            self._create_alert_from_one_file(single_file)
        elif directory:
            self._create_alert_from_dir(directory)
        elif multi_directory:
            self._create_alerts_from_multi_dir(multi_directory)
        else:
            log.error("Invalid arguments provided.")
            exit(1)

    @staticmethod
    def _process_rules(file_content: dict) -> list:
        rules = file_content.get("rules")
        if not rules:
            log.error("No rules found in alert config.")
            exit(1)
        # Remove uid & namespace_uid fields from each rule as they will not allow overriding existing rules
        for rule in rules:
            grafana_alert = rule.get("grafana_alert")
            try:
                grafana_alert.pop("uid", None)
            except AttributeError:
                log.debug("No uid or  found in alert config.")
            try:
                grafana_alert.pop("namespace_uid", None)
            except AttributeError:
                log.debug("No namespace_uid or  found in alert config.")
        file_content["rules"] = rules
        return file_content

    def _create_alert_from_one_file(self, file_path: str) -> bool:
        file_content, err = self._valid_single_file_arg(file_path)
        if err:
            return False
        log.debug("file content: {}", file_content)
        # Typically, existing rules have some fields associated with them 
        # which is added by grafana (say, uid, namespace_uid). This is either 
        # auto generated or done as a part of the grafana alert creation 
        # internal workflow.
        stripped_file_content = self._process_rules(file_content)
        return self.gc.create_alert(
            self.alert_folder_name,
            json.dumps(stripped_file_content),
        )

    def _create_alert_from_dir(self, directory, subdir=None):
        log.debug("Processing directory: {} {}", directory, subdir)
        if not os.path.isdir(directory):
            log.error("Directory not found: {}", directory)
            return
        
        for root, _, files in os.walk(directory):
            for file in files:
                alert_payload = {
                    "interval": None,
                    "name": None,
                    "rules": []
                }
                if not file.endswith(".json"):
                    log.warning("Skipping non-JSON file: {}", file)
                    continue
                file_path = os.path.join(root, file)
                log.debug("Processing file: {}", file_path)
                file_content, err = self._valid_single_file_arg(file_path)
                if err:
                    log.error(
                        "Failed to load alert config from {}. Err={}",
                        file_path, err,
                    )
                    exit(-1)
                cleaned_file_content = self._process_rules(file_content)
                if alert_payload["interval"] is None:
                    alert_payload["interval"] = cleaned_file_content.get("interval")
                if alert_payload["name"] is None:
                    alert_payload["name"] = cleaned_file_content.get("name")
                rules = cleaned_file_content.get("rules")
                for rule in rules:
                    alert_payload["rules"].append(rule)
                if subdir != None:
                    self.gc.create_alert(subdir, json.dumps(alert_payload)) 
                else:
                    self.gc.create_alert(self.alert_folder_name, json.dumps(alert_payload))
    
    def _create_alerts_from_multi_dir(self, root_directory: str):
        subdirectories = [d for d in os.listdir(root_directory) if os.path.isdir(os.path.join(root_directory, d))]
        for subdir in subdirectories:
            log.debug("Pre-Processing directory: {} {}", root_directory, subdir)
            self._create_alert_from_dir(os.path.join(root_directory, subdir), subdir)


class DownloadAlert(AlertManager):
    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )

    def _validate_file(self, file_path: str) -> bool:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create file if it doesn't exist
            if not os.path.exists(file_path):
                log.debug("Creating new file: {}", file_path)
                with open(file_path, 'w') as f:
                    f.write('')
            return True
        except OSError as e:
            log.error("Failed to create file {}: {}", file_path, str(e))
            return False

    def process_args(self, alert_name, directory, output, multi_directory):
        valid = self._validate_file(output)
        if not valid:
            log.error("Invalid output file path: {}", output)
            exit(1)

        if alert_name:
            self._download_single_alert(alert_name, output)
        elif directory:
            self._download_alerts_from_folder(self.alert_folder_name, output)
        elif multi_directory:
            self._download_alerts_from_all_folders(output)
        else:
            log.error("No valid download option provided.")
    
    def _download_single_alert(self, alert_name, output):
        log.debug("Downloading alert: {}", alert_name)
        alert_payload, found = self.gc.download_alert(
            self.alert_folder_name,
            alert_name,
        )
        if not found:
            log.error("Alert not found: {}", alert_name)
            exit(1)
        self._save_alert_to_file(alert_payload, output)

    def _download_alerts_from_folder(self, folder_name, output):
        log.debug("Downloading alerts from folder: {}", folder_name)
        alert_payload, found = self.gc.download_alerts_folder(
            folder_name,
        )
        if not found:
            log.error("Error downloading alerts from folder: {}", folder_name)
            exit(1)
        # payload for folder comes in the format ({'folder_name': [alert_rule_group]}) - So we need to first extract just the folder name list and then iterate over it
        try:
            for alert_rule_group in alert_payload[0][folder_name]:
                alert_group_name = alert_rule_group.get("name")
                output_path = os.path.join(output, f"{alert_group_name}.json")
                os.makedirs(output, exist_ok=True)
                self._save_alert_to_file(alert_rule_group, output_path)
        except Exception as e: 
            log.debug("Error downloading alerts from folder: {} Error {}", folder_name, e)

    def _download_alerts_from_all_folders(self, output_dir):
        find_folder_api = "/api/folders"
        folders_response = self.gc._http_get_request_to_grafana(find_folder_api)
        log.debug("Output DIR: {}", output_dir)
        if os.path.exists(output_dir) and os.path.isfile(output_dir):
            # Remove the file
            os.remove(output_dir)
            log.debug(f"File {output_dir} has been removed.")
        else:
            log.debug(f"File {output_dir} does not exist.")
        # Ensure output_dir is a directory
        if not os.path.exists(output_dir):
            log.debug("Creating directory: {}", output_dir)
            os.makedirs(output_dir, exist_ok=True)
        elif not os.path.isdir(output_dir):
            log.error("Output path exists and is not a directory: {}", output_dir)
            return
        for folder in folders_response[0]:
            folder_name = folder['title']
            folder_output_path = os.path.join(output_dir, folder_name)
            log.debug("Downloading alerts from folder: {}", folder_name)
            self._download_alerts_from_folder(folder_name, folder_output_path)

    def _save_alert_to_file(self, alert_payload, output_path):
        with open(output_path, 'w') as f:
            json.dump(alert_payload, f, indent=2)
        log.debug("Saved alerts to file: {}", output_path)


class DeleteAlert(AlertManager):
    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )

    def process_args(self, alert_name, directory):
        if alert_name:
            res = self.gc.delete_alert(
                self.alert_folder_name,
                alert_name,
            )
            log.debug("Single alert deletion response: {}", res)
        elif directory:
            res = self.gc.delete_alert(
                self.alert_folder_name,
                None,
                delete_all=True,
            )
            log.debug("All alert deletion response: {}", res)
        else:
            log.error("Invalid arguments provided.")
            exit(1)


if __name__ == "__main__":
    log.info("Executing={}", ' '.join(sys.argv))
    args = parse_args()

    if args.debug:
        log.remove()
        log.add(sys.stderr, level="DEBUG")

    grafana_client = GrafanaClient(
        grafana_server=args.grafana_address,
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        verify_ssl=args.verify_ssl,
    )
    alert_folder_name = args.alert_folder_name

    if args.command == "upload":
        i = UploadAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        i.process_args(
            single_file=args.single_file,
            directory=args.directory,
            multi_directory=args.multi_directory,
        )
    elif args.command == "download":
        e = DownloadAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        e.process_args(
            alert_name=args.alert_name,
            directory=args.directory,
            output=args.output,
            multi_directory=args.multi_directory,
        )
    elif args.command == "delete":
        d = DeleteAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        d.process_args(
            alert_name=args.alert_name,
            directory=args.directory,
        )
    else:
        log.error("Invalid command provided.")
        exit(1)
