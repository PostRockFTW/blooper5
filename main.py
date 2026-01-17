"""
Blooper5 - Digital Audio Workstation
Main entry point
"""
import dearpygui.dearpygui as dpg
from pathlib import Path
from ui.theme import apply_vscode_theme, apply_ui_scale
from ui.views.LandingPage import LandingPage
from ui.views.SettingsPage import SettingsPage
from ui.views.DAWView import DAWView
from core.models import Song, Track, AppState, Note
from core.persistence import ProjectFile


# Module-level variables (accessed by callbacks)
landing_page = None
settings_page = None
daw_view = None
app_state = None


def main():
    """Launch Blooper5 DAW."""
    global landing_page, settings_page, daw_view, app_state

    print("=== Blooper5 DAW ===")
    print("Initializing...")

    # Initialize DearPyGui
    dpg.create_context()

    # Create app state
    app_state = AppState()

    # Create settings page first (it loads settings)
    settings_page = SettingsPage(on_close=on_settings_close)

    # Apply UI scale from settings
    ui_scale = settings_page.settings.get("video", {}).get("ui_scale", 1.0)
    print(f"Applying UI scale: {ui_scale}x")
    apply_ui_scale(ui_scale)

    # Create landing page
    landing_page = LandingPage(
        on_new_project=on_new_project,
        on_open_project=on_open_project,
        on_return_to_project=on_return_to_project,
        on_save_project=on_save_project,
        on_settings=on_settings,
        on_exit=on_exit
    )

    # Create DAW view
    daw_view = DAWView(
        on_return_to_landing=on_return_to_landing,
        app_state=app_state,
        on_save_project=on_save_project,
        on_load_project=on_load_project,
        on_new_project=on_new_project
    )

    # Create windows
    window_tag = landing_page.create()
    settings_page.create()
    daw_view.create()

    # Hide settings and DAW initially
    settings_page.hide()
    daw_view.hide()

    # Apply VS Code theme
    apply_vscode_theme()

    # Setup viewport
    dpg.create_viewport(title="Blooper5", width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Set landing page as primary window
    dpg.set_primary_window(window_tag, True)

    print("Ready!")

    # Main render loop
    while dpg.is_dearpygui_running():
        # Update settings page (handles key capture if in binding mode)
        settings_page.update()

        # Update DAW view (handles splitter dragging)
        daw_view.update()

        dpg.render_dearpygui_frame()

        # 'H' key returns to landing page from DAW (hamburger simulation)
        if hasattr(dpg, "mvKey_H") and dpg.is_key_pressed(dpg.mvKey_H):
            if dpg.is_item_visible(daw_view._window_tag):
                on_return_to_landing()

        # Ctrl+S saves project
        if dpg.is_key_down(dpg.mvKey_Control) and dpg.is_key_pressed(dpg.mvKey_S):
            if dpg.is_item_visible(daw_view._window_tag):
                on_save_project()

    # Cleanup
    dpg.destroy_context()
    print("Blooper5 closed.")


def on_new_project():
    """Create a new project and open DAW interface."""
    print("[NEW PROJECT] Opening DAW interface")

    # Create new empty song with 16 tracks
    tracks = tuple(Track(name=f"Track {i+1}") for i in range(16))
    new_song = Song(
        name="Untitled",
        bpm=120.0,
        time_signature=(4, 4),
        tpqn=480,
        tracks=tracks
    )
    app_state.set_current_song(new_song)
    app_state.set_selected_track(0)  # Select first track

    # Show DAW
    landing_page.set_active_project(True)
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)

    # Initialize Piano Roll with first track
    daw_view._on_track_selected(0, initial_load=True)


def on_open_project(file_path: str):
    """Load an existing project and open DAW interface."""
    print(f"[OPEN PROJECT] Loading: {file_path}")

    try:
        # Load song from file
        song = ProjectFile.load(Path(file_path))
        app_state.set_current_song(song)
        app_state.set_selected_track(0)  # Select first track

        # Show DAW (do window transitions first)
        landing_page.set_active_project(True)
        landing_page.hide()
        daw_view.show()
        dpg.set_primary_window(daw_view._window_tag, True)

        # Load first track into Piano Roll
        daw_view._on_track_selected(0, initial_load=True)

        # Add to recent projects AFTER DAW is fully initialized
        landing_page.add_recent_project(str(file_path))

        print(f"[OPEN PROJECT] Loaded: {song.name}")

    except Exception as e:
        print(f"[ERROR] Failed to load project: {e}")
        # TODO: Show error dialog to user


def on_save_project(file_path: str = None):
    """
    Save current project to file.

    Args:
        file_path: Path to save to (None = use current path or prompt)
    """
    song = app_state.get_current_song()
    if not song:
        print("[ERROR] No active project to save")
        return

    # Get notes from Piano Roll and update selected track
    selected_track_index = app_state.get_selected_track()
    if selected_track_index is not None:
        piano_roll_notes = tuple(daw_view.piano_roll.get_notes())
        old_track = song.tracks[selected_track_index]

        # Create new track with updated notes (Track is immutable)
        from dataclasses import replace as dataclass_replace
        new_track = dataclass_replace(old_track, notes=piano_roll_notes)

        # Create new song with updated track (Song is immutable)
        new_tracks = list(song.tracks)
        new_tracks[selected_track_index] = new_track
        song = dataclass_replace(song, tracks=tuple(new_tracks))

        app_state.set_current_song(song)

    # Determine save path
    if file_path is None:
        if song.file_path:
            file_path = song.file_path
        else:
            # TODO: Show file dialog to get path
            file_path = Path.home() / "Documents" / f"{song.name}.bloom5"
            print(f"[SAVE] No path specified, saving to: {file_path}")

    try:
        # Save to file
        ProjectFile.save(song, Path(file_path))

        # Update song with file path
        song = dataclass_replace(song, file_path=str(file_path))
        app_state.set_current_song(song)
        app_state.mark_clean()

        # Add to recent projects
        landing_page.add_recent_project(str(file_path))

        print(f"[SAVE] Project saved: {file_path}")

    except Exception as e:
        print(f"[ERROR] Failed to save project: {e}")
        # TODO: Show error dialog to user


def on_load_project(file_path: str):
    """
    Load project from file (called from within DAW).

    Args:
        file_path: Path to project file
    """
    # Same as on_open_project but doesn't change window visibility
    try:
        song = ProjectFile.load(Path(file_path))
        app_state.set_current_song(song)
        app_state.set_selected_track(0)

        # Load first track into Piano Roll with proper colors
        daw_view._on_track_selected(0)

        # Add to recent projects AFTER Piano Roll is loaded
        landing_page.add_recent_project(str(file_path))

        print(f"[LOAD] Project loaded: {song.name}")

    except Exception as e:
        print(f"[ERROR] Failed to load project: {e}")
        # TODO: Show error dialog to user


def on_return_to_project():
    """Return to active DAW project from landing page."""
    print("[RETURN TO PROJECT] Returning to DAW")
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)


def on_return_to_landing():
    """Return to landing page from DAW (hamburger button)."""
    print("[RETURN TO LANDING] Showing landing page")

    # Save current Piano Roll notes to app_state before switching views
    daw_view._save_current_track_notes()

    daw_view.hide()
    landing_page.show()
    dpg.set_primary_window(landing_page._window_tag, True)


def on_settings():
    """Open settings dialog."""
    print("[SETTINGS] Opening settings")
    landing_page.hide()
    settings_page.show()
    dpg.set_primary_window(settings_page._window_tag, True)


def on_settings_close():
    """Close settings dialog and return to landing page."""
    print("[SETTINGS] Closing settings")
    settings_page.hide()
    landing_page.show()
    dpg.set_primary_window(landing_page._window_tag, True)


def on_exit():
    """Exit application."""
    print("[EXIT] Closing Blooper5")
    dpg.stop_dearpygui()


if __name__ == "__main__":
    main()
