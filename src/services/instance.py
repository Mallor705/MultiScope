import os
import time
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from ..core.config import Config
from ..core.exceptions import DependencyError
from ..core.logger import Logger
from ..models.profile import GameProfile
from ..models.instance import GameInstance
from .proton import ProtonService
from .process import ProcessService

class InstanceService:
    """Serviço responsável por gerenciar instâncias do jogo, incluindo validação de dependências, criação, lançamento e monitoramento."""
    def __init__(self, logger: Logger):
        """Inicializa o serviço de instâncias com logger, ProtonService e ProcessService."""
        self.logger = logger
        self.proton_service = ProtonService(logger)
        self.process_service = ProcessService(logger)
        self._dependency_cache: Dict[str, bool] = {}
        self._env_cache: Dict[str, dict] = {}

    def validate_dependencies(self) -> None:
        """Valida se todos os comandos necessários estão disponíveis no sistema."""
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
        """Lança todas as instâncias do jogo conforme o perfil fornecido."""
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
            Path.home() / '.config/protonfixes',
            Config.PREFIX_BASE_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        instances = self._create_instances(profile, profile_name)

        self.logger.info(f"Launching {profile.num_players} instance(s) of '{profile.game_name}'...")

        original_game_path = profile.exe_path.parent

        for instance in instances:
            self._launch_single_instance(instance, profile, proton_path, steam_root, original_game_path)
            time.sleep(5)

        self.logger.info(f"All {profile.num_players} instances launched")
        self.logger.info(f"PIDs: {self.process_service.pids}")
        self.logger.info("Press CTRL+C to terminate all instances")

    def _create_instances(self, profile: GameProfile, profile_name: str) -> List[GameInstance]:
        """Cria os modelos de instância para cada jogador."""
        instances = []
        for i in range(1, profile.num_players + 1):
            # Organiza os prefixos por jogo e por instância
            prefix_dir = Config.get_prefix_base_dir(profile.game_name) / f"instance_{i}"
            log_file = Config.LOG_DIR / f"{profile_name}_instance_{i}.log"
            prefix_dir.mkdir(parents=True, exist_ok=True)
            (prefix_dir / "pfx").mkdir(exist_ok=True)
            instance = GameInstance(
                instance_num=i,
                profile_name=profile_name,
                prefix_dir=prefix_dir,
                log_file=log_file
            )
            instances.append(instance)
        return instances

    def _create_game_directory_symlink_structure(self, instance: GameInstance, original_game_path: Path, original_exe_path: Path, profile: GameProfile) -> Path:
        """Cria uma estrutura de diretórios espelhada com symlinks para a pasta original do jogo.
        Retorna o caminho para o link simbólico do executável principal.
        """
        instance_game_root = instance.prefix_dir / "game_files"
        instance_game_root.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Instance {instance.instance_num}: Creating symlink structure for {original_game_path} at {instance_game_root}")

        # Determina o caminho relativo do executável original em relação à pasta raiz do jogo.
        try:
            relative_exe_path = original_exe_path.relative_to(original_game_path)
        except ValueError as e:
            # Isso pode acontecer se original_exe_path não estiver dentro de original_game_path
            self.logger.error(f"Instance {instance.instance_num}: Executable path {original_exe_path} is not inside game path {original_game_path}. Error: {e}")
            raise

        # Caminho esperado para o link simbólico do executável
        symlinked_exe_path_target = instance_game_root / relative_exe_path

        self._process_game_files(instance, original_game_path, instance_game_root, profile)
        self._verify_executable_symlink(instance, symlinked_exe_path_target, original_exe_path)

        return symlinked_exe_path_target

    def _process_game_files(self, instance: GameInstance, original_game_path: Path, instance_game_root: Path, profile: GameProfile) -> None:
        """Processa todos os arquivos do jogo, criando symlinks e configurando o Goldberg Emulator."""
        self.logger.info(f"Instance {instance.instance_num}: Processing game files and setting up Goldberg Emulator")

        # 1. Identificar arquivos do Steam no diretório do jogo
        steam_api_files = self._identify_steam_api_files(original_game_path)
        self.logger.info(f"Instance {instance.instance_num}: Found Steam API files: {steam_api_files}")

        # 2. Criar estrutura de diretórios
        instance_game_root.mkdir(parents=True, exist_ok=True)

        # 3. Criar symlinks para os arquivos do jogo
        for item in original_game_path.rglob("*"):
            relative_item_path = item.relative_to(original_game_path)
            target_path_for_item = instance_game_root / relative_item_path

            # Garante que o diretório pai exista
            target_path_for_item.parent.mkdir(parents=True, exist_ok=True)

            if item.is_dir():
                target_path_for_item.mkdir(parents=True, exist_ok=True)
            else:
                # Não criar symlink se o arquivo já existir (caso do Goldberg)
                if not target_path_for_item.exists():
                    try:
                        target_path_for_item.symlink_to(item)
                        self.logger.info(f"Instance {instance.instance_num}: Created symlink: {target_path_for_item} -> {item}")
                    except FileExistsError:
                        self.logger.info(f"Instance {instance.instance_num}: File already exists: {target_path_for_item}")
                    except Exception as e:
                        self.logger.warning(f"Instance {instance.instance_num}: Failed to create symlink for {item}: {e}")

        # 4. Copiar arquivos do Goldberg para o mesmo local dos originais
        self._copy_goldberg_files(instance_game_root, steam_api_files, profile, instance)

    def _copy_goldberg_files(self, instance_game_root: Path, steam_api_files: dict, profile: GameProfile, instance: GameInstance) -> None:
        """Copia os arquivos do Goldberg Emulator para a pasta da instância."""
        if not profile.use_goldberg_emulator:
            self.logger.info(f"Instance {instance.instance_num}: Goldberg Emulator is disabled in profile. Skipping file copy.")
            return

        goldberg_source_dir = Path(__file__).parent.parent / "utils" / "goldberg_emulator"
        
        if not goldberg_source_dir.exists():
            self.logger.error(f"Goldberg source directory not found: {goldberg_source_dir}")
            return

        # Mapear arquivos do Goldberg para os arquivos do Steam
        goldberg_files_map = {
            'win64': {
                'steam_api64.dll': 'steam_api64.dll',
                'steamclient64.dll': 'steamclient64.dll',
                'winmm.dll': 'winmm.dll'
            },
            'win32': {
                'steam_api.dll': 'steam_api.dll',
                'steamclient.dll': 'steamclient.dll',
                'winmm.dll': 'winmm.dll'
            },
            'linux64': {
                'steam_api64.dll': 'libsteam_api64.so',
                'steamclient64.dll': 'libsteamclient64.so',
                'winmm.dll': 'libwinmm.so'
            },
            'linux32': {
                'steam_api.dll': 'libsteam_api.so',
                'steamclient.dll': 'libsteamclient.so',
                'winmm.dll': 'libwinmm.so'
            }
        }

        # Determine which Goldberg files to copy based on whether the game is native or not
        files_to_copy = {}
        if profile.is_native:
            # For native Linux games, copy .so files
            if 'linux64' in goldberg_files_map:
                files_to_copy.update(goldberg_files_map['linux64'])
            if 'linux32' in goldberg_files_map:
                files_to_copy.update(goldberg_files_map['linux32'])
        else:
            # For non-native (Windows) games, copy .dll files
            if 'win64' in goldberg_files_map:
                files_to_copy.update(goldberg_files_map['win64'])
            if 'win32' in goldberg_files_map:
                files_to_copy.update(goldberg_files_map['win32'])

        # Variável para armazenar o diretório onde os arquivos do Steam API estão
        steam_api_instance_dir = None

        # Coletar todos os diretórios únicos onde foram encontrados arquivos do Steam API
        unique_dirs = set()
        for platform_files in steam_api_files.values():
            for relative_path in platform_files:
                unique_dirs.add(relative_path.parent)

        # Copiar arquivos do Goldberg para todos os diretórios encontrados
        for relative_dir in unique_dirs:
            # Construir o caminho na instância usando o caminho relativo do jogo original
            steam_api_dir = instance_game_root / relative_dir
            if not steam_api_instance_dir:
                steam_api_instance_dir = steam_api_dir  # Guardar o primeiro diretório para usar depois
            
            # Copiar os arquivos filtrados do Goldberg para cada diretório
            for goldberg_file, steam_file in files_to_copy.items():
                source_file = goldberg_source_dir / goldberg_file
                if source_file.exists():
                    target_file = steam_api_dir / steam_file
                    # Remover arquivo existente se necessário
                    if target_file.exists():
                        target_file.unlink()
                    shutil.copy2(source_file, target_file)
                    self.logger.info(f"Copied Goldberg file {goldberg_file} to {target_file}")
                else:
                    self.logger.warning(f"Goldberg file not found: {goldberg_file}")

            # Copiar pasta settings para o mesmo diretório dos arquivos do Steam API na instância
            settings_source = goldberg_source_dir / "settings"
            if settings_source.exists():
                settings_target = steam_api_dir / "settings"
                
                # Criar pasta se não existir
                settings_target.mkdir(exist_ok=True)
                
                # Copiar apenas os arquivos do Goldberg, preservando o resto
                for item in settings_source.glob("*"):
                    if item.is_file():
                        target_file = settings_target / item.name
                        if target_file.exists():
                            target_file.unlink()
                        shutil.copy2(item, target_file)
                        self.logger.info(f"Copied Goldberg settings file: {item.name}")
                    elif item.is_dir():
                        target_dir = settings_target / item.name
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.copytree(item, target_dir)
                        self.logger.info(f"Copied Goldberg settings directory: {item.name}")
            else:
                self.logger.warning("settings folder not found in Goldberg source directory")

            # Configurar arquivos do Goldberg para este diretório
            self._setup_settings(steam_api_dir, profile, instance)

    def _setup_settings(self, instance_game_root: Path, profile: GameProfile, instance: GameInstance) -> None:
        """Configura a pasta settings com as configurações específicas da instância."""
        settings_dir = instance_game_root / "settings"
        
        # Garantir que a pasta existe
        settings_dir.mkdir(exist_ok=True)

        # Configurar arquivos do Goldberg
        self._setup_goldberg_config(settings_dir, profile, instance)

    def _setup_goldberg_config(self, settings_dir: Path, profile: GameProfile, instance: GameInstance) -> None:
        """Configura os arquivos de configuração do Goldberg Emulator."""
        # Configurar AppID
        if profile.app_id:
            with open(settings_dir / "steam_appid.txt", "w") as f:
                f.write(f"{profile.app_id}\n")
            self.logger.info(f"Instance {instance.instance_num}: Set Steam AppID to {profile.app_id}")

        # Configurar nome da conta e SteamID se houver configurações específicas da instância
        if profile.player_configs and (instance.instance_num - 1) < len(profile.player_configs):
            instance_config = profile.player_configs[instance.instance_num - 1]
            
            if instance_config.account_name:
                with open(settings_dir / "account_name.txt", "w") as f:
                    f.write(f"{instance_config.account_name}\n")
                self.logger.info(f"Instance {instance.instance_num}: Set account name to {instance_config.account_name}")

            if instance_config.user_steam_id:
                with open(settings_dir / "user_steam_id.txt", "w") as f:
                    f.write(f"{instance_config.user_steam_id}\n")
                self.logger.info(f"Instance {instance.instance_num}: Set SteamID to {instance_config.user_steam_id}")

            if instance_config.language:
                with open(settings_dir / "language.txt", "w") as f:
                    f.write(f"{instance_config.language}\n")
                self.logger.info(f"Instance {instance.instance_num}: Set language to {instance_config.language}")
            
            if instance_config.listen_port:
                with open(settings_dir / "listen_port.txt", "w") as f:
                    f.write(f"{instance_config.listen_port}\n")
                self.logger.info(f"Instance {instance.instance_num}: Set listen port to {instance_config.listen_port}")

    def _identify_steam_api_files(self, game_path: Path) -> dict:
        """Identifica os arquivos do Steam API no diretório do jogo."""
        steam_files = {
            'win64': [],
            'win32': [],
            'linux64': [],
            'linux32': []
        }
        
        # Procurar por arquivos do Steam API em todos os diretórios e subpastas
        for file in game_path.rglob("*"):
            if file.name == "steam_api64.dll":
                steam_files['win64'].append(file.relative_to(game_path))
            elif file.name == "steam_api.dll":
                steam_files['win32'].append(file.relative_to(game_path))
            elif file.name == "libsteam_api64.so":
                steam_files['linux64'].append(file.relative_to(game_path))
            elif file.name == "libsteam_api.so":
                steam_files['linux32'].append(file.relative_to(game_path))
        
        return steam_files

    def _verify_executable_symlink(self, instance: GameInstance, symlinked_exe_path_target: Path, original_exe_path: Path) -> None:
        """Verifica se o link simbólico para o executável foi criado corretamente."""
        if not symlinked_exe_path_target.exists() or not symlinked_exe_path_target.is_symlink():
            self.logger.error(f"Instance {instance.instance_num}: Expected symlinked executable at {symlinked_exe_path_target} was not found or is not a symlink.")
            # Adicionalmente, verificar se o alvo do symlink é o executável original
            if symlinked_exe_path_target.is_symlink() and Path(os.readlink(str(symlinked_exe_path_target))) != original_exe_path:
                 self.logger.error(f"Instance {instance.instance_num}: Symlink {symlinked_exe_path_target} points to {os.readlink(str(symlinked_exe_path_target))}, not {original_exe_path}")
            raise FileNotFoundError(f"Failed to create or verify symlink for executable {original_exe_path} at {symlinked_exe_path_target}")

        self.logger.info(f"Instance {instance.instance_num}: Symlinked executable verified at: {symlinked_exe_path_target}")

    def _launch_single_instance(self, instance: GameInstance, profile: GameProfile,
                              proton_path: Optional[Path], steam_root: Optional[Path], original_game_path: Path) -> None:
        """Lança uma única instância do jogo."""
        self.logger.info(f"Preparing instance {instance.instance_num}...")

        symlinked_executable_path = self._create_game_directory_symlink_structure(
            instance,
            original_game_path,
            profile.exe_path,
            profile # Passando o objeto profile completo
        )

        env = self._prepare_environment(instance, steam_root, profile)
        cmd = self._build_command(profile, proton_path, instance, symlinked_executable_path)
        self.logger.info(f"Launching instance {instance.instance_num} (Log: {instance.log_file})")
        pid = self.process_service.launch_instance(cmd, instance.log_file, env, cwd=symlinked_executable_path.parent)
        instance.pid = pid
        self.logger.info(f"Instance {instance.instance_num} started with PID: {pid}")

    def _prepare_environment(self, instance: GameInstance, steam_root: Optional[Path], profile: Optional[GameProfile] = None) -> dict:
        """Prepara as variáveis de ambiente para a instância do jogo, incluindo isolamento de controles e configuração XKB."""
        # Use cache for base environment
        base_env_key = f"base_{profile.is_native if profile else False}_{steam_root}_{profile.app_id if profile else None}"
        if base_env_key not in self._env_cache:
            env = os.environ.copy()
            env['PATH'] = os.environ['PATH']

            # Limpar variáveis Python potencialmente conflitantes
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

            # Configuração XKB para layout de teclado (cache os valores)
            xkb_vars = ['XKB_DEFAULT_LAYOUT', 'XKB_DEFAULT_VARIANT', 'XKB_DEFAULT_RULES', 'XKB_DEFAULT_MODEL', 'XKB_DEFAULT_OPTIONS']
            for var in xkb_vars:
                if var in os.environ:
                    env[var] = os.environ[var]

            self._env_cache[base_env_key] = env
        else:
            env = self._env_cache[base_env_key].copy()

        # Variáveis de ambiente específicas da instância
        if not (profile.is_native if profile else False):
            env['STEAM_COMPAT_DATA_PATH'] = str(instance.prefix_dir)
            env['WINEPREFIX'] = str(instance.prefix_dir / 'pfx')    
            env['WINEDLLOVERRIDES'] = "OnlineFix64=n,b;steam_api64=n,b;winmm=n,b"

        # Adicionar variáveis de ambiente definidas no perfil
        if profile and profile.env_vars:
            for key, value in profile.env_vars.items():
                env[key] = value

        # Handle joystick assignment
        assigned_joystick_path = self._get_joystick_for_instance(instance, profile)
        if assigned_joystick_path:
            env['SDL_JOYSTICK_DEVICE'] = assigned_joystick_path
        else:
            env.pop('SDL_JOYSTICK_DEVICE', None)

        return env

    def _get_joystick_for_instance(self, instance: GameInstance, profile: Optional[GameProfile]) -> Optional[str]:
        """Get joystick path for instance."""
        if not profile or not profile.player_physical_device_ids:
            return None

        idx = instance.instance_num - 1
        if not (0 <= idx < len(profile.player_physical_device_ids)):
            return None

        device_from_profile = profile.player_physical_device_ids[idx]
        if not device_from_profile or not device_from_profile.strip():
            return None

        if Path(device_from_profile).exists():
            return device_from_profile
        return None

    def _build_command(self, profile: GameProfile, proton_path: Optional[Path], instance: GameInstance, symlinked_exe_path: Path) -> List[str]:
        """Monta o comando para executar o gamescope e o jogo (nativo ou via Proton), usando bwrap para isolar o controle."""
        instance_idx = instance.instance_num - 1

        # Validar dispositivos de entrada
        device_info = self._validate_input_devices(profile, instance_idx, instance.instance_num)

        # Construir comando do Gamescope
        gamescope_cmd = self._build_gamescope_command(profile, device_info['should_add_grab_flags'], instance.instance_num)

        # Construir comando base do jogo
        base_cmd = self._build_base_game_command(profile, proton_path, symlinked_exe_path, gamescope_cmd, instance.instance_num)

        # Construir comando bwrap com dispositivos
        bwrap_cmd = self._build_bwrap_command(profile, instance_idx, device_info, instance.instance_num)

        final_cmd = bwrap_cmd + base_cmd
        final_bwrap_cmd_str = ' '.join(final_cmd)
        self.logger.info(f"Instance {instance.instance_num}: Full bwrap command: {final_bwrap_cmd_str}")

        return final_cmd

    def _validate_input_devices(self, profile: GameProfile, instance_idx: int, instance_num: int) -> dict:
        """Valida dispositivos de entrada e retorna informações sobre eles."""
        # Determinar se esta instância terá mouse e teclado dedicados e válidos
        has_dedicated_mouse = False
        mouse_path_str_for_instance = None
        if profile.player_mouse_event_paths and 0 <= instance_idx < len(profile.player_mouse_event_paths):
            mouse_path_str_for_instance = profile.player_mouse_event_paths[instance_idx]
            if mouse_path_str_for_instance and mouse_path_str_for_instance.strip():
                mouse_path_obj = Path(mouse_path_str_for_instance)
                if mouse_path_obj.exists() and mouse_path_obj.is_char_device():
                    has_dedicated_mouse = True
                else:
                    self.logger.warning(f"Instance {instance_num}: Mouse device '{mouse_path_str_for_instance}' specified in profile but not found or not a char device.")

        has_dedicated_keyboard = False
        keyboard_path_str_for_instance = None
        if profile.player_keyboard_event_paths and 0 <= instance_idx < len(profile.player_keyboard_event_paths):
            keyboard_path_str_for_instance = profile.player_keyboard_event_paths[instance_idx]
            if keyboard_path_str_for_instance and keyboard_path_str_for_instance.strip():
                keyboard_path_obj = Path(keyboard_path_str_for_instance)
                if keyboard_path_obj.exists() and keyboard_path_obj.is_char_device():
                    has_dedicated_keyboard = True
                else:
                    self.logger.warning(f"Instance {instance_num}: Keyboard device '{keyboard_path_str_for_instance}' specified in profile but not found or not a char device.")

        return {
            'has_dedicated_mouse': has_dedicated_mouse,
            'mouse_path_str_for_instance': mouse_path_str_for_instance,
            'has_dedicated_keyboard': has_dedicated_keyboard,
            'keyboard_path_str_for_instance': keyboard_path_str_for_instance,
            'should_add_grab_flags': has_dedicated_mouse and has_dedicated_keyboard
        }

    def _build_gamescope_command(self, profile: GameProfile, should_add_grab_flags: bool, instance_num: int) -> List[str]:
        """Constrói o comando do Gamescope."""
        gamescope_path = 'gamescope'

        # Usa largura efetiva (dividida se for splitscreen)
        effective_width = profile.effective_instance_width

        gamescope_cli_options = [
            gamescope_path,
            '-W', str(effective_width),
            '-H', str(profile.instance_height),
            '-w', str(effective_width),
            '-h', str(profile.instance_height),
        ]

        # Configurações específicas para splitscreen vs normal
        if profile.is_splitscreen_mode:
            gamescope_cli_options.append('-b')  # borderless ao invés de fullscreen
        else:
            gamescope_cli_options.extend(['-f', '--adaptive-sync'])

        if should_add_grab_flags:
            self.logger.info(f"Instance {instance_num}: Using dedicated mouse and keyboard. Adding --grab and --force-grab-cursor to Gamescope.")
            gamescope_cli_options.extend(['--grab', '--force-grab-cursor'])

        return gamescope_cli_options

    def _build_base_game_command(self, profile: GameProfile, proton_path: Optional[Path], symlinked_exe_path: Path, gamescope_cmd: List[str], instance_num: int) -> List[str]:
        """Constrói o comando base do jogo."""
        # Adiciona os argumentos do jogo definidos no perfil, se houver
        game_specific_args = []
        if profile.game_args:
            game_specific_args = profile.game_args.split()
            self.logger.info(f"Instance {instance_num}: Adding game arguments: {game_specific_args}")

        base_cmd_prefix = gamescope_cmd + ['--']  # Separador para o comando a ser executado

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
        """Constrói o comando bwrap com dispositivos de entrada."""
        bwrap_cmd = [
            'bwrap',
            '--dev-bind', '/', '/',
            '--proc', '/proc',
            '--tmpfs', '/tmp',
            '--cap-add', 'all',
        ]

        # Ensure ProtonFixes config directory is accessible inside bwrap
        protonfixes_config_dir = Path.home() / '.config' / 'protonfixes'
        bwrap_cmd.extend(['--bind', str(protonfixes_config_dir), str(protonfixes_config_dir)])
        self.logger.info(f"Instance {instance_num}: Added bwrap bind for ProtonFixes: {protonfixes_config_dir}")

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
        """Coleta os caminhos dos dispositivos a serem vinculados."""
        device_paths_to_bind = []

        # Joysticks
        if profile.player_physical_device_ids and 0 <= instance_idx < len(profile.player_physical_device_ids):
            joystick_path_str = profile.player_physical_device_ids[instance_idx]
            if joystick_path_str and joystick_path_str.strip():
                joystick_path = Path(joystick_path_str)
                if joystick_path.exists() and joystick_path.is_char_device():
                    device_paths_to_bind.append(str(joystick_path))
                    self.logger.info(f"Instance {instance_num}: Queued joystick '{joystick_path}' for bwrap binding.")
                else:
                    self.logger.warning(f"Instance {instance_num}: Joystick device '{joystick_path_str}' specified in profile but not found or not a char device. Not binding.")

        # Mouses - usa as variáveis já validadas
        if device_info['has_dedicated_mouse']:
            device_paths_to_bind.append(device_info['mouse_path_str_for_instance'])
            self.logger.info(f"Instance {instance_num}: Queued mouse device '{device_info['mouse_path_str_for_instance']}' for bwrap binding.")

        # Teclados - usa as variáveis já validadas
        if device_info['has_dedicated_keyboard']:
            device_paths_to_bind.append(device_info['keyboard_path_str_for_instance'])
            self.logger.info(f"Instance {instance_num}: Queued keyboard device '{device_info['keyboard_path_str_for_instance']}' for bwrap binding.")

        return device_paths_to_bind

    def monitor_and_wait(self) -> None:
        """Monitora as instâncias até que todas sejam finalizadas."""
        while self.process_service.monitor_processes():
            time.sleep(5)

        self.logger.info("All instances have terminated")

    def terminate_all(self) -> None:
        """Finaliza todas as instâncias do jogo gerenciadas pelo serviço."""
        self.process_service.terminate_all()
