import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

def get_bot_token():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable is missing!")
    return token

def telegram_api_call(method: str, payload: dict = None) -> dict:
    token = get_bot_token()
    if not token:
        return {"ok": False, "description": "BOT_TOKEN not configured"}
    
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        response = requests.post(
            url,
            json=payload or {},
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API request failed ({method}): {e}")
        return {"ok": False, "description": str(e)}

def send_message(chat_id, text: str, reply_markup: dict = None, parse_mode: str = "HTML") -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return telegram_api_call("sendMessage", payload)

def edit_message_text(chat_id, message_id: int, text: str, reply_markup: dict = None, parse_mode: str = "HTML") -> dict:
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return telegram_api_call("editMessageText", payload)

def answer_callback_query(callback_query_id: str, text: str = None, show_alert: bool = False) -> dict:
    payload = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        payload["text"] = text
    return telegram_api_call("answerCallbackQuery", payload)

def set_webhook(url: str, secret_token: str = None) -> dict:
    payload = {
        "url": url,
        "allowed_updates": ["message", "callback_query"]
    }
    if secret_token:
        payload["secret_token"] = secret_token
    return telegram_api_call("setWebhook", payload)

def get_webhook_info() -> dict:
    return telegram_api_call("getWebhookInfo")

def delete_webhook(drop_pending_updates: bool = False) -> dict:
    payload = {"drop_pending_updates": drop_pending_updates}
    return telegram_api_call("deleteWebhook", payload)
