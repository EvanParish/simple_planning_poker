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

import html
import random
import re
import string
from collections.abc import Callable
from time import time

from models import Room, User

ROOM_CODE_LENGTH = 6
ROOM_CODE_CHARS = string.ascii_uppercase + string.digits
DISCONNECT_GRACE_SECONDS = 15

CARDS = ['1', '2', '3', '5', '8', '13', '21', '?', '☕']
NUMERIC_CARDS = {'1', '2', '3', '5', '8', '13', '21'}
_GITHUB_HOSTS = r'(?:github\.com|va\.ghe\.com)'
_GITHUB_ISSUE_RE = re.compile(rf'https?://{_GITHUB_HOSTS}/[^/\s]+/([^/\s]+)/issues/(\d+)')
_GITHUB_BOARD_PREFIX_RE = re.compile(rf'https?://{_GITHUB_HOSTS}/orgs/[^/\s]+/projects/\d+/views/\d+')
_GITHUB_BOARD_ISSUE_RE = re.compile(r'issue=([^%\s&;]+)%7C([^%\s&;]+)%7C(\d+)', re.IGNORECASE)
_URL_RE = re.compile(r'https?://[^\s<>]+')

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
        existing.connect_epoch += 1
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


def should_auto_reveal(room: Room) -> bool:
    """Return True if all active non-observer users have voted."""
    if room.is_revealed:
        return False
    voters = [u for u in room.active_users() if not u.is_observer]
    if not voters:
        return False
    return all(u.vote is not None for u in voters)


def check_and_auto_reveal(room: Room) -> bool:
    """Auto-reveal if all eligible users have voted. Returns True if revealed."""
    if should_auto_reveal(room):
        reveal_votes(room)
        return True
    return False


def calculate_average(room: Room) -> float | None:
    """Calculate average of numeric votes. Returns None if no numeric votes."""
    numeric = [int(u.vote) for u in room.users.values() if u.vote in NUMERIC_CARDS]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def vote_counts(room: Room) -> list[tuple[str, int]]:
    """Count votes by card value. Returns [(card, count), ...] sorted by count desc, then card order."""
    counts: dict[str, int] = {}
    for user in room.users.values():
        if user.vote is not None:
            counts[user.vote] = counts.get(user.vote, 0) + 1
    card_order = {c: i for i, c in enumerate(CARDS)}
    return sorted(counts.items(), key=lambda x: (-x[1], card_order.get(x[0], 99)))


def set_topic(room: Room, client_id: str, text: str) -> bool:
    """Set the room's current discussion topic. Only moderators can do this."""
    user = room.users.get(client_id)
    if user is None or not user.is_moderator:
        return False
    room.current_topic = text
    return True


def format_topic_html(text: str) -> str:
    """Convert topic text to safe HTML with clickable links. GitHub issue URLs are shortened."""
    escaped = html.escape(text)

    def _replace_url(match):
        url = match.group(0)
        issue_match = _GITHUB_ISSUE_RE.fullmatch(url)
        if issue_match:
            return f'<a href="{url}" target="_blank" class="text-blue-600 underline">{issue_match.group(1)}#{issue_match.group(2)}</a>'
        if _GITHUB_BOARD_PREFIX_RE.match(url):
            board_match = _GITHUB_BOARD_ISSUE_RE.search(url)
            if board_match:
                return f'<a href="{url}" target="_blank" class="text-blue-600 underline">{board_match.group(2)}#{board_match.group(3)}</a>'
        return f'<a href="{url}" target="_blank" class="text-blue-600 underline">{url}</a>'

    result = _URL_RE.sub(_replace_url, escaped)
    return result.replace('\n', '<br>')


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


# --- Connection lifecycle ---


def mark_disconnected(room: Room, client_id: str) -> None:
    """Mark a user as disconnected and record the timestamp."""
    user = room.users.get(client_id)
    if user is None:
        return
    user.is_connected = False
    user.last_seen = time()


def reconnect_user(room: Room, client_id: str) -> User | None:
    """Re-mark a user as connected. Increments connect_epoch to invalidate stale disconnect timers."""
    user = room.users.get(client_id)
    if user is None:
        return None
    user.is_connected = True
    user.last_seen = time()
    user.connect_epoch += 1
    return user


def remove_user(room: Room, client_id: str) -> None:
    """Fully remove a user from the room."""
    room.users.pop(client_id, None)


def inherit_moderator(room: Room) -> User | None:
    """Transfer moderator to the oldest connected participant. Returns new mod or None."""
    candidates = sorted(room.active_users(), key=lambda u: u.joined_at)
    if not candidates:
        return None
    candidates[0].is_moderator = True
    return candidates[0]


def process_disconnect(room_code: str, client_id: str, connect_epoch: int) -> bool:
    """Mark a client as disconnected if the epoch matches. Returns True if marked."""
    room = get_room(room_code)
    if room is None:
        return False
    user = room.users.get(client_id)
    if user is None:
        return False
    if user.connect_epoch != connect_epoch:
        return False
    mark_disconnected(room, client_id)
    notify_room(room_code)
    return True


def handle_disconnect_timeout(room_code: str, client_id: str) -> bool:
    """Handle the end of a disconnect grace period. Returns True if user was removed."""
    room = get_room(room_code)
    if room is None:
        return False
    user = room.users.get(client_id)
    if user is None:
        return False
    if user.is_connected:
        return False
    was_moderator = user.is_moderator
    remove_user(room, client_id)
    if not room.users:
        remove_room(room_code)
        return True
    if was_moderator:
        inherit_moderator(room)
    check_and_auto_reveal(room)
    notify_room(room_code)
    return True
