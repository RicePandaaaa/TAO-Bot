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

The bot also needs **Message Content Intent** enabled in the Discord Developer Portal
under the bot's Privileged Gateway Intents. The code enables this intent in `bot.py`.

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

## Website message log

The message log focuses on tracking the messages sent into the configured channels (optionally also tracking messages that mention a configured role). 

Content, date, time, and message IDs are stored in the logged data within logs/sorted_data.json. 

Tracked channels and roles are stored separately in logs/tracked_IDs.json when restarting the bot.

All of this is managed hrough the web log command (weblog). Each message is able to be filed under more than one category at once (its channel's category and every mentioned (within the message) role's category). If an edit changes the roles mentioned, the message adjusts the categories, removing from the deleted mentioned role's categories and adding the new mentioned categories.

If a message is deleted, they are removed from the logs and their category is renumbered to prevent gaps. This should happen only for accidental duplicate posts caught immediately and does not keep permanent announcement history of the channels it tracks.

Command: weblog action: [add | delete | list] [channel: <#channel> | role: <@role>] name: [ category ]

Adding a channel or role adds the id of the channel or role with the name of the category to the tracked list. 
| *requires action, id (channel or role), and name

Deleting a channel or role removes the id of the channel or role from the tracked list.
| *requires action and id (channel or role)

List provides all of the tracked channels and roles.
| *requires action

*This command requires administration access to change any of its parameters for tracked roles and channels. The responses for its commands show in the channel it is run within.

## Deployment notes

- **First run** migrates the legacy `cogs/*.csv` professor lists into the database (only when
  the professors table is empty). The CSVs can be deleted after the first successful run.
- **After deploying new/changed commands**, run `tao.sync` (or `tao.sync ~` for instant
  guild-only sync) so slash commands update.
- **Prompts posted before the persistent-view update** (July 2026) use old button/select IDs
  and must be re-posted once (`send_announcements_prompt`, `send_tao_review_prompt`,
  `send_welcome_prompt`, `send_prof_prompt`). Prompts posted after it keep working across
  restarts.
- `data/` (the SQLite DB and its WAL sidecar files) and `logs/` (message log and tracked-ID JSON files) must persist across restarts and is
  gitignored — back it up occasionally.
