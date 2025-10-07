import os
import time
import shutil
from pathlib import Path
import psutil
from typing import List, Optional, Dict
from ..core.config import Config
from ..core.exceptions import DependencyError
from ..core.logger import Logger
from ..models.profile import GameProfile, PlayerInstanceConfig
from ..models.instance import GameInstance
from .proton import ProtonService
from .process import ProcessService
from .dependency_manager import DependencyManager

class InstanceService:
    """Service responsible for managing game instances, including dependency validation, creation, launching, and monitoring."""
    def __init__(self, logger: Logger):
        """Initializes the instance service with logger, ProtonService, and ProcessService."""
        self.logger = logger
        self.proton_service = ProtonService(logger)
        self.process_service = ProcessService(logger)
        self._dependency_cache: Dict[str, bool] = {}
        self._env_cache: Dict[str, dict] = {}
        self.cpu_count = psutil.cpu_count(logical=True) # Get the number of logical CPU cores (includes threads)

    def validate_dependencies(self) -> None:
        """Validates if all necessary commands are available on the system."""
        if self._dependency_cache:
            self.logger.info("Dependencies already validated (cached)")
            return

        self.logger.info("Validating dependencies...")
        for cmd in Config.REQUIRED_COMMANDS:
            if cmd not in self._dependency_cache:
                self._dependency_cache[cmd] = shutil.which(cmd) is not None
            if not self._dependency_cache[cmd]:
                raise DependencyError(f"Required command '{cmd}' not found")
        self.logger.info("Dependencies validated successfully")

    def launch_instances(self, profile: GameProfile, profile_name: str) -> None:
            """Launches all game instances according to the provided profile."""
            if not profile.exe_path:
                self.logger.error(f"Executable path is not configured for profile '{profile_name}'. Cannot launch.")
                return

            # Validate gamescope if needed
            if profile.use_gamescope:
                if not shutil.which('gamescope'):
                    raise DependencyError("Gamescope is enabled for this profile but 'gamescope' command not found. Please install gamescope or disable it in the profile settings.")
                self.logger.info("Gamescope is enabled and available for this profile.")
            
            # Validate bwrap if needed
            if not profile.disable_bwrap:
                if not shutil.which('bwrap'):
                    raise DependencyError("bwrap is required but not found. Please install bubblewrap or enable 'Disable bwrap' in the profile settings (not recommended).")
                self.logger.info("bwrap is enabled and available for this profile.")
            else:
                self.logger.warning("⚠️  bwrap is disabled for this profile. Input device isolation will NOT work!")

            # Cache proton lookup
            proton_cache_key = f"{profile.is_native}_{profile.proton_version}"
            if proton_cache_key not in self._env_cache:
                if profile.is_native:
                    proton_path = None
                    steam_root = None
                else:
                    proton_path, steam_root = self.proton_service.find_proton_path(profile.proton_version or "Experimental")
                self._env_cache[proton_cache_key] = {'proton_path': proton_path, 'steam_root': steam_root}
            else:
                cached_data = self._env_cache[proton_cache_key]
                proton_path = cached_data['proton_path']
                steam_root = cached_data['steam_root']

            self.process_service.cleanup_previous_instances(proton_path, profile.exe_path)

            # Create directories in batch
            directories = [
                Config.LOG_DIR,
                Config.PREFIX_BASE_DIR
            ]
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            instances = self._create_instances(profile, profile_name, proton_path, steam_root)

            # Calculate CPU core assignments for each instance
            num_instances = len(instances)
            if num_instances == 0:
                self.logger.info("No instances to launch.")
                return

            cores_per_instance = self.cpu_count // num_instances
            remaining_cores = self.cpu_count % num_instances
            core_assignments = []
            current_core_start = 0

            for i in range(num_instances):
                num_cores_for_instance = cores_per_instance
                if remaining_cores > 0:
                    num_cores_for_instance += 1
                    remaining_cores -= 1

                # Build the core string, e.g., "0-3" or "4,5,6"
                cores_list = []
                for j in range(num_cores_for_instance):
                    cores_list.append(str(current_core_start + j))
                core_assignments.append(",".join(cores_list))
                current_core_start += num_cores_for_instance

            self.logger.info(f"Launching {profile.effective_num_players()} instance(s) of '{profile.game_name}'...")

            original_game_path = profile.exe_path.parent

            for i, instance in enumerate(instances):
                cpu_affinity = core_assignments[i]
                self._launch_single_instance(instance, profile, proton_path, steam_root, original_game_path, cpu_affinity)
                time.sleep(5)

            self.logger.info(f"All {profile.effective_num_players} instances launched")
            self.logger.info(f"PIDs: {self.process_service.pids}")
            self.logger.info("Press CTRL+C to terminate all instances")

    def _create_instances(self, profile: GameProfile, profile_name: str, proton_path: Optional[Path], steam_root: Optional[Path]) -> List[GameInstance]:
        """Creates instance models for each player."""
        instances = []

        if not profile.is_native and proton_path and steam_root:
            dependency_manager = DependencyManager(self.logger, proton_path, steam_root)
        else:
            dependency_manager = None

        # Iterates over the complete list of player configurations with its index
        for i, player_config in enumerate(profile.player_configs):
            instance_num = i + 1

            # Checks if this instance is in the list of selected players to launch.
            # If the selection list is empty or None, all players are launched.
            if profile.selected_players and instance_num not in profile.selected_players:
                self.logger.info(f"Skipping instance {instance_num} as it's not selected by the user.")
                continue  # Skip to the next player if not selected

            # Organizes prefixes by game and by instance.
            # Uses the sanitized `profile.game_name` to ensure paths are clean.
            prefix_dir = Config.get_prefix_base_dir(profile.game_name) / f"instance_{instance_num}"
            log_file = Config.LOG_DIR / f"{profile.game_name}_instance_{instance_num}.log"
            prefix_dir.mkdir(parents=True, exist_ok=True)
            (prefix_dir / "pfx").mkdir(exist_ok=True)

            if dependency_manager:
                # Initialize the prefix first. This is a crucial, one-time setup.
                dependency_manager.initialize_prefix(prefix_dir)

                # Now, apply dependencies if configured
                if profile.apply_dxvk_vkd3d:
                    dependency_manager.apply_dxvk_vkd3d(prefix_dir)
                if profile.winetricks_verbs:
                    dependency_manager.apply_winetricks(prefix_dir, profile.winetricks_verbs)

            instance = GameInstance(
                instance_num=instance_num,
                profile_name=profile.game_name,  # Use sanitized name
                prefix_dir=prefix_dir,
                log_file=log_file,
                player_config=player_config
            )
            instances.append(instance)
        return instances

    def _create_game_directory_symlink_structure(self, instance: GameInstance, original_game_path: Path, original_exe_path: Path, profile: GameProfile) -> Path:
        """Creates a mirrored directory structure with symlinks for the original game folder.
        Returns the path to the main executable's symlink.
        """
        instance_game_root = instance.prefix_dir / "game_files"
        instance_game_root.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Instance {instance.instance_num}: Creating symlink structure for {original_game_path} at {instance_game_root}")

        # Determines the relative path of the original executable in relation to the game's root folder.
        try:
            relative_exe_path = original_exe_path.relative_to(original_game_path)
        except ValueError as e:
            # This can happen if original_exe_path is not inside original_game_path
            self.logger.error(f"Instance {instance.instance_num}: Executable path {original_exe_path} is not inside game path {original_game_path}. Error: {e}")
            raise

        # Expected path for the executable symlink
        symlinked_exe_path_target = instance_game_root / relative_exe_path

        self._process_game_files(instance, original_game_path, instance_game_root, profile)
        self._verify_executable_symlink(instance, symlinked_exe_path_target, original_exe_path)

        return symlinked_exe_path_target

    def _process_game_files(self, instance: GameInstance, original_game_path: Path, instance_game_root: Path, profile: GameProfile) -> None:
        """Processes all game files, creating symlinks and configuring the Goldberg Emulator."""
        self.logger.info(f"Instance {instance.instance_num}: Processing game files")

        # Create directory structure
        instance_game_root.mkdir(parents=True, exist_ok=True)

        # Create symlinks for game files
        for item in original_game_path.rglob("*"):
            relative_item_path = item.relative_to(original_game_path)
            target_path_for_item = instance_game_root / relative_item_path

            # Ensures the parent directory exists
            target_path_for_item.parent.mkdir(parents=True, exist_ok=True)

            if item.is_dir():
                target_path_for_item.mkdir(parents=True, exist_ok=True)
            else:
                if not target_path_for_item.exists():
                    try:
                        target_path_for_item.symlink_to(item)
                        self.logger.info(f"Instance {instance.instance_num}: Created symlink: {target_path_for_item} -> {item}")
                    except FileExistsError:
                        self.logger.info(f"Instance {instance.instance_num}: File already exists: {target_path_for_item}")
                    except Exception as e:
                        self.logger.warning(f"Instance {instance.instance_num}: Failed to create symlink for {item}: {e}")

    def _verify_executable_symlink(self, instance: GameInstance, symlinked_exe_path_target: Path, original_exe_path: Path) -> None:
        """Verifies if the symlink for the executable was created correctly."""
        if not symlinked_exe_path_target.exists() or not symlinked_exe_path_target.is_symlink():
            self.logger.error(f"Instance {instance.instance_num}: Expected symlinked executable at {symlinked_exe_path_target} was not found or is not a symlink.")
            # Additionally, check if the symlink target is the original executable
            if symlinked_exe_path_target.is_symlink() and Path(os.readlink(str(symlinked_exe_path_target))) != original_exe_path:
                 self.logger.error(f"Instance {instance.instance_num}: Symlink {symlinked_exe_path_target} points to {os.readlink(str(symlinked_exe_path_target))}, not {original_exe_path}")
            raise FileNotFoundError(f"Failed to create or verify symlink for executable {original_exe_path} at {symlinked_exe_path_target}")

        self.logger.info(f"Instance {instance.instance_num}: Executable symlink verified: {symlinked_exe_path_target}")

    def _launch_single_instance(self, instance: GameInstance, profile: GameProfile,
                              proton_path: Optional[Path], steam_root: Optional[Path], original_game_path: Path, cpu_affinity: str) -> None:
        """Launches a single game instance with CPU affinity."""
        self.logger.info(f"Preparing instance {instance.instance_num} with CPU affinity: {cpu_affinity}...")

        if not profile.exe_path:
            self.logger.error(f"Instance {instance.instance_num}: Executable path is missing in profile, cannot launch.")
            return

        symlinked_executable_path = self._create_game_directory_symlink_structure(
            instance,
            original_game_path,
            profile.exe_path,
            profile # Passing the complete profile object
        )

        # Validate devices for this instance
        instance_idx = instance.instance_num - 1
        device_info = self._validate_input_devices(profile, instance_idx, instance.instance_num)

        env = self._prepare_environment(instance, steam_root, profile, device_info, cpu_affinity)
        cmd = self._build_command(profile, proton_path, instance, symlinked_executable_path, cpu_affinity)

        self.logger.info(f"Launching instance {instance.instance_num} (Log: {instance.log_file})")
        pid = self.process_service.launch_instance(cmd, instance.log_file, env, cwd=symlinked_executable_path.parent)
        instance.pid = pid
        self.logger.info(f"Instance {instance.instance_num} started with PID: {pid}")

    def _prepare_environment(self, instance: GameInstance, steam_root: Optional[Path], profile: Optional[GameProfile] = None, device_info: dict = {}, cpu_affinity: str = "") -> dict:
        """Prepares environment variables for the game instance, including control isolation, XKB configuration, and CPU affinity for Wine."""
        # Use cache for base environment
        base_env_key = f"base_{profile.is_native if profile else False}_{steam_root}_{profile.app_id if profile else None}"
        if base_env_key not in self._env_cache:
            env = os.environ.copy()
            env['PATH'] = os.environ['PATH']

            # Clean up potentially conflicting Python variables
            env.pop('PYTHONHOME', None)
            env.pop('PYTHONPATH', None)

            if not (profile.is_native if profile else False):
                if steam_root:
                    env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = str(steam_root)
                env['DXVK_ASYNC'] = '1'
                env['DXVK_LOG_LEVEL'] = 'info'

                if profile and profile.app_id:
                    env['SteamAppId'] = profile.app_id
                    env['SteamGameId'] = profile.app_id

            # XKB configuration for keyboard layout (cache values)
            xkb_vars = ['XKB_DEFAULT_LAYOUT', 'XKB_DEFAULT_VARIANT', 'XKB_DEFAULT_RULES', 'XKB_DEFAULT_MODEL', 'XKB_DEFAULT_OPTIONS']
            for var in xkb_vars:
                if var in os.environ:
                    env[var] = os.environ[var]

            self._env_cache[base_env_key] = env
        else:
            env = self._env_cache[base_env_key].copy()

        # Instance-specific environment variables
        if not (profile.is_native if profile else False):
            env['STEAM_COMPAT_DATA_PATH'] = str(instance.prefix_dir)
            env['WINEPREFIX'] = str(instance.prefix_dir / 'pfx')
            # Add WINE_CPU_TOPOLOGY for CPU affinity
            env['WINE_CPU_TOPOLOGY'] = f"{self.cpu_count}:{cpu_affinity}"
            self.logger.info(f"Instance {instance.instance_num}: Setting WINE_CPU_TOPOLOGY to '{env['WINE_CPU_TOPOLOGY']}'.")

        # Add environment variables defined in the profile
        if profile and profile.env_vars:
            for key, value in profile.env_vars.items():
                env[key] = value

        # Handle joystick assignment
        assigned_joystick_path = self._get_joystick_for_instance(instance, profile)
        if assigned_joystick_path:
            env['SDL_JOYSTICK_DEVICE'] = assigned_joystick_path
        else:
            env.pop('SDL_JOYSTICK_DEVICE', None)

        # Handle audio device assignment (PULSE_SINK for PulseAudio)
        if device_info and device_info.get('audio_device_id_for_instance'):
            audio_device_id = device_info['audio_device_id_for_instance']
            env['PULSE_SINK'] = audio_device_id
            self.logger.info(f"Instance {instance.instance_num}: Setting PULSE_SINK to '{audio_device_id}'.")
        else:
            env.pop('PULSE_SINK', None)
            self.logger.info(f"Instance {instance.instance_num}: No specific audio device assigned. PULSE_SINK not set.")

        # Define WAYLANDDRV_PRIMARY_MONITOR com base na configuração do jogador
        if instance.player_config and instance.player_config.monitor_id:
            env['WAYLANDDRV_PRIMARY_MONITOR'] = instance.player_config.monitor_id
            self.logger.info(f"Instance {instance.instance_num}: Setting WAYLANDDRV_PRIMARY_MONITOR to '{instance.player_config.monitor_id}'.")
        else:
            env.pop('WAYLANDDRV_PRIMARY_MONITOR', None)
            self.logger.info(f"Instance {instance.instance_num}: No specific monitor selected for this instance.")

        return env

    def _get_joystick_for_instance(self, instance: GameInstance, profile: Optional[GameProfile]) -> Optional[str]:
        """Get joystick path for instance."""
        if not profile or not profile.player_configs or not (0 <= instance.instance_num - 1 < len(profile.player_configs)):
            return None

        idx = instance.instance_num - 1
        player_config = profile.player_configs[idx]
        device_from_profile = player_config.PHYSICAL_DEVICE_ID

        if not device_from_profile or not device_from_profile.strip():
            return None

        if Path(device_from_profile).exists():
            return device_from_profile
        return None

    def _build_command(self, profile: GameProfile, proton_path: Optional[Path], instance: GameInstance, symlinked_exe_path: Path, cpu_affinity: str) -> List[str]:
        """Builds the command to run gamescope and the game (native or via Proton), using bwrap to isolate the control."""
        instance_idx = instance.instance_num - 1

        # Validate input devices
        device_info = self._validate_input_devices(profile, instance_idx, instance.instance_num)

        # Build Gamescope command only if enabled
        if profile.use_gamescope:
            gamescope_cmd = self._build_gamescope_command(profile, device_info['should_add_grab_flags'], instance.instance_num)
        else:
            gamescope_cmd = []
            self.logger.info(f"Instance {instance.instance_num}: Gamescope is disabled for this profile.")

        # Build base game command
        base_cmd = self._build_base_game_command(profile, proton_path, symlinked_exe_path, gamescope_cmd, instance.instance_num)

        # Build bwrap command with devices (only if not disabled)
        if profile.disable_bwrap:
            bwrap_cmd = []
            self.logger.info(f"Instance {instance.instance_num}: bwrap is disabled for this profile.")
        else:
            bwrap_cmd = self._build_bwrap_command(profile, instance_idx, device_info, instance.instance_num)

        # Add taskset at the beginning of the final command to ensure affinity for the entire process
        taskset_cmd = ["taskset", "-c", cpu_affinity]
        final_cmd = taskset_cmd + bwrap_cmd + base_cmd
        final_bwrap_cmd_str = ' '.join(final_cmd)
        self.logger.info(f"Instance {instance.instance_num}: Full command: {final_bwrap_cmd_str}")

        return final_cmd

    def _validate_input_devices(self, profile: GameProfile, instance_idx: int, instance_num: int) -> dict:
        """Validates input devices and returns information about them."""
        has_dedicated_mouse = False
        mouse_path_str_for_instance = None

        # Get specific player config
        player_config = profile.player_configs[instance_idx] if profile.player_configs and 0 <= instance_idx < len(profile.player_configs) else None

        if player_config:
            mouse_path_str_for_instance = player_config.MOUSE_EVENT_PATH
            if mouse_path_str_for_instance and mouse_path_str_for_instance.strip():
                mouse_path_obj = Path(mouse_path_str_for_instance)
                if mouse_path_obj.exists() and mouse_path_obj.is_char_device():
                    has_dedicated_mouse = True
                else:
                    self.logger.warning(f"Instance {instance_num}: Mouse device '{mouse_path_str_for_instance}' specified in profile but not found or not a char device.")

        has_dedicated_keyboard = False
        keyboard_path_str_for_instance = None
        if player_config:
            keyboard_path_str_for_instance = player_config.KEYBOARD_EVENT_PATH
            if keyboard_path_str_for_instance and keyboard_path_str_for_instance.strip():
                keyboard_path_obj = Path(keyboard_path_str_for_instance)
                if keyboard_path_obj.exists() and keyboard_path_obj.is_char_device():
                    has_dedicated_keyboard = True
                else:
                    self.logger.warning(f"Instance {instance_num}: Keyboard device '{keyboard_path_str_for_instance}' specified in profile but not found or not a char device.")

        audio_device_id_for_instance = None
        if player_config:
            audio_device_id = player_config.AUDIO_DEVICE_ID
            if audio_device_id and audio_device_id.strip():
                audio_device_id_for_instance = audio_device_id
                self.logger.info(f"Instance {instance_num}: Audio device ID '{audio_device_id}' assigned.")

        return {
            'has_dedicated_mouse': has_dedicated_mouse,
            'mouse_path_str_for_instance': mouse_path_str_for_instance,
            'has_dedicated_keyboard': has_dedicated_keyboard,
            'keyboard_path_str_for_instance': keyboard_path_str_for_instance,
            'audio_device_id_for_instance': audio_device_id_for_instance,
            'should_add_grab_flags': has_dedicated_mouse and has_dedicated_keyboard
        }

    def _build_gamescope_command(self, profile: GameProfile, should_add_grab_flags: bool, instance_num: int) -> List[str]:
        """Builds the Gamescope command."""
        gamescope_path = 'gamescope'

        # Get instance dimensions directly from the profile
        effective_width, effective_height = profile.get_instance_dimensions(instance_num)

        gamescope_cli_options = [
            gamescope_path,
            '-v',
            '-W', str(effective_width),
            '-H', str(effective_height),
            '-w', str(effective_width),
            '-h', str(effective_height),
        ]

        # Always set an unfocused FPS limit to a very high value
        gamescope_cli_options.extend(['-o', '999'])
        self.logger.info(f"Instance {instance_num}: Setting unfocused FPS limit to 999.")

        # Always set a focused FPS limit to a very high value
        gamescope_cli_options.extend(['-r', '999'])
        self.logger.info(f"Instance {instance_num}: Setting focused FPS limit to 999.")

        # Specific configurations for splitscreen vs normal
        if profile.is_splitscreen_mode:
            gamescope_cli_options.append('-b')  # borderless instead of fullscreen
        else:
            gamescope_cli_options.extend(['-f', '--adaptive-sync'])

        if should_add_grab_flags:
            self.logger.info(f"Instance {instance_num}: Using dedicated mouse and keyboard. Adding --grab and --force-grab-cursor to Gamescope.")
            gamescope_cli_options.extend(['--grab', '--force-grab-cursor'])

        return gamescope_cli_options

    def _build_base_game_command(self, profile: GameProfile, proton_path: Optional[Path], symlinked_exe_path: Path, gamescope_cmd: List[str], instance_num: int) -> List[str]:
        """Builds the base game command."""
        # Add game arguments defined in the profile, if any
        game_specific_args = []
        if profile.game_args:
            game_specific_args = profile.game_args.split()
            self.logger.info(f"Instance {instance_num}: Adding game arguments: {game_specific_args}")

        # Only add gamescope prefix and separator if gamescope is enabled
        if gamescope_cmd:
            base_cmd_prefix = gamescope_cmd + ['--']  # Separator for the command to be executed
        else:
            base_cmd_prefix = []

        if profile.is_native:
            base_cmd = list(base_cmd_prefix)
            if symlinked_exe_path:
                base_cmd.append(str(symlinked_exe_path))
                base_cmd.extend(game_specific_args)
        else:
            base_cmd = list(base_cmd_prefix)
            if proton_path and symlinked_exe_path:
                base_cmd.extend([str(proton_path), 'run', str(symlinked_exe_path)])
                base_cmd.extend(game_specific_args)

        return base_cmd

    def _build_bwrap_command(self, profile: GameProfile, instance_idx: int, device_info: dict, instance_num: int) -> List[str]:
        """Builds the bwrap command with input devices."""
        bwrap_cmd = [
            'bwrap',
            '--dev-bind', '/', '/',
            '--proc', '/proc',
            '--tmpfs', '/tmp',
            '--cap-add', 'all',
        ]

        device_paths_to_bind = self._collect_device_paths(profile, instance_idx, device_info, instance_num)

        if device_paths_to_bind:
            bwrap_cmd.extend(['--tmpfs', '/dev/input'])
            for device_path in device_paths_to_bind:
                bwrap_cmd.extend(['--dev-bind', device_path, device_path])
                self.logger.info(f"Instance {instance_num}: bwrap will bind '{device_path}' to '{device_path}'.")
        else:
            self.logger.info(f"Instance {instance_num}: No specific input devices to bind with bwrap. Creating an empty isolated /dev/input.")
            bwrap_cmd.extend(['--tmpfs', '/dev/input'])

        return bwrap_cmd

    def _collect_device_paths(self, profile: GameProfile, instance_idx: int, device_info: dict, instance_num: int) -> List[str]:
        """Collects all necessary device paths for bwrap."""
        collected_paths = []

        # Joysticks
        # Get specific player config
        player_config = profile.player_configs[instance_idx] if profile.player_configs and 0 <= instance_idx < len(profile.player_configs) else None

        if player_config:
            joystick_path_str = player_config.PHYSICAL_DEVICE_ID
            if joystick_path_str and joystick_path_str.strip():
                joystick_path = Path(joystick_path_str)
                if joystick_path.exists() and joystick_path.is_char_device():
                    collected_paths.append(str(joystick_path))
                    self.logger.info(f"Instance {instance_num}: Queued joystick '{joystick_path}' for bwrap binding.")
                else:
                    self.logger.warning(f"Instance {instance_num}: Joystick device '{joystick_path_str}' specified in profile but not found or not a char device. Not binding.")

        # Mice - uses already validated variables
        if device_info['has_dedicated_mouse']:
            collected_paths.append(device_info['mouse_path_str_for_instance'])
            self.logger.info(f"Instance {instance_num}: Queued mouse device '{device_info['mouse_path_str_for_instance']}' for bwrap binding.")

        # Keyboards - uses already validated variables
        if device_info['has_dedicated_keyboard']:
            collected_paths.append(device_info['keyboard_path_str_for_instance'])
            self.logger.info(f"Instance {instance_num}: Queued keyboard device '{device_info['keyboard_path_str_for_instance']}' for bwrap binding.")

        return collected_paths

    def monitor_and_wait(self) -> None:
        """Monitors instances until all are terminated."""
        while self.process_service.monitor_processes():
            time.sleep(5)

        self.logger.info("All instances have terminated")

    def terminate_all(self) -> None:
        """Terminates all game instances managed by the service."""
        self.process_service.terminate_all()
