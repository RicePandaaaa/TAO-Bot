import csv
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite

CENTRAL = ZoneInfo("America/Chicago")

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS professors (
    class_name TEXT NOT NULL,
    prof_name  TEXT NOT NULL,
    PRIMARY KEY (class_name, prof_name)
);

CREATE TABLE IF NOT EXISTS private_rooms (
    channel_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_stats (
    channel_id INTEGER NOT NULL,
    hour_ts    TEXT NOT NULL,
    dow        INTEGER NOT NULL,
    hour       INTEGER NOT NULL,
    count      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (channel_id, hour_ts)
);

CREATE TABLE IF NOT EXISTS member_stats (
    day    TEXT PRIMARY KEY,
    joins  INTEGER NOT NULL DEFAULT 0,
    leaves INTEGER NOT NULL DEFAULT 0
);
"""

# Config keys editable through the config cog. Values are stored as text;
# *_role/*_channel/*_category keys hold Discord IDs.
CONFIG_KEYS = (
    "welcome_role_1",
    "welcome_role_2",
    "pt_log_channel",
    "private_category",
    "archive_category",
    "review_216",
    "review_217",
    "review_102",
)

# Values seeded on first run so behavior matches the previously hardcoded IDs
DEFAULT_CONFIG = {
    "welcome_role_1": "1147655175209754764",
    "welcome_role_2": "1147655249784492113",
    "pt_log_channel": "1022982386557923369",
    "private_category": "1488619460897280222",
}


class Database:
    """ Async wrapper around the bot's single SQLite database """

    def __init__(self, path: str = "data/tao.db"):
        self.path = path
        self.conn: aiosqlite.Connection = None  # type: ignore[assignment]

    async def init(self) -> None:
        """ Opens the connection, creates tables, and runs one-time migrations """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)

        for key, value in DEFAULT_CONFIG.items():
            await self.conn.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (key, value))

        await self._migrate_csvs()
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.commit()
            await self.conn.close()

    async def _migrate_csvs(self) -> None:
        """ One-time import of the legacy cogs/*.csv professor lists (only when the table is empty) """
        async with self.conn.execute("SELECT COUNT(*) FROM professors") as cursor:
            row = await cursor.fetchone()
            if row is not None and row[0] > 0:
                return

        if not os.path.isdir("cogs"):
            return

        for filename in os.listdir("cogs"):
            if not filename.endswith(".csv"):
                continue

            class_name = filename[:-4]
            with open(os.path.join("cogs", filename), "r") as csv_file:
                for row in csv.reader(csv_file):
                    if not row:
                        continue
                    professor = row[0].strip()
                    if not professor or professor == "TBD":
                        continue
                    await self.conn.execute(
                        "INSERT OR IGNORE INTO professors (class_name, prof_name) VALUES (?, ?)",
                        (class_name, professor))
                    logging.info(f"Migrated professor \"{professor}\" for \"{class_name}\" from CSV")

    # ---------- Config ----------

    async def get_config(self, key: str, default: str | None = None) -> str | None:
        async with self.conn.execute("SELECT value FROM config WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row is not None else default

    async def get_config_id(self, key: str) -> int | None:
        """ Fetches a config value and converts it to a Discord ID, or None if unset/invalid """
        value = await self.get_config(key)
        try:
            return int(value) if value is not None else None
        except ValueError:
            logging.warning(f"Config key \"{key}\" holds a non-numeric value: {value}")
            return None

    async def set_config(self, key: str, value: str) -> None:
        await self.conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value))
        await self.conn.commit()

    async def all_config(self) -> dict[str, str]:
        async with self.conn.execute("SELECT key, value FROM config") as cursor:
            return {key: value async for key, value in cursor}

    # ---------- Professors ----------

    async def get_professors(self, class_name: str) -> list[str]:
        async with self.conn.execute(
                "SELECT prof_name FROM professors WHERE class_name = ? ORDER BY prof_name", (class_name,)) as cursor:
            return [row[0] async for row in cursor]

    async def set_professors(self, class_name: str, prof_names: list[str]) -> None:
        """ Replaces the professor list for a class in one transaction """
        await self.conn.execute("DELETE FROM professors WHERE class_name = ?", (class_name,))
        await self.conn.executemany(
            "INSERT OR IGNORE INTO professors (class_name, prof_name) VALUES (?, ?)",
            [(class_name, name) for name in prof_names])
        await self.conn.commit()

    async def all_classes(self) -> list[str]:
        async with self.conn.execute("SELECT DISTINCT class_name FROM professors ORDER BY class_name") as cursor:
            return [row[0] async for row in cursor]

    # ---------- Private rooms ----------

    async def add_room(self, channel_id: int, student_id: int) -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO private_rooms (channel_id, student_id, created_at) VALUES (?, ?, ?)",
            (channel_id, student_id, datetime.now(CENTRAL).isoformat()))
        await self.conn.commit()

    async def get_room_student(self, channel_id: int) -> int | None:
        async with self.conn.execute(
                "SELECT student_id FROM private_rooms WHERE channel_id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row is not None else None

    async def remove_room(self, channel_id: int) -> None:
        await self.conn.execute("DELETE FROM private_rooms WHERE channel_id = ?", (channel_id,))
        await self.conn.commit()

    # ---------- Statistics ----------

    async def add_message_counts(self, counts: dict[tuple[int, str], int]) -> None:
        """ Flushes aggregated message counts, keyed by (channel_id, 'YYYY-MM-DDTHH:00' Central time) """
        rows = []
        for (channel_id, hour_ts), count in counts.items():
            bucket = datetime.fromisoformat(hour_ts)
            rows.append((channel_id, hour_ts, bucket.weekday(), bucket.hour, count))

        await self.conn.executemany(
            "INSERT INTO message_stats (channel_id, hour_ts, dow, hour, count) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(channel_id, hour_ts) DO UPDATE SET count = count + excluded.count",
            rows)
        await self.conn.commit()

    async def add_member_event(self, joined: bool) -> None:
        """ Records a member join or leave for today (Central time) """
        day = datetime.now(CENTRAL).strftime("%Y-%m-%d")
        if joined:
            await self.conn.execute(
                "INSERT INTO member_stats (day, joins, leaves) VALUES (?, 1, 0) "
                "ON CONFLICT(day) DO UPDATE SET joins = joins + 1", (day,))
        else:
            await self.conn.execute(
                "INSERT INTO member_stats (day, joins, leaves) VALUES (?, 0, 1) "
                "ON CONFLICT(day) DO UPDATE SET leaves = leaves + 1", (day,))
        await self.conn.commit()

    async def messages_per_day(self, since: str, channel_id: int | None = None) -> list[tuple[str, int]]:
        """ Daily message totals since the given 'YYYY-MM-DD', optionally for one channel """
        query = "SELECT substr(hour_ts, 1, 10) AS day, SUM(count) FROM message_stats WHERE hour_ts >= ?"
        params: list = [since]
        if channel_id is not None:
            query += " AND channel_id = ?"
            params.append(channel_id)
        query += " GROUP BY day ORDER BY day"

        async with self.conn.execute(query, params) as cursor:
            return [(day, total) async for day, total in cursor]

    async def top_channels(self, since: str, limit: int = 5) -> list[tuple[int, int]]:
        """ The busiest channels since the given 'YYYY-MM-DD' """
        async with self.conn.execute(
                "SELECT channel_id, SUM(count) AS total FROM message_stats WHERE hour_ts >= ? "
                "GROUP BY channel_id ORDER BY total DESC LIMIT ?", (since, limit)) as cursor:
            return [(channel_id, total) async for channel_id, total in cursor]

    async def heatmap_counts(self, since: str) -> list[tuple[int, int, int]]:
        """ (dow, hour, total) triples since the given 'YYYY-MM-DD' """
        async with self.conn.execute(
                "SELECT dow, hour, SUM(count) FROM message_stats WHERE hour_ts >= ? GROUP BY dow, hour",
                (since,)) as cursor:
            return [(dow, hour, total) async for dow, hour, total in cursor]

    async def member_events_per_day(self, since: str) -> list[tuple[str, int, int]]:
        """ (day, joins, leaves) rows since the given 'YYYY-MM-DD' """
        async with self.conn.execute(
                "SELECT day, joins, leaves FROM member_stats WHERE day >= ? ORDER BY day", (since,)) as cursor:
            return [(day, joins, leaves) async for day, joins, leaves in cursor]
