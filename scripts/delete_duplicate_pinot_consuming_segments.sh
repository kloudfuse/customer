#!/bin/bash

# create a dir for the table and run it from within that dir;
# it will dump a bunch of status files in case things go wrong we can use to track
# be careful on which controller you are connecting to

CONTROLLER=localhost:9000
TABLE=kf_metrics_FIXME

# Get a list of segments for a table
curl -s "http://${CONTROLLER}/tables/${TABLE}_REALTIME/consumingSegmentsInfo" > "${TABLE}.new"
echo "Total segments:"
cat "${TABLE}.new" | jq '._segmentToConsumingInfoMap | keys[]' | wc -l

cat "${TABLE}.new" | jq '._segmentToConsumingInfoMap | keys[]' | sed s'/"//'g > "${TABLE}"

# Filter out duplicate consuming
cat ${TABLE} | sort -r | awk -F__ '++seen[$2] == 2; seen[$2] >= 2' | uniq > "${TABLE}.to_be_deleted"


echo "Deleting the following segments"
cat ${TABLE}.to_be_deleted

echo -n "Press enter to proceed or ^C to cancel"
read ans

for seg in `cat "${TABLE}.to_be_deleted"`; do
    echo " deleting ${seg}"
    curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/$seg" -X 'DELETE'
done
