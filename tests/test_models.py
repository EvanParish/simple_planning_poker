"""Tests for User and Room models."""

from time import time

from models import Room, User


class TestUser:
    def test_defaults(self):
        u = User(client_id='abc', name='Alice')
        assert u.client_id == 'abc'
        assert u.name == 'Alice'
        assert u.vote is None
        assert u.is_observer is False
        assert u.is_moderator is False
        assert u.is_connected is True
        assert isinstance(u.last_seen, float)
        assert isinstance(u.joined_at, float)
        assert u.connect_epoch == 0

    def test_custom_fields(self):
        t = time()
        u = User(
            client_id='x',
            name='Bob',
            vote='5',
            is_observer=True,
            is_moderator=True,
            is_connected=False,
            last_seen=t,
            joined_at=t,
        )
        assert u.vote == '5'
        assert u.is_observer is True
        assert u.is_moderator is True
        assert u.is_connected is False
        assert u.last_seen == t
        assert u.joined_at == t


class TestRoom:
    def test_defaults(self):
        r = Room(room_code='ABC123')
        assert r.room_code == 'ABC123'
        assert r.users == {}
        assert r.is_revealed is False
        assert r.current_topic == ''
        assert r.timer_end is None

    def test_active_users_filters_disconnected(self):
        r = Room(room_code='TEST01')
        r.users['a'] = User(client_id='a', name='Alice', is_connected=True)
        r.users['b'] = User(client_id='b', name='Bob', is_connected=False)
        r.users['c'] = User(client_id='c', name='Charlie', is_connected=True)

        active = r.active_users()
        assert len(active) == 2
        assert {u.name for u in active} == {'Alice', 'Charlie'}

    def test_active_name_set(self):
        r = Room(room_code='TEST02')
        r.users['a'] = User(client_id='a', name='Alice', is_connected=True)
        r.users['b'] = User(client_id='b', name='Bob', is_connected=False)

        names = r.active_name_set()
        assert names == {'alice'}

    def test_active_users_empty_room(self):
        r = Room(room_code='EMPTY1')
        assert r.active_users() == []
        assert r.active_name_set() == set()
