# Simple Planning Poker

Simple Planning Poker is a lightweight, web-based planning poker app for agile teams. It runs on NiceGUI, keeps all
state in memory, and requires no accounts or database. Rooms are ephemeral: when the last user disconnects, the room is
removed.

## Features
1. Create or join a room using a 6-character alphanumeric code (with shareable invite link)
2. Fibonacci voting cards (1–21) plus "?" (unsure) and "☕" (break) options
3. Auto-reveal when all non-observers vote, with moderator reveal/reset controls
4. Observer mode, vote distribution, and average calculation (excludes ? and ☕)
5. Moderator topic area with GitHub issue URL shortening (`repo#number` links)
6. Countdown timer with presets (1m–5m) and custom duration, auto-reveal on expiry, and audio chimes
7. Moderator transfer and automatic inheritance on disconnect
8. Reconnect grace period with departed vote preservation
9. Duplicate display-name detection
10. Light and dark theme toggle

## Run with Docker
```bash
docker compose up --build
```

Open `http://localhost:5858`

## Run locally (uv)
Requires Python 3.14 (see `.python-version`).

1. Install [uv](https://astral.sh/uv/).
2. Install dependencies: `uv sync`
3. Start the app: `uv run main.py`
4. Open `http://localhost:5858`

## Configuration
- `STORAGE_SECRET` (optional): set a fixed secret for NiceGUI storage. If not set, one is generated at startup.
