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
        assert len(codes) == 50

    def test_avoids_existing_codes(self):
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
        state.remove_room('NOROOM')

    def test_remove_also_clears_listeners(self):
        room = state.create_room('c1', 'Alice')
        code = room.room_code
        callback = lambda: None  # noqa: E731
        state.register_listener(code, callback)
        state.remove_room(code)
        assert code not in state._room_listeners


class TestClearAllRooms:
    def test_clears(self):
        state.create_room('c1', 'Alice')
        state.create_room('c2', 'Bob')
        assert len(state.rooms) == 2
        state.clear_all_rooms()
        assert len(state.rooms) == 0

    def test_clears_listeners(self):
        room = state.create_room('c1', 'Alice')
        state.register_listener(room.room_code, lambda: None)
        state.clear_all_rooms()
        assert len(state._room_listeners) == 0


class TestSubmitVote:
    def test_submit_valid_vote(self):
        room = state.create_room('c1', 'Alice')
        assert state.submit_vote(room, 'c1', '5') is True
        assert room.users['c1'].vote == '5'

    def test_change_vote(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.submit_vote(room, 'c1', '13')
        assert room.users['c1'].vote == '13'

    def test_vote_special_cards(self):
        room = state.create_room('c1', 'Alice')
        assert state.submit_vote(room, 'c1', '?') is True
        assert room.users['c1'].vote == '?'
        assert state.submit_vote(room, 'c1', '☕') is True
        assert room.users['c1'].vote == '☕'

    def test_reject_when_revealed(self):
        room = state.create_room('c1', 'Alice')
        state.reveal_votes(room)
        assert state.submit_vote(room, 'c1', '5') is False

    def test_reject_observer(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_observer = True
        assert state.submit_vote(room, 'c1', '5') is False

    def test_reject_invalid_card(self):
        room = state.create_room('c1', 'Alice')
        assert state.submit_vote(room, 'c1', '99') is False

    def test_reject_unknown_user(self):
        room = state.create_room('c1', 'Alice')
        assert state.submit_vote(room, 'nobody', '5') is False


class TestRevealVotes:
    def test_reveal(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        assert room.is_revealed is True


class TestResetRound:
    def test_clears_votes_and_revealed(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        state.submit_vote(room, 'c2', '8')
        state.reveal_votes(room)

        state.reset_round(room)
        assert room.is_revealed is False
        assert room.users['c1'].vote is None
        assert room.users['c2'].vote is None


class TestToggleObserver:
    def test_toggle_on_clears_vote(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        result = state.toggle_observer(room, 'c1')
        assert result is True
        assert room.users['c1'].is_observer is True
        assert room.users['c1'].vote is None

    def test_toggle_off(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_observer = True
        result = state.toggle_observer(room, 'c1')
        assert result is False
        assert room.users['c1'].is_observer is False

    def test_unknown_user_returns_none(self):
        room = state.create_room('c1', 'Alice')
        assert state.toggle_observer(room, 'nobody') is None


class TestShouldAutoReveal:
    def test_all_voted_triggers(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        state.submit_vote(room, 'c2', '8')
        assert state.should_auto_reveal(room) is True

    def test_partial_votes_no_trigger(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        assert state.should_auto_reveal(room) is False

    def test_no_votes_no_trigger(self):
        room = state.create_room('c1', 'Alice')
        assert state.should_auto_reveal(room) is False

    def test_already_revealed_no_trigger(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        assert state.should_auto_reveal(room) is False

    def test_observers_excluded_from_check(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c2'].is_observer = True
        state.submit_vote(room, 'c1', '5')
        assert state.should_auto_reveal(room) is True

    def test_all_observers_no_trigger(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_observer = True
        assert state.should_auto_reveal(room) is False

    def test_special_cards_count_as_voted(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '?')
        state.submit_vote(room, 'c2', '☕')
        assert state.should_auto_reveal(room) is True

    def test_disconnected_user_excluded(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c2'].is_connected = False
        state.submit_vote(room, 'c1', '5')
        assert state.should_auto_reveal(room) is True

    def test_single_user_voted(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '3')
        assert state.should_auto_reveal(room) is True


class TestCheckAndAutoReveal:
    def test_reveals_when_all_voted(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        assert state.check_and_auto_reveal(room) is True
        assert room.is_revealed is True

    def test_no_reveal_when_partial(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        assert state.check_and_auto_reveal(room) is False
        assert room.is_revealed is False

    def test_no_reveal_when_already_revealed(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        assert state.check_and_auto_reveal(room) is False

    def test_observer_toggle_triggers_reveal(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        state.toggle_observer(room, 'c2')
        assert state.check_and_auto_reveal(room) is True
        assert room.is_revealed is True


class TestLateJoiner:
    def test_late_joiner_cannot_vote_when_revealed(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        state.join_room(room, 'c2', 'Bob')
        assert state.submit_vote(room, 'c2', '8') is False
        assert room.users['c2'].vote is None

    def test_late_joiner_can_vote_after_reset(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        state.join_room(room, 'c2', 'Bob')
        state.reset_round(room)
        assert state.submit_vote(room, 'c2', '8') is True
        assert room.users['c2'].vote == '8'

    def test_late_joiner_sees_revealed_state(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '5')
        state.reveal_votes(room)
        state.join_room(room, 'c2', 'Bob')
        assert room.is_revealed is True
        assert room.users['c1'].vote == '5'


class TestCalculateAverage:
    def test_numeric_votes(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        state.submit_vote(room, 'c2', '8')
        assert state.calculate_average(room) == 6.5

    def test_excludes_special_cards(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.join_room(room, 'c3', 'Charlie')
        state.submit_vote(room, 'c1', '5')
        state.submit_vote(room, 'c2', '?')
        state.submit_vote(room, 'c3', '☕')
        assert state.calculate_average(room) == 5.0

    def test_no_numeric_votes(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '?')
        assert state.calculate_average(room) is None

    def test_no_votes_at_all(self):
        room = state.create_room('c1', 'Alice')
        assert state.calculate_average(room) is None

    def test_single_vote(self):
        room = state.create_room('c1', 'Alice')
        state.submit_vote(room, 'c1', '21')
        assert state.calculate_average(room) == 21.0


class TestRoomListeners:
    def test_register_and_notify(self):
        calls = []
        state.register_listener('ROOM01', lambda: calls.append(1))
        state.notify_room('ROOM01')
        assert calls == [1]

    def test_multiple_listeners(self):
        calls = []
        state.register_listener('ROOM01', lambda: calls.append('a'))
        state.register_listener('ROOM01', lambda: calls.append('b'))
        state.notify_room('ROOM01')
        assert calls == ['a', 'b']

    def test_unregister(self):
        calls = []
        cb = lambda: calls.append(1)  # noqa: E731
        state.register_listener('ROOM01', cb)
        state.unregister_listener('ROOM01', cb)
        state.notify_room('ROOM01')
        assert calls == []

    def test_unregister_nonexistent_noop(self):
        state.unregister_listener('NOPE', lambda: None)

    def test_notify_empty_room(self):
        state.notify_room('EMPTY1')  # should not raise

    def test_exception_in_listener_does_not_break_others(self):
        calls = []

        def bad_cb():
            raise RuntimeError('oops')

        state.register_listener('ROOM01', bad_cb)
        state.register_listener('ROOM01', lambda: calls.append('ok'))
        state.notify_room('ROOM01')
        assert calls == ['ok']


class TestMarkDisconnected:
    def test_marks_user_disconnected(self):
        room = state.create_room('c1', 'Alice')
        state.mark_disconnected(room, 'c1')
        assert room.users['c1'].is_connected is False

    def test_updates_last_seen(self):
        room = state.create_room('c1', 'Alice')
        old_last_seen = room.users['c1'].last_seen
        state.mark_disconnected(room, 'c1')
        assert room.users['c1'].last_seen >= old_last_seen

    def test_unknown_user_noop(self):
        room = state.create_room('c1', 'Alice')
        state.mark_disconnected(room, 'nobody')  # should not raise


class TestReconnectUser:
    def test_reconnects_disconnected_user(self):
        room = state.create_room('c1', 'Alice')
        room.users['c1'].is_connected = False
        user = state.reconnect_user(room, 'c1')
        assert user is not None
        assert user.is_connected is True

    def test_increments_connect_epoch(self):
        room = state.create_room('c1', 'Alice')
        old_epoch = room.users['c1'].connect_epoch
        state.reconnect_user(room, 'c1')
        assert room.users['c1'].connect_epoch == old_epoch + 1

    def test_updates_last_seen(self):
        room = state.create_room('c1', 'Alice')
        old_last_seen = room.users['c1'].last_seen
        state.reconnect_user(room, 'c1')
        assert room.users['c1'].last_seen >= old_last_seen

    def test_unknown_user_returns_none(self):
        room = state.create_room('c1', 'Alice')
        assert state.reconnect_user(room, 'nobody') is None

    def test_idempotent_on_connected_user(self):
        room = state.create_room('c1', 'Alice')
        user = state.reconnect_user(room, 'c1')
        assert user.is_connected is True


class TestRemoveUser:
    def test_removes_user(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.remove_user(room, 'c1')
        assert 'c1' not in room.users
        assert 'c2' in room.users

    def test_remove_nonexistent_noop(self):
        room = state.create_room('c1', 'Alice')
        state.remove_user(room, 'nobody')  # should not raise


class TestInheritModerator:
    def test_assigns_to_oldest_participant(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.join_room(room, 'c3', 'Charlie')
        # Remove the moderator
        state.remove_user(room, 'c1')
        new_mod = state.inherit_moderator(room)
        assert new_mod is not None
        assert new_mod.is_moderator is True
        # Bob joined before Charlie, so Bob should be moderator
        assert new_mod.name == 'Bob'

    def test_empty_room_returns_none(self):
        room = Room(room_code='EMPTY1')
        assert state.inherit_moderator(room) is None

    def test_skips_disconnected_users(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.join_room(room, 'c3', 'Charlie')
        state.remove_user(room, 'c1')
        room.users['c2'].is_connected = False
        new_mod = state.inherit_moderator(room)
        assert new_mod.name == 'Charlie'


class TestProcessDisconnect:
    def test_marks_disconnected_on_epoch_match(self):
        room = state.create_room('c1', 'Alice')
        epoch = room.users['c1'].connect_epoch
        result = state.process_disconnect(room.room_code, 'c1', epoch)
        assert result is True
        assert room.users['c1'].is_connected is False

    def test_rejects_on_epoch_mismatch(self):
        room = state.create_room('c1', 'Alice')
        result = state.process_disconnect(room.room_code, 'c1', 999)
        assert result is False
        assert room.users['c1'].is_connected is True

    def test_rejects_missing_room(self):
        assert state.process_disconnect('NOROOM', 'c1', 0) is False

    def test_rejects_missing_user(self):
        room = state.create_room('c1', 'Alice')
        assert state.process_disconnect(room.room_code, 'nobody', 0) is False

    def test_notifies_room(self):
        room = state.create_room('c1', 'Alice')
        calls = []
        state.register_listener(room.room_code, lambda: calls.append(1))
        epoch = room.users['c1'].connect_epoch
        state.process_disconnect(room.room_code, 'c1', epoch)
        assert calls == [1]


class TestHandleDisconnectTimeout:
    def test_removes_disconnected_user(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c2'].is_connected = False
        result = state.handle_disconnect_timeout(room.room_code, 'c2')
        assert result is True
        assert 'c2' not in room.users

    def test_skips_connected_user(self):
        room = state.create_room('c1', 'Alice')
        result = state.handle_disconnect_timeout(room.room_code, 'c1')
        assert result is False
        assert 'c1' in room.users

    def test_skips_missing_room(self):
        assert state.handle_disconnect_timeout('NOROOM', 'c1') is False

    def test_skips_missing_user(self):
        room = state.create_room('c1', 'Alice')
        assert state.handle_disconnect_timeout(room.room_code, 'nobody') is False

    def test_destroys_empty_room(self):
        room = state.create_room('c1', 'Alice')
        code = room.room_code
        room.users['c1'].is_connected = False
        state.handle_disconnect_timeout(code, 'c1')
        assert state.get_room(code) is None

    def test_inherits_moderator(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c1'].is_connected = False
        state.handle_disconnect_timeout(room.room_code, 'c1')
        assert room.users['c2'].is_moderator is True

    def test_does_not_inherit_if_not_moderator(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c2'].is_connected = False
        state.handle_disconnect_timeout(room.room_code, 'c2')
        assert room.users['c1'].is_moderator is True
        assert 'c2' not in room.users

    def test_triggers_auto_reveal_after_removal(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c1', '5')
        # Bob hasn't voted and disconnects
        room.users['c2'].is_connected = False
        state.handle_disconnect_timeout(room.room_code, 'c2')
        # Only Alice remains with a vote → auto-reveal triggers
        assert room.is_revealed is True

    def test_destroys_pending_vote(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        state.submit_vote(room, 'c2', '8')
        room.users['c2'].is_connected = False
        state.handle_disconnect_timeout(room.room_code, 'c2')
        # Bob's vote should be gone (user removed entirely)
        assert 'c2' not in room.users

    def test_notifies_room(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        room.users['c2'].is_connected = False
        calls = []
        state.register_listener(room.room_code, lambda: calls.append(1))
        state.handle_disconnect_timeout(room.room_code, 'c2')
        assert len(calls) == 1


class TestJoinRoomConnectEpoch:
    def test_reconnect_increments_epoch(self):
        room = state.create_room('c1', 'Alice')
        old_epoch = room.users['c1'].connect_epoch
        room.users['c1'].is_connected = False
        state.join_room(room, 'c1', 'Alice')
        assert room.users['c1'].connect_epoch == old_epoch + 1

    def test_new_user_starts_at_zero(self):
        room = state.create_room('c1', 'Alice')
        state.join_room(room, 'c2', 'Bob')
        assert room.users['c2'].connect_epoch == 0
