# Usage:
# python3 create_contact_points.py -g "https://<KFUSE_DNS_NAME>/grafana"
# -c ./files/sample_contact_points.csv

import os
import argparse
import csv
import json
from typing import Dict
from jinja2 import Environment, FileSystemLoader
from create_alerts import GrafanaClient
from grafana_client import CONTACT_POINT_NAME_SUFFIX

class Receiver:
    type = None
    name = None
    receiver = None

    def __init__(self, kwargs):
        self.type = kwargs.get("type")
        self.name = kwargs.get("contact_point_name")
        self.receiver = kwargs.get("receiver")
        self.template_body_file = kwargs.get("template_body_file")
        self.template_title_file = kwargs.get("template_title_file")

    def __read_file_contents(self, file: str) -> str:
        if len(file) == 0:
            return ""

        file_dir = os.path.dirname(__file__)
        full_path = os.path.join(file_dir, "files", file)

        with open(full_path, 'r', encoding='utf-8') as f:
            return ''.join(f.readlines())

    def as_dict(self):
        return {
            "type" : self.type,
            "name" : self.name + CONTACT_POINT_NAME_SUFFIX,
            "receiver" : self.receiver,
            "template_title": json.dumps(self.__read_file_contents(self.template_title_file)),
            "template_body": json.dumps(self.__read_file_contents(self.template_body_file))
        }

class ContactPointReceivers:
    def __init__(self, receivers: Dict):
        file_dir = os.path.dirname(__file__)
        env = Environment(loader=FileSystemLoader(
            os.path.join(file_dir, "./files")))
        self.template = env.get_template("receiver_template.json")
        self.receivers = {}
        for rec in receivers:
            self.receivers.update(
                {rec:json.loads(self.template.render(receivers[rec].as_dict()))})

def populate_receivers(contact_points_csv_file: str) -> Dict:
    contact_points = {}
    with open(contact_points_csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("contact_point_name") + CONTACT_POINT_NAME_SUFFIX
            contact_points.update({key: Receiver(row)})
    return contact_points

def merge_alertmanager_config(
        alertmanager_config: dict,
        cp_receivers: ContactPointReceivers) -> dict:

    existing_receivers = alertmanager_config['alertmanager_config']['receivers']
    unmanaged_receivers = [r for r in existing_receivers\
                     if not r['name'].endswith(CONTACT_POINT_NAME_SUFFIX)]

    alertmanager_config["alertmanager_config"]["receivers"] = unmanaged_receivers + list(cp_receivers.receivers.values())
    return alertmanager_config

def create_contact_points(g: GrafanaClient, contact_points_file: str) -> None:
    receivers = populate_receivers(contact_points_file)
    cp_receivers: ContactPointReceivers = ContactPointReceivers(receivers=receivers)
    alertmanager_config, success = g.get_alertmanager_config()
    if not success:
        raise RuntimeError("failed to get alertmanager config")
    updated_alertmanager_config = merge_alertmanager_config(alertmanager_config, cp_receivers)
    with open("./uploading_alertmanager_config.json", "w", encoding='utf-8') as cj:
        print("writing to ./uploading_alertmanager_config.json")
        cj.write(json.dumps(updated_alertmanager_config, indent=4, sort_keys=True))
    success = g.update_alertmanager_config(json.dumps(updated_alertmanager_config,
                                                       indent=4,
                                                       sort_keys=True))
    if not success:
        raise RuntimeError("failed to update alertmanager config")
    print("successfully updated alertmanager alert config.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to create contact points")
    parser.add_argument(
        "-g", "--grafana_server", help="Grafana server address", default="http://grafana.server",
        required=True
    )
    parser.add_argument(
        "-u", "--grafana_username", help="Grafana username", default="admin"
    )
    parser.add_argument(
        "-p", "--grafana_passwd", help="Grafana password", default="password"
    )
    parser.add_argument(
        "-c", "--contact_points_file", required=True,
        help="CSV file with config for contact points (absolute path)",
    )
    args = parser.parse_args()
    gc = GrafanaClient(grafana_server=args.grafana_server, grafana_username=args.grafana_username,
                       grafana_password=args.grafana_passwd)
    # import pdb
    # pdb.runcall(create_contact_points, gc, args.contact_points_file)
    create_contact_points(gc, args.contact_points_file)
