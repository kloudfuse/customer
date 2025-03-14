# Usage:
# python3 create_notification_policies.py -g "http://<KFUSE_DNS_NAME>/grafana"
# -j <NR_ALERT_CONFIG>.json

import argparse
import json
import os
from itertools import chain
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader
from grafana_client import GrafanaClient, CONTACT_POINT_NAME_SUFFIX

NOTIFICATION_CHANNELS_KEY = "notification_channels"

class Matcher:
    def __init__(self, key: str, value_list: List) -> None:
        self.__key = key
        if len(value_list) > 1:
            self.__op = "=~"
            self.__value = "|".join(value_list)
        elif len(value_list) == 1:
            self.__op = "="
            self.__value = value_list[0]

    @staticmethod
    def from_list(l: List):
        m = Matcher('', [])
        m.__key = l[0]
        m.__op = l[1]
        m.__value = l[2]
        return m

    def as_dict(self) -> Dict:
        return {
            "key": self.__key,
            "op": self.__op,
            "value": self.__value,
        }

class Policy:
    __continue = True
    __nested_routes = json.dumps([])

    def __init__(self, channel: str, service_name:str, span_name_list: List,
                 append_suffix_to_receiver_name: bool) -> None:
        self.__channel = channel
        if append_suffix_to_receiver_name:
            self.__channel += CONTACT_POINT_NAME_SUFFIX
        self.__matchers = [Matcher("service_name", [service_name]), Matcher("kfuse_generated", ["true"])]
        if len(span_name_list) > 0:
            self.__matchers.append(Matcher("span_name", span_name_list))

    def set_continue(self, cont: bool) -> None:
        self.__continue = cont

    def is_policy_not_script_managed(self, known_policies: List[str]) -> bool:
        if self.__channel in known_policies:
            return False

        return not self.__channel.endswith(CONTACT_POINT_NAME_SUFFIX)

    @staticmethod
    def from_dict(d: Dict):
        p = Policy(d.get('receiver', ''), '', [], False)
        p.__continue = d.get('continue', False)
        p.__matchers = [Matcher.from_list(m) for m in d.get('object_matchers', [])]
        nested_routes = d.get('routes', [])
        p.__nested_routes = json.dumps(nested_routes)
        return p

    def as_dict(self) -> Dict:
        return {
            "channel": self.__channel,
            "continue": json.dumps(self.__continue),
            "matchers": [m.as_dict() for m in self.__matchers],
            "nested_routes": self.__nested_routes
        }

class RoutingPolicy:
    __policies = []
    __known_policies = []
    def __init__(self, services_config: List) -> None:
        for svc in services_config:
            for i, ch in enumerate(svc[NOTIFICATION_CHANNELS_KEY]):
                self.__known_policies.append(ch)
                policy = Policy(ch, svc['apm_name'], svc['transactions'], True)

                if i == len(svc[NOTIFICATION_CHANNELS_KEY]) - 1:
                    policy.set_continue(False)

                self.__policies.append(policy)

    def add_policies(self, policies: List[Policy]) -> None:
        self.__policies.extend(policies)

    def get_known_policies(self) -> List:
        return self.__known_policies

    def as_dict(self) -> Dict:
        return {
            "routing_policies": [p.as_dict() for p in self.__policies]
        }

def get_current_receivers_config(g: GrafanaClient) -> Dict:
    resp, success = g.get_alertmanager_config()
    if not success:
        raise RuntimeError("Failed to get existing alert manager config")

    if 'alertmanager_config' not in resp or 'receivers' not in resp['alertmanager_config']:
        raise RuntimeError("Receivers are not defined - run create_contact_points.py before "
                           + "running this script")

    return resp['alertmanager_config']['receivers'],\
        resp['alertmanager_config']['route'].get('routes', [])

def merge_policies(existing_policies: List[Policy], routing_policy: RoutingPolicy) -> None:
    known_policies = routing_policy.get_known_policies()
    ui_policies = [p for p in existing_policies if p.is_policy_not_script_managed(known_policies)]
    routing_policy.add_policies(ui_policies)

def create_notification_policies(g: GrafanaClient, json_file: str,
                                 skip_merge_existing_policies: bool) -> None:
    with open(json_file, 'r', encoding='utf-8') as f:
        j = f.readlines()
        config = json.loads(''.join(j))

    file_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(os.path.join(file_dir, "./files")))
    template = env.get_template("routing_policy_config.json")
    current_receivers_config, existing_routes = get_current_receivers_config(g)
    existing_policies = [Policy.from_dict(r) for r in existing_routes]
    services = [c.get('services', []) for c in config.get('clients', [])]
    policies = RoutingPolicy(list(chain.from_iterable(services)))
    
    if not skip_merge_existing_policies:
        merge_policies(existing_policies, policies)
    d = {'receivers': json.dumps(current_receivers_config)}
    d.update(policies.as_dict())
    routing_policy_json = template.render(d)
    
    success = g.update_alertmanager_config(routing_policy_json)
    if not success:
        raise RuntimeError("Failed to update alert manager config")
    print("Updated alert manager config with notification policies")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to create notification policies for alerts defined in NR alert"
         + " file config")
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
        "-s", "--skip_merge_existing_policies", help="Skip merging with existing policies",
        action=argparse.BooleanOptionalAction
    )
    parser.add_argument(
        "-j", "--nr_config_json", required=True,
        help="JSON file with NR alert policy config "\
            + "(which contains both service name and notification channels)"
    )
    args = parser.parse_args()
    gc = GrafanaClient(grafana_server=args.grafana_server, grafana_username=args.grafana_username,
                       grafana_password=args.grafana_passwd)
    create_notification_policies(gc, args.nr_config_json, args.skip_merge_existing_policies)
