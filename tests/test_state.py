"""Tests for state management and game logic."""

import string

import pytest

import state
from models import Room


@pytest.fixture(autouse=True)
def _clean_state():
    """Ensure each test starts with a clean global state."""
    state.clear_all_rooms()
    yield
    state.clear_all_rooms()


class TestGenerateRoomCode:
    def test_length_and_charset(self):
        code = state.generate_room_code()
        assert len(code) == 6
        assert all(c in string.ascii_uppercase + string.digits for c in code)

    def test_uniqueness(self):
        codes = {state.generate_room_code() for _ in range(50)}
        # With 36^6 possibilities, 50 codes should all be unique
        assert len(codes) == 50

    def test_avoids_existing_codes(self):
        # Fill state with a known code, ensure generator skips it
        state.rooms['AAAAAA'] = Room(room_code='AAAAAA')
        code = state.generate_room_code()
        assert code != 'AAAAAA'


class TestGetRoom:
    def test_returns_none_for_missing(self):
        assert state.get_room('ZZZZZZ') is None

    def test_returns_room(self):
        room = state.create_room('c1', 'Alice')
        found = state.get_room(room.room_code)
        assert found is room

    def test_case_insensitive(self):
        room = state.create_room('c1', 'Alice')
        assert state.get_room(room.room_code.lower()) is room


class TestCreateRoom:
    def test_creates_room_with_moderator(self):
        room = state.create_room('c1', 'Alice')
        assert room.room_code in state.rooms
        assert len(room.users) == 1

        user = room.users['c1']
        assert user.name == 'Alice'
        assert user.is_moderator is True
        assert user.is_connected is True

    def test_room_not_revealed(self):
        room = state.create_room('c1', 'Alice')
        assert room.is_revealed is False


class TestHasDuplicateName:
    def test_no_duplicate(self):
        room = state.create_room('c1', 'Alice')
        assert state.has_duplicate_name(room, 'Bob') is False

    def test_duplicate_case_insensitive(self):
        room = state.create_room('c1', 'Alice')
        assert state.has_duplicate_name(room, 'alice') is True
        assert state.has_duplicate_name(room, 'ALICE') is True

    def test_exclude_client_id(self):
        room = state.create_room('c1', 'Alice')
        assert state.has_duplicate_name(room, 'Alice', exclude_client_id='c1') is False

    def test_disconnected_user_not_counted(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_connected = False
        assert state.has_duplicate_name(room, 'Alice') is False


class TestJoinRoom:
    def test_join_new_user(self):
        room = state.create_room('c1', 'Alice')
        user = state.join_room(room, 'c2', 'Bob')
        assert user is not None
        assert user.name == 'Bob'
        assert user.is_moderator is False
        assert 'c2' in room.users

    def test_join_duplicate_name_rejected(self):
        room = state.create_room('c1', 'Alice')
        result = state.join_room(room, 'c2', 'Alice')
        assert result is None
        assert 'c2' not in room.users

    def test_reconnect_existing_user(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_connected = False

        user = state.join_room(room, 'c1', 'Alice')
        assert user is not None
        assert user.is_connected is True
        assert user.is_moderator is True

    def test_reconnect_preserves_moderator(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_connected = False

        user = state.join_room(room, 'c1', 'Alice')
        assert user.is_moderator is True


class TestRemoveRoom:
    def test_remove_existing(self):
        room = state.create_room('c1', 'Alice')
        code = room.room_code
        state.remove_room(code)
        assert state.get_room(code) is None

    def test_remove_nonexistent_noop(self):
        state.remove_room('NOROOM')  # should not raise


class TestClearAllRooms:
    def test_clears(self):
        state.create_room('c1', 'Alice')
        state.create_room('c2', 'Bob')
        assert len(state.rooms) == 2
        state.clear_all_rooms()
        assert len(state.rooms) == 0
