import gi
import os
from ..models.profile import Profile, SplitscreenConfig, PlayerInstanceConfig

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from ..services.device_manager import DeviceManager
from ..services.verification_service import VerificationService
from gi.repository import Adw, Gdk, GObject, Gtk

from ..services.instance import InstanceService


class LayoutSettingsPage(Adw.PreferencesPage):
    __gsignals__ = {
        "settings-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "instance-state-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, profile, logger, **kwargs):
        super().__init__(**kwargs)
        self._is_loading = False
        self.profile = profile
        self.player_rows = []
        self.logger = logger
        self.instance_service = InstanceService(logger)
        self.verification_service = VerificationService(logger)
        self.device_manager = DeviceManager()
        self.input_devices = self.device_manager.get_input_devices()
        self.audio_devices = self.device_manager.get_audio_devices()
        self.display_outputs = self.device_manager.get_display_outputs()

        self._build_ui()
        self.load_profile_data()
        self._run_verification()

    def _build_ui(self):
        self.set_title("Layout Settings")

        layout_group = Adw.PreferencesGroup(title="General Layout")
        layout_group.get_style_context().add_class("general-layout-group")
        self.add(layout_group)

        self.num_players_row = Adw.SpinRow(
            title="Number of Instances",
            subtitle="How many Steam instances to launch",
        )
        self.num_players_row.get_style_context().add_class("num-players-row")
        adjustment = Gtk.Adjustment(value=2, lower=1, upper=8, step_increment=1)
        self.num_players_row.set_adjustment(adjustment)
        adjustment.connect("value-changed", self._on_num_players_changed)
        layout_group.add(self.num_players_row)

        self.resolutions = ["Custom", "1920x1080", "2560x1440", "1280x720", "800x600"]
        self.resolution_row = Adw.ComboRow(
            title="Base Resolution", model=Gtk.StringList.new(self.resolutions)
        )
        self.resolution_row.get_style_context().add_class("resolution-row")
        self.resolution_row.connect("notify::selected-item", self._on_resolution_changed)
        self.resolution_row.connect("notify::selected-item", self._on_setting_changed)
        layout_group.add(self.resolution_row)

        self.instance_width_row = Adw.EntryRow(title="Custom Width")
        self.instance_width_row.get_style_context().add_class("instance-width-row")
        self.instance_width_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_width_row)

        self.instance_height_row = Adw.EntryRow(title="Custom Height")
        self.instance_height_row.get_style_context().add_class("instance-height-row")
        self.instance_height_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_height_row)

        self.screen_modes = ["Fullscreen", "Splitscreen"]
        self.screen_mode_row = Adw.ComboRow(
            title="Screen Mode", model=Gtk.StringList.new(self.screen_modes)
        )
        self.screen_mode_row.get_style_context().add_class("screen-mode-row")
        self.screen_mode_row.connect("notify::selected-item", self._on_screen_mode_changed)
        layout_group.add(self.screen_mode_row)

        self.orientations = ["Horizontal", "Vertical"]
        self.orientation_row = Adw.ComboRow(
            title="Splitscreen Orientation", model=Gtk.StringList.new(self.orientations)
        )
        self.orientation_row.get_style_context().add_class("orientation-row")
        self.orientation_row.connect("notify::selected-item", self._on_setting_changed)
        layout_group.add(self.orientation_row)

        # Gamescope toggle
        self.use_gamescope_row = Adw.SwitchRow(
            title="Use Gamescope",
            subtitle="Disable to run Steam directly in bwrap without Gamescope"
        )
        self.use_gamescope_row.get_style_context().add_class("use-gamescope-row")
        self.use_gamescope_row.connect("notify::active", self._on_setting_changed)
        layout_group.add(self.use_gamescope_row)

        # Global environment variables
        self.env_group = Adw.PreferencesGroup(title="Environment Variables (Global)")
        self.env_group.get_style_context().add_class("global-env-group")
        self.add(self.env_group)
        self.global_env_rows = []

        self.global_env_add_row = Adw.ActionRow(title="Add environment variable")
        self.global_env_add_row.get_style_context().add_class("global-env-add-row")
        global_add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        global_add_btn.get_style_context().add_class("add-button")
        global_add_btn.set_valign(Gtk.Align.CENTER)
        global_add_btn.connect("clicked", self._on_add_global_env_clicked)
        self.global_env_add_row.add_suffix(global_add_btn)
        self.env_group.add(self.global_env_add_row)

        self.players_group = Adw.PreferencesGroup(title="Instance Configurations")
        self.players_group.get_style_context().add_class("players-group")
        self.add(self.players_group)

    def load_profile_data(self):
        self._is_loading = True

        adj = self.num_players_row.get_adjustment()
        adj.set_value(self.profile.num_players)

        res_str = f"{self.profile.instance_width}x{self.profile.instance_height}"
        if res_str in self.resolutions:
            self.resolution_row.set_selected(self.resolutions.index(res_str))
        else:
            self.resolution_row.set_selected(0) # Custom

        self.instance_width_row.set_text(str(self.profile.instance_width or ""))
        self.instance_height_row.set_text(str(self.profile.instance_height or ""))

        is_custom = self.resolution_row.get_selected() == 0
        self.instance_width_row.set_visible(is_custom)
        self.instance_height_row.set_visible(is_custom)

        is_splitscreen = self.profile.mode == "splitscreen"
        self.screen_mode_row.set_selected(1 if is_splitscreen else 0)
        self.orientation_row.set_visible(is_splitscreen)

        # Load gamescope setting
        self.use_gamescope_row.set_active(self.profile.use_gamescope)

        if is_splitscreen and self.profile.splitscreen:
            orientation = self.profile.splitscreen.orientation.capitalize()
            self.orientation_row.set_selected(self.orientations.index(orientation))

        self.rebuild_player_rows()
        # Populate per-player device selections
        for i, row_dict in enumerate(self.player_rows):
            if i < len(self.profile.player_configs):
                config = self.profile.player_configs[i]
                row_dict["grab_input"].set_active(config.grab_input_devices)
                self._set_combo_row_selection(row_dict["joystick"], self.input_devices["joystick"], config.PHYSICAL_DEVICE_ID)
                # self._set_combo_row_selection(row_dict["mouse"], self.input_devices["mouse"], config.MOUSE_EVENT_PATH)
                # self._set_combo_row_selection(row_dict["keyboard"], self.input_devices["keyboard"], config.KEYBOARD_EVENT_PATH)
                self._set_combo_row_selection(row_dict["audio"], self.audio_devices, config.AUDIO_DEVICE_ID)
                # Ensure env UI exists for this player
                if not row_dict.get("env_initialized"):
                    env_title_row = Adw.ActionRow(title="Environment Variables")
                    add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
                    add_btn.get_style_context().add_class("add-button")
                    add_btn.set_valign(Gtk.Align.CENTER)
                    add_btn.connect("clicked", lambda b, i=i: self._add_player_env_row_by_index(i))
                    env_title_row.add_suffix(add_btn)
                    row_dict["expander"].add_row(env_title_row)
                    row_dict["env_initialized"] = True
                    row_dict["env_rows"] = []
                # Populate per-player ENV
                if getattr(config, "env", None):
                    for k, v in (config.env or {}).items():
                        self._add_player_env_row_by_index(i, k, v)
        # Populate global ENV
        if hasattr(self, "global_env_rows"):
            for env_row in self.global_env_rows:
                self.env_group.remove(env_row["row"])
        self.global_env_rows = []
        if getattr(self.profile, "env", None):
            for k, v in (self.profile.env or {}).items():
                self._add_global_env_row(k, v)

        # After loading, enforce exclusivity rules on the UI
        active_grab_index = -1
        for i, row_dict in enumerate(self.player_rows):
            if row_dict["grab_input"].get_active():
                active_grab_index = i
                break

        if active_grab_index != -1:
            for i, row_dict in enumerate(self.player_rows):
                if i != active_grab_index:
                    row_dict["grab_input"].set_sensitive(False)

        self._is_loading = False

    def _set_combo_row_selection(self, combo_row, device_list, device_id):
        if not device_id:
            combo_row.set_selected(0)
            return

        try:
            canonical_id = os.path.realpath(device_id)
            for i, device in enumerate(device_list):
                if os.path.realpath(device["id"]) == canonical_id:
                    combo_row.set_selected(i + 1)
                    return
        except Exception as e:
            self.logger.error(f"Error matching device {device_id}: {e}")

        combo_row.set_selected(0)

    def get_updated_data(self) -> Profile:
        self.profile.num_players = int(self.num_players_row.get_value())

        selected_res = self.resolution_row.get_selected_item().get_string()
        if selected_res == "Custom":
            self.profile.instance_width = int(self.instance_width_row.get_text() or 0)
            self.profile.instance_height = int(self.instance_height_row.get_text() or 0)
        else:
            width, height = map(int, selected_res.split("x"))
            self.profile.instance_width = width
            self.profile.instance_height = height

        self.profile.mode = self.screen_mode_row.get_selected_item().get_string().lower()
        if self.profile.mode == "splitscreen":
            orientation = self.orientation_row.get_selected_item().get_string().lower()
            self.profile.splitscreen = SplitscreenConfig(orientation=orientation)
        else:
            self.profile.splitscreen = None

        # Save gamescope setting
        self.profile.use_gamescope = self.use_gamescope_row.get_active()

        # Collect global environment variables
        self.profile.env = self._collect_env_from_rows(self.global_env_rows)

        new_configs = []
        for i in range(self.profile.num_players):
            if i < len(self.player_rows):
                row_dict = self.player_rows[i]
                new_config = PlayerInstanceConfig(
                    PHYSICAL_DEVICE_ID=self._get_combo_row_device_id(row_dict["joystick"], self.input_devices["joystick"]),
                    grab_input_devices=row_dict["grab_input"].get_active(),
                    # MOUSE_EVENT_PATH=self._get_combo_row_device_id(row_dict["mouse"], self.input_devices["mouse"]),
                    # KEYBOARD_EVENT_PATH=self._get_combo_row_device_id(row_dict["keyboard"], self.input_devices["keyboard"]),
                    AUDIO_DEVICE_ID=self._get_combo_row_device_id(row_dict["audio"], self.audio_devices),
                    env=self._collect_env_from_rows(row_dict.get("env_rows", [])),
                )
                new_configs.append(new_config)
            else:
                new_configs.append(PlayerInstanceConfig()) # Add empty config for new players
        self.profile.player_configs = new_configs

        self.profile.selected_players = self.get_selected_players()

        return self.profile

    def _on_setting_changed(self, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_num_players_changed(self, adjustment):
        if not self._is_loading:
            self.rebuild_player_rows()
            # Ensure env sections exist after rebuilding player rows
            for idx, row_dict in enumerate(self.player_rows):
                if "env_rows" not in row_dict:
                    row_dict["env_rows"] = []
                if not row_dict.get("env_initialized"):
                    env_title_row = Adw.ActionRow(title="Environment Variables")
                    add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
                    add_btn.get_style_context().add_class("add-button")
                    add_btn.set_valign(Gtk.Align.CENTER)
                    add_btn.connect("clicked", lambda b, i=idx: self._add_player_env_row_by_index(i))
                    env_title_row.add_suffix(add_btn)
                    row_dict["expander"].add_row(env_title_row)
                    row_dict["env_initialized"] = True
            self.emit("settings-changed")

    def _on_player_selected_changed(self, checkbox, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_resolution_changed(self, combo_row, *args):
        is_custom = combo_row.get_selected() == 0
        self.instance_width_row.set_visible(is_custom)
        self.instance_height_row.set_visible(is_custom)
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_screen_mode_changed(self, combo_row, *args):
        is_splitscreen = combo_row.get_selected_item().get_string().lower() == "splitscreen"
        self.orientation_row.set_visible(is_splitscreen)
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_grab_input_toggled(self, switch, gparam, index):
        if self._is_loading:
            return

        is_active = switch.get_active()

        for i, row_dict in enumerate(self.player_rows):
            grab_switch = row_dict["grab_input"]
            if i == index:
                continue

            if is_active:
                grab_switch.set_active(False)
                grab_switch.set_sensitive(False)
            else:
                grab_switch.set_sensitive(True)

        self._on_setting_changed()

    def _create_env_kv_row(self, container):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("env-var-box")

        key_entry = Gtk.Entry(placeholder_text="KEY")
        key_entry.get_style_context().add_class("env-key-entry")
        value_entry = Gtk.Entry(placeholder_text="VALUE")
        value_entry.get_style_context().add_class("env-value-entry")
        remove_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove_btn.get_style_context().add_class("remove-button")
        remove_btn.set_valign(Gtk.Align.CENTER)

        key_entry.connect("changed", self._on_setting_changed)
        value_entry.connect("changed", self._on_setting_changed)

        box.append(key_entry)
        box.append(Gtk.Label(label="="))
        box.append(value_entry)
        box.append(remove_btn)

        row = Adw.ActionRow()
        row.set_child(box)
        row.get_style_context().add_class("env-var-row")

        # Add row to correct container type
        if isinstance(container, Adw.PreferencesGroup):
            container.add(row)
        elif isinstance(container, Adw.ExpanderRow):
            container.add_row(row)
        else:
            try:
                container.add(row)
            except Exception:
                container.add_row(row)

        return {"row": row, "key": key_entry, "value": value_entry, "remove": remove_btn}

    def _on_add_global_env_clicked(self, button):
        self._add_global_env_row()

    def _add_global_env_row(self, key: str = "", value: str = ""):
        env_row = self._create_env_kv_row(self.env_group)
        env_row["key"].set_text(str(key) if key is not None else "")
        env_row["value"].set_text(str(value) if value is not None else "")
        def on_remove(btn, row=env_row):
            try:
                self.env_group.remove(row["row"])
            except Exception:
                pass
            if row in self.global_env_rows:
                self.global_env_rows.remove(row)
            self._on_setting_changed()
        env_row["remove"].connect("clicked", on_remove)
        self.global_env_rows.append(env_row)

    def _add_player_env_row_by_index(self, idx: int, key: str = "", value: str = ""):
        if idx < 0 or idx >= len(self.player_rows):
            return
        rd = self.player_rows[idx]
        env_row = self._create_env_kv_row(rd["expander"])
        env_row["key"].set_text(str(key) if key is not None else "")
        env_row["value"].set_text(str(value) if value is not None else "")
        def on_remove(btn, row=env_row, rd=rd):
            try:
                rd["expander"].remove(row["row"])
            except Exception:
                pass
            if "env_rows" in rd and row in rd["env_rows"]:
                rd["env_rows"].remove(row)
            self._on_setting_changed()
        env_row["remove"].connect("clicked", on_remove)
        rd.setdefault("env_rows", [])
        rd["env_rows"].append(env_row)

    def _collect_env_from_rows(self, rows) -> dict:
        env = {}
        for r in rows or []:
            key = (r["key"].get_text() or "").strip()
            val = r["value"].get_text() if r["value"] else ""
            if key:
                env[key] = str(val)
        return env

    def rebuild_player_rows(self):
        for row_dict in self.player_rows:
            self.players_group.remove(row_dict["expander"])
        self.player_rows = []

        num_players = int(self.num_players_row.get_value())
        # Ensure player_configs list is long enough
        while len(self.profile.player_configs) < num_players:
            self.profile.player_configs.append(PlayerInstanceConfig())

        for i in range(num_players):
            expander = Adw.ExpanderRow(title=f"Instance {i + 1}")
            expander.get_style_context().add_class("player-expander")
            self.players_group.add(expander)

            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)
            checkbox.get_style_context().add_class("player-checkbox")
            checkbox.connect("toggled", self._on_player_selected_changed)
            expander.add_prefix(checkbox)

            def create_device_row(title, device_type):
                devices = self.input_devices.get(device_type, [])
                model = Gtk.StringList.new(["None"] + [d["name"] for d in devices])
                row = Adw.ComboRow(title=title, model=model)
                row.get_style_context().add_class(f"{device_type}-row")
                row.connect("notify::selected-item", self._on_setting_changed)
                expander.add_row(row)
                return row

            joystick_row = create_device_row("Gamepad", "joystick")
            # mouse_row = create_device_row("Mouse", "mouse")
            # keyboard_row = create_device_row("Keyboard", "keyboard")

            grab_input_switch = Adw.SwitchRow(title="Capturar Mouse e Teclado")
            grab_input_switch.connect("notify::active", self._on_grab_input_toggled, i)
            expander.add_row(grab_input_switch)


            audio_model = Gtk.StringList.new(["None"] + [d["name"] for d in self.audio_devices])
            audio_row = Adw.ComboRow(title="Audio Device", model=audio_model)
            audio_row.get_style_context().add_class("audio-row")
            audio_row.connect("notify::selected-item", self._on_setting_changed)
            expander.add_row(audio_row)

            launch_button = Gtk.Button(label="Start")
            launch_button.get_style_context().add_class("configure-button")
            launch_button.set_valign(Gtk.Align.CENTER)
            launch_button.connect(
                "clicked", self._on_instance_launch_clicked, i
            )
            expander.add_suffix(launch_button)

            self.player_rows.append({
                "checkbox": checkbox,
                "expander": expander,
                "joystick": joystick_row,
                "grab_input": grab_input_switch,
                "audio": audio_row,
                "status_icon": None,
                "launch_button": launch_button,
                "is_running": False,
            })

    def _run_verification(self):
        for i, row_dict in enumerate(self.player_rows):
            instance_num = i + 1
            status = self.verification_service.verify_instance(instance_num)

            # Remove existing icon first
            if row_dict["status_icon"]:
                row_dict["expander"].remove(row_dict["status_icon"])
                row_dict["status_icon"] = None

            if status == "Passed":
                icon = Gtk.Image.new_from_icon_name("check-outlined-symbolic")
                icon.get_style_context().add_class("verification-passed-icon")
                row_dict["expander"].add_suffix(icon)
                row_dict["status_icon"] = icon

    def get_selected_players(self) -> list[int]:
        return [i + 1 for i, r in enumerate(self.player_rows) if r["checkbox"].get_active()]

    def _get_combo_row_device_id(self, combo_row, device_list):
        selected_idx = combo_row.get_selected()
        if selected_idx > 0 and (selected_idx - 1) < len(device_list):
            return device_list[selected_idx - 1]["id"]
        return None

    def _on_instance_launch_clicked(self, button, instance_idx):
        row_data = self.player_rows[instance_idx]
        instance_num = instance_idx + 1

        if row_data["is_running"]:
            self.instance_service.terminate_instance(instance_num)
            button.set_label("Start")
            button.get_style_context().remove_class("destructive-action")
            row_data["is_running"] = False
        else:
            self.instance_service.launch_instance(
                self.profile, instance_num, use_gamescope_override=False
            )
            button.set_label("Stop")
            button.get_style_context().add_class("destructive-action")
            row_data["is_running"] = True

        self._run_verification()
        self.emit("instance-state-changed")

    def is_any_instance_running(self):
        return any(r["is_running"] for r in self.player_rows)

    def set_running_state(self, is_running):
        for row_data in self.player_rows:
            row_data["is_running"] = is_running
            button = row_data["launch_button"]
            if is_running:
                button.set_label("Stop")
                button.get_style_context().add_class("destructive-action")
            else:
                button.set_label("Start")
                button.get_style_context().remove_class("destructive-action")
