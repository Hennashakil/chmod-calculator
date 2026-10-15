"""chmod calculator: explain a Linux permission mode in plain English."""

from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from modes import ModeError, explain

app = Flask(__name__)
# Hosting platforms put a proxy in front that handles HTTPS; trust its headers
# so links like the API example show https:// and the real host name.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

PRESETS = ["644", "600", "755", "750", "700", "777", "1777", "4755"]


@app.get("/")
def index():
    mode = request.args.get("mode", "750")
    result, error = None, None
    try:
        result = explain(mode)
    except ModeError as e:
        error = str(e)
    return render_template("index.html", mode=mode, result=result, error=error, presets=PRESETS)


@app.get("/api/mode/<path:mode>")
def api_mode(mode):
    try:
        return jsonify(explain(mode))
    except ModeError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; script-src 'none'; frame-ancestors 'none'"
    )
    return resp


if __name__ == "__main__":
    app.run(debug=False)
