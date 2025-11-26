import os
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import psutil

from ..core.config import Config
from ..core.exceptions import DependencyError
from ..core.logger import Logger
from ..models.profile import Profile, PlayerInstanceConfig


class InstanceService:
    """Service responsible for managing Steam instances."""

    # Constants for sandboxed user
    _SANDBOX_USER = "steamuser"
    _SANDBOX_UID = "1000"
    _SANDBOX_GID = "1000"
    _SANDBOX_HOME = f"/home/{_SANDBOX_USER}"

    def __init__(self, logger: Logger):
        """Initializes the instance service."""
        self.logger = logger
        self.pids: List[int] = []
        self.processes: List[subprocess.Popen] = []
        self.cpu_count = psutil.cpu_count(logical=True)
        self.termination_in_progress = False

    def launch_steam(self, profile: Profile) -> None:
        """A wrapper for launch_steam_instances that can be called from the GUI."""
        self.launch_steam_instances(profile)

    def validate_dependencies(self, use_gamescope: bool = True) -> None:
        """Validates if all necessary commands are available on the system."""
        self.logger.info("Validating dependencies...")
        required_commands = ["bwrap", "steam"]
        if use_gamescope:
            required_commands.insert(0, "gamescope")
        for cmd in required_commands:
            if not shutil.which(cmd):
                raise DependencyError(f"Required command '{cmd}' not found")
        self.logger.info("Dependencies validated successfully")

    def launch_steam_instances(self, profile: Profile) -> None:
        """Launches all Steam instances according to the provided profile."""
        self.validate_dependencies(use_gamescope=profile.use_gamescope)

        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

        num_instances = profile.effective_num_players()
        if num_instances == 0:
            self.logger.info("No instances to launch.")
            return

        self.logger.info(f"Launching {num_instances} instance(s) of Steam...")

        for i in range(num_instances):
            instance_num = (profile.selected_players[i] if profile.selected_players else i + 1)
            self._launch_single_instance(profile, instance_num)
            time.sleep(5) # Stagger launches

        self.logger.info(f"All {num_instances} instances launched")
        self.logger.info(f"PIDs: {self.pids}")

    def _launch_single_instance(self, profile: Profile, instance_num: int) -> None:
        """Launches a single steam instance."""
        self.logger.info(f"Preparing instance {instance_num}...")

        home_path = Config.get_steam_home_path(instance_num)
        home_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Instance {instance_num}: Using isolated home path '{home_path}'")

        # Share data from the main Steam installation
        self._share_steam_data(home_path)

        instance_idx = instance_num - 1
        device_info = self._validate_input_devices(profile, instance_idx, instance_num)

        env = self._prepare_environment(profile, device_info, instance_num)
        cmd = self._build_command(profile, device_info, instance_num, home_path)

        log_file = Config.LOG_DIR / f"steam_instance_{instance_num}.log"
        self.logger.info(f"Launching instance {instance_num} (Log: {log_file})")

        try:
            # Use 'script' command to capture all terminal output from nested processes
            # (gamescope -> bwrap -> steam). This is more reliable than stdout redirection
            # because it captures output from a pseudo-terminal.
            cmd_str = shlex.join(cmd)
            script_cmd = ["script", "-q", "-e", "-c", cmd_str, str(log_file)]
            
            process = subprocess.Popen(
                script_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=home_path,  # Launch from the isolated home directory
                preexec_fn=os.setpgrp,
            )
            self.pids.append(process.pid)
            self.processes.append(process)
            self.logger.info(f"Instance {instance_num} started with PID: {process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to launch instance {instance_num}: {e}")

    def _share_steam_data(self, home_path: Path) -> None:
        """
        Prepares the Steam directory structure for the sandbox.
        Creates writable directories and copies files that need to be instance-specific.
        Shared directories (common, compatdata) will be bind-mounted via bwrap.
        """
        self.logger.info(f"Preparing Steam data structure for instance at {home_path}...")

        real_user_home = Path.home()
        source_steam_dir = real_user_home / ".local/share/Steam"
        if not source_steam_dir.is_dir():
            self.logger.warning(
                f"Main Steam directory not found at '{source_steam_dir}'. Skipping data sharing."
            )
            return

        # Define destination paths within the sandboxed home
        dest_steam_dir = home_path / ".local/share/Steam"
        dest_steamapps_dir = dest_steam_dir / "steamapps"

        # Ensure destination directories exist
        try:
            dest_steamapps_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Ensured destination directory exists: {dest_steamapps_dir}")
        except OSError as e:
            self.logger.error(f"Failed to create destination directories: {e}")
            return

        # Essential Steam directories that will be bind-mounted via bwrap
        essential_dirs = [
            "ubuntu12_32",
            "ubuntu12_64",
            "linux32",
            "linux64",
            "bin",
            "package",
            "public",
            "resource",
            "graphics",
            "friends",
            "controller_base",
            "clientui",
            "steam",
            "legacycompat",
            "compatibilitytools.d",
        ]

        # Create mount point directories for essential Steam directories
        for dir_name in essential_dirs:
            source_dir = source_steam_dir / dir_name
            if source_dir.is_dir():
                mount_point = dest_steam_dir / dir_name
                mount_point.mkdir(exist_ok=True)
                self.logger.info(f"Created mount point for essential dir: {mount_point}")

        # Create mount points for all steamapps subdirectories
        source_steamapps_dir = source_steam_dir / "steamapps"
        if source_steamapps_dir.is_dir():
            for item in source_steamapps_dir.iterdir():
                if item.is_dir():
                    mount_point = dest_steamapps_dir / item.name
                    mount_point.mkdir(exist_ok=True)
                    self.logger.info(f"Created mount point for: {mount_point}")

        # Copy .acf manifest files - each instance needs its own copy
        if source_steamapps_dir.is_dir():
            for item in source_steamapps_dir.iterdir():
                if item.is_file() and item.suffix == ".acf":
                    dest_item_path = dest_steamapps_dir / item.name
                    if not dest_item_path.exists():
                        try:
                            shutil.copy2(item, dest_item_path)
                            self.logger.info(f"Copied manifest {item.name}")
                        except OSError as e:
                            self.logger.error(f"Failed to copy {item.name}: {e}")

    def _prepare_environment(self, profile: Profile, device_info: dict, instance_num: int) -> dict:
        """Prepares a minimal environment for the Steam instance."""
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)

        # This is critical for preventing system crashes and graphical glitches.
        env["ENABLE_GAMESCOPE_WSI"] = "1"

        # Set the HOME variable for the sandboxed user
        env["HOME"] = self._SANDBOX_HOME

        # Isolate steam instance data
        steam_data_path = Config.get_steam_data_path(instance_num)
        steam_data_path.mkdir(parents=True, exist_ok=True)
        env["STEAM_COMPAT_DATA_PATH"] = str(steam_data_path)

        # Handle joystick assignment
        if device_info.get("joystick_path_str_for_instance"):
            env["SDL_JOYSTICK_DEVICE"] = device_info["joystick_path_str_for_instance"]
            self.logger.info(f"Instance {instance_num}: Setting SDL_JOYSTICK_DEVICE to '{device_info['joystick_path_str_for_instance']}'.")

        # Handle audio device assignment
        if device_info.get("audio_device_id_for_instance"):
            env["PULSE_SINK"] = device_info["audio_device_id_for_instance"]
            self.logger.info(f"Instance {instance_num}: Setting PULSE_SINK to '{device_info['audio_device_id_for_instance']}'.")

        # Custom ENV variables are set via bwrap --setenv to target Steam directly.

        self.logger.info(f"Instance {instance_num}: Final environment prepared.")
        return env

    def _build_command(self, profile: Profile, device_info: dict, instance_num: int, home_path: Path) -> List[str]:
        """
        Builds the final command array in the correct order:
        [gamescope] -> [bwrap] -> [steam]  (when gamescope is enabled)
        [bwrap] -> [steam]                  (when gamescope is disabled)
        """
        instance_idx = instance_num - 1

        # 1. Build the innermost steam command
        steam_cmd = self._build_base_steam_command(instance_num, profile.use_gamescope)

        # 2. Build the bwrap command, which will wrap the steam command
        bwrap_cmd = self._build_bwrap_command(profile, instance_idx, device_info, instance_num, home_path)

        # 3. Prepend bwrap to the steam command
        final_cmd = bwrap_cmd + steam_cmd

        # 4. Build the Gamescope command and prepend it (if enabled)
        if profile.use_gamescope:
            should_add_grab_flags = device_info.get("should_add_grab_flags", False)
            gamescope_cmd = self._build_gamescope_command(profile, should_add_grab_flags, instance_num)

            # Add the '--' separator before the command Gamescope will run
            final_cmd = gamescope_cmd + ["--"] + final_cmd
            self.logger.info(f"Instance {instance_num}: Launching with Gamescope")
        else:
            self.logger.info(f"Instance {instance_num}: Launching without Gamescope (bwrap only)")

        self.logger.info(f"Instance {instance_num}: Full command: {shlex.join(final_cmd)}")
        return final_cmd

    def _validate_input_devices(self, profile: Profile, instance_idx: int, instance_num: int) -> dict:
        """Validates input devices and returns information about them."""
        # Get specific player config
        player_config = (
            profile.player_configs[instance_idx]
            if profile.player_configs and 0 <= instance_idx < len(profile.player_configs)
            else PlayerInstanceConfig() # Default empty config
        )

        def _validate_device(path_str: Optional[str], device_type: str) -> Optional[str]:
            if not path_str or not path_str.strip():
                return None
            path_obj = Path(path_str)
            if path_obj.exists() and path_obj.is_char_device():
                 self.logger.info(f"Instance {instance_num}: {device_type} device '{path_str}' assigned.")
                 return str(path_obj.resolve())
            self.logger.warning(
                f"Instance {instance_num}: {device_type} device '{path_str}' not found or not a char device."
            )
            return None

        mouse_path = _validate_device(player_config.MOUSE_EVENT_PATH, "Mouse")
        keyboard_path = _validate_device(player_config.KEYBOARD_EVENT_PATH, "Keyboard")
        joystick_path = _validate_device(player_config.PHYSICAL_DEVICE_ID, "Joystick")

        audio_id = player_config.AUDIO_DEVICE_ID
        if audio_id and audio_id.strip():
            self.logger.info(f"Instance {instance_num}: Audio device ID '{audio_id}' assigned.")

        return {
            "mouse_path_str_for_instance": mouse_path,
            "keyboard_path_str_for_instance": keyboard_path,
            "joystick_path_str_for_instance": joystick_path,
            "audio_device_id_for_instance": audio_id if audio_id and audio_id.strip() else None,
            "should_add_grab_flags": bool(mouse_path and keyboard_path),
        }

    def _build_gamescope_command(self, profile: Profile, should_add_grab_flags: bool, instance_num: int) -> List[str]:
        """Builds the Gamescope command."""
        width, height = profile.get_instance_dimensions(instance_num)
        if not width or not height:
            self.logger.error(f"Instance {instance_num}: Invalid dimensions. Aborting launch.")
            return []

        cmd = [
            "gamescope",
            "-e", # Enable Steam integration
            "-W", str(width),
            "-H", str(height),
            "-w", str(width),
            "-h", str(height),
            # "--mangoapp",
        ]

        if not profile.is_splitscreen_mode:
            cmd.extend(["-f", "--adaptive-sync"])
        else:
            cmd.append("-b") # Borderless

        if should_add_grab_flags:
            self.logger.info(f"Instance {instance_num}: Using dedicated mouse/keyboard. Grabbing input.")
            cmd.extend(["--grab", "--force-grab-cursor"])

        return cmd

    def _build_base_steam_command(self, instance_num: int, use_gamescope: bool = True) -> List[str]:
        """Builds the base steam command."""
        if use_gamescope:
            self.logger.info(f"Instance {instance_num}: Using Steam command with Gamescope flags.")
            return ["steam", "-gamepadui", "-steamos3", "-steamdeck", "-pipewire-dmabuf"]
        else:
            self.logger.info(f"Instance {instance_num}: Using plain Steam command.")
            return ["steam"]

    def _build_bwrap_command(self, profile: Profile, instance_idx: int, device_info: dict, instance_num: int, home_path: Path) -> List[str]:
        """Builds the bwrap command, including device bindings and Steam directory mounts."""
        cmd = [
            "bwrap",
            "--die-with-parent",
            "--unshare-user",  # Isolate user namespace
            "--dev-bind", "/", "/",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--tmpfs", "/home",  # Create a writable /home for the user mount
            "--share-net",
            # Mount the isolated home directory to the fake user's home
            "--bind", str(home_path), self._SANDBOX_HOME,
        ]

        # Add bind mounts for shared Steam directories
        cmd.extend(self._get_steam_bind_mounts(home_path, instance_num))

        # Handle input device bindings
        device_paths_to_bind = [
            p for p in [
                device_info.get("joystick_path_str_for_instance"),
                device_info.get("mouse_path_str_for_instance"),
                device_info.get("keyboard_path_str_for_instance")
            ] if p
        ]

        if device_paths_to_bind:
            cmd.extend(["--tmpfs", "/dev/input"])
            for device_path in device_paths_to_bind:
                cmd.extend(["--dev-bind", device_path, device_path])
                self.logger.info(f"Instance {instance_num}: bwrap will bind '{device_path}'.")
        else:
            cmd.extend(["--tmpfs", "/dev/input"])

        # Ensure custom ENV variables reach Steam inside the sandbox
        try:
            extra_env = profile.get_env_for_instance(instance_idx) if hasattr(profile, "get_env_for_instance") else {}
            for k, v in (extra_env or {}).items():
                if v is None:
                    v = ""
                cmd.extend(["--setenv", str(k), str(v)])
            if extra_env:
                self.logger.info(f"Instance {instance_num}: Added {len(extra_env)} --setenv entries to bwrap.")
        except Exception as e:
            self.logger.error(f"Instance {instance_num}: Failed to add --setenv entries: {e}")
        return cmd

    def _get_steam_bind_mounts(self, home_path: Path, instance_num: int) -> List[str]:
        """
        Returns bwrap bind mount arguments for sharing Steam directories.
        This replaces symlinks with proper bind mounts that work correctly in the sandbox.
        """
        bind_args = []
        real_user_home = Path.home()
        source_steam_dir = real_user_home / ".local/share/Steam"

        if not source_steam_dir.is_dir():
            return bind_args

        # Sandbox destination base path
        sandbox_steam_dir = f"{self._SANDBOX_HOME}/.local/share/Steam"

        # Essential Steam directories that must be shared (read-only) for Steam to run
        # These contain the Steam client binaries and runtime
        essential_ro_dirs = [
            "ubuntu12_32",
            "ubuntu12_64",
            "linux32",
            "linux64",
            "bin",
            "package",
            "public",
            "resource",
            "graphics",
            "friends",
            "controller_base",
            "clientui",
            "steam",
            "legacycompat",
            "compatibilitytools.d",
        ]

        # Essential files that need to be shared (read-only)
        essential_ro_files = [
            "steam.sh",
            "bootstrap.tar.xz",
            "fossilize_engine_filters.json",
        ]

        # Bind mount essential directories as read-only
        for dir_name in essential_ro_dirs:
            source_dir = source_steam_dir / dir_name
            if source_dir.is_dir():
                bind_args.extend([
                    "--ro-bind", str(source_dir), f"{sandbox_steam_dir}/{dir_name}"
                ])
                self.logger.info(f"Instance {instance_num}: Will bind-mount {dir_name} (ro)")

        # Bind mount essential files as read-only
        for file_name in essential_ro_files:
            source_file = source_steam_dir / file_name
            if source_file.is_file():
                bind_args.extend([
                    "--ro-bind", str(source_file), f"{sandbox_steam_dir}/{file_name}"
                ])
                self.logger.info(f"Instance {instance_num}: Will bind-mount {file_name} (ro)")

        # Bind mount ALL steamapps subdirectories (read-write for game data)
        source_steamapps = source_steam_dir / "steamapps"
        if source_steamapps.is_dir():
            sandbox_steamapps = f"{sandbox_steam_dir}/steamapps"

            for item in source_steamapps.iterdir():
                if item.is_dir():
                    bind_args.extend([
                        "--bind", str(item), f"{sandbox_steamapps}/{item.name}"
                    ])
                    self.logger.info(f"Instance {instance_num}: Will bind-mount steamapps/{item.name}")

        return bind_args

    def terminate_all(self) -> None:
        """Terminates all managed steam instances."""
        if self.termination_in_progress:
            return
        try:
            self.termination_in_progress = True
            self.logger.info("Starting termination of all instances...")

            for process in self.processes:
                if process.poll() is None: # if process is still running
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        self.logger.info(f"Sent SIGKILL to process group of PID {process.pid}")
                    except ProcessLookupError:
                        self.logger.info(f"Process group for PID {process.pid} not found.")
                    except Exception as e:
                        self.logger.error(f"Failed to kill process group for PID {process.pid}: {e}")

            # Wait for all processes to terminate
            for process in self.processes:
                process.wait()

            self.logger.info("Instance termination complete.")
            self.pids = []
            self.processes = []
        finally:
            self.termination_in_progress = False
