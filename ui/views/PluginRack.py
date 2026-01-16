"""
Plugin Rack - Visual plugin chain with auto-generated parameter controls.

Features:
- List of available plugins (from registry)
- Drag-and-drop to add plugins to track
- Plugin chain visualization (Source → FX1 → FX2 → Output)
- Auto-generated parameter controls from PluginMetadata
- Bypass/Enable toggle per plugin
- Preset management (save/load plugin states)
- Reorder plugins in chain
"""

import dearpygui.dearpygui as dpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# Mock PluginMetadata (will be replaced with plugins.base.PluginMetadata)
@dataclass
class MockParameterDef:
    """Parameter definition for auto-generating UI controls."""
    name: str
    min_val: float
    max_val: float
    default_val: float
    step: float = 0.01
    unit: str = ""  # Hz, dB, ms, etc.


@dataclass
class MockPluginMetadata:
    """Metadata about a plugin for UI generation."""
    id: str
    name: str
    category: str  # "source" or "effect"
    version: str
    parameters: List[MockParameterDef]


# Mock plugin state
@dataclass
class PluginInstance:
    """An instance of a plugin in the chain."""
    metadata: MockPluginMetadata
    enabled: bool = True
    bypassed: bool = False
    parameters: Dict[str, float] = None

    def __post_init__(self):
        if self.parameters is None:
            # Initialize with default values
            self.parameters = {
                p.name: p.default_val
                for p in self.metadata.parameters
            }


class PluginRack:
    """Plugin rack for visualizing and controlling plugin chains."""

    def __init__(self, width: int = 400, height: int = 800):
        self.width = width
        self.height = height

        # Plugin chain (list of PluginInstance)
        self.plugin_chain: List[PluginInstance] = []
        self.source_plugin: Optional[PluginInstance] = None

        # Available plugins (mock registry)
        self.available_sources = self._get_mock_sources()
        self.available_effects = self._get_mock_effects()

        # DearPyGui IDs
        self.window_id = None
        self.chain_container_id = None

    def _get_mock_sources(self) -> List[MockPluginMetadata]:
        """Mock source plugins until registry is ready."""
        return [
            MockPluginMetadata(
                id="DUAL_OSC",
                name="Dual Oscillator",
                category="source",
                version="1.0",
                parameters=[
                    MockParameterDef("osc1_freq", 20.0, 20000.0, 440.0, 1.0, "Hz"),
                    MockParameterDef("osc2_freq", 20.0, 20000.0, 880.0, 1.0, "Hz"),
                    MockParameterDef("osc1_gain", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("osc2_gain", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("detune", -100.0, 100.0, 0.0, 1.0, "cents"),
                ]
            ),
            MockPluginMetadata(
                id="WAVETABLE",
                name="Wavetable Synth",
                category="source",
                version="1.0",
                parameters=[
                    MockParameterDef("position", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("frequency", 20.0, 20000.0, 440.0, 1.0, "Hz"),
                    MockParameterDef("gain", 0.0, 1.0, 0.7, 0.01),
                ]
            ),
            MockPluginMetadata(
                id="NOISE_DRUM",
                name="Noise Drum",
                category="source",
                version="1.0",
                parameters=[
                    MockParameterDef("decay", 0.01, 2.0, 0.2, 0.01, "s"),
                    MockParameterDef("cutoff", 100.0, 10000.0, 2000.0, 10.0, "Hz"),
                    MockParameterDef("resonance", 0.0, 1.0, 0.3, 0.01),
                ]
            ),
        ]

    def _get_mock_effects(self) -> List[MockPluginMetadata]:
        """Mock effect plugins until registry is ready."""
        return [
            MockPluginMetadata(
                id="EQ",
                name="3-Band EQ",
                category="effect",
                version="1.0",
                parameters=[
                    MockParameterDef("low_gain", -12.0, 12.0, 0.0, 0.1, "dB"),
                    MockParameterDef("mid_gain", -12.0, 12.0, 0.0, 0.1, "dB"),
                    MockParameterDef("high_gain", -12.0, 12.0, 0.0, 0.1, "dB"),
                ]
            ),
            MockPluginMetadata(
                id="REVERB",
                name="Simple Reverb",
                category="effect",
                version="1.0",
                parameters=[
                    MockParameterDef("room_size", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("damping", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("wet", 0.0, 1.0, 0.3, 0.01),
                    MockParameterDef("dry", 0.0, 1.0, 0.7, 0.01),
                ]
            ),
            MockPluginMetadata(
                id="DELAY",
                name="Stereo Delay",
                category="effect",
                version="1.0",
                parameters=[
                    MockParameterDef("delay_time", 0.0, 2.0, 0.5, 0.01, "s"),
                    MockParameterDef("feedback", 0.0, 0.95, 0.4, 0.01),
                    MockParameterDef("mix", 0.0, 1.0, 0.3, 0.01),
                ]
            ),
            MockPluginMetadata(
                id="SPACE_REVERB",
                name="Space Reverb",
                category="effect",
                version="1.0",
                parameters=[
                    MockParameterDef("size", 0.0, 1.0, 0.7, 0.01),
                    MockParameterDef("decay", 0.1, 10.0, 2.0, 0.1, "s"),
                    MockParameterDef("pre_delay", 0.0, 0.5, 0.02, 0.001, "s"),
                    MockParameterDef("damping", 0.0, 1.0, 0.5, 0.01),
                    MockParameterDef("diffusion", 0.0, 1.0, 0.7, 0.01),
                    MockParameterDef("mix", 0.0, 1.0, 0.4, 0.01),
                ]
            ),
        ]

    def add_source_plugin(self, plugin_id: str):
        """Set the source plugin for this track."""
        for meta in self.available_sources:
            if meta.id == plugin_id:
                self.source_plugin = PluginInstance(metadata=meta)
                self._rebuild_ui()
                return

    def add_effect_plugin(self, plugin_id: str):
        """Add an effect plugin to the chain."""
        for meta in self.available_effects:
            if meta.id == plugin_id:
                instance = PluginInstance(metadata=meta)
                self.plugin_chain.append(instance)
                self._rebuild_ui()
                return

    def remove_plugin(self, index: int):
        """Remove a plugin from the chain."""
        if 0 <= index < len(self.plugin_chain):
            self.plugin_chain.pop(index)
            self._rebuild_ui()

    def move_plugin(self, from_index: int, to_index: int):
        """Reorder plugins in the chain."""
        if 0 <= from_index < len(self.plugin_chain) and 0 <= to_index < len(self.plugin_chain):
            plugin = self.plugin_chain.pop(from_index)
            self.plugin_chain.insert(to_index, plugin)
            self._rebuild_ui()

    def toggle_bypass(self, index: int):
        """Toggle bypass for a plugin."""
        if index == -1 and self.source_plugin:  # Source plugin
            self.source_plugin.bypassed = not self.source_plugin.bypassed
        elif 0 <= index < len(self.plugin_chain):
            self.plugin_chain[index].bypassed = not self.plugin_chain[index].bypassed
        self._rebuild_ui()

    def _create_parameter_control(self, plugin: PluginInstance, param_def: MockParameterDef, parent):
        """Auto-generate UI control for a parameter."""
        param_id = f"{plugin.metadata.id}_{param_def.name}"

        with dpg.group(horizontal=True, parent=parent):
            # Parameter label with unit
            label_text = f"{param_def.name.replace('_', ' ').title()}"
            if param_def.unit:
                label_text += f" ({param_def.unit})"
            dpg.add_text(label_text, width=150)

            # Slider control
            def update_param(sender, value):
                plugin.parameters[param_def.name] = value

            dpg.add_slider_float(
                tag=param_id,
                default_value=plugin.parameters[param_def.name],
                min_value=param_def.min_val,
                max_value=param_def.max_val,
                callback=update_param,
                width=200,
                format=f"%.{2 if param_def.step < 1 else 0}f"
            )

            # Value display
            dpg.add_text(f"{plugin.parameters[param_def.name]:.2f}")

    def _create_plugin_panel(self, plugin: PluginInstance, index: int, parent):
        """Create a collapsible panel for a plugin."""
        panel_id = f"plugin_panel_{plugin.metadata.id}_{index}"

        # Panel header color based on bypass state
        header_color = (60, 60, 70) if not plugin.bypassed else (40, 40, 40)

        with dpg.collapsing_header(label=plugin.metadata.name, parent=parent, default_open=True):
            # Plugin controls row
            with dpg.group(horizontal=True):
                # Bypass button
                bypass_label = "Enable" if plugin.bypassed else "Bypass"
                dpg.add_button(
                    label=bypass_label,
                    callback=lambda: self.toggle_bypass(index),
                    width=80
                )

                # Remove button
                if index >= 0:  # Only show for effect plugins, not source
                    dpg.add_button(
                        label="Remove",
                        callback=lambda: self.remove_plugin(index),
                        width=80
                    )

                # Move buttons
                if index > 0:
                    dpg.add_button(
                        label="↑",
                        callback=lambda: self.move_plugin(index, index - 1),
                        width=30
                    )
                if index < len(self.plugin_chain) - 1 and index >= 0:
                    dpg.add_button(
                        label="↓",
                        callback=lambda: self.move_plugin(index, index + 1),
                        width=30
                    )

            dpg.add_spacer(height=5)

            # Plugin info
            dpg.add_text(f"Category: {plugin.metadata.category.upper()}")
            dpg.add_text(f"Version: {plugin.metadata.version}")
            dpg.add_separator()

            # Parameter controls
            if not plugin.bypassed:
                for param_def in plugin.metadata.parameters:
                    self._create_parameter_control(plugin, param_def, parent=dpg.last_container())
                    dpg.add_spacer(height=3)

    def _rebuild_ui(self):
        """Rebuild the plugin chain UI."""
        if not self.chain_container_id:
            return

        # Clear existing UI
        dpg.delete_item(self.chain_container_id, children_only=True)

        # Source plugin section
        dpg.add_text("SOURCE", color=(200, 200, 100), parent=self.chain_container_id)
        dpg.add_separator(parent=self.chain_container_id)

        if self.source_plugin:
            self._create_plugin_panel(self.source_plugin, -1, self.chain_container_id)
        else:
            dpg.add_text("No source plugin selected", parent=self.chain_container_id)
            # Source selector dropdown
            if dpg.does_item_exist("source_selector"):
                dpg.delete_item("source_selector")

            source_names = [s.name for s in self.available_sources]
            dpg.add_combo(
                tag="source_selector",
                items=source_names,
                label="Select Source",
                callback=lambda s, v: self.add_source_plugin(
                    self.available_sources[source_names.index(v)].id
                ),
                parent=self.chain_container_id,
                width=250
            )

        dpg.add_spacer(height=20, parent=self.chain_container_id)

        # Effects chain section
        dpg.add_text("EFFECTS CHAIN", color=(100, 200, 200), parent=self.chain_container_id)
        dpg.add_separator(parent=self.chain_container_id)

        if self.plugin_chain:
            for i, plugin in enumerate(self.plugin_chain):
                self._create_plugin_panel(plugin, i, self.chain_container_id)
                dpg.add_spacer(height=10, parent=self.chain_container_id)
        else:
            dpg.add_text("No effects in chain", parent=self.chain_container_id)

        # Add effect button
        dpg.add_spacer(height=10, parent=self.chain_container_id)
        effect_names = [e.name for e in self.available_effects]

        if dpg.does_item_exist("effect_selector"):
            dpg.delete_item("effect_selector")

        dpg.add_combo(
            tag="effect_selector",
            items=effect_names,
            label="Add Effect",
            callback=lambda s, v: self.add_effect_plugin(
                self.available_effects[effect_names.index(v)].id
            ),
            parent=self.chain_container_id,
            width=250
        )

    def create_window(self, tag: str = "plugin_rack_window"):
        """Create the DearPyGui window for the plugin rack."""
        with dpg.window(label="Plugin Rack", tag=tag, width=self.width, height=self.height):
            # Title
            dpg.add_text("Plugin Chain Editor", color=(255, 255, 255))
            dpg.add_separator()

            # Scrollable container for plugins
            with dpg.child_window(height=self.height - 100) as container:
                self.chain_container_id = container

            # Preset controls at bottom
            with dpg.group(horizontal=True):
                dpg.add_button(label="Save Preset", callback=self._save_preset)
                dpg.add_button(label="Load Preset", callback=self._load_preset)
                dpg.add_button(label="Reset All", callback=self._reset_all)

        self.window_id = tag
        self._rebuild_ui()

    def _save_preset(self):
        """Save current plugin chain as preset."""
        # TODO: Implement preset saving (JSON serialization)
        print("Save preset (not implemented yet)")

    def _load_preset(self):
        """Load a preset."""
        # TODO: Implement preset loading
        print("Load preset (not implemented yet)")

    def _reset_all(self):
        """Reset all parameters to defaults."""
        if self.source_plugin:
            for param_name, param_def in zip(
                self.source_plugin.parameters.keys(),
                self.source_plugin.metadata.parameters
            ):
                self.source_plugin.parameters[param_name] = param_def.default_val

        for plugin in self.plugin_chain:
            for param_name, param_def in zip(
                plugin.parameters.keys(),
                plugin.metadata.parameters
            ):
                plugin.parameters[param_name] = param_def.default_val

        self._rebuild_ui()


def create_plugin_rack_demo():
    """Demo function to test the plugin rack."""
    dpg.create_context()

    rack = PluginRack(width=500, height=800)
    rack.create_window()

    # Add some plugins for demonstration
    rack.add_source_plugin("DUAL_OSC")
    rack.add_effect_plugin("EQ")
    rack.add_effect_plugin("REVERB")

    dpg.create_viewport(title="Plugin Rack Demo", width=550, height=850)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    create_plugin_rack_demo()
