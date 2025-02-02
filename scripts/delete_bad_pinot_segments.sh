#!/bin/bash

# create a dir for the table and run it from within that dir;
# it will dump a bunch of status files in case things go wrong we can use to track
# be careful on which controller you are connecting to

CONTROLLER=localhost:9000
TABLE=kf_metrics_rollup_FIXME

# Get a list of segments for a table
curl -s "http://${CONTROLLER}/tables/${TABLE}_REALTIME/segmentsStatus" > "${TABLE}.new"
echo "Total segments:"
cat "${TABLE}.new" | jq '.[].segmentName' | wc -l

# Filter out good segments
cat "${TABLE}.new" | jq '.[] | select(.segmentStatus != "GOOD") | .segmentName' | sed s'/"//'g > "${TABLE}.bad"
echo "Deleting !GOOD segments:"
wc -l "${TABLE}.bad"

echo -n "Press enter to proceed or ^C to cancel"
read ans

# Fetch segment status
for seg in `cat "${TABLE}.bad"`; do
    curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/$seg/metadata?columns=\*" > "${seg}.status"
    cat "${seg}.status"
    #read ans
    echo " deleting ${seg}"
    curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/$seg" -X 'DELETE'
done
