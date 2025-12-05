import os
import shlex
import copy
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# import psutil

from ..core.config import Config
from ..core.exceptions import DependencyError, VirtualDeviceError
from ..core.logger import Logger
from ..models.profile import Profile, PlayerInstanceConfig
from .virtual_device_service import VirtualDeviceService


class InstanceService:
    """Service responsible for managing Steam instances."""

    def __init__(self, logger: Logger):
        """Initializes the instance service."""
        self.logger = logger
        self.virtual_device_service = VirtualDeviceService(logger)
        self._virtual_joystick_path: Optional[str] = None
        self._virtual_joystick_checked: bool = False
        self.pids: dict[int, int] = {}
        self.processes: dict[int, subprocess.Popen] = {}
        # self.cpu_count = psutil.cpu_count(logical=True)
        self.termination_in_progress = False

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

    def _launch_single_instance(self, profile: Profile, instance_num: int) -> None:
        """Launches a single steam instance."""
        self.logger.info(f"Preparing instance {instance_num}...")

        home_path = Config.get_steam_home_path(instance_num)
        home_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Instance {instance_num}: Using isolated home path '{home_path}'")

        # Prepare minimal home structure - Steam will auto-install on first run
        self._prepare_steam_home(home_path)

        instance_idx = instance_num - 1
        device_info = self._validate_input_devices(profile, instance_idx, instance_num)

        env = self._prepare_environment(profile, device_info, instance_num)
        total_instances = profile.effective_num_players()
        cmd = self._build_command(profile, device_info, instance_num, home_path, total_instances)

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
                cwd=Path.home(),  # Launch from the user's real home directory
                preexec_fn=os.setpgrp,
            )
            self.pids[instance_num] = process.pid
            self.processes[instance_num] = process
            self.logger.info(f"Instance {instance_num} started with PID: {process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to launch instance {instance_num}: {e}")

    def launch_instance(
        self,
        profile: Profile,
        instance_num: int,
        use_gamescope_override: Optional[bool] = None,
    ) -> None:
        """Launches a single Steam instance."""
        if not self._virtual_joystick_checked:
            self._virtual_joystick_checked = True
            needs_virtual_joystick = False
            num_players = profile.effective_num_players()
            if num_players > 0:
                # Check player configs up to the number of players
                for i in range(num_players):
                    player_config = (
                        profile.player_configs[i]
                        if profile.player_configs and i < len(profile.player_configs)
                        else PlayerInstanceConfig()
                    )
                    if not player_config.PHYSICAL_DEVICE_ID:
                        needs_virtual_joystick = True
                        break

            if needs_virtual_joystick:
                self.logger.info("One or more instances lack a physical joystick. Creating a virtual one.")
                try:
                    self._virtual_joystick_path = self.virtual_device_service.create_virtual_joystick()
                except VirtualDeviceError:
                    self.logger.error("Halting launch due to virtual joystick creation failure.")
                    # Re-raise the exception to be caught by the UI layer
                    raise

        active_profile = profile
        if use_gamescope_override is not None:
            active_profile = copy.deepcopy(profile)
            active_profile.use_gamescope = use_gamescope_override

        self.validate_dependencies(use_gamescope=active_profile.use_gamescope)
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._launch_single_instance(active_profile, instance_num)

    def terminate_instance(self, instance_num: int) -> None:
        """Terminates a single Steam instance."""
        if instance_num not in self.processes:
            self.logger.warning(
                f"Attempted to terminate non-existent instance {instance_num}"
            )
            return

        process = self.processes[instance_num]
        if process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                self.logger.info(
                    f"Sent SIGKILL to process group of PID {process.pid} for instance {instance_num}"
                )
            except ProcessLookupError:
                self.logger.info(
                    f"Process group for PID {process.pid} not found for instance {instance_num}."
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to kill process group for PID {process.pid} for instance {instance_num}: {e}"
                )
        process.wait()
        del self.processes[instance_num]
        del self.pids[instance_num]

    def _prepare_steam_home(self, home_path: Path) -> None:
        """
        Prepares the isolated Steam directories for the instance.
        This involves creating the directory structure and copying app manifests
        to ensure games are recognized.
        """
        self.logger.info(f"Preparing isolated Steam directories for instance at {home_path}...")

        instance_steam_local = home_path / ".local/share/Steam"
        instance_steam_dot_steam = home_path / ".steam"

        # Create essential Steam directories within the instance's isolated path
        (instance_steam_local / "steamapps").mkdir(parents=True, exist_ok=True)
        instance_steam_dot_steam.mkdir(parents=True, exist_ok=True)

        # Copy .acf (app manifest) files from the host to the instance.
        # This makes Steam recognize games as "installed" so it can find them
        # in the shared steamapps/common directory.
        host_steamapps = Path.home() / ".local/share/Steam/steamapps"
        dest_steamapps = instance_steam_local / "steamapps"

        if host_steamapps.exists():
            for acf_file in host_steamapps.glob("*.acf"):
                dest_file = dest_steamapps / acf_file.name
                if not dest_file.exists():
                    shutil.copy(acf_file, dest_file)
        else:
            self.logger.warning(f"Host Steam directory '{host_steamapps}' not found. Cannot copy game manifests.")

        self.logger.info("Isolated Steam directories are ready.")

    def _prepare_environment(self, profile: Profile, device_info: dict, instance_num: int) -> dict:
        """Prepares a minimal environment for the Steam instance."""
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)

        # Enable this if you experience system crashes and graphical glitches.
        env["ENABLE_GAMESCOPE_WSI"] = "0"
        env["LD_PRELOAD"] = ""
        # Handle audio device assignment
        if device_info.get("audio_device_id_for_instance"):
            env["PULSE_SINK"] = device_info["audio_device_id_for_instance"]
            self.logger.info(f"Instance {instance_num}: Setting PULSE_SINK to '{device_info['audio_device_id_for_instance']}'.")

        # Custom ENV variables are set via bwrap --setenv to target Steam directly.

        self.logger.info(f"Instance {instance_num}: Final environment prepared.")
        return env

    def _build_command(self, profile: Profile, device_info: dict, instance_num: int, home_path: Path, total_instances: int = 2) -> List[str]:
        """
        Builds the final command array in the correct order:
        [taskset] -> [gamescope] -> [bwrap] -> [steam]  (when gamescope is enabled)
        [taskset] -> [bwrap] -> [steam]                  (when gamescope is disabled)
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

        # mouse_path = _validate_device(player_config.MOUSE_EVENT_PATH, "Mouse")
        # keyboard_path = _validate_device(player_config.KEYBOARD_EVENT_PATH, "Keyboard")
        mouse_path = None
        keyboard_path = None
        joystick_path = _validate_device(player_config.PHYSICAL_DEVICE_ID, "Joystick")

        audio_id = player_config.AUDIO_DEVICE_ID
        if audio_id and audio_id.strip():
            self.logger.info(f"Instance {instance_num}: Audio device ID '{audio_id}' assigned.")

        return {
            "mouse_path_str_for_instance": mouse_path,
            "keyboard_path_str_for_instance": keyboard_path,
            "joystick_path_str_for_instance": joystick_path,
            "audio_device_id_for_instance": audio_id if audio_id and audio_id.strip() else None,
            "should_add_grab_flags": player_config.grab_input_devices,
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
            "-o", "999", # Always set an unfocused FPS limit to a very high value
            "-r", "999", # Always set a focused FPS limit to a very high value
            # "--xwayland-count", "2",
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
            return ["steam", "-gamepadui", "-steamdeck", "-steamos3"]
        else:
            self.logger.info(f"Instance {instance_num}: Using plain Steam command.")
            return ["steam"]

    def _build_bwrap_command(self, profile: Profile, instance_idx: int, device_info: dict, instance_num: int, home_path: Path) -> List[str]:
        """
        Builds the bwrap command for sandboxing.
        This strategy uses the real user's home directory but mounts instance-specific
        Steam directories over the real ones to achieve isolation.
        """
        real_home = Path.home()
        instance_steam_local = home_path / ".local/share/Steam"
        instance_steam_dot_steam = home_path / ".steam"
        target_steam_local = real_home / ".local/share/Steam"
        target_steam_dot_steam = real_home / ".steam"

        cmd = [
            "bwrap",
            "--dev-bind", "/", "/",
            "--dev-bind", "/dev", "/dev",
            "--tmpfs", "/dev/shm",
            "--proc", "/proc",
            "--die-with-parent",
            "--unshare-ipc",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-cgroup",
            "--new-session",
            "--tmpfs", "/tmp",
            "--bind", "/tmp/.X11-unix", "/tmp/.X11-unix",
        ]

        # --- Device Isolation ---
        cmd.extend(["--tmpfs", "/dev/input"])

        joystick_path = device_info.get("joystick_path_str_for_instance")
        # If the instance has no physical joystick, assign the virtual one if it exists
        if not joystick_path and self._virtual_joystick_path:
            self.logger.info(f"Instance {instance_num}: Assigning virtual joystick '{self._virtual_joystick_path}'.")
            joystick_path = self._virtual_joystick_path

        device_paths_to_bind = [
            device_info.get("mouse_path_str_for_instance"),
            device_info.get("keyboard_path_str_for_instance"),
            joystick_path,
        ]
        for device_path in device_paths_to_bind:
            if device_path:
                self.logger.info(f"Instance {instance_num}: Exposing device '{device_path}' to sandbox.")
                cmd.extend(["--dev-bind", device_path, device_path])

        if Path("/dev/uinput").exists():
            cmd.extend(["--dev-bind", "/dev/uinput", "/dev/uinput"])
        if Path("/dev/input/mice").exists():
            cmd.extend(["--dev-bind", "/dev/input/mice", "/dev/input/mice"])
        # --- End Device Isolation ---

        # --- Steam Directory Isolation ---
        # Mount the instance-specific directories over the real Steam locations
        cmd.extend([
            "--bind", str(instance_steam_local), str(target_steam_local),
            "--bind", str(instance_steam_dot_steam), str(target_steam_dot_steam),
        ])

        # Mount host's common games and compatibility tools into the sandboxed Steam directory
        host_steam_path = str(target_steam_local)
        sandbox_steam_path = str(target_steam_local) # Same path, but it's now a mount point

        # Share games
        common_path = Path(host_steam_path) / "steamapps/common"
        if common_path.exists():
            cmd.extend(["--bind", str(common_path), str(Path(sandbox_steam_path) / "steamapps/common")])

        # Share compatibility tools
        host_compat = Path(host_steam_path) / "compatibilitytools.d"
        sandbox_compat = Path(sandbox_steam_path) / "compatibilitytools.d"
        if host_compat.exists():
            ignore = {"LegacyRuntime"}
            for folder in host_compat.iterdir():
                if folder.is_dir() and folder.name not in ignore:
                    cmd.extend(["--bind", str(folder), str(sandbox_compat / folder.name)])
        # --- End Steam Directory Isolation ---

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

    def terminate_all(self) -> None:
        """Terminates all managed steam instances."""
        if self.termination_in_progress:
            return
        try:
            self.termination_in_progress = True
            self.logger.info("Starting termination of all instances...")

            for instance_num in list(self.processes.keys()):
                self.terminate_instance(instance_num)

            self.logger.info("Instance termination complete.")
            self.pids.clear()
            self.processes.clear()

            if self._virtual_joystick_path:
                self.virtual_device_service.destroy_virtual_joystick()
                self._virtual_joystick_path = None
            self._virtual_joystick_checked = False
        finally:
            self.termination_in_progress = False
