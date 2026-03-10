from flask import Flask, request, jsonify
import base64, json, os, logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

PROXY_VARS = [
    {"name": "HTTP_PROXY",  "value": os.getenv("HTTP_PROXY",  "http://squid.proxy-injector.svc.cluster.local:3128")},
    {"name": "HTTPS_PROXY", "value": os.getenv("HTTPS_PROXY", "http://squid.proxy-injector.svc.cluster.local:3128")},
    {"name": "NO_PROXY",    "value": os.getenv("NO_PROXY",    ".cluster.local,.svc,127.0.0.1")},
    {"name": "http_proxy",  "value": os.getenv("HTTP_PROXY",  "http://squid.proxy-injector.svc.cluster.local:3128")},
    {"name": "https_proxy", "value": os.getenv("HTTPS_PROXY", "http://squid.proxy-injector.svc.cluster.local:3128")},
    {"name": "no_proxy",    "value": os.getenv("NO_PROXY",    ".cluster.local,.svc,127.0.0.1")},
]

@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200

@app.route("/inject", methods=["POST"])
def inject():
    review = request.json
    pod = review["request"]["object"]
    pod_name = pod["metadata"].get("name", pod["metadata"].get("generateName", "unknown"))

    app.logger.info(f"Processing pod: {pod_name}")

    patch = []
    for i, container in enumerate(pod["spec"]["containers"]):
        existing = [e["name"] for e in container.get("env", [])]
        has_env = "env" in container

        vars_to_inject = [v for v in PROXY_VARS if v["name"] not in existing]
        app.logger.info(f"Container {i}: has_env={has_env}, vars_to_inject={[v['name'] for v in vars_to_inject]}")

        if not vars_to_inject:
            continue

        if not has_env:
            patch.append({
                "op": "add",
                "path": f"/spec/containers/{i}/env",
                "value": vars_to_inject
            })
        else:
            for var in vars_to_inject:
                patch.append({
                    "op": "add",
                    "path": f"/spec/containers/{i}/env/-",
                    "value": var
                })

    app.logger.info(f"Final patch: {json.dumps(patch)}")
    patch_b64 = base64.b64encode(json.dumps(patch).encode()).decode()

    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": review["request"]["uid"],
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": patch_b64,
        }
    })

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=(
            "/etc/tls/tls.crt",
            "/etc/tls/tls.key"
        )
    )