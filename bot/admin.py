import os
import time
import logging
from bot import client, database, keyboards, messages

logger = logging.getLogger(__name__)

def get_admin_ids() -> list:
    raw_admin = os.environ.get("ADMIN_ID", "")
    ids = []
    for part in raw_admin.replace(" ", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids

def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()

def render_admin_stats() -> str:
    stats = database.get_user_stats()
    db_status = "🟢 Connected (PostgreSQL / Supabase)" if stats.get("db_connected") else "🔴 Not Connected (Check DATABASE_URL)"

    text = f"""📊 <b>Universal Learning Game — Admin Dashboard</b>

<b>Database Status:</b> {db_status}

<b>📈 User Analytics:</b>
• <b>Total Registered Users:</b> <code>{stats.get('total_users', 0)}</code>
• <b>Active Users:</b> <code>{stats.get('active_users', 0)}</code>
• <b>Blocked Users:</b> <code>{stats.get('blocked_users', 0)}</code>
• <b>Joined Today:</b> <code>{stats.get('joined_today', 0)}</code>
• <b>Interacted Today:</b> <code>{stats.get('interacted_today', 0)}</code>
• <b>Total /start Commands:</b> <code>{stats.get('total_starts', 0)}</code>

<b>⚡ Admin Controls:</b>
• Send <code>/broadcast &lt;message&gt;</code> to broadcast an announcement to all active users.
• Tap <b>Recent Users</b> below to inspect recent activity logs."""
    return text

def handle_admin_command(user_id: int, chat_id: int, text: str):
    if not is_admin(user_id):
        client.send_message(chat_id, messages.ADMIN_ACCESS_DENIED)
        return

    text_clean = text.strip()

    # /broadcast command handler
    if text_clean.startswith("/broadcast"):
        parts = text_clean.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            client.send_message(
                chat_id,
                "⚠️ <b>Broadcast format missing.</b>\n\nUsage: <code>/broadcast &lt;Your message here&gt;</code>\n\nSupports standard HTML tags (<b>bold</b>, <i>italic</i>, <code>code</code>, <a href='...'>link</a>)."
            )
            return

        broadcast_text = parts[1].strip()
        execute_broadcast(chat_id, broadcast_text)
        return

    # Default /admin or /admin stats
    stats_text = render_admin_stats()
    client.send_message(chat_id, stats_text, reply_markup=keyboards.get_admin_keyboard())

def execute_broadcast(admin_chat_id: int, text: str):
    user_ids = database.get_all_active_user_ids()
    total_target = len(user_ids)

    if total_target == 0:
        client.send_message(
            admin_chat_id,
            "⚠️ <b>No active users found in the database.</b>\n\nUsers are automatically registered when they press /start in the bot."
        )
        return

    status_msg = client.send_message(
        admin_chat_id,
        f"⏳ <b>Broadcasting announcement...</b>\n\nTargeting <code>{total_target}</code> registered users. Please wait."
    )
    status_msg_id = status_msg.get("result", {}).get("message_id")

    delivered = 0
    blocked = 0
    failed = 0

    for idx, uid in enumerate(user_ids, 1):
        res = client.send_message(uid, text)
        if res.get("ok"):
            delivered += 1
        else:
            err_desc = res.get("description", "").lower()
            if "blocked" in err_desc or "deactivated" in err_desc or "user is deactivated" in err_desc:
                blocked += 1
                database.mark_user_blocked(uid)
            elif "too many requests" in err_desc:
                retry_after = res.get("parameters", {}).get("retry_after", 1)
                time.sleep(retry_after)
                # Retry once
                retry_res = client.send_message(uid, text)
                if retry_res.get("ok"):
                    delivered += 1
                else:
                    failed += 1
            else:
                failed += 1

        # Rate limit safety: Telegram allows ~30 messages/sec broadcast limit; sleep 0.04s
        time.sleep(0.04)

        # Update status periodically for large sets
        if status_msg_id and idx % 25 == 0:
            client.edit_message_text(
                admin_chat_id,
                status_msg_id,
                f"⏳ <b>Broadcasting progress:</b> {idx}/{total_target}\n• Delivered: {delivered}\n• Blocked: {blocked}\n• Failed: {failed}"
            )

    report = f"""📢 <b>Broadcast Announcement Complete!</b>

<b>Delivery Statistics:</b>
• <b>Total Targeted:</b> <code>{total_target}</code>
• <b>Successfully Delivered:</b> <code>{delivered}</code>
• <b>Blocked (Removed from active):</b> <code>{blocked}</code>
• <b>Failed (API errors):</b> <code>{failed}</code>

<i>All blocked user profiles have been automatically updated in the database to prevent future delivery attempts.</i>"""

    if status_msg_id:
        client.edit_message_text(admin_chat_id, status_msg_id, report)
    else:
        client.send_message(admin_chat_id, report)

def handle_admin_callback(user_id: int, chat_id: int, message_id: int, data: str):
    if not is_admin(user_id):
        client.send_message(chat_id, messages.ADMIN_ACCESS_DENIED)
        return

    if data == "admin_stats":
        stats_text = render_admin_stats()
        client.edit_message_text(chat_id, message_id, stats_text, reply_markup=keyboards.get_admin_keyboard())
    elif data == "admin_recent":
        recent_users = database.get_recent_users(10)
        if not recent_users:
            text = "👥 <b>Recent Users</b>\n\nNo user activity recorded yet."
        else:
            lines = ["👥 <b>10 Most Recently Active Users:</b>\n"]
            for u in recent_users:
                uname = f"@{u.get('username')}" if u.get('username') else "No username"
                fname = u.get('first_name') or "Unknown"
                uid = u.get('user_id')
                starts = u.get('start_count', 1)
                status = u.get('status', 'active')
                lines.append(f"• <b>{fname}</b> ({uname}) [<code>{uid}</code>]\n  └ Starts: {starts} | Status: {status}")
            text = "\n".join(lines)
        client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_admin_keyboard())
    elif data == "admin_broadcast_info":
        text = messages.get_admin_help_message()
        client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_admin_keyboard())
