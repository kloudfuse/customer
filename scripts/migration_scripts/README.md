# Grafana Alert & Dashboard Management Scripts

These Python scripts are provided for managing alerts and dashboards in Grafana. The scripts allow users to upload, download, and delete alerts and dashboards in specified folders within Grafana.

## Prerequisites
- Python 3.x
- Required Python packages: `requests`, `loguru`, `argparse` (use the requirements.txt file to install all the pakcages `pip3 install -r requirements.txt`)
- Access to a Grafana instance with API authentication


## Common Arguments
These arguments apply to both alert and dashboard scripts:

- `-f, --folder-name` : Grafana folder name
- `-a, --grafana-address` : Grafana server URL
- `-u, --grafana-username` : Grafana username (default: `admin`)
- `-p, --grafana-password` : Grafana password (default: `password`)
- `-v, --verify-ssl` : Disable SSL verification (default: enabled). Use this flag to skip SSL verification when connecting to Grafana.

---

# Alert Management
The `alert.py` script allows managing Grafana alerts, including uploading, downloading, and deleting alerts.

### Upload Alerts
Uploads alerts to a specific Grafana folder.

#### Upload a single alert:
```sh
python alert.py upload -s /path/to/alert.json \
    -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Upload multiple alerts from a directory:
```sh
python alert.py upload -d /path/to/alerts/directory \
    -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Upload alerts from multiple directories:
```sh
python alert.py upload -m /path/to/root_directory \
    -a http://<grafana-instance>/grafana \
    -u admin -p password \
    -f "placeholder"
```

### Download Alerts
Retrieves alerts from Grafana and saves them as JSON files.

#### Download a single alert:
```sh
python alert.py download -s "Alert Name" -o /path/to/alert.json \
    -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Download all alerts from a folder:
```sh
python alert.py download -d -o /path/to/alerts/download/ \
    -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Download alerts from all folders:
```sh
python alert.py download -m -o /path/to/alerts/download/ \
    -a http://<grafana-instance>/grafana \
    -u admin -p password \
    -f "placeholder"
```

### Delete Alerts
Removes alerts from Grafana.

#### Delete a single alert:
```sh
python alert.py delete -s "Alert Name" \
    -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Delete all alerts in a folder:
```sh
python alert.py delete -d -f "My Alert Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

---

# Dashboard Management
The `dashboard.py` script allows uploading and downloading dashboards.

### Upload Dashboards
Uploads dashboards to a specified folder in Grafana.

#### Upload a single dashboard:
```sh
python dashboard.py upload -s /path/to/dashboard.json \
    -f "My Dashboard Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Upload all dashboards from a directory:
```sh
python dashboard.py upload -d /path/to/dashboards/directory \
    -f "My Dashboard Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Upload dashboards from multiple directories:
```sh
python dashboard.py upload -m /path/to/dashboards_root_directory \
    -a http://<grafana-instance>/grafana \
    -u admin -p password \
    -f "all"
```

### Download Dashboards
Retrieves dashboards from Grafana and saves them as JSON files.

#### Download a single dashboard:
```sh
python dashboard.py download -s "Dashboard Name" -o /path/to/dashboard.json \
    -f "My Dashboard Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Download all dashboards from a folder:
```sh
python dashboard.py download -d -o /path/to/dashboards/download/ \
    -f "My Dashboard Folder" \
    -a http://<grafana-instance>/grafana \
    -u admin -p password
```

#### Download dashboards from all folders:
```sh
python dashboard.py download -m -o /path/to/dashboards/download/ \
    -a http://<grafana-instance>/grafana \
    -u admin -p password \
    -f "all"
```

---

## Notes
- Replace `<grafana-instance>` with the actual Grafana server URL.
- Ensure the API credentials used have the necessary permissions to manage alerts and dashboards.
- The `-f` flag is required but serves as a placeholder in some multi-directory operations.

This documentation provides a structured guide for efficiently managing Grafana alerts and dashboards through the provided scripts.

