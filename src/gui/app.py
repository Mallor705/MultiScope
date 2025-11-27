import sys
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk
from ..core.config import Config
from ..core.logger import Logger
from ..models.profile import Profile
from ..services.instance import InstanceService
from .layout_editor import LayoutSettingsPage

class MultiScopeWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("MultiScope")
        self.set_default_size(800, 600)

        self.logger = Logger("MultiScope-GUI", Config.LOG_DIR, reset=True)
        self.instance_service = InstanceService(logger=self.logger)
        self.profile = Profile.load()

        self._build_ui()

    def _show_error_dialog(self, message):
        dialog = Adw.MessageDialog(
            transient_for=self, modal=True, title="Error", body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _build_ui(self):
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        header_bar = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header_bar)

        self.layout_settings_page = LayoutSettingsPage(self.profile, self.logger)
        self.layout_settings_page.connect("settings-changed", self._trigger_auto_save)
        self.toolbar_view.set_content(self.layout_settings_page)

        # Footer Bar for Launch/Stop buttons
        self.footer_bar = Adw.HeaderBar()
        self.footer_bar.set_show_end_title_buttons(False)
        self.toolbar_view.add_bottom_bar(self.footer_bar)

        self.launch_button = Gtk.Button.new_with_mnemonic("_Launch Steam")
        self.launch_button.get_style_context().add_class("suggested-action")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        self.footer_bar.pack_end(self.launch_button)

        self.stop_button = Gtk.Button.new_with_mnemonic("_Stop All")
        self.stop_button.get_style_context().add_class("destructive-action")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_visible(False)
        self.footer_bar.pack_end(self.stop_button)

    def _trigger_auto_save(self, *args):
        updated_profile = self.layout_settings_page.get_updated_data()
        self.profile = updated_profile
        self.profile.save()
        self.logger.info("Profile auto-saved.")
        self.layout_settings_page._run_verification()

    def on_launch_clicked(self, button):
        self.layout_settings_page._run_verification()
        selected_players = self.layout_settings_page.get_selected_players()
        if not selected_players:
            self._show_error_dialog("No instances selected to launch.")
            return

        self.profile.selected_players = selected_players
        self.profile.save() # Save selection before launching

        self.instance_service.launch_steam(self.profile)
        self.launch_button.set_visible(False)
        self.stop_button.set_visible(True)
        self.layout_settings_page.set_sensitive(False) # Disable UI during session

    def on_stop_clicked(self, button):
        self.instance_service.terminate_all()
        self.launch_button.set_visible(True)
        self.stop_button.set_visible(False)
        self.layout_settings_page.set_sensitive(True) # Re-enable UI
        self.layout_settings_page._run_verification()

class MultiScopeApplication(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.github.jules.multiscope", **kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = MultiScopeWindow(application=app)

        css_provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                self.win.get_display(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self.win.present()

def run_gui():
    """Lança a aplicação GUI."""
    # Set the dark theme BEFORE instantiating the app
    style_manager = Adw.StyleManager.get_default()
    style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    app = MultiScopeApplication()
    app.run(sys.argv)
