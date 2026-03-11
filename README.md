# proxy-injector

> ⚠️ **Disclaimer**: This is a prototype intended as a reference and source of inspiration.
> It is not production-ready and may require adjustments to fit your specific environment and requirements.
> Use it at your own risk.


Mutating webhook for automatic HTTP proxy environment variable injection in OpenShift pods.

## How it works

When a pod is created in a namespace labeled with `inject-proxy=true`, the webhook intercepts the request and automatically adds proxy environment variables before the pod starts. TLS is managed by OpenShift's native Service CA Operator, with no external dependencies.

## Requirements

- OpenShift 4.x
- Podman
- quay.io account

## Repository structure
```
proxy-injector/
├── README.md
├── Dockerfile
├── webhook/
│   └── webhook.py
└── manifests/
    ├── 00-namespace.yaml
    ├── 01-rbac.yaml
    ├── 02-configmap.yaml
    ├── 03-deployment.yaml
    ├── 04-service.yaml
    ├── 05-webhook.yaml
    └── 06-squid.yaml
```

## Build and push
```bash
podman build --no-cache -t quay.io/YOUR_USER/proxy-injector:latest .
podman push quay.io/YOUR_USER/proxy-injector:latest
```

## Configuration

Edit `manifests/02-configmap.yaml` with your proxy values:
```yaml
data:
  HTTP_PROXY: "http://your-proxy:3128"
  HTTPS_PROXY: "http://your-proxy:3128"
  NO_PROXY: ".cluster.local,.svc,127.0.0.1"
  http_proxy: "http://your-proxy:3128"
  https_proxy: "http://your-proxy:3128"
  no_proxy: ".cluster.local,.svc,127.0.0.1"
```

Edit `manifests/03-deployment.yaml` with your image:
```yaml
image: quay.io/YOUR_USER/proxy-injector:latest
```

## Deployment
```bash
oc apply -f manifests/
```

Verify everything is running:
```bash
oc get pods -n proxy-injector
```

Verify the Service CA Operator injected the TLS secret:
```bash
oc get secret proxy-injector-tls -n proxy-injector
```

Verify the caBundle was injected into the webhook:
```bash
oc get mutatingwebhookconfiguration proxy-injector \
  -o jsonpath='{.webhooks[0].clientConfig.caBundle}' \
  | base64 -d | openssl x509 -noout -text | grep -i issuer
```

## Enable on a namespace
```bash
oc label namespace my-namespace inject-proxy=true
```

From that point on, all pods created in that namespace will automatically receive the proxy environment variables.

## Verify it works
```bash
# Create a test pod
oc run curl-test -n my-namespace --image=curlimages/curl -- sleep 3600

# Check injected variables
oc get pod curl-test -n my-namespace -o jsonpath='{.spec.containers[0].env}'

# Verify traffic goes through the proxy
oc exec curl-test -n my-namespace -- curl -v http://example.com 2>&1 | head -10
```

You should see:
```
* Uses proxy env variable http_proxy == 'http://your-proxy:3128'
* Established connection to your-proxy (x.x.x.x port 3128)
```

## Squid (optional)

The repository includes a Squid deployment in `manifests/06-squid.yaml` for testing in environments without an external proxy. To verify traffic is going through it:
```bash
oc logs -f deployment/squid -n proxy-injector
```

## Notes

- The webhook uses `failurePolicy: Ignore` — if the webhook goes down, pods will still start without the proxy variables.
- Variables are injected in both uppercase and lowercase for compatibility with curl and other tools.
- If a pod already has any of the variables defined, the webhook will not overwrite them.
- `imagePullPolicy: Always` is set on the deployment to ensure the latest image is always used.