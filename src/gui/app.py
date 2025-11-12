import sys
from pathlib import Path

import gi
from pydantic import ValidationError

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk

from ..core.config import Config
from ..core.logger import Logger
from ..models.game import Game
from ..models.profile import GameProfile, Profile
from ..services.game_manager import GameManager
from ..services.instance import InstanceService
from .dialogs import AddGameDialog, ConfirmationDialog, TextInputDialog
from .game_editor import AdvancedSettingsPage, GameEditor


class ProtonCoopWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O título da janela do SO é definido aqui
        self.set_title("Proton Coop")
        self.set_default_size(1024, 768)

        self.logger = Logger("ProtonCoop-GUI", Config.LOG_DIR, reset=True)
        self.game_manager = GameManager(logger=self.logger)
        self.instance_service = InstanceService(logger=self.logger)

        self.selected_game = None
        self.selected_profile = None
        self.game_editor = None
        self.advanced_settings_page = None
        self.games_group = None

        self._build_ui()
        self.load_games_into_sidebar()

        # Drag and Drop
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        self.add_controller(drop_target)

    def _show_error_dialog(self, message):
        dialog = Adw.MessageDialog(
            transient_for=self, modal=True, title="Error", body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _build_ui(self):
        # Toolbar View
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        # Header Bar
        header_bar = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header_bar)

        add_game_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_game_button.set_tooltip_text("Add a new game")
        add_game_button.connect("clicked", self.on_add_game_clicked)
        header_bar.pack_start(add_game_button)

        # View Switcher
        self.view_switcher = Adw.ViewSwitcher()
        header_bar.set_title_widget(self.view_switcher)

        # Split View
        self.split_view = Adw.NavigationSplitView()
        self.toolbar_view.set_content(self.split_view)
        self.split_view.set_collapsed(False)

        # Barra lateral
        self.sidebar_page = Adw.PreferencesPage()
        sidebar_navigation_page = Adw.NavigationPage.new(self.sidebar_page, "Games")
        self.split_view.set_sidebar(sidebar_navigation_page)

        # Content View Stack
        self.view_stack = Adw.ViewStack()
        content_navigation_page = Adw.NavigationPage.new(self.view_stack, "Content")
        self.split_view.set_content(content_navigation_page)
        self.view_switcher.set_stack(self.view_stack)

        # Página de Boas-Vindas
        self.welcome_page = Adw.StatusPage(
            title="Welcome to Proton Coop!",
            icon_name="co.uk.somnilok.Linux-Coop-symbolically",
        )
        self.view_stack.add_titled(self.welcome_page, "welcome", "Welcome")

        # Barra de rodapé
        self.footer_bar = Adw.HeaderBar()
        self.footer_bar.set_show_end_title_buttons(False)
        self.footer_bar.set_visible(False)
        self.toolbar_view.add_bottom_bar(self.footer_bar)

        self.launch_button = Gtk.Button.new_with_mnemonic("_Launch")
        self.launch_button.get_style_context().add_class("suggested-action")
        self.launch_button.add_css_class("uniform-button")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        self.footer_bar.pack_end(self.launch_button)

        self.stop_button = Gtk.Button.new_with_mnemonic("_Stop")
        self.stop_button.get_style_context().add_class("destructive-action")
        self.stop_button.add_css_class("uniform-button")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_visible(False)
        self.footer_bar.pack_end(self.stop_button)

    def load_games_into_sidebar(self):
        # Substituir o grupo antigo para evitar erros críticos
        if self.games_group:
            self.sidebar_page.remove(self.games_group)

        self.games_group = Adw.PreferencesGroup()
        self.games_group.set_margin_top(10)
        self.games_group.set_margin_bottom(10)
        self.games_group.set_margin_start(10)
        self.games_group.set_margin_end(10)
        self.sidebar_page.add(self.games_group)

        games = self.game_manager.get_games()
        for game in games:
            game_row = Adw.ActionRow(title=game.game_name)
            game_row.add_css_class("game-row")
            game_row.set_activatable(True)
            game_row.connect("activated", self.on_game_selected, game)
            self._setup_context_menu(game_row, game)
            self.games_group.add(game_row)

    def _setup_context_menu(self, widget, game):
        popover = Gtk.Popover.new()
        popover.set_parent(widget)
        widget.connect("destroy", lambda w: popover.unparent())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        popover.set_child(box)

        delete_button = Gtk.Button(label="Delete")
        delete_button.get_style_context().add_class("flat")
        delete_button.connect("clicked", self.on_delete_game, game, popover)
        box.append(delete_button)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", lambda g, n, x, y: popover.popup())
        widget.add_controller(gesture)

    def on_delete_game(self, button, game, popover):
        popover.popdown()
        dialog = ConfirmationDialog(
            self, "Delete Game?", f"Are you sure you want to delete {game.game_name}?"
        )
        dialog.connect(
            "response", lambda d, r: self._on_delete_game_confirmed(d, r, game)
        )
        dialog.present()

    def _on_delete_game_confirmed(self, dialog, response_id, game):
        if response_id == "ok":
            self.game_manager.delete_game(game)
            self.load_games_into_sidebar()
            self._show_welcome_screen()
        dialog.destroy()

    def _show_welcome_screen(self):
        welcome_stack_page = self.view_stack.get_page(self.welcome_page)
        welcome_stack_page.set_visible(True)
        self.view_stack.set_visible_child(self.welcome_page)
        self.footer_bar.set_visible(False)
        self.selected_game = None
        self.selected_profile = None

    def on_game_selected(self, widget, game):
        self.selected_game = game
        self.selected_profile = self.game_manager.get_profile(game, "Default")

        if self.game_editor is None:
            self.game_editor = GameEditor(game, self.logger)
            self.game_editor.connect("profile-selected", self._on_profile_switched)
            self.game_editor.connect("settings-changed", self._trigger_auto_save)
            self.view_stack.add_titled_with_icon(
                self.game_editor, "game_settings", "Game Settings", "settings-symbolic"
            )

            self.advanced_settings_page = AdvancedSettingsPage(game, self.logger)
            self.advanced_settings_page.connect(
                "settings-changed", self._trigger_auto_save
            )
            self.view_stack.add_titled_with_icon(
                self.advanced_settings_page,
                "advanced_settings",
                "Advanced",
                "preferences-system-symbolic",
            )

        self.game_editor.update_for_game(game)
        self.advanced_settings_page.update_for_game(game)

        welcome_stack_page = self.view_stack.get_page(self.welcome_page)
        welcome_stack_page.set_visible(False)
        self.view_stack.set_visible_child(self.game_editor)
        self.footer_bar.set_visible(True)
        self.launch_button.set_sensitive(True)

    def _on_profile_switched(self, editor, profile):
        self.selected_profile = profile
        self.logger.info(f"Switched to profile: {profile.profile_name}")

    def on_add_game_clicked(self, button):
        dialog = AddGameDialog(self)
        dialog.connect("response", self._on_add_game_dialog_response)
        dialog.present()

    def _on_add_game_dialog_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                self._add_game_from_archive(Path(file.get_path()))
        dialog.destroy()

    def _add_game_from_archive(self, archive_path: Path):
        try:
            handler_data, _ = self.game_manager._extract_and_parse_handler(archive_path)
            exe_name = handler_data.get("ExecutableName")
        except (FileNotFoundError, ValueError) as e:
            self._show_error_dialog(str(e))
            return

        folder_dialog = Gtk.FileChooserDialog(
            title="Select the game's root folder",
            transient_for=self,
            modal=True,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        folder_dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL, "_Select", Gtk.ResponseType.OK
        )
        folder_dialog.connect("response", self._on_game_root_selected, archive_path, exe_name)
        folder_dialog.present()

    def _on_game_root_selected(self, dialog, response_id, archive_path, exe_name):
        if response_id == Gtk.ResponseType.OK:
            folder = dialog.get_file()
            if folder:
                game_root_path = Path(folder.get_path())

                exe_dialog = Gtk.FileChooserDialog(
                    title=f"Select the executable '{exe_name}'",
                    transient_for=self,
                    modal=True,
                    action=Gtk.FileChooserAction.OPEN,
                )
                exe_dialog.add_buttons(
                    "_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK
                )

                # Start browsing from the selected game root path
                folder_gfile = Gio.File.new_for_path(str(game_root_path))
                exe_dialog.set_current_folder(folder_gfile)

                exe_dialog.connect("response", self._on_exe_selected, archive_path, game_root_path, exe_name)
                exe_dialog.present()
        dialog.destroy()

    def _on_exe_selected(self, dialog, response_id, archive_path, game_root_path, exe_name):
        if response_id == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                exe_path = Path(file.get_path())

                if exe_path.name != exe_name:
                    self._show_error_dialog(
                        f"Invalid executable selected. Please select '{exe_name}'."
                    )
                    # Re-open the dialog in the same folder
                    dialog.present()
                    return

                try:
                    self.game_manager.add_game_from_archive(archive_path, exe_path, game_root_path)
                    self.load_games_into_sidebar()
                except (ValidationError, FileExistsError) as e:
                    self._show_error_dialog(str(e))
                except Exception as e:
                    self.logger.error(f"Failed to add new game: {e}")
                    self._show_error_dialog(
                        "An unexpected error occurred. See logs for details."
                    )
        dialog.destroy()

    def _on_drop(self, drop_target, value, x, y):
        file_list = value.get_files()
        for file in file_list:
            path = file.get_path()
            if path.endswith(".nc") or path.endswith(".zip"):
                self._add_game_from_archive(Path(path))
            else:
                self.logger.warning(f"Ignoring unsupported file type: {path}")
        return True

    def _trigger_auto_save(self, *args):
        if self.game_editor and self.advanced_settings_page:
            updated_game, updated_profile = self.game_editor.get_updated_data()
            self.advanced_settings_page.get_updated_data()

            # Sync the profile state in the main window
            self.selected_profile = updated_profile

            self.game_manager.save_game(updated_game)
            self.game_manager.save_profile(updated_game, updated_profile)

            self.logger.info("Game and profile auto-saved.")

    def on_launch_clicked(self, button):
        if self.selected_game and self.selected_profile:
            selected_players = self.game_editor.get_selected_players()
            if not selected_players:
                self._show_error_dialog("No instances selected to launch.")
                return

            self.selected_profile.selected_players = selected_players
            game_profile = GameProfile(
                game=self.selected_game, profile=self.selected_profile
            )

            self.instance_service.launch_game(game_profile)
            self.launch_button.set_visible(False)
            self.stop_button.set_visible(True)
            self.split_view.set_sensitive(False)  # Disable UI

    def on_stop_clicked(self, button):
        self.instance_service.terminate_all()
        self.launch_button.set_visible(True)
        self.stop_button.set_visible(False)
        self.split_view.set_sensitive(True)  # Enable UI


class ProtonCoopApplication(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.github.jules.protoncoop", **kwargs)
        resource_path = str(Path(__file__).parent / "resources" / "compiled.gresource")
        Gio.Resource.load(resource_path)._register()
        self.connect("activate", self.on_activate)

        # Carregar o CSS
        css_provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "style.css"
        css_provider.load_from_path(str(css_path))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def on_activate(self, app):
        self.win = ProtonCoopWindow(application=app)
        self.win.present()


def run_gui():
    """Lança a aplicação GUI."""
    # Definir o tema escuro usando a abordagem moderna ANTES de instanciar a app
    style_manager = Adw.StyleManager.get_default()
    style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    app = ProtonCoopApplication()
    app.run(sys.argv)
