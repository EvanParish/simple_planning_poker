"""Reusable NiceGUI UI components.

Components:
- render_header: Room code display + copy link + moderator controls
- render_user_list: Vertical list of participants with vote status
- render_voting_bar: Card selection bar + observer toggle
- render_average_banner: Displayed when votes are revealed
"""

from collections.abc import Callable

from nicegui import ui

from models import Room, User
from state import CARDS


def _vote_status(user: User, is_revealed: bool) -> tuple[str, str]:
    """Returns (label, color) describing a user's current vote status."""
    if user.is_observer:
        return ('Observer', 'grey')
    if not user.vote:
        return ('Thinking...', 'grey')
    if is_revealed:
        return (user.vote, 'primary')
    return ('✓ Voted', 'green')


def render_header(room: Room, is_moderator: bool, on_reveal: Callable, on_reset: Callable) -> None:
    with ui.row().classes('w-full items-center justify-between'):
        with ui.row().classes('items-center gap-2'):
            ui.label(f'Room {room.room_code}').classes('text-2xl font-bold')
            ui.button(
                icon='content_copy',
                on_click=lambda: ui.run_javascript(
                    f'navigator.clipboard.writeText(window.location.origin + "/room/{room.room_code}")'
                ),
            ).props('flat round size=sm').tooltip('Copy invite link')

        if is_moderator:
            with ui.row().classes('gap-2'):
                if not room.is_revealed:
                    ui.button('Reveal Cards', icon='visibility', on_click=on_reveal, color='primary')
                else:
                    ui.button('Reset Round', icon='refresh', on_click=on_reset, color='secondary')


def render_user_row(user: User, is_revealed: bool) -> None:
    label, color = _vote_status(user, is_revealed)
    with ui.row().classes('w-full items-center p-3 rounded-lg bg-white shadow-sm'):
        ui.label(user.name).classes('font-medium flex-1')
        if user.is_moderator:
            ui.badge('Mod', color='blue').props('outline')
        ui.badge(label, color=color)


def render_user_list(room: Room) -> None:
    sorted_users = sorted(room.active_users(), key=lambda u: u.joined_at)
    with ui.column().classes('w-full gap-2'):
        for user in sorted_users:
            render_user_row(user, room.is_revealed)


def render_average_banner(average: float | None) -> None:
    with ui.card().classes('w-full p-4 bg-blue-50'):
        if average is not None:
            ui.label(f'Average: {average:.1f}').classes('text-xl font-bold text-center w-full')
        else:
            ui.label('No numeric votes').classes('text-center text-gray-500 w-full')


def render_voting_bar(
    selected_card: str | None, is_observer: bool, is_revealed: bool, on_vote: Callable, on_toggle_observer: Callable
) -> None:
    disabled = is_observer or is_revealed
    with ui.row().classes('w-full justify-center gap-1 flex-wrap'):
        for card in CARDS:
            is_selected = card == selected_card
            btn = ui.button(card, on_click=lambda c=card: on_vote(c))
            btn.classes('min-w-[3rem]')
            if is_selected:
                btn.props('color=primary')
            else:
                btn.props('outline color=grey')
            if disabled:
                btn.props('disable')

    ui.switch('Observer Mode', value=is_observer, on_change=on_toggle_observer).classes('mt-2')
