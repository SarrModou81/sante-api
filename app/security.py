import time
import uuid
from collections import Counter

from flask import g, jsonify, request

from app.extensions import limiter

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

# Bonus /metrics : compteur de reponses par code de statut (par processus Gunicorn)
status_counter = Counter()


def register_security(app):
    @app.before_request
    def start_timer():
        g.start = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def add_headers_and_log(response):
        response.headers.update(SECURITY_HEADERS)
        response.headers["X-Request-ID"] = g.get("request_id", "")
        duration_ms = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
        status_counter[response.status_code] += 1
        app.logger.info("%s %s -> %s (%.1f ms) [%s]", request.method, request.path,
                        response.status_code, duration_ms, g.get("request_id"))
        return response

    @app.get("/metrics")
    @limiter.exempt
    def metrics():
        total = sum(status_counter.values())
        by_status = {str(code): count for code, count in sorted(status_counter.items())}
        return jsonify(requests_total=total, requests_by_status=by_status), 200