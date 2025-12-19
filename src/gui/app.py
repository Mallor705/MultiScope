import sys
import threading
import time
import gi
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk
from ..core.config import Config
from ..core.exceptions import VirtualDeviceError
from ..core.logger import Logger
from ..models.profile import Profile
from ..services.instance import InstanceService
from ..services.kde_manager import KdeManager
from .layout_editor import LayoutSettingsPage


class MultiScopeWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("MultiScope")
        self.set_default_size(800, 600)

        self.logger = Logger("MultiScope-GUI", Config.LOG_DIR, reset=True)
        self.instance_service = InstanceService(logger=self.logger)
        self.profile = Profile.load()
        self.kde_manager = KdeManager(self.logger)

        self._launch_thread = None
        self._cancel_launch_event = threading.Event()

        self._build_ui()
        self._update_launch_button_state()

    def _show_error_dialog(self, message):
        dialog = Adw.MessageDialog(
            transient_for=self, modal=True, title="Error", body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _build_ui(self):
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.get_style_context().add_class("main-content")
        self.set_content(self.toolbar_view)

        header_bar = Adw.HeaderBar()
        header_bar.get_style_context().add_class("header-bar")
        self.toolbar_view.add_top_bar(header_bar)

        self.layout_settings_page = LayoutSettingsPage(self.profile, self.logger)
        self.layout_settings_page.connect("settings-changed", self._trigger_auto_save)
        self.layout_settings_page.connect(
            "instance-state-changed", self._on_instance_state_changed
        )
        self.toolbar_view.set_content(self.layout_settings_page)

        # Footer Bar for Play/Stop buttons
        self.footer_bar = Adw.HeaderBar()
        self.footer_bar.get_style_context().add_class("footer-bar")
        self.footer_bar.set_title_widget(Gtk.Label(label=""))
        self.footer_bar.set_show_end_title_buttons(False)
        self.toolbar_view.add_bottom_bar(self.footer_bar)

        self.launch_button = Gtk.Button.new_with_mnemonic("Play")
        self.launch_button.get_style_context().add_class("suggested-action")
        self.launch_button.get_style_context().add_class("launch-button")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        self.launch_button.set_sensitive(False)
        self.footer_bar.pack_end(self.launch_button)

        self.stop_button = Gtk.Button.new_with_mnemonic("Stop")
        self.stop_button.get_style_context().add_class("destructive-action")
        self.stop_button.get_style_context().add_class("stop-button")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_visible(False)
        self.footer_bar.pack_end(self.stop_button)

    def _trigger_auto_save(self, *args):
        updated_profile = self.layout_settings_page.get_updated_data()
        self.profile = updated_profile
        self.profile.save()
        self.logger.info("Profile auto-saved.")
        self.layout_settings_page._run_verification()
        self._update_launch_button_state()

    def _update_launch_button_state(self, *args):
        selected_players = self.layout_settings_page.get_selected_players()
        if not selected_players:
            self.launch_button.set_sensitive(False)
            return

        all_passed = True
        for player_num in selected_players:
            status = self.layout_settings_page.verification_service.get_instance_status(
                player_num
            )
            if status != "Passed":
                all_passed = False
                break
        self.launch_button.set_sensitive(all_passed)

    def _on_instance_state_changed(self, *args):
        if self.layout_settings_page.is_any_instance_running():
            self.launch_button.set_sensitive(False)
        else:
            self._update_launch_button_state()

    def _launch_worker(self):
        """Worker function to launch instances in a separate thread."""
        selected_players = self.profile.selected_players
        self.logger.info(f"Launch worker started for players: {selected_players}")

        try:
            for instance_num in selected_players:
                if self._cancel_launch_event.is_set():
                    self.logger.info("Launch sequence cancelled by user.")
                    break

                self.logger.info(f"Worker launching instance {instance_num}...")
                self.instance_service.launch_instance(self.profile, instance_num)
                time.sleep(5)  # Stagger launches

            # If the loop completes without errors, finalize the launch
            GLib.idle_add(self._on_launch_finished)

        except VirtualDeviceError as e:
            self.logger.error(f"Caught virtual device error: {e}. Aborting launch.")
            # Ensure any instances that *did* launch are stopped
            self.instance_service.terminate_all()
            # Safely update the UI from the main thread
            GLib.idle_add(self._show_error_dialog, f"Could not launch: {e}")
            GLib.idle_add(self._restore_ui_after_failed_launch)

    def _restore_ui_after_failed_launch(self):
        """Restores the UI to its pre-launch state after a failure."""
        self.kde_manager.restore_panel_states()
        self.launch_button.set_visible(True)
        self.stop_button.set_visible(False)
        self.layout_settings_page.set_sensitive(True)
        self.layout_settings_page.set_running_state(False)
        self._launch_thread = None
        self._cancel_launch_event.clear()
        self._update_launch_button_state()

    def _on_launch_finished(self):
        """Callback executed in the main thread when the launch worker is done."""
        self.logger.info("Launch worker finished.")
        # If the process was cancelled, terminate_all has already been called.
        # Otherwise, we just update the UI state.
        if not self._cancel_launch_event.is_set():
            self.launch_button.set_visible(False)
            self.stop_button.set_visible(True)
            self.layout_settings_page.set_sensitive(False)
            self.layout_settings_page.set_running_state(True)
        self._launch_thread = None
        self._cancel_launch_event.clear()


    def on_launch_clicked(self, button):
        self.layout_settings_page._run_verification()
        selected_players = self.layout_settings_page.get_selected_players()
        if not selected_players:
            self._show_error_dialog("No instances selected to launch.")
            return

        self.profile.selected_players = selected_players
        self.profile.save() # Save selection before launching

        if self.profile.enable_kwin_script:
            self.kde_manager.start_kwin_script(self.profile)

        # KDE Panel Management
        self.kde_manager.save_panel_states()
        self.kde_manager.set_panels_dodge_windows()

        # Update UI immediately to give feedback
        self.launch_button.set_visible(False)
        self.stop_button.set_visible(True)
        self.layout_settings_page.set_sensitive(False)

        # Start the launch process in a background thread
        self._cancel_launch_event.clear()
        self._launch_thread = threading.Thread(target=self._launch_worker)
        self._launch_thread.start()


    def on_stop_clicked(self, button):
        if self._launch_thread and self._launch_thread.is_alive():
            self.logger.info("Cancelling in-progress launch...")
            self._cancel_launch_event.set()
            # The worker will terminate running instances as it shuts down

        self.instance_service.terminate_all()

        # Stop KWin script if it was started
        self.kde_manager.stop_kwin_script()

        # KDE Panel Management
        self.kde_manager.restore_panel_states()

        self.launch_button.set_visible(True)
        self.stop_button.set_visible(False)
        self.layout_settings_page.set_sensitive(True)
        self.layout_settings_page.set_running_state(False)
        self.layout_settings_page._run_verification()
        self._update_launch_button_state()

class MultiScopeApplication(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.github.mallor705.multiscope", **kwargs)
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
