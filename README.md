# grougBot

An LLM that plays World of Warcraft TBC (2.4.3) on a self-hosted CMaNGOS server, through a headless protocol client. No game client and no screen reading.

- `server/`: CMaNGOS-TBC in Docker (MariaDB, realmd, mangosd), client data extraction, DB setup, GM tools
- `bot/`: Python client that speaks the TBC network protocol (login, world session, character)

## Bot quick start

Needs Python 3.11+ and a running server.

```sh
cd bot
python hello.py          # logs in as BOT_ACCOUNT, creates/enters the character, prints position
```

Credentials come from `server/.env`, which isn't committed. On a new machine, create it with at least:

```
BOT_ACCOUNT=BOT1
BOT_PASSWORD=...
```

## Server quick start (Windows/Linux with Docker)

1. Copy a 2.4.3.8606 client somewhere and set `WOW_CLIENT_DIR` in `server/.env`, together with `DB_ROOT_PASSWORD`, `DB_PASSWORD`, `CMANGOS_COMMIT`, `TBCDB_COMMIT`, `RA_USER` and `RA_PASS`.
2. In `server/`, run each step from the comment at the top of `docker-compose.yml`: build, start db, extract, dbinit, up.
3. Run GM commands with `python tools/gm.py "account create NAME PASS 1"`.

The mmaps extraction takes hours. It only runs once, and the result is kept in the `gamedata` Docker volume.
