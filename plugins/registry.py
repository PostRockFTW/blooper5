"""
Plugin registry for discovery and instantiation.

Features:
- Manual plugin registration (no auto-discovery for simplicity)
- Plugin validation
- Instance caching
- Categorized lookup (sources vs effects)
"""
from typing import Dict, List, Optional, Type
import importlib
import sys

from plugins.base import AudioProcessor, PluginMetadata, PluginCategory


class PluginRegistry:
    """
    Manages plugin discovery and instantiation.

    Plugins are registered manually in SOURCE_PLUGINS and EFFECT_PLUGINS dicts.
    Each entry maps plugin ID to module path.
    """

    # Plugin registries (ID -> module path)
    SOURCE_PLUGINS = {
        "DUAL_OSC": "plugins.sources.dual_osc",
        "WAVETABLE_SYNTH": "plugins.sources.wavetable_synth",
        "NOISE_DRUM": "plugins.sources.noise_drum",
        "FM_DRUM": "plugins.sources.fm_drum",
        "SQUARE_CYMBAL": "plugins.sources.square_cymbal",
        "PERIODIC_NOISE": "plugins.sources.periodic_noise",
        "ZION_CYMBAL": "plugins.sources.zion_cymbal",
    }

    EFFECT_PLUGINS = {
        "EQ": "plugins.effects.eq",
        "REVERB": "plugins.effects.reverb",
        "PLATE_REVERB": "plugins.effects.plate_reverb",
        "SPACE_REVERB": "plugins.effects.space_reverb",
        "DELAY": "plugins.effects.delay",
    }

    def __init__(self):
        """Initialize plugin registry."""
        # Combine source and effect registries
        self._plugin_map = {**self.SOURCE_PLUGINS, **self.EFFECT_PLUGINS}

        # Cache for plugin classes (plugin_id -> class)
        self._class_cache: Dict[str, Type[AudioProcessor]] = {}

        # Cache for plugin instances (plugin_id -> instance)
        # Note: In Blooper5, we typically don't cache instances since
        # each track may need its own instance. But we cache classes.
        self._instance_cache: Dict[str, AudioProcessor] = {}

        # Metadata cache (plugin_id -> metadata)
        self._metadata_cache: Dict[str, PluginMetadata] = {}

    def _load_module(self, plugin_id: str):
        """
        Dynamically import plugin module.

        Args:
            plugin_id: Plugin ID

        Returns:
            Imported module

        Raises:
            ImportError: If module cannot be loaded
        """
        module_path = self._plugin_map.get(plugin_id)
        if not module_path:
            raise ValueError(f"Unknown plugin ID: {plugin_id}")

        try:
            # Check if already loaded and reload for hot-reloading
            if module_path in sys.modules:
                return importlib.reload(sys.modules[module_path])
            return importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Failed to load plugin '{plugin_id}' from '{module_path}': {e}")

    def _get_plugin_class(self, plugin_id: str) -> Type[AudioProcessor]:
        """
        Get plugin class by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin class

        Raises:
            ImportError: If module cannot be loaded
            AttributeError: If class not found in module
        """
        # Check cache first
        if plugin_id in self._class_cache:
            return self._class_cache[plugin_id]

        # Load module
        module = self._load_module(plugin_id)

        # Find AudioProcessor subclass
        # Convention: Look for a class that inherits from AudioProcessor
        plugin_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                issubclass(obj, AudioProcessor) and
                obj is not AudioProcessor):
                plugin_class = obj
                break

        if plugin_class is None:
            raise AttributeError(
                f"Plugin module '{self._plugin_map[plugin_id]}' must contain "
                f"a class inheriting from AudioProcessor"
            )

        # Validate plugin
        self.validate_plugin(plugin_class)

        # Cache and return
        self._class_cache[plugin_id] = plugin_class
        return plugin_class

    def validate_plugin(self, plugin_class: Type[AudioProcessor]) -> bool:
        """
        Validate plugin implementation.

        Checks:
        1. Inherits from AudioProcessor
        2. Has valid metadata
        3. Implements required methods

        Args:
            plugin_class: Plugin class to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Check inheritance
        if not issubclass(plugin_class, AudioProcessor):
            raise ValueError(f"{plugin_class.__name__} must inherit from AudioProcessor")

        # Check that required methods are implemented (not abstract)
        try:
            # Create temporary instance to check metadata
            temp_instance = plugin_class()
            metadata = temp_instance.get_metadata()

            # Validate metadata
            if not isinstance(metadata, PluginMetadata):
                raise ValueError(f"{plugin_class.__name__}.get_metadata() must return PluginMetadata")

            # Check category matches registration
            # (This is a soft check - we trust the metadata)

        except NotImplementedError as e:
            raise ValueError(f"{plugin_class.__name__} has unimplemented abstract methods: {e}")
        except Exception as e:
            raise ValueError(f"{plugin_class.__name__} validation failed: {e}")

        return True

    def get_plugin_metadata(self, plugin_id: str) -> PluginMetadata:
        """
        Get plugin metadata without creating instance.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin metadata

        Raises:
            ValueError: If plugin not found
        """
        # Check cache
        if plugin_id in self._metadata_cache:
            return self._metadata_cache[plugin_id]

        # Load class and get metadata
        plugin_class = self._get_plugin_class(plugin_id)
        instance = plugin_class()
        metadata = instance.get_metadata()

        # Cache and return
        self._metadata_cache[plugin_id] = metadata
        return metadata

    def create_instance(self, plugin_id: str) -> AudioProcessor:
        """
        Create new plugin instance.

        Args:
            plugin_id: Plugin ID

        Returns:
            New plugin instance

        Raises:
            ValueError: If plugin not found or cannot be instantiated
        """
        plugin_class = self._get_plugin_class(plugin_id)

        try:
            instance = plugin_class()
            return instance
        except Exception as e:
            raise ValueError(f"Failed to create instance of '{plugin_id}': {e}")

    def get_all_plugin_ids(self) -> List[str]:
        """
        Get list of all registered plugin IDs.

        Returns:
            List of plugin IDs
        """
        return list(self._plugin_map.keys())

    def get_source_plugin_ids(self) -> List[str]:
        """
        Get list of source plugin IDs.

        Returns:
            List of source plugin IDs
        """
        return list(self.SOURCE_PLUGINS.keys())

    def get_effect_plugin_ids(self) -> List[str]:
        """
        Get list of effect plugin IDs.

        Returns:
            List of effect plugin IDs
        """
        return list(self.EFFECT_PLUGINS.keys())

    def get_plugins_by_category(self, category: PluginCategory) -> List[str]:
        """
        Get plugin IDs filtered by category.

        Args:
            category: Plugin category (SOURCE or EFFECT)

        Returns:
            List of plugin IDs
        """
        if category == PluginCategory.SOURCE:
            return self.get_source_plugin_ids()
        elif category == PluginCategory.EFFECT:
            return self.get_effect_plugin_ids()
        else:
            raise ValueError(f"Unknown category: {category}")

    def plugin_exists(self, plugin_id: str) -> bool:
        """
        Check if plugin is registered.

        Args:
            plugin_id: Plugin ID

        Returns:
            True if plugin exists
        """
        return plugin_id in self._plugin_map

    def get_plugin_count(self) -> int:
        """
        Get total number of registered plugins.

        Returns:
            Plugin count
        """
        return len(self._plugin_map)

    def clear_caches(self):
        """Clear all internal caches (for hot-reloading during development)."""
        self._class_cache.clear()
        self._instance_cache.clear()
        self._metadata_cache.clear()

    def register_plugin(self, plugin_id: str, module_path: str, category: PluginCategory):
        """
        Manually register a plugin (for third-party plugins).

        Args:
            plugin_id: Unique plugin ID (UPPER_SNAKE_CASE)
            module_path: Python module path (e.g., "my_plugins.my_synth")
            category: Plugin category

        Raises:
            ValueError: If plugin_id already exists
        """
        if plugin_id in self._plugin_map:
            raise ValueError(f"Plugin ID '{plugin_id}' is already registered")

        # Add to appropriate registry
        if category == PluginCategory.SOURCE:
            self.SOURCE_PLUGINS[plugin_id] = module_path
        elif category == PluginCategory.EFFECT:
            self.EFFECT_PLUGINS[plugin_id] = module_path
        else:
            raise ValueError(f"Unknown category: {category}")

        # Update combined map
        self._plugin_map[plugin_id] = module_path

        # Clear caches to force reload
        self.clear_caches()

    def unregister_plugin(self, plugin_id: str):
        """
        Remove plugin from registry.

        Args:
            plugin_id: Plugin ID to unregister
        """
        if plugin_id not in self._plugin_map:
            return

        # Remove from appropriate registry
        if plugin_id in self.SOURCE_PLUGINS:
            del self.SOURCE_PLUGINS[plugin_id]
        if plugin_id in self.EFFECT_PLUGINS:
            del self.EFFECT_PLUGINS[plugin_id]

        # Remove from combined map
        del self._plugin_map[plugin_id]

        # Clear caches
        self.clear_caches()


# Global plugin registry singleton
_global_registry: Optional[PluginRegistry] = None


def get_global_registry() -> PluginRegistry:
    """
    Get the global plugin registry singleton.

    Returns:
        Global plugin registry

    Raises:
        RuntimeError: If registry not initialized
    """
    global _global_registry
    if _global_registry is None:
        raise RuntimeError("Plugin registry not initialized. Call initialize_registry() first.")
    return _global_registry


def initialize_registry() -> PluginRegistry:
    """
    Initialize the global plugin registry.

    Returns:
        Initialized global registry
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_registry():
    """Reset global plugin registry (for testing)."""
    global _global_registry
    _global_registry = None
