import psycopg2
import os
import select
import json

def listen_for_settings(channel: str = 'bot_settings', dsn: str | None = None):
    dsn = dsn or os.getenv('DATABASE_DSN') or os.getenv('DATABASE_URL')
    conn = psycopg2.connect(dsn)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"LISTEN {channel};")
    print(f"LISTENING on channel {channel}")
    try:
        while True:
            if select.select([conn],[],[], 60) == ([],[],[]):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = json.loads(notify.payload) if notify.payload else {}
                yield payload
    finally:
        cur.close()
        conn.close()