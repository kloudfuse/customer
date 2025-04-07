#!/bin/bash

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <version> <dest-az-value> <should-install-ingress?> <namespace> <values-file>"
  exit 1
fi

VERSION="$1"
DEST_AZ_VALUE="$2"
INSTALL_INGRESS="$3"
NAMESPACE="$4"
VALUES_FILE="$5"

COMMAND="helm upgrade --install kfuse oci://us-east1-docker.pkg.dev/mvp-demo-301906/kfuse-helm/kfuse --version $VERSION \
  -f $VALUES_FILE \
  --namespace $NAMESPACE \
  --set ingress-nginx.installIngressRules=$INSTALL_INGRESS \
  --set ingress-nginx.controller.ingressClassResource.name=\"$DEST_AZ_VALUE\" \
  --set ingress-nginx.controller.ingressClass=\"$DEST_AZ_VALUE\" \
  --set ingress-nginx.controller.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[0].matchExpressions[0].values[0]=\"$DEST_AZ_VALUE\" \
  --set ingress-nginx.controller.tolerations[0].value=\"$DEST_AZ_VALUE\""

# Echo the command and ask for confirmation
echo "The following command will be executed:"
echo "$COMMAND"

read -p "Do you want to proceed? (y/n): " CONFIRMATION

if [ "$CONFIRMATION" != "y" ] && [ "$CONFIRMATION" != "Y" ]; then
  echo "Operation cancelled."
  exit 1
fi

# Execute the command
eval "$COMMAND"
