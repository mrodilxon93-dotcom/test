import json
import os
import sys
import logging

# Ensure project root is in sys.path so 'bot' package is accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from bot.handlers import process_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Preload index.html bytes for instant high-speed delivery
def load_index_html():
    candidates = [
        os.path.join(parent_dir, "index.html"),
        os.path.join(current_dir, "index.html"),
        "index.html"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read {p}: {e}")
    return b"<html><body><h1>Universal Learning Game</h1><p>index.html not found.</p></body></html>"

INDEX_HTML_BYTES = load_index_html()

def app(environ, start_response):
    """
    Standard WSGI Application (Vercel Python Serverless Entrypoint).
    1. GET / or /index.html -> Serves the Universal Learning Game website.
    2. POST /api/webhook -> Processes Telegram Webhook Updates.
    3. GET /api/webhook -> Healthcheck endpoint.
    """
    raw_path = environ.get("PATH_INFO", "")
    path = raw_path.split("?")[0].rstrip("/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # 1. Serve Universal Learning Game HTML website on root
    if path in ("", "/", "/index.html"):
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(INDEX_HTML_BYTES))),
            ("Cache-Control", "public, max-age=3600")
        ]
        start_response("200 OK", headers)
        return [INDEX_HTML_BYTES]

    # 2. Telegram Webhook endpoint
    if "/api/webhook" in path or path.endswith("webhook"):
        if method == "POST":
            # Secret token validation
            webhook_secret = os.environ.get("WEBHOOK_SECRET")
            if webhook_secret:
                incoming_secret = environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN")
                if incoming_secret != webhook_secret:
                    logger.warning("Rejected webhook request: Invalid secret token.")
                    start_response("403 Forbidden", [("Content-Type", "application/json")])
                    return [b'{"error": "Forbidden: Invalid secret token"}']

            try:
                content_length = int(environ.get("CONTENT_LENGTH", 0))
                body = environ["wsgi.input"].read(content_length)
                update = json.loads(body.decode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to parse webhook JSON payload: {e}")
                start_response("400 Bad Request", [("Content-Type", "application/json")])
                return [b'{"error": "Bad Request: Malformed JSON"}']

            try:
                process_update(update)
            except Exception as e:
                logger.error(f"Unhandled error in process_update: {e}", exc_info=True)

            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"ok": true}']

        # GET Health check
        status_payload = {
            "status": "online",
            "service": "Universal Learning Game Telegram Webhook",
            "platform": "Vercel Python WSGI Serverless",
            "bot_configured": bool(os.environ.get("BOT_TOKEN")),
            "database_configured": bool(os.environ.get("DATABASE_URL")),
            "webhook_secret_enforced": bool(os.environ.get("WEBHOOK_SECRET")),
            "web_app_url": os.environ.get("WEB_APP_URL", "https://universallearninggame.vercel.app/")
        }
        body = json.dumps(status_payload, indent=2).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*")
        ]
        start_response("200 OK", headers)
        return [body]

    # Fallback: Serve index.html for any other frontend routes
    headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(INDEX_HTML_BYTES)))
    ]
    start_response("200 OK", headers)
    return [INDEX_HTML_BYTES]

# Alias handler for compatibility
handler = app
