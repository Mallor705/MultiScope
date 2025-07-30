import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")  # Import Adw
from gi.repository import Gtk, Adw, Gdk # Adicionado Adw e Gdk
from pathlib import Path
import json
from ..services.device_manager import DeviceManager
from ..models.profile import GameProfile, PlayerInstanceConfig, SplitscreenConfig
from ..services.proton import ProtonService
from ..core.logger import Logger
from ..core.config import Config
from .styles import initialize_styles, get_style_manager, StyleManagerError
from typing import Dict, List, Tuple, Any, Optional
import subprocess
import os # Import os for process management (killpg, getpgid)
import signal # Import signal for process termination
import time # Import time for busy-wait in _stop_game
import cairo # Import cairo here for drawing
import sys # Import sys for executable path
from gi.repository import GLib # Import GLib for timeout_add

class ProfileEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Linux Coop Profile Editor")
        self.set_default_size(1200, 700) # Increased default width for side pane

        # Create the main vertical box which will hold the main content (paned), buttons, and statusbar
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_vbox) # Changed from self.add(main_vbox)

        # Create a horizontal Paned widget for the side menu and main content
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_vbox.append(self.main_paned) # Changed from pack_start



        # Left Pane: Profile List with Add Button
        # Create a vertical container for the sidebar
        self.sidebar_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.sidebar_vbox.set_size_request(200, -1) # Set a minimum width for the side pane
        self.main_paned.set_start_child(self.sidebar_vbox)

        # Profile list with scrolled window
        self.profile_list_scrolled_window = Gtk.ScrolledWindow()
        self.profile_list_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.profile_list_scrolled_window.set_vexpand(True)  # Expand to fill available space
        self.sidebar_vbox.append(self.profile_list_scrolled_window)

        self.profile_listbox = Gtk.ListBox()
        self.profile_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.profile_listbox.connect("row-activated", self._on_profile_selected_from_list)
        self.profile_list_scrolled_window.set_child(self.profile_listbox)

        # Buttons container
        self.buttons_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.buttons_hbox.set_margin_start(8)
        self.buttons_hbox.set_margin_end(8)
        self.buttons_hbox.set_margin_bottom(8)
        self.buttons_hbox.set_margin_top(8)
        self.sidebar_vbox.append(self.buttons_hbox)

        # Add Profile Button
        self.add_profile_button = Gtk.Button(label="🎮 Add New Profile")
        self.add_profile_button.set_hexpand(True)  # Take most of the space
        self.add_profile_button.add_css_class("suggested-action")  # Makes it blue/prominent
        self.add_profile_button.set_tooltip_text("Create a new game profile with default settings")
        self.add_profile_button.connect("clicked", self._on_add_profile_clicked)
        self.buttons_hbox.append(self.add_profile_button)

        # Delete Profile Button (initially hidden)
        self.delete_profile_button = Gtk.Button(label="🗑️")
        self.delete_profile_button.set_size_request(40, -1)  # Small fixed width
        self.delete_profile_button.add_css_class("destructive-action")  # Makes it red
        self.delete_profile_button.set_tooltip_text("Delete selected profile")
        self.delete_profile_button.connect("clicked", self._on_delete_profile_clicked)
        self.delete_profile_button.set_visible(False)  # Hidden by default
        self.buttons_hbox.append(self.delete_profile_button)

        # Track selected profile
        self.selected_profile_name = None

        # Right Pane: Container with Notebook and Fixed Buttons
        right_pane_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_pane_vbox.set_vexpand(True)
        right_pane_vbox.set_hexpand(True)
        self.main_paned.set_end_child(right_pane_vbox)

        # Notebook with tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)
        self.notebook.set_hexpand(True)
        right_pane_vbox.append(self.notebook)

        # Fixed buttons section at the bottom of right pane
        button_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        right_pane_vbox.append(button_separator)

        button_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_container.set_halign(Gtk.Align.END) # Align buttons to the right
        button_container.set_margin_start(10)
        button_container.set_margin_end(10)
        button_container.set_margin_top(10)
        button_container.set_margin_bottom(10)
        right_pane_vbox.append(button_container)

        # Create the fixed buttons
        load_button = Gtk.Button(label="Load Profile")
        load_button.connect("clicked", self.on_load_button_clicked)
        button_container.append(load_button)

        save_button = Gtk.Button(label="Save Profile")
        save_button.connect("clicked", self.on_save_button_clicked)
        button_container.append(save_button)

        # Make play_button an instance variable
        self.play_button = Gtk.Button(label="▶️ Launch Game")
        # Connect to a general handler that will decide to launch or stop
        self.play_button.connect("clicked", self.on_play_button_clicked)
        button_container.append(self.play_button)

        # Initialize configuration widgets early
        self.num_players_spin = Gtk.SpinButton.new_with_range(1, 4, 1)
        self.num_players_spin.set_value(1) # Default value
        self.instance_width_spin = Gtk.SpinButton.new_with_range(640, 3840, 1)
        self.instance_width_spin.set_value(1920) # Default from example.json
        self.instance_height_spin = Gtk.SpinButton.new_with_range(480, 2160, 1)
        self.instance_height_spin.set_value(1080) # Default from example.json

        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("None", "None")
        self.mode_combo.append("splitscreen", "splitscreen")
        self.mode_combo.set_active(0) # Default to None

        self.splitscreen_orientation_label = Gtk.Label(label="Splitscreen Orientation:", xalign=0)
        self.splitscreen_orientation_combo = Gtk.ComboBoxText()
        self.splitscreen_orientation_combo.append("horizontal", "horizontal")
        self.splitscreen_orientation_combo.append("vertical", "vertical")
        self.splitscreen_orientation_combo.set_active(0) # Default to horizontal

        self.device_manager = DeviceManager()
        self.detected_input_devices = self.device_manager.get_input_devices()
        self.detected_audio_devices = self.device_manager.get_audio_devices()
        self.detected_display_outputs = self.device_manager.get_display_outputs() # Adicionado para seleção de monitor

        self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs")) # Moved logger initialization here
        self.proton_service = ProtonService(self.logger)

        # Mappings for device names to IDs and vice-versa
        self.device_name_to_id = {"None": None}
        self.device_id_to_name = {None: "None"}

        for device_type in ["joystick", "mouse", "keyboard"]:
            for device in self.detected_input_devices.get(device_type, []):
                self.device_name_to_id[device["name"]] = device["id"]
                self.device_id_to_name[device["id"]] = device["name"]

        for device in self.detected_audio_devices:
            self.device_name_to_id[device["name"]] = device["id"]
            self.device_id_to_name[device["id"]] = device["name"]

        for device in self.detected_display_outputs:
            self.device_name_to_id[device["name"]] = device["id"]
            self.device_id_to_name[device["id"]] = device["name"]

        # Debug logs for mappings
        self.logger.info(f"DEBUG: device_name_to_id: {self.device_name_to_id}")
        self.logger.info(f"DEBUG: device_id_to_name: {self.device_id_to_name}")

        # Initialize player config entries list
        # self.player_config_entries = [] # REMOVED: This is no longer used
        self.player_checkboxes = []

        # Atributo para controlar o processo do jogo
        self.cli_process_pid = None
        self.monitoring_timeout_id = None # Para controlar o timeout do monitoramento

        # Tab 1: General Settings
        self.general_settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.general_settings_page.set_vexpand(True)
        self.general_settings_page.set_hexpand(True)
        self.notebook.append_page(self.general_settings_page, Gtk.Label(label="General Settings"))

        # Create a ScrolledWindow for general settings
        general_scrolled_window = Gtk.ScrolledWindow()
        general_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        general_scrolled_window.set_vexpand(True)
        general_scrolled_window.set_hexpand(True)
        self.general_settings_page.append(general_scrolled_window)

        # Create a container for the general settings content
        self.general_settings_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.general_settings_container.set_vexpand(True)
        self.general_settings_container.set_hexpand(True)
        general_scrolled_window.set_child(self.general_settings_container)

        self.setup_general_settings() # Call setup_general_settings here

        # Tab 2: Player Configurations
        self.player_configs_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.player_configs_page.set_vexpand(True)
        self.player_configs_page.set_hexpand(True)
        self.notebook.append_page(self.player_configs_page, Gtk.Label(label="Player Configurations"))

        # Create a ScrolledWindow for player configurations
        player_scrolled_window = Gtk.ScrolledWindow()
        player_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        player_scrolled_window.set_vexpand(True)
        player_scrolled_window.set_hexpand(True)
        self.player_configs_page.append(player_scrolled_window) # Changed from pack_start

        # Create a Viewport for the player configurations content (Gtk.Viewport is deprecated in Gtk4)
        self.player_config_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.player_config_vbox.set_vexpand(True)
        self.player_config_vbox.set_hexpand(True)
        player_scrolled_window.set_child(self.player_config_vbox) # Changed from player_viewport.add

        self.setup_player_configs()

        # Tab 3: Window Layout Preview
        self.window_layout_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window_layout_page.set_vexpand(True)
        self.window_layout_page.set_hexpand(True)
        self.notebook.append_page(self.window_layout_page, Gtk.Label(label="Window Layout Preview"))

        # Add a grid for layout settings in the preview tab
        self.preview_settings_grid = Gtk.Grid()
        self.preview_settings_grid.set_column_spacing(10)
        self.preview_settings_grid.set_row_spacing(10)
        self.preview_settings_grid.set_margin_start(5) # Changed from set_border_width
        self.preview_settings_grid.set_margin_end(5)   # Changed from set_border_width
        self.preview_settings_grid.set_margin_top(5)   # Changed from set_border_width
        self.preview_settings_grid.set_margin_bottom(5) # Changed from set_border_width
        self.preview_settings_grid.set_hexpand(False)
        self.window_layout_page.append(self.preview_settings_grid) # Changed from pack_start

        # Num Players
        preview_row = 0
        self.preview_settings_grid.attach(Gtk.Label(label="Number of Players:", xalign=0), 0, preview_row, 1, 1)
        self.preview_settings_grid.attach(self.num_players_spin, 1, preview_row, 1, 1)
        preview_row += 1

        # Instance Width
        self.preview_settings_grid.attach(Gtk.Label(label="Instance Width:", xalign=0), 0, preview_row, 1, 1)
        self.preview_settings_grid.attach(self.instance_width_spin, 1, preview_row, 1, 1)
        preview_row += 1

        # Instance Height
        self.preview_settings_grid.attach(Gtk.Label(label="Instance Height:", xalign=0), 0, preview_row, 1, 1)
        self.preview_settings_grid.attach(self.instance_height_spin, 1, preview_row, 1, 1)
        preview_row += 1

        # Mode (splitscreen or not)
        self.preview_settings_grid.attach(Gtk.Label(label="Mode:", xalign=0), 0, preview_row, 1, 1)
        self.preview_settings_grid.attach(self.mode_combo, 1, preview_row, 1, 1)
        preview_row += 1

        # Splitscreen Orientation
        self.preview_settings_grid.attach(self.splitscreen_orientation_label, 0, preview_row, 1, 1)
        self.preview_settings_grid.attach(self.splitscreen_orientation_combo, 1, preview_row, 1, 1)
        self.splitscreen_orientation_label.hide()
        self.splitscreen_orientation_combo.hide()
        preview_row += 1

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.on_draw_window_layout) # Changed from connect("draw", ...)
        self.drawing_area.set_hexpand(True) # Ensure drawing area expands horizontally
        self.drawing_area.set_vexpand(True) # Ensure drawing area expands vertically
        self.drawing_area.set_size_request(200, 200) # Set minimum size for drawing area
        self.window_layout_page.append(self.drawing_area) # Changed from pack_start

        # Connect signals for redraw
        self.instance_width_spin.connect("value-changed", self.on_layout_setting_changed)
        self.instance_height_spin.connect("value-changed", self.on_layout_setting_changed)
        self.num_players_spin.connect("value-changed", self.on_layout_setting_changed)
        self.mode_combo.connect("changed", self.on_layout_setting_changed)
        self.splitscreen_orientation_combo.connect("changed", self.on_layout_setting_changed)

        # Connect mode combo to its specific handler for visibility
        self.mode_combo.connect("changed", self.on_mode_changed)

        # Connect num_players_spin to its specific handler for player config UI update
        self.num_players_spin.connect("value-changed", self.on_num_players_changed)

        # Add a Statusbar at the bottom (Gtk.Statusbar is deprecated in Gtk4)
        self.statusbar = Gtk.Label() # Using a Label as a simple statusbar replacement
        self.statusbar.set_halign(Gtk.Align.START)
        self.statusbar.set_margin_start(10)
        self.statusbar.set_margin_end(10)
        self.statusbar.set_margin_top(5)
        self.statusbar.set_margin_bottom(5)
        main_vbox.append(self.statusbar) # Changed from pack_end

        self.show() # Changed from show_all()
        self._update_play_button_state() # Set initial button state
        self._populate_profile_list() # Populate the side profile list on startup

    def setup_general_settings(self):
        # Use a main VBox for this page to hold frames
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_vbox.set_margin_start(5)
        main_vbox.set_margin_end(5)
        main_vbox.set_margin_top(5)
        main_vbox.set_margin_bottom(5)
        main_vbox.set_vexpand(True)
        main_vbox.set_hexpand(True)
        self.general_settings_container.append(main_vbox) # Changed to use scrolled container


        # Frame 1: Game Details
        game_details_frame = Gtk.Frame(label="Game Details")
        main_vbox.append(game_details_frame) # Changed from pack_start

        game_details_grid = Gtk.Grid()
        game_details_grid.set_column_spacing(10)
        game_details_grid.set_row_spacing(10)
        game_details_grid.set_margin_start(5) # Changed from set_border_width
        game_details_grid.set_margin_end(5)   # Changed from set_border_width
        game_details_grid.set_margin_top(5)   # Changed from set_border_width
        game_details_grid.set_margin_bottom(5) # Changed from set_border_width
        game_details_frame.set_child(game_details_grid) # Changed from add

        row = 0

        # Game Name
        game_details_grid.attach(Gtk.Label(label="Game Name:", xalign=0), 0, row, 1, 1)
        self.game_name_entry = Gtk.Entry()
        self.game_name_entry.set_placeholder_text("Ex: Palworld")
        game_details_grid.attach(self.game_name_entry, 1, row, 1, 1)
        row += 1

        # Executable Path
        game_details_grid.attach(Gtk.Label(label="Executable Path:", xalign=0), 0, row, 1, 1)

        exe_path_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.exe_path_entry = Gtk.Entry()
        self.exe_path_entry.set_hexpand(True)
        self.exe_path_entry.set_placeholder_text("Ex: ~/.steam/steamapps/common/Palworld/Palworld.exe")
        exe_path_hbox.append(self.exe_path_entry) # Changed from pack_start

        exe_path_button = Gtk.Button(label="Browse...")
        exe_path_button.connect("clicked", self.on_exe_path_button_clicked)
        exe_path_hbox.append(exe_path_button) # Changed from pack_start

        game_details_grid.attach(exe_path_hbox, 1, row, 1, 1)
        row += 1

        # App ID
        game_details_grid.attach(Gtk.Label(label="App ID (Steam):", xalign=0), 0, row, 1, 1)
        self.app_id_entry = Gtk.Entry()
        self.app_id_entry.set_placeholder_text("Optional (ex: 1621530)")
        game_details_grid.attach(self.app_id_entry, 1, row, 1, 1)
        row += 1

        # Game Arguments
        game_details_grid.attach(Gtk.Label(label="Game Arguments:", xalign=0), 0, row, 1, 1)
        self.game_args_entry = Gtk.Entry()
        self.game_args_entry.set_placeholder_text("Optional (ex: -EpicPortal)")
        game_details_grid.attach(self.game_args_entry, 1, row, 1, 1)
        row += 1

        # Is Native Checkbox
        game_details_grid.attach(Gtk.Label(label="Is Native Game (Linux)?", xalign=0), 0, row, 1, 1)
        self.is_native_check = Gtk.CheckButton()
        self.is_native_check.set_active(False) # Most games will be Windows
        game_details_grid.attach(self.is_native_check, 1, row, 1, 1)
        row += 1

        # Frame 2: Proton & Launch Options
        proton_options_frame = Gtk.Frame(label="Proton & Launch Options")
        main_vbox.append(proton_options_frame) # Changed from pack_start

        proton_options_grid = Gtk.Grid()
        proton_options_grid.set_column_spacing(10)
        proton_options_grid.set_row_spacing(10)
        proton_options_grid.set_margin_start(5) # Changed from set_border_width
        proton_options_grid.set_margin_end(5)   # Changed from set_border_width
        proton_options_grid.set_margin_top(5)   # Changed from set_border_width
        proton_options_grid.set_margin_bottom(5) # Changed from set_border_width
        proton_options_frame.set_child(proton_options_grid) # Changed from add

        row = 0 # Reset row counter for this grid

        # Proton Version
        proton_options_grid.attach(Gtk.Label(label="Proton Version:", xalign=0), 0, row, 1, 1)
        self.proton_version_combo = Gtk.ComboBoxText()
        proton_versions = self.proton_service.list_installed_proton_versions()
        if not proton_versions:
            self.proton_version_combo.append_text("No Proton versions found")
            self.proton_version_combo.set_sensitive(False)
        else:
            self.proton_version_combo.append_text("None (Use Steam default)")
            for version in proton_versions:
                self.proton_version_combo.append_text(version)
            self.proton_version_combo.set_active(0)

        proton_options_grid.attach(self.proton_version_combo, 1, row, 1, 1)
        row += 1

        # Environment Variables
        env_vars_frame = Gtk.Frame(label="Custom Environment Variables")
        main_vbox.append(env_vars_frame) # Changed from pack_start

        env_vars_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        env_vars_vbox.set_margin_start(5) # Changed from set_border_width
        env_vars_vbox.set_margin_end(5)   # Changed from set_border_width
        env_vars_vbox.set_margin_top(5)   # Changed from set_border_width
        env_vars_vbox.set_margin_bottom(5) # Changed from set_border_width
        env_vars_frame.set_child(env_vars_vbox) # Changed from add

        self.env_vars_listbox = Gtk.ListBox()
        self.env_vars_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        env_vars_vbox.append(self.env_vars_listbox) # Changed from pack_start
        self.env_var_entries = []

        self._add_env_var_row("WINEDLLOVERRIDES", "")
        self._add_env_var_row("MANGOHUD", "1")

        add_env_var_button = Gtk.Button(label="Add Variable")
        add_env_var_button.connect("clicked", self._on_add_env_var_clicked)
        env_vars_vbox.append(add_env_var_button) # Changed from pack_start

        # Buttons are now fixed at the bottom of the main window, so they're removed from this tab

    # Add _update_play_button_state method
    def _update_play_button_state(self):
        if self.cli_process_pid:
            self.play_button.set_label("⏹️ Stop Gaming")
            self.play_button.set_css_classes(["destructive-action"]) # Gtk4 CSS class
        else:
            self.play_button.set_label("▶️ Launch Game")
            self.play_button.set_css_classes(["suggested-action"]) # Gtk4 CSS class
        self.play_button.set_sensitive(True) # Ensure button is always sensitive initially

    def on_exe_path_button_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Game Executable",
            action=Gtk.FileChooserAction.OPEN
        )

        # Set parent after creation for GTK4 compatibility
        dialog.set_transient_for(self)
        dialog.set_modal(True)

        # Add buttons manually for GTK4 compatibility
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Open", Gtk.ResponseType.OK)

        dialog.connect("response", self._on_exe_path_dialog_response)
        dialog.present()

    def _on_exe_path_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                self.exe_path_entry.set_text(file.get_path())
        dialog.destroy()
        self.statusbar.set_label("Executable path selected.") # Changed from push

    def on_load_button_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Load Game Profile",
            action=Gtk.FileChooserAction.OPEN
        )

        # Set parent after creation for GTK4 compatibility
        dialog.set_transient_for(self)
        dialog.set_modal(True)

        # Add buttons manually for GTK4 compatibility
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Open", Gtk.ResponseType.OK)

        try:
            Config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            # Use Gio.File for GTK4 compatibility
            from gi.repository import Gio
            folder = Gio.File.new_for_path(str(Config.PROFILE_DIR))
            dialog.set_current_folder(folder)
        except Exception as e:
            self.logger.warning(f"Could not set initial folder for profile loading: {e}")

        dialog.connect("response", self._on_load_dialog_response)
        dialog.present()

    def _on_load_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                file_path = Path(file.get_path())
                try:
                    profile = GameProfile.load_from_file(file_path)
                    self.load_profile_data(profile.model_dump(by_alias=True)) # Use model_dump to convert to dict
                    self.logger.info(f"Profile loaded successfully from {file_path}")
                    self.statusbar.set_label(f"Profile loaded: {file_path.name}") # Changed from push
                    # Select the loaded profile in the listbox by its filename stem
                    self._select_profile_in_list(file_path.stem)
                except Exception as e:
                    self.logger.error(f"Failed to load profile: {e}")
                    self.statusbar.set_label(f"Error loading profile: {e}") # Changed from push
                    # Create an error dialog using Adw.MessageDialog (Gtk4)
                    error_dialog = Adw.MessageDialog(
                        heading="Profile Load Error",
                        body=f"Error loading profile:\n{e}",
                        modal=True,
                    )
                    error_dialog.add_response("ok", "Ok")
                    error_dialog.set_response_enabled("ok", True)
                    error_dialog.set_default_response("ok")
                    error_dialog.set_transient_for(self)
                    error_dialog.connect("response", lambda d, r: d.close())
                    error_dialog.present() # Show the dialog
        dialog.destroy()

    def _on_add_env_var_clicked(self, button):
        self._add_env_var_row()
        self.statusbar.set_label("Environment variable added.") # Changed from push

    def _add_env_var_row(self, key="", value=""):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        key_entry = Gtk.Entry()
        key_entry.set_placeholder_text("Variable Name")
        key_entry.set_hexpand(True)
        key_entry.set_text(key)
        hbox.append(key_entry) # Changed from pack_start

        value_entry = Gtk.Entry()
        value_entry.set_placeholder_text("Value")
        value_entry.set_hexpand(True)
        value_entry.set_text(value)
        hbox.append(value_entry) # Changed from pack_start

        remove_button = Gtk.Button(label="-")
        # remove_button.set_relief(Gtk.ReliefStyle.NONE) # set_relief is Gtk3 only
        remove_button.set_tooltip_text("Remove this environment variable")

        list_box_row = Gtk.ListBoxRow()
        list_box_row.set_child(hbox) # Changed from add

        remove_button.connect("clicked", lambda btn, row=list_box_row, k_entry=key_entry, v_entry=value_entry: self._remove_env_var_row(btn, row, k_entry, v_entry))
        hbox.append(remove_button) # Changed from pack_end

        self.env_vars_listbox.append(list_box_row) # Changed from add
        list_box_row.show() # Explicitly show the row for Gtk4 ListBox
        self.env_var_entries.append((key_entry, value_entry, list_box_row))

    def _remove_env_var_row(self, button, row, key_entry, value_entry):
        self.env_vars_listbox.remove(row)
        self.env_var_entries.remove((key_entry, value_entry, row))
        self.statusbar.set_label("Environment variable removed.") # Changed from push

    def _get_env_vars_from_ui(self) -> Dict[str, str]:
        env_vars = {}
        for row_data in self.env_var_entries:
            key = row_data[0].get_text().strip()
            value = row_data[1].get_text().strip()
            if key:
                env_vars[key] = value
        return env_vars

    def _get_player_configs_from_ui(self) -> List[Dict[str, Any]]:
        player_configs_data = []
        for i, (is_enabled_checkbox, player_widgets) in enumerate(zip(self.player_checkboxes, self.player_device_combos)):
            config = {}
            # Iterate through the entry widgets and collect data
            # No need to iterate self.player_config_entries, it's not structured for this anymore
            # Instead, use the player_widgets directly
            for key, widget in player_widgets.items(): # key will now be UPPER_SNAKE_CASE
                if isinstance(widget, Gtk.Entry):
                    value = widget.get_text().strip()
                    config[key] = value if value != "" else None # Convert empty string to None if applicable
                elif isinstance(widget, Gtk.DropDown): # Gtk.DropDown for device selection
                    selected_item = widget.get_selected_item()
                    selected_name = selected_item.get_string() if selected_item else "None"

                    self.logger.info(f"DEBUG: Player config: Selected name for {key}: '{selected_name}'")

                    # Convert name back to ID using the mapping
                    device_id = self.device_name_to_id.get(selected_name, None)
                    self.logger.info(f"DEBUG: Player config: Resolved ID for {key} ('{selected_name}'): '{device_id}'")
                    config[key] = device_id
                else:
                    config[key] = "" # Default empty string for other widget types if any
            player_configs_data.append(config)
        self.logger.info(f"DEBUG: Collected player configurations data: {player_configs_data}")
        return player_configs_data

    def setup_player_configs(self):
        self.player_frames = []
        self.player_device_combos = []

        self._create_player_config_uis(self.num_players_spin.get_value_as_int())

    def _create_player_config_uis(self, num_players: int):
        for frame in self.player_frames:
            frame.unparent() # Changed from destroy()
        self.player_frames.clear()
        self.player_device_combos.clear()
        self.player_checkboxes.clear()

        # In Gtk4, Gtk.Box.get_children() is removed. Remove children one by one.
        while self.player_config_vbox.get_first_child():
            self.player_config_vbox.remove(self.player_config_vbox.get_first_child())

        for i in range(num_players):
            player_frame = Gtk.Frame(label=f"Player {i+1} Configuration")
            player_frame.set_margin_top(10) # Changed from set_shadow_type
            player_frame.set_margin_bottom(10) # Added margin
            player_frame.set_margin_start(10) # Added margin
            player_frame.set_margin_end(10) # Added margin
            self.player_config_vbox.append(player_frame) # Changed from pack_start
            player_frame.show() # Explicitly show the frame
            self.player_frames.append(player_frame)

            player_grid = Gtk.Grid()
            player_grid.set_column_spacing(10)
            player_grid.set_row_spacing(10)
            player_grid.set_margin_start(10) # Changed from set_border_width
            player_grid.set_margin_end(10)   # Changed from set_border_width
            player_grid.set_margin_top(10)   # Changed from set_border_width
            player_grid.set_margin_bottom(10) # Changed from set_border_width
            player_frame.set_child(player_grid) # Changed from add
            player_grid.show() # Explicitly show the grid

            player_combos = {
                "ACCOUNT_NAME": Gtk.Entry(),
                "LANGUAGE": Gtk.Entry(),
                "LISTEN_PORT": Gtk.Entry(),
                "USER_STEAM_ID": Gtk.Entry(),
                "PHYSICAL_DEVICE_ID": Gtk.DropDown.new_from_strings(self._create_device_list_store(self.detected_input_devices["joystick"])) , # Changed to Gtk.DropDown.new_from_strings
                "MOUSE_EVENT_PATH": Gtk.DropDown.new_from_strings(self._create_device_list_store(self.detected_input_devices["mouse"])) , # Changed to Gtk.DropDown.new_from_strings
                "KEYBOARD_EVENT_PATH": Gtk.DropDown.new_from_strings(self._create_device_list_store(self.detected_input_devices["keyboard"])) , # Changed to Gtk.DropDown.new_from_strings
                "AUDIO_DEVICE_ID": Gtk.DropDown.new_from_strings(self._create_device_list_store(self.detected_audio_devices)) , # Changed to Gtk.DropDown.new_from_strings
                "MONITOR_ID": Gtk.DropDown.new_from_strings(self._create_device_list_store(self.detected_display_outputs)) , # Changed to Gtk.DropDown.new_from_strings
            }
            self.player_device_combos.append(player_combos)

            p_row = 0

            check_button = Gtk.CheckButton(label=f"Enable Player {i + 1}")
            check_button.set_active(True)
            self.player_checkboxes.append(check_button)
            player_grid.attach(check_button, 0, p_row, 2, 1)
            check_button.show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Account Name:", xalign=0), 0, p_row, 1, 1)
            player_combos["ACCOUNT_NAME"].set_placeholder_text(f"Player {i+1}")
            player_grid.attach(player_combos["ACCOUNT_NAME"], 1, p_row, 1, 1)
            player_combos["ACCOUNT_NAME"].show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Language:", xalign=0), 0, p_row, 1, 1)
            player_combos["LANGUAGE"].set_placeholder_text("Ex: brazilian, english")
            player_grid.attach(player_combos["LANGUAGE"], 1, p_row, 1, 1)
            player_combos["LANGUAGE"].show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Listen Port (Goldberg):", xalign=0), 0, p_row, 1, 1)
            player_combos["LISTEN_PORT"].set_placeholder_text("Optional")
            player_grid.attach(player_combos["LISTEN_PORT"], 1, p_row, 1, 1)
            player_combos["LISTEN_PORT"].show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="User Steam ID:", xalign=0), 0, p_row, 1, 1)
            player_combos["USER_STEAM_ID"].set_placeholder_text("Optional (ex: 7656119...)")
            player_grid.attach(player_combos["USER_STEAM_ID"], 1, p_row, 1, 1)
            player_combos["USER_STEAM_ID"].show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Joystick Device:", xalign=0), 0, p_row, 1, 1)
            physical_device_id_combo = player_combos["PHYSICAL_DEVICE_ID"]
            # Removed Gtk.CellRendererText and pack_start/add_attribute for Gtk4 Gtk.DropDown
            physical_device_id_combo.set_selected(0) # Select "None" by default
            player_grid.attach(physical_device_id_combo, 1, p_row, 1, 1)
            physical_device_id_combo.show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Mouse Device:", xalign=0), 0, p_row, 1, 1)
            mouse_event_path_combo = player_combos["MOUSE_EVENT_PATH"]
            # Removed Gtk.CellRendererText and pack_start/add_attribute for Gtk4 Gtk.DropDown
            mouse_event_path_combo.set_selected(0) # Select "None" by default
            player_grid.attach(mouse_event_path_combo, 1, p_row, 1, 1)
            mouse_event_path_combo.show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Keyboard Device:", xalign=0), 0, p_row, 1, 1)
            keyboard_event_path_combo = player_combos["KEYBOARD_EVENT_PATH"]
            # Removed Gtk.CellRendererText and pack_start/add_attribute for Gtk4 Gtk.DropDown
            keyboard_event_path_combo.set_selected(0) # Select "None" by default
            player_grid.attach(keyboard_event_path_combo, 1, p_row, 1, 1)
            keyboard_event_path_combo.show()
            p_row += 1

            player_grid.attach(Gtk.Label(label="Audio Device:", xalign=0), 0, p_row, 1, 1)
            audio_device_id_combo = player_combos["AUDIO_DEVICE_ID"]
            # Removed Gtk.CellRendererText and pack_start/add_attribute for Gtk4 Gtk.DropDown
            audio_device_id_combo.set_selected(0) # Select "None" by default
            player_grid.attach(audio_device_id_combo, 1, p_row, 1, 1)
            audio_device_id_combo.show()
            p_row += 1

            # Monitor Selection
            player_grid.attach(Gtk.Label(label="Monitor:", xalign=0), 0, p_row, 1, 1)
            monitor_combo = player_combos["MONITOR_ID"]
            # Removed Gtk.CellRendererText and pack_start/add_attribute for Gtk4 Gtk.DropDown
            monitor_combo.set_selected(0) # Select "None" by default
            player_grid.attach(monitor_combo, 1, p_row, 1, 1)
            monitor_combo.show()
            p_row += 1

        # self.player_config_vbox.show_all() # Not needed for Gtk4
        self.logger.info(f"DEBUG: Created {len(self.player_frames)} player config UIs.")
        self.player_config_vbox.queue_draw() # Force redraw after creating UIs

    def on_num_players_changed(self, spin_button):
        num_players = spin_button.get_value_as_int()
        # self._create_player_config_uis(num_players) # REMOVED: This causes redundant UI recreation
        self.statusbar.set_label(f"Number of players changed to {num_players}.") # Changed from push

    def on_mode_changed(self, combo):
        mode = combo.get_active_text()
        if mode == "splitscreen":
            self.splitscreen_orientation_label.show()
            self.splitscreen_orientation_combo.show()
            # REMOVED: self.primary_monitor_label.hide()
            # REMOVED: self.primary_monitor_entry.hide()
            self.statusbar.set_label("Splitscreen mode activated.") # Changed from push
        else:
            self.splitscreen_orientation_label.hide()
            self.splitscreen_orientation_combo.hide()
            # REMOVED: self.primary_monitor_label.show()
            # REMOVED: self.primary_monitor_entry.show()
            self.statusbar.set_label("Splitscreen mode deactivated.") # Changed from push

    def on_save_button_clicked(self, button):
        self.statusbar.set_label("Saving profile...") # Changed from push
        profile_data_dumped = self.get_profile_data()

        # Collect selected players based on checkbox states
        selected_players_indices = [i + 1 for i, cb in enumerate(self.player_checkboxes) if cb.get_active()]
        profile_data_dumped['selected_players'] = selected_players_indices

        profile_name = self.game_name_entry.get_text().replace(" ", "_").lower()
        if not profile_name:
            dialog = Adw.MessageDialog(
                heading="Save Error",
                body="Game name cannot be empty.",
                modal=True,
            )
            dialog.add_response("ok", "Ok")
            dialog.set_response_enabled("ok", True)
            dialog.set_default_response("ok")
            dialog.set_transient_for(self)
            dialog.connect("response", lambda d, r: d.close())
            dialog.present()
            self.statusbar.set_label("Error: Game name is empty.") # Changed from push
            return

        profile_dir = Config.PROFILE_DIR
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir / f"{profile_name}.json"

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data_dumped, f, indent=2)
            self.statusbar.set_label(f"Profile saved successfully to: {profile_path.name}") # Changed from push

            # Invalidate the cache for this profile after saving
            from ..core.cache import get_cache # Import here to ensure it's available
            cache = get_cache()
            cache.invalidate_profile(str(profile_path))

            # Reload the just-saved profile to ensure GUI and cache are updated
            reloaded_profile = GameProfile.load_from_file(profile_path)
            self.load_profile_data(reloaded_profile.model_dump(by_alias=True))

            self._populate_profile_list() # Refresh the profile list after saving
            self._select_profile_in_list(profile_name) # Select the newly saved/updated profile
        except Exception as e:
            self.logger.error(f"Failed to save profile to {profile_path}: {e}")
            self.statusbar.set_label(f"Error saving profile: {e}") # Changed from push
            error_dialog = Adw.MessageDialog(
                heading="Error saving profile",
                body=f"Error saving profile:\n{e}",
                modal=True,
            )
            error_dialog.add_response("ok", "Ok")
            error_dialog.set_response_enabled("ok", True)
            error_dialog.set_default_response("ok")
            error_dialog.set_transient_for(self)
            error_dialog.connect("response", lambda d, r: d.close())
            error_dialog.present()

    def on_play_button_clicked(self, widget):
        if self.cli_process_pid:
            self._stop_game()
            return

        self.statusbar.set_label("Starting game...") # Changed from push
        self.on_save_button_clicked(widget) # Ensure profile is saved before playing

        profile_name = self.game_name_entry.get_text().replace(" ", "_").lower()
        if not profile_name:
            self.logger.error("Cannot launch game with an empty profile name.")
            self.statusbar.set_label("Error: Profile name empty. Game not launched.") # Changed from push
            return

        script_path = Path(__file__).parent.parent.parent / "linuxcoop.py"
        python_exec = sys.executable # Use o interpretador Python atual do ambiente virtual
        if not python_exec:
            self.statusbar.set_label("Error: Python interpreter not found.") # Changed from push
            dialog = Adw.MessageDialog(
                heading="Launch Error",
                body="No Python interpreter found on the system.",
                modal=True,
            )
            dialog.add_response("ok", "Ok")
            dialog.set_response_enabled("ok", True)
            dialog.set_default_response("ok")
            dialog.set_transient_for(self)
            dialog.connect("response", lambda d, r: d.close())
            dialog.present()
            return

        command = [python_exec, str(script_path), profile_name]
        self.logger.info(f"Executing command: {' '.join(command)}")

        self.play_button.set_sensitive(False)
        self.play_button.set_label("Iniciando...")

        try:
            # Launch the CLI script as a separate process group
            process = subprocess.Popen(command, preexec_fn=os.setsid)
            self.cli_process_pid = process.pid
            self.statusbar.set_label(f"Game '{profile_name}' launched successfully with PID: {self.cli_process_pid}.") # Changed from push
            self._update_play_button_state() # Update button to "Stop Gaming"
            # Start monitoring the process
            self.monitoring_timeout_id = GLib.timeout_add(1000, self._check_cli_process) # Corrigido para GLib.timeout_add
        except Exception as e:
            self.logger.error(f"Failed to launch game: {e}")
            self.statusbar.set_label(f"Error launching game: {e}") # Changed from push
            dialog = Adw.MessageDialog(
                heading="Launch Error",
                body=f"Error launching game:\n{e}",
                modal=True,
            )
            dialog.add_response("ok", "Ok")
            dialog.set_response_enabled("ok", True)
            dialog.set_default_response("ok")
            dialog.set_transient_for(self)
            dialog.connect("response", lambda d, r: d.close())
            dialog.present()
            self.cli_process_pid = None # Reset PID on error
            self._update_play_button_state() # Reset button to "Launch Game"

    # Add _stop_game method
    def _stop_game(self):
        if not self.cli_process_pid:
            self.statusbar.set_label("No game process to stop.") # Changed from push
            return

        self.statusbar.set_label("Stopping game...") # Changed from push
        self.play_button.set_sensitive(False)
        self.play_button.set_label("Parando...")

        try:
            # Terminate the process group
            os.killpg(os.getpgid(self.cli_process_pid), signal.SIGTERM)
            self.logger.info(f"Sent SIGTERM to process group {os.getpgid(self.cli_process_pid)}")

            # Give it a moment to terminate
            # Gtk.timeout_add(1000, self._check_cli_process_after_term, self.cli_process_pid)
            # More direct approach: busy-wait for a short period, then force kill if needed
            for _ in range(5): # Wait up to 5 seconds
                if not self._is_process_running(self.cli_process_pid):
                    break
                time.sleep(1)

            if self._is_process_running(self.cli_process_pid):
                os.killpg(os.getpgid(self.cli_process_pid), signal.SIGKILL)
                self.logger.warning(f"Sent SIGKILL to process group {os.getpgid(self.cli_process_pid)} as SIGTERM was not enough.")

        except ProcessLookupError:
            self.logger.info(f"Process {self.cli_process_pid} already terminated or not found.")
        except OSError as e:
            self.logger.error(f"Error terminating process group for PID {self.cli_process_pid}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while stopping the game: {e}")

        self.cli_process_pid = None
        if self.monitoring_timeout_id:
            GLib.source_remove(self.monitoring_timeout_id) # Stop monitoring
            self.monitoring_timeout_id = None
        self.statusbar.set_label("Game stopped.") # Changed from push
        self._update_play_button_state() # Reset button to "Launch Game"

    # Helper to check if a process is running
    def _is_process_running(self, pid):
        if pid is None:
            return False
        try:
            os.kill(pid, 0) # Check if process exists
            return True
        except OSError:
            return False

    # Add _check_cli_process for monitoring
    def _check_cli_process(self):
        if self.cli_process_pid and not self._is_process_running(self.cli_process_pid):
            self.logger.info(f"Detected CLI process {self.cli_process_pid} has terminated.")
            self.cli_process_pid = None
            self._update_play_button_state()
            self.statusbar.set_label("Game process terminated.") # Changed from push
            if self.monitoring_timeout_id:
                GLib.source_remove(self.monitoring_timeout_id)
                self.monitoring_timeout_id = None
            return False # Stop the timeout
        return True # Continue monitoring

    def on_layout_setting_changed(self, widget):
        self.drawing_area.queue_draw()

    def on_draw_window_layout(self, widget, cr, width, height):
        """Main entry point for drawing the window layout preview."""
        try:
            # Get configuration from UI
            layout_settings = self._get_layout_settings()

            # Validate the data
            if not self._validate_layout_data(layout_settings):
                return

            # Calculate drawing parameters
            drawing_params = self._calculate_drawing_parameters(width, height, layout_settings)

            # Create preview profile
            profile = self._create_preview_profile(layout_settings)
            if not profile:
                return

            # Setup cairo context
            cr.set_line_width(2)

            # Draw the appropriate layout
            if layout_settings['mode'] == "splitscreen" and layout_settings['num_players'] > 1:
                self._draw_splitscreen_layout(cr, profile, drawing_params, layout_settings)
            else:
                self._draw_fullscreen_layout(cr, profile, drawing_params)

        except Exception as e:
            self.logger.error(f"Error drawing window layout: {e}")

    def _get_layout_settings(self):
        """Extract layout settings from UI widgets."""
        return {
            'instance_width': self.instance_width_spin.get_value_as_int(),
            'instance_height': self.instance_height_spin.get_value_as_int(),
            'num_players': max(1, self.num_players_spin.get_value_as_int()),
            'mode': self.mode_combo.get_active_text(),
            'orientation': self.splitscreen_orientation_combo.get_active_text()
        }

    def _validate_layout_data(self, settings):
        """Validate layout settings."""
        return (settings['instance_width'] > 0 and
                settings['instance_height'] > 0 and
                settings['num_players'] >= 1)

    def _calculate_drawing_parameters(self, drawing_width, drawing_height, settings):
        """Calculate scale and offset parameters for drawing."""
        scale_w = drawing_width / settings['instance_width']
        scale_h = drawing_height / settings['instance_height']
        scale = min(scale_w, scale_h) * 0.9

        scaled_total_width = settings['instance_width'] * scale
        scaled_total_height = settings['instance_height'] * scale

        return {
            'scale': scale,
            'x_offset': (drawing_width - scaled_total_width) / 2,
            'y_offset': (drawing_height - scaled_total_height) / 2
        }

    def _create_preview_profile(self, settings):
        """Create a dummy profile for preview calculations."""
        try:
            dummy_player_configs = []
            for _ in range(settings['num_players']):
                dummy_player_configs.append(PlayerInstanceConfig())

            return GameProfile(
                GAME_NAME="Preview",
                EXE_PATH=None,
                NUM_PLAYERS=settings['num_players'],
                INSTANCE_WIDTH=settings['instance_width'],
                INSTANCE_HEIGHT=settings['instance_height'],
                MODE=settings['mode'],
                SPLITSCREEN=SplitscreenConfig(orientation=settings['orientation']) if settings['mode'] == "splitscreen" else None,
                player_configs=dummy_player_configs,
                PLAYER_PHYSICAL_DEVICE_IDS=[],
                PLAYER_MOUSE_EVENT_PATHS=[],
                PLAYER_KEYBOARD_EVENT_PATHS=[],
                PLAYER_AUDIO_DEVICE_IDS=[],
                is_native=False,
            )
        except Exception as e:
            self.logger.error(f"Error creating preview profile: {e}")
            return None

    def _draw_splitscreen_layout(self, cr, profile, drawing_params, settings):
        """Draw splitscreen layout for multiple players."""
        for i in range(settings['num_players']):
            instance_w, instance_h = profile.get_instance_dimensions(i + 1)
            draw_w = instance_w * drawing_params['scale']
            draw_h = instance_h * drawing_params['scale']

            pos_x, pos_y = self._calculate_player_position(
                i, settings['num_players'], settings['orientation'],
                draw_w, draw_h, profile, drawing_params['scale']
            )

            self._draw_player_window(
                cr, i + 1, pos_x, pos_y, draw_w, draw_h,
                drawing_params['x_offset'], drawing_params['y_offset'],
                profile
            )

    def _draw_fullscreen_layout(self, cr, profile, drawing_params):
        """Draw fullscreen layout for single player."""
        instance_w, instance_h = profile.get_instance_dimensions(1)
        draw_w = instance_w * drawing_params['scale']
        draw_h = instance_h * drawing_params['scale']

        self._draw_player_window(
            cr, 1, 0, 0, draw_w, draw_h,
            drawing_params['x_offset'], drawing_params['y_offset'],
            profile
        )

    def _calculate_player_position(self, player_index, num_players, orientation, draw_w, draw_h, profile, scale):
        """Calculate the position for a specific player window."""
        pos_x, pos_y = 0.0, 0.0

        if num_players == 2:
            if orientation == "horizontal":
                pos_x = player_index * draw_w
            else:  # vertical
                pos_y = player_index * draw_h
        elif num_players == 3:
            pos_x, pos_y = self._calculate_three_player_position(
                player_index, orientation, profile, scale
            )
        elif num_players == 4:
            # 2x2 grid
            row = player_index // 2
            col = player_index % 2
            pos_x = col * draw_w
            pos_y = row * draw_h
        else:  # Generic case for more than 4 players
            if orientation == "horizontal":  # Stacked vertically
                pos_y = player_index * draw_h
            else:  # vertical (Side by side)
                pos_x = player_index * draw_w

        return pos_x, pos_y

    def _calculate_three_player_position(self, player_index, orientation, profile, scale):
        """Calculate position for 3-player splitscreen layout."""
        p1_unscaled_w, p1_unscaled_h = profile.get_instance_dimensions(1)
        p2_unscaled_w, p2_unscaled_h = profile.get_instance_dimensions(2)

        p1_draw_w, p1_draw_h = p1_unscaled_w * scale, p1_unscaled_h * scale
        p2_draw_w, p2_draw_h = p2_unscaled_w * scale, p2_unscaled_h * scale

        if orientation == "horizontal":  # 1 large top, 2 small bottom
            if player_index == 0:  # Player 1 (top)
                return 0, 0
            elif player_index == 1:  # Player 2 (bottom-left)
                return 0, p1_draw_h
            elif player_index == 2:  # Player 3 (bottom-right)
                return p2_draw_w, p1_draw_h
        else:  # vertical: 1 large left, 2 small right
            if player_index == 0:  # Player 1 (left)
                return 0, 0
            elif player_index == 1:  # Player 2 (top-right)
                return p1_draw_w, 0
            elif player_index == 2:  # Player 3 (bottom-right)
                return p1_draw_w, p2_draw_h

        return 0, 0

    def _draw_player_window(self, cr, player_num, pos_x, pos_y, width, height, x_offset, y_offset, profile):
        """Draw a single player window with text and monitor info."""
        # Draw window rectangle
        cr.rectangle(x_offset + pos_x, y_offset + pos_y, width, height)
        cr.set_source_rgb(1.0, 1.0, 1.0)  # White border
        cr.stroke()

        # Draw player text
        self._draw_player_text(cr, player_num, pos_x, pos_y, width, height, x_offset, y_offset)

        # Draw monitor info
        self._draw_monitor_info(cr, player_num - 1, pos_x, pos_y, width, height, x_offset, y_offset, profile)

    def _draw_player_text(self, cr, player_num, pos_x, pos_y, width, height, x_offset, y_offset):
        """Draw player number text."""
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        font_size = max(10, min(width, height) // 5)
        cr.set_font_size(font_size)
        cr.set_source_rgb(1.0, 1.0, 1.0)  # White text

        text = f"P{player_num}"
        _, _, width_text, height_text, _, _ = cr.text_extents(text)
        text_x = x_offset + pos_x + (width - width_text) / 2
        text_y = y_offset + pos_y + (height + height_text) / 2
        cr.move_to(text_x, text_y)
        cr.show_text(text)

    def _draw_monitor_info(self, cr, player_index, pos_x, pos_y, width, height, x_offset, y_offset, profile):
        """Draw monitor ID information below player text."""
        monitor_id_text = self._get_monitor_text(player_index, profile)

        if monitor_id_text:
            # Calculate font size relative to player text
            base_font_size = max(10, min(width, height) // 5)
            font_size = base_font_size * 0.7

            cr.set_font_size(font_size)
            cr.set_source_rgb(0.7, 0.7, 0.7)  # Gray text for monitor ID

            _, _, width_text, height_text, _, _ = cr.text_extents(monitor_id_text)
            text_x = x_offset + pos_x + (width - width_text) / 2
            text_y = y_offset + pos_y + (height + height_text) / 2 + (base_font_size * 0.8)
            cr.move_to(text_x, text_y)
            cr.show_text(monitor_id_text)

    def _get_monitor_text(self, player_index, profile):
        """Get monitor text for a specific player."""
        if (profile.player_configs and
            player_index < len(profile.player_configs)):
            player_instance = profile.player_configs[player_index]
            monitor_id_from_profile = player_instance.monitor_id
            if monitor_id_from_profile:
                return self.device_id_to_name.get(monitor_id_from_profile, "None")
        return ""

    def get_profile_data(self):
        proton_version = self.proton_version_combo.get_active_text()
        if proton_version == "None (Use Steam default)" or not proton_version:
            proton_version = None

        player_configs_data = self._get_player_configs_from_ui()

        splitscreen_config = None
        if self.mode_combo.get_active_text() == "splitscreen":
            selected_orientation = self.splitscreen_orientation_combo.get_active_text()
            self.logger.info(f"DEBUG: Selected splitscreen orientation from UI: {selected_orientation}")
            splitscreen_config = SplitscreenConfig(
                orientation=selected_orientation
            )
            self.logger.info(f"DEBUG: SplitscreenConfig orientation immediately after creation: {splitscreen_config.orientation}")

        # Correctly determine is_native_value by checking if the path ends with .exe
        exe_path_text = self.exe_path_entry.get_text()
        is_native_value = False
        if exe_path_text:
            is_native_value = not Path(exe_path_text).suffix.lower() == ".exe"

        mode = self.mode_combo.get_active_text()

        profile_data = GameProfile(
            game_name=self.game_name_entry.get_text(),
            exe_path=self.exe_path_entry.get_text(),
            num_players=self.num_players_spin.get_value_as_int(),
            proton_version=proton_version,
            instance_width=self.instance_width_spin.get_value_as_int(),
            instance_height=self.instance_height_spin.get_value_as_int(),
            app_id=self.app_id_entry.get_text() or None,
            game_args=self.game_args_entry.get_text(),
            env_vars=self._get_env_vars_from_ui(),
            is_native=is_native_value,
            mode=mode,
            splitscreen=splitscreen_config,
            player_configs=player_configs_data, # Use the already collected data
        )

        self.logger.info(f"DEBUG: Mode value before GameProfile instantiation: {mode}")

        if profile_data.splitscreen:
            self.logger.info(f"DEBUG: Splitscreen orientation in GameProfile object: {profile_data.splitscreen.orientation}")

        profile_dumped = profile_data.model_dump(by_alias=True, exclude_unset=False, exclude_defaults=False, mode='json')
        self.logger.info(f"DEBUG: Collecting {len(profile_dumped.get('PLAYERS') or [])} player configs for saving.")
        return profile_dumped

    def load_profile_data(self, profile_data):
        """Main entry point for loading profile data into the UI."""
        try:
            # Load different sections of the profile
            self._load_basic_profile_settings(profile_data)
            self._load_proton_settings(profile_data)
            self._load_instance_settings(profile_data)
            self._load_mode_and_splitscreen_settings(profile_data)
            self._load_environment_variables(profile_data)
            self._load_player_configurations(profile_data)
            self._finalize_profile_loading()

        except Exception as e:
            self.logger.error(f"Error loading profile data: {e}")

    def _load_basic_profile_settings(self, profile_data):
        """Load basic profile settings like name, executable path, and player count."""
        self.game_name_entry.set_text(profile_data.get("GAME_NAME", ""))
        self.exe_path_entry.set_text(str(profile_data.get("EXE_PATH", "")))
        self.num_players_spin.set_value(profile_data.get("NUM_PLAYERS", 1))

    def _load_proton_settings(self, profile_data):
        """Load Proton version settings."""
        proton_version = profile_data.get("PROTON_VERSION")
        if proton_version:
            model = self.proton_version_combo.get_model()
            for i, row in enumerate(model):
                if row[0] == proton_version:
                    self.proton_version_combo.set_active(i)
                    break
            else:
                self.proton_version_combo.set_active(0)
        else:
            self.proton_version_combo.set_active(0)

    def _load_instance_settings(self, profile_data):
        """Load instance-specific settings like dimensions and game configuration."""
        self.instance_width_spin.set_value(profile_data.get("INSTANCE_WIDTH", 1920))
        self.instance_height_spin.set_value(profile_data.get("INSTANCE_HEIGHT", 1080))
        self.app_id_entry.set_text(profile_data.get("APP_ID", ""))
        self.game_args_entry.set_text(profile_data.get("GAME_ARGS", ""))
        self.is_native_check.set_active(profile_data.get("IS_NATIVE", False))

    def _load_mode_and_splitscreen_settings(self, profile_data):
        """Load mode and splitscreen configuration."""
        mode = profile_data.get("MODE")
        if mode:
            self.mode_combo.set_active_id(mode)
        else:
            self.mode_combo.set_active_id("None")

        # Configure splitscreen visibility and orientation
        current_mode = self.mode_combo.get_active_id()
        if current_mode == "splitscreen":
            self._show_splitscreen_controls()
            self._load_splitscreen_orientation(profile_data)
        else:
            self._hide_splitscreen_controls()

    def _show_splitscreen_controls(self):
        """Show splitscreen orientation controls."""
        self.splitscreen_orientation_label.show()
        self.splitscreen_orientation_combo.show()

    def _hide_splitscreen_controls(self):
        """Hide splitscreen orientation controls."""
        self.splitscreen_orientation_label.hide()
        self.splitscreen_orientation_combo.hide()

    def _load_splitscreen_orientation(self, profile_data):
        """Load splitscreen orientation from profile data."""
        splitscreen_data = profile_data.get("SPLITSCREEN")
        if splitscreen_data and isinstance(splitscreen_data, dict):
            orientation = splitscreen_data.get("ORIENTATION", "horizontal")
            self.splitscreen_orientation_combo.set_active_id(orientation)
        else:
            # Default value if no splitscreen data
            self.splitscreen_orientation_combo.set_active_id("horizontal")

    def _load_environment_variables(self, profile_data):
        """Load environment variables from profile data."""
        # Clear existing environment variables
        self._clear_environment_variables_ui()

        env_vars_data = profile_data.get("ENV_VARS", {})
        if env_vars_data:
            self._populate_environment_variables(env_vars_data)
        else:
            self._add_default_environment_variables()

    def _clear_environment_variables_ui(self):
        """Clear existing environment variable entries from UI."""
        while self.env_vars_listbox.get_first_child():
            self.env_vars_listbox.remove(self.env_vars_listbox.get_first_child())
        self.env_var_entries.clear()
        self.env_vars_listbox.queue_draw()

    def _populate_environment_variables(self, env_vars_data):
        """Populate environment variables from data."""
        for key, value in env_vars_data.items():
            self._add_env_var_row(key, value)

    def _add_default_environment_variables(self):
        """Add default environment variables when none are present."""
        self._add_env_var_row("WINEDLLOVERRIDES", "")
        self._add_env_var_row("MANGOHUD", "1")

    def _load_player_configurations(self, profile_data):
        """Load player configurations from profile data."""
        # Clear existing player UI
        self._clear_player_configurations_ui()

        # Get player data and recreate UI
        players_data = profile_data.get("PLAYERS", []) or []
        num_players = len(players_data)

        if num_players > 0:
            self.num_players_spin.set_value(num_players)
            self._create_player_config_uis(num_players)
            self._populate_player_configurations(players_data, profile_data)

    def _clear_player_configurations_ui(self):
        """Clear existing player configuration UI elements."""
        while self.player_config_vbox.get_first_child():
            self.player_config_vbox.remove(self.player_config_vbox.get_first_child())

        self.player_frames.clear()
        self.player_device_combos.clear()
        self.player_checkboxes.clear()
        self.player_config_vbox.queue_draw()

    def _populate_player_configurations(self, players_data, profile_data):
        """Populate player configurations from data."""
        selected_players = profile_data.get("selected_players", []) or []

        for i, player_config_data in enumerate(players_data):
            if i < len(self.player_device_combos):
                self._load_single_player_configuration(
                    i, player_config_data, selected_players
                )

    def _load_single_player_configuration(self, player_index, player_data, selected_players):
        """Load configuration for a single player."""
        player_combos = self.player_device_combos[player_index]
        player_checkbox = self.player_checkboxes[player_index]

        # Set player selection checkbox
        player_checkbox.set_active((player_index + 1) in selected_players)

        # Load text fields
        self._load_player_text_fields(player_combos, player_data)

        # Load device dropdowns
        self._load_player_device_settings(player_combos, player_data)

    def _load_player_text_fields(self, player_combos, player_data):
        """Load text field values for a player."""
        text_fields = ["ACCOUNT_NAME", "LANGUAGE", "LISTEN_PORT", "USER_STEAM_ID"]
        for field in text_fields:
            value = player_data.get(field, "") or ""
            player_combos[field].set_text(value)

    def _load_player_device_settings(self, player_combos, player_data):
        """Load device dropdown settings for a player."""
        device_fields = [
            "PHYSICAL_DEVICE_ID", "MOUSE_EVENT_PATH",
            "KEYBOARD_EVENT_PATH", "AUDIO_DEVICE_ID", "MONITOR_ID"
        ]

        for field in device_fields:
            self._set_device_dropdown(player_combos[field], player_data.get(field))

    def _set_device_dropdown(self, dropdown, device_id):
        """Set a device dropdown to the correct value based on device ID."""
        device_name = self.device_id_to_name.get(device_id, "None")
        selected_index = self._get_dropdown_index_for_name(dropdown, device_name)
        dropdown.set_selected(selected_index)

    def _finalize_profile_loading(self):
        """Finalize profile loading by updating UI elements."""
        # Update the layout preview after loading all profile data
        self.drawing_area.queue_draw()


    def _get_dropdown_index_for_name(self, dropdown: Gtk.DropDown, name: str) -> int:
        model = dropdown.get_model()
        if model:
            for i in range(model.get_n_items()):
                item = model.get_item(i)
                if item and item.get_string() == name:
                    return i
        return 0 # Default to first item (e.g., "None") if not found or model is empty

    def _create_device_list_store(self, devices: List[Dict[str, str]]) -> List[str]:
        string_list_data = ["None"] # Add "None" as the first option
        for device in devices:
            string_list_data.append(device["name"])
        return string_list_data

    def _populate_profile_list(self):
        """Populates the ListBox with available game profiles, displaying GAME_NAME."""
        # In Gtk4, Gtk.ListBox.get_children() is removed. Remove rows one by one.
        while self.profile_listbox.get_first_child():
            self.profile_listbox.remove(self.profile_listbox.get_first_child())

        profile_dir = Config.PROFILE_DIR
        profile_dir.mkdir(parents=True, exist_ok=True)

        profiles = sorted(profile_dir.glob("*.json"))

        if not profiles:
            label = Gtk.Label(label="No profiles found.\nCreate one and save it!")
            label.set_halign(Gtk.Align.CENTER)
            row = Gtk.ListBoxRow()
            row.set_child(label) # Changed from add
            self.profile_listbox.append(row) # Changed from add
            row.set_sensitive(False) # Make it non-selectable

            # Hide delete button when no profiles
            self.delete_profile_button.set_visible(False)
            self.selected_profile_name = None
        else:
            for profile_path in profiles:
                profile_name_stem = profile_path.stem # Get filename without extension
                try:
                    profile = GameProfile.load_from_file(profile_path) # Load profile, uses cache
                    display_name = profile.game_name or profile_name_stem # Use GAME_NAME, fallback to filename
                except Exception as e:
                    self.logger.warning(f"Could not load profile {profile_name_stem} for display in list: {e}")
                    display_name = profile_name_stem + " (Error)" # Indicate error

                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=display_name)
                label.set_halign(Gtk.Align.START) # Align text to the start
                row.set_child(label) # Changed from add
                # Store the actual filename stem in the label's name property
                label.set_name(profile_name_stem)
                self.profile_listbox.append(row) # Changed from add

        # self.profile_listbox.show_all() # Not needed for Gtk4

    def _on_profile_selected_from_list(self, listbox, row):
        """Handles selection of a profile from the sidebar list, using stored filename."""
        profile_name_stem = row.get_child().get_name() # Get the filename stem from the label's name property
        if not profile_name_stem:
            self.logger.warning("Attempted to select a profile without a stored filename property.")
            return

        # Update selected profile and show delete button
        self.selected_profile_name = profile_name_stem
        self.delete_profile_button.set_visible(True)

        profile_path = Config.PROFILE_DIR / f"{profile_name_stem}.json"
        self.logger.info(f"Loading profile from sidebar: {profile_name_stem}")

        try:
            profile = GameProfile.load_from_file(profile_path)
            self.load_profile_data(profile.model_dump(by_alias=True))
            self.statusbar.set_label(f"Profile loaded: {profile_name_stem}") # Changed from push
            # Switch to General Settings tab after loading
            self.notebook.set_current_page(0)
        except Exception as e:
            self.logger.error(f"Failed to load profile {profile_name_stem}: {e}")
            # Show error dialog
            error_dialog = Adw.MessageDialog(
                heading="Load Error",
                body=f"Failed to load profile '{profile_name_stem}':\n{str(e)}"
            )
            error_dialog.add_response("ok", "OK")
            error_dialog.set_default_response("ok")
            error_dialog.set_close_response("ok")
            error_dialog.set_transient_for(self)
            error_dialog.connect("response", lambda d, r: d.close())
            error_dialog.present()

    def _on_add_profile_clicked(self, button):
        """Handle add new profile button click."""
        self._create_new_profile()

    def _on_delete_profile_clicked(self, button):
        """Handle delete profile button click."""
        if not self.selected_profile_name:
            return

        self._delete_selected_profile()

    def _create_new_profile(self):
        """Create a new profile with default values."""
        # Create dialog to get profile name
        dialog = Gtk.Dialog(
            title="New Profile",
            transient_for=self,
            modal=True
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        # Create content area
        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)

        # Add instruction label
        instruction_label = Gtk.Label(label="Enter a name for your new game profile:")
        instruction_label.set_halign(Gtk.Align.START)
        instruction_label.set_margin_bottom(5)
        content_area.append(instruction_label)

        # Add label and entry for profile name
        label = Gtk.Label(label="Profile Name:")
        label.set_halign(Gtk.Align.START)
        content_area.append(label)

        entry = Gtk.Entry()
        entry.set_placeholder_text("e.g., Palworld, Elden Ring, Enshrouded...")
        entry.set_activates_default(True)  # Press Enter to create
        entry.grab_focus()  # Focus on entry when dialog opens
        content_area.append(entry)

        # Add example text
        example_label = Gtk.Label(label="💡 Tip: Use descriptive names like the game title")
        example_label.set_halign(Gtk.Align.START)
        example_label.set_margin_top(5)
        example_label.add_css_class("dim-label")
        content_area.append(example_label)

        # Show dialog and handle response
        dialog.present()

        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                profile_name = entry.get_text().strip()
                if profile_name:
                    # Validate profile name
                    if self._validate_profile_name(profile_name):
                        self._create_profile_with_name(profile_name)
                    else:
                        # Don't close dialog on validation error
                        return
                else:
                    self.statusbar.set_label("❌ Profile name cannot be empty")
                    return
            dialog.destroy()

        dialog.connect("response", on_response)

    def _validate_profile_name(self, profile_name):
        """Validate the profile name and show error if invalid."""
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        for char in invalid_chars:
            if char in profile_name:
                self.statusbar.set_label(f"❌ Profile name cannot contain '{char}'")
                return False

        # Check length
        if len(profile_name) > 50:
            self.statusbar.set_label("❌ Profile name too long (max 50 characters)")
            return False

        # Check if already exists
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        if profile_path.exists():
            self.statusbar.set_label(f"❌ Profile '{profile_name}' already exists")
            return False

        return True

    def _create_profile_with_name(self, profile_name):
        """Create a new profile file with the given name."""
        try:
            # Ensure profile directory exists
            Config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)

            # Create profile path
            profile_path = Config.PROFILE_DIR / f"{profile_name}.json"

            # Profile validation is now done in _validate_profile_name

            # Create default profile data
            default_profile_data = {
                "GAME_NAME": profile_name,
                "EXE_PATH": "",
                "NUM_PLAYERS": 2,
                "INSTANCE_WIDTH": 1920,
                "INSTANCE_HEIGHT": 1080,
                "APP_ID": "",
                "GAME_ARGS": "",
                "IS_NATIVE": False,
                "MODE": "None",
                "SPLITSCREEN": None,
                "PROTON_VERSION": None,
                "PLAYERS": [
                    {
                        "ACCOUNT_NAME": "Player1",
                        "LANGUAGE": "english",
                        "LISTEN_PORT": "",
                        "USER_STEAM_ID": "",
                        "PHYSICAL_DEVICE_ID": "",
                        "MOUSE_EVENT_PATH": "",
                        "KEYBOARD_EVENT_PATH": "",
                        "AUDIO_DEVICE_ID": "",
                        "MONITOR_ID": ""
                    },
                    {
                        "ACCOUNT_NAME": "Player2",
                        "LANGUAGE": "english",
                        "LISTEN_PORT": "",
                        "USER_STEAM_ID": "",
                        "PHYSICAL_DEVICE_ID": "",
                        "MOUSE_EVENT_PATH": "",
                        "KEYBOARD_EVENT_PATH": "",
                        "AUDIO_DEVICE_ID": "",
                        "MONITOR_ID": ""
                    }
                ],
                "ENV_VARS": {
                    "WINEDLLOVERRIDES": "",
                    "MANGOHUD": "1"
                }
            }

            # Save the profile
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(default_profile_data, f, indent=4)

            # Refresh the profile list
            self._populate_profile_list()

            # Load the new profile
            self.load_profile_data(default_profile_data)

            # Select the new profile in the list
            self._select_profile_in_list(profile_name)

            # Update selected profile and show delete button
            self.selected_profile_name = profile_name
            self.delete_profile_button.set_visible(True)

            # Switch to General Settings tab
            self.notebook.set_current_page(0)

            self.statusbar.set_label(f"✅ Profile '{profile_name}' created successfully!")
            self.logger.info(f"Created new profile: {profile_name}")

        except Exception as e:
            error_msg = f"❌ Error creating profile '{profile_name}': {e}"
            self.statusbar.set_label(error_msg)
            self.logger.error(error_msg)

    def _delete_selected_profile(self):
        """Delete the currently selected profile after confirmation."""
        if not self.selected_profile_name:
            return

        # Create confirmation dialog
        dialog = Adw.MessageDialog(
            heading="Delete Profile",
            body=f"Are you sure you want to delete the profile '{self.selected_profile_name}'?\n\nThis action cannot be undone.",
            transient_for=self,
            modal=True
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response_id):
            if response_id == "delete":
                self._confirm_delete_profile()
            dialog.close()

        dialog.connect("response", on_response)
        dialog.present()

    def _confirm_delete_profile(self):
        """Actually delete the profile file and update UI."""
        try:
            # Save the name before clearing
            deleted_name = self.selected_profile_name

            # Delete the profile file
            profile_path = Config.PROFILE_DIR / f"{self.selected_profile_name}.json"
            if profile_path.exists():
                profile_path.unlink()
                self.logger.info(f"Deleted profile: {self.selected_profile_name}")

            # Clear UI and update
            self._clear_all_fields()
            self._populate_profile_list()

            # Hide delete button and clear selection
            self.delete_profile_button.set_visible(False)
            self.selected_profile_name = None

            self.statusbar.set_label(f"✅ Profile '{deleted_name}' deleted successfully")

        except Exception as e:
            error_msg = f"❌ Error deleting profile: {e}"
            self.statusbar.set_label(error_msg)
            self.logger.error(error_msg)

    def _clear_all_fields(self):
        """Clear all form fields to default values."""
        # Basic settings
        self.game_name_entry.set_text("")
        self.exe_path_entry.set_text("")
        self.num_players_spin.set_value(1)
        self.instance_width_spin.set_value(1920)
        self.instance_height_spin.set_value(1080)
        self.app_id_entry.set_text("")
        self.game_args_entry.set_text("")
        self.is_native_check.set_active(False)

        # Mode settings
        self.mode_combo.set_active_id("None")
        self.splitscreen_orientation_combo.set_active_id("horizontal")
        self._hide_splitscreen_controls()

        # Proton version
        self.proton_version_combo.set_active(0)

        # Clear environment variables
        self._clear_environment_variables_ui()
        self._add_default_environment_variables()

        # Clear player configurations
        self._clear_player_configurations_ui()
        self.num_players_spin.set_value(1)
        self._create_player_config_uis(1)

        # Update preview
        self.drawing_area.queue_draw()

    def _select_profile_in_list(self, profile_name_to_select: str):
        current_row = self.profile_listbox.get_first_child()
        while current_row:
            # Check if the row is a valid Gtk.ListBoxRow and its child (label) has the correct name
            if isinstance(current_row, Gtk.ListBoxRow) and isinstance(current_row.get_child(), Gtk.Label) and current_row.get_child().get_name() == profile_name_to_select:
                self.profile_listbox.select_row(current_row)
                break
            current_row = current_row.get_next_sibling()

class LinuxCoopApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.linuxcoop.app")
        self.connect("activate", self.on_activate)

        # Initialize Adwaita
        Adw.init()

        # Configure proper Adwaita style manager to avoid warnings
        self._configure_adwaita_style()

        # Initialize styles using the professional StyleManager
        self._initialize_application_styles()

    def _configure_adwaita_style(self):
        """Configure Adwaita style manager to follow system theme preference"""
        try:
            style_manager = Adw.StyleManager.get_default()
            # Use PREFER_DARK to automatically follow system theme preference
            # This will use dark theme when system prefers dark, light when system prefers light
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

            # Optional: Connect to theme changes to update custom styles if needed
            style_manager.connect("notify::dark", self._on_theme_changed)

            # Log current theme state
            is_dark = style_manager.get_dark()
            theme_name = "dark" if is_dark else "light"
            self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
            self.logger.info(f"Configured Adwaita to follow system theme. Current theme: {theme_name}")
        except Exception as e:
            # Fallback if AdwStyleManager is not available
            self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
            self.logger.warning(f"Could not configure Adwaita style manager: {e}")

    def _on_theme_changed(self, style_manager, param):
        """Handle system theme changes"""
        try:
            is_dark = style_manager.get_dark()
            theme_name = "dark" if is_dark else "light"
            self.logger.info(f"System theme changed to: {theme_name}")

            # Trigger StyleManager to reload theme-specific styles
            from .styles import get_style_manager
            style_manager_instance = get_style_manager()
            style_manager_instance._load_theme_specific_styles()

            # Update window styling if needed
            self._update_window_for_theme(is_dark)
        except Exception as e:
            self.logger.warning(f"Error handling theme change: {e}")

    def _update_window_for_theme(self, is_dark: bool):
        """Update window-specific styling based on theme"""
        try:
            # Force refresh of all widgets to apply new theme
            self.queue_draw()

            # Update any theme-sensitive components
            if hasattr(self, 'drawing_area'):
                self.drawing_area.queue_draw()

        except Exception as e:
            self.logger.warning(f"Error updating window for theme: {e}")

    def _initialize_application_styles(self):
        """Initialize application styles using the StyleManager"""
        try:
            initialize_styles()
            self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
            self.logger.info("Successfully initialized application styles")
        except StyleManagerError as e:
            # Fallback to basic styling if StyleManager fails
            self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
            self.logger.warning(f"Failed to initialize StyleManager: {e}")
            self._apply_fallback_styles()

    def _apply_fallback_styles(self):
        """Apply minimal fallback styles if StyleManager fails"""
        try:
            style_manager = get_style_manager()
            fallback_css = """
            /* Minimal fallback styles */
            * { font-family: system-ui, sans-serif; }
            label { padding: 4px 0; min-height: 20px; }
            entry, button { padding: 6px; min-height: 28px; }
            """
            style_manager.load_css_from_string(fallback_css, "fallback")
        except Exception as e:
            self.logger.error(f"Even fallback styles failed: {e}")

    def on_activate(self, app):
        window = ProfileEditorWindow(app)
        window.present() # Changed from show_all() or show()

def run_gui():
    app = LinuxCoopApp()
    app.run(None)

if __name__ == "__main__":
    # This ensures that the GUI is only started if the script is executed directly
    # and not when imported as a module.
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1") # Added Adw require
    from gi.repository import Gtk, Gdk, Adw # Added Adw import
    import cairo # Import cairo here for drawing
    import time # Import time for busy-wait in _stop_game
    from gi.repository import GLib # Importado para usar GLib.timeout_add
    run_gui()
