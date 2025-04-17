import yaml
import subprocess
import sys, requests
from requests.auth import HTTPBasicAuth
def construct_value(loader, node):
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            "while constructing a value",
            node.start_mark,
            "expected a scalar, but found %s" % node.id, node.start_mark
        )
    return str(node.value)
yaml.Loader.add_constructor(u'tag:yaml.org,2002:value', construct_value)

def load_values_yaml(file_path):
    with open(file_path, 'r') as file:
        try:
            values = yaml.load(file, Loader=yaml.Loader)  # Use the custom loader
            return values
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            sys.exit(1)

class RestClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)

    def _make_request(self, method, endpoint, data=None, headers=None):
        url = f"{self.base_url}{endpoint}"
        try:
            combined_headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
            if headers:
                combined_headers.update(headers)

            response = requests.request(method, url, json=data, headers=combined_headers, auth = self.auth)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def create_group(self, group_name):
        endpoint = "/groups/"
        data = {"name": group_name}
        return self._make_request("POST", endpoint, data)
    
    def get_groups(self):
        endpoint = "/groups/"
        return self._make_request("GET", endpoint)
    
    def get_users(self):
        endpoint = "/users/"
        return self._make_request("GET", endpoint)

    def add_user_to_group(self, group_id, user_id):
        endpoint = f"/groups/{group_id}/users"
        data = {"userId": user_id, "Permission": "Member"}
        return self._make_request("POST", endpoint, data)
    
    def create_policy(self, name, scope):
        endpoint = "/policies/"
        data = {
            "name": name,
            "scope": scope
        }
        return self._make_request("POST", endpoint, data)
    
    def create_rbac_config(self, group_name, policy_name):
        endpoint = "/rbacconfig/"
        data = {
            "group": group_name,
            "policy": policy_name
        }
        return self._make_request("POST", endpoint, data)

def main(file_path):
    values = load_values_yaml(file_path)
    base_url = "https://pisco.kloudfuse.io/rbac/"  # Adjust base URL as needed
    client = RestClient(base_url, "admin", "password")

    config = values.get('user-mgmt-service', {})
    groups = config['config']['groups']
    policies = config['config']['rbac_policies']
    rbac_configs = config['config']['rbac_configs']

    users_db = client.get_users()   

    for group in groups:
        group_name = group['name']
        print(f"Creating group: {group_name}")
        client.create_group(group_name)

    groups_db = client.get_groups()

    for group in groups:
        group_id = None
        user_id = None
        group_name = group['name']
        for grp in groups_db:
            if grp['name'] == group_name:
                group_id = grp['id']
                print (f"Found group: {group_name} with id: {group_id}")
                break
        for user in group['users']:
            user_email = user['value']
            for usr in users_db:
                if usr['email'] == user_email:
                    user_id = usr['id']
                    print (f"Found user: {user_email} with id: {user_id}")
                    break
        print(f"Adding user: {user_email} to group: {group_name}")
        if group_id is not None and user_id is not None:
            response = client.add_user_to_group(group_id, user_id)
            if response:
                print("User added to group:", response)
            else:
                print("Failed to add user to group.")
        else:
            print("User not found.")

    for policy in policies:
        policy_name = policy['name']
        policy_scope = policy['scope']

        response = client.create_policy(policy_name, policy_scope)
        if response:
            print("Policy created:", response)
        else:
            print("Failed to create policy.")

    for rbac_config in rbac_configs:
        group_name = rbac_config['group']
        policy_name = rbac_config['policy']
        print (f"Creating RBAC config: {group_name} - {policy_name}")
        response = client.create_rbac_config(policy_name, group_name)
        if response:
            print("RBAC configuration created:", response)
        else:
            print("Failed to create RBAC configuration.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python gescript.py <path-to-customer-values.yaml>")
        sys.exit(1)

    file_path = sys.argv[1]
    main(file_path)
