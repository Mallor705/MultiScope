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


class GameEditor(Adw.PreferencesPage):
    __gsignals__ = {
        "settings-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, game, logger, **kwargs):
        super().__init__(**kwargs)
        self._is_loading = False
        self.game = game
        self.profile = None
        self.player_rows = []
        self._selected_path = game.game_root_path
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

        # Caminho da Raiz do Jogo
        self.game_root_path_row = Adw.ActionRow(title="Game Root Path")
        self.path_label = Gtk.Label(
            label=f"<small><i>{self._selected_path}</i></small>",
            use_markup=True,
            halign=Gtk.Align.START,
        )
        self.path_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.path_label.set_hexpand(True)

        button = Gtk.Button(label="Browse...")
        button.connect("clicked", self._on_open_folder_dialog)

        self.game_root_path_row.add_suffix(self.path_label)
        self.game_root_path_row.add_suffix(button)
        game_group.add(self.game_root_path_row)

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

    def update_for_game(self, game):
        self._is_loading = True
        try:
            self.game = game
            self._selected_path = game.game_root_path
            self.path_label.set_markup(f"<small><i>{self._selected_path}</i></small>")

            self.load_game_data()
            self.load_profile_data()
        finally:
            self._is_loading = False

    def _on_setting_changed(self, *args):
        if not self._is_loading:
            self.emit("settings-changed")

    def _on_open_folder_dialog(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Game Root Folder",
            transient_for=self.get_root(),
            modal=True,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL, "_Select", Gtk.ResponseType.OK
        )
        dialog.connect("response", self._on_folder_selected)
        dialog.present()

    def _on_folder_selected(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            folder = dialog.get_file()
            if folder:
                self._selected_path = Path(folder.get_path())
                self.path_label.set_markup(
                    f"<small><i>{self._selected_path}</i></small>"
                )
        dialog.destroy()

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
        pass

    def get_updated_data(self):
        # Atualizar dados do Jogo
        self.game.game_name = self.game_name_row.get_text()
        if self._selected_path:
            self.game.game_root_path = self._selected_path
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

        return self.game, self.profile


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
