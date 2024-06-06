#!/bin/bash
#
set -euo pipefail
#set -x

# Example usage: ./upload_dashboards.sh -g "https://<KFUSE_DNS_NAME>/grafana" -d modified_dashboards -n 63
# You can get the folder ID (-n <folder_id>) from grafana by running:
# curl -u "<username>:password>" "https://<KFUSE_DNS_NAME>/grafana/api/folders" | jq .
# Pick the ID of the folder from the output.

function upload_dashboards() {
   for FILENAME in $MODIFIED_DASHBOARD_DIR/*.json; do
     OUT=$(cat $FILENAME | jq --arg new_folder_id $NEW_FOLDER_ID\
	     '. * {overwrite: true, folderId: $new_folder_id|tonumber|floor,  dashboard: {id: null, uid: null}}'\
	     | curl --fail -X POST -H "Content-Type: application/json"\
	     --user "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_SERVER/api/dashboards/db"\
	     --write-out '%{http_code}' -d @- )
     if [ -z $OUT -o $OUT -gt 202 ]; then
       echo "Failed to upload dashboard $FILENAME; curl response status code = $OUT"
     fi
   done || exit 1
}

function usage() {
   echo "Usage: $0 -g <KFUSE_DNS_NAME/grafana> -d <dashboard_dir> [-u <grafana_username> -p <grafana_password>]" 1>&2
   exit 1
}

while getopts ":g:u:p:d:n:" o; do
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
	    MODIFIED_DASHBOARD_DIR=${OPTARG}
	    ;;
	n)
            NEW_FOLDER_ID=${OPTARG}
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

upload_dashboards
echo "Uploaded all modified dashboards from folder $MODIFIED_DASHBOARD_DIR"
