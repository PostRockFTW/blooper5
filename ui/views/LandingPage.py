"""
Landing Page for Blooper5.
Main entry point showing New Project, Open Project, and Recent Projects.
"""
import dearpygui.dearpygui as dpg
from typing import Optional, Callable, List, Dict
from pathlib import Path
import json
from datetime import datetime


class LandingPage:
    """
    Landing page view for Blooper5.

    Shows:
    - New Project button
    - Open Project button
    - Recent projects list (last 10)
    - Settings button
    - Exit button
    - Return to Project button (when project is active)
    """

    def __init__(self,
                 on_new_project: Callable,
                 on_open_project: Callable,
                 on_import_midi: Optional[Callable] = None,
                 on_export_midi: Optional[Callable] = None,
                 on_return_to_project: Optional[Callable] = None,
                 on_save_project: Optional[Callable] = None,
                 on_save_as_project: Optional[Callable] = None,
                 on_settings: Optional[Callable] = None,
                 on_exit: Optional[Callable] = None):
        """
        Args:
            on_new_project: Callback when "New Project" clicked
            on_open_project: Callback when "Open Project" clicked (receives file_path)
            on_import_midi: Callback when "Import MIDI" clicked (receives file_path)
            on_export_midi: Callback when "Export MIDI" clicked (receives file_path)
            on_return_to_project: Callback when "Return to Project" clicked (optional)
            on_save_project: Callback when "Save Project" clicked (optional)
            on_save_as_project: Callback when "Save As" clicked (optional)
            on_settings: Callback when "Settings" clicked (optional)
            on_exit: Callback when "Exit" clicked (optional)
        """
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_import_midi = on_import_midi
        self.on_export_midi = on_export_midi
        self.on_return_to_project = on_return_to_project
        self.on_save_project = on_save_project
        self.on_save_as_project = on_save_as_project
        self.on_settings = on_settings
        self.on_exit = on_exit

        self.has_active_project = False
        self.recent_projects: List[Dict] = []
        self._window_tag = "landing_page_window"
        self._load_recent_projects()

    def _load_recent_projects(self):
        """Load recent projects from config file."""
        config_path = Path.home() / ".blooper5" / "recent_projects.json"

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.recent_projects = json.load(f)
            except Exception as e:
                print(f"Failed to load recent projects: {e}")
                self.recent_projects = []
        else:
            self.recent_projects = []

    def _save_recent_projects(self):
        """Save recent projects to config file."""
        config_path = Path.home() / ".blooper5" / "recent_projects.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, 'w') as f:
                json.dump(self.recent_projects, f, indent=2)
        except Exception as e:
            print(f"Failed to save recent projects: {e}")

    def add_recent_project(self, file_path: str):
        """
        Add a project to recent projects list.

        Args:
            file_path: Full path to project file
        """
        # Remove if already exists
        self.recent_projects = [p for p in self.recent_projects if p['path'] != file_path]

        # Add to front
        project_info = {
            'path': file_path,
            'name': Path(file_path).stem,
            'last_opened': datetime.now().isoformat()
        }
        self.recent_projects.insert(0, project_info)

        # Keep only last 10
        self.recent_projects = self.recent_projects[:10]

        self._save_recent_projects()

        # Refresh the UI to show the updated list
        self._refresh_recent_projects()

    def set_active_project(self, active: bool):
        """
        Set whether there's an active project.
        Controls visibility of "Return to Project", "Save Project", and "Save As" buttons.

        Args:
            active: True if project is active
        """
        self.has_active_project = active
        if dpg.does_item_exist("return_to_project_btn"):
            dpg.configure_item("return_to_project_btn", show=active)
        if dpg.does_item_exist("save_project_btn"):
            dpg.configure_item("save_project_btn", show=active)
        if dpg.does_item_exist("save_as_project_btn"):
            dpg.configure_item("save_as_project_btn", show=active)

    def create(self) -> str:
        """
        Create the landing page window.

        Returns:
            Window tag
        """
        from ui.theme import create_accent_button_theme, create_success_button_theme

        with dpg.window(label="Blooper5",
                       width=900, height=700,
                       pos=(50, 50),
                       tag=self._window_tag,
                       no_scrollbar=True,
                       no_resize=True,
                       no_move=False):

            # === HEADER ===
            dpg.add_spacer(height=30)

            # Title - top left
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=40)
                dpg.add_text("BLOOPER5", color=(0, 122, 204, 255))
                dpg.add_spacer(width=10)
                dpg.add_text("Digital Audio Workstation", color=(150, 150, 150, 255))

            dpg.add_spacer(height=30)
            dpg.add_separator()
            dpg.add_spacer(height=30)

            # === TWO COLUMN LAYOUT ===
            with dpg.group(horizontal=True):
                # LEFT COLUMN - Action Buttons
                with dpg.group():
                    dpg.add_spacer(width=40)
                    with dpg.group():
                        # New Project button (accent blue, prominent)
                        new_btn = dpg.add_button(
                            label="New Project",
                            width=280,
                            height=70,
                            callback=lambda: self.on_new_project()
                        )
                        accent_theme = create_accent_button_theme()
                        dpg.bind_item_theme(new_btn, accent_theme)

                        dpg.add_spacer(height=15)

                        # Load Project button (standard style)
                        dpg.add_button(
                            label="Load Project",
                            width=280,
                            height=50,
                            callback=self._show_file_dialog
                        )

                        dpg.add_spacer(height=15)

                        # Import MIDI button
                        dpg.add_button(
                            label="Import MIDI File",
                            width=280,
                            height=50,
                            callback=self._show_import_midi_dialog
                        )

                        dpg.add_spacer(height=15)

                        # Export MIDI button (shown only when project active)
                        dpg.add_button(
                            label="Export MIDI File",
                            width=280,
                            height=50,
                            callback=self._show_export_midi_dialog,
                            tag="export_midi_btn",
                            show=self.has_active_project
                        )

                        dpg.add_spacer(height=15)

                        # Save Project button (hidden by default, shown when project active)
                        dpg.add_button(
                            label="Save Project",
                            width=280,
                            height=50,
                            callback=lambda: self.on_save_project() if self.on_save_project else None,
                            tag="save_project_btn",
                            show=self.has_active_project
                        )

                        dpg.add_spacer(height=15)

                        # Save As button (hidden by default, shown when project active)
                        dpg.add_button(
                            label="Save As...",
                            width=280,
                            height=50,
                            callback=lambda: self.on_save_as_project() if self.on_save_as_project else None,
                            tag="save_as_project_btn",
                            show=self.has_active_project
                        )

                        dpg.add_spacer(height=15)

                        # Return to Project button (success green, hidden by default)
                        return_btn = dpg.add_button(
                            label="Return to Project",
                            width=280,
                            height=50,
                            callback=lambda: self.on_return_to_project() if self.on_return_to_project else None,
                            tag="return_to_project_btn",
                            show=self.has_active_project
                        )
                        success_theme = create_success_button_theme()
                        dpg.bind_item_theme(return_btn, success_theme)

                        dpg.add_spacer(height=30)

                        # Settings button
                        dpg.add_button(
                            label="Settings",
                            callback=lambda: self.on_settings() if self.on_settings else None,
                            width=280,
                            height=40
                        )

                        dpg.add_spacer(height=10)

                        # Exit button
                        dpg.add_button(
                            label="Exit",
                            callback=lambda: self.on_exit() if self.on_exit else None,
                            width=280,
                            height=40
                        )

                # Spacer between columns
                dpg.add_spacer(width=50)

                # RIGHT COLUMN - Recent Projects
                with dpg.group():
                    # Section header
                    dpg.add_text("RECENT PROJECTS", color=(100, 150, 200, 255))
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=15)

                    # Recent projects list container (will be dynamically updated)
                    with dpg.group(tag="recent_projects_list"):
                        self._build_recent_projects_list()

        return self._window_tag

    def _build_recent_projects_list(self):
        """Build the recent projects list UI."""
        if self.recent_projects:
            # Recent projects list
            for i, project in enumerate(self.recent_projects[:8]):
                with dpg.group(horizontal=True):
                    # Project name button (clickable)
                    proj_btn = dpg.add_button(
                        label=f"  {project['name']}",
                        width=380,
                        height=40,
                        callback=lambda s, a, u: self._open_recent_project(u),
                        user_data=project['path']
                    )

                    # Last opened date
                    dpg.add_spacer(width=15)
                    try:
                        dt = datetime.fromisoformat(project['last_opened'])
                        date_str = dt.strftime("%m/%d/%y")
                    except:
                        date_str = "Unknown"
                    dpg.add_text(date_str, color=(120, 120, 120, 255))

                if i < min(len(self.recent_projects[:8]) - 1, 7):
                    dpg.add_spacer(height=8)
        else:
            dpg.add_spacer(height=40)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=120)
                dpg.add_text("No recent projects", color=(100, 100, 100, 255))

    def _refresh_recent_projects(self):
        """Refresh the recent projects list display."""
        if dpg.does_item_exist("recent_projects_list"):
            # Delete all children of the recent projects list
            children = dpg.get_item_children("recent_projects_list", slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)

            # Rebuild the list inside the container
            dpg.push_container_stack("recent_projects_list")
            self._build_recent_projects_list()
            dpg.pop_container_stack()

    def _show_file_dialog(self):
        """Show file dialog to open a project."""
        # Create file dialog if it doesn't exist
        if not dpg.does_item_exist("open_project_dialog"):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self._file_dialog_callback,
                tag="open_project_dialog",
                width=700,
                height=400,
                default_path=str(Path.home() / "Documents")
            ):
                dpg.add_file_extension(".bloom5", color=(0, 122, 204, 255))
                dpg.add_file_extension(".*")

        dpg.show_item("open_project_dialog")

    def _file_dialog_callback(self, sender, app_data):
        """Handle file dialog selection."""
        selections = app_data.get('selections', {})
        if selections:
            file_path = list(selections.values())[0]
            self._open_recent_project(file_path)

    def _open_recent_project(self, file_path: str):
        """Open a recent project."""
        print(f"Opening project: {file_path}")
        # Note: add_recent_project is called by on_open_project in main.py
        self.on_open_project(file_path)

    def _show_import_midi_dialog(self):
        """Show file dialog for MIDI import."""
        if not dpg.does_item_exist("import_midi_dialog"):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self._handle_import_midi,
                tag="import_midi_dialog",
                width=700,
                height=400,
                default_path=str(Path.home() / "Documents")
            ):
                dpg.add_file_extension(".mid", color=(0, 255, 122, 255))
                dpg.add_file_extension(".midi", color=(0, 255, 122, 255))
                dpg.add_file_extension(".*")
        dpg.show_item("import_midi_dialog")

    def _handle_import_midi(self, sender, app_data):
        """Handle MIDI import file selection."""
        if app_data['selections']:
            file_path = list(app_data['selections'].values())[0]
            if self.on_import_midi:
                self.on_import_midi(file_path)

    def _show_export_midi_dialog(self):
        """Show file dialog for MIDI export."""
        if not dpg.does_item_exist("export_midi_dialog"):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self._handle_export_midi,
                tag="export_midi_dialog",
                width=700,
                height=400,
                default_path=str(Path.home() / "Documents")
            ):
                dpg.add_file_extension(".mid", color=(122, 122, 255, 255))
                dpg.add_file_extension(".*")
        dpg.show_item("export_midi_dialog")

    def _handle_export_midi(self, sender, app_data):
        """Handle MIDI export file selection."""
        if app_data['selections']:
            file_path = list(app_data['selections'].values())[0]
            if self.on_export_midi:
                self.on_export_midi(file_path)

    def show(self):
        """Show the landing page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.show_item(self._window_tag)

    def hide(self):
        """Hide the landing page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.hide_item(self._window_tag)

    def destroy(self):
        """Destroy the landing page window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.delete_item(self._window_tag)
