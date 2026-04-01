import os
import uuid

from dotenv import load_dotenv
from nicegui import app, ui  # noqa: E402

import state  # noqa: E402

load_dotenv()

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

    ui.navigate.to(f'/room/{room.room_code}')


@ui.page('/')
def landing_page():
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
            validation={'Must be 6 alphanumeric characters': lambda v: not v or (len(v) == 6 and v.isalnum())},
        ).classes('w-full')

        with ui.row().classes('w-full mt-4 gap-2'):
            ui.button('Create Room', on_click=lambda: _on_create_room(name_input), color='primary').classes('flex-1')
            ui.button(
                'Join Room', on_click=lambda: _on_join_room(name_input, room_code_input), color='secondary'
            ).classes('flex-1')


@ui.page('/room/{room_code}')
def room_page(room_code: str):
    room = state.get_room(room_code)
    if room is None:
        ui.label('Room not found.').classes('text-xl text-red-500 absolute-center')
        return

    client_id = _get_or_create_client_id()
    user = room.users.get(client_id)

    ui.query('body').classes('bg-gray-100')

    with ui.column().classes('w-full max-w-2xl mx-auto p-4'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label(f'Room {room.room_code}').classes('text-2xl font-bold')
            ui.button(
                icon='content_copy',
                on_click=lambda: ui.clipboard.write(
                    f'{ui.run_javascript("window.location.origin")}/room/{room.room_code}'
                ),
            ).props('flat round').tooltip('Copy invite link')

        if user:
            ui.label(f'Welcome, {user.name}!').classes('text-lg text-gray-600')
            if user.is_moderator:
                ui.badge('Moderator', color='primary').classes('mt-1')
        else:
            ui.label('You are not in this room.').classes('text-gray-500')
            ui.button('Go Home', on_click=lambda: ui.navigate.to('/')).classes('mt-2')

        ui.label('Voting UI coming in Phase 3...').classes('text-gray-400 mt-8 text-center w-full')


ui.run(
    title='Planning Poker',
    port=5858,
    reload=True,
    storage_secret=os.environ.get('STORAGE_SECRET', os.urandom(24).hex()),
    show=False,
)
