from nicegui import ui


def _validate_name(name_input: ui.input) -> bool:
    name_input.validate()
    return not name_input.error


async def _on_create_room(name_input: ui.input):
    if not _validate_name(name_input):
        return
    ui.notify(f'Creating room for {name_input.value.strip()}...', type='info')


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
    ui.notify(f'Joining room {room_code_input.value.upper()}...', type='info')


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


ui.run(title='Planning Poker', port=5858, reload=True)
