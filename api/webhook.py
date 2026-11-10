import os
import sys
import json
import time
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing psycopg2 for database
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except Exception:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 is not available; running database in mock/fallback mode.")

# ====================================================================
# 1. DATABASE HELPERS (Supabase / PostgreSQL)
# ====================================================================

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or not PSYCOPG2_AVAILABLE:
        return None
    try:
        ssl_mode = "require" if "supabase" in db_url or "sslmode" not in db_url else None
        conn_kwargs = {"connect_timeout": 5}
        if ssl_mode and "sslmode=" not in db_url:
            conn_kwargs["sslmode"] = ssl_mode
        conn = psycopg2.connect(db_url, **conn_kwargs)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def db_upsert_user(user_id: int, username: str = None, first_name: str = None) -> bool:
    try:
        conn = get_db_connection()
        if not conn:
            return False
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO telegram_users (
                user_id, username, first_name, registered_at,
                last_interaction_at, last_start_at, start_count, status
            )
            VALUES (%s, %s, %s, NOW(), NOW(), NOW(), 1, 'active')
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_interaction_at = NOW(),
                last_start_at = NOW(),
                start_count = telegram_users.start_count + 1,
                status = 'active';
            """, (user_id, username, first_name))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error upserting user: {e}")
        return False

def db_update_interaction(user_id: int, username: str = None, first_name: str = None) -> bool:
    try:
        conn = get_db_connection()
        if not conn:
            return False
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO telegram_users (
                user_id, username, first_name, registered_at,
                last_interaction_at, last_start_at, start_count, status
            )
            VALUES (%s, %s, %s, NOW(), NOW(), NOW(), 1, 'active')
            ON CONFLICT (user_id) DO UPDATE SET
                username = COALESCE(EXCLUDED.username, telegram_users.username),
                first_name = COALESCE(EXCLUDED.first_name, telegram_users.first_name),
                last_interaction_at = NOW(),
                status = 'active';
            """, (user_id, username, first_name))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating interaction: {e}")
        return False

def db_get_stats() -> dict:
    try:
        conn = get_db_connection()
        if not conn:
            return {"total_users": 0, "active_users": 0, "blocked_users": 0, "joined_today": 0, "interacted_today": 0, "total_starts": 0, "db_connected": False}
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT
                COUNT(*)::int AS total_users,
                COUNT(*) FILTER (WHERE registered_at >= CURRENT_DATE)::int AS joined_today,
                COUNT(*) FILTER (WHERE last_interaction_at >= CURRENT_DATE)::int AS interacted_today,
                COALESCE(SUM(start_count), 0)::int AS total_starts,
                COUNT(*) FILTER (WHERE status = 'active')::int AS active_users,
                COUNT(*) FILTER (WHERE status = 'blocked')::int AS blocked_users
            FROM telegram_users;
            """)
            row = cur.fetchone()
            res = dict(row) if row else {}
            res["db_connected"] = True
            conn.close()
            return res
    except Exception as e:
        return {"total_users": 0, "db_connected": False, "error": str(e)}

def db_get_recent_users(limit: int = 10) -> list:
    try:
        conn = get_db_connection()
        if not conn:
            return []
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username, first_name, start_count, status FROM telegram_users ORDER BY last_interaction_at DESC LIMIT %s;", (limit,))
            res = list(cur.fetchall())
            conn.close()
            return res
    except Exception:
        return []

def db_get_all_active_ids() -> list:
    try:
        conn = get_db_connection()
        if not conn:
            return []
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM telegram_users WHERE status = 'active' ORDER BY last_interaction_at DESC;")
            res = [row[0] for row in cur.fetchall()]
            conn.close()
            return res
    except Exception:
        return []

def db_mark_blocked(user_id: int) -> bool:
    try:
        conn = get_db_connection()
        if not conn:
            return False
        with conn.cursor() as cur:
            cur.execute("UPDATE telegram_users SET status = 'blocked', last_interaction_at = NOW() WHERE user_id = %s;", (user_id,))
        conn.close()
        return True
    except Exception:
        return False

# ====================================================================
# 2. TELEGRAM BOT API CLIENT WITH RETRY & LOGGING
# ====================================================================

def send_telegram(method: str, payload: dict) -> dict:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN is missing!")
        return {"ok": False, "description": "BOT_TOKEN not configured"}
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
        res_json = r.json()
        if not res_json.get("ok"):
            logger.error(f"Telegram API responded with error ({method}): {res_json} | Payload was: {payload}")
        return res_json
    except Exception as e:
        logger.error(f"Telegram API call error ({method}): {e}")
        return {"ok": False, "description": str(e)}

def tg_send_message(chat_id, text: str, reply_markup: dict = None, parse_mode: str = "HTML") -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = send_telegram("sendMessage", payload)
    
    # If failed, retry without HTML parsing and without reply_markup for 100% delivery guarantee
    if not res.get("ok") and reply_markup:
        logger.warning(f"sendMessage failed ({res.get('description')}), retrying without reply_markup...")
        payload_plain = {"chat_id": chat_id, "text": text}
        return send_telegram("sendMessage", payload_plain)
    return res

def tg_edit_message(chat_id, message_id: int, text: str, reply_markup: dict = None, parse_mode: str = "HTML") -> dict:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_telegram("editMessageText", payload)

def tg_answer_callback(callback_id: str, text: str = None) -> dict:
    return send_telegram("answerCallbackQuery", {"callback_query_id": callback_id, "text": text or ""})

def tg_set_menu_button(chat_id: int = None) -> dict:
    """Sets the Telegram native Mini App menu button at the bottom-left of the chat"""
    url = get_game_url()
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "🚀 OPEN GAME",
            "web_app": {"url": url}
        }
    }
    if chat_id:
        payload["chat_id"] = chat_id
    return send_telegram("setChatMenuButton", payload)

# ====================================================================
# 3. KEYBOARDS & MESSAGES (TELEGRAM MINI APP INTEGRATION)
# ====================================================================

def get_game_url():
    raw_url = os.environ.get("WEB_APP_URL", "https://universallearninggame.vercel.app/").strip()
    if raw_url.startswith("http://"):
        raw_url = "https://" + raw_url[7:]
    elif not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    return raw_url.rstrip("/")

def get_persistent_reply_keyboard():
    url = get_game_url()
    return {
        "keyboard": [
            [
                {
                    "text": "🚀 OPEN GAME",
                    "web_app": {"url": url}
                }
            ],
            [
                {"text": "📖 How to Use"},
                {"text": "ℹ️ About"}
            ],
            [
                {"text": "📢 Updates / Announcements"},
                {"text": "🆘 Help & Support"}
            ]
        ],
        "is_persistent": True,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_open_game_inline_keyboard():
    url = get_game_url()
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🚀 Open Mini App (Telegram ichida ochish)",
                    "web_app": {"url": url}
                }
            ]
        ]
    }

def get_admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📊 Refresh Stats", "callback_data": "admin_stats"}, {"text": "👥 Recent Users", "callback_data": "admin_recent"}],
            [{"text": "📢 Broadcast Info", "callback_data": "admin_broadcast_info"}]
        ]
    }

WELCOME_MESSAGE = """Welcome to Universal Learning Game! 🎓

Ready to improve your knowledge and challenge yourself?

Your learning journey starts here.

Press the <b>🚀 Open Mini App</b> button below to launch the learning platform directly inside Telegram!

📌 Reminder: Come back every day and press START or tap OPEN GAME below to continue your streak.

Good luck! 🚀"""

HOW_TO_USE_MESSAGE = """📖 <b>How to Use Universal Learning Game</b>

1. <b>Open the Mini App:</b> Tap <b>🚀 OPEN GAME</b> on your keyboard or the button below to launch the platform right inside Telegram.
2. <b>10 Interactive Modes:</b> Learn, Classic Quiz, Flashcards (SRS), Matching Game, and Final Exam simulations.
3. <b>Slide Evidence:</b> Every question is synchronized with verified lecture presentation slides.
4. <b>Daily Engagement:</b> Return every day and keep your study streak alive!"""

ABOUT_MESSAGE = """ℹ️ <b>About Universal Learning Game</b>

<b>Universal Learning Game</b> is an interactive educational platform designed to transform complex lecture materials, PowerPoint slides, and questions into an engaging Telegram Mini App.

✨ <b>Platform Highlights:</b>
• <b>10 Study Modes:</b> Learn, Quiz, Flashcards (SRS), Matching, Fill in the Blanks, True/False, and Final Exam.
• <b>Slide Evidence Synchronization:</b> Real-time proof from lecture slides.
• <b>Native Telegram Experience:</b> Opens directly inside Telegram in fullscreen.

Current Course: <b>Lecture 5 · The Verb and Verbal Categories</b> (61 Questions & 51 Slides)"""

UPDATES_MESSAGE = """📢 <b>Latest Announcements & Updates</b>

<b>Version 2.5 Release Notes:</b>
• 🎓 <b>Lecture 5 is Live:</b> 61 questions and 51 slides covering Theoretical English Grammar.
• 📱 <b>Telegram Mini App Integration:</b> Opens inside Telegram with fullscreen support.
• 🔄 <b>Dynamic Answer Shuffling:</b> Option positions are randomized on every round.
• ⏩ <b>Skip & Navigation:</b> Jump freely between questions."""

def get_help_message():
    sup = os.environ.get("SUPPORT_USERNAME", "Odilxon_Support").lstrip("@")
    return f"🆘 <b>Help & Support</b>\n\nNeed assistance or have questions?\n\n• <b>Direct Support:</b> @{sup}\n• <b>Platform Status:</b> Online 24/7 on Vercel Serverless."

# ====================================================================
# 4. ADMIN LOGIC
# ====================================================================

def is_admin(user_id: int) -> bool:
    raw_admin = os.environ.get("ADMIN_ID", "")
    for part in raw_admin.replace(" ", ",").split(","):
        if part.strip().isdigit() and int(part.strip()) == user_id:
            return True
    return False

def render_admin_stats() -> str:
    s = db_get_stats()
    db_status = "🟢 Connected (PostgreSQL / Supabase)" if s.get("db_connected") else "🟡 Running without Database"
    return f"""📊 <b>Universal Learning Game — Admin Dashboard</b>

<b>Database Status:</b> {db_status}

<b>📈 Analytics:</b>
• <b>Total Users:</b> <code>{s.get('total_users', 0)}</code>
• <b>Active Users:</b> <code>{s.get('active_users', 0)}</code>
• <b>Blocked Users:</b> <code>{s.get('blocked_users', 0)}</code>
• <b>Joined Today:</b> <code>{s.get('joined_today', 0)}</code>
• <b>Interacted Today:</b> <code>{s.get('interacted_today', 0)}</code>
• <b>Total /start Commands:</b> <code>{s.get('total_starts', 0)}</code>

<b>⚡ Admin Controls:</b>
• Broadcast: <code>/broadcast &lt;message&gt;</code>"""

def handle_broadcast(admin_chat_id: int, text: str):
    user_ids = db_get_all_active_ids()
    if not user_ids:
        tg_send_message(admin_chat_id, "⚠️ No active users in database to broadcast to.")
        return
    delivered = 0
    blocked = 0
    failed = 0
    for uid in user_ids:
        res = tg_send_message(uid, text)
        if res.get("ok"):
            delivered += 1
        else:
            err = res.get("description", "").lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
                db_mark_blocked(uid)
            else:
                failed += 1
        time.sleep(0.04)
    tg_send_message(admin_chat_id, f"📢 <b>Broadcast Complete!</b>\n• Delivered: {delivered}\n• Blocked: {blocked}\n• Failed: {failed}")

# ====================================================================
# 5. UPDATE DISPATCHER
# ====================================================================

def process_telegram_update(update: dict):
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        from_user = msg.get("from", {})
        user_id = from_user.get("id")
        username = from_user.get("username")
        first_name = from_user.get("first_name")
        text = msg.get("text", "").strip()

        if not chat_id or not user_id:
            return

        # 1. /start command
        if text.startswith("/start"):
            db_upsert_user(user_id, username, first_name)
            # Configure native Mini App menu button for user
            tg_set_menu_button(chat_id)
            # Send Welcome with persistent keyboard
            tg_send_message(
                chat_id=chat_id,
                text=WELCOME_MESSAGE,
                reply_markup=get_persistent_reply_keyboard()
            )
            # Send direct inline Mini App button
            tg_send_message(
                chat_id=chat_id,
                text="👇 <b>Mini ilovani ochish uchun quyidagi tugmani bosing:</b>",
                reply_markup=get_open_game_inline_keyboard()
            )
            return

        # 2. "🚀 OPEN GAME" text message
        if "OPEN GAME" in text.upper():
            db_update_interaction(user_id, username, first_name)
            tg_send_message(
                chat_id=chat_id,
                text="🎮 <b>Universal Learning Game</b>\n\nMini ilovani Telegram ichida ochish uchun quyidagi tugmani bosing:",
                reply_markup=get_open_game_inline_keyboard()
            )
            return

        # 3. "📖 How to Use"
        if "HOW TO USE" in text.upper() or text.startswith("/help"):
            db_update_interaction(user_id, username, first_name)
            tg_send_message(
                chat_id=chat_id,
                text=HOW_TO_USE_MESSAGE,
                reply_markup=get_open_game_inline_keyboard()
            )
            return

        # 4. "ℹ️ About"
        if "ABOUT" in text.upper() or text.startswith("/about"):
            db_update_interaction(user_id, username, first_name)
            tg_send_message(
                chat_id=chat_id,
                text=ABOUT_MESSAGE,
                reply_markup=get_open_game_inline_keyboard()
            )
            return

        # 5. "📢 Updates"
        if "UPDATES" in text.upper() or "ANNOUNCEMENTS" in text.upper():
            db_update_interaction(user_id, username, first_name)
            tg_send_message(chat_id, UPDATES_MESSAGE)
            return

        # 6. "🆘 Help & Support"
        if "HELP" in text.upper() or "SUPPORT" in text.upper():
            db_update_interaction(user_id, username, first_name)
            tg_send_message(chat_id, get_help_message())
            return

        # 7. /admin and /broadcast
        if text.startswith("/admin") or text.startswith("/broadcast"):
            if not is_admin(user_id):
                tg_send_message(chat_id, "⛔ <b>Access Denied:</b> Administrator only.")
                return
            db_update_interaction(user_id, username, first_name)
            if text.startswith("/broadcast"):
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    handle_broadcast(chat_id, parts[1].strip())
                else:
                    tg_send_message(chat_id, "Usage: <code>/broadcast &lt;message&gt;</code>")
                return
            tg_send_message(chat_id, render_admin_stats(), reply_markup=get_admin_keyboard())
            return

        # 8. Fallback text
        db_update_interaction(user_id, username, first_name)
        fallback = f"Assalomu alaykum, <b>{first_name or 'qadrli foydalanuvchi'}</b>! 👋\n\nMini ilovani Telegram ichida ochish uchun quyidagi tugmani bosing:"
        tg_send_message(chat_id, fallback, reply_markup=get_open_game_inline_keyboard())
        return

    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        user_id = cb.get("from", {}).get("id")
        msg = cb.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        message_id = msg.get("message_id")
        data = cb.get("data", "")

        if cb_id:
            tg_answer_callback(cb_id)
        if not chat_id or not message_id or not is_admin(user_id):
            return

        if data == "admin_stats":
            tg_edit_message(chat_id, message_id, render_admin_stats(), reply_markup=get_admin_keyboard())
        elif data == "admin_recent":
            recent = db_get_recent_users(10)
            if not recent:
                t = "👥 <b>Recent Users:</b>\n\nNo records yet."
            else:
                lines = ["👥 <b>10 Most Recently Active Users:</b>\n"]
                for u in recent:
                    lines.append(f"• <b>{u.get('first_name') or 'User'}</b> (@{u.get('username') or 'none'}) [<code>{u.get('user_id')}</code>] - Starts: {u.get('start_count')}")
                t = "\n".join(lines)
            tg_edit_message(chat_id, message_id, t, reply_markup=get_admin_keyboard())
        elif data == "admin_broadcast_info":
            tg_edit_message(chat_id, message_id, "📢 <b>Broadcast Command:</b>\n\nSend <code>/broadcast &lt;message&gt;</code> to notify all users.", reply_markup=get_admin_keyboard())

# ====================================================================
# 6. WSGI APPLICATION (VERCEL ENTRYPOINT)
# ====================================================================

def read_index_html():
    candidates = ["index.html", "../index.html", os.path.join(os.path.dirname(__file__), "..", "index.html"), os.path.join(os.path.dirname(__file__), "index.html")]
    for c in candidates:
        if os.path.exists(c):
            try:
                with open(c, "rb") as f:
                    return f.read()
            except Exception:
                pass
    return b"<html><body><h1>Universal Learning Game</h1><p>Website is online.</p></body></html>"

INDEX_HTML_DATA = read_index_html()

def app(environ, start_response):
    raw_path = environ.get("PATH_INFO", "")
    path = raw_path.split("?")[0].rstrip("/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # 1. Serve Universal Learning Game HTML website on root / or /index.html
    if path in ("", "/", "/index.html"):
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(INDEX_HTML_DATA))),
            ("Cache-Control", "public, max-age=3600")
        ]
        start_response("200 OK", headers)
        return [INDEX_HTML_DATA]

    # 2. Telegram Webhook endpoint (/api/webhook or /webhook)
    if "/api/webhook" in path or path.endswith("webhook"):
        if method == "POST":
            webhook_secret = os.environ.get("WEBHOOK_SECRET")
            if webhook_secret:
                incoming_secret = environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN")
                if incoming_secret != webhook_secret:
                    start_response("403 Forbidden", [("Content-Type", "application/json")])
                    return [b'{"error": "Forbidden: Invalid secret token"}']

            try:
                content_len = int(environ.get("CONTENT_LENGTH", 0))
                body = environ["wsgi.input"].read(content_len)
                update = json.loads(body.decode("utf-8"))
                process_telegram_update(update)
            except Exception as e:
                logger.error(f"Error handling webhook update: {e}", exc_info=True)

            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"ok": true}']

        # GET health check
        status_info = {
            "status": "online",
            "service": "Universal Learning Game Telegram Webhook",
            "bot_configured": bool(os.environ.get("BOT_TOKEN")),
            "database_configured": bool(os.environ.get("DATABASE_URL")),
            "web_app_url": get_game_url()
        }
        res_bytes = json.dumps(status_info, indent=2).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json"), ("Content-Length", str(len(res_bytes)))])
        return [res_bytes]

    # Fallback to index.html
    headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(INDEX_HTML_DATA)))]
    start_response("200 OK", headers)
    return [INDEX_HTML_DATA]

handler = app
application = app
