set -ex;

# This script creates a new PVC named data-kafka-broker-* that is identical to the old kafka PVC
# It attaches the new PVC to the original PV and removes the old PVC
# It also deletes the kakfa STS in preparation for the upgrade

if ! jq --version &> /dev/null
then
  echo "jq is not installed, please install jq and rerun the script"
  exit 1
fi

broker=$1
namespace=$2

if [ -z "$broker" ]; then
echo "Usage: ./kafka-upgrade.sh <number of kafka pods> [namespace]"
exit 1
fi

if [ -z "$namespace" ]; then
  namespace="kfuse"
fi

i=0

while [ $i -lt $broker ]; do
  REPLICA=$i
  OLD_PVC="data-kafka-${REPLICA}"
  PV_NAME=$(kubectl -n $namespace get pvc $OLD_PVC -o jsonpath="{.spec.volumeName}")
  NEW_PVC="data-kafka-broker-${REPLICA}"
  NEW_PVC_MANIFEST_FILE="$NEW_PVC.yaml"

  # save old pvc yaml
  kubectl -n $namespace get pvc $OLD_PVC -o yaml > "$OLD_PVC.yaml"

  # Create new PVC manifest
  kubectl -n $namespace get pvc $OLD_PVC -o json | jq "
    .metadata.name = \"$NEW_PVC\"
    | with_entries(
        select([.key] |
          inside([\"metadata\", \"spec\", \"apiVersion\", \"kind\"]))
      )
    | del(
        .metadata.annotations, .metadata.creationTimestamp,
        .metadata.finalizers, .metadata.resourceVersion,
        .metadata.selfLink, .metadata.uid, .metadata.deletionTimestamp,
        .metadata.deletionGracePeriodSeconds
      )
    " > $NEW_PVC_MANIFEST_FILE

  # dump new manifest
  cat $NEW_PVC_MANIFEST_FILE

  # Modify PV reclaim policy and remove claim reference
  kubectl -n $namespace patch pv $PV_NAME -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
  kubectl -n $namespace patch pv $PV_NAME -p '{"spec":{"claimRef": null}}'
  kubectl -n $namespace apply -f $NEW_PVC_MANIFEST_FILE
  i=$((i + 1))
done

kubectl delete sts kafka --wait=true

i=0
while [ $i -lt $broker ]; do
  REPLICA=$i
  OLD_PVC="data-kafka-${REPLICA}"
  NEW_PVC="data-kafka-broker-${REPLICA}"
  NEW_PVC_MANIFEST_FILE="$NEW_PVC.yaml"
  PV_NAME=$(kubectl -n $namespace get pvc $NEW_PVC -o jsonpath="{.spec.volumeName}")

  # Create the new PVC, change the PV reclaim policy and delete the old pvc
  kubectl -n $namespace apply -f $NEW_PVC_MANIFEST_FILE
  kubectl -n $namespace patch pv $PV_NAME -p '{"spec":{"persistentVolumeReclaimPolicy":"Delete"}}'
  kubectl -n $namespace delete pvc $OLD_PVC

  i=$((i + 1))
done
