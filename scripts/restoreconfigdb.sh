#!/bin/bash
set -x

S3_PATH=$1

if [ -z "$S3_PATH" ] ; then
  echo "Usage: ./restoreconfigdb.sh s3path"
  exit 1
fi

DBS=("alertsdb" "beffedb" "hydrationdb" "logsconfigdb" "rbacdb" "apmconfigdb")

# Function to get or set original replicas using ReplicaSet annotations
get_or_set_replicas() {
    local deployment=$1
    
    # Get the newest ReplicaSet directly from deployment
    RS_NAME=$(kubectl describe deployment $deployment | grep "NewReplicaSet:" | awk '{print $2}')
    
    # Try to get existing annotation first
    ORIGINAL_REPLICAS=$(kubectl get rs $RS_NAME -o=jsonpath='{.metadata.annotations.original-replicas}' 2>/dev/null)
    
    if [ -z "$ORIGINAL_REPLICAS" ]; then
        # If annotation doesn't exist, get current replicas and set annotation
        ORIGINAL_REPLICAS=$(kubectl get deployment $deployment -o=jsonpath='{.spec.replicas}')
        kubectl annotate rs $RS_NAME original-replicas=$ORIGINAL_REPLICAS --overwrite
    fi
    
    echo $ORIGINAL_REPLICAS
}

get_replica_count(){
  local deployment=$1
  local rs_name=$(kubectl describe deployment $deployment | grep "NewReplicaSet:" | awk '{print $2}')
  local replicas=$(kubectl get rs $rs_name -o=jsonpath='{.metadata.annotations.original-replicas}')
  echo $replicas
}

scale_deployment() {
  local deployment=$1
  local replicas=$2
  kubectl scale deployment $deployment --replicas=$replicas >/dev/null 2>&1
}

SERVICES=("user-mgmt-service" "kfuse-grafana" "trace-query-service")

echo "Storing original replica counts in ReplicaSet annotations..."
for service in "${SERVICES[@]}"; do
  if ! get_or_set_replicas $service; then
        echo "Failed to process replica count for $service. Exiting." >&2
    exit 1
  fi
  scale_deployment $service 0
done

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

echo "Scaling up services to original replica counts from ReplicaSet annotations..."
for service in "${SERVICES[@]}"; do
  replicas=$(get_replica_count $service)
  scale_deployment $service $replicas
done

echo "Restore process completed!"
