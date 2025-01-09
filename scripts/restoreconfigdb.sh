set -x

S3_PATH=$1

if [ -z "$S3_PATH" ] ; then
echo "Usage: ./restoreconfigdb.sh s3path"
exit 1
fi

aws s3 cp "$S3_PATH" - | gzip -d |  kubectl exec -it kfuse-configdb-0 --  bash -c "PGPASSWORD=password psql -q -U postgres"
