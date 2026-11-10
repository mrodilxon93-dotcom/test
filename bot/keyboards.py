import os

def get_web_url():
    return os.environ.get("WEB_APP_URL", "https://universallearninggame.vercel.app/")

def get_persistent_reply_keyboard():
    """
    Persistent Telegram Reply Keyboard pinned at the bottom of the chat,
    replacing the standard typing area with permanent action buttons.
    Uses is_persistent: true, resize_keyboard: true, one_time_keyboard: false.
    No WebAppInfo or Mini App launch configurations.
    """
    return {
        "keyboard": [
            [
                {"text": "🚀 OPEN GAME"}
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

def get_open_game_url_keyboard(url=None):
    """
    Inline keyboard containing a standard clickable external URL button.
    Opens the game in the user's external browser (Safari/Chrome/Telegram in-app browser),
    strictly WITHOUT using Telegram Mini App WebAppInfo.
    """
    target_url = url or get_web_url()
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🌐 Click to Play in Browser",
                    "url": target_url
                }
            ]
        ]
    }

def get_admin_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Refresh Stats", "callback_data": "admin_stats"},
                {"text": "👥 Recent Users", "callback_data": "admin_recent"}
            ],
            [
                {"text": "📢 Broadcast Info", "callback_data": "admin_broadcast_info"}
            ]
        ]
    }
