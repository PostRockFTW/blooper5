"""
Settings Page for Blooper5.
Two-column layout: category buttons on left, settings fields on right.
"""
import dearpygui.dearpygui as dpg
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import json
from ui.widgets.KeyBindingCapture import KeyBindingCapture


class SettingsPage:
    """
    Settings page view for Blooper5.

    Two-column layout:
    - Left: Category buttons (Video, Audio, MIDI, Key Bindings, General, Plugins)
    - Right: Settings fields for selected category
    """

    def __init__(self, on_close: Optional[Callable] = None):
        """
        Args:
            on_close: Callback when settings page is closed
        """
        self.on_close = on_close
        self.current_category = "General"
        self._window_tag = "settings_page_window"
        self._settings_content_tag = "settings_content_group"
        self.category_buttons = {}  # Track category button tags for highlighting

        # Key binding capture widget
        self.key_capture = KeyBindingCapture()

        # Default settings
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from config file."""
        config_path = Path.home() / ".blooper5" / "settings.json"

        # Default settings
        defaults = {
            "general": {
                "auto_save_enabled": True,  # NEW: toggle for auto-save
                "auto_save_interval": 300,  # seconds
                "undo_limit": 100,
                "default_bpm": 120,
                "default_tpqn": 480
            },
            "video": {
                "vsync": True,
                "ui_scale": 1.0  # NEW: UI scaling (0.5x - 2.0x)
            },
            "audio": {
                "sample_rate": 44100,
                "buffer_size": 512,
                "output_device": "Default",
                "input_device": "Default"
            },
            "midi": {
                "input_device": "None",
                "output_device": "None",
                "midi_clock_sync": False
            },
            "key_bindings": {
                "new_project": "Ctrl+N",
                "open_project": "Ctrl+O",
                "save_project": "Ctrl+S",
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Y",
                "play/pause": "Space",  # CHANGED: renamed from "play"
                "stop": "Escape"
            },
            "piano_roll": {
                "vertical_scroll_modifier": "none",
                "horizontal_scroll_modifier": "shift",
                "horizontal_zoom_modifier": "ctrl",
                "vertical_zoom_modifier": "ctrl+shift"
            },
            "plugins": {
                "vst_paths": [],
                "auto_scan": True
            }
        }

        settings_modified = False

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings added)
                    for category in defaults:
                        if category in loaded:
                            defaults[category].update(loaded[category])
                        elif category == "piano_roll":
                            # New category added, mark for save
                            settings_modified = True

                    # Migration: Remove old video settings
                    if "video" in loaded:
                        for old_key in ["window_width", "window_height", "fullscreen"]:
                            if old_key in defaults["video"]:
                                defaults["video"].pop(old_key, None)
                                settings_modified = True

                    # Migration: Rename "play" to "play/pause" in key_bindings
                    if "key_bindings" in loaded:
                        if "play" in loaded["key_bindings"] and "play/pause" not in loaded["key_bindings"]:
                            defaults["key_bindings"]["play/pause"] = loaded["key_bindings"]["play"]
                            defaults["key_bindings"].pop("play", None)
                            settings_modified = True

                    # Save back if new categories were added
                    if settings_modified:
                        try:
                            with open(config_path, 'w') as f:
                                json.dump(defaults, f, indent=2)
                            print("[SETTINGS] Saved new piano_roll settings to file")
                        except Exception as e:
                            print(f"Failed to save migrated settings: {e}")

                    return defaults
            except Exception as e:
                print(f"Failed to load settings: {e}")
                return defaults
        else:
            # No config file exists, save defaults
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(defaults, f, indent=2)
                print("[SETTINGS] Created new settings file with defaults")
            except Exception as e:
                print(f"Failed to save default settings: {e}")
            return defaults

    def _save_settings(self):
        """Save settings to config file."""
        config_path = Path.home() / ".blooper5" / "settings.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _switch_category(self, category: str):
        """Switch to a different settings category."""
        from ui.theme import create_accent_button_theme

        self.current_category = category

        # Update button highlighting
        accent_theme = create_accent_button_theme()
        for cat, btn_tag in self.category_buttons.items():
            if dpg.does_item_exist(btn_tag):
                if cat == category:
                    # Highlight selected category
                    dpg.bind_item_theme(btn_tag, accent_theme)
                else:
                    # Remove highlight from others
                    dpg.bind_item_theme(btn_tag, 0)  # 0 = default theme

        self._refresh_settings_content()

    def _refresh_settings_content(self):
        """Refresh the right panel with current category settings."""
        if dpg.does_item_exist(self._settings_content_tag):
            dpg.delete_item(self._settings_content_tag)

        # Create new settings content based on current category
        if self.current_category == "General":
            self._create_general_settings()
        elif self.current_category == "Video":
            self._create_video_settings()
        elif self.current_category == "Audio":
            self._create_audio_settings()
        elif self.current_category == "MIDI":
            self._create_midi_settings()
        elif self.current_category == "Piano Roll":
            self._create_piano_roll_settings()
        elif self.current_category == "Key Bindings":
            self._create_keybindings_settings()
        elif self.current_category == "Plugins":
            self._create_plugins_settings()

    def _create_general_settings(self):
        """Create General settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("GENERAL SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # Auto-save enabled toggle (NEW)
            def toggle_auto_save(sender, value):
                self._update_setting("general", "auto_save_enabled", value)
                # Enable/disable interval input
                dpg.configure_item("auto_save_interval_input", enabled=value)

            dpg.add_checkbox(
                label="Enable Auto-Save",
                default_value=self.settings["general"]["auto_save_enabled"],
                callback=toggle_auto_save
            )

            dpg.add_spacer(height=15)

            # Auto-save interval
            dpg.add_text("Auto-Save Interval (seconds):")
            dpg.add_input_int(
                default_value=self.settings["general"]["auto_save_interval"],
                width=200,
                callback=lambda s, v: self._update_setting("general", "auto_save_interval", v),
                tag="auto_save_interval_input",
                enabled=self.settings["general"]["auto_save_enabled"]
            )

            dpg.add_spacer(height=15)

            # Undo limit
            dpg.add_text("Undo History Limit:")
            dpg.add_input_int(
                default_value=self.settings["general"]["undo_limit"],
                width=200,
                callback=lambda s, v: self._update_setting("general", "undo_limit", v)
            )

            dpg.add_spacer(height=15)

            # Default BPM
            dpg.add_text("Default Project BPM:")
            dpg.add_input_int(
                default_value=self.settings["general"]["default_bpm"],
                min_value=30,
                max_value=300,
                width=200,
                callback=lambda s, v: self._update_setting("general", "default_bpm", v)
            )

            dpg.add_spacer(height=15)

            # Default TPQN
            dpg.add_text("Default TPQN (Ticks Per Quarter Note):")
            dpg.add_input_int(
                default_value=self.settings["general"]["default_tpqn"],
                min_value=96,
                max_value=960,
                width=200,
                callback=lambda s, v: self._update_setting("general", "default_tpqn", v)
            )

    def _create_video_settings(self):
        """Create Video settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("VIDEO SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # VSync
            dpg.add_checkbox(
                label="VSync (Vertical Sync) - Prevents screen tearing",
                default_value=self.settings["video"]["vsync"],
                callback=lambda s, v: self._update_setting("video", "vsync", v)
            )

            dpg.add_spacer(height=20)

            # UI Scale (NEW)
            dpg.add_text("UI Scale (for accessibility):")
            dpg.add_spacer(height=5)

            with dpg.group(horizontal=True):
                dpg.add_slider_float(
                    default_value=self.settings["video"]["ui_scale"],
                    min_value=0.5,
                    max_value=2.0,
                    width=250,
                    format="%.2fx",
                    callback=lambda s, v: self._update_setting("video", "ui_scale", v),
                    tag="ui_scale_slider"
                )

                dpg.add_spacer(width=10)
                dpg.add_text("(50% - 200%)", color=(150, 150, 150, 255))

            dpg.add_spacer(height=15)

            # Apply scale button
            with dpg.group(horizontal=True):
                apply_btn = dpg.add_button(
                    label="Apply Scale Now",
                    callback=self._apply_ui_scale_now,
                    width=150,
                    height=30
                )
                dpg.add_spacer(width=10)
                dpg.add_text("Click to apply scale without restarting", color=(150, 150, 150, 255))

    def _create_audio_settings(self):
        """Create Audio settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("AUDIO SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # Sample rate
            dpg.add_text("Sample Rate (Hz):")
            dpg.add_combo(
                items=["44100", "48000", "88200", "96000"],
                default_value=str(self.settings["audio"]["sample_rate"]),
                width=200,
                callback=lambda s, v: self._update_setting("audio", "sample_rate", int(v))
            )

            dpg.add_spacer(height=15)

            # Buffer size (slider + text input)
            dpg.add_text("Buffer Size (samples):")
            dpg.add_text("Lower = less latency, higher = more stability",
                        color=(150, 150, 150, 255))
            dpg.add_spacer(height=5)

            with dpg.group(horizontal=True):
                # Slider
                dpg.add_slider_int(
                    default_value=self.settings["audio"]["buffer_size"],
                    min_value=128,
                    max_value=2048,
                    width=250,
                    clamped=True,
                    callback=lambda s, v: self._update_buffer_size(v, sync_input=True),
                    tag="buffer_size_slider"
                )

                dpg.add_spacer(width=15)

                # Text input override
                dpg.add_input_int(
                    default_value=self.settings["audio"]["buffer_size"],
                    width=100,
                    min_value=64,
                    max_value=4096,
                    min_clamped=True,
                    max_clamped=True,
                    callback=lambda s, v: self._update_buffer_size(v, sync_slider=True),
                    tag="buffer_size_input"
                )

            dpg.add_spacer(height=15)

            # Output device
            dpg.add_text("Output Device:")
            dpg.add_combo(
                items=["Default", "Device 1", "Device 2"],  # TODO: Enumerate actual devices
                default_value=self.settings["audio"]["output_device"],
                width=300,
                callback=lambda s, v: self._update_setting("audio", "output_device", v)
            )

            dpg.add_spacer(height=15)

            # Input device
            dpg.add_text("Input Device:")
            dpg.add_combo(
                items=["Default", "Device 1", "Device 2"],  # TODO: Enumerate actual devices
                default_value=self.settings["audio"]["input_device"],
                width=300,
                callback=lambda s, v: self._update_setting("audio", "input_device", v)
            )

    def _create_midi_settings(self):
        """Create MIDI settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("MIDI SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # MIDI input
            dpg.add_text("MIDI Input Device:")
            dpg.add_combo(
                items=["None", "Device 1", "Device 2"],  # TODO: Enumerate actual devices
                default_value=self.settings["midi"]["input_device"],
                width=300,
                callback=lambda s, v: self._update_setting("midi", "input_device", v)
            )

            dpg.add_spacer(height=15)

            # MIDI output
            dpg.add_text("MIDI Output Device:")
            dpg.add_combo(
                items=["None", "Device 1", "Device 2"],  # TODO: Enumerate actual devices
                default_value=self.settings["midi"]["output_device"],
                width=300,
                callback=lambda s, v: self._update_setting("midi", "output_device", v)
            )

            dpg.add_spacer(height=15)

            # MIDI clock sync
            dpg.add_checkbox(
                label="Enable MIDI Clock Sync",
                default_value=self.settings["midi"]["midi_clock_sync"],
                callback=lambda s, v: self._update_setting("midi", "midi_clock_sync", v)
            )

    def _format_modifier_display(self, modifier: str) -> str:
        """Format modifier string for display (proper capitalization)."""
        if modifier == "none":
            return "None"
        # Handle compound modifiers like "ctrl+shift"
        parts = modifier.split('+')
        return '+'.join(p.capitalize() for p in parts)

    def _create_piano_roll_settings(self):
        """Create Piano Roll settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("PIANO ROLL SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=10)

            dpg.add_text("Mouse Wheel Modifiers", color=(200, 200, 200))
            dpg.add_spacer(height=5)
            dpg.add_text("Configure which modifier keys control mouse wheel actions:", color=(150, 150, 150))
            dpg.add_spacer(height=10)

            modifier_options = ["None", "Shift", "Ctrl", "Alt", "Ctrl+Shift", "Ctrl+Alt", "Shift+Alt"]

            # Vertical Scroll
            dpg.add_text("Vertical Scroll:")
            dpg.add_combo(
                items=modifier_options,
                default_value=self._format_modifier_display(self.settings["piano_roll"]["vertical_scroll_modifier"]),
                callback=lambda s, v: self._update_setting("piano_roll", "vertical_scroll_modifier", v.lower()),
                width=200
            )
            dpg.add_spacer(height=5)

            # Horizontal Scroll
            dpg.add_text("Horizontal Scroll:")
            dpg.add_combo(
                items=modifier_options,
                default_value=self._format_modifier_display(self.settings["piano_roll"]["horizontal_scroll_modifier"]),
                callback=lambda s, v: self._update_setting("piano_roll", "horizontal_scroll_modifier", v.lower()),
                width=200
            )
            dpg.add_spacer(height=5)

            # Horizontal Zoom
            dpg.add_text("Horizontal Zoom:")
            dpg.add_combo(
                items=modifier_options,
                default_value=self._format_modifier_display(self.settings["piano_roll"]["horizontal_zoom_modifier"]),
                callback=lambda s, v: self._update_setting("piano_roll", "horizontal_zoom_modifier", v.lower()),
                width=200
            )
            dpg.add_spacer(height=5)

            # Vertical Zoom
            dpg.add_text("Vertical Zoom:")
            dpg.add_combo(
                items=modifier_options,
                default_value=self._format_modifier_display(self.settings["piano_roll"]["vertical_zoom_modifier"]),
                callback=lambda s, v: self._update_setting("piano_roll", "vertical_zoom_modifier", v.lower()),
                width=200
            )

            dpg.add_spacer(height=15)
            dpg.add_separator()
            dpg.add_spacer(height=10)
            dpg.add_text("Current Mapping:", color=(150, 150, 150))
            dpg.add_spacer(height=5)

            # Preview of current settings
            v_scroll = self._format_modifier_display(self.settings['piano_roll']['vertical_scroll_modifier'])
            h_scroll = self._format_modifier_display(self.settings['piano_roll']['horizontal_scroll_modifier'])
            h_zoom = self._format_modifier_display(self.settings['piano_roll']['horizontal_zoom_modifier'])
            v_zoom = self._format_modifier_display(self.settings['piano_roll']['vertical_zoom_modifier'])

            dpg.add_text(f"• Mouse Wheel = {v_scroll if v_scroll != 'None' else 'No modifier'} → Vertical Scroll", color=(200, 200, 200))
            dpg.add_text(f"• {h_scroll} + Wheel = Horizontal Scroll", color=(200, 200, 200))
            dpg.add_text(f"• {h_zoom} + Wheel = Horizontal Zoom", color=(200, 200, 200))
            dpg.add_text(f"• {v_zoom} + Wheel = Vertical Zoom", color=(200, 200, 200))

    def _create_keybindings_settings(self):
        """Create Key Bindings settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("KEY BINDINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=10)

            # Instructions
            dpg.add_text("Click a button and press your desired key combination.",
                        color=(150, 150, 150, 255))
            dpg.add_text("Press ESC to cancel binding.",
                        color=(150, 150, 150, 255))
            dpg.add_spacer(height=15)

            bindings = [
                ("New Project", "new_project"),
                ("Open Project", "open_project"),
                ("Save Project", "save_project"),
                ("Undo", "undo"),
                ("Redo", "redo"),
                ("Play/Pause", "play/pause"),  # CHANGED from "Play", "play"
                ("Stop", "stop")
            ]

            for label, key in bindings:
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{label}:")
                    dpg.add_spacer(width=20)

                    # Display current binding
                    current_binding = self.settings["key_bindings"].get(key, "None")
                    dpg.add_text(current_binding, tag=f"binding_display_{key}",
                                color=(0, 122, 204, 255))
                    dpg.add_spacer(width=20)

                    # Bind button
                    dpg.add_button(
                        label="Click to bind...",
                        callback=lambda s, a, u: self._start_key_capture(u),
                        user_data=key,
                        tag=f"bind_button_{key}",
                        width=150
                    )

                    dpg.add_spacer(width=10)

                    # Clear button
                    dpg.add_button(
                        label="Clear",
                        callback=lambda s, a, u: self._clear_binding(u),
                        user_data=key,
                        width=60
                    )

                dpg.add_spacer(height=10)

            dpg.add_spacer(height=20)
            dpg.add_separator()
            dpg.add_spacer(height=15)

            # Piano Roll Controls (display only - configured in Piano Roll settings)
            dpg.add_text("Piano Roll Controls", color=(200, 200, 200))
            dpg.add_text("(Configure these in Piano Roll settings)", color=(150, 150, 150, 255))
            dpg.add_spacer(height=10)

            # Get piano roll settings
            pr_settings = self.settings.get("piano_roll", {
                "vertical_scroll_modifier": "none",
                "horizontal_scroll_modifier": "shift",
                "horizontal_zoom_modifier": "ctrl",
                "vertical_zoom_modifier": "ctrl+shift"
            })

            # Display piano roll controls
            pr_controls = [
                ("Vertical Scroll", pr_settings.get("vertical_scroll_modifier", "none")),
                ("Horizontal Scroll", pr_settings.get("horizontal_scroll_modifier", "shift")),
                ("Horizontal Zoom", pr_settings.get("horizontal_zoom_modifier", "ctrl")),
                ("Vertical Zoom", pr_settings.get("vertical_zoom_modifier", "ctrl+shift"))
            ]

            for label, modifier in pr_controls:
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{label}:")
                    dpg.add_spacer(width=20)

                    # Format modifier for display
                    modifier_display = self._format_modifier_display(modifier) + " + Mouse Wheel"
                    dpg.add_text(modifier_display, color=(0, 122, 204, 255))

                dpg.add_spacer(height=8)

            dpg.add_spacer(height=20)

            # Status message
            dpg.add_text("", tag="binding_status_text", color=(200, 200, 80, 255))

    def _create_plugins_settings(self):
        """Create Plugins settings fields."""
        parent = "settings_right_column"

        with dpg.group(tag=self._settings_content_tag, parent=parent):
            dpg.add_text("PLUGIN SETTINGS", color=(100, 150, 200, 255))
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # VST paths
            dpg.add_text("VST Plugin Directories:")
            dpg.add_spacer(height=5)

            vst_paths = self.settings["plugins"]["vst_paths"]
            if vst_paths:
                for path in vst_paths:
                    dpg.add_text(f"  • {path}", color=(180, 180, 180, 255))
            else:
                dpg.add_text("  No VST paths configured", color=(120, 120, 120, 255))

            dpg.add_spacer(height=10)
            dpg.add_button(label="Add VST Directory...", width=200)

            dpg.add_spacer(height=20)

            # Auto-scan
            dpg.add_checkbox(
                label="Auto-scan for plugins on startup",
                default_value=self.settings["plugins"]["auto_scan"],
                callback=lambda s, v: self._update_setting("plugins", "auto_scan", v)
            )

    def _update_setting(self, category: str, key: str, value: Any):
        """Update a setting value."""
        self.settings[category][key] = value
        self._save_settings()
        print(f"Updated {category}.{key} = {value}")

    def _update_buffer_size(self, value: int, sync_slider=False, sync_input=False):
        """
        Update buffer size and sync slider/input.

        Args:
            value: New buffer size value
            sync_slider: If True, update slider to match input
            sync_input: If True, update input to match slider
        """
        import math

        # Snap to power of 2 for slider
        if sync_slider:
            # Round to nearest power of 2
            value = 2 ** round(math.log2(value))
            dpg.set_value("buffer_size_slider", value)

        if sync_input:
            dpg.set_value("buffer_size_input", value)

        self._update_setting("audio", "buffer_size", value)

    def _apply_ui_scale_now(self):
        """Apply UI scale changes immediately without restarting."""
        from ui.theme import apply_ui_scale

        ui_scale = self.settings.get("video", {}).get("ui_scale", 1.0)
        print(f"Applying UI scale: {ui_scale}x")
        apply_ui_scale(ui_scale)

    def _start_key_capture(self, binding_key):
        """Start capturing keystrokes for a binding."""
        # Update button text
        dpg.set_item_label(f"bind_button_{binding_key}", "Press key...")
        dpg.set_value("binding_status_text",
                     "Press a key combination or ESC to cancel...")

        # Start key capture widget
        self.key_capture.start_capture(
            target_name=binding_key,
            on_captured=lambda binding_str: self._finalize_binding(binding_key, binding_str),
            on_cancelled=lambda: self._cancel_key_capture(binding_key)
        )

    def _clear_binding(self, binding_key):
        """Clear a key binding."""
        self.settings["key_bindings"][binding_key] = "None"
        self._save_settings()
        dpg.set_value(f"binding_display_{binding_key}", "None")

    def update(self):
        """
        Called every frame to update key capture widget.
        """
        self.key_capture.update()



    def _finalize_binding(self, binding_key, binding_str):
        """Save the captured binding."""
        self.settings["key_bindings"][binding_key] = binding_str
        self._save_settings()

        # Update UI
        dpg.set_value(f"binding_display_{binding_key}", binding_str)
        dpg.set_item_label(f"bind_button_{binding_key}", "Click to bind...")
        dpg.set_value("binding_status_text", f"Bound to: {binding_str}")

    def _cancel_key_capture(self, binding_key):
        """Cancel key capture mode."""
        dpg.set_item_label(f"bind_button_{binding_key}", "Click to bind...")
        dpg.set_value("binding_status_text", "Binding cancelled")

    def create(self) -> str:
        """
        Create the settings page window.

        Returns:
            Window tag
        """
        from ui.theme import create_accent_button_theme

        with dpg.window(label="Settings",
                       width=900, height=700,
                       pos=(50, 50),
                       tag=self._window_tag,
                       no_scrollbar=True,
                       no_resize=True,
                       modal=False):

            # === HEADER ===
            dpg.add_spacer(height=30)

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=40)
                dpg.add_text("SETTINGS", color=(0, 122, 204, 255))

            dpg.add_spacer(height=30)
            dpg.add_separator()
            dpg.add_spacer(height=30)

            # === TWO COLUMN LAYOUT ===
            with dpg.group(horizontal=True):
                # LEFT COLUMN - Category Buttons
                with dpg.group():
                    dpg.add_spacer(width=40)
                    with dpg.group():
                        categories = ["General", "Video", "Audio", "MIDI", "Piano Roll", "Key Bindings", "Plugins"]

                        for category in categories:
                            btn_tag = f"category_btn_{category.lower().replace(' ', '_')}"
                            btn = dpg.add_button(
                                label=category,
                                width=200,
                                height=45,
                                callback=lambda s, a, u: self._switch_category(u),
                                user_data=category,
                                tag=btn_tag
                            )

                            # Store button tag for later theme updates
                            self.category_buttons[category] = btn_tag

                            # Highlight current category
                            if category == self.current_category:
                                accent_theme = create_accent_button_theme()
                                dpg.bind_item_theme(btn, accent_theme)

                            dpg.add_spacer(height=10)

                # Spacer between columns
                dpg.add_spacer(width=50)

                # RIGHT COLUMN - Settings Content
                with dpg.group(tag="settings_right_column"):
                    pass  # Content will be added by _refresh_settings_content()

            # === FOOTER ===
            dpg.add_spacer(height=40)

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=600)

                # Close button
                dpg.add_button(
                    label="Close",
                    callback=lambda: self.on_close() if self.on_close else None,
                    width=120,
                    height=40
                )

        # Initialize with default category
        self._refresh_settings_content()

        return self._window_tag

    def show(self):
        """Show the settings page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.show_item(self._window_tag)

    def hide(self):
        """Hide the settings page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.hide_item(self._window_tag)

    def destroy(self):
        """Destroy the settings page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.delete_item(self._window_tag)
