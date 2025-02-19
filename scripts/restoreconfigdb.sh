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

echo "Storing original replica counts in ReplicaSet annotations..."
UMS_REPLICAS=$(get_or_set_replicas user-mgmt-service)
GRAFANA_REPLICAS=$(get_or_set_replicas kfuse-grafana)
TQS_REPLICAS=$(get_or_set_replicas trace-query-service)

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

echo "Scaling up services to original replica counts from ReplicaSet annotations..."
UMS_RS=$(kubectl describe deployment user-mgmt-service | grep "NewReplicaSet:" | awk '{print $2}')
GRAFANA_RS=$(kubectl describe deployment kfuse-grafana | grep "NewReplicaSet:" | awk '{print $2}')
TQS_RS=$(kubectl describe deployment trace-query-service | grep "NewReplicaSet:" | awk '{print $2}')

UMS_REPLICAS=$(kubectl get rs $UMS_RS -o=jsonpath='{.metadata.annotations.original-replicas}')
GRAFANA_REPLICAS=$(kubectl get rs $GRAFANA_RS -o=jsonpath='{.metadata.annotations.original-replicas}')
TQS_REPLICAS=$(kubectl get rs $TQS_RS -o=jsonpath='{.metadata.annotations.original-replicas}')

kubectl scale deployment user-mgmt-service --replicas=$UMS_REPLICAS >/dev/null 2>&1
kubectl scale deployment kfuse-grafana --replicas=$GRAFANA_REPLICAS >/dev/null 2>&1
kubectl scale deployment trace-query-service --replicas=$TQS_REPLICAS >/dev/null 2>&1

echo "Restore process completed!"
