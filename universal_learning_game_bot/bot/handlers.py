import logging
from bot import client, database, keyboards, messages, admin

logger = logging.getLogger(__name__)

def process_update(update: dict):
    # 1. Handle incoming chat messages
    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        from_user = msg.get("from", {})
        
        chat_id = chat.get("id")
        user_id = from_user.get("id")
        username = from_user.get("username")
        first_name = from_user.get("first_name")
        text = msg.get("text", "").strip()

        if not chat_id or not user_id:
            return

        # /start command — Daily START Engagement Core with Persistent Reply Keyboard
        if text.startswith("/start"):
            database.upsert_user_start(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.WELCOME_MESSAGE,
                reply_markup=keyboards.get_persistent_reply_keyboard()
            )
            return

        # "🚀 OPEN GAME" persistent reply button press
        if "OPEN GAME" in text.upper():
            database.update_user_interaction(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.get_game_link_message(),
                reply_markup=keyboards.get_open_game_url_keyboard()
            )
            return

        # "📖 How to Use" persistent reply button press or /help
        if "HOW TO USE" in text.upper() or text.startswith("/help"):
            database.update_user_interaction(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.HOW_TO_USE_MESSAGE
            )
            return

        # "ℹ️ About" persistent reply button press or /about
        if "ABOUT" in text.upper() or text.startswith("/about"):
            database.update_user_interaction(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.ABOUT_MESSAGE
            )
            return

        # "📢 Updates" persistent reply button press
        if "UPDATES" in text.upper() or "ANNOUNCEMENTS" in text.upper():
            database.update_user_interaction(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.UPDATES_MESSAGE
            )
            return

        # "🆘 Help & Support" persistent reply button press
        if "HELP" in text.upper() or "SUPPORT" in text.upper():
            database.update_user_interaction(user_id, username, first_name)
            client.send_message(
                chat_id=chat_id,
                text=messages.get_help_support_message()
            )
            return

        # /admin or /broadcast commands
        if text.startswith("/admin") or text.startswith("/broadcast"):
            database.update_user_interaction(user_id, username, first_name)
            admin.handle_admin_command(user_id, chat_id, text)
            return

        # Fallback text message
        database.update_user_interaction(user_id, username, first_name)
        fallback_text = (
            f"Hello, <b>{first_name or 'there'}</b>! 👋\n\n"
            "Tap <b>🚀 OPEN GAME</b> on your permanent keyboard below to launch the learning game, or send <b>/start</b> to view instructions."
        )
        client.send_message(
            chat_id=chat_id,
            text=fallback_text,
            reply_markup=keyboards.get_persistent_reply_keyboard()
        )
        return

    # 2. Handle callback queries (Admin panel buttons)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        from_user = cb.get("from", {})
        msg = cb.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        message_id = msg.get("message_id")
        data = cb.get("data", "")
        
        user_id = from_user.get("id")
        username = from_user.get("username")
        first_name = from_user.get("first_name")

        if cb_id:
            client.answer_callback_query(cb_id)

        if not chat_id or not message_id:
            return

        if user_id:
            database.update_user_interaction(user_id, username, first_name)

        if data.startswith("admin_"):
            admin.handle_admin_callback(user_id, chat_id, message_id, data)
