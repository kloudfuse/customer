# Usage: python3 get_segment_status.py --table_name <TABLE_NAME> [--pinot_controller_port <PORT>]
# Example: python3 get_segment_status.py --table_name kf_logs_REALTIME --pinot_controller_port 9000
import argparse
from typing import List
import requests

def get_from_pinot(controller_port: str, table_name: str, path: str,
                   additional_params_str: str) -> List[str]:
    params = {"path": "/pinot/PROPERTYSTORE/SEGMENTS/" + table_name + additional_params_str}
    url = "http://localhost:" + controller_port + path
    headers = {"content-type": "application/json"}

    resp = requests.get(url, params=params, headers=headers, timeout=30000)
    if resp.status_code not in (200, 204):
        print("Status code: " + str(resp.status_code) + "; body = " + str(resp.json()))
        raise RuntimeError("failed to query pinot controller for segments")
    return resp.json()

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        description="Script to fetch status of segments from pinot-controller")
    parser.add_argument(
        "-p", "--pinot_controller_port", help="Pinot controller port (port forwarded locally)",
        default="9000", required=False
    )
    parser.add_argument(
        "-t", "--table_name", help="Pinot table to query against", required=True
    )
    args = parser.parse_args()

    segments_list = get_from_pinot(args.pinot_controller_port, args.table_name, "/zk/ls", "")
    for segment in segments_list:
        segment_metadata = get_from_pinot(args.pinot_controller_port, args.table_name,
                                          "/zk/get/", "/" + segment)
        print("Segment name: " + segment + ", status: " +\
               segment_metadata.get("simpleFields", {}).get("segment.realtime.status", ""))
    print(f"Total number of segments = {len(segments_list)}")
