set -x

S3_PATH=$1

if [ -z "$S3_PATH" ] ; then
echo "Usage: ./backupconfigdb.sh s3path"
exit 1
fi

kubectl exec -it kfuse-configdb-0 -- bash -c "PGPASSWORD=password pg_dumpall -U postgres"  | gzip | aws s3 cp - "$S3_PATH"
