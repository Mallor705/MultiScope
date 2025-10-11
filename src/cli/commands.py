import signal
import subprocess
import os
from functools import lru_cache
from typing import Optional
from ..core.config import Config
from ..core.logger import Logger
from ..core.exceptions import LinuxCoopError, ProfileNotFoundError
from ..models.profile import GameProfile
from ..services.instance import InstanceService

class TerminateCLI(Exception):
    """Exception to terminate the CLI in a controlled manner."""
    pass

class LinuxCoopCLI:
    """Command-line interface for Linux-Coop."""
    def __init__(self):
        """Initializes the CLI with logger and signal configuration."""
        self.logger = Logger("linux-coop", Config.LOG_DIR)
        self._instance_service: Optional[InstanceService] = None
        self.setup_signal_handlers()

    @property
    def instance_service(self) -> InstanceService:
        """Lazy loading of InstanceService."""
        if self._instance_service is None:
            self._instance_service = InstanceService(self.logger)
        return self._instance_service

    def setup_signal_handlers(self):
        """Configures signal handlers to ensure cleanup upon exit."""
        def signal_handler(signum, frame):
            self.logger.info("Received interrupt signal. Terminating instances...")
            # Use the property to ensure InstanceService is initialized
            self.instance_service.terminate_all()
            raise TerminateCLI()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self, profile_name: str, edit_mode: bool = False, parent_pid: Optional[int] = None):
        """Main execution flow of the CLI."""
        if not profile_name or not profile_name.strip():
            self.logger.error("The profile name cannot be empty.")
            raise TerminateCLI()

        # Sanitize profile name to match the filesystem convention (spaces -> underscores)
        sanitized_profile_name = profile_name.replace(' ', '_')
        profile_path = Config.PROFILE_DIR / f"{sanitized_profile_name}.json"

        if not profile_path.exists():
            self.logger.error(f"Profile not found: {profile_path}")
            raise ProfileNotFoundError(f"Profile '{profile_name}' not found. Searched for '{sanitized_profile_name}.json'.")

        if edit_mode:
            self.edit_profile(profile_path)
            return # Exit after editing

        try:
            # Batch validations using the sanitized name
            self._batch_validate(sanitized_profile_name)

            # Load profile (with cache) using the sanitized name
            profile = self._load_profile(sanitized_profile_name)
            self.logger.info(f"Loaded profile env_vars: {profile.env_vars}")

            self.logger.info(f"Loading profile: {profile.game_name} for {profile.effective_num_players} players")

            # Pass the sanitized game_name from the profile to ensure consistency
            self.instance_service.launch_instances(profile, profile.game_name)
            # Pass the parent_pid to the monitoring loop
            self.instance_service.monitor_and_wait(parent_pid)
            self.logger.info("Script completed")
        except LinuxCoopError as e:
            self.logger.error(str(e))
            raise TerminateCLI()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.instance_service.terminate_all() # Ensure cleanup on unexpected error
            raise TerminateCLI()

    def _batch_validate(self, profile_name: str):
        """Executes all necessary validations in batch."""
        # Validate dependencies (cached in InstanceService)
        self.instance_service.validate_dependencies()

        # Validate profile exists
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        if not profile_path.exists():
            self.logger.error(f"Profile not found: {profile_path}")
            raise ProfileNotFoundError(f"Profile '{profile_name}' not found")

    @lru_cache(maxsize=16)
    def _load_profile(self, profile_name: str) -> GameProfile:
        """Loads profile with cache."""
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        return GameProfile.load_from_file(profile_path)

    def edit_profile(self, profile_path: os.PathLike):
        """Opens the specified profile file in the system's default text editor.
        Tries to use the EDITOR environment variable, otherwise a fallback like 'xdg-open'."""
        editor = os.environ.get('EDITOR')
        if editor:
            command = [editor, str(profile_path)]
        else:
            # Fallback for Linux. For Windows or macOS, different commands might be needed.
            command = ["xdg-open", str(profile_path)]
        
        self.logger.info(f"Opening profile {profile_path} with command: {' '.join(command)}")
        try:
            subprocess.run(command, check=True)
            self.logger.info("Profile opened successfully. Please save and close the editor to apply changes.")
        except FileNotFoundError:
            self.logger.error(f"Editor command not found: {command[0]}. Please set the EDITOR environment variable or install a suitable default application (e.g., 'xdg-open').")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error opening profile with editor: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while trying to open the profile: {e}")

def main(profile_name: str, edit_mode: bool = False, parent_pid: Optional[int] = None):
    """Launches game instances using the specified profile or edits it."""
    cli = LinuxCoopCLI()
    try:
        cli.run(profile_name, edit_mode=edit_mode, parent_pid=parent_pid)
    except TerminateCLI:
        pass
