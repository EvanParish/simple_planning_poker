"""Reusable NiceGUI UI components.

Components:
- render_theme_toggle: Dark/light mode toggle button
- render_header: Room code display + copy link + moderator controls
- render_topic_area: Editable topic for moderator, read-only for others
- render_voting_cards: Card selection buttons
- render_observer_toggle: Observer mode checkbox
- render_user_list: Vertical list of participants with vote status
- render_results_banner: Average + vote distribution when revealed
"""

from collections.abc import Callable

from nicegui import app, ui

from models import Room, User
from state import CARDS, TIMER_PRESETS, format_topic_html


def _vote_status(user: User, is_revealed: bool) -> tuple[str, str]:
    """Returns (label, color) describing a user's current vote status."""
    if not user.is_connected:
        return ('Reconnecting...', 'orange')
    if user.is_observer:
        return ('Observer', 'grey')
    if not user.vote:
        return ('Thinking...', 'grey')
    if is_revealed:
        return (user.vote, 'primary')
    return ('✓ Voted', 'green')


def render_theme_toggle() -> None:
    dark = ui.dark_mode(app.storage.user.get('dark_mode', False))
    icon = 'light_mode' if dark.value else 'dark_mode'

    def toggle():
        dark.toggle()
        app.storage.user['dark_mode'] = dark.value
        btn._props['icon'] = 'light_mode' if dark.value else 'dark_mode'
        btn.update()

    with ui.element('div').classes('fixed top-4 right-4 z-50'):
        btn = ui.button(icon=icon, on_click=toggle).props('flat round size=sm').tooltip('Toggle dark mode')


def render_header(room: Room, is_moderator: bool, on_reveal: Callable, on_reset: Callable) -> None:
    with ui.row().classes('w-full items-center justify-between'):
        with ui.row().classes('items-center gap-2'):
            ui.button(
                icon='home',
                on_click=lambda: ui.navigate.to('/'),
            ).props('flat round size=sm').tooltip('Back to home')
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


def render_topic_area(room: Room, is_moderator: bool, on_set_topic: Callable, on_topic_blur: Callable) -> None:
    if is_moderator:
        textarea = (
            ui.textarea(
                label='Current Topic',
                placeholder='Describe the issue being estimated...',
                value=room.current_topic,
                on_change=lambda e: on_set_topic(e.value),
            )
            .classes('w-full')
            .props('outlined autogrow debounce=300 clearable')
        )
        textarea.on('blur', on_topic_blur)
    elif room.current_topic:
        with ui.card().classes('w-full p-3'):
            ui.html(format_topic_html(room.current_topic))


def render_user_row(user: User, is_revealed: bool) -> None:
    label, color = _vote_status(user, is_revealed)
    with ui.card().tight().classes('w-full'):
        with ui.row().classes('w-full items-center p-3'):
            ui.label(user.name).classes('text-base font-medium flex-1')
            if user.is_moderator:
                ui.badge('Mod', color='blue').props('outline')
            ui.badge(label, color=color).classes('text-base px-3 py-1')


def render_user_list(room: Room) -> None:
    sorted_users = sorted(room.users.values(), key=lambda u: u.joined_at)
    with ui.column().classes('w-full gap-2'):
        for user in sorted_users:
            render_user_row(user, room.is_revealed)


def render_results_banner(average: float | None, counts: list[tuple[str, int]]) -> None:
    with ui.card().classes('w-full p-4 results-card'):
        if average is not None:
            ui.label(f'Average: {average:.1f}').classes('text-xl font-bold text-center w-full')
        else:
            ui.label('No numeric votes').classes('text-center text-gray-500 w-full')
        if counts:
            with ui.row().classes('w-full justify-center gap-3 mt-2'):
                for card, count in counts:
                    ui.badge(f'{card} × {count}', color='primary').props('outline').classes('text-base px-3 py-1')


def render_voting_cards(selected_card: str | None, is_observer: bool, is_revealed: bool, on_vote: Callable) -> None:
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


def render_observer_toggle(is_observer: bool, on_toggle_observer: Callable) -> None:
    ui.checkbox('Observer Mode', value=is_observer, on_change=on_toggle_observer)


# --- Web Audio API sound helpers ---

_JS_PLAY_START_SOUND = """
(() => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const gain = ctx.createGain();
    gain.gain.value = 0.15;
    gain.connect(ctx.destination);
    const o1 = ctx.createOscillator();
    o1.type = 'sine';
    o1.frequency.value = 440;
    o1.connect(gain);
    o1.start(ctx.currentTime);
    o1.stop(ctx.currentTime + 0.1);
    const o2 = ctx.createOscillator();
    o2.type = 'sine';
    o2.frequency.value = 660;
    o2.connect(gain);
    o2.start(ctx.currentTime + 0.1);
    o2.stop(ctx.currentTime + 0.2);
})();
"""

_JS_PLAY_FINISH_SOUND = """
(() => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const gain = ctx.createGain();
    gain.gain.value = 0.15;
    gain.connect(ctx.destination);
    const freqs = [880, 660, 440];
    freqs.forEach((f, i) => {
        const o = ctx.createOscillator();
        o.type = 'sine';
        o.frequency.value = f;
        o.connect(gain);
        o.start(ctx.currentTime + i * 0.15);
        o.stop(ctx.currentTime + (i + 1) * 0.15);
    });
})();
"""


def _format_duration(seconds: int) -> str:
    """Format seconds as a human-readable duration label."""
    if seconds >= 60 and seconds % 60 == 0:
        return f'{seconds // 60}m'
    return f'{seconds}s'


def _js_countdown_script(timer_end: float) -> str:
    """Generate JavaScript for a live countdown display."""
    return f"""
    (() => {{
        const timerEnd = {timer_end};
        window._pokerTimerEnd = timerEnd;
        const el = document.getElementById('timer-countdown');
        if (!el) return;
        let finished = false;
        function update() {{
            if (window._pokerTimerEnd !== timerEnd) return;
            const remaining = Math.max(0, Math.ceil(timerEnd - Date.now() / 1000));
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            el.textContent = mins + ':' + String(secs).padStart(2, '0');
            if (remaining <= 0 && !finished) {{
                finished = true;
                {_JS_PLAY_FINISH_SOUND}
            }}
            if (remaining > 0) {{
                setTimeout(update, 250);
            }}
        }}
        update();
    }})();
    """


def render_timer_controls(
    room: Room,
    is_moderator: bool,
    on_start_timer: Callable,
    on_cancel_timer: Callable,
) -> None:
    """Render timer controls for the moderator and countdown for all users."""
    has_active_timer = room.timer_end is not None and not room.is_revealed

    if has_active_timer:
        with ui.row().classes('w-full items-center justify-center gap-3'):
            ui.icon('timer', size='sm', color='primary')
            ui.label().classes('text-xl font-mono font-bold').props('id=timer-countdown')
            if is_moderator:
                ui.button(icon='close', on_click=on_cancel_timer, color='negative').props('flat round size=sm').tooltip(
                    'Cancel timer'
                )
        ui.run_javascript(_js_countdown_script(room.timer_end))
    else:
        ui.run_javascript('window._pokerTimerEnd = null;')
        if is_moderator and not room.is_revealed:
            with ui.row().classes('w-full items-center justify-center gap-2 flex-wrap'):
                for preset in TIMER_PRESETS:
                    ui.button(
                        _format_duration(preset),
                        icon='timer',
                        on_click=lambda p=preset: on_start_timer(p),
                    ).props('outline').classes('text-base')
                custom_input = ui.number(label='Custom (s)', min=1, max=3600, step=1, value=90).props(
                    'dense outlined style="max-width: 120px"'
                )
                ui.button(
                    'Start',
                    icon='play_arrow',
                    on_click=lambda: on_start_timer(int(custom_input.value)) if custom_input.value else None,
                ).props('color=primary').classes('text-base')
