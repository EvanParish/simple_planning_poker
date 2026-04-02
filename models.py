"""Pydantic/dataclass models for User and Room."""

from dataclasses import dataclass, field
from time import time


@dataclass
class User:
    client_id: str
    name: str
    vote: str | None = None
    is_observer: bool = False
    is_moderator: bool = False
    is_connected: bool = True
    last_seen: float = field(default_factory=time)
    joined_at: float = field(default_factory=time)
    connect_epoch: int = 0


@dataclass
class Room:
    room_code: str
    users: dict[str, User] = field(default_factory=dict)
    is_revealed: bool = False

    def active_users(self) -> list[User]:
        return [u for u in self.users.values() if u.is_connected]

    def active_name_set(self) -> set[str]:
        return {u.name.lower() for u in self.active_users()}
