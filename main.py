import asyncio
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from nicegui import app, ui  # noqa: E402

import state  # noqa: E402
from ui import (  # noqa: E402
    render_header,
    render_observer_toggle,
    render_results_banner,
    render_topic_area,
    render_user_list,
    render_voting_cards,
)


def _get_or_create_client_id() -> str:
    storage = app.storage.user
    if 'client_id' not in storage:
        storage['client_id'] = str(uuid.uuid4())
    return storage['client_id']


def _validate_name(name_input: ui.input) -> bool:
    name_input.validate()
    return not name_input.error


async def _on_create_room(name_input: ui.input):
    if not _validate_name(name_input):
        return
    client_id = _get_or_create_client_id()
    name = name_input.value.strip()
    room = state.create_room(client_id, name)
    ui.navigate.to(f'/room/{room.room_code}')


async def _on_join_room(name_input: ui.input, room_code_input: ui.input):
    if not _validate_name(name_input):
        return
    room_code_input.validate()
    if room_code_input.error:
        return
    if not room_code_input.value:
        room_code_input.error = 'Room code is required'
        room_code_input.update()
        return

    code = room_code_input.value.strip().upper()
    room = state.get_room(code)
    if room is None:
        ui.notify('Room not found. Check the code and try again.', type='negative')
        return

    client_id = _get_or_create_client_id()
    name = name_input.value.strip()
    user = state.join_room(room, client_id, name)
    if user is None:
        ui.notify('That name is already taken in this room. Please choose another.', type='warning')
        return

    state.notify_room(room.room_code)
    ui.navigate.to(f'/room/{room.room_code}')


@ui.page('/')
def landing_page(room: str = ''):
    ui.query('body').classes('bg-gray-100')

    with ui.card().classes('absolute-center w-96 p-8'):
        ui.label('Planning Poker').classes('text-3xl font-bold text-center w-full mb-2')
        ui.label('Estimate together, without the influence.').classes('text-sm text-gray-500 text-center w-full mb-6')

        name_input = ui.input(
            label='Display Name',
            placeholder='Enter your name',
            validation={'Name is required': lambda v: bool(v and v.strip())},
        ).classes('w-full')

        room_code_input = ui.input(
            label='Room Code',
            placeholder='6-digit code',
            value=room,
            validation={'Must be 6 alphanumeric characters': lambda v: not v or (len(v) == 6 and v.isalnum())},
        ).classes('w-full')

        with ui.row().classes('w-full mt-4 gap-2'):
            ui.button('Create Room', on_click=lambda: _on_create_room(name_input), color='primary').classes('flex-1')
            ui.button(
                'Join Room', on_click=lambda: _on_join_room(name_input, room_code_input), color='secondary'
            ).classes('flex-1')


async def _delayed_disconnect_removal(room_code: str, client_id: str, expected_epoch: int):
    """Wait for the grace period, then remove the user if they haven't reconnected."""
    await asyncio.sleep(state.DISCONNECT_GRACE_SECONDS)
    room = state.get_room(room_code)
    if room is None:
        return
    user = room.users.get(client_id)
    if user is None:
        return
    if user.connect_epoch != expected_epoch:
        return
    state.handle_disconnect_timeout(room_code, client_id)


def _setup_room_listeners(room_code: str, room_content, client_id: str) -> None:
    """Register this client for real-time room updates; handle disconnect lifecycle."""
    client = ui.context.client
    connect_epoch = state.get_room(room_code).users[client_id].connect_epoch

    def on_update():
        with client:
            room_content.refresh()

    state.register_listener(room_code, on_update)

    def on_disconnect():
        state.unregister_listener(room_code, on_update)
        if state.process_disconnect(room_code, client_id, connect_epoch):
            asyncio.create_task(_delayed_disconnect_removal(room_code, client_id, connect_epoch))

    client.on_disconnect(on_disconnect)


def _make_room_handlers(room, client_id):
    """Create event handler callbacks for a room participant."""
    code = room.room_code

    def on_vote(card: str):
        state.submit_vote(room, client_id, card)
        state.check_and_auto_reveal(room)
        state.notify_room(code)

    def on_reveal():
        state.reveal_votes(room)
        state.notify_room(code)

    def on_reset():
        state.reset_round(room)
        state.notify_room(code)

    def on_toggle_observer():
        state.toggle_observer(room, client_id)
        state.check_and_auto_reveal(room)
        state.notify_room(code)

    return on_vote, on_reveal, on_reset, on_toggle_observer


def _make_topic_handlers(room, client_id):
    """Create event handler callbacks for the topic text area."""
    code = room.room_code

    def on_set_topic(text: str):
        state.set_topic(room, client_id, text)

    def on_topic_blur():
        state.notify_room(code)

    return on_set_topic, on_topic_blur


@ui.page('/room/{room_code}')
def room_page(room_code: str):
    room = state.get_room(room_code)
    if room is None:
        ui.label('Room not found.').classes('text-xl text-red-500 absolute-center')
        return

    client_id = _get_or_create_client_id()
    if client_id not in room.users:
        ui.navigate.to(f'/?room={room.room_code}')
        return

    state.reconnect_user(room, client_id)
    state.notify_room(room.room_code)

    on_vote, on_reveal, on_reset, on_toggle_observer = _make_room_handlers(room, client_id)
    on_set_topic, on_topic_blur = _make_topic_handlers(room, client_id)

    ui.query('body').classes('bg-gray-100')

    @ui.refreshable
    def room_content():
        user = room.users.get(client_id)
        if user is None:
            return

        with ui.column().classes('w-full max-w-2xl mx-auto p-4 gap-4'):
            render_header(room, user.is_moderator, on_reveal, on_reset)
            render_topic_area(room, user.is_moderator, on_set_topic, on_topic_blur)
            render_voting_cards(user.vote, user.is_observer, room.is_revealed, on_vote)

            if room.is_revealed:
                render_results_banner(state.calculate_average(room), state.vote_counts(room))

            render_observer_toggle(user.is_observer, on_toggle_observer)
            render_user_list(room)

    room_content()
    _setup_room_listeners(room.room_code, room_content, client_id)


ui.run(
    title='Planning Poker',
    port=5858,
    reload=True,
    reconnect_timeout=10.0,
    storage_secret=os.environ.get('STORAGE_SECRET', os.urandom(24).hex()),
    show=False,
)
