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
from typing import Dict, List

class ProfileEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Linux Coop Profile Editor")
        self.set_default_size(1000, 700)

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
        self.logger = Logger(name="LinuxCoopGUI", log_dir=Path("./logs"))
        self.proton_service = ProtonService(self.logger)
        
        self.notebook = Gtk.Notebook()
        self.add(self.notebook)

        # Initialize player config entries list
        self.player_config_entries = []

        # Tab 1: General Settings
        self.general_settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.general_settings_page.set_border_width(10)
        self.notebook.append_page(self.general_settings_page, Gtk.Label(label="General Settings"))

        self.general_settings_grid = Gtk.Grid()
        self.general_settings_grid.set_column_spacing(10)
        self.general_settings_grid.set_row_spacing(10)
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

        self.show_all()

    def setup_general_settings(self):
        row = 0

        # Game Name
        self.general_settings_grid.attach(Gtk.Label(label="Game Name:", xalign=0), 0, row, 1, 1)
        self.game_name_entry = Gtk.Entry()
        self.general_settings_grid.attach(self.game_name_entry, 1, row, 1, 1)
        row += 1

        # Exe Path
        self.general_settings_grid.attach(Gtk.Label(label="Executable Path:", xalign=0), 0, row, 1, 1)
        
        exe_path_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.exe_path_entry = Gtk.Entry()
        self.exe_path_entry.set_hexpand(True)
        exe_path_hbox.pack_start(self.exe_path_entry, True, True, 0)
        
        exe_path_button = Gtk.Button(label="Browse...")
        exe_path_button.connect("clicked", self.on_exe_path_button_clicked)
        exe_path_hbox.pack_start(exe_path_button, False, False, 0)

        self.general_settings_grid.attach(exe_path_hbox, 1, row, 1, 1)
        row += 1

        # Proton Version
        self.general_settings_grid.attach(Gtk.Label(label="Proton Version:", xalign=0), 0, row, 1, 1)
        self.proton_version_combo = Gtk.ComboBoxText()
        # Populate with detected Proton versions
        proton_versions = self.proton_service.list_installed_proton_versions()
        if not proton_versions:
            self.proton_version_combo.append_text("No Proton versions found")
            self.proton_version_combo.set_sensitive(False) # Disable if no versions found
        else:
            self.proton_version_combo.append_text("None") # Option for no specific Proton version
            for version in proton_versions:
                self.proton_version_combo.append_text(version)
            self.proton_version_combo.set_active(0) # Select "None" by default

        self.general_settings_grid.attach(self.proton_version_combo, 1, row, 1, 1)
        row += 1

        # App ID
        self.general_settings_grid.attach(Gtk.Label(label="App ID:", xalign=0), 0, row, 1, 1)
        self.app_id_entry = Gtk.Entry()
        self.general_settings_grid.attach(self.app_id_entry, 1, row, 1, 1)
        row += 1

        # Game Args
        self.general_settings_grid.attach(Gtk.Label(label="Game Arguments:", xalign=0), 0, row, 1, 1)
        self.game_args_entry = Gtk.Entry()
        self.general_settings_grid.attach(self.game_args_entry, 1, row, 1, 1)
        row += 1

        # Use Goldberg Emu
        self.general_settings_grid.attach(Gtk.Label(label="Use Goldberg Emulator:", xalign=0), 0, row, 1, 1)
        self.use_goldberg_emu_check = Gtk.CheckButton()
        self.use_goldberg_emu_check.set_active(True) # Default from example.json
        self.general_settings_grid.attach(self.use_goldberg_emu_check, 1, row, 1, 1)
        row += 1

        # Env Vars
        env_vars_frame = Gtk.Frame(label="Environment Variables")
        env_vars_frame.set_margin_top(10)
        env_vars_frame.set_margin_bottom(10)
        self.general_settings_grid.attach(env_vars_frame, 0, row, 2, 1) # Span two columns
        
        env_vars_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        env_vars_frame.add(env_vars_vbox)

        self.env_vars_listbox = Gtk.ListBox()
        self.env_vars_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        env_vars_vbox.pack_start(self.env_vars_listbox, True, True, 0)
        self.env_var_entries = [] # List to store (key_entry, value_entry) tuples

        # Add default env vars
        self._add_env_var_row("WINEDLLOVERRIDES", "")
        self._add_env_var_row("MANGOHUD", "1")

        add_env_var_button = Gtk.Button(label="Add Environment Variable")
        add_env_var_button.connect("clicked", self._on_add_env_var_clicked)
        env_vars_vbox.pack_start(add_env_var_button, False, False, 0)
        row += 1 # Increment row for the next element after env vars frame

        # Add a horizontal box for Save and Load buttons
        button_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.general_settings_page.pack_end(button_hbox, False, False, 0)

        # Save Button
        save_button = Gtk.Button(label="Save Profile")
        save_button.connect("clicked", self.on_save_button_clicked)
        button_hbox.pack_end(save_button, False, False, 0)

        # Load Button
        load_button = Gtk.Button(label="Load Profile")
        load_button.connect("clicked", self.on_load_button_clicked)
        button_hbox.pack_end(load_button, False, False, 0)

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

    def on_load_button_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Load Game Profile",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        # Set the current folder to PROFILE_DIR
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
            except Exception as e:
                self.logger.error(f"Failed to load profile from {file_path}: {e}")
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
        
        # Create a ListBoxRow and add the hbox to it
        list_box_row = Gtk.ListBoxRow()
        list_box_row.add(hbox)

        # Connect the remove button to a lambda that passes the ListBoxRow itself
        remove_button.connect("clicked", lambda btn, row=list_box_row, k_entry=key_entry, v_entry=value_entry: self._remove_env_var_row(btn, row, k_entry, v_entry))
        hbox.pack_end(remove_button, False, False, 0)

        self.env_vars_listbox.add(list_box_row)
        list_box_row.show_all()
        self.env_var_entries.append((key_entry, value_entry, list_box_row)) # Store entries and row for removal

    def _remove_env_var_row(self, button, row, key_entry, value_entry):
        self.env_vars_listbox.remove(row)
        # Remove the tuple from our tracking list
        self.env_var_entries.remove((key_entry, value_entry, row))

    def _get_env_vars_from_ui(self) -> Dict[str, str]:
        env_vars = {}
        for key_entry, value_entry, _ in self.env_var_entries:
            key = key_entry.get_text().strip().upper() # Convert key to ALL CAPS
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
                elif isinstance(widget, Gtk.ComboBox): # Alterado para Gtk.ComboBox
                    model = widget.get_model()
                    active_iter = widget.get_active_iter()
                    if active_iter:
                        selected_id = model.get_value(active_iter, 0) # Obtém o ID (coluna 0)
                        config[key] = selected_id if selected_id != "" else None # Salva None se for a opção "None" do ListStore
                    else:
                        config[key] = None # Nenhum item selecionado
                else:
                    config[key] = ""
            player_configs_data.append(config)
        return player_configs_data

    def setup_player_configs(self):
        self.player_frames = [] # To hold a frame for each player's config
        self.player_device_combos = [] # To hold lists of combo boxes for each player
        
        # Initial creation of player config UIs based on default num_players
        self._create_player_config_uis(self.num_players_spin.get_value_as_int())

    def _create_player_config_uis(self, num_players: int):
        for frame in self.player_frames:
            frame.destroy()
        self.player_frames.clear()
        self.player_device_combos.clear()
        self.player_config_entries.clear()

        # Clear existing widgets in player_config_vbox before repopulating
        for child in self.player_config_vbox.get_children():
            self.player_config_vbox.remove(child)

        for i in range(num_players):
            player_frame = Gtk.Frame(label=f"Player {i+1} Configuration")
            player_frame.set_margin_top(10)
            self.player_config_vbox.pack_start(player_frame, False, False, 0)
            self.player_frames.append(player_frame)

            player_grid = Gtk.Grid()
            player_grid.set_column_spacing(5)
            player_grid.set_row_spacing(5)
            player_grid.set_border_width(5)
            player_frame.add(player_grid)

            player_combos = {
                "account_name": Gtk.Entry(),
                "language": Gtk.Entry(),
                "listen_port": Gtk.Entry(),
                "user_steam_id": Gtk.Entry(),
                "physical_device_id": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["joystick"])),
                "mouse_event_path": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["mouse"])),
                "keyboard_event_path": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_input_devices["keyboard"])),
                "audio_device_id": Gtk.ComboBox.new_with_model(self._create_device_list_store(self.detected_audio_devices))
            }
            self.player_device_combos.append(player_combos)

            # Populate combos with detected devices - REMOVIDO: Já tratado por _create_device_list_store
            # for dev in self.detected_input_devices.get("physical_device_ids", []):
            #     player_combos["physical_device_id"].append_text(dev)
            # player_combos["physical_device_id"].set_active(0)

            # player_combos["mouse_event_path"].append_text("None")
            # for dev in self.detected_input_devices.get("mouse_event_paths", []):
            #     player_combos["mouse_event_path"].append_text(dev)
            # player_combos["mouse_event_path"].set_active(0)
            
            # player_combos["keyboard_event_path"].append_text("None")
            # for dev in self.detected_input_devices.get("keyboard_event_paths", []):
            #     player_combos["keyboard_event_path"].append_text(dev)
            # player_combos["keyboard_event_path"].set_active(0)

            # player_combos["audio_device_id"].append_text("None")
            # for dev in self.detected_audio_devices:
            #     player_combos["audio_device_id"].append_text(dev)
            # player_combos["audio_device_id"].set_active(0)

            # Add fields to player grid
            p_row = 0
            player_grid.attach(Gtk.Label(label="Account Name:", xalign=0), 0, p_row, 1, 1)
            player_grid.attach(player_combos["account_name"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Language:", xalign=0), 0, p_row, 1, 1)
            player_grid.attach(player_combos["language"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Listen Port:", xalign=0), 0, p_row, 1, 1)
            player_grid.attach(player_combos["listen_port"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="User Steam ID:", xalign=0), 0, p_row, 1, 1)
            player_grid.attach(player_combos["user_steam_id"], 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Joystick Device:", xalign=0), 0, p_row, 1, 1)
            physical_device_id_combo = player_combos["physical_device_id"]
            renderer = Gtk.CellRendererText()
            physical_device_id_combo.pack_start(renderer, True)
            physical_device_id_combo.add_attribute(renderer, "text", 1) # Display 'name'
            physical_device_id_combo.set_active(0) # Select "None" by default
            player_grid.attach(physical_device_id_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Mouse Device:", xalign=0), 0, p_row, 1, 1)
            mouse_event_path_combo = player_combos["mouse_event_path"]
            renderer = Gtk.CellRendererText()
            mouse_event_path_combo.pack_start(renderer, True)
            mouse_event_path_combo.add_attribute(renderer, "text", 1) # Display 'name'
            mouse_event_path_combo.set_active(0) # Select "None" by default
            player_grid.attach(mouse_event_path_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Keyboard Device:", xalign=0), 0, p_row, 1, 1)
            keyboard_event_path_combo = player_combos["keyboard_event_path"]
            renderer = Gtk.CellRendererText()
            keyboard_event_path_combo.pack_start(renderer, True)
            keyboard_event_path_combo.add_attribute(renderer, "text", 1) # Display 'name'
            keyboard_event_path_combo.set_active(0) # Select "None" by default
            player_grid.attach(keyboard_event_path_combo, 1, p_row, 1, 1)
            p_row += 1

            player_grid.attach(Gtk.Label(label="Audio Device:", xalign=0), 0, p_row, 1, 1)
            audio_device_id_combo = player_combos["audio_device_id"]
            renderer = Gtk.CellRendererText()
            audio_device_id_combo.pack_start(renderer, True)
            audio_device_id_combo.add_attribute(renderer, "text", 1) # Display 'name'
            audio_device_id_combo.set_active(0) # Select "None" by default
            player_grid.attach(audio_device_id_combo, 1, p_row, 1, 1)
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
            }
            self.player_config_entries.append((player_frame, player_config_widgets))
        self.player_config_vbox.show_all()
        self.logger.info(f"DEBUG: Created {len(self.player_config_entries)} player config UIs.") # Debug line
    
    def on_num_players_changed(self, spin_button):
        num_players = spin_button.get_value_as_int()
        self._create_player_config_uis(num_players)

    def on_mode_changed(self, combo):
        mode = combo.get_active_text()
        if mode == "splitscreen":
            self.splitscreen_orientation_label.show()
            self.splitscreen_orientation_combo.show()
        else:
            self.splitscreen_orientation_label.hide()
            self.splitscreen_orientation_combo.hide()

    def on_save_button_clicked(self, button):
        print("Save button clicked!")
        profile_data_dumped = self.get_profile_data() # This call already uses model_dump(mode='json')

        # DEBUG: Check the type of the 'exe_path' field within the dumped data
        if "EXE_PATH" in profile_data_dumped:
            print(f"DEBUG: Type of EXE_PATH in dumped data: {type(profile_data_dumped['EXE_PATH'])}")
            print(f"DEBUG: Value of EXE_PATH in dumped data: {profile_data_dumped['EXE_PATH']}")

        # Save the profile data to a JSON file
        profile_name = self.game_name_entry.get_text().replace(" ", "_").lower()
        if not profile_name:
            # Handle case where game name is empty
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       "Game Name cannot be empty.")
            dialog.run()
            dialog.destroy()
            return

        profile_dir = Path.home() / ".config/linux-coop/profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir / f"{profile_name}.json"

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data_dumped, f, indent=2)
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                                       f"Profile saved successfully to {profile_path}")
            dialog.run()
            dialog.destroy()
        except Exception as e:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                       f"Error saving profile: {e}")
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

        # Calculate scaling factor to fit preview within drawing area
        drawing_area_width = widget.get_allocated_width()
        drawing_area_height = widget.get_allocated_height()

        if width == 0 or height == 0:
            return

        scale_w = drawing_area_width / width
        scale_h = drawing_area_height / height
        scale = min(scale_w, scale_h) * 0.9 # Use 90% of available space

        # These are the scaled dimensions of the total 'screen' area, not individual windows
        scaled_total_width = width * scale
        scaled_total_height = height * scale

        # Calculate offsets to center the overall layout
        x_offset_display = (drawing_area_width - scaled_total_width) / 2
        y_offset_display = (drawing_area_height - scaled_total_height) / 2

        try:
            dummy_profile = GameProfile(
                GAME_NAME="Preview",
                EXE_PATH=None,
                NUM_PLAYERS=num_players,
                INSTANCE_WIDTH=width,
                INSTANCE_HEIGHT=height,
                MODE=mode,
                SPLITSCREEN=SplitscreenConfig(orientation=orientation) if mode == "splitscreen" else None,
                PLAYER_PHYSICAL_DEVICE_IDS=[],
                PLAYER_MOUSE_EVENT_PATHS=[],
                PLAYER_KEYBOARD_EVENT_PATHS=[],
                PLAYER_AUDIO_DEVICE_IDS=[],
                is_native=False,
                use_goldberg_emu=False
            )
        except Exception as e:
            print(f"Error creating dummy profile: {e}")
            return

        cr.set_line_width(2)

        if mode == "splitscreen" and num_players > 1:
            if num_players == 2:
                instance_w, instance_h = dummy_profile.get_instance_dimensions(1)
                draw_w = instance_w * scale
                draw_h = instance_h * scale

                if orientation == "horizontal":
                    # Two windows side-by-side (each half width, full height)
                    # Player 1
                    cr.rectangle(x_offset_display, y_offset_display, draw_w, scaled_total_height)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()
                    # Player 2
                    cr.rectangle(x_offset_display + draw_w, y_offset_display, draw_w, scaled_total_height)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()
                else: # vertical
                    # Two windows top-bottom (each full width, half height)
                    # Player 1
                    cr.rectangle(x_offset_display, y_offset_display, scaled_total_width, draw_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()
                    # Player 2
                    cr.rectangle(x_offset_display, y_offset_display + draw_h, scaled_total_width, draw_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

            elif num_players == 3:
                if orientation == "horizontal": # One large top, two small bottom
                    # Player 1 (top, full width, half height)
                    # Use get_instance_dimensions for precise dimensions
                    inst1_w, inst1_h = dummy_profile.get_instance_dimensions(1)
                    draw_inst1_w = inst1_w * scale
                    draw_inst1_h = inst1_h * scale
                    cr.rectangle(x_offset_display, y_offset_display, draw_inst1_w, draw_inst1_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

                    # Players 2 & 3 (bottom half, split horizontally)
                    inst2_w, inst2_h = dummy_profile.get_instance_dimensions(2) # Dimensions for subsequent players
                    draw_inst2_w = inst2_w * scale
                    draw_inst2_h = inst2_h * scale

                    # Player 2
                    cr.rectangle(x_offset_display, y_offset_display + draw_inst1_h, draw_inst2_w, draw_inst2_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

                    # Player 3
                    cr.rectangle(x_offset_display + draw_inst2_w, y_offset_display + draw_inst1_h, draw_inst2_w, draw_inst2_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

                else: # vertical # One large left, two small right
                    # Player 1 (left, half width, full height)
                    inst1_w, inst1_h = dummy_profile.get_instance_dimensions(1)
                    draw_inst1_w = inst1_w * scale
                    draw_inst1_h = inst1_h * scale
                    cr.rectangle(x_offset_display, y_offset_display, draw_inst1_w, draw_inst1_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

                    # Players 2 & 3 (right half, split vertically)
                    inst2_w, inst2_h = dummy_profile.get_instance_dimensions(2)
                    draw_inst2_w = inst2_w * scale
                    draw_inst2_h = inst2_h * scale

                    # Player 2
                    cr.rectangle(x_offset_display + draw_inst1_w, y_offset_display, draw_inst2_w, draw_inst2_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

                    # Player 3
                    cr.rectangle(x_offset_display + draw_inst1_w, y_offset_display + draw_inst2_h, draw_inst2_w, draw_inst2_h)
                    cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                    cr.stroke()

            elif num_players == 4:
                # 2x2 Grid, all windows are the same size
                instance_w, instance_h = dummy_profile.get_instance_dimensions(1)
                draw_w = instance_w * scale
                draw_h = instance_h * scale

                # Player 1 (Top-Left)
                cr.rectangle(x_offset_display, y_offset_display, draw_w, draw_h)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                cr.stroke()

                # Player 2 (Top-Right)
                cr.rectangle(x_offset_display + draw_w, y_offset_display, draw_w, draw_h)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                cr.stroke()

                # Player 3 (Bottom-Left)
                cr.rectangle(x_offset_display, y_offset_display + draw_h, draw_w, draw_h)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                cr.stroke()

                # Player 4 (Bottom-Right)
                cr.rectangle(x_offset_display + draw_w, y_offset_display + draw_h, draw_w, draw_h)
                cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                cr.stroke()
            
            else: # General case for more than 4 players, or other splits (uniform horizontal/vertical)
                current_x = x_offset_display
                current_y = y_offset_display

                if orientation == "horizontal": # Stacked vertically
                    for i in range(num_players):
                        instance_w, instance_h = dummy_profile.get_instance_dimensions(i + 1)
                        draw_h = instance_h * scale # Width will be scaled_total_width
                        
                        cr.rectangle(x_offset_display, current_y, scaled_total_width, draw_h)
                        cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                        cr.stroke()
                        current_y += draw_h
                else: # vertical (Side by side)
                    for i in range(num_players):
                        instance_w, instance_h = dummy_profile.get_instance_dimensions(i + 1)
                        draw_w = instance_w * scale # Height will be scaled_total_height
                        
                        cr.rectangle(current_x, y_offset_display, draw_w, scaled_total_height)
                        cr.set_source_rgb(1.0, 1.0, 1.0) # White border
                        cr.stroke()
                        current_x += draw_w

        else: # None or single player
            instance_w, instance_h = dummy_profile.get_instance_dimensions(1)
            draw_w = instance_w * scale
            draw_h = instance_h * scale
            cr.rectangle(x_offset_display, y_offset_display, draw_w, draw_h)
            cr.set_source_rgb(1.0, 1.0, 1.0) # White border
            cr.stroke()

    def get_profile_data(self):
        proton_version = self.proton_version_combo.get_active_text()
        if proton_version == "None" or not proton_version:
            proton_version = None

        player_configs_data = []
        for _, widgets in self.player_config_entries:
            config = {}
            for key, widget in widgets.items():
                if isinstance(widget, Gtk.Entry):
                    config[key] = widget.get_text()
                elif isinstance(widget, Gtk.ComboBox): # Alterado para Gtk.ComboBox
                    model = widget.get_model()
                    active_iter = widget.get_active_iter()
                    if active_iter:
                        selected_id = model.get_value(active_iter, 0) # Obtém o ID (coluna 0)
                        config[key] = selected_id if selected_id != "" else None # Salva None se for a opção "None" do ListStore
                    else:
                        config[key] = None # Nenhum item selecionado
                else:
                    config[key] = ""
            player_configs_data.append(config)

        splitscreen_config = None
        if self.mode_combo.get_active_text() == "splitscreen":
            selected_orientation = self.splitscreen_orientation_combo.get_active_text()
            self.logger.info(f"DEBUG: Selected splitscreen orientation from UI: {selected_orientation}") # Debug line
            splitscreen_config = SplitscreenConfig(
                orientation=selected_orientation
            )
            self.logger.info(f"DEBUG: SplitscreenConfig orientation immediately after creation: {splitscreen_config.orientation}") # NEW DEBUG LINE
        
        is_native_value = not Path(self.exe_path_entry.get_text()).name.lower().endswith('.exe')

        mode = self.mode_combo.get_active_text()

        profile_data = GameProfile(
            game_name=self.game_name_entry.get_text(),
            exe_path=self.exe_path_entry.get_text(),
            num_players=self.num_players_spin.get_value_as_int(),
            proton_version=proton_version,
            instance_width=self.instance_width_spin.get_value_as_int(),
            instance_height=self.instance_height_spin.get_value_as_int(),
            app_id=self.app_id_entry.get_text() or None,
            game_args=self.game_args_entry.get_text() or None,
            is_native=is_native_value,
            mode=mode,
            splitscreen=splitscreen_config,
            env_vars=self._get_env_vars_from_ui(),
            player_configs=player_configs_data,
            use_goldberg_emu=self.use_goldberg_emu_check.get_active()
        )
        
        # DEBUG: Check the mode value right before GameProfile instantiation
        self.logger.info(f"DEBUG: Mode value before GameProfile instantiation: {mode}")

        # DEBUG: Check the orientation directly from the GameProfile object before dumping
        if profile_data.splitscreen:
            self.logger.info(f"DEBUG: Splitscreen orientation in GameProfile object: {profile_data.splitscreen.orientation}")

        profile_dumped = profile_data.model_dump(by_alias=True, exclude_unset=False, exclude_defaults=False, mode='json')
        self.logger.info(f"DEBUG: Collecting {len(profile_dumped.get('PLAYERS', []))} player configs for saving.") # Debug line
        return profile_dumped

    def load_profile_data(self, profile_data):
        self.game_name_entry.set_text(profile_data.get("GAME_NAME", ""))
        self.exe_path_entry.set_text(str(profile_data.get("EXE_PATH", "")))
        self.num_players_spin.set_value(profile_data.get("NUM_PLAYERS", 1))
        
        # Set Proton Version Combo Box
        proton_version = profile_data.get("PROTON_VERSION")
        if proton_version:
            # Try to find the index of the version in the combo box
            model = self.proton_version_combo.get_model()
            for i, row in enumerate(model):
                if row[0] == proton_version:
                    self.proton_version_combo.set_active(i)
                    break
            else:
                # If not found, set to "None" or first item
                self.proton_version_combo.set_active(0) # This would be "None" if present
        else:
            self.proton_version_combo.set_active(0) # Default to "None"

        self.instance_width_spin.set_value(profile_data.get("INSTANCE_WIDTH", 1920))
        self.instance_height_spin.set_value(profile_data.get("INSTANCE_HEIGHT", 1080))
        self.app_id_entry.set_text(profile_data.get("APP_ID", ""))
        self.game_args_entry.set_text(profile_data.get("GAME_ARGS", ""))

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
                self.splitscreen_orientation_combo.set_active(0) # Default to horizontal or first item
        else:
            self.splitscreen_orientation_combo.set_active(0) # Default to horizontal or first item

        self.use_goldberg_emu_check.set_active(profile_data.get("USE_GOLDBERG_EMU", True))

        # Load environment variables
        for key_entry, value_entry, list_box_row in self.env_var_entries:
            list_box_row.destroy() # Clear existing rows before loading new ones
        self.env_var_entries.clear()

        env_vars = profile_data.get("ENV_VARS", {})
        if env_vars:
            for key, value in env_vars.items():
                self._add_env_var_row(key, value)
        
        # Load player configurations
        self._create_player_config_uis(profile_data.get("NUM_PLAYERS", 1)) # Re-create based on num_players

        player_configs_data = profile_data.get("PLAYERS", [])
        if player_configs_data:
            for i, player_config_data in enumerate(player_configs_data):
                if i < len(self.player_device_combos):
                    player_combos = self.player_device_combos[i]
                    player_combos["account_name"].set_text(player_config_data.get("ACCOUNT_NAME", ""))
                    player_combos["language"].set_text(player_config_data.get("LANGUAGE", ""))
                    player_combos["listen_port"].set_text(player_config_data.get("LISTEN_PORT", ""))
                    player_combos["user_steam_id"].set_text(player_config_data.get("USER_STEAM_ID", ""))
                    
                    # Set ComboBoxText for device IDs/paths
                    for combo_key, alias_key in [
                        ("physical_device_id", "PHYSICAL_DEVICE_ID"),
                        ("mouse_event_path", "MOUSE_EVENT_PATH"),
                        ("keyboard_event_path", "KEYBOARD_EVENT_PATH"),
                        ("audio_device_id", "AUDIO_DEVICE_ID")
                    ]:
                        selected_value = player_config_data.get(alias_key) # Use alias_key to get ALL CAPS value
                        if selected_value:
                            model = player_combos[combo_key].get_model()
                            for j, row in enumerate(model):
                                if row[0] == selected_value:
                                    player_combos[combo_key].set_active(j)
                                    break
                            else:
                                # If not found, set to "None" or first item
                                player_combos[combo_key].set_active(0)
                        else:
                            player_combos[combo_key].set_active(0)

    def _create_device_list_store(self, devices: List[Dict[str, str]]) -> Gtk.ListStore:
        list_store = Gtk.ListStore(str, str) # id, name
        list_store.append(["", "None"]) # Add "None" option as the first choice
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
    run_gui() 