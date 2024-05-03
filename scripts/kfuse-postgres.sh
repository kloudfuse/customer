#!/usr/bin/env bash

# Optional parameters:
# 1. pod name - default kfuse-configdb-0
# 2. namespace - default kfuse
# 3. database name - default configdb

kubectl exec -it ${1:-kfuse-configdb-0} -n ${2:-kfuse} -- bash -c "PGPASSWORD=\$POSTGRES_PASSWORD psql -U postgres -d ${3:-configdb}"
