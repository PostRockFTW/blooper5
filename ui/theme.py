"""
VS Code Dark Mode theme for Blooper5.
Provides color palette and DearPyGui theme configuration.
"""
import dearpygui.dearpygui as dpg
from typing import Dict, Tuple

# VS Code Dark Mode Color Palette
# Based on VS Code's default dark theme (Dark+)

class VSCodeDark:
    """VS Code dark mode color constants."""

    # Background colors
    BG_EDITOR = (30, 30, 30, 255)          # #1E1E1E - Main editor background
    BG_SIDEBAR = (37, 37, 38, 255)         # #252526 - Sidebar background
    BG_PANEL = (51, 51, 51, 255)           # #333333 - Panel background
    BG_INPUT = (60, 60, 60, 255)           # #3C3C3C - Input fields
    BG_HOVER = (45, 45, 45, 255)           # #2D2D2D - Hover state

    # Border colors
    BORDER = (60, 60, 60, 255)             # #3C3C3C - General borders
    BORDER_ACTIVE = (0, 122, 204, 255)     # #007ACC - Active element border

    # Text colors
    TEXT_PRIMARY = (212, 212, 212, 255)    # #D4D4D4 - Primary text
    TEXT_SECONDARY = (150, 150, 150, 255)  # #969696 - Secondary text
    TEXT_DISABLED = (90, 90, 90, 255)      # #5A5A5A - Disabled text

    # Accent colors
    ACCENT_BLUE = (0, 122, 204, 255)       # #007ACC - Primary accent (buttons, links)
    ACCENT_BLUE_HOVER = (0, 142, 234, 255) # #008EEA - Hover state
    ACCENT_BLUE_ACTIVE = (0, 102, 184, 255)# #0066B8 - Active/pressed state

    # Status colors
    SUCCESS = (80, 160, 80, 255)           # #50A050 - Success/play
    WARNING = (220, 180, 80, 255)          # #DCB450 - Warning
    ERROR = (220, 80, 80, 255)             # #DC5050 - Error/stop
    INFO = (100, 150, 220, 255)            # #6496DC - Info

    # Selection colors
    SELECTION = (38, 79, 120, 255)         # #264F78 - Selected items
    SELECTION_HOVER = (45, 90, 135, 255)   # #2D5A87 - Hovered selection

    # Widget-specific colors
    SLIDER_GRAB = (0, 122, 204, 255)       # Slider handle
    SLIDER_GRAB_ACTIVE = (0, 142, 234, 255)# Slider handle when dragging
    SLIDER_TRACK = (90, 90, 90, 255)       # Slider track background

    BUTTON_NORMAL = (60, 60, 60, 255)      # Normal button
    BUTTON_HOVER = (70, 70, 70, 255)       # Hovered button
    BUTTON_ACTIVE = (80, 80, 80, 255)      # Pressed button

    BUTTON_ACCENT_NORMAL = ACCENT_BLUE
    BUTTON_ACCENT_HOVER = ACCENT_BLUE_HOVER
    BUTTON_ACCENT_ACTIVE = ACCENT_BLUE_ACTIVE

    # Spacing
    FRAME_PADDING = (8, 6)                 # Padding inside widgets
    ITEM_SPACING = (8, 4)                  # Space between widgets
    WINDOW_PADDING = (12, 12)              # Padding inside windows


def apply_vscode_theme() -> None:
    """
    Apply VS Code dark theme to DearPyGui.
    Call this once during application initialization.
    """
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window/frame colors
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, VSCodeDark.BG_EDITOR)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, VSCodeDark.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, VSCodeDark.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, VSCodeDark.BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, VSCodeDark.BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, VSCodeDark.BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, VSCodeDark.BORDER_ACTIVE)

            # Text colors
            dpg.add_theme_color(dpg.mvThemeCol_Text, VSCodeDark.TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, VSCodeDark.TEXT_DISABLED)

            # Button colors
            dpg.add_theme_color(dpg.mvThemeCol_Button, VSCodeDark.BUTTON_NORMAL)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, VSCodeDark.BUTTON_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, VSCodeDark.BUTTON_ACTIVE)

            # Header/collapsing header colors
            dpg.add_theme_color(dpg.mvThemeCol_Header, VSCodeDark.BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, VSCodeDark.SELECTION_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, VSCodeDark.SELECTION)

            # Tab colors
            dpg.add_theme_color(dpg.mvThemeCol_Tab, VSCodeDark.BG_SIDEBAR)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, VSCodeDark.BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, VSCodeDark.BG_PANEL)

            # Slider colors
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, VSCodeDark.SLIDER_GRAB)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, VSCodeDark.SLIDER_GRAB_ACTIVE)

            # Spacing
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, VSCodeDark.FRAME_PADDING[0], VSCodeDark.FRAME_PADDING[1])
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, VSCodeDark.ITEM_SPACING[0], VSCodeDark.ITEM_SPACING[1])
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, VSCodeDark.WINDOW_PADDING[0], VSCodeDark.WINDOW_PADDING[1])
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)  # Slight rounding
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 3)

    dpg.bind_theme(global_theme)


def create_accent_button_theme() -> str:
    """
    Create accent button theme for primary actions (Play, Save, etc.).

    Returns:
        Theme tag that can be bound to buttons
    """
    with dpg.theme() as accent_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, VSCodeDark.BUTTON_ACCENT_NORMAL)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, VSCodeDark.BUTTON_ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, VSCodeDark.BUTTON_ACCENT_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

    return accent_theme


def create_success_button_theme() -> str:
    """
    Create success/play button theme (green).

    Returns:
        Theme tag that can be bound to buttons
    """
    with dpg.theme() as success_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, VSCodeDark.SUCCESS)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (90, 180, 90, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (70, 140, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

    return success_theme


def create_error_button_theme() -> str:
    """
    Create error/stop button theme (red).

    Returns:
        Theme tag that can be bound to buttons
    """
    with dpg.theme() as error_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, VSCodeDark.ERROR)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (230, 90, 90, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 70, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

    return error_theme
