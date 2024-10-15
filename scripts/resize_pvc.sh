set -x
sts_name=$1
size=$2
namespace=$3

# https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/volume-expansion#using_volume_expansion
# if the storageclass is not resizeable add the following line at top level to make it resizeable
# allowVolumeExpansion: true

if [ -z "$sts_name" ] || [ -z "$size" ]; then
echo "Usage: ./resize_pvc.sh <statefulset name> <size> [namespace]"
exit 1
fi

if [ -z "$namespace" ]; then
namespace="kfuse"
fi


for pod in `kubectl get pods -n $namespace -o 'custom-columns=NAME:.metadata.name,CONTROLLER:.metadata.ownerReferences[].name' | grep $sts_name$ | awk '{print $1}'`
do
  for pvc in `kubectl get pods -n $namespace $pod -o 'custom-columns=PVC:.spec.volumes[].persistentVolumeClaim.claimName' | grep -v PVC`
  do
    echo Patching $pvc
    echo "kubectl patch pvc $pvc -n $namespace --patch '{\"spec\": {\"resources\": {\"requests\": {\"storage\": \"'$size'\" }}}}'"
    kubectl patch pvc $pvc -n $namespace --patch '{"spec": {"resources": {"requests": {"storage": "'$size'" }}}}'
    if [ $? -ne 0 ]; then
      echo "failed to patch pvc. can not move forward."
      exit 1
    fi
    echo "saving old sts $sts_name yaml"
    kubectl -n $namespace get sts $sts_name -o yaml > old_$sts_name.yaml
    echo "creating updated sts $sts_name yaml"
    sed "s/storage:.*/storage: $size/g" old_$sts_name.yaml > updated_$sts_name.yaml
    echo "kubectl delete sts $sts_name --cascade=orphan -n $namespace"
    kubectl delete sts $sts_name --cascade=orphan -n $namespace
    echo "applying updated $sts_name yaml"
    kubectl apply -f updated_$sts_name.yaml
    echo Make sure that the helm values.yaml reflects the updated disk size.
  done
done
