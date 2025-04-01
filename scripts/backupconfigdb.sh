#!/bin/bash
set -x

S3_PATH=$1
NAMESPACE=$2

if [ -z "$NAMESPACE" ] ; then
  NAMESPACE=kfuse
fi

PGPW=`kubectl -n "$NAMESPACE" get secret kfuse-pg-credentials -o jsonpath="{.data.postgresql-password}" | base64 --decode ; echo`

if [ -z "$PGPW" ] ; then
  echo "Secret not found in the kfuse namespace"
  exit 1
fi

if [ -z "$S3_PATH" ] ; then
  echo "Usage: ./backupconfigdb.sh s3path [namespace]"
  exit 1
fi

DBS=("alertsdb" "beffedb" "hydrationdb" "logsconfigdb" "rbacdb" "apmconfigdb")

for DB in "${DBS[@]}"; do
  kubectl -n "$NAMESPACE" exec -it kfuse-configdb-0 -- bash -c "PGPASSWORD=$PGPW pg_dump -U postgres -d $DB" | gzip | aws s3 cp - "$S3_PATH/$DB.sql.gz"
done
