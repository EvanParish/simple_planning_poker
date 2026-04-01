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
from time import time

from models import Room, User

ROOM_CODE_LENGTH = 6
ROOM_CODE_CHARS = string.ascii_uppercase + string.digits

rooms: dict[str, Room] = {}


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
    # Reconnecting user
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


def clear_all_rooms() -> None:
    rooms.clear()
