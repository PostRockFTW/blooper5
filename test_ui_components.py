"""
Test script to demo all three UI components.

Run this from your terminal or IDE to see the UI in action.
Choose which component to test with command line args.

Usage:
    python test_ui_components.py piano       # Test Piano Roll
    python test_ui_components.py drum        # Test Drum Roll
    python test_ui_components.py plugins     # Test Plugin Rack
    python test_ui_components.py all         # Test all components (separate windows)
"""

import sys
import dearpygui.dearpygui as dpg


def test_piano_roll():
    """Test the Piano Roll UI."""
    print("Loading Piano Roll...")
    from ui.views.PianoRoll import PianoRoll

    dpg.create_context()

    piano_roll = PianoRoll(width=1200, height=600)
    piano_roll.create_window()

    # Add some instructions
    with dpg.window(label="Instructions", pos=(10, 10), width=300, height=150):
        dpg.add_text("Piano Roll Demo", color=(255, 255, 100))
        dpg.add_separator()
        dpg.add_text("Features visible:")
        dpg.add_text("• Grid with beat/measure lines")
        dpg.add_text("• Mock notes with octave colors")
        dpg.add_text("• Velocity indicators (left edge)")
        dpg.add_text("• Zoom controls in toolbar")
        dpg.add_text("• Triplet grid subdivisions")

    dpg.create_viewport(title="Blooper5 - Piano Roll Demo", width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

    print("Piano Roll demo closed.")


def test_drum_roll():
    """Test the Drum Roll UI."""
    print("Loading Drum Roll...")
    from ui.views.DrumRoll import DrumRoll

    dpg.create_context()

    drum_roll = DrumRoll(width=1200, height=600)
    drum_roll.create_window()

    # Add instructions
    with dpg.window(label="Instructions", pos=(10, 10), width=300, height=180):
        dpg.add_text("Drum Roll Demo", color=(255, 255, 100))
        dpg.add_separator()
        dpg.add_text("Features visible:")
        dpg.add_text("• Alternating pad rows")
        dpg.add_text("• Drum hits as circles")
        dpg.add_text("• Mock 4/4 beat pattern:")
        dpg.add_text("  - Kick on 1 & 3")
        dpg.add_text("  - Snare on 2 & 4")
        dpg.add_text("  - Hi-hats on 8th notes")
        dpg.add_text("• Velocity affects size/brightness")

    dpg.create_viewport(title="Blooper5 - Drum Roll Demo", width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

    print("Drum Roll demo closed.")


def test_plugin_rack():
    """Test the Plugin Rack UI."""
    print("Loading Plugin Rack...")
    from ui.views.PluginRack import PluginRack

    dpg.create_context()

    rack = PluginRack(width=500, height=800)
    rack.create_window()

    # Pre-populate with some plugins for demo
    rack.add_source_plugin("DUAL_OSC")
    rack.add_effect_plugin("EQ")
    rack.add_effect_plugin("REVERB")
    rack.add_effect_plugin("DELAY")

    # Add instructions
    with dpg.window(label="Instructions", pos=(520, 10), width=350, height=250):
        dpg.add_text("Plugin Rack Demo", color=(255, 255, 100))
        dpg.add_separator()
        dpg.add_text("Features visible:")
        dpg.add_text("• Source plugin (Dual Osc)")
        dpg.add_text("• Effects chain (EQ → Reverb → Delay)")
        dpg.add_text("• Auto-generated parameter sliders")
        dpg.add_text("• Bypass/Enable toggles")
        dpg.add_text("• Move Up/Down buttons")
        dpg.add_text("• Remove button")
        dpg.add_text("• Add Effect dropdown")
        dpg.add_separator()
        dpg.add_text("Try:")
        dpg.add_text("• Adjust parameter sliders")
        dpg.add_text("• Bypass a plugin (grays out)")
        dpg.add_text("• Reorder plugins with arrows")
        dpg.add_text("• Add more effects from dropdown")

    dpg.create_viewport(title="Blooper5 - Plugin Rack Demo", width=900, height=850)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

    print("Plugin Rack demo closed.")


def test_all():
    """Run all three demos in sequence."""
    print("Testing all components...")
    print("\n=== 1/3: Piano Roll ===")
    test_piano_roll()
    print("\n=== 2/3: Drum Roll ===")
    test_drum_roll()
    print("\n=== 3/3: Plugin Rack ===")
    test_plugin_rack()
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nDefaulting to Piano Roll demo...")
        component = "piano"
    else:
        component = sys.argv[1].lower()

    try:
        if component == "piano":
            test_piano_roll()
        elif component == "drum":
            test_drum_roll()
        elif component == "plugins" or component == "rack":
            test_plugin_rack()
        elif component == "all":
            test_all()
        else:
            print(f"Unknown component: {component}")
            print(__doc__)
            sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\nMake sure you're running this from the blooper5 root directory:")
        print("  cd C:\\Users\\nick\\Documents\\Vibe Code Projects\\blooper5")
        print("  python test_ui_components.py piano")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
