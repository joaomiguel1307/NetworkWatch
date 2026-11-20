import sqlite3
from datetime import datetime, timezone

DB_PATH = "networkwatch.db"


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                mac TEXT,
                latency_ms REAL,
                online INTEGER NOT NULL,
                scanned_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_history_ip ON device_history(ip)")


def save_scan(devices):
    timestamp = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.executemany(
            "INSERT INTO device_history (ip, mac, latency_ms, online, scanned_at) VALUES (?, ?, ?, 1, ?)",
            [(d["ip"], d.get("mac"), d.get("latency_ms"), timestamp) for d in devices]
        )


def get_latest_devices():
    with connect() as db:
        rows = db.execute("""
            SELECT h.ip, h.mac, h.latency_ms, h.scanned_at
            FROM device_history h
            INNER JOIN (
                SELECT ip, MAX(id) AS latest_id FROM device_history GROUP BY ip
            ) latest ON latest.latest_id = h.id
            ORDER BY h.ip
        """).fetchall()
    return [dict(row) for row in rows]


def get_stats():
    with connect() as db:
        total = db.execute("SELECT COUNT(DISTINCT ip) FROM device_history").fetchone()[0]
        scans = db.execute("SELECT COUNT(DISTINCT scanned_at) FROM device_history").fetchone()[0]
        last = db.execute("SELECT MAX(scanned_at) FROM device_history").fetchone()[0]
    return {"known_devices": total, "scans": scans, "last_scan": last}
