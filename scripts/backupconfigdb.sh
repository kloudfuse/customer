#!/bin/bash
set -x

S3_PATH=$1
PGPW=`kubectl get secret kfuse-pg-credentials -o jsonpath="{.data.postgresql-password}" | base64 --decode ; echo`

if [ -z "$S3_PATH" ] ; then
  echo "Usage: ./backupconfigdb.sh s3path"
  exit 1
fi

DBS=("alertsdb" "beffedb" "hydrationdb" "logsconfigdb" "rbacdb" "apmconfigdb")

for DB in "${DBS[@]}"; do
  kubectl exec -it kfuse-configdb-0 -- bash -c "PGPASSWORD=$PGPW pg_dump -U postgres -d $DB" | gzip | aws s3 cp - "$S3_PATH/$DB.sql.gz"
done
