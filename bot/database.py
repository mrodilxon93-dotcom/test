import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if psycopg2 is available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 is not installed in the current environment; running in mock/fallback mode.")

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL environment variable is not set.")
        return None
    
    if not PSYCOPG2_AVAILABLE:
        logger.error("psycopg2 is required to connect to DATABASE_URL.")
        return None

    try:
        # Supabase and modern clouds require sslmode='require'
        ssl_mode = "require" if "supabase" in db_url or "sslmode" not in db_url else None
        conn_kwargs = {"connect_timeout": 5}
        if ssl_mode and "sslmode=" not in db_url:
            conn_kwargs["sslmode"] = ssl_mode

        conn = psycopg2.connect(db_url, **conn_kwargs)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def init_db_schema():
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_interaction_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_start_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                start_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE INDEX IF NOT EXISTS idx_telegram_users_status ON telegram_users(status);
            CREATE INDEX IF NOT EXISTS idx_telegram_users_last_interaction ON telegram_users(last_interaction_at);
            """)
        return True
    except Exception as e:
        logger.error(f"Failed to initialize schema: {e}")
        return False
    finally:
        conn.close()

def upsert_user_start(user_id: int, username: str = None, first_name: str = None) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
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
        return True
    except Exception as e:
        logger.error(f"Failed to upsert user start: {e}")
        return False
    finally:
        conn.close()

def update_user_interaction(user_id: int, username: str = None, first_name: str = None) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
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
        return True
    except Exception as e:
        logger.error(f"Failed to update user interaction: {e}")
        return False
    finally:
        conn.close()

def mark_user_blocked(user_id: int) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE telegram_users SET status = 'blocked', last_interaction_at = NOW() WHERE user_id = %s;", (user_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to mark user as blocked: {e}")
        return False
    finally:
        conn.close()

def get_user_stats() -> dict:
    conn = get_connection()
    if not conn:
        return {
            "total_users": 0,
            "joined_today": 0,
            "interacted_today": 0,
            "total_starts": 0,
            "active_users": 0,
            "blocked_users": 0,
            "db_connected": False
        }
    try:
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
            stats = dict(row) if row else {}
            stats["db_connected"] = True
            return stats
    except Exception as e:
        logger.error(f"Failed to fetch user stats: {e}")
        return {"total_users": 0, "db_connected": False, "error": str(e)}
    finally:
        conn.close()

def get_recent_users(limit: int = 10) -> list:
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT user_id, username, first_name, registered_at, last_interaction_at, start_count, status
            FROM telegram_users
            ORDER BY last_interaction_at DESC
            LIMIT %s;
            """, (limit,))
            return list(cur.fetchall())
    except Exception as e:
        logger.error(f"Failed to fetch recent users: {e}")
        return []
    finally:
        conn.close()

def get_all_active_user_ids() -> list:
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM telegram_users WHERE status = 'active' ORDER BY last_interaction_at DESC;")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Failed to fetch active user IDs: {e}")
        return []
    finally:
        conn.close()
