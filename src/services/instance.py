import os
import shlex
import copy
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from ..core.config import Config
from ..core.exceptions import DependencyError, VirtualDeviceError
from ..core.logger import Logger
from ..models.profile import Profile, PlayerInstanceConfig
from .virtual_device import VirtualDeviceService
from .cmd_builder import CommandBuilder
from .kde_manager import KdeManager
from .device_manager import DeviceManager


class InstanceService:
    """Service responsible for managing Steam instances."""

    def __init__(self, logger: Logger, kde_manager: Optional[KdeManager] = None):
        """Initializes the instance service."""
        self.logger = logger
        self.virtual_device = VirtualDeviceService(logger)
        self.kde_manager = kde_manager
        self.device_manager = DeviceManager()
        self._virtual_joystick_path: Optional[str] = None
        self._virtual_joystick_checked: bool = False
        self.pids: dict[int, int] = {}
        self.pgids: dict[int, int] = {}
        self.processes: dict[int, subprocess.Popen] = {}
        self.termination_in_progress = False
        self.is_flatpak = self._is_flatpak()

    def _is_flatpak(self) -> bool:
        """Checks if the application is running inside a Flatpak."""
        return os.path.exists("/.flatpak-info")

    def validate_dependencies(self, use_gamescope: bool = True) -> None:
        """Validates if all necessary commands are available on the system."""
        self.logger.info("Validating dependencies...")
        required_commands = ["bwrap", "steam"]
        if use_gamescope:
            required_commands.insert(0, "gamescope")

        for cmd_name in required_commands:
            # If in Flatpak, check on the host. Otherwise, check locally.
            if self.is_flatpak:
                check_cmd = ["flatpak-spawn", "--host", "which", cmd_name]
                try:
                    # We check the return code. A non-zero indicates the command is not found.
                    subprocess.run(check_cmd, check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    raise DependencyError(f"Required command '{cmd_name}' not found on the host system")
            else:
                if not shutil.which(cmd_name):
                    raise DependencyError(f"Required command '{cmd_name}' not found")

        self.logger.info("Dependencies validated successfully")

    def _launch_single_instance(self, profile: Profile, instance_num: int) -> None:
        """Launches a single steam instance."""
        self.logger.info(f"Preparing instance {instance_num}...")

        home_path = Config.get_steam_home_path(instance_num)
        home_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Instance {instance_num}: Using isolated home path '{home_path}'")

        self._prepare_home(home_path)
        device_info = self._validate_input_devices(profile, instance_num, instance_num)
        env = self._prepare_environment(profile, device_info, instance_num)

        cmd_builder = CommandBuilder(
            self.logger,
            profile,
            device_info,
            self.device_manager,
            instance_num,
            home_path,
            self._virtual_joystick_path,
        )
        cmd = cmd_builder.build_command()

        # If running in Flatpak, use an inline script to launch on the host
        if self.is_flatpak:
            escaped_cmd = " ".join(shlex.quote(c) for c in cmd)
            inline_script = f"""
                set -m; 
                {escaped_cmd} & 
                PID=$!; 
                PGID=$(ps -o pgid= -p $PID | tr -d ' '); 
                echo $PGID; 
                fg %1;
            """
            cmd = ["flatpak-spawn", "--host", "bash", "-c", inline_script]

        log_file = Config.LOG_DIR / f"steam_instance_{instance_num}.log"
        self.logger.info(f"Launching instance {instance_num} (Log: {log_file})")
        self.logger.info(f"Instance {instance_num}: Full command: {shlex.join(cmd)}")

        try:
            # For Flatpak, we need to capture stdout to get the PGID
            stdout_pipe = subprocess.PIPE if self.is_flatpak else subprocess.DEVNULL
            
            process = subprocess.Popen(
                cmd,
                stdout=stdout_pipe,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=Path.home(),
                preexec_fn=os.setpgrp if not self.is_flatpak else None,
            )

            if self.is_flatpak:
                # Read the PGID from the host-launcher script
                try:
                    pgid_line = process.stdout.readline().decode().strip()
                    self.pgids[instance_num] = int(pgid_line)
                    self.logger.info(f"Instance {instance_num} started on host with PGID: {self.pgids[instance_num]}")
                except (ValueError, IndexError) as e:
                    self.logger.error(f"Failed to parse PGID for instance {instance_num}: {e}")
                    raise
            else:
                self.pgids[instance_num] = os.getpgid(process.pid)
            
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
                    if not player_config.physical_device_id:
                        needs_virtual_joystick = True
                        break

            if needs_virtual_joystick:
                self.logger.info("One or more instances lack a physical joystick. Creating a virtual one.")
                try:
                    self._virtual_joystick_path = self.virtual_device.create_virtual_joystick()
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
        """Terminates a single Steam instance gracefully."""
        if instance_num not in self.processes:
            self.logger.warning(f"Attempted to terminate non-existent instance {instance_num}")
            return

        process = self.processes[instance_num]
        self.logger.info(f"Terminating instance {process.pid}...")
        
        if process.poll() is None:
            pgid = self.pgids.get(instance_num)
            if pgid:
                if self.is_flatpak:
                    self.logger.info(f"Sending SIGTERM to host process group {pgid} for instance {instance_num}")
                    subprocess.run(["flatpak-spawn", "--host", "kill", "-s", "SIGTERM", f"-{pgid}"])
                else:
                    try:
                        self.logger.info(f"Sending SIGTERM to process group {pgid} for instance {instance_num}")
                        os.killpg(pgid, signal.SIGTERM)
                    except ProcessLookupError:
                        self.logger.info(f"Process group for PID {process.pid} not found for instance {instance_num}.")

            try:
                process.wait(timeout=10)
                self.logger.info(f"Instance {instance_num} terminated gracefully.")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Instance {instance_num} did not terminate after 10s. Sending SIGKILL.")
                if pgid:
                    if self.is_flatpak:
                        subprocess.run(["flatpak-spawn", "--host", "kill", "-s", "SIGKILL", f"-{pgid}"])
                    else:
                        try:
                            os.killpg(pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            self.logger.info(f"Process group for PID {process.pid} not found when sending SIGKILL.")

        if process.poll() is None:
            process.wait()

        if instance_num in self.processes:
            del self.processes[instance_num]
        if instance_num in self.pids:
            del self.pids[instance_num]
        if instance_num in self.pgids:
            del self.pgids[instance_num]


    def _prepare_home(self, home_path: Path) -> None:
        """
        Prepares the isolated Steam directories for the instance.
        This involves creating the directory structure and copying app manifests
        to ensure games are recognized.
        """
        self.logger.info(f"Preparing isolated Steam directories for instance at {home_path}...")

        sdbx_steam_local = home_path / ".local/share/Steam"

        # Create essential Steam directories within the instance's isolated path
        (sdbx_steam_local / "steamapps").mkdir(parents=True, exist_ok=True)
        (sdbx_steam_local / "compatibilitytools.d").mkdir(parents=True, exist_ok=True)

        # Copy .acf (app manifest) files from the host to the instance.
        # This makes Steam recognize games as "installed" so it can find them
        # in the shared steamapps/common directory.
        host_steamapps = Path.home() / ".local/share/Steam/steamapps"
        dest_steamapps = sdbx_steam_local / "steamapps"

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
        # env["LD_PRELOAD"] = ""
        # Handle audio device assignment
        if device_info.get("audio_device_id_for_instance"):
            env["PULSE_SINK"] = device_info["audio_device_id_for_instance"]
            self.logger.info(f"Instance {instance_num}: Setting PULSE_SINK to '{device_info['audio_device_id_for_instance']}'.")

        # Custom ENV variables are set via bwrap --setenv to target Steam directly.

        self.logger.info(f"Instance {instance_num}: Final environment prepared.")
        return env

    def _validate_input_devices(self, profile: Profile, instance_num: int, instance_num_display: int) -> dict:
        """Validates input devices and returns information about them."""
        # Get specific player config
        player_config = (
            profile.player_configs[instance_num]
            if profile.player_configs and 0 <= instance_num < len(profile.player_configs)
            else PlayerInstanceConfig() # Default empty config
        )

        def _validate_device(path_str: Optional[str], device_type: str) -> Optional[str]:
            if not path_str or not path_str.strip():
                return None
            path_obj = Path(path_str)
            if path_obj.exists() and path_obj.is_char_device():
                 self.logger.info(f"Instance {instance_num_display}: {device_type} device '{path_str}' assigned.")
                 return str(path_obj.resolve())
            self.logger.warning(
                f"Instance {instance_num_display}: {device_type} device '{path_str}' not found or not a char device."
            )
            return None

        mouse_path = None
        keyboard_path = None
        joystick_path = _validate_device(player_config.physical_device_id, "Joystick")

        audio_id = player_config.audio_device_id
        if audio_id and audio_id.strip():
            self.logger.info(f"Instance {instance_num_display}: Audio device ID '{audio_id}' assigned.")

        return {
            "mouse_path_str_for_instance": mouse_path,
            "keyboard_path_str_for_instance": keyboard_path,
            "joystick_path_str_for_instance": joystick_path,
            "audio_device_id_for_instance": audio_id if audio_id and audio_id.strip() else None,
            "should_add_grab_flags": player_config.grab_input_devices,
        }

    def terminate_all(self) -> None:
        """Terminates all managed steam instances."""
        if self.termination_in_progress:
            return
        try:
            self.termination_in_progress = True
            self.logger.info("Starting termination of all instances...")

            # Cleanup virtual joystick
            if self._virtual_joystick_path:
                self.virtual_device.destroy_virtual_joystick()
                self._virtual_joystick_path = None
                self.logger.info("Virtual joystick destroyed.")
            self._virtual_joystick_checked = False

            # Cleanup KDE-specific settings
            if self.kde_manager:
                self.kde_manager.stop_kwin_script()
                self.kde_manager.restore_panel_states()
                self.logger.info("KDE-specific cleanup complete.")

            for instance_num in list(self.processes.keys()):
                self.terminate_instance(instance_num)

            self.logger.info("Instance termination complete.")
            self.pids.clear()
            self.processes.clear()

        finally:
            self.termination_in_progress = False
