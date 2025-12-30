import os
import subprocess
import json
from ..core.logger import Logger
from pathlib import Path
from ..models.profile import Profile
import pydbus

class KdeManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.original_panel_states = {}
        self.qdbus_command = self._find_qdbus_command()
        self.kwin_script_id = None

    def start_kwin_script(self, profile: Profile):
        """
        Starts the appropriate KWin script using D-Bus.
        """
        if not self.is_kde_desktop():
            self.logger.warning("Not a KDE desktop, skipping KWin script.")
            return

        # Se não for splitscreen, ativa o script per-monitor para fullscreen
        if not profile.is_splitscreen_mode or not profile.splitscreen:
            self.logger.info("Fullscreen mode, loading KWin script.")
            script_name = "kwin_gamescope.js"
        else:
            orientation = profile.splitscreen.orientation
            script_name = "kwin_gamescope_vertical.js" if orientation == "vertical" else "kwin_gamescope_horizontal.js"

        script_path = Path(__file__).parent.parent.parent / "scripts" / script_name

        self.logger.info(f"Attempting to load KWin script: {script_path}")

        if not script_path.exists():
            self.logger.error(f"KWin script not found at {script_path}")
            return

        try:
            bus = pydbus.SessionBus()
            kwin_proxy = bus.get("org.kde.KWin", "/Scripting")

            self.logger.info("Loading KWin script via D-Bus...")
            self.kwin_script_id = kwin_proxy.loadScript(str(script_path))
            self.logger.info(f"KWin script loaded with ID: {self.kwin_script_id}.")

            try:
                self.logger.info("Attempting to explicitly start the script...")
                kwin_proxy.start()
                self.logger.info("KWin script started successfully.")
            except Exception as e:
                self.logger.warning(f"Could not explicitly start KWin script (this may be normal): {e}")

        except Exception as e:
            self.logger.error(f"Failed to load KWin script via D-Bus: {e}")

    def stop_kwin_script(self):
        """
        Stops and unloads the KWin splitscreen script using its ID.
        """
        if not self.kwin_script_id:
            self.logger.info("No KWin script ID to stop.")
            return

        try:
            bus = pydbus.SessionBus()
            kwin_proxy = bus.get("org.kde.KWin", "/Scripting")

            self.logger.info(f"Unloading KWin script with ID: {self.kwin_script_id}...")
            # Note: KWin's unloadScript might take the ID, but some docs suggest the object path.
            # The pydbus proxy object should handle this correctly. Let's assume the ID is what's needed.
            # Based on newer patterns, often the script object itself has a stop/unload method,
            # but for this API, unloadScript on the main interface is the documented way.
            kwin_proxy.unloadScript(str(self.kwin_script_id))

            self.logger.info("KWin script unloaded successfully.")
            self.kwin_script_id = None

        except Exception as e:
            self.logger.error(f"Failed to stop KWin script via D-Bus: {e}")


    def is_kde_desktop(self):
        """Check if the current desktop environment is KDE."""
        return os.environ.get("XDG_CURRENT_DESKTOP") == "KDE"

    def _find_qdbus_command(self):
        """Find the correct qdbus command (qdbus or qdbus6)."""
        for cmd in ["qdbus6", "qdbus"]:
            try:
                subprocess.run([cmd, "--version"], capture_output=True, check=True)
                self.logger.info(f"Using '{cmd}' for dbus communication.")
                return cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        self.logger.warning("Neither 'qdbus' nor 'qdbus6' command found.")
        return None

    def _run_qdbus_script(self, script):
        """Run a Plasma Shell script using the detected qdbus command."""
        if not self.qdbus_command:
            return None
        try:
            command = [
                self.qdbus_command,
                "org.kde.plasmashell",
                "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript",
                script,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error executing qdbus script: {e}")
            self.logger.error(f"Stderr: {e.stderr}")
            return None
        except FileNotFoundError:
            self.logger.error(f"'{self.qdbus_command}' not found.")
            return None

    def get_panel_count(self):
        """Get the number of panels."""
        script = "print(panels().length)"
        count_str = self._run_qdbus_script(script)
        return int(count_str) if count_str and count_str.isdigit() else 0

    def save_panel_states(self):
        """Save the current visibility state of all panels."""
        if not self.is_kde_desktop() or not self.qdbus_command:
            return

        panel_count = self.get_panel_count()
        if panel_count == 0:
            self.logger.info("No KDE panels found.")
            return

        self.original_panel_states = {}
        for i in range(panel_count):
            script = f"print(panels()[{i}].hiding)"
            state = self._run_qdbus_script(script)
            if state is not None:
                self.original_panel_states[i] = state
                self.logger.info(f"Saved panel {i} state: {state}")

    def set_panels_dodge_windows(self):
        """Set all panels to 'Dodge Windows' visibility."""
        if not self.is_kde_desktop() or not self.qdbus_command:
            return

        panel_count = self.get_panel_count()
        for i in range(panel_count):
            script = f"panels()[{i}].hiding = 'dodgewindows'"
            self._run_qdbus_script(script)
            self.logger.info(f"Set panel {i} to 'Dodge Windows'")

    def restore_panel_states(self):
        """Restore the visibility state of all panels to their original state."""
        if not self.is_kde_desktop() or not self.qdbus_command or not self.original_panel_states:
            return

        for i, state in self.original_panel_states.items():
            # The 'null' state needs to be handled as a special case
            script_state = f"'{state}'" if state != "null" else "null"
            script = f"panels()[{i}].hiding = {script_state}"
            self._run_qdbus_script(script)
            self.logger.info(f"Restored panel {i} to state: {state}")
        self.original_panel_states = {}
