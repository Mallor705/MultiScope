import os
from pathlib import Path

import gi

from ..core.config import Config
from ..core.logger import Logger
from ..models.profile import PlayerInstanceConfig, Profile
from ..services.device_manager import DeviceManager
from ..services.game_manager import GameManager
from ..services.proton import ProtonService
from .dialogs import TextInputDialog

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GObject, Gtk, Pango

from .dialogs import ConfirmationDialog


class ProfileRow(GObject.Object):
    name = GObject.Property(type=str)

    def __init__(self, name):
        super().__init__()
        self.name = name


class GameEditor(Adw.PreferencesPage):
    __gsignals__ = {
        "profile-selected": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "settings-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, game, logger, **kwargs):
        super().__init__(**kwargs)
        self._is_loading = False
        self.game = game
        self.profile = None
        self.player_rows = []
        self._selected_path = game.exe_path
        self.logger = logger

        # Inicializar serviços
        self.proton_service = ProtonService(self.logger)
        self.device_manager = DeviceManager()
        self.game_manager = GameManager(self.logger)

        # Obter listas de dispositivos
        self.input_devices = self.device_manager.get_input_devices()
        self.audio_devices = self.device_manager.get_audio_devices()
        self.display_outputs = self.device_manager.get_display_outputs()

        self._build_ui()
        self.update_for_game(game)

    def _build_ui(self):
        self.set_title("Game Settings")

        # Grupo de Configurações do Jogo
        game_group = Adw.PreferencesGroup(title="Game Configuration")
        self.add(game_group)

        # Nome do Jogo
        self.game_name_row = Adw.EntryRow(title="Game Name")
        self.game_name_row.connect("changed", self._on_setting_changed)
        game_group.add(self.game_name_row)

        # Caminho do Executável
        self.exe_path_row = Adw.ActionRow(title="Executable Path")
        self.path_label = Gtk.Label(
            label=f"<small><i>{self._selected_path}</i></small>",
            use_markup=True,
            halign=Gtk.Align.START,
        )
        self.path_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.path_label.set_hexpand(True)

        button = Gtk.Button(label="Browse...")
        button.connect("clicked", self._on_open_file_dialog)

        self.exe_path_row.add_suffix(self.path_label)
        self.exe_path_row.add_suffix(button)
        game_group.add(self.exe_path_row)

        # App ID
        self.app_id_row = Adw.EntryRow(title="Steam App ID")
        self.app_id_row.connect("changed", self._on_setting_changed)
        game_group.add(self.app_id_row)

        # Argumentos do Jogo
        self.game_args_row = Adw.EntryRow(title="Game Arguments")
        self.game_args_row.connect("changed", self._on_setting_changed)
        game_group.add(self.game_args_row)

        # Seletor de Versão do Proton
        proton_versions = self.proton_service.list_installed_proton_versions()
        self.proton_version_row = Adw.ComboRow(
            title="Proton Version", model=Gtk.StringList.new(proton_versions)
        )
        self.proton_version_row.connect(
            "notify::selected-item", self._on_setting_changed
        )
        game_group.add(self.proton_version_row)

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

        # Grupo de Configurações de Layout
        layout_group = Adw.PreferencesGroup(title="Layout Settings")
        self.add(layout_group)

        self.num_players_row = Adw.SpinRow(
            title="Number of Players",
            subtitle="Changing this will reset player configs",
        )
        adjustment = Gtk.Adjustment(value=2, lower=1, upper=8, step_increment=1)
        self.num_players_row.set_adjustment(adjustment)
        self.num_players_handler_id = adjustment.connect(
            "value-changed", self._on_num_players_adjustment_changed
        )
        adjustment.connect("value-changed", self._on_setting_changed)
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
        self.instance_width_row.set_visible(False)  # Oculto por padrão
        self.instance_width_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_width_row)

        self.instance_height_row = Adw.EntryRow(title="Custom Instance Height")
        self.instance_height_row.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.instance_height_row.set_visible(False)  # Oculto por padrão
        self.instance_height_row.connect("changed", self._on_setting_changed)
        layout_group.add(self.instance_height_row)

        # Grupo de Configurações dos Jogadores
        self.players_group = Adw.PreferencesGroup(title="Player Configurations")
        self.add(self.players_group)

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
        # A Gtk.ListItem não é um widget, então não podemos conectar "destroy" a ela.
        # Conectamos ao seu filho widget, que é a Gtk.Box.
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

        # Configurar o menu de contexto
        popover = list_item.popover
        popover.set_parent(list_item.get_child())
        delete_button = popover.get_child().get_first_child()

        # Desconectar manipuladores antigos para evitar múltiplos sinais
        if hasattr(delete_button, "handler_id"):
            delete_button.disconnect(delete_button.handler_id)

        # Não permitir a exclusão do perfil 'Default'
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

            # Se o perfil excluído era o ativo, volte para 'Default'
            if current_profile_name == profile.profile_name:
                self.update_for_game(self.game)
                self.profile_selector_row.set_selected(0)  # Seleciona 'Default'
            else:
                # Apenas recarregue a lista de perfis mantendo a seleção atual
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

    def update_for_game(self, game):
        self._is_loading = True
        try:
            self.game = game
            self._selected_path = game.exe_path
            self.path_label.set_markup(f"<small><i>{self._selected_path}</i></small>")

            selected_idx = self.update_profile_list()

            # Tenta carregar o 'Default' ou o primeiro perfil
            default_profile = self.game_manager.get_profile(self.game, "Default")
            if default_profile:
                self.profile = default_profile
                self.profile_selector_row.set_selected(selected_idx)
            else:  # Se o Default não existir (caso de erro), cria um
                self.profile = Profile(profile_name="Default")
                self.game_manager.add_profile(self.game, self.profile)
                self.update_profile_list()

            self.load_game_data()
            self.load_profile_data()
        finally:
            self._is_loading = False

    def _on_profile_selected(self, combo_row, selected_item_prop):
        # Adicionar uma proteção para evitar a execução durante a configuração inicial
        if self.profile is None or self._is_loading:
            return

        selected_item = combo_row.get_selected_item()
        if not selected_item:
            return

        profile_name = selected_item.name
        if profile_name == self.profile.profile_name:
            return  # Evitar recarregamento desnecessário

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
                # Obter os dados atuais da UI, mas atribuir um novo nome
                _, new_profile = self.get_updated_data()
                new_profile.profile_name = profile_name

                try:
                    self.game_manager.add_profile(self.game, new_profile)
                    selected_idx = self.update_profile_list(profile_name)
                    self.profile_selector_row.set_selected(selected_idx)

                except FileExistsError:
                    self.logger.error(
                        f"Profile '{profile_name}' already exists."
                    )  # Substituir por dialog de erro
        dialog.destroy()

    def _on_setting_changed(self, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_resolution_changed(self, combo_row, selected_item_prop):
        selected_item = combo_row.get_selected_item()
        if not selected_item:
            return

        is_custom = selected_item.get_string() == "Custom"
        self.instance_width_row.set_visible(is_custom)
        self.instance_height_row.set_visible(is_custom)

    def _on_open_file_dialog(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Game Executable",
            transient_for=self.get_root(),
            modal=True,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK
        )
        dialog.connect("response", self._on_file_selected)
        dialog.present()

    def _on_file_selected(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                self._selected_path = Path(file.get_path())
                self.path_label.set_markup(
                    f"<small><i>{self._selected_path}</i></small>"
                )
        dialog.destroy()

    def _rebuild_player_rows(self):
        # Limpar linhas antigas
        for row_dict in self.player_rows:
            self.players_group.remove(row_dict["expander"])
        self.player_rows = []

        num_players = int(self.num_players_row.get_value())

        for i in range(num_players):
            player_expander = Adw.ExpanderRow(title=f"Player {i + 1}")
            self.players_group.add(player_expander)

            # Checkbox for instance selection
            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)  # Default to selected
            player_expander.add_prefix(checkbox)

            # ACCOUNT_NAME
            account_name_row = Adw.EntryRow(title="Account Name")
            account_name_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(account_name_row)

            # LANGUAGE
            language_row = Adw.EntryRow(title="Language")
            language_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(language_row)

            # Listen Port
            listen_port_row = Adw.EntryRow(title="Listen Port")
            listen_port_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(listen_port_row)

            # User Steam ID
            user_steam_id_row = Adw.EntryRow(title="User Steam ID")
            user_steam_id_row.connect("changed", self._on_setting_changed)
            player_expander.add_row(user_steam_id_row)

            # Seletores de Dispositivos
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

    def _on_num_players_adjustment_changed(self, adjustment):
        self._rebuild_player_rows()

    def load_game_data(self):
        self._is_loading = True
        try:
            self.game_name_row.set_text(self.game.game_name)
            self.app_id_row.set_text(self.game.app_id or "")
            self.game_args_row.set_text(self.game.game_args or "")

            if self.game.proton_version:
                versions = self.proton_version_row.get_model()
                for i in range(versions.get_n_items()):
                    version = versions.get_string(i)
                    if version == self.game.proton_version:
                        self.proton_version_row.set_selected(i)
                        break
            else:
                self.proton_version_row.set_selected(0)
        finally:
            self._is_loading = False

    def load_profile_data(self):
        self._is_loading = True
        try:
            # Bloquear o sinal para evitar loop recursivo
            adjustment = self.num_players_row.get_adjustment()
            adjustment.handler_block(self.num_players_handler_id)
            adjustment.set_value(self.profile.num_players)
            self._rebuild_player_rows()  # Reconstruir as linhas com base no novo número
            adjustment.handler_unblock(self.num_players_handler_id)

            # Carregar resolução
            width = self.profile.instance_width
            height = self.profile.instance_height
            resolution_str = f"{width}x{height}"

            if width and height and resolution_str in self.resolutions:
                # Encontrar o índice da resolução e definir no ComboRow
                for i, res in enumerate(self.resolutions):
                    if res == resolution_str:
                        self.resolution_row.set_selected(i)
                        break
                self.instance_width_row.set_visible(False)
                self.instance_height_row.set_visible(False)
            else:
                # Definir como 'Custom' e preencher os valores
                self.resolution_row.set_selected(0)  # "Custom"
                self.instance_width_row.set_text(
                    str(width) if width is not None else ""
                )
                self.instance_height_row.set_text(
                    str(height) if height is not None else ""
                )
                self.instance_width_row.set_visible(True)
                self.instance_width_row.set_visible(True)
                self.instance_height_row.set_visible(True)

            # Load player data
            for i, row_dict in enumerate(self.player_rows):
                if self.profile.player_configs and i < len(self.profile.player_configs):
                    config = self.profile.player_configs[i]
                    row_dict["account_name"].set_text(config.ACCOUNT_NAME or "")
                    row_dict["language"].set_text(config.LANGUAGE or "")
                    row_dict["listen_port"].set_text(config.LISTEN_PORT or "")
                    row_dict["user_steam_id"].set_text(config.USER_STEAM_ID or "")
                    self._set_combo_row_selection(
                        row_dict["joystick"],
                        self.input_devices["joystick"],
                        config.PHYSICAL_DEVICE_ID,
                    )
                    self._set_combo_row_selection(
                        row_dict["mouse"],
                        self.input_devices["mouse"],
                        config.MOUSE_EVENT_PATH,
                    )
                    self._set_combo_row_selection(
                        row_dict["keyboard"],
                        self.input_devices["keyboard"],
                        config.KEYBOARD_EVENT_PATH,
                    )
                    self._set_combo_row_selection(
                        row_dict["audio"], self.audio_devices, config.AUDIO_DEVICE_ID
                    )
                    self._set_combo_row_selection(
                        row_dict["monitor"], self.display_outputs, config.monitor_id
                    )
        finally:
            self._is_loading = False

    def _set_combo_row_selection(self, combo_row, device_list, device_id):
        if not device_id:
            combo_row.set_selected(0)  # "None"
            return

        # Apenas tenta resolver o caminho se for um caminho de dispositivo de entrada
        id_to_match = device_id
        if device_id.startswith("/dev/input"):
            try:
                id_to_match = os.path.realpath(device_id)
            except Exception:
                # Se realpath falhar, ainda tentaremos a correspondência com o ID original
                pass

        for i, device in enumerate(device_list):
            current_device_id = device["id"]
            if current_device_id.startswith("/dev/input"):
                try:
                    current_device_id = os.path.realpath(current_device_id)
                except Exception:
                    pass

            if current_device_id == id_to_match:
                combo_row.set_selected(i + 1)  # Deslocamento para "None"
                return

        # Se nenhuma correspondência for encontrada, defina como "None"
        combo_row.set_selected(0)

    def get_updated_data(self):
        # Atualizar dados do Jogo
        self.game.game_name = self.game_name_row.get_text()
        if self._selected_path:
            self.game.exe_path = self._selected_path
        self.game.app_id = self.app_id_row.get_text() or None
        self.game.game_args = self.game_args_row.get_text() or None
        self.game.is_native = False
        selected_item = self.proton_version_row.get_selected_item()
        if selected_item:
            selected_string = selected_item.get_string()
            self.game.proton_version = (
                None if selected_string == "None" else selected_string
            )
        else:
            self.game.proton_version = None

        # Atualizar dados do Perfil
        self.profile.num_players = int(self.num_players_row.get_value())

        selected_res = self.resolution_row.get_selected_item().get_string()
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

        return self.game, self.profile

    def _get_combo_row_device_id(self, combo_row, device_list):
        selected_index = combo_row.get_selected()
        if selected_index <= 0:  # 0 is "None", -1 is no selection
            return None
        # Adjust index to account for "None" at the start
        device_index = selected_index - 1
        if device_index < len(device_list):
            return device_list[device_index]["id"]
        return None

    def get_selected_players(self) -> list[int]:
        """Returns a list of the instance numbers for the selected players."""
        selected = []
        for i, row_data in enumerate(self.player_rows):
            if row_data["checkbox"].get_active():
                selected.append(i + 1)  # Instance numbers are 1-based
        return selected


class AdvancedSettingsPage(Adw.PreferencesPage):
    __gsignals__ = {"settings-changed": (GObject.SIGNAL_RUN_FIRST, None, ())}

    def __init__(self, game, logger, **kwargs):
        super().__init__(**kwargs)
        self._is_loading = False
        self.game = game
        self.logger = logger
        self.env_var_rows = []
        self._build_ui()
        self.update_for_game(game)

    def _build_ui(self):
        self.set_title("Advanced Settings")

        # Grupo de Configurações da Instância
        instance_group = Adw.PreferencesGroup(title="Instance Settings")
        self.add(instance_group)

        # Usar MangoHud
        self.use_mangohud_row = Adw.SwitchRow(title="Use MangoHud")
        self.use_mangohud_row.connect("notify::active", self._on_setting_changed)
        instance_group.add(self.use_mangohud_row)

        # Variáveis de Ambiente
        env_vars_expander = Adw.ExpanderRow(title="Environment Variables")
        instance_group.add(env_vars_expander)

        self.env_vars_list_box = Gtk.ListBox()
        self.env_vars_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        env_vars_expander.add_row(self.env_vars_list_box)

        add_env_var_button = Gtk.Button.new_with_label("Add Variable")
        add_env_var_button.connect("clicked", self._on_add_env_var_clicked)

        button_row = Adw.ActionRow()
        button_row.add_suffix(add_env_var_button)
        env_vars_expander.add_row(button_row)

        # Grupo de Configurações do Wine
        wine_group = Adw.PreferencesGroup(title="Wine Settings")
        self.add(wine_group)

        # Usar VKD3D
        self.use_vkd3d_row = Adw.SwitchRow(title="Apply DXVK/VKD3D")
        self.use_vkd3d_row.connect("notify::active", self._on_setting_changed)
        wine_group.add(self.use_vkd3d_row)

        # Verbos do Winetricks
        self.winetricks_verbs_row = Adw.EntryRow(title="Winetricks Verbs")
        self.winetricks_verbs_row.connect("changed", self._on_setting_changed)
        wine_group.add(self.winetricks_verbs_row)

    def update_for_game(self, game):
        self._is_loading = True
        try:
            self.game = game
            self.load_game_data()
        finally:
            self._is_loading = False

    def _on_setting_changed(self, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_add_env_var_clicked(self, button):
        self._add_env_var_row()
        self.emit("settings-changed")

    def _add_env_var_row(self, key="", value=""):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        key_entry = Gtk.Entry(text=key, placeholder_text="KEY")
        key_entry.connect("changed", self._on_setting_changed)
        value_entry = Gtk.Entry(text=value, placeholder_text="VALUE", hexpand=True)
        value_entry.connect("changed", self._on_setting_changed)

        remove_button = Gtk.Button.new_from_icon_name("edit-delete-symbolic")

        row.append(key_entry)
        row.append(value_entry)
        row.append(remove_button)

        self.env_vars_list_box.append(row)

        row_data = {"row": row, "key": key_entry, "value": value_entry}
        self.env_var_rows.append(row_data)

        remove_button.connect("clicked", self._on_remove_env_var_clicked, row)

    def _on_remove_env_var_clicked(self, button, row):
        row_data_to_remove = None
        for data in self.env_var_rows:
            if data["row"] == row:
                row_data_to_remove = data
                break

        if row_data_to_remove:
            list_box_row = row.get_parent()
            self.env_vars_list_box.remove(list_box_row)
            self.env_var_rows.remove(row_data_to_remove)
            self.emit("settings-changed")

    def load_game_data(self):
        self._is_loading = True
        try:
            self.winetricks_verbs_row.set_text(
                " ".join(self.game.winetricks_verbs)
                if self.game.winetricks_verbs
                else ""
            )
            self.use_vkd3d_row.set_active(self.game.apply_dxvk_vkd3d)
            self.use_mangohud_row.set_active(self.game.use_mangohud)

            while child := self.env_vars_list_box.get_first_child():
                self.env_vars_list_box.remove(child)
            self.env_var_rows = []
            if self.game.env_vars:
                for key, value in self.game.env_vars.items():
                    self._add_env_var_row(key, value)
        finally:
            self._is_loading = False

    def get_updated_data(self):
        winetricks_text = self.winetricks_verbs_row.get_text()
        self.game.winetricks_verbs = (
            winetricks_text.split() if winetricks_text else None
        )
        self.game.apply_dxvk_vkd3d = self.use_vkd3d_row.get_active()
        self.game.use_mangohud = self.use_mangohud_row.get_active()
        env_vars = {}
        for row_data in self.env_var_rows:
            key = row_data["key"].get_text()
            value = row_data["value"].get_text()
            if key:
                env_vars[key] = value
        self.game.env_vars = env_vars if env_vars else None
        return self.game
