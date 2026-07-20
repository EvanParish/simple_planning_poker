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

> [!Note]
> Multi-arch images (`linux/amd64` and `linux/arm64`) are published to Docker Hub.

Build and run locally with compose (reads `STORAGE_SECRET` from `.env`):
```bash
cp .env.example .env   # then edit STORAGE_SECRET
docker compose up --build
```

Or pull and run the prebuilt image:
```bash
docker run -d -p 5858:5858 \
  -e STORAGE_SECRET="$(python -c 'import os; print(os.urandom(24).hex())')" \
  evanoddball/simple_planning_poker
```

Or run the prebuilt image using compose:
```yml
services:
  app:
    build: .
    image: evanoddball/simple_planning_poker
    container_name: simple-planning-poker
    restart: unless-stopped
    ports:
      - "5858:5858"
    env_file:
      - .env
```

Open `http://localhost:5858` to connect.

## Run locally (uv)
Requires Python 3.14 (see `.python-version`).

1. Install [uv](https://astral.sh/uv/).
2. Install dependencies: `uv sync`
3. Start the app: `uv run main.py`
4. Open `http://localhost:5858`

## Configuration
- `STORAGE_SECRET` (optional): set a fixed secret for NiceGUI storage. If not set, one is generated at startup.
- `RELOAD` (optional): set to `true` to enable hot-reload (development only). Defaults to off.
