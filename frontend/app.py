from flask import Flask, render_template, request, jsonify
import base64
import os
from urllib.parse import quote

import redis
import requests
from requests import RequestException
from redis.exceptions import RedisError


app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080").rstrip("/")
BACKEND_TIMEOUT = float(os.getenv("BACKEND_TIMEOUT", "5"))
MAX_NAME_LENGTH = int(os.getenv("MAX_NAME_LENGTH", "64"))


def get_cache_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        socket_timeout=2,
        socket_connect_timeout=2,
        decode_responses=True,
    )


def normalize_name(value: str) -> str:
    return " ".join((value or "").strip().split())


def cache_key_for(name: str) -> str:
    return f"monster:{name.lower()}"


@app.route("/", methods=["GET", "POST"])
def index():
    image_b64 = None
    name = ""
    source = ""
    error = ""

    if request.method == "POST":
        name = normalize_name(request.form.get("name", ""))

        if not name:
            error = "Veuillez entrer un nom de monstre."
        elif len(name) > MAX_NAME_LENGTH:
            error = f"Le nom ne doit pas dépasser {MAX_NAME_LENGTH} caractères."
        else:
            cache_key = cache_key_for(name)
            cache = get_cache_client()

            try:
                cached = cache.get(cache_key)
            except RedisError:
                cached = None

            if cached:
                image_b64 = cached
                source = "cache (Redis)"
            else:
                try:
                    resp = requests.get(
                        f"{BACKEND_URL}/monster/{quote(name, safe='')}",
                        timeout=BACKEND_TIMEOUT,
                    )
                    resp.raise_for_status()
                    image_b64 = base64.b64encode(resp.content).decode("utf-8")
                    try:
                        cache.setex(cache_key, CACHE_TTL, image_b64)
                    except RedisError:
                        pass
                    source = "backend (généré)"
                except RequestException:
                    error = "Le backend de génération est momentanément indisponible."

    return render_template(
        "index.html",
        image=image_b64,
        name=name,
        source=source,
        error=error,
        cache_ttl=CACHE_TTL,
    )


@app.route("/health")
@app.route("/healthz")
def health():
    return jsonify({
        "status": "ok",
        "service": "monster-frontend",
        "version": APP_VERSION,
    })


@app.route("/readyz")
def ready():
    redis_ok = False
    backend_ok = False

    try:
        redis_ok = bool(get_cache_client().ping())
    except RedisError:
        redis_ok = False

    try:
        response = requests.get(f"{BACKEND_URL}/healthz", timeout=BACKEND_TIMEOUT)
        backend_ok = response.ok
    except RequestException:
        backend_ok = False

    status_code = 200 if redis_ok and backend_ok else 503
    return jsonify({
        "status": "ready" if status_code == 200 else "not_ready",
        "service": "monster-frontend",
        "redis": redis_ok,
        "backend": backend_ok,
    }), status_code


if __name__ == "__main__":
    # Mode local uniquement. En production Docker/Kubernetes, Gunicorn lance app:app.
    app.run(host="0.0.0.0", port=5000, debug=False)
