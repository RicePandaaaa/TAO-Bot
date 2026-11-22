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
"""

# Config keys editable through the config cog. Values are stored as text;
# *_role/*_channel/*_category keys hold Discord IDs.
CONFIG_KEYS = (
    "welcome_role_1",
    "welcome_role_2",
    "pt_log_channel",
    "private_category",
    "archive_category",
    "room_close_role",
    "review_216",
    "review_217",
    "review_102",
)

# Values seeded on first run so behavior matches the previously hardcoded IDs.
# These are IDs from the ENGR TAO server and are only used when a key is missing from the
# database: change live values with `/config set` (or `/config verification`), not here.
DEFAULT_CONFIG = {
    # Roles given to every new member (on_member_join in bot.py)
    "welcome_role_1": "1147655175209754764",    # "Announcements" role: server/TAO club announcement pings
    "welcome_role_2": "1147655249784492113",    # "Bulletin Board" role: bulletin board channel pings

    "pt_log_channel": "1022982386557923369",    # #bot-log channel: `/pt add` usage is logged here
    "private_category": "1488619460897280222",  # Category where `/room create` creates private PT/student channels
    # "archive_category" has no default: set it with `/config set` before `/close`/`/room archive` work

    # PT/faculty verification contact shown in `send_verification_prompt`
    "verify_name": "Alex",
    "verify_user_id": "367771798508404736",     # Alex's Discord user ID
    "verify_email": "alex-gonce@tamu.edu",
}


class Database:
    """ Async wrapper around the bot's single SQLite database """

    def __init__(self, path: str = "data/tao.db"):
        self.path = path
        self.conn: aiosqlite.Connection = None

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
        await self._drop_stats_tables()

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

    async def _drop_stats_tables(self) -> None:
        """ One-time cleanup: the removed /stats commands kept their data in these tables """
        async with self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('message_stats', 'member_stats')") as cursor:
            tables = [row[0] async for row in cursor]
        if not tables:
            return

        for table in tables:
            await self.conn.execute(f"DROP TABLE {table}")
        await self.conn.commit()
        await self.conn.execute("VACUUM")  # shrinks the file now that the data is gone
        logging.info(f"Dropped old stats tables: {', '.join(tables)}")

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
