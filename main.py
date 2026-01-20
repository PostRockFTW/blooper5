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
_pending_new_project_after_save = False
_pending_file_path_to_load = None  # File to load after saving
_pending_load_after_save = False  # Flag to indicate load after save as


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
        on_save_as_project=on_save_as_project,
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
    dpg.create_viewport(title="Blooper5", width=1400, height=900)
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
    # Check for unsaved changes
    if app_state.is_dirty():
        _show_unsaved_new_project_dialog()
        return

    # No unsaved changes, proceed directly
    _create_new_project()


def _create_new_project():
    """Actually create the new project."""
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
    app_state.mark_clean()  # New project starts with no unsaved changes

    # Show DAW
    landing_page.set_active_project(True)
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)

    # Initialize Piano Roll with first track
    daw_view._on_track_selected(0, initial_load=True)


def _show_unsaved_new_project_dialog():
    """Show dialog for unsaved changes before creating new project."""
    dialog_tag = "unsaved_new_project_dialog"

    if not dpg.does_item_exist(dialog_tag):
        with dpg.window(
            label="Unsaved Changes",
            modal=True,
            show=False,
            tag=dialog_tag,
            pos=[400, 300],
            width=450,
            height=180,
            no_resize=True,
            no_collapse=True
        ):
            dpg.add_text("You have unsaved changes.")
            dpg.add_text("Do you want to save before creating a new project?")
            dpg.add_spacer(height=20)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Save",
                    width=120,
                    callback=lambda: _handle_new_project_save(dialog_tag)
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Don't Save",
                    width=120,
                    callback=lambda: _handle_new_project_dont_save(dialog_tag)
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Cancel",
                    width=120,
                    callback=lambda: dpg.hide_item(dialog_tag)
                )

    dpg.show_item(dialog_tag)


def _handle_new_project_save(dialog_tag: str):
    """Handle save button in new project unsaved changes dialog."""
    global _pending_new_project_after_save

    song = app_state.get_current_song()
    dpg.hide_item(dialog_tag)

    # If project has file_path, just save and continue
    if song and song.file_path:
        on_save_project()
        _create_new_project()
    else:
        # New project, need Save As dialog first
        # Set flag to create new project after save completes
        _pending_new_project_after_save = True
        on_save_as_project()


def _handle_new_project_dont_save(dialog_tag: str):
    """Handle don't save button in new project unsaved changes dialog."""
    app_state.mark_clean()
    dpg.hide_item(dialog_tag)
    _create_new_project()


def on_open_project(file_path: str):
    """Load an existing project and open DAW interface."""
    print(f"[OPEN PROJECT] Loading: {file_path}")

    # Check for unsaved changes
    if app_state.is_dirty():
        _show_unsaved_load_project_dialog(file_path)
        return

    # No unsaved changes, proceed with loading
    _do_open_project(file_path)


def _do_open_project(file_path: str):
    """Actually load the project (internal function)."""
    try:
        # Load song from file
        from dataclasses import replace as dataclass_replace
        song = ProjectFile.load(Path(file_path))

        # Set the file path on the song so saves know where to write
        song = dataclass_replace(song, file_path=str(file_path))

        app_state.set_current_song(song)
        app_state.set_selected_track(0)  # Select first track
        app_state.mark_clean()  # Clear dirty flag for newly loaded project

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


def _show_unsaved_load_project_dialog(file_path: str):
    """Show dialog for unsaved changes before loading project."""
    global _pending_file_path_to_load
    _pending_file_path_to_load = file_path

    dialog_tag = "unsaved_load_project_dialog"

    if not dpg.does_item_exist(dialog_tag):
        with dpg.window(
            label="Unsaved Changes",
            modal=True,
            show=False,
            tag=dialog_tag,
            pos=[400, 300],
            width=450,
            height=180,
            no_resize=True,
            no_collapse=True
        ):
            dpg.add_text("You have unsaved changes.")
            dpg.add_text("Do you want to save before loading?")
            dpg.add_spacer(height=20)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Save",
                    width=120,
                    callback=lambda: _handle_load_project_save(dialog_tag)
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Don't Save",
                    width=120,
                    callback=lambda: _handle_load_project_dont_save(dialog_tag)
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Cancel",
                    width=120,
                    callback=lambda: dpg.hide_item(dialog_tag)
                )

    dpg.show_item(dialog_tag)


def _handle_load_project_save(dialog_tag: str):
    """Handle save button in load project dialog."""
    global _pending_load_after_save

    song = app_state.get_current_song()
    dpg.hide_item(dialog_tag)

    if song and song.file_path:
        # Save existing project, then load new one
        on_save_project()
        _do_open_project(_pending_file_path_to_load)
    else:
        # New project needs Save As - show dialog and set flag to load after
        _pending_load_after_save = True
        on_save_as_project()


def _handle_load_project_dont_save(dialog_tag: str):
    """Handle don't save button in load project dialog."""
    app_state.mark_clean()
    dpg.hide_item(dialog_tag)
    _do_open_project(_pending_file_path_to_load)


def on_save_project(file_path: str = None):
    """
    Save current project to file.

    Args:
        file_path: Path to save to (None = use current path or prompt)
    """
    print(f"[SAVE] on_save_project called with file_path={file_path}")
    song = app_state.get_current_song()
    if not song:
        print("[ERROR] No active project to save")
        return
    print(f"[SAVE] Current song: {song.name}, file_path: {song.file_path}")

    # Save current piano roll notes to song (also updates current_song_id)
    daw_view._save_current_track_notes()

    # Get updated song after notes are saved
    song = app_state.get_current_song()
    from dataclasses import replace as dataclass_replace

    # Determine save path
    if file_path is None:
        if song.file_path:
            file_path = song.file_path
        else:
            # New project with no path - show Save As dialog
            print("[SAVE] New project, showing Save As dialog")
            _show_save_file_dialog()
            return  # Will be called again from dialog callback

    print(f"[SAVE] About to save to: {file_path}")
    try:
        # Save to file
        print(f"[SAVE] Calling ProjectFile.save()")
        ProjectFile.save(song, Path(file_path))

        # Update song with file path
        song = dataclass_replace(song, file_path=str(file_path))
        app_state.set_current_song(song)
        app_state.mark_clean()

        # Update DAWView's current_song_id to match the new song object
        daw_view.current_song_id = id(song)

        # Add to recent projects
        landing_page.add_recent_project(str(file_path))

        print(f"[SAVE] Project saved: {file_path}")

    except Exception as e:
        print(f"[ERROR] Failed to save project: {e}")
        # TODO: Show error dialog to user


def on_save_as_project():
    """Show file dialog and save project to chosen location."""
    song = app_state.get_current_song()
    if not song:
        print("[ERROR] No active project to save")
        return

    _show_save_file_dialog()


def _show_save_file_dialog():
    """Show file dialog for Save As operation."""
    if not dpg.does_item_exist("save_as_dialog"):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=_save_as_callback,
            tag="save_as_dialog",
            width=700,
            height=400,
            default_path=str(Path.home() / "Documents"),
            default_filename="Untitled.bloom5"
        ):
            dpg.add_file_extension(".bloom5", color=(0, 122, 204, 255))
            dpg.add_file_extension(".*")

    dpg.show_item("save_as_dialog")


def _save_as_callback(sender, app_data):
    """Handle save as file dialog selection."""
    global _pending_new_project_after_save, _pending_load_after_save

    print(f"[SAVE AS] Callback triggered, app_data: {app_data}")

    # Get file path from app_data (DearPyGui uses 'file_path_name')
    file_path = app_data.get('file_path_name')
    if not file_path:
        # User cancelled dialog
        print("[SAVE AS] No file path, user cancelled")
        _pending_new_project_after_save = False
        _pending_load_after_save = False
        return

    print(f"[SAVE AS] Selected file: {file_path}")
    on_save_project(file_path)

    # If there's a pending new project, create it now
    if _pending_new_project_after_save:
        _pending_new_project_after_save = False
        _create_new_project()

    # If there's a pending load, do it now
    if _pending_load_after_save:
        _pending_load_after_save = False
        _do_open_project(_pending_file_path_to_load)


def on_load_project(file_path: str):
    """
    Load project from file (called from within DAW).

    Args:
        file_path: Path to project file
    """
    # Same as on_open_project but doesn't change window visibility
    try:
        from dataclasses import replace as dataclass_replace
        song = ProjectFile.load(Path(file_path))

        # Set the file path on the song so saves know where to write
        song = dataclass_replace(song, file_path=str(file_path))

        app_state.set_current_song(song)
        app_state.set_selected_track(0)
        app_state.mark_clean()  # Clear dirty flag for newly loaded project

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
