#!/bin/bash
# Check if a prefix argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <prefix>"
  exit 1
fi

PREFIX="$1"

# Find and delete all S3 buckets matching the prefix
for bucket in $(aws s3 ls | awk '{print $3}' | grep "^$PREFIX"); do
  echo "Deleting bucket: $bucket"
  aws s3 rb s3://$bucket --force
done

