import argparse
import json
import requests


headers = {
    'accept': 'application/json'
}

def make_get_request(url, headers=None, params=None):
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()

def make_post_request(url, headers=None, data=None, json=None):
    response = requests.put(url, headers=headers, data=data, json=json)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response

def filter_response_by_field(url, segment_names, field_path, value, table):
    consumers = dict()
    getUrl = url + "zk/get?path=%2Fpinot%2FPROPERTYSTORE%2FSEGMENTS%2F" + table
    for s in segment_names:
        data = make_get_request(getUrl + "/" + s)
        if data['simpleFields']['segment.realtime.status'] == 'IN_PROGRESS':
            consumers[s] = data
    return consumers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Log ingest client')
    parser.add_argument('--dry-run', type=bool, default=False, required=False)
    parser.add_argument('--pinot-controller-port', type=str, default=9000, required=True)
    parser.add_argument('--table', type=str, default="kf_logs", required=True,
                        help="One of kf_logs_REALTIME or kf_metrics_REALTIME or kf_traces_REALTIME")

    args = parser.parse_args()

    url = "http://localhost:" + args.pinot_controller_port  + "/"
    listUrl = url + "zk/ls?path=%2Fpinot%2FPROPERTYSTORE%2FSEGMENTS%2F" + args.table
    response = make_get_request(listUrl, headers=headers)
    consuming_segments = filter_response_by_field(url, response, 'segment.realtime.status', 'CONSUMING', args.table)
    putUrl = url + "zk/put?path=%2Fpinot%2FPROPERTYSTORE%2FSEGMENTS%2F" + args.table
    print("found " + str(len(consuming_segments.items())) + " consuming segments")
    for c, v in consuming_segments.items():
        print("Consuming segment name " + str(c) + " startOffset " + v['simpleFields']['segment.realtime.startOffset'])
        v['simpleFields']['segment.realtime.startOffset'] = "0"
        v = json.dumps(v, indent=4)
        if not args.dry_run:
            print("Setting segment value to " + v)
            response = make_post_request(putUrl + "/" + c, data=v, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            print(response)
