from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import logging

# Ensure project root is in sys.path so 'bot' package can be imported seamlessly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from bot.handlers import process_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check and status endpoint"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        status_payload = {
            "status": "online",
            "service": "Universal Learning Game Telegram Webhook",
            "platform": "Vercel Serverless Function (Python 3.9+)",
            "bot_configured": bool(os.environ.get("BOT_TOKEN")),
            "database_configured": bool(os.environ.get("DATABASE_URL")),
            "webhook_secret_enforced": bool(os.environ.get("WEBHOOK_SECRET")),
            "web_app_url": os.environ.get("WEB_APP_URL", "https://universallearninggame.vercel.app/")
        }
        self.wfile.write(json.dumps(status_payload, indent=2).encode("utf-8"))

    def do_POST(self):
        """Processes incoming Telegram Bot Webhook Updates"""
        # 1. Enforce Webhook Secret Token Verification if configured
        webhook_secret = os.environ.get("WEBHOOK_SECRET")
        if webhook_secret:
            incoming_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if incoming_secret != webhook_secret:
                logger.warning("Rejected webhook request: Invalid secret token.")
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Forbidden: Invalid secret token"}).encode("utf-8"))
                return

        # 2. Parse Incoming JSON payload
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to read/parse webhook request: {e}")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Bad Request: Malformed JSON"}).encode("utf-8"))
            return

        # 3. Route and Process Update
        try:
            process_update(update)
        except Exception as e:
            logger.error(f"Unhandled error in process_update: {e}", exc_info=True)

        # 4. Always return 200 OK so Telegram acknowledges update delivery
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
