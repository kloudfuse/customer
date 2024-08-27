import requests
import json

# Define the Pinot server host and port
PINOT_HOST = 'http://localhost'
PINOT_PORT = '61733'  # Default controller port

# Endpoint to retrieve all schemas
SCHEMA_ENDPOINT = f"{PINOT_HOST}:{PINOT_PORT}/schemas/kf_logs"

def get_schema():
    try:
        response = requests.get(SCHEMA_ENDPOINT)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()  # Return the JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schemas: {e}")
        return None

def get_table_config():
    try:
        table_config_endpoint = f"{PINOT_HOST}:{PINOT_PORT}/tableConfigs/kf_logs"
        response = requests.get(table_config_endpoint)
        response.raise_for_status()
        return response.json()  # Return the JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching table config for: {e}")
        return None

def add_string_column_to_schema(schema):
    new_column = {
        "name": "log_line",
        "dataType": "STRING",
        "maxLength": 1048576
    }
    # Append the new column to the schema's 'dimensionFieldSpecs'
    if 'dimensionFieldSpecs' not in schema:
        schema['dimensionFieldSpecs'] = []
    schema['dimensionFieldSpecs'].append(new_column)
    return schema

def update_schema(updated_schema):
    schema_name = "kf_logs"
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.put(f"{SCHEMA_ENDPOINT}", 
                                data=json.dumps(updated_schema), 
                                headers=headers)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating schema")
        return None

def update_config(table_config):
    column_name = "log_line"
    table_indexing_config = table_config['realtime']['tableIndexConfig']
    if 'noDictionaryColumns' not in table_indexing_config:
        table_indexing_config['noDictionaryColumns'] = []
    if column_name not in table_indexing_config['noDictionaryColumns']:
        table_indexing_config['noDictionaryColumns'].append("log_line")
    if 'noDictionaryConfig' not in table_indexing_config:
        table_indexing_config['noDictionaryConfig'] = []
    if column_name not in table_indexing_config['noDictionaryConfig']:
        table_indexing_config['noDictionaryConfig']["log_line"] = "ZSTANDARD"
    new_field_config = {
        "name": "log_line",
        "encodingType":"RAW",
        "indexTypes":["TEXT"],
        "properties":{"useANDForMultiTermTextIndexQueries":"true"}
    }
    field_exists = any(f['name'] == "log_line" for f in table_config["realtime"]['fieldConfigList'])
    if not field_exists:
        table_config["realtime"]['fieldConfigList'].append(new_field_config)
    else:
        print(f"Field {column_name} already exists in fieldConfigList.")
    return table_config


def update_table_config(updated_table_config):
    table_config_endpoint = f"{PINOT_HOST}:{PINOT_PORT}/tableConfigs/kf_logs"
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.put(table_config_endpoint,
                                data=json.dumps(updated_table_config),
                                headers=headers)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating table config : {e}")
        return None


def main():
    schema = get_schema()
    print(schema)

    updated_schema = add_string_column_to_schema(schema)
    print(f"Updated schema with new column log_line")
    print(json.dumps(updated_schema, indent=2))
    result = update_schema(updated_schema)
    if result:
        print(f"Schema successfully updated.")
    else:
        print(f"Failed to update schema")

    table_config = get_table_config()
    print(table_config)
    updated_table_config = update_config(table_config)
    print(f"Updated table config")
    print(json.dumps(updated_table_config, indent=2))
    update_table_config(updated_table_config)

if __name__ == "__main__":
    main()
