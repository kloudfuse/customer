#!/usr/bin/python

import argparse
import json
import os
import sys
from typing import Optional, Union, Tuple

from loguru import logger as log

from grafana_client import GrafanaClient

def parse_args():
    """Grafana Dashboard Management Tool

    Common Arguments:
        -f, --dashboard-folder-name  dashboard folder name in Grafana
        -a, --grafana-address    Grafana server address
        -u, --grafana-username   Grafana username (default: admin)
        -p, --grafana-password   Grafana password (default: password)

    Examples:
        # Upload dashboards Operations
        # ----------------
        # Upload single dashboard file to a folder named "My dashboard Folder":
        python dashboard.py upload -s /path/to/dashboard.json \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload all dashboards from directory to a folder named "My dashboard Folder":
        python dashboard.py upload -d /path/to/dashboards/directory \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload dashboards from all folders (only one level down) within a root directory:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the upload.
        python dashboard.py upload -m /path/to/dashboards_root_directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "all"

        # Download dashboards Operations
        # ----------------
        # Download single dashboard named "dashboard Name" from a folder named "My dashboard Folder" in Grafana/dashboards tab:
        python dashboard.py download -s "dashboard Name" \
            -o /path/to/dashboard.json \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download all dashboards from a folder named "My dashboard Folder" in Grafana/dashboards tab to dashboards_file_name.json:
        python dashboard.py download -d -o /path/to/dashboards/download/directory \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download dashboards from all Grafana folders:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the download.
        python dashboard.py download -m -o /path/to/dashboards/download/directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "all"

    """


    parser = argparse.ArgumentParser(description="Grafana Dashboard Management Script")

    # Create parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parent_parser.add_argument(
        "-f",
        "--dashboard-folder-name",
        required=True,
        help="dashboard folder name in Grafana"
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

    # Main parser
    parser = argparse.ArgumentParser(
        description="Grafana Dashboard Management Tool"
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
        help='Upload dashboards to Grafana',
        parents=[parent_parser]
    )
    upload_mode = upload_parser.add_mutually_exclusive_group(
        required=True
    )
    upload_mode.add_argument(
        '-s',
        '--single-file',
        help='Path to single dashboard JSON file'
    )
    upload_mode.add_argument(
        '-d',
        '--directory',
        help='Path to directory containing multiple dashboards'
    )
    upload_mode.add_argument(
        '-m',
        '--multi-directory',
        help='Path to parent directory containing multiple folders of dashboards'
    )

    # Download command (similar structure)
    download_parser = subparsers.add_parser(
        'download',
        help='Download dashboards from Grafana',
        parents=[parent_parser]
    )
    # Add required output file argument
    download_parser.add_argument(
        '-o',
        '--output',
        required=True,
        help='Output file path to save dashboard configuration'
    )
    download_mode = download_parser.add_mutually_exclusive_group(
        required=True
    )
    download_mode.add_argument(
        '-s',
        '--dashboard-name',
        metavar='DASHBOARD_NAME',
        help='Download single dashboard to file'
    )
    download_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Download all dashboard from a grafana folder (directory)'
    )
    download_mode.add_argument(
        '-m',
        '--multi-directory',
        action='store_true',
        help='Download dashboards from all Grafana folders'
    )

    # Delete command (similar structure)
    # delete_parser = subparsers.add_parser(
    #     'delete',
    #     help='Delete alerts from Grafana',
    #     parents=[parent_parser]
    # )
    # delete_mode = delete_parser.add_mutually_exclusive_group(
    #     required=True
    # )
    # delete_mode.add_argument(
    #     '-s',
    #     '--dashboard-name',
    #     metavar='ALERT_NAME',
    #     help='Name of single alert to delete'
    # )
    # delete_mode.add_argument(
    #     '-d',
    #     '--directory',
    #     action='store_true',
    #     help='Delete all alerts in folder'
    # )


    return parser.parse_args()

class DashboardManager(object):
    from grafana_client import GrafanaClient

    def __init__(
            self,
            grafana_client: Optional[GrafanaClient] = None,
            dashboard_folder_name: Optional[str] = None,
    ):
        self.gc = grafana_client
        self.dashboard_folder_name = dashboard_folder_name

    def _valid_single_file_arg(self, file_path: str) -> Tuple[Union[dict, None], Union[int, None]]:
        """Validate and load Dashboard configuration from a JSON file.

        Args:
            file_path (str): Path to the JSON file containing dashboard configuration

        Returns:
            tuple: A tuple containing:
                - dict | None: Dashboard configuration if successful, None if failed
                - int | None: Error code (1) if failed, None if successful

        Example:
            >>> content, err = valid_single_file_arg("path/to/dashboard.json")
            >>> if err:
            >>>     print(f"Failed to load dashboard config: {err}")
        """
        if not os.path.isfile(file_path):
            log.error("File not found: {}", file_path)
            return None, 1
        try:
            with open(file_path, "r") as f:
                dashboard_content = json.load(f)
                log.debug(
                    "Successfully loaded dashboard configuration from {}",
                    file_path)
                if dashboard_content.get("dashboard") is None:
                    return dashboard_content, None
                else:
                    return dashboard_content["dashboard"], None
        except json.JSONDecodeError as e:
            log.error("Invalid JSON in file {}: {}", file_path, str(e))
            return None, 1
        except IOError as e:
            log.error("Error reading file {}: {}", file_path, str(e))
            return None, 1

class UploadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )

    def process_args(self, single_file, directory, multi_directory):
        log.error("single_file={}, directory={}, multi_directory={}", single_file, directory, multi_directory)
        if single_file:
            self._create_dashboard_from_one_file(single_file)
        elif directory:
            self._create_dashboards_from_dir(directory)
        elif multi_directory:
            self._create_dashboards_from_root_dir(multi_directory)
        else:
            log.error("Invalid arguments provided.")
            exit(1)
    
    def _create_dashboard_from_one_file(self, single_file):
        content, err = self._valid_single_file_arg(single_file)
        if err:
            exit(err)
        self.gc.upload_dashboard(content, self.dashboard_folder_name)

    def _create_dashboards_from_dir(self, directory, folder_name=None):
        for file in os.listdir(directory):
            if file.endswith(".json"):
                content, err = self._valid_single_file_arg(os.path.join(directory, file))
                if err:
                    exit(err)
                if folder_name:
                    self.gc.upload_dashboard(content, folder_name)
                else:
                    self.gc.upload_dashboard(content, self.dashboard_folder_name)

    def _create_dashboards_from_root_dir(self, multi_directory):
        for folder in os.listdir(multi_directory):
            folder_path = os.path.join(multi_directory, folder)
            if os.path.isdir(folder_path):
                self._create_dashboards_from_dir(folder_path, folder)

class DownloadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )

    def process_args(self, dashboard_name, directory, output, multi_directory):
        log.debug("dashboard_name={}, directory={}, multi_directory={}", dashboard_name, directory, multi_directory)
        if dashboard_name:
            self._download_single_dashboard_from_folder(dashboard_name, output)
        elif directory:
            self._download_all_dashboards_from_folder(self.dashboard_folder_name, output)
        elif multi_directory:
            self._download_all_dashboards_from_grafana(multi_directory)
        else:
            log.error("Invalid arguments provided.")
            exit(1)

    def _download_single_dashboard_from_folder(self, dashboard_name, output):
        log.debug("Downloading dashboard: {}", dashboard_name)
        dashboard_payload, found = self.gc.download_dashboard(
            dashboard_name,
        )
        if not found:
            log.error("Dashboard not found: {}", dashboard_name)
            exit(1)
        self._save_dashboard_to_file(dashboard_payload, output)

    def _download_all_dashboards_from_folder(self, folder_name, directory):
        log.debug("Downloading all dashboards from folder: {}", folder_name)
        dashboards_uids = self.gc.get_dashboard_uids_by_folder(folder_name=folder_name)
        for dashboard_uid in dashboards_uids:
            dashboard_payload, found = self.gc.download_dashboard(
                dashboard_uid,
                is_uid=True
            )
            if not found:
                log.error("Dashboard not found: {}", dashboard_uid)
                exit(1)
            title= dashboard_payload['dashboard']['title']
            title = title.replace(" ", "_")
            title = title.replace("/", "_")
            os.makedirs(directory, exist_ok=True)
            output_path = os.path.join(directory, f"{title}.json")
            self._save_dashboard_to_file(dashboard_payload, output_path)

    def _download_all_dashboards_from_grafana(self, multi_directory):
        log.debug("Downloading all dashboards from Grafana")
        find_folder_api = "/api/folders"
        folders_response = self.gc._http_get_request_to_grafana(find_folder_api)

        log.error("folders_response={}", folders_response)
        for folder in folders_response[0]:
            log.error("folder={}", folder)
            folder_name = folder["title"]
            folder_output_dir = os.path.join("./", folder_name)
            self._download_all_dashboards_from_folder(folder_name=folder_name, directory=folder_output_dir)


    def _save_dashboard_to_file(self, dashboard_payload, output_path):
        with open(output_path, 'w') as f:
            json.dump(dashboard_payload, f, indent=2)
        log.debug("Saved dashboard to file: {}", output_path)
            
    

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
    )

    dashboard_folder_name = args.dashboard_folder_name

    if args.command == "upload":
        i = UploadDashboard(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )
        i.process_args(
            single_file=args.single_file,
            directory=args.directory,
            multi_directory=args.multi_directory,
        )
    elif args.command == "download":
        e = DownloadDashboard(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )
        e.process_args(
            dashboard_name=args.dashboard_name,
            directory=args.directory,
            output=args.output,
            multi_directory=args.multi_directory,
        )
    else:
        log.error("Invalid command provided.")
        exit(1)
