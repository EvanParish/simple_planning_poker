# Copilot Instructions

## Commands

- **Run:** `uv run main.py`
- **Lint:** `uv run ruff check .`
- **Lint (fix):** `uv run ruff check --fix .`
- **Format:** `uv run ruff format .`
- **Format (check):** `uv run ruff format --check .`
- **Add dependency:** `uv add <package>`
- **Add dev dependency:** `uv add --group dev <package>`
- **Test (all):** `uv run pytest`
- **Test (single file):** `uv run pytest tests/test_state.py`
- **Test (single test):** `uv run pytest tests/test_state.py::test_calculate_average`
- **Test (keyword match):** `uv run pytest -k "auto_reveal"`
- **Test (with coverage):** `uv run pytest --cov --cov-report=term-missing`

## Architecture

This is a web-based planning poker app using **NiceGUI** with fully in-memory state (no database). See `spec.md` for the full product spec.

### Target file structure

- `main.py` — Entry point, NiceGUI config, route definitions
- `models.py` — Pydantic/dataclass models for `User` and `Room`
- `state.py` — In-memory state store (dict of room code → `Room`) and core logic (averages, auto-reveal)
- `ui.py` — Reusable NiceGUI UI components (voting cards, user rows, moderator controls)

### Key design constraints

- **No external databases** — all state lives in Python data structures in memory
- **No auth systems** — identity is a session/local-storage token scoped to the room lifetime
- **No external CSS frameworks** — use only NiceGUI's built-in Tailwind integration

### State model

- Rooms are keyed by a 6-digit alphanumeric code
- Users are keyed by a UUID `client_id` stored in browser local storage
- Disconnected users get a 15-second grace period before removal
- Moderator role inherits to the oldest remaining participant on disconnect

## Conventions

- **Python 3.14** managed via `uv` (see `.python-version`)
- **Ruff** for linting and formatting (configured in `pyproject.toml`)
- Single quotes for strings, 120-char line length, 4-space indent
- Max cyclomatic complexity: 6 (`C901` rule)
- Voting cards: Fibonacci (1, 2, 3, 5, 8, 13, 21) plus `?` and `☕`
- `?` and `☕` votes are excluded from average calculations

## Testing

All application logic (`models.py`, `state.py`, and any non-UI module) must have 100% test coverage. UI components (`ui.py`) are excluded from coverage requirements.

Tests live in a `tests/` directory mirroring the source structure (e.g., `tests/test_state.py` for `state.py`). Use `pytest` with `pytest-cov` for coverage.

When adding or changing application logic, always add or update corresponding tests in the same commit.

## Git Permissions

- **DO NOT COMMIT CHANGES WITHOUT EXPLICIT USER APPROVAL** - Always wait for the user to review and approve changes before committing. This ensures that all modifications align with user expectations and project requirements.