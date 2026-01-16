"""
Blooper5 - Digital Audio Workstation
Main entry point
"""
import dearpygui.dearpygui as dpg
from ui.theme import apply_vscode_theme, apply_ui_scale
from ui.views.LandingPage import LandingPage
from ui.views.SettingsPage import SettingsPage
from ui.views.DAWView import DAWView


# Module-level variables (accessed by callbacks)
landing_page = None
settings_page = None
daw_view = None


def main():
    """Launch Blooper5 DAW."""
    global landing_page, settings_page, daw_view

    print("=== Blooper5 DAW ===")
    print("Initializing...")

    # Initialize DearPyGui
    dpg.create_context()

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
        on_settings=on_settings,
        on_exit=on_exit
    )

    # Create DAW view
    daw_view = DAWView(
        on_return_to_landing=on_return_to_landing,
        on_save_project=None,  # TODO: Implement save/load
        on_load_project=None
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

        dpg.render_dearpygui_frame()

        # 'H' key returns to landing page from DAW (hamburger simulation)
        if hasattr(dpg, "mvKey_H") and dpg.is_key_pressed(dpg.mvKey_H):
            if dpg.is_item_visible(daw_view._window_tag):
                on_return_to_landing()

    # Cleanup
    dpg.destroy_context()
    print("Blooper5 closed.")


def on_new_project():
    """Create a new project and open DAW interface."""
    print("[NEW PROJECT] Opening DAW interface")
    landing_page.set_active_project(True)
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)


def on_open_project(file_path: str):
    """Load an existing project and open DAW interface."""
    print(f"[OPEN PROJECT] Loading: {file_path}")
    # TODO: Implement project loading
    landing_page.set_active_project(True)
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)


def on_return_to_project():
    """Return to active DAW project from landing page."""
    print("[RETURN TO PROJECT] Returning to DAW")
    landing_page.hide()
    daw_view.show()
    dpg.set_primary_window(daw_view._window_tag, True)


def on_return_to_landing():
    """Return to landing page from DAW (hamburger button)."""
    print("[RETURN TO LANDING] Showing landing page")
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
