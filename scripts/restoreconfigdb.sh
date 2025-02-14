#!/bin/bash
set -x

S3_PATH=$1

if [ -z "$S3_PATH" ] ; then
  echo "Usage: ./restoreconfigdb.sh s3path"
  exit 1
fi

DBS=("alertsdb" "beffedb" "hydrationdb" "logsconfigdb" "rbacdb" "apmconfigdb")

echo "Scaling down services..."
kubectl scale deployment user-mgmt-service --replicas=0 >/dev/null 2>&1
kubectl scale deployment kfuse-grafana --replicas=0 >/dev/null 2>&1
kubectl scale deployment trace-query-service --replicas=0 >/dev/null 2>&1

sleep 30  # Wait for services to scale down

echo "Dropping and recreating databases..."
for DB in "${DBS[@]}"; do
  kubectl exec -i kfuse-configdb-0 -- bash -c "PGPASSWORD=password psql -U postgres -q -c \"\pset format unaligned; DROP DATABASE IF EXISTS $DB;\"" >/dev/null 2>&1
  kubectl exec -i kfuse-configdb-0 -- bash -c "PGPASSWORD=password psql -U postgres -q -c \"\pset format unaligned; CREATE DATABASE $DB;\"" >/dev/null 2>&1
done

echo "Restoring databases..."
for DB in "${DBS[@]}"; do
  echo "Restoring $DB..."
  aws s3 cp "$S3_PATH/$DB.sql.gz" - | gzip -d | \
    kubectl exec -i kfuse-configdb-0 -- bash -c "PGPASSWORD=password psql -U postgres -d $DB -q" 2>&1 | grep -v "already exists" || true
done

echo "Scaling up services..."
kubectl scale deployment user-mgmt-service --replicas=1 >/dev/null 2>&1
kubectl scale deployment kfuse-grafana --replicas=1 >/dev/null 2>&1
kubectl scale deployment trace-query-service --replicas=1 >/dev/null 2>&1

echo "Restore process completed!"
