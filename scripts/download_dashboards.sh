#!/bin/bash
#
set -euo pipefail
#set -x

# Example usage: ./download_dashboards.sh -g "https://<KFUSE_DNS_NAME>/grafana" -d files

function download_dashboards() {
  dashboards=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X GET $GRAFANA_SERVER/api/search?folderIds=0&query=&starred=false)
  for uid in $(echo $dashboards | jq -r '.[] | .uid'); do
    uid="${uid/$'\r'/}" # remove the trailing '/r'
    curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X GET "$GRAFANA_SERVER/api/dashboards/uid/$uid" | jq '.' > grafana-dashboard-$uid.json
    slug=$(cat grafana-dashboard-$uid.json | jq -r '.meta.slug')
    mv grafana-dashboard-$uid.json $DASHBOARD_DIR/grafana-dashboard-$uid-$slug.json # rename with dashboard name and id
    echo "Dashboard $uid exported"
  done
}

function usage() {
   echo "Usage: $0 -g <KFUSE_DNS_NAME/grafana> -d <dashboard_dir> [-u <grafana_username> -p <grafana_password>]" 1>&2
   exit 1
}

while getopts ":g:u:p:d:" o; do
    case "${o}" in
        g)
            GRAFANA_SERVER=${OPTARG}
            ;;
        p)
            gp=${OPTARG}
            ;;
	u)
	    gu=${OPTARG}
	    ;;
	d)
	    DASHBOARD_DIR=${OPTARG}
	    ;;
        *)
            echo "Unknown arg ${OPTARG}"
	    usage
            ;;
    esac
done
shift $((OPTIND-1))

GRAFANA_USER=${gu:-"admin"}
GRAFANA_PASSWORD=${gp:-"password"}

rm -rf $DASHBOARD_DIR
mkdir -p $DASHBOARD_DIR

download_dashboards
echo "Downloaded all dashboards to $DASHBOARD_DIR"
