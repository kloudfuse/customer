# Docker Rate Limit for OSS Images

## Symptom
During Kloudfuse installation or upgrade you encounter Docker Rate Limit for pulling the OSS images with following error.

```
Error response from daemon: toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit
```

This is most likely you have a single org IP and multiple image pulls from Docker Repositories. 

## Solution
Reach out to `customer-success@kloudfuse.com` or on shared `kfuse-` channel. The customer success team will help you with a token that you an use to pull the OSS images.

### Steps for using the token
1. Create a new docker-registry secret e.g. `kfuse-image-dockerhub-credentials`

```
kubectl create secret docker-registry  kfuse-image-dockerhub-credentials \
    --docker-server=docker.io \
    --docker-username=<docker-id> \
    --docker-password=<token> \
    --docker-email=<email-id>
```

2. In the custom-values.yaml file for your deployment, add following in the `global` section

```
global:
  imagePullSecrets:
    - kfuse-image-pull-credentials
    - kfuse-image-dockerhub-credentials
```

3. Rerun the upgrade command form [here](https://docs.kloudfuse.com/platform/latest/install/)