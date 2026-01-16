"""
Settings Page Test for Blooper5.
Demonstrates the settings page functionality.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dearpygui.dearpygui as dpg
from ui.theme import apply_vscode_theme, apply_ui_scale
from ui.views.SettingsPage import SettingsPage


def on_close():
    """Callback when settings page is closed."""
    print("=== SETTINGS CLOSED ===")
    dpg.stop_dearpygui()


def main():
    """Main entry point for settings page test."""

    # Initialize DearPyGui
    dpg.create_context()

    # Create settings page (loads settings)
    settings_page = SettingsPage(on_close=on_close)

    # Apply UI scale from settings
    ui_scale = settings_page.settings.get("video", {}).get("ui_scale", 1.0)
    print(f"Applying UI scale: {ui_scale}x")
    apply_ui_scale(ui_scale)

    # Create settings page UI
    window_tag = settings_page.create()

    # Setup viewport
    dpg.create_viewport(title="Blooper5 - Settings",
                       width=900, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Set primary window
    dpg.set_primary_window(window_tag, True)

    # Main render loop
    while dpg.is_dearpygui_running():
        # Update settings page (handles key capture if in binding mode)
        settings_page.update()

        dpg.render_dearpygui_frame()

    # Cleanup
    dpg.destroy_context()


if __name__ == "__main__":
    print("=== Blooper5 Settings Page Test ===")
    print("Click different category buttons on the left to view settings")
    print("All changes are automatically saved to ~/.blooper5/settings.json")
    print("-" * 50)
    main()
