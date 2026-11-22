# TAO-Bot

Discord bot for the ENGR TAO server (freshman engineering students, PTs, and faculty at TAMU).

## Project layout

```
bot.py               Start here: creates the bot, opens the database and loads every cog
cogs/                Slash commands, one file per command group (/course, /post, /pt, /room, ...)
views/               Things users click
    role_menus.py    The role selection menus (professors, student status, pronouns, pings)
    confirm.py       Confirm/Cancel buttons used before risky actions
core/                Shared code the commands use
    db.py            SQLite database: config, professor lists, private rooms
    checks.py        Role names (TAO Officer, PT, Prof), permission checks and the error handler
    utils.py         Small helpers for replying and building embeds
data/                The database file (tao.db), created on first run and not tracked by git
```

Every `.py` file in `cogs/` is loaded automatically, so a new command group only needs a new file there.
After adding or changing slash commands, run `tao.sync` in the server so Discord picks them up.
Use `/help` in the server to see every command you have access to.
