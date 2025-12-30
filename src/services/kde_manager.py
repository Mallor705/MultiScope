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
        self.kwin_script_id = None
        try:
            self.bus = pydbus.SessionBus()
            self.plasma_shell = self.bus.get("org.kde.plasmashell", "/PlasmaShell")
        except Exception as e:
            self.logger.warning(f"Could not connect to Plasma Shell via D-Bus: {e}")
            self.plasma_shell = None

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
        return "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "")

    def _run_plasma_script(self, script):
        """Run a Plasma Shell script using pydbus."""
        if not self.plasma_shell:
            self.logger.warning("Plasma Shell D-Bus service not available.")
            return None
        try:
            # The result from evaluateScript is often a string representation of the output,
            # which might be empty or require parsing.
            result = self.plasma_shell.evaluateScript(script)
            # pydbus might return the value directly, so we handle it as such.
            # If it's a string, we might need to strip trailing newlines.
            if isinstance(result, str):
                return result.strip()
            return result
        except Exception as e:
            self.logger.error(f"Error executing Plasma script via D-Bus: {e}")
            return None

    def get_panel_count(self):
        """Get the number of panels."""
        script = "print(panels().length)"
        count = self._run_plasma_script(script)
        # The script `print(panels().length)` returns a string like "2\n".
        # We need to handle this to get an integer.
        try:
            return int(str(count).strip())
        except (ValueError, TypeError):
            self.logger.error(f"Could not parse panel count from: {count}")
            return 0

    def save_panel_states(self):
        """Save the current visibility state of all panels."""
        if not self.is_kde_desktop() or not self.plasma_shell:
            return

        panel_count = self.get_panel_count()
        if panel_count == 0:
            self.logger.info("No KDE panels found.")
            return

        self.original_panel_states = {}
        for i in range(panel_count):
            script = f"print(panels()[{i}].hiding)"
            state = self._run_plasma_script(script)
            if state is not None:
                self.original_panel_states[i] = state
                self.logger.info(f"Saved panel {i} state: {state}")

    def set_panels_dodge_windows(self):
        """Set all panels to 'Dodge Windows' visibility."""
        if not self.is_kde_desktop() or not self.plasma_shell:
            return

        panel_count = self.get_panel_count()
        for i in range(panel_count):
            script = f"panels()[{i}].hiding = 'dodgewindows'"
            self._run_plasma_script(script)
            self.logger.info(f"Set panel {i} to 'Dodge Windows'")

    def restore_panel_states(self):
        """Restore the visibility state of all panels to their original state."""
        if not self.is_kde_desktop() or not self.plasma_shell or not self.original_panel_states:
            return

        for i, state in self.original_panel_states.items():
            # The 'null' state needs to be handled as a special case
            script_state = f"'{state}'" if state != "null" else "null"
            script = f"panels()[{i}].hiding = {script_state}"
            self._run_plasma_script(script)
            self.logger.info(f"Restored panel {i} to state: {state}")
        self.original_panel_states = {}
