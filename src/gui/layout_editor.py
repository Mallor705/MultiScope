import gi
import os
from ..models.profile import SplitscreenConfig, PlayerInstanceConfig

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from ..services.device_manager import DeviceManager
from ..services.game_manager import GameManager
from gi.repository import Adw, Gdk, GObject, Gtk, Pango, Gio
from .dialogs import ConfirmationDialog, TextInputDialog


class ProfileRow(GObject.Object):
    name = GObject.Property(type=str)

    def __init__(self, name):
        super().__init__()
        self.name = name

class LayoutSettingsPage(Adw.PreferencesPage):
    __gsignals__ = {
        "settings-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "profile-selected": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, game, logger, **kwargs):
        super().__init__(**kwargs)
        self._is_loading = False
        self.game = game
        self.profile = None
        self.player_rows = []
        self.logger = logger

        # Initialize services
        self.device_manager = DeviceManager()
        self.game_manager = GameManager(self.logger)

        # Get device lists
        self.input_devices = self.device_manager.get_input_devices()
        self.audio_devices = self.device_manager.get_audio_devices()
        self.display_outputs = self.device_manager.get_display_outputs()

        self._build_ui()
        if game:
            self.update_for_game(game)

    def _build_ui(self):
        self.set_title("Layout Settings")

        # Grupo de Perfis
        profile_group = Adw.PreferencesGroup(title="Profile Management")
        self.add(profile_group)

        self.profile_model = Gio.ListStore.new(ProfileRow)
        self.profile_selector_row = Adw.ComboRow(
            title="Active Profile", model=self.profile_model
        )
        self._setup_profile_factory()
        self.profile_selector_row.connect(
            "notify::selected-item", self._on_profile_selected
        )
        profile_group.add(self.profile_selector_row)

        save_profile_button = Gtk.Button(label="New Profile")
        save_profile_button.connect("clicked", self._on_save_as_new_profile)
        action_row = Adw.ActionRow()
        action_row.add_suffix(save_profile_button)
        profile_group.add(action_row)

        layout_group = Adw.PreferencesGroup()
        self.add(layout_group)

        self.num_players_row = Adw.SpinRow(
            title="Number of Players",
            subtitle="Changing this will reset player configs",
        )
        adjustment = Gtk.Adjustment(value=2, lower=1, upper=8, step_increment=1)
        self.num_players_row.set_adjustment(adjustment)
        adjustment.connect("value-changed", self._on_num_players_changed)
        layout_group.add(self.num_players_row)

        # Resolução
        self.resolutions = ["Custom", "1920x1080", "2560x1440", "1280x720", "800x600"]
        self.resolution_row = Adw.ComboRow(
            title="Resolution", model=Gtk.StringList.new(self.resolutions)
        )
        self.resolution_row.connect(
            "notify::selected-item", self._on_resolution_changed
        )
        self.resolution_row.connect("notify::selected-item", self._on_setting_changed)
        layout_group.add(self.resolution_row)

        self.instance_width_row = Adw.EntryRow(title="Custom Instance Width")
        self.instance_width_row.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.instance_width_row.set_visible(False)
        self.instance_width_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_width_row)

        self.instance_height_row = Adw.EntryRow(title="Custom Instance Height")
        self.instance_height_row.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.instance_height_row.set_visible(False)
        self.instance_height_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_height_row)

        # Modo de Tela
        self.screen_modes = ["Fullscreen", "Splitscreen"]
        self.screen_mode_row = Adw.ComboRow(
            title="Screen Mode", model=Gtk.StringList.new(self.screen_modes)
        )
        self.screen_mode_row.connect("notify::selected-item", self._on_screen_mode_changed)
        layout_group.add(self.screen_mode_row)

        # Orientação do Splitscreen
        self.orientations = ["Horizontal", "Vertical"]
        self.orientation_row = Adw.ComboRow(
            title="Splitscreen Orientation", model=Gtk.StringList.new(self.orientations)
        )
        self.orientation_row.connect("notify::selected-item", self._on_setting_changed)
        self.orientation_row.set_visible(False)  # Oculto por padrão
        layout_group.add(self.orientation_row)

        # Player Configurations Group
        self.players_group = Adw.PreferencesGroup(title="Player Configurations")
        self.add(self.players_group)

    def update_for_game(self, game):
        self._is_loading = True
        try:
            self.game = game
            selected_idx = self.update_profile_list()

            default_profile = self.game_manager.get_profile(self.game, "Default")
            if default_profile:
                self.profile = default_profile
                self.profile_selector_row.set_selected(selected_idx)
            else:
                self.profile = Profile(profile_name="Default")
                self.game_manager.add_profile(self.game, self.profile)
                self.update_profile_list()

            self.load_profile_data()
        finally:
            self._is_loading = False

    def load_profile_data(self):
        self._is_loading = True
        try:
            # Load general layout settings
            adjustment = self.num_players_row.get_adjustment()
            adjustment.set_value(self.profile.num_players)

            width = self.profile.instance_width
            height = self.profile.instance_height
            resolution_str = f"{width}x{height}"

            if width and height and resolution_str in self.resolutions:
                for i, res in enumerate(self.resolutions):
                    if res == resolution_str:
                        self.resolution_row.set_selected(i)
                        break
                self.instance_width_row.set_visible(False)
                self.instance_height_row.set_visible(False)
            else:
                self.resolution_row.set_selected(0)  # "Custom"
                self.instance_width_row.set_text(str(width) if width is not None else "")
                self.instance_height_row.set_text(str(height) if height is not None else "")
                self.instance_width_row.set_visible(True)
                self.instance_height_row.set_visible(True)

            if self.profile.mode == "splitscreen":
                self.screen_mode_row.set_selected(1)
                self.orientation_row.set_visible(True)
                if self.profile.splitscreen:
                    orientation = self.profile.splitscreen.orientation.capitalize()
                    if orientation in self.orientations:
                        self.orientation_row.set_selected(self.orientations.index(orientation))
            else:
                self.screen_mode_row.set_selected(0)
                self.orientation_row.set_visible(False)

            # Load player-specific settings
            self.rebuild_player_rows_for_profile(self.profile)
            for i, row_dict in enumerate(self.player_rows):
                if self.profile.player_configs and i < len(self.profile.player_configs):
                    config = self.profile.player_configs[i]
                    row_dict["account_name"].set_text(config.ACCOUNT_NAME or "")
                    row_dict["language"].set_text(config.LANGUAGE or "")
                    row_dict["listen_port"].set_text(config.LISTEN_PORT or "")
                    row_dict["user_steam_id"].set_text(config.USER_STEAM_ID or "")
                    self._set_combo_row_selection(row_dict["joystick"], self.input_devices["joystick"], config.PHYSICAL_DEVICE_ID)
                    self._set_combo_row_selection(row_dict["mouse"], self.input_devices["mouse"], config.MOUSE_EVENT_PATH)
                    self._set_combo_row_selection(row_dict["keyboard"], self.input_devices["keyboard"], config.KEYBOARD_EVENT_PATH)
                    self._set_combo_row_selection(row_dict["audio"], self.audio_devices, config.AUDIO_DEVICE_ID)
                    self._set_combo_row_selection(row_dict["monitor"], self.display_outputs, config.monitor_id)
        finally:
            self._is_loading = False
    def _set_combo_row_selection(self, combo_row, device_list, device_id):
        if not device_id:
            combo_row.set_selected(0)  # "None"
            return

        id_to_match = device_id
        if device_id.startswith("/dev/input"):
            try:
                id_to_match = os.path.realpath(device_id)
            except Exception:
                pass

        for i, device in enumerate(device_list):
            current_device_id = device["id"]
            if current_device_id.startswith("/dev/input"):
                try:
                    current_device_id = os.path.realpath(current_device_id)
                except Exception:
                    pass

            if current_device_id == id_to_match:
                combo_row.set_selected(i + 1)
                return

        combo_row.set_selected(0)

    def get_updated_data(self):
        if not self.profile:
            return None

        self.profile.num_players = int(self.num_players_row.get_value())

        selected_res_item = self.resolution_row.get_selected_item()
        if selected_res_item:
            selected_res = selected_res_item.get_string()
            if selected_res == "Custom":
                width_text = self.instance_width_row.get_text()
                self.profile.instance_width = (
                    int(width_text) if width_text.isdigit() else None
                )
                height_text = self.instance_height_row.get_text()
                self.profile.instance_height = (
                    int(height_text) if height_text.isdigit() else None
                )
            else:
                try:
                    width, height = map(int, selected_res.split("x"))
                    self.profile.instance_width = width
                    self.profile.instance_height = height
                except (ValueError, IndexError):
                    self.profile.instance_width = None
                    self.profile.instance_height = None

        # Atualizar modo de tela e orientação
        selected_mode_item = self.screen_mode_row.get_selected_item()
        if selected_mode_item:
            selected_mode = selected_mode_item.get_string().lower()
            self.profile.mode = selected_mode
            if selected_mode == "splitscreen":
                selected_orientation_item = self.orientation_row.get_selected_item()
                if selected_orientation_item:
                    orientation = selected_orientation_item.get_string().lower()
                    self.profile.splitscreen = SplitscreenConfig(orientation=orientation)
            else:
                self.profile.splitscreen = None

        new_configs = []
        for row_dict in self.player_rows:
            new_config = PlayerInstanceConfig(
                ACCOUNT_NAME=row_dict["account_name"].get_text() or None,
                LANGUAGE=row_dict["language"].get_text() or None,
                LISTEN_PORT=row_dict["listen_port"].get_text() or None,
                USER_STEAM_ID=row_dict["user_steam_id"].get_text() or None,
                PHYSICAL_DEVICE_ID=self._get_combo_row_device_id(
                    row_dict["joystick"], self.input_devices["joystick"]
                ),
                MOUSE_EVENT_PATH=self._get_combo_row_device_id(
                    row_dict["mouse"], self.input_devices["mouse"]
                ),
                KEYBOARD_EVENT_PATH=self._get_combo_row_device_id(
                    row_dict["keyboard"], self.input_devices["keyboard"]
                ),
                AUDIO_DEVICE_ID=self._get_combo_row_device_id(
                    row_dict["audio"], self.audio_devices
                ),
                monitor_id=self._get_combo_row_device_id(
                    row_dict["monitor"], self.display_outputs
                ),
            )
            new_configs.append(new_config)
        self.profile.player_configs = new_configs

        return self.profile

    def _on_setting_changed(self, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_num_players_changed(self, adjustment):
        if not self._is_loading:
            self.profile.num_players = int(adjustment.get_value())
            self.rebuild_player_rows_for_profile(self.profile)
            self.emit("settings-changed")

    def _on_resolution_changed(self, combo_row, selected_item_prop):
        selected_item = combo_row.get_selected_item()
        if not selected_item:
            return

        is_custom = selected_item.get_string() == "Custom"
        self.instance_width_row.set_visible(is_custom)
        self.instance_height_row.set_visible(is_custom)

    def _on_screen_mode_changed(self, combo_row, selected_item_prop):
        selected_item = combo_row.get_selected_item()
        if not selected_item:
            return

        is_splitscreen = selected_item.get_string().lower() == "splitscreen"
        self.orientation_row.set_visible(is_splitscreen)
        self._on_setting_changed()

    def _setup_profile_factory(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_setup_profile_row)
        factory.connect("bind", self._on_bind_profile_row)
        self.profile_selector_row.set_factory(factory)

    def _on_setup_profile_row(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)

        popover = Gtk.Popover.new()
        list_item.popover = popover
        box.connect("destroy", lambda w: popover.unparent())

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        popover.set_child(popover_box)

        delete_button = Gtk.Button(label="Delete")
        delete_button.get_style_context().add_class("flat")
        popover_box.append(delete_button)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", lambda g, n, x, y: popover.popup())
        box.add_controller(gesture)

    def _on_bind_profile_row(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        profile_row = list_item.get_item()
        label.set_text(profile_row.name)

        popover = list_item.popover
        popover.set_parent(list_item.get_child())
        delete_button = popover.get_child().get_first_child()

        if hasattr(delete_button, "handler_id"):
            delete_button.disconnect(delete_button.handler_id)

        if profile_row.name == "Default":
            delete_button.set_sensitive(False)
            delete_button.set_tooltip_text("The Default profile cannot be deleted.")
        else:
            delete_button.set_sensitive(True)
            delete_button.set_tooltip_text("")
            delete_button.handler_id = delete_button.connect(
                "clicked", self._on_delete_profile, profile_row, popover
            )

    def _on_delete_profile(self, button, profile_row, popover):
        popover.popdown()
        profile = self.game_manager.get_profile(self.game, profile_row.name)
        if profile:
            dialog = ConfirmationDialog(
                self.get_root(),
                "Delete Profile?",
                f"Are you sure you want to delete the profile '{profile.profile_name}'?",
            )
            dialog.connect(
                "response",
                lambda d, r: self._on_delete_profile_confirmed(d, r, profile),
            )
            dialog.present()

    def _on_delete_profile_confirmed(self, dialog, response_id, profile):
        if response_id == "ok":
            current_profile_name = self.profile.profile_name
            self.game_manager.delete_profile(self.game, profile)

            if current_profile_name == profile.profile_name:
                self.update_for_game(self.game)
            else:
                self.update_profile_list(current_profile_name)

        dialog.destroy()

    def update_profile_list(self, selected_name=None):
        self.profile_model.remove_all()
        profiles = self.game_manager.get_profiles(self.game)
        profile_rows = [ProfileRow("Default")] + [
            ProfileRow(p.profile_name) for p in profiles
        ]

        selected_idx = 0
        for i, p_row in enumerate(profile_rows):
            self.profile_model.append(p_row)
            if selected_name and p_row.name == selected_name:
                selected_idx = i

        return selected_idx

    def _on_profile_selected(self, combo_row, selected_item_prop):
        if self.profile is None or self._is_loading:
            return

        selected_item = combo_row.get_selected_item()
        if not selected_item:
            return

        profile_name = selected_item.name
        if profile_name == self.profile.profile_name:
            return

        selected_profile = self.game_manager.get_profile(self.game, profile_name)
        if selected_profile:
            self.profile = selected_profile
            self.load_profile_data()
            self.emit("profile-selected", self.profile)

    def _on_save_as_new_profile(self, button):
        dialog = TextInputDialog(
            self.get_root(), "Save New Profile", "Enter the name for the new profile:"
        )
        dialog.connect("response", self._on_save_as_new_profile_dialog_response)
        dialog.present()

    def _on_save_as_new_profile_dialog_response(self, dialog, response_id):
        if response_id == "ok":
            profile_name = dialog.get_input()
            if profile_name and profile_name != "Default":
                new_profile = self.get_updated_data()
                new_profile.profile_name = profile_name

                try:
                    self.game_manager.add_profile(self.game, new_profile)
                    selected_idx = self.update_profile_list(profile_name)
                    self.profile_selector_row.set_selected(selected_idx)
                except FileExistsError:
                    self.logger.error(
                        f"Profile '{profile_name}' already exists."
                    )
        dialog.destroy()

    def rebuild_player_rows_for_profile(self, profile):
        self.profile = profile
        for row_dict in self.player_rows:
            self.players_group.remove(row_dict["expander"])
        self.player_rows = []

        num_players = self.profile.num_players if self.profile else 0

        for i in range(num_players):
            player_expander = Adw.ExpanderRow(title=f"Player {i + 1}")
            self.players_group.add(player_expander)

            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)
            player_expander.add_prefix(checkbox)

            account_name_row = Adw.EntryRow(title="Account Name")
            account_name_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(account_name_row)

            language_row = Adw.EntryRow(title="Language")
            language_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(language_row)

            listen_port_row = Adw.EntryRow(title="Listen Port")
            listen_port_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(listen_port_row)

            user_steam_id_row = Adw.EntryRow(title="User Steam ID")
            user_steam_id_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(user_steam_id_row)

            joystick_model = Gtk.StringList.new(
                ["None"] + [d["name"] for d in self.input_devices["joystick"]]
            )
            joystick_row = Adw.ComboRow(title="Gamepad", model=joystick_model)
            joystick_row.connect("notify::selected-item", self._on_setting_changed)
            player_expander.add_row(joystick_row)

            mouse_model = Gtk.StringList.new(
                ["None"] + [d["name"] for d in self.input_devices["mouse"]]
            )
            mouse_row = Adw.ComboRow(title="Mouse", model=mouse_model)
            mouse_row.connect("notify::selected-item", self._on_setting_changed)
            player_expander.add_row(mouse_row)

            keyboard_model = Gtk.StringList.new(
                ["None"] + [d["name"] for d in self.input_devices["keyboard"]]
            )
            keyboard_row = Adw.ComboRow(title="Keyboard", model=keyboard_model)
            keyboard_row.connect("notify::selected-item", self._on_setting_changed)
            player_expander.add_row(keyboard_row)

            audio_model = Gtk.StringList.new(
                ["None"] + [d["name"] for d in self.audio_devices]
            )
            audio_row = Adw.ComboRow(title="Audio Device", model=audio_model)
            audio_row.connect("notify::selected-item", self._on_setting_changed)
            player_expander.add_row(audio_row)

            monitor_model = Gtk.StringList.new(
                ["None"] + [d["name"] for d in self.display_outputs]
            )
            monitor_row = Adw.ComboRow(title="Monitor", model=monitor_model)
            monitor_row.connect("notify::selected-item", self._on_setting_changed)
            player_expander.add_row(monitor_row)

            self.player_rows.append(
                {
                    "checkbox": checkbox,
                    "expander": player_expander,
                    "account_name": account_name_row,
                    "language": language_row,
                    "listen_port": listen_port_row,
                    "user_steam_id": user_steam_id_row,
                    "joystick": joystick_row,
                    "mouse": mouse_row,
                    "keyboard": keyboard_row,
                    "audio": audio_row,
                    "monitor": monitor_row,
                }
            )

    def get_selected_players(self) -> list[int]:
        selected = []
        for i, row_data in enumerate(self.player_rows):
            if row_data["checkbox"].get_active():
                selected.append(i + 1)
        return selected

    def _get_combo_row_device_id(self, combo_row, device_list):
        selected_index = combo_row.get_selected()
        if selected_index <= 0:
            return None
        device_index = selected_index - 1
        if device_index < len(device_list):
            return device_list[device_index]["id"]
        return None
