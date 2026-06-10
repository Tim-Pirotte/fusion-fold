# Fusion Fold
## Local Deployment
1. Ensure that Docker is installed on the system
2. Copy every .example file, remove the .example suffix and change the default secrets. For the Redis ACL file you should put the sha256 hash of the secret in instead of the plaintext secret.
3. Run `docker compose up --build` (mind your current directory)

## Kubernetes Deployment
1. Ensure Docker, KubeCTL and K3D are installed on the system
2. Copy every .example file from the local deployment folders into chart/files/<Application name> without the .example suffix and change the secrets the same way as the local deployment.
3. Create a cluster with port 80 exposed on port 8000 of the host: `k3d cluster create k3s-default -p "8000:80@loadbalancer" -v "C:/tmp:/tmp"` ("/tmp:/tmp" for Linux and Mac) TODO check if 80:80 should be added
4. Create a namespace: `kubectl create namespace fusion-fold`
5. Set the docker-registry secret so you can access the private images:
```
kubectl create secret docker-registry ghcr-secret `
   -n fusion-fold `
   --docker-server=ghcr.io `
   --docker-username=<Your git username> `
   --docker-password=<PAT token with read permissions to GHCR> `
   --docker-email=<Your git e-mail>
```
6. Run `helm install fusion-fold .\chart\ -n fusion-fold ` (mind your current directory)
