"""In-memory state manager and core game logic.

Maps room codes to Room objects. Contains functions for:
- Room creation and lookup
- Room code generation
- Vote submission and reset
- Average calculation (excluding ? and ☕)
- Auto-reveal check
- Disconnect grace period handling
- Moderator inheritance
"""

import random
import string
from collections.abc import Callable
from time import time

from models import Room, User

ROOM_CODE_LENGTH = 6
ROOM_CODE_CHARS = string.ascii_uppercase + string.digits

CARDS = ['1', '2', '3', '5', '8', '13', '21', '?', '☕']
NUMERIC_CARDS = {'1', '2', '3', '5', '8', '13', '21'}

rooms: dict[str, Room] = {}
_room_listeners: dict[str, list[Callable]] = {}


# --- Room CRUD ---


def generate_room_code() -> str:
    while True:
        code = ''.join(random.choices(ROOM_CODE_CHARS, k=ROOM_CODE_LENGTH))
        if code not in rooms:
            return code


def get_room(room_code: str) -> Room | None:
    return rooms.get(room_code.upper())


def create_room(client_id: str, name: str) -> Room:
    code = generate_room_code()
    user = User(
        client_id=client_id,
        name=name,
        is_moderator=True,
        joined_at=time(),
        last_seen=time(),
    )
    room = Room(room_code=code, users={client_id: user})
    rooms[code] = room
    return room


def has_duplicate_name(room: Room, name: str, exclude_client_id: str | None = None) -> bool:
    for user in room.active_users():
        if user.client_id == exclude_client_id:
            continue
        if user.name.lower() == name.lower():
            return True
    return False


def join_room(room: Room, client_id: str, name: str) -> User | None:
    """Add a user to a room. Returns the User on success, None if name is taken."""
    if client_id in room.users:
        existing = room.users[client_id]
        existing.is_connected = True
        existing.last_seen = time()
        return existing

    if has_duplicate_name(room, name):
        return None

    user = User(
        client_id=client_id,
        name=name,
        joined_at=time(),
        last_seen=time(),
    )
    room.users[client_id] = user
    return user


def remove_room(room_code: str) -> None:
    rooms.pop(room_code.upper(), None)
    _room_listeners.pop(room_code.upper(), None)


def clear_all_rooms() -> None:
    rooms.clear()
    _room_listeners.clear()


# --- Voting logic ---


def submit_vote(room: Room, client_id: str, card: str) -> bool:
    """Submit or change a vote. Returns True if successful."""
    if room.is_revealed:
        return False
    user = room.users.get(client_id)
    if user is None or user.is_observer:
        return False
    if card not in CARDS:
        return False
    user.vote = card
    return True


def reveal_votes(room: Room) -> None:
    room.is_revealed = True


def reset_round(room: Room) -> None:
    room.is_revealed = False
    for user in room.users.values():
        user.vote = None


def toggle_observer(room: Room, client_id: str) -> bool | None:
    """Toggle observer status. Returns new status, or None if user not found."""
    user = room.users.get(client_id)
    if user is None:
        return None
    user.is_observer = not user.is_observer
    if user.is_observer:
        user.vote = None
    return user.is_observer


def calculate_average(room: Room) -> float | None:
    """Calculate average of numeric votes. Returns None if no numeric votes."""
    numeric = [int(u.vote) for u in room.users.values() if u.vote in NUMERIC_CARDS]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


# --- Room update listeners (for real-time sync) ---


def register_listener(room_code: str, callback: Callable) -> None:
    _room_listeners.setdefault(room_code, []).append(callback)


def unregister_listener(room_code: str, callback: Callable) -> None:
    listeners = _room_listeners.get(room_code, [])
    if callback in listeners:
        listeners.remove(callback)


def notify_room(room_code: str) -> None:
    for cb in list(_room_listeners.get(room_code, [])):
        try:
            cb()
        except Exception:
            pass
