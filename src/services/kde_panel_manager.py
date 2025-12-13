import os
import subprocess
import json
from ..core.logger import Logger

class KdePanelManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.original_panel_states = {}
        self.qdbus_command = self._find_qdbus_command()

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
