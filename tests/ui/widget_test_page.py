"""
Widget Test Page for Blooper5.
Showcases all UI widgets with VS Code dark mode theme for visual testing.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dearpygui.dearpygui as dpg
from ui.theme import apply_vscode_theme, create_accent_button_theme, create_success_button_theme, create_error_button_theme


def create_widget_showcase():
    """
    Creates a comprehensive widget showcase for visual testing.
    Tests form, fit, and function of all UI elements.
    """

    # Create main window
    with dpg.window(label="Blooper5 Widget Test Page",
                    width=1000, height=800,
                    pos=(50, 50),
                    tag="primary_window"):

        dpg.add_text("Blooper5 - UI Widget Test Page", color=(0, 122, 204, 255))
        dpg.add_text("VS Code Dark Mode Theme", color=(150, 150, 150, 255))
        dpg.add_separator()

        # ===== SECTION 1: BUTTONS =====
        with dpg.collapsing_header(label="Buttons", default_open=True):
            dpg.add_text("Standard Buttons:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Normal Button", callback=lambda: print("Normal clicked"))
                dpg.add_button(label="Disabled", enabled=False)
                dpg.add_button(label="Small", small=True, callback=lambda: print("Small clicked"))

            dpg.add_spacer(height=10)
            dpg.add_text("Themed Buttons:")
            with dpg.group(horizontal=True):
                accent_btn = dpg.add_button(label="Accent Button", callback=lambda: print("Accent clicked"))
                dpg.bind_item_theme(accent_btn, create_accent_button_theme())

                success_btn = dpg.add_button(label="▶ Play", callback=lambda: print("Play clicked"))
                dpg.bind_item_theme(success_btn, create_success_button_theme())

                error_btn = dpg.add_button(label="⏹ Stop", callback=lambda: print("Stop clicked"))
                dpg.bind_item_theme(error_btn, create_error_button_theme())

        dpg.add_spacer(height=5)

        # ===== SECTION 2: SLIDERS =====
        with dpg.collapsing_header(label="Sliders", default_open=True):
            dpg.add_text("Float Sliders:")
            dpg.add_slider_float(label="Volume", default_value=0.7, min_value=0.0, max_value=1.0,
                                callback=lambda s, v: print(f"Volume: {v:.2f}"))
            dpg.add_slider_float(label="Pan", default_value=0.0, min_value=-1.0, max_value=1.0,
                                callback=lambda s, v: print(f"Pan: {v:.2f}"))

            dpg.add_spacer(height=10)
            dpg.add_text("Integer Slider:")
            dpg.add_slider_int(label="Cutoff (Hz)", default_value=1000, min_value=20, max_value=20000,
                              callback=lambda s, v: print(f"Cutoff: {v} Hz"))

            dpg.add_spacer(height=10)
            dpg.add_text("Vertical Slider:")
            with dpg.group(horizontal=True):
                dpg.add_slider_float(label="", default_value=0.5, min_value=0.0, max_value=1.0,
                                    vertical=True, height=100,
                                    callback=lambda s, v: print(f"Vertical: {v:.2f}"))
                dpg.add_text("   Vertical fader example")

        dpg.add_spacer(height=5)

        # ===== SECTION 3: INPUT FIELDS =====
        with dpg.collapsing_header(label="Input Fields", default_open=True):
            dpg.add_text("Text Input:")
            dpg.add_input_text(label="Project Name", default_value="My Project",
                              callback=lambda s, v: print(f"Project name: {v}"))

            dpg.add_spacer(height=10)
            dpg.add_text("Numeric Input:")
            dpg.add_input_int(label="BPM", default_value=120, min_value=30, max_value=300,
                             callback=lambda s, v: print(f"BPM: {v}"))
            dpg.add_input_float(label="Frequency", default_value=440.0, min_value=20.0, max_value=20000.0,
                               callback=lambda s, v: print(f"Frequency: {v:.1f} Hz"))

        dpg.add_spacer(height=5)

        # ===== SECTION 4: COMBO/DROPDOWN =====
        with dpg.collapsing_header(label="Dropdowns & Combos", default_open=True):
            dpg.add_text("Combo Box (Dropdown):")
            dpg.add_combo(label="Waveform",
                         items=["SINE", "SAW", "SQUARE", "TRIANGLE"],
                         default_value="SAW",
                         callback=lambda s, v: print(f"Waveform: {v}"))

            dpg.add_spacer(height=10)
            dpg.add_text("Listbox:")
            dpg.add_listbox(label="MIDI Device",
                           items=["Device 1", "Device 2", "Device 3", "None"],
                           default_value="None",
                           num_items=3,
                           callback=lambda s, v: print(f"MIDI Device: {v}"))

        dpg.add_spacer(height=5)

        # ===== SECTION 5: CHECKBOXES & RADIO =====
        with dpg.collapsing_header(label="Checkboxes & Radio Buttons", default_open=True):
            dpg.add_text("Checkboxes:")
            dpg.add_checkbox(label="Enable Reverb", default_value=True,
                            callback=lambda s, v: print(f"Reverb: {v}"))
            dpg.add_checkbox(label="Enable Delay", default_value=False,
                            callback=lambda s, v: print(f"Delay: {v}"))
            dpg.add_checkbox(label="Enable EQ", default_value=True,
                            callback=lambda s, v: print(f"EQ: {v}"))

            dpg.add_spacer(height=10)
            dpg.add_text("Radio Buttons:")
            dpg.add_radio_button(items=["Mono", "Stereo", "Surround"],
                                default_value="Stereo",
                                callback=lambda s, v: print(f"Output: {v}"))

        dpg.add_spacer(height=5)

        # ===== SECTION 6: TABS =====
        with dpg.collapsing_header(label="Tabs", default_open=True):
            with dpg.tab_bar():
                with dpg.tab(label="Track 1"):
                    dpg.add_text("Content for Track 1")
                    dpg.add_slider_float(label="Volume", default_value=0.8, max_value=1.0)

                with dpg.tab(label="Track 2"):
                    dpg.add_text("Content for Track 2")
                    dpg.add_slider_float(label="Volume", default_value=0.6, max_value=1.0)

                with dpg.tab(label="Master"):
                    dpg.add_text("Master track settings")
                    dpg.add_slider_float(label="Master Volume", default_value=1.0, max_value=1.0)

        dpg.add_spacer(height=5)

        # ===== SECTION 7: PROGRESS & STATUS =====
        with dpg.collapsing_header(label="Progress & Status", default_open=True):
            dpg.add_text("Progress Bar:")
            dpg.add_progress_bar(default_value=0.65, overlay="65%", width=300)

            dpg.add_spacer(height=10)
            dpg.add_text("Loading Indicator:")
            dpg.add_loading_indicator(style=1, radius=2.0)

        dpg.add_spacer(height=5)

        # ===== SECTION 8: COLOR PICKER =====
        with dpg.collapsing_header(label="Color Picker", default_open=True):
            dpg.add_text("Color Picker with Palette (for track colors):")

            # Full color picker with visual palette selector and numeric inputs
            dpg.add_color_picker(default_value=(0, 122, 204, 255),
                                label="Track Color",
                                no_side_preview=False,
                                alpha_bar=True,
                                width=250,
                                callback=lambda s, v: print(f"Color RGBA: {v}"))

            dpg.add_spacer(height=10)
            dpg.add_text("Compact Color Editor with Inputs:")

            # Compact version with numeric sliders
            dpg.add_color_edit(default_value=(220, 80, 80, 255),
                              label="Error Color",
                              no_picker=False,
                              alpha_bar=True,
                              input_mode=dpg.mvColorEdit_input_rgb,
                              callback=lambda s, v: print(f"Error Color: {v}"))

        dpg.add_spacer(height=5)

        # ===== SECTION 9: PLOTS =====
        with dpg.collapsing_header(label="Plots (for waveforms)", default_open=False):
            dpg.add_text("Line Plot (waveform preview):")
            import math
            # Generate sample waveform data
            x_data = [i/100 for i in range(100)]
            y_data = [math.sin(i/100 * 2 * math.pi * 2) for i in range(100)]

            with dpg.plot(label="Waveform", height=200, width=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label="Time")
                dpg.add_plot_axis(dpg.mvYAxis, label="Amplitude", tag="y_axis")
                dpg.add_line_series(x_data, y_data, label="Sine Wave", parent="y_axis")

        dpg.add_spacer(height=10)

        # ===== FOOTER =====
        dpg.add_separator()
        dpg.add_text("Widget Test Page - All interactions logged to console",
                    color=(150, 150, 150, 255))


def main():
    """Main entry point for widget test page."""

    # Initialize DearPyGui
    dpg.create_context()

    # Apply VS Code dark theme
    apply_vscode_theme()

    # Create widget showcase
    create_widget_showcase()

    # Setup viewport
    dpg.create_viewport(title="Blooper5 - Widget Test Page",
                       width=1100, height=900)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Set primary window
    dpg.set_primary_window("primary_window", True)

    # Main render loop
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

    # Cleanup
    dpg.destroy_context()


if __name__ == "__main__":
    print("=== Blooper5 Widget Test Page ===")
    print("Testing UI widgets with VS Code dark mode theme")
    print("All widget interactions will be logged below:")
    print("-" * 50)
    main()
