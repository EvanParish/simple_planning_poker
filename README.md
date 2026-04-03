# Simple Planning Poker

Simple Planning Poker is a lightweight, web-based planning poker app for agile teams. It runs on NiceGUI, keeps all
state in memory, and requires no accounts or database. Rooms are ephemeral: when the last user disconnects, the room is
removed.

## Features
1. Create or join a room using a 6-character alphanumeric code
2. Fibonacci voting cards plus "unsure" and "break" options
3. Auto-reveal when all non-observers vote, with moderator reveal/reset controls
4. Observer mode, vote counts, and average calculation
5. Reconnect grace period and moderator handoff
6. Light and dark theme toggle

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
