import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from pathlib import Path
import json
from ..services.device_manager import DeviceManager
from ..models.profile import GameProfile, PlayerInstanceConfig, SplitscreenConfig
from ..services.proton import ProtonService
from ..core.logger import Logger
from ..core.config import Config
from typing import Dict, List, Tuple
import subprocess
import shutil
import cairo # Import cairo here for drawing
import sys # Importado para usar sys.executable

class ProfileEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Linux Coop Profile Editor")
        self.set_default_size(1000, 700)

        # Create the main vertical box which will hold the notebook and statusbar
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_vbox) # Add main_vbox as the single child of the window

        # Initialize configuration widgets early
        self.num_players_spin = Gtk.SpinButton.new_with_range(1, 4, 1)
        self.num_players_spin.set_value(1) # Default value
        self.instance_width_spin = Gtk.SpinButton.new_with_range(640, 3840, 1)
        self.instance_width_spin.set_value(1920) # Default from example.json
        self.instance_height_spin = Gtk.SpinButton.new_with_range(480, 2160, 1)
        self.instance_height_spin.set_value(1080) # Default from example.json

        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append_text("None")
        self.mode_combo.append_text("splitscreen")
        self.mode_combo.set_active(0) # Default to None

        self.splitscreen_orientation_label = Gtk.Label(label="Splitscreen Orientation:", xalign=0)
        self.splitscreen_orientation_combo = Gtk.ComboBoxText()
        self.splitscreen_orientation_combo.append_text("horizontal")
        self.splitscreen_orientation_combo.append_text("vertical")
        self.splitscreen_orientation_combo.set_active(0) # Default to horizontal

        self.device_manager = DeviceManager()
        self.detected_input_devices = self.device_manager.get_input_devices()
        self.detected_audio_devices = self.device_manager.get_audio_devices()
        self.detected_display_outputs = self.device_manager.get_display_outputs() # Adicionado para seleção de monitor
        self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
        self.proton_service = ProtonService(self.logger)

        self.notebook = Gtk.Notebook()
        main_vbox.pack_start(self.notebook, True, True, 0) # Empacota o notebook no main_vbox

        # Initialize player config entries list
        self.player_config_entries = []
        self.player_checkboxes = []

        # Tab 1: General Settings
        self.general_settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.general_settings_page.set_border_width(10)
        self.notebook.append_page(self.general_settings_page, Gtk.Label(label="General Settings"))

        self.general_settings_grid = Gtk.Grid()
        self.general_settings_grid.set_column_spacing(10)
        self.general_settings_grid.set_row_spacing(10)
        self.general_settings_grid.set_border_width(10)
        self.general_settings_page.pack_start(self.general_settings_grid, False, False, 0)
        self.setup_general_settings()

        # Tab 2: Player Configurations
        self.player_configs_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.player_configs_page.set_border_width(10)
        self.player_configs_page.set_vexpand(True) # Ensure this page expands vertically
        # self.player_configs_page.set_hexpand(True) # Removed as it's a vertical box and may not be necessary
        self.notebook.append_page(self.player_configs_page, Gtk.Label(label="Player Configurations"))

        # Create a ScrolledWindow for player configurations
        player_scrolled_window = Gtk.ScrolledWindow()
        player_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        player_scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        player_scrolled_window.set_vexpand(True) # Essential for vertical expansion within its parent
        player_scrolled_window.set_hexpand(True) # Essential for horizontal expansion within its parent
        self.player_configs_page.pack_start(player_scrolled_window, True, True, 0)

        # Create a Viewport for the player configurations content
        player_viewport = Gtk.Viewport()
        player_scrolled_window.add(player_viewport)

        self.player_config_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        player_viewport.add(self.player_config_vbox) # Add the vbox to the viewport
        self.setup_player_configs()

        # Tab 3: Window Layout Preview
        self.window_layout_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window_layout_page.set_border_width(10)
        self.notebook.append_page(self.window_layout_page, Gtk.Label(label="Window Layout Preview"))

        # Add a grid for layout settings in the preview tab
        self.preview_settings_grid = Gtk.Grid()
        self.preview_settings_grid.set_column_spacing(10)
        self.preview_settings_grid.set_row_spacing(10)
        self.preview_settings_grid.set_border_width(10)
        self.window_layout_page.pack_start(self.preview_settings_grid, False, False, 0)

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

        # REMOVED: Primary Monitor Entry (NEW)
        # self.primary_monitor_label = Gtk.Label(label="Primary Monitor (Fullscreen):", xalign=0)
        # self.preview_settings_grid.attach(self.primary_monitor_label, 0, preview_row, 1, 1)
        # self.primary_monitor_entry = Gtk.Entry()
        # self.primary_monitor_entry.set_placeholder_text("Ex: DP-1, HDMI-A-1 (leave blank for default)")
        # self.preview_settings_grid.attach(self.primary_monitor_entry, 1, preview_row, 1, 1)
        # self.primary_monitor_label.hide() # Hide by default, show only in non-splitscreen mode
        # self.primary_monitor_entry.hide() # Hide by default
        # preview_row += 1

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self.on_draw_window_layout)
        self.window_layout_page.pack_start(self.drawing_area, True, True, 0)

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

        # Add a Statusbar at the bottom
        self.statusbar = Gtk.Statusbar()
        main_vbox.pack_end(self.statusbar, False, False, 0)

        self.show_all()

    def setup_general_settings(self):
        # Use a main VBox for this page to hold frames
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.general_settings_page.pack_start(main_vbox, True, True, 0)

        # Frame 1: Game Details
        game_details_frame = Gtk.Frame(label="Game Details")
        game_details_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        main_vbox.pack_start(game_details_frame, False, False, 0)

        game_details_grid = Gtk.Grid()
        game_details_grid.set_column_spacing(10)
        game_details_grid.set_row_spacing(10)
        game_details_grid.set_border_width(10)
        game_details_frame.add(game_details_grid)

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
        exe_path_hbox.pack_start(self.exe_path_entry, True, True, 0)

        exe_path_button = Gtk.Button(label="Browse...")
        exe_path_button.connect("clicked", self.on_exe_path_button_clicked)
        exe_path_hbox.pack_start(exe_path_button, False, False, 0)

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
        proton_options_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        main_vbox.pack_start(proton_options_frame, False, False, 0)

        proton_options_grid = Gtk.Grid()
        proton_options_grid.set_column_spacing(10)
        proton_options_grid.set_row_spacing(10)
        proton_options_grid.set_border_width(10)
        proton_options_frame.add(proton_options_grid)

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
        env_vars_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        main_vbox.pack_start(env_vars_frame, False, False, 0)

        env_vars_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        env_vars_vbox.set_border_width(10)
        env_vars_frame.add(env_vars_vbox)

        self.env_vars_listbox = Gtk.ListBox()
        self.env_vars_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        env_vars_vbox.pack_start(self.env_vars_listbox, True, True, 0)
        self.env_var_entries = []

        self._add_env_var_row("WINEDLLOVERRIDES", "")
        self._add_env_var_row("MANGOHUD", "1")

        add_env_var_button = Gtk.Button(label="Add Variable")
        add_env_var_button.connect("clicked", self._on_add_env_var_clicked)
        env_vars_vbox.pack_start(add_env_var_button, False, False, 0)

        # Buttons at the bottom
        button_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_hbox.set_halign(Gtk.Align.END) # Align buttons to the right
        main_vbox.pack_end(button_hbox, False, False, 0)

        load_button = Gtk.Button(label="Load Profile")
        load_button.connect("clicked", self.on_load_button_clicked)
        button_hbox.pack_start(load_button, False, False, 0)

        save_button = Gtk.Button(label="Save Profile")
        save_button.connect("clicked", self.on_save_button_clicked)
        button_hbox.pack_start(save_button, False, False, 0)

        play_button = Gtk.Button(label="▶️ Launch Game")
        play_button.get_style_context().add_class("suggested-action") # Highlight play button
        play_button.connect("clicked", self.on_play_button_clicked)
        button_hbox.pack_start(play_button, False, False, 0)

    def on_exe_path_button_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Game Executable",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.exe_path_entry.set_text(dialog.get_filename())

        dialog.destroy()
        self.statusbar.push(0, "Executable path selected.")

    def on_load_button_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Load Game Profile",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        try:
            Config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            dialog.set_current_folder(str(Config.PROFILE_DIR))
        except Exception as e:
            self.logger.warning(f"Could not set initial folder for profile loading: {e}")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = Path(dialog.get_filename())
            try:
                profile = GameProfile.load_from_file(file_path)
                self.load_profile_data(profile.model_dump(by_alias=True)) # Use model_dump to convert to dict
                self.logger.info(f"Profile loaded successfully from {file_path}")
                self.statusbar.push(0, f"Profile loaded: {file_path.name}")
            except Exception as e:
                self.logger.error(f"Failed to load profile from {file_path}: {e}")
                self.statusbar.push(0, f"Error loading profile: {e}")
                error_dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"Error loading profile:\n{e}"
                )
                error_dialog.run()
                error_dialog.destroy()
        dialog.destroy()

    def _on_add_env_var_clicked(self, button):
        self._add_env_var_row()
        self.statusbar.push(0, "Environment variable added.")

    def _add_env_var_row(self, key="", value=""):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        key_entry = Gtk.Entry()
        key_entry.set_placeholder_text("Variable Name")
        key_entry.set_hexpand(True)
        key_entry.set_text(key)
        hbox.pack_start(key_entry, True, True, 0)

        value_entry = Gtk.Entry()
        value_entry.set_placeholder_text("Value")
        value_entry.set_hexpand(True)
        value_entry.set_text(value)
        hbox.pack_start(value_entry, True, True, 0)

        remove_button = Gtk.Button(label="-")
        remove_button.set_relief(Gtk.ReliefStyle.NONE)
        remove_button.set_tooltip_text("Remove this environment variable")

        list_box_row = Gtk.ListBoxRow()
        list_box_row.add(hbox)

        remove_button.connect("clicked", lambda btn, row=list_box_row, k_entry=key_entry, v_entry=value_entry: self._remove_env_var_row(btn, row, k_entry, v_entry))
        hbox.pack_end(remove_button, False, False, 0)

        self.env_vars_listbox.add(list_box_row)
        list_box_row.show_all()
        self.env_var_entries.append((key_entry, value_entry, list_box_row))

    def _remove_env_var_row(self, button, row, key_entry, value_entry):
        self.env_vars_listbox.remove(row)
        self.env_var_entries.remove((key_entry, value_entry, row))
        self.statusbar.push(0, "Environment variable removed.")

    def _get_env_vars_from_ui(self) -> Dict[str, str]:
        env_vars = {}
        for key_entry, value_entry, _ in self.env_var_entries:
            key = key_entry.get_text().strip().upper()
            value = value_entry.get_text().strip()
            if key:
                env_vars[key] = value
        return env_vars

    def _get_player_configs_from_ui(self) -> List[Dict[str, str]]:
        player_configs_data = []
        for _, widgets in self.player_config_entries:
            config = {}
            for key, widget in widgets.items():
                if isinstance(widget, Gtk.Entry):
                    config[key] = widget.get_text()
                elif isinstance(widget, Gtk.ComboBox):
                    model = widget.get_model()
                    active_iter = widget.get_active_iter()
                    if active_iter:
                        selected_value = model.get_value(active_iter, 0)
                        # Certifica-se de que a string vazia seja salva como None se for a opção "None"
                        config[key] = selected_value if selected_value != "" else None
                    else:
                        config[key] = None # Define explicitamente como None se nada estiver selecionado
                else:
                    config[key] = ""
            player_configs_data.append(config)
        return player_configs_data

    def setup_player_configs(self):
        self.player_frames = []
        self.player_device_combos = []

        self._create_player_config_uis(self.num_players_spin.get_value_as_int())

    def _create_player_config_uis(self, num_players: int):
        for frame in self.player_frames:
            frame.destroy()
        self.player_frames.clear()
        self.player_device_combos.clear()
        self.player_config_entries.clear()
        self.player_checkboxes.clear()

        for child in self.player_config_vbox.get_children():
            self.player_config_vbox.remove(child)

        for i in range(num_players):
            player_frame = Gtk.Frame(label=f"Player {i+1} Configuration")
            player_frame.set_margin_top(10)
            player_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
            self.player_config_vbox.pack_start(player_frame, False, False, 0)
            self.player_frames.append(player_frame)

            player_grid = Gtk.Grid()
            player_grid.set_column_spacing(10)
            player_grid.set_row_spacing(10)
            player_grid.set_border_width(10)
            player_frame.add(player_grid)

            player_combos = {
                "account_name": Gtk.Entry(),
                "language": Gtk.Entry(),
                "listen_port": Gtk.Entry(),
                "user_steam_id": Gtk.Entry(),
                "physical_device_id": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["joystick"])),
                "mouse_event_path": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["mouse"])),
                "keyboard_event_path": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["keyboard"])),
                "audio_device_id": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_audio_devices)),
                "MONITOR_ID": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_display_outputs)), # Corrigido para MONITOR_ID (maiúsculo)
            }
            self.player_device_combos.append(player_combos)

            p_row = 0

            check_button = Gtk.CheckButton(label=f"Enable Player {i + 1}")
            check_button.set_active(True)
            self.player_checkboxes.append(check_button)
            player_grid.attach(check_button, 0, p_row, 2, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Account Name:", xalign=0), 0, p_row, 1, 1)
            player_combos["account_name"].set_placeholder_text(f"Player {i+1}")
            player_grid.attach(player_combos["account_name"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Language:", xalign=0), 0, p_row, 1, 1)
            player_combos["language"].set_placeholder_text("Ex: brazilian, english")
            player_grid.attach(player_combos["language"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Listen Port (Goldberg):", xalign=0), 0, p_row, 1, 1)
            player_combos["listen_port"].set_placeholder_text("Optional")
            player_grid.attach(player_combos["listen_port"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="User Steam ID:", xalign=0), 0, p_row, 1, 1)
            player_combos["user_steam_id"].set_placeholder_text("Optional (ex: 7656119...)")
            player_grid.attach(player_combos["user_steam_id"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Joystick Device:", xalign=0), 0, p_row, 1, 1)
            physical_device_id_combo = player_combos["physical_device_id"]
            renderer = Gtk.CellRendererText()
            physical_device_id_combo.pack_start(renderer, True)
            physical_device_id_combo.add_attribute(renderer, "text", 1)
            physical_device_id_combo.set_active(0)
            player_grid.attach(physical_device_id_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Mouse Device:", xalign=0), 0, p_row, 1, 1)
            mouse_event_path_combo = player_combos["mouse_event_path"]
            renderer = Gtk.CellRendererText()
            mouse_event_path_combo.pack_start(renderer, True)
            mouse_event_path_combo.add_attribute(renderer, "text", 1)
            mouse_event_path_combo.set_active(0)
            player_grid.attach(mouse_event_path_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Keyboard Device:", xalign=0), 0, p_row, 1, 1)
            keyboard_event_path_combo = player_combos["keyboard_event_path"]
            renderer = Gtk.CellRendererText()
            keyboard_event_path_combo.pack_start(renderer, True)
            keyboard_event_path_combo.add_attribute(renderer, "text", 1)
            keyboard_event_path_combo.set_active(0)
            player_grid.attach(keyboard_event_path_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Audio Device:", xalign=0), 0, p_row, 1, 1)
            audio_device_id_combo = player_combos["audio_device_id"]
            renderer = Gtk.CellRendererText()
            audio_device_id_combo.pack_start(renderer, True)
            audio_device_id_combo.add_attribute(renderer, "text", 1)
            audio_device_id_combo.set_active(0)
            player_grid.attach(audio_device_id_combo, 1, p_row, 1, 1)
            p_row += 1

            # Monitor Selection
            player_grid.attach(Gtk.Label(label="Monitor:", xalign=0), 0, p_row, 1, 1)
            monitor_combo = player_combos["MONITOR_ID"]
            renderer = Gtk.CellRendererText()
            monitor_combo.pack_start(renderer, True)
            monitor_combo.add_attribute(renderer, "text", 1)
            monitor_combo.set_active(0)
            player_grid.attach(monitor_combo, 1, p_row, 1, 1)
            p_row += 1

            player_config_widgets = {
                "ACCOUNT_NAME": player_combos["account_name"],
                "LANGUAGE": player_combos["language"],
                "LISTEN_PORT": player_combos["listen_port"],
                "USER_STEAM_ID": player_combos["user_steam_id"],
                "PHYSICAL_DEVICE_ID": physical_device_id_combo,
                "MOUSE_EVENT_PATH": mouse_event_path_combo,
                "KEYBOARD_EVENT_PATH": keyboard_event_path_combo,
                "AUDIO_DEVICE_ID": audio_device_id_combo,
                "MONITOR_ID": monitor_combo, # Adicionado monitor_id
            }
            self.player_config_entries.append((player_frame, player_config_widgets))
        self.player_config_vbox.show_all()
        self.logger.info(f"DEBUG: Created {len(self.player_config_entries)} player config UIs.")

    def on_num_players_changed(self, spin_button):
        num_players = spin_button.get_value_as_int()
        self._create_player_config_uis(num_players)
        self.statusbar.push(0, f"Number of players changed to {num_players}.")

    def on_mode_changed(self, combo):
        mode = combo.get_active_text()
        if mode == "splitscreen":
            self.splitscreen_orientation_label.show()
            self.splitscreen_orientation_combo.show()
            # REMOVED: self.primary_monitor_label.hide()
            # REMOVED: self.primary_monitor_entry.hide()
            self.statusbar.push(0, "Splitscreen mode activated.")
        else:
            self.splitscreen_orientation_label.hide()
            self.splitscreen_orientation_combo.hide()
            # REMOVED: self.primary_monitor_label.show()
            # REMOVED: self.primary_monitor_entry.show()
            self.statusbar.push(0, "Splitscreen mode deactivated.")

    def on_save_button_clicked(self, button):
        self.statusbar.push(0, "Saving profile...")
        profile_data_dumped = self.get_profile_data()

        selected_players = [i + 1 for i, cb in enumerate(self.player_checkboxes) if cb.get_active()]
        profile_data_dumped['selected_players'] = selected_players

        profile_name = self.game_name_entry.get_text().replace(" ", "_").lower()
        if not profile_name:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       "Game name cannot be empty.")
            dialog.run()
            dialog.destroy()
            self.statusbar.push(0, "Error: Game name is empty.")
            return

        profile_dir = Path.home() / ".config/linux-coop/profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir / f"{profile_name}.json"

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data_dumped, f, indent=2)
            self.statusbar.push(0, f"Profile saved successfully to: {profile_path.name}")
        except Exception as e:
            self.logger.error(f"Failed to save profile to {profile_path}: {e}")
            self.statusbar.push(0, f"Error saving profile: {e}")
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       f"Error saving profile:\n{e}")
            dialog.run()
            dialog.destroy()

    def on_play_button_clicked(self, widget):
        self.statusbar.push(0, "Starting game...")
        self.on_save_button_clicked(widget) # Ensure profile is saved before playing

        profile_name = self.game_name_entry.get_text().replace(" ", "_").lower()
        if not profile_name:
            self.logger.error("Cannot launch game with an empty profile name.")
            self.statusbar.push(0, "Error: Profile name empty. Game not launched.")
            return

        script_path = Path(__file__).parent.parent.parent / "linuxcoop.py"
        python_exec = sys.executable # Use o interpretador Python atual do ambiente virtual
        if not python_exec:
            self.statusbar.push(0, "Error: Python interpreter not found.")
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       "No Python interpreter found on the system.")
            dialog.run()
            dialog.destroy()
            return

        command = [python_exec, str(script_path), profile_name]
        self.logger.info(f"Executing command: {' '.join(command)}")
        try:
            subprocess.Popen(command) # Non-blocking call
            self.statusbar.push(0, f"Game '{profile_name}' launched successfully.")
        except Exception as e:
            self.logger.error(f"Failed to launch game: {e}")
            self.statusbar.push(0, f"Error launching game: {e}")
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       f"Error launching game:\n{e}")
            dialog.run()
            dialog.destroy()

    def on_layout_setting_changed(self, widget):
        self.drawing_area.queue_draw()

    def on_draw_window_layout(self, widget, cr):
        width = self.instance_width_spin.get_value_as_int()
        height = self.instance_height_spin.get_value_as_int()
        num_players = self.num_players_spin.get_value_as_int()
        mode = self.mode_combo.get_active_text()
        orientation = self.splitscreen_orientation_combo.get_active_text()

        # Ensure num_players is at least 1 to prevent ZeroDivisionError
        if num_players < 1:
            num_players = 1

        drawing_area_width = widget.get_allocated_width()
        drawing_area_height = widget.get_allocated_height()

        if width == 0 or height == 0:
            return

        scale_w = drawing_area_width / width
        scale_h = drawing_area_height / height
        scale = min(scale_w, scale_h) * 0.9

        scaled_total_width = width * scale
        scaled_total_height = height * scale

        x_offset_display = (drawing_area_width - scaled_total_width) / 2
        y_offset_display = (drawing_area_height - scaled_total_height) / 2

        # print(f"DEBUG LAYOUT: Total Width/Height (unscaled): {width}x{height}")
        # print(f"DEBUG LAYOUT: Drawing Area Width/Height: {drawing_area_width}x{drawing_area_height}")
        # print(f"DEBUG LAYOUT: Scale: {scale}")
        # print(f"DEBUG LAYOUT: Scaled Total Width/Height: {scaled_total_width}x{scaled_total_height}")
        # print(f"DEBUG LAYOUT: Offsets: X={x_offset_display}, Y={y_offset_display}")
        # print(f"DEBUG LAYOUT: Num Players: {num_players}, Mode: {mode}, Orientation: {orientation}")

        try:
            # Create dummy player configs for the dummy profile to ensure effective_num_players is correct
            dummy_player_configs = []
            for _ in range(num_players):
                dummy_player_configs.append(PlayerInstanceConfig())

            dummy_profile = GameProfile(
                GAME_NAME="Preview",
                EXE_PATH=None,
                NUM_PLAYERS=num_players,
                INSTANCE_WIDTH=width, # Use total width for dummy profile
                INSTANCE_HEIGHT=height, # Use total height for dummy profile
                MODE=mode,
                SPLITSCREEN=SplitscreenConfig(orientation=orientation) if mode == "splitscreen" else None,
                player_configs=dummy_player_configs, # Pass dummy player configs
                # Other player device IDs and native flag are not needed for layout preview
                PLAYER_PHYSICAL_DEVICE_IDS=[],
                PLAYER_MOUSE_EVENT_PATHS=[],
                PLAYER_KEYBOARD_EVENT_PATHS=[],
                PLAYER_AUDIO_DEVICE_IDS=[],
                PLAYER_MONITOR_IDS=[],
                is_native=False,
            )
        except Exception as e:
            print(f"Error creating dummy profile: {e}")
            return

        cr.set_line_width(2)

        if mode == "splitscreen" and num_players > 1:
            for i in range(num_players):
                instance_w, instance_h = dummy_profile.get_instance_dimensions(i + 1) # Unscaled dimensions
                draw_w = instance_w * scale
                draw_h = instance_h * scale

                pos_x, pos_y = 0.0, 0.0 # Initialize positions

                if num_players == 2:
                    if orientation == "horizontal":
                        pos_x = i * draw_w
                    else: # vertical
                        pos_y = i * draw_h
                elif num_players == 3:
                    # Fetch dimensions for all players in 3-player splitscreen
                    p1_unscaled_w, p1_unscaled_h = dummy_profile.get_instance_dimensions(1)
                    p2_unscaled_w, p2_unscaled_h = dummy_profile.get_instance_dimensions(2) # P2 and P3 have same dimensions

                    p1_draw_w, p1_draw_h = p1_unscaled_w * scale, p1_unscaled_h * scale
                    p2_draw_w, p2_draw_h = p2_unscaled_w * scale, p2_unscaled_h * scale

                    if orientation == "horizontal": # 1 large top, 2 small bottom
                        if i == 0: # Player 1 (top)
                            pos_x, pos_y = 0, 0
                        elif i == 1: # Player 2 (bottom-left)
                            pos_x, pos_y = 0, p1_draw_h # Offset by P1's height
                        elif i == 2: # Player 3 (bottom-right)
                            pos_x, pos_y = p2_draw_w, p1_draw_h # Offset by P2's width and P1's height
                    else: # vertical: 1 large left, 2 small right
                        if i == 0: # Player 1 (left)
                            pos_x, pos_y = 0, 0
                        elif i == 1: # Player 2 (top-right)
                            pos_x, pos_y = p1_draw_w, 0 # Offset by P1's width
                        elif i == 2: # Player 3 (bottom-right)
                            pos_x, pos_y = p1_draw_w, p2_draw_h # Offset by P1's width and P2's height
                elif num_players == 4:
                    # 2x2 grid
                    row = i // 2
                    col = i % 2
                    pos_x = col * draw_w
                    pos_y = row * draw_h
                else: # Generic case for more than 4 players, uniform distribution
                    if orientation == "horizontal": # Stacked vertically
                        pos_y = i * draw_h
                    else: # vertical (Side by side)
                        pos_x = i * draw_w

                # print(f"DEBUG LAYOUT: P{i+1} - Unscaled: {instance_w}x{instance_h}, Scaled: {draw_w:.2f}x{draw_h:.2f}, Pos: ({pos_x:.2f}, {pos_y:.2f}), Rect: ({x_offset_display + pos_x:.2f}, {y_offset_display + pos_y:.2f}, {draw_w:.2f}, {draw_h:.2f})")

                cr.rectangle(x_offset_display + pos_x, y_offset_display + pos_y, draw_w, draw_h)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                cr.stroke()

                # Draw player number inside the rectangle
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                font_size = max(10, min(draw_w, draw_h) // 5)
                cr.set_font_size(font_size)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White text

                text = f"P{i+1}"
                xbearing, ybearing, width_text, height_text, xadvance, yadvance = cr.text_extents(text)
                text_x = x_offset_display + pos_x + (draw_w - width_text) / 2
                text_y = y_offset_display + pos_y + (draw_h + height_text) / 2
                cr.move_to(text_x, text_y)
                cr.show_text(text)

                # Desenha o Monitor ID abaixo do número do jogador
                monitor_id_text = ""
                if self.player_config_entries and i < len(self.player_config_entries):
                    player_config_widgets = self.player_config_entries[i][1]
                    monitor_combo = player_config_widgets.get("MONITOR_ID")
                    if monitor_combo:
                        active_iter = monitor_combo.get_active_iter()
                        if active_iter:
                            monitor_id_text = monitor_combo.get_model().get_value(active_iter, 0)

                if monitor_id_text:
                    cr.set_font_size(font_size * 0.7)
                    cr.set_source_rgb(0.7, 0.7, 0.7) # Texto cinza para o ID do monitor
                    xbearing, ybearing, width_text, height_text, xadvance, yadvance = cr.text_extents(monitor_id_text)
                    text_x = x_offset_display + pos_x + (draw_w - width_text) / 2
                    text_y = y_offset_display + pos_y + (draw_h + height_text) / 2 + (font_size * 0.8) # Posição abaixo do número do jogador
                    cr.move_to(text_x, text_y)
                    cr.show_text(monitor_id_text)
        else:
            instance_w, instance_h = dummy_profile.get_instance_dimensions(1)
            draw_w = instance_w * scale
            draw_h = instance_h * scale
            cr.rectangle(x_offset_display, y_offset_display, draw_w, draw_h)
            cr.set_source_rgb(1.0, 1.0, 1.0) # White border
            cr.stroke()

            # Draw Player 1 label for single instance
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            font_size = max(10, min(draw_w, draw_h) // 5)
            cr.set_font_size(font_size)
            cr.set_source_rgb(1.0, 1.0, 1.0)

            text = "P1"
            xbearing, ybearing, width_text, height_text, xadvance, yadvance = cr.text_extents(text)
            text_x = x_offset_display + (draw_w - width_text) / 2
            text_y = y_offset_display + (draw_h + height_text) / 2
            cr.move_to(text_x, text_y)
            cr.show_text(text)

    def get_profile_data(self):
        proton_version = self.proton_version_combo.get_active_text()
        if proton_version == "None (Use Steam default)" or not proton_version:
            proton_version = None

        player_configs_data = []
        for _, widgets in self.player_config_entries:
            config = {}
            for key, widget in widgets.items():
                if isinstance(widget, Gtk.Entry):
                    config[key] = widget.get_text()
                elif isinstance(widget, Gtk.ComboBox):
                    model = widget.get_model()
                    active_iter = widget.get_active_iter()
                    if active_iter:
                        selected_value = model.get_value(active_iter, 0)
                        # Certifica-se de que a string vazia seja salva como None se for a opção "None"
                        config[key] = selected_value if selected_value != "" else None
                    else:
                        config[key] = None # Define explicitamente como None se nada estiver selecionado
                else:
                    config[key] = ""
            player_configs_data.append(config)

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
            player_configs=self._get_player_configs_from_ui(),
        )

        self.logger.info(f"DEBUG: Mode value before GameProfile instantiation: {mode}")

        if profile_data.splitscreen:
            self.logger.info(f"DEBUG: Splitscreen orientation in GameProfile object: {profile_data.splitscreen.orientation}")

        profile_dumped = profile_data.model_dump(by_alias=True, exclude_unset=False, exclude_defaults=False, mode='json')
        self.logger.info(f"DEBUG: Collecting {len(profile_dumped.get('PLAYERS') or [])} player configs for saving.")
        return profile_dumped

    def load_profile_data(self, profile_data):
        self.game_name_entry.set_text(profile_data.get("GAME_NAME", ""))
        self.exe_path_entry.set_text(str(profile_data.get("EXE_PATH", "")))
        self.num_players_spin.set_value(profile_data.get("NUM_PLAYERS", 1))

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

        self.instance_width_spin.set_value(profile_data.get("INSTANCE_WIDTH", 1920))
        self.instance_height_spin.set_value(profile_data.get("INSTANCE_HEIGHT", 1080))
        self.app_id_entry.set_text(profile_data.get("APP_ID", ""))
        self.game_args_entry.set_text(profile_data.get("GAME_ARGS", ""))
        self.is_native_check.set_active(profile_data.get("IS_NATIVE", False))

        mode = profile_data.get("MODE")
        if mode:
            self.mode_combo.set_active_id(mode)
        else:
            self.mode_combo.set_active_id("None")

        splitscreen_data = profile_data.get("SPLITSCREEN")
        if splitscreen_data:
            splitscreen_orientation = splitscreen_data.get("ORIENTATION")
            if splitscreen_orientation:
                self.splitscreen_orientation_combo.set_active_id(splitscreen_orientation)
            else:
                self.splitscreen_orientation_combo.set_active(0)
        else:
            self.splitscreen_orientation_combo.set_active(0)

        env_vars_data = profile_data.get("ENV_VARS", {})
        for key_entry, value_entry, list_box_row in self.env_var_entries:
            list_box_row.destroy()
        self.env_var_entries.clear()

        if env_vars_data:
            for key, value in env_vars_data.items():
                self._add_env_var_row(key, value)

        self._create_player_config_uis(profile_data.get("NUM_PLAYERS", 1))

        player_configs_data = profile_data.get("PLAYERS", [])
        if player_configs_data:
            for i, player_config_data in enumerate(player_configs_data):
                if i < len(self.player_device_combos):
                    player_combos = self.player_device_combos[i]
                    player_combos["account_name"].set_text(player_config_data.get("ACCOUNT_NAME", ""))
                    player_combos["language"].set_text(player_config_data.get("LANGUAGE", ""))
                    player_combos["listen_port"].set_text(player_config_data.get("LISTEN_PORT", ""))
                    player_combos["user_steam_id"].set_text(player_config_data.get("USER_STEAM_ID", ""))

                    for combo_key, alias_key in [
                        ("physical_device_id", "PHYSICAL_DEVICE_ID"),
                        ("mouse_event_path", "MOUSE_EVENT_PATH"),
                        ("keyboard_event_path", "KEYBOARD_EVENT_PATH"),
                        ("audio_device_id", "AUDIO_DEVICE_ID")
                    ]:
                        selected_value = player_config_data.get(alias_key)
                        if selected_value:
                            model = player_combos[combo_key].get_model()
                            for j, row in enumerate(model):
                                if row[0] == selected_value:
                                    player_combos[combo_key].set_active(j)
                                    break
                            else:
                                if len(player_combos[combo_key].get_model()) > 0:
                                    player_combos[combo_key].set_active(0)

                    # Carrega o Monitor ID para cada jogador
                    monitor_id = player_config_data.get("MONITOR_ID")
                    
                    # Adicionar verificação defensiva para a existência da chave 'MONITOR_ID' no player_combos
                    if "MONITOR_ID" in player_combos:
                        monitor_combo = player_combos["MONITOR_ID"]
                        model = monitor_combo.get_model()

                        # Definir para a opção "None" (índice 0) por padrão
                        if len(model) > 0:
                            monitor_combo.set_active(0)

                        if monitor_id is not None and monitor_id != "": # Se um monitor específico for salvo e não for vazio
                            for j, row in enumerate(model):
                                if row[0] == monitor_id:
                                    monitor_combo.set_active(j)
                                    break
                    else:
                        self.logger.warning(f"MONITOR_ID widget not found for player {i+1} in player_combos. Skipping monitor loading for this player.")

            selected_players = profile_data.get("selected_players")
            if selected_players is None:
                for cb in self.player_checkboxes:
                    cb.set_active(True)
            else:
                for i, cb in enumerate(self.player_checkboxes):
                    cb.set_active((i + 1) in selected_players)
        
        # REMOVED: Load Primary Monitor
        # REMOVED: self.primary_monitor_entry.set_text(profile_data.get("PRIMARY_MONITOR", ""))

    def _create_device_list_store(self, devices: List[Dict[str, str]]) -> Gtk.ListStore:
        list_store = Gtk.ListStore(str, str)
        list_store.append(["", "None"])
        for device in devices:
            list_store.append([device["id"], device["name"]])
        return list_store

class LinuxCoopApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.linuxcoop.app")

    def do_activate(self):
        window = ProfileEditorWindow(self)
        window.show_all()

def run_gui():
    app = LinuxCoopApp()
    app.run(None)

if __name__ == "__main__":
    # This ensures that the GUI is only started if the script is executed directly
    # and not when imported as a module.
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk
    import cairo # Import cairo here for drawing
    # REMOVED: Initialize Gdk for display operations
    # REMOVED: if not Gdk.Display.get_default():
    # REMOVED:     print("Error: Could not get default Gdk Display. Is a display server running?")
    # REMOVED:     sys.exit(1)
    run_gui()
