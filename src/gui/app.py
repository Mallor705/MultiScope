import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from src.core import Config, Logger, Utils, VirtualDeviceError
from src.gui.layout_editor import LayoutSettingsPage
from src.models import Profile
from src.services import InstanceService, KdeManager


class TwinverseWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Twinverse")
        self.set_default_size(800, 600)

        self.logger = Logger("Twinverse-GUI", Config.LOG_DIR, reset=True)
        self.profile = Profile.load()
        self.kde_manager = KdeManager(self.logger)
        self.instance_service = InstanceService(logger=self.logger, kde_manager=self.kde_manager)
        self._launch_thread = None
        self._cancel_launch_event = threading.Event()
        self._is_running = False
        self.utils = Utils()
        self._build_ui()
        self._update_launch_button_state()
        self.connect("close-request", self.on_close_request)

    def _show_error_dialog(self, message):
        dialog = Adw.MessageDialog(transient_for=self, modal=True, title="Error", body=message)
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
        self.layout_settings_page.connect("verification-completed", self._update_launch_button_state)
        self.toolbar_view.set_content(self.layout_settings_page)

        # Footer Bar for Play/Stop buttons - Agora uma caixa comum
        self.footer_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6,
            homogeneous=False,
            halign=Gtk.Align.END,  # Alinha tudo à direita
        )

        # Adiciona um "spacer" expansível para empurrar o botão para direita
        spacer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        spacer.set_hexpand(True)  # Expande horizontalmente
        self.footer_bar.append(spacer)

        self.launch_button = Gtk.Button()
        self.launch_button.get_style_context().add_class("launch-button")
        self.launch_button.get_style_context().add_class("play-button-fixed-size")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        self.launch_button.set_sensitive(False)

        self.launch_spinner = Gtk.Spinner()
        self.launch_spinner.set_spinning(False)

        self.launch_label = Gtk.Label(label="Play")
        self.launch_content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            hexpand=False,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.launch_content_box.append(self.launch_label)

        self.launch_button.set_child(self.launch_content_box)
        self.footer_bar.append(self.launch_button)

        self.toolbar_view.add_bottom_bar(self.footer_bar)

    def _trigger_auto_save(self, *args):
        updated_profile = self.layout_settings_page.get_updated_data()
        self.profile = updated_profile
        self.profile.save()
        self.logger.info("Profile auto-saved.")
        self.layout_settings_page._run_all_verifications()
        self._update_launch_button_state()

    def _update_launch_button_state(self, *args):
        selected_players = self.layout_settings_page.get_selected_players()
        if not selected_players:
            self.launch_button.set_sensitive(False)
            return

        all_verified = all(self.layout_settings_page.get_instance_verification_status(p) for p in selected_players)
        self.launch_button.set_sensitive(all_verified)

    def _launch_worker(self):
        selected_players = self.profile.selected_players
        self.logger.info(f"Launch worker started for players: {selected_players}")

        try:
            for instance_num in selected_players:
                if self._cancel_launch_event.is_set():
                    self.logger.info("Launch sequence cancelled by user.")
                    break
                self.logger.info(f"Worker launching instance {instance_num}...")
                self.instance_service.launch_instance(self.profile, instance_num)
                time.sleep(5)

            if not self._cancel_launch_event.is_set():
                GLib.idle_add(self._on_launch_finished)

        except VirtualDeviceError as e:
            self.logger.error(f"Caught virtual device error: {e}. Aborting launch.")
            self.instance_service.terminate_all()
            GLib.idle_add(self._show_error_dialog, f"Could not launch: {e}")
            GLib.idle_add(self._restore_ui_after_failed_launch)

    def _restore_ui_after_failed_launch(self):
        self.kde_manager.restore_panel_states()
        self.launch_label.set_label("Play")
        self.launch_spinner.stop()
        if self.launch_spinner.get_parent() == self.launch_content_box:
            self.launch_content_box.remove(self.launch_spinner)
        self.layout_settings_page.set_sensitive(True)
        self.layout_settings_page.set_running_state(False)
        self._is_running = False
        self._launch_thread = None
        self._cancel_launch_event.clear()
        self._update_launch_button_state()

    def _on_launch_finished(self):
        self.logger.info("Launch worker finished.")
        if not self._cancel_launch_event.is_set():
            self.launch_label.set_label("Stop")
            self.launch_button.get_style_context().remove_class("launch-button")
            self.launch_button.get_style_context().add_class("stop-button")
            self.layout_settings_page.set_sensitive(False)
            self.layout_settings_page.set_running_state(True)
            self._is_running = True

        self.launch_spinner.stop()
        if self.launch_spinner.get_parent() == self.launch_content_box:
            self.launch_content_box.remove(self.launch_spinner)
        self.launch_button.set_sensitive(True)
        self._launch_thread = None
        self._cancel_launch_event.clear()

    def on_launch_clicked(self, button):
        if self._is_running:
            self.on_stop_clicked()
            return

        self.layout_settings_page._run_all_verifications()
        selected_players = self.layout_settings_page.get_selected_players()
        if not selected_players:
            self._show_error_dialog("No instances selected to launch.")
            return

        self.profile.selected_players = selected_players
        self.profile.save()

        if self.profile.enable_kwin_script:
            self.kde_manager.start_kwin_script(self.profile)

        self.kde_manager.save_panel_states()
        self.kde_manager.set_panels_dodge_windows()

        self.launch_label.set_label("Starting")
        self.launch_button.set_sensitive(False)
        self.launch_content_box.append(self.launch_spinner)
        self.launch_spinner.start()
        self.layout_settings_page.set_sensitive(False)

        self._cancel_launch_event.clear()
        self._launch_thread = threading.Thread(target=self._launch_worker)
        self._launch_thread.start()

    def on_stop_clicked(self):
        if self._launch_thread and self._launch_thread.is_alive():
            self.logger.info("Cancelling in-progress launch...")
            self._cancel_launch_event.set()

        self.launch_label.set_label("Stopping")
        self.launch_button.set_sensitive(False)
        self.launch_content_box.append(self.launch_spinner)
        self.launch_spinner.start()

        stop_thread = threading.Thread(target=self._stop_worker)
        stop_thread.start()

    def _stop_worker(self):
        self.instance_service.terminate_all()
        GLib.idle_add(self._on_termination_finished)

    def _on_termination_finished(self):
        self.logger.info("Termination worker finished.")
        self.launch_label.set_label("Play")
        self.launch_button.set_sensitive(True)
        self.launch_spinner.stop()
        if self.launch_spinner.get_parent() == self.launch_content_box:
            self.launch_content_box.remove(self.launch_spinner)
        self.launch_button.get_style_context().remove_class("stop-button")
        self.launch_button.get_style_context().add_class("launch-button")
        self.layout_settings_page.set_sensitive(True)
        self.layout_settings_page.set_running_state(False)
        self.layout_settings_page._run_all_verifications()
        self._update_launch_button_state()
        self._is_running = False

    def on_close_request(self, *args):
        self.logger.info("Close request received. Starting shutdown procedure.")
        self.set_sensitive(False)
        shutdown_thread = threading.Thread(target=self._shutdown_worker)
        shutdown_thread.start()
        return True

    def _shutdown_worker(self):
        self.logger.info("Shutdown worker started.")
        self._stop_worker()
        GLib.idle_add(self.get_application().quit)


class TwinverseApplication(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="io.github.mall0r.Twinverse", **kwargs)
        self.base_path = Utils.get_base_path()

        # Load resources
        resource_path = self.base_path / "res" / "compiled.gresource"
        if resource_path.exists():
            resources = Gio.Resource.load(str(resource_path))
            Gio.Resource._register(resources)

        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = TwinverseWindow(application=app)

        css_provider = Gtk.CssProvider()
        css_path = self.base_path / "res" / "styles" / "style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                self.win.get_display(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self.win.present()


def run_gui():
    """Launches the GUI application."""
    # Unset the old "prefer dark theme" setting to avoid Adwaita warnings
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-application-prefer-dark-theme", False)

    # Set the dark theme BEFORE instantiating the app
    style_manager = Adw.StyleManager.get_default()
    style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    app = TwinverseApplication()
    app.run(sys.argv)
