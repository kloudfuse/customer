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

class PinotControllerClient(object):
    def __init__(self, port, table) -> None:
        self.pinot_controller_port = port
        self.table = table
        self.base_url = "http://localhost:" + self.pinot_controller_port  + "/"
        self.consuming_segments_url = None
        self.segment_metadata_url = None
        self.segment_metadata_put_url = None
        self._create_urls()

    def _create_urls(self):
        self.consuming_segments_url = "{0}tables/{1}/consumingSegmentsInfo".format(self.base_url, self.table)
        base_path = "path=%2Fpinot%2FPROPERTYSTORE%2FSEGMENTS%2F"
        self.segment_metadata_url = "{0}zk/get?{1}{2}".format(self.base_url, base_path, self.table)
        self.segment_metadata_put_url = "{0}zk/put?{1}{2}".format(self.base_url, base_path, self.table)

    def get_consuming_segments_list(self):
        response = make_get_request(self.consuming_segments_url, headers=headers)
        # for k in response['_segmentToConsumingInfoMap']:
        #     segments.append(k)
        #     # print(k, response['_segmentToConsumingInfoMap'][k])
        # print(len(segments))
        # return segments
        return list(response['_segmentToConsumingInfoMap'].keys())

    def get_segments_metadata(self, consuming_segments):
        segment_to_metadata_dict = dict()
        for segment in consuming_segments:
            metadata = make_get_request(self.segment_metadata_url + "/" + segment)
            if metadata['simpleFields']['segment.realtime.status'] == 'IN_PROGRESS':
                segment_to_metadata_dict[segment] = metadata
            else:
                print("Warning. Segment={0} is not InProgress".format(segment))
                print(metadata['simpleFields']['segment.realtime.status'])
                # Since it is best effort, not erroring on it
        return segment_to_metadata_dict

    def reset_segment_state(self, segment_to_metadata_dict):
        for segment, metadata in segment_to_metadata_dict.items():
            print("Consuming segment name={0}, startOffset={1}".format(
                str(segment),
                metadata['simpleFields']['segment.realtime.startOffset']))
            metadata['simpleFields']['segment.realtime.startOffset'] = "0"
            metadata = json.dumps(metadata, indent=4)
            if not args.dry_run:
                print("Setting segment value to " + metadata)
                response = make_post_request(
                    self.segment_metadata_put_url + "/" + segment, 
                    data=metadata, 
                    headers=headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
                print(response)


def parse_args():
    parser = argparse.ArgumentParser(description='Client to reset consuming state')
    parser.add_argument('--dry-run', type=bool, default=False, required=False)
    parser.add_argument('--pinot-controller-port', 
                        type=str, 
                        default=9000, 
                        required=False,
                        help="Port forward for PinotController")
    parser.add_argument('--table', 
                        type=str,
                        default="kf_logs_REALTIME", 
                        required=True,
                        choices=['kf_logs_REALTIME',
                                 'kf_metrics_REALTIME',
                                 'kf_events_REALTIME',
                                 'kf_metrics_rollup_REALTIME',
                                 'kf_traces_errors_REALTIME',
                                 'kf_traces_REALTIME'],
                        help="Specify Pinot Tables")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    pc = PinotControllerClient(
        port=args.pinot_controller_port, 
        table=args.table)

    consuming_segments = pc.get_consuming_segments_list()
    segment_to_metadata_dict = pc.get_segments_metadata(consuming_segments)
    pc.reset_segment_state(segment_to_metadata_dict)
