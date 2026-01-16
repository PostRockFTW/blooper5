"""
Base classes for all plugins.

Plugins are:
- Discovered automatically via entry points
- Validated via metadata schema
- Sandboxed for safety
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np


class PluginMetadata:
    """
    Plugin metadata (name, version, author, etc.).

    Attributes:
        name: Plugin name
        version: Plugin version (semantic versioning)
        author: Plugin author
        category: "source" or "effect"
        description: Plugin description
        parameters: List of parameter definitions
    """

    def __init__(self, metadata_dict: Dict[str, Any]):
        """
        Initialize from metadata dictionary.

        Args:
            metadata_dict: Metadata dictionary from plugin

        Raises:
            ValueError: If metadata is invalid
        """
        self.name = metadata_dict.get("name", "")
        self.version = metadata_dict.get("version", "1.0.0")
        self.author = metadata_dict.get("author", "Unknown")
        self.category = metadata_dict.get("category", "")
        self.description = metadata_dict.get("description", "")

        # Parse parameter definitions
        params_data = metadata_dict.get("parameters", [])
        self.parameters = [ParameterDefinition(p) for p in params_data]

        # Validate on construction
        self.validate()

    def validate(self) -> bool:
        """
        Validate metadata schema.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.name:
            raise ValueError("Plugin name is required")

        if self.category not in ["source", "effect"]:
            raise ValueError(f"Invalid category: {self.category}. Must be 'source' or 'effect'")

        # Validate version format (simple check)
        parts = self.version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Invalid version format: {self.version}. Expected semantic versioning (e.g., 1.0.0)")

        return True


class ParameterDefinition:
    """
    Definition of a plugin parameter.

    Attributes:
        name: Parameter name
        type: Parameter type ("float", "int", "bool", "enum")
        min_value: Minimum value (for numeric types)
        max_value: Maximum value (for numeric types)
        default_value: Default value
        unit: Display unit (e.g., "Hz", "dB", "%")
        enum_values: List of values for enum type
    """

    def __init__(self, param_dict: Dict[str, Any]):
        """
        Initialize from parameter dictionary.

        Args:
            param_dict: Parameter definition dictionary
        """
        self.name = param_dict.get("name", "")
        self.type = param_dict.get("type", "float")
        self.min_value = param_dict.get("min_value", 0.0)
        self.max_value = param_dict.get("max_value", 1.0)
        self.default_value = param_dict.get("default_value", 0.5)
        self.unit = param_dict.get("unit", "")
        self.enum_values = param_dict.get("enum_values", [])

        # Validate parameter definition
        self._validate()

    def _validate(self):
        """Validate parameter definition."""
        if not self.name:
            raise ValueError("Parameter name is required")

        valid_types = ["float", "int", "bool", "enum"]
        if self.type not in valid_types:
            raise ValueError(f"Invalid parameter type: {self.type}. Must be one of {valid_types}")

        if self.type == "enum" and not self.enum_values:
            raise ValueError(f"Parameter {self.name} is enum type but has no enum_values")

        if self.type in ["float", "int"]:
            if self.min_value >= self.max_value:
                raise ValueError(f"Parameter {self.name}: min_value must be less than max_value")


class AudioProcessor(ABC):
    """Base class for all audio processors (sources and effects)."""

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Returns:
            Plugin metadata
        """
        raise NotImplementedError()

    @abstractmethod
    def process(self, input_buffer: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Process audio buffer.

        Args:
            input_buffer: Input audio (stereo, shape=(frames, 2))
            sample_rate: Audio sample rate

        Returns:
            Processed audio (same shape as input)
        """
        raise NotImplementedError()

    @abstractmethod
    def set_parameter(self, param_name: str, value: Any):
        """
        Set plugin parameter.

        Args:
            param_name: Parameter name
            value: Parameter value

        Raises:
            ValueError: If parameter name or value is invalid
        """
        raise NotImplementedError()

    @abstractmethod
    def get_parameter(self, param_name: str) -> Any:
        """
        Get plugin parameter value.

        Args:
            param_name: Parameter name

        Returns:
            Parameter value

        Raises:
            ValueError: If parameter name is invalid
        """
        raise NotImplementedError()

    def get_all_parameters(self) -> Dict[str, Any]:
        """
        Get all parameter values as dictionary.

        Returns:
            Dictionary of parameter name -> value
        """
        metadata = self.get_metadata()
        return {param.name: self.get_parameter(param.name) for param in metadata.parameters}

    def reset(self):
        """Reset plugin state (clear buffers, reset envelopes, etc.)."""
        # Default implementation does nothing
        pass


class SourcePlugin(AudioProcessor):
    """Base class for instrument/synth plugins."""

    @abstractmethod
    def note_on(self, note: int, velocity: int):
        """
        Trigger note on.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
        """
        raise NotImplementedError()

    @abstractmethod
    def note_off(self, note: int):
        """
        Trigger note off.

        Args:
            note: MIDI note number (0-127)
        """
        raise NotImplementedError()

    def all_notes_off(self):
        """Release all currently playing notes."""
        # Default implementation does nothing
        pass

    def get_active_notes(self) -> List[int]:
        """
        Get list of currently active note numbers.

        Returns:
            List of MIDI note numbers
        """
        return []


class EffectPlugin(AudioProcessor):
    """Base class for audio effect plugins."""

    def set_wet_dry(self, wet: float):
        """
        Set wet/dry mix.

        Args:
            wet: Wet amount (0.0=fully dry, 1.0=fully wet)
        """
        self.set_parameter("mix", wet)

    def get_wet_dry(self) -> float:
        """
        Get wet/dry mix.

        Returns:
            Wet amount (0.0-1.0)
        """
        return self.get_parameter("mix")
