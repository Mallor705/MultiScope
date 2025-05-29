import os
import time
import shutil
from pathlib import Path
from typing import List
from ..core.config import Config
from ..core.exceptions import DependencyError
from ..models.profile import GameProfile
from ..models.instance import GameInstance
from .proton import ProtonService
from .process import ProcessService

class InstanceService:
    """Serviço responsável por gerenciar instâncias do jogo, incluindo validação de dependências, criação, lançamento e monitoramento."""
    def __init__(self, logger):
        """Inicializa o serviço de instâncias com logger, ProtonService e ProcessService."""
        self.logger = logger
        self.proton_service = ProtonService(logger)
        self.process_service = ProcessService(logger)
    
    def validate_dependencies(self):
        """Valida se todos os comandos necessários estão disponíveis no sistema."""
        self.logger.info("Validating dependencies...")
        for cmd in Config.REQUIRED_COMMANDS:
            if not shutil.which(cmd):
                raise DependencyError(f"Required command '{cmd}' not found")
        self.logger.info("Dependencies validated successfully")
    
    def launch_instances(self, profile: GameProfile, profile_name: str):
        """Lança todas as instâncias do jogo conforme o perfil fornecido."""
        if profile.is_native:
            proton_path = None
            steam_root = None
        else:
            proton_path, steam_root = self.proton_service.find_proton_path(profile.proton_version)
        
        if profile.is_native:
            self.process_service.cleanup_previous_instances(None, profile.exe_path)
        else:
            self.process_service.cleanup_previous_instances(proton_path, profile.exe_path)
        
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        (Path.home() / '.config/protonfixes').mkdir(parents=True, exist_ok=True)
        Config.PREFIX_BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        instances = self._create_instances(profile, profile_name)
        
        self.logger.info(f"Launching {profile.num_players} instance(s) of '{profile.game_name}'...")
        
        for instance in instances:
            self._launch_single_instance(instance, profile, proton_path, steam_root)
            time.sleep(5)
        
        self.logger.info(f"All {profile.num_players} instances launched")
        self.logger.info(f"PIDs: {self.process_service.pids}")
        self.logger.info("Press CTRL+C to terminate all instances")
    
    def _create_instances(self, profile: GameProfile, profile_name: str) -> List[GameInstance]:
        """Cria os modelos de instância para cada jogador."""
        instances = []
        for i in range(1, profile.num_players + 1):
            prefix_dir = Config.PREFIX_BASE_DIR / f"{profile_name}_instance_{i}"
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
    
    def _launch_single_instance(self, instance: GameInstance, profile: GameProfile, 
                              proton_path: Path, steam_root: Path):
        """Lança uma única instância do jogo."""
        self.logger.info(f"Preparing instance {instance.instance_num}...")
        env = self._prepare_environment(instance, steam_root, profile)
        cmd = self._build_command(profile, proton_path, instance)
        self.logger.info(f"Launching instance {instance.instance_num} (Log: {instance.log_file})")
        pid = self.process_service.launch_instance(cmd, instance.log_file, env)
        instance.pid = pid
        self.logger.info(f"Instance {instance.instance_num} started with PID: {pid}")
    
    def _prepare_environment(self, instance: GameInstance, steam_root: Path, profile: GameProfile = None) -> dict:
        """Prepara as variáveis de ambiente para a instância do jogo, incluindo isolamento de controles."""
        env = os.environ.copy()
        env['PATH'] = os.environ['PATH']
        if not profile.is_native:
            env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = str(steam_root)
            env['STEAM_COMPAT_DATA_PATH'] = str(instance.prefix_dir)
            env['WINEPREFIX'] = str(instance.prefix_dir / 'pfx')
            env['DXVK_ASYNC'] = '1'
            env['PROTON_LOG'] = '1'
            env['PROTON_LOG_DIR'] = str(Config.LOG_DIR)

        assigned_device_path = None
        if profile and profile.player_physical_device_ids:
            idx = instance.instance_num - 1
            if 0 <= idx < len(profile.player_physical_device_ids):
                device_from_profile = profile.player_physical_device_ids[idx]
                # Tratar string vazia explicitamente como "sem dispositivo"
                if device_from_profile and device_from_profile.strip(): 
                    if Path(device_from_profile).exists():
                        self.logger.info(f"Instance {instance.instance_num}: Valid device '{device_from_profile}' found in profile and host. Assigning for SDL.")
                        assigned_device_path = device_from_profile
                    else:
                        self.logger.warning(f"Instance {instance.instance_num}: Device '{device_from_profile}' from profile not found on host.")
                else:
                    self.logger.info(f"Instance {instance.instance_num}: No device configured in profile for this instance (empty string).")
            # else: Instance number out of bounds for device list or list is shorter than num_players

        if assigned_device_path:
            env['SDL_JOYSTICK_DEVICE'] = assigned_device_path
            self.logger.info(f"Instance {instance.instance_num}: SDL_JOYSTICK_DEVICE set to '{assigned_device_path}'")
        else:
            env['SDL_JOYSTICK_DEVICE'] = "/dev/null"
            self.logger.info(f"Instance {instance.instance_num}: SDL_JOYSTICK_DEVICE set to '/dev/null'.")
        
        # print(f"[DEBUG] Ambiente da instância {instance.instance_num}: {env}")
        return env
    
    def _build_command(self, profile: GameProfile, proton_path: Path, instance: GameInstance = None) -> List[str]:
        """Monta o comando para executar o gamescope e o jogo (nativo ou via Proton), usando bwrap para isolar o controle."""
        base_cmd = []
        gamescope_path = '/usr/bin/gamescope'
        if profile.is_native:
            base_cmd = [
                gamescope_path,
                '-W', str(profile.instance_width),
                '-H', str(profile.instance_height),
                '-f',
                '--',
                str(profile.exe_path)
            ]
        else:
            base_cmd = [
                gamescope_path,
                '-W', str(profile.instance_width),
                '-H', str(profile.instance_height),
                '-f',
                '--',
                str(proton_path),
                'run',
                str(profile.exe_path)
            ]
        
        bwrap_cmd = [
            'bwrap',
            '--dev-bind', '/', '/',
            '--proc', '/proc',
            '--tmpfs', '/tmp',
            '--tmpfs', '/dev/input',
            '--chdir', '/',
        ]
        
        assigned_device_path_for_bwrap = None
        if profile and profile.player_physical_device_ids and instance:
            idx = instance.instance_num - 1
            if 0 <= idx < len(profile.player_physical_device_ids):
                device_from_profile = profile.player_physical_device_ids[idx]
                # Tratar string vazia explicitamente como "sem dispositivo"
                if device_from_profile and device_from_profile.strip(): 
                    device_path_obj = Path(device_from_profile)
                    if device_path_obj.exists() and device_path_obj.is_char_device():
                        self.logger.info(f"Instance {instance.instance_num}: Binding device '{device_from_profile}' with bwrap.")
                        assigned_device_path_for_bwrap = device_from_profile
                    elif not device_path_obj.exists():
                        self.logger.warning(f"Instance {instance.instance_num}: Device '{device_from_profile}' from profile not found on host. Not binding with bwrap.")
                    else: # Exists but not a char device
                        self.logger.warning(f"Instance {instance.instance_num}: Device '{device_from_profile}' from profile is not a character device. Not binding with bwrap.")
                else:
                    self.logger.info(f"Instance {instance.instance_num}: No device configured in profile for this instance (empty string). Not binding any specific device with bwrap.")
                        
        if assigned_device_path_for_bwrap:
            bwrap_cmd += ['--dev-bind', assigned_device_path_for_bwrap, assigned_device_path_for_bwrap]
            self.logger.info(f"Instance {instance.instance_num}: bwrap will bind '{assigned_device_path_for_bwrap}'.")
        else:
            self.logger.info(f"Instance {instance.instance_num}: No specific device to bind with bwrap. /dev/input will be isolated and likely empty of joysticks.")

        final_bwrap_cmd_str = ' '.join(bwrap_cmd + base_cmd)
        self.logger.info(f"Instance {instance.instance_num}: Full bwrap command: {final_bwrap_cmd_str}")

        return bwrap_cmd + base_cmd

    
    def monitor_and_wait(self):
        """Monitora as instâncias até que todas sejam finalizadas."""
        while self.process_service.monitor_processes():
            time.sleep(5)
        
        self.logger.info("All instances have terminated")
    
    def terminate_all(self):
        """Finaliza todas as instâncias do jogo gerenciadas pelo serviço."""
        self.process_service.terminate_all()