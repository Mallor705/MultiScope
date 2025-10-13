import os
import signal
import subprocess
from functools import lru_cache
from typing import Optional

from ..core.config import Config
from ..core.exceptions import LinuxCoopError, ProfileNotFoundError
from ..core.logger import Logger
from ..models.profile import GameProfile
from ..services.instance import InstanceService


class TerminateCLI(Exception):
    """Custom exception used to signal a controlled termination of the CLI."""
    pass


class LinuxCoopCLI:
    """
    The main command-line interface for Proton-Coop.

    This class orchestrates the application's flow when run from the terminal.
    It handles signal trapping for graceful shutdowns, lazy-loads services,
    and manages the primary operations of running or editing a game profile.
    """

    def __init__(self):
        """Initializes the CLI, setting up the logger and signal handlers."""
        self.logger = Logger("proton-coop", Config.LOG_DIR)
        self._instance_service: Optional[InstanceService] = None
        self.setup_signal_handlers()

    @property
    def instance_service(self) -> InstanceService:
        """
        Provides lazy-loaded access to the InstanceService.

        This avoids initializing the service until it's actually needed,
        improving startup time for operations that don't require it (like
        listing profiles).

        Returns:
            InstanceService: The singleton instance of the service.
        """
        if self._instance_service is None:
            self._instance_service = InstanceService(self.logger)
        return self._instance_service

    def setup_signal_handlers(self):
        """
        Configures handlers for SIGINT and SIGTERM to ensure graceful shutdown.

        When a handled signal is received, it triggers the termination of all
        game instances before exiting.
        """
        def signal_handler(signum, frame):
            self.logger.info("Interrupt signal received. Terminating instances...")
            self.instance_service.terminate_all()
            raise TerminateCLI()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self, profile_name: str, edit_mode: bool = False, parent_pid: Optional[int] = None):
        """
        The main execution entry point for the CLI.

        It validates the profile, loads it, and either launches the game
        instances or opens the profile for editing. It also initiates the

        process monitoring loop if instances are launched.

        Args:
            profile_name (str): The name of the game profile to use.
            edit_mode (bool): If True, open the profile in a text editor
                              instead of running it.
            parent_pid (Optional[int]): The PID of a parent process (e.g., the GUI)
                                        to monitor for termination.
        """
        if not profile_name or not profile_name.strip():
            self.logger.error("Profile name cannot be empty.")
            raise TerminateCLI()

        sanitized_name = profile_name.replace(' ', '_').replace('-', '_')
        profile_path = Config.PROFILE_DIR / f"{sanitized_name}.json"

        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile '{profile_name}' not found.")

        if edit_mode:
            self.edit_profile(profile_path)
            return

        try:
            self._validate_dependencies()
            profile = self._load_profile(sanitized_name)
            self.logger.info(f"Loaded profile: {profile.game_name} for {profile.effective_num_players()} players")
            self.instance_service.launch_instances(profile, profile.game_name)
            self.instance_service.monitor_and_wait(parent_pid)
            self.logger.info("Script completed.")
        except LinuxCoopError as e:
            self.logger.error(str(e))
            raise TerminateCLI()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.instance_service.terminate_all()  # Ensure cleanup
            raise TerminateCLI()

    def _validate_dependencies(self):
        """Executes all necessary pre-run validations."""
        self.instance_service.validate_dependencies()

    @lru_cache(maxsize=16)
    def _load_profile(self, profile_name: str) -> GameProfile:
        """Loads a game profile from a file, with caching."""
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        return GameProfile.load_from_file(profile_path)

    def edit_profile(self, profile_path: os.PathLike):
        """
        Opens the specified profile file in the system's default text editor.

        It respects the `EDITOR` environment variable if set, otherwise it
        falls back to `xdg-open`.

        Args:
            profile_path (os.PathLike): The path to the profile `.json` file.
        """
        editor = os.environ.get('EDITOR')
        command = [editor, str(profile_path)] if editor else ["xdg-open", str(profile_path)]

        self.logger.info(f"Opening profile with command: {' '.join(command)}")
        try:
            subprocess.run(command, check=True)
            self.logger.info("Profile opened. Save and close the editor to apply changes.")
        except FileNotFoundError:
            self.logger.error(f"Editor command not found: {command[0]}.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error opening profile with editor: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")


def main(profile_name: str, edit_mode: bool = False, parent_pid: Optional[int] = None):
    """
    The main function for the command-line entry point.

    Initializes and runs the `LinuxCoopCLI`, handling the `TerminateCLI`
    exception for a clean exit.

    Args:
        profile_name (str): The name of the profile to run or edit.
        edit_mode (bool): If true, opens the profile for editing.
        parent_pid (Optional[int]): The PID of the calling process to monitor.
    """
    cli = LinuxCoopCLI()
    try:
        cli.run(profile_name, edit_mode=edit_mode, parent_pid=parent_pid)
    except TerminateCLI:
        pass
