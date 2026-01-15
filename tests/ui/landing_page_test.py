"""
Landing Page Test for Blooper5.
Demonstrates the landing page functionality.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dearpygui.dearpygui as dpg
from ui.theme import apply_vscode_theme, apply_ui_scale
from ui.views.LandingPage import LandingPage
from ui.views.SettingsPage import SettingsPage
from pathlib import Path
import json


def on_new_project():
    """Callback for New Project button."""
    print("=== NEW PROJECT CLICKED ===")
    print("Would navigate to empty DAW interface")
    # In real app: create new project state, navigate to main view
    landing_page.set_active_project(True)
    landing_page.hide()
    print("Landing page hidden. Press hamburger (or close window) to return.")


def on_open_project(file_path: str):
    """Callback for Open Project button."""
    print(f"=== OPEN PROJECT CLICKED ===")
    print(f"Would load project from: {file_path}")
    # In real app: load project from file, navigate to main view
    landing_page.set_active_project(True)
    landing_page.hide()
    print("Landing page hidden. Press hamburger (or close window) to return.")


def on_return_to_project():
    """Callback for Return to Project button."""
    print("=== RETURN TO PROJECT CLICKED ===")
    print("Would navigate back to active project")
    landing_page.hide()


def on_settings():
    """Callback for Settings button."""
    print("=== SETTINGS CLICKED ===")
    landing_page.hide()
    settings_page.show()
    dpg.set_primary_window(settings_page._window_tag, True)


def on_settings_close():
    """Callback when settings page is closed."""
    print("=== SETTINGS CLOSED ===")
    settings_page.hide()
    landing_page.show()
    dpg.set_primary_window(landing_page._window_tag, True)


def on_exit():
    """Callback for Exit button."""
    print("=== EXIT CLICKED ===")
    print("Would close application")
    dpg.stop_dearpygui()


def main():
    """Main entry point for landing page test."""
    global landing_page, settings_page

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

    # Create landing page window
    window_tag = landing_page.create()

    # Create settings page window and hide it initially
    settings_page.create()
    settings_page.hide()

    # Setup viewport
    dpg.create_viewport(title="Blooper5",
                       width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Set landing page as primary window initially
    dpg.set_primary_window(window_tag, True)

    # Main render loop
    while dpg.is_dearpygui_running():
        # Capture keystrokes for key binding configuration
        settings_page._capture_keystroke()

        dpg.render_dearpygui_frame()

        # Simulate hamburger button: pressing 'H' key shows landing page
        if dpg.is_key_pressed(dpg.mvKey_H):
            landing_page.show()
            print("(Hamburger pressed - showing landing page)")

    # Cleanup
    dpg.destroy_context()


if __name__ == "__main__":
    print("=== Blooper5 Landing Page Test ===")
    print("Controls:")
    print("  - Click 'New Project' or 'Open Project' to simulate navigation")
    print("  - Press 'H' key to simulate hamburger button (return to landing page)")
    print("  - Click 'Return to Project' to hide landing page again")
    print("-" * 50)
    main()
