# TAO-Bot

Discord bot for the ENGR TAO server (freshman engineering students, PTs, and faculty at TAMU).
Single-server bot hosted on SparkedHost.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python bot.py
```

Create a `.env` file with:

```
TOKEN=<bot token>
READY_CHANNEL_ID=<channel the bot greets on startup>
```

Everything else is stored in `data/tao.db` (SQLite, created automatically) and is editable
through commands **without restarting the bot**.

## Runtime configuration

All commands below are officer-only (`TAO Officer` role) unless noted.

| Command | Purpose |
|---|---|
| `config_list` | Show all config keys and current values |
| `config_get <key>` / `config_set <key> <value>` | Read/write one config value (IDs are validated against the server) |
| `set_professors <class> <names>` | Replace a class's professor list (comma-separated last names) |
| `list_professors [class]` | Show configured professors (all classes if omitted) |
| `set_216_review_link` / `set_217_review_link` / `set_102_review_link` | Update the current-semester review links (persisted) |

Config keys: `welcome_role_1`, `welcome_role_2` (roles added on member join), `pt_log_channel`
(where `make_pt` is logged), `private_category` / `archive_category` (for `room` / `close` /
`archive_rooms`), `review_216` / `review_217` / `review_102`.

After changing a professor list, re-post the selection prompt with `send_prof_prompt` — old
prompts keep showing the old options.

## Statistics

The bot counts messages per channel per hour (no message content is stored) and member
joins/leaves per day, all in America/Chicago time. Counts are flushed to the database once a
minute. Officer-only query commands:

| Command | Output |
|---|---|
| `stats [week\|month\|semester]` | Server-wide messages/day chart + totals, busiest day, top channels |
| `stats channel <channel> [period]` | Same for a single channel |
| `stats growth [period]` | Joins/leaves/net chart + member count |
| `stats heatmap [weeks]` | Day-of-week × hour-of-day heatmap (prime-time finder) |

`semester` = last 120 days.

## Deployment notes

- **First run** migrates the legacy `cogs/*.csv` professor lists into the database (only when
  the professors table is empty). The CSVs can be deleted after the first successful run.
- **After deploying new/changed commands**, run `tao.sync` (or `tao.sync ~` for instant
  guild-only sync) so slash commands update.
- **Prompts posted before the persistent-view update** (July 2026) use old button/select IDs
  and must be re-posted once (`send_announcements_prompt`, `send_tao_review_prompt`,
  `send_welcome_prompt`, `send_prof_prompt`). Prompts posted after it keep working across
  restarts.
- `data/` (the SQLite DB and its WAL sidecar files) must persist across restarts and is
  gitignored — back it up occasionally.
