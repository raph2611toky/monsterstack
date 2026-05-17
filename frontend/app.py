from flask import Flask, render_template, request
import redis
import requests
import base64
import os

app = Flask(__name__)

cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    db=0
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")


@app.route("/", methods=["GET", "POST"])
def index():
    image_b64 = None
    name = ""
    source = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            cache_key = f"monster:{name}"
            cached = cache.get(cache_key)
            if cached:
                image_b64 = cached.decode("utf-8")
                source = "cache (Redis)"
            else:
                resp = requests.get(f"{BACKEND_URL}/monster/{name}", timeout=5)
                if resp.status_code == 200:
                    image_b64 = base64.b64encode(resp.content).decode("utf-8")
                    cache.setex(cache_key, 3600, image_b64)
                    source = "backend (généré)"

    return render_template("index.html", image=image_b64, name=name, source=source)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)