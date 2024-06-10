set -ex;

if ! jq --version &> /dev/null
then
  echo "jq is not installed, please install jq and rerun the script"
  exit 1
fi

if [ -z "$1" ]; then
  echo "Usage: $0 number of broker pods"
  exit 1
fi

n=$1
i=0

while [ $i -lt $n ]; do
  REPLICA=$i
  OLD_PVC="data-kafka-${REPLICA}"
  NEW_PVC="data-kafka-broker-${REPLICA}"
  PV_NAME=$(kubectl get pvc $OLD_PVC -o jsonpath="{.spec.volumeName}")
  NEW_PVC_MANIFEST_FILE="$NEW_PVC.yaml"
 
  # save old pvc yaml
  kubectl get pvc $OLD_PVC -o yaml > "$OLD_PVC.yaml"

  # Modify PV reclaim policy
  kubectl patch pv $PV_NAME -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'

  # Create new PVC manifest
  kubectl get pvc $OLD_PVC -o json | jq "
    .metadata.name = \"$NEW_PVC\"
    | with_entries(
        select([.key] |
          inside([\"metadata\", \"spec\", \"apiVersion\", \"kind\"]))
      )
    | del(
        .metadata.annotations, .metadata.creationTimestamp,
        .metadata.finalizers, .metadata.resourceVersion,
        .metadata.selfLink, .metadata.uid
      )
    " > $NEW_PVC_MANIFEST_FILE
  # dump new manifest
  cat $NEW_PVC_MANIFEST_FILE
 
  kubectl delete pvc $OLD_PVC --wait=false || true
  # Make PV available again and create the new PVC
  kubectl patch pv $PV_NAME -p '{"spec":{"claimRef": null}}'
  kubectl apply -f $NEW_PVC_MANIFEST_FILE
  i=$((i + 1))
done
