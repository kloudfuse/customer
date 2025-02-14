#!/bin/bash
set -x

S3_PATH=$1

if [ -z "$S3_PATH" ] ; then
  echo "Usage: ./backupconfigdb.sh s3path"
  exit 1
fi

DBS=("alertsdb" "beffedb" "hydrationdb" "logsconfigdb" "rbacdb" "apmconfigdb")

for DB in "${DBS[@]}"; do
  kubectl exec -it kfuse-configdb-0 -- bash -c "PGPASSWORD=password pg_dump -U postgres -d $DB" | gzip | aws s3 cp - "$S3_PATH/$DB.sql.gz"
done
