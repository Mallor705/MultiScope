import os
import time
import shutil
from pathlib import Path
from typing import List
from ..core.config import Config
from ..core.exceptions import DependencyError
from ..models.profile import GameProfile
from ..models.instance import GameInstance
from .proton_service import ProtonService
from .process_service import ProcessService

class InstanceService:
    def __init__(self, logger):
        self.logger = logger
        self.proton_service = ProtonService(logger)
        self.process_service = ProcessService(logger)
    
    def validate_dependencies(self):
        """Check if required commands are available"""
        self.logger.info("Validating dependencies...")
        for cmd in Config.REQUIRED_COMMANDS:
            if not shutil.which(cmd):
                raise DependencyError(f"Required command '{cmd}' not found")
        self.logger.info("Dependencies validated successfully")
    
    def launch_instances(self, profile: GameProfile, profile_name: str):
        """Launch all game instances"""
        proton_path, steam_root = self.proton_service.find_proton_path(profile.proton_version)
        
        self.process_service.cleanup_previous_instances(proton_path, profile.exe_path)
        
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
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
        """Create instance models"""
        instances = []
        for i in range(1, profile.num_players + 1):
            prefix_dir = Config.PREFIX_BASE_DIR / f"{profile_name}_instance_{i}"
            log_file = Config.LOG_DIR / f"{profile_name}_instance_{i}.log"
            
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
        """Launch a single game instance"""
        self.logger.info(f"Preparing instance {instance.instance_num}...")
        
        env = self._prepare_environment(instance, steam_root)
        cmd = self._build_command(profile, proton_path)
        
        self.logger.info(f"Launching instance {instance.instance_num} (Log: {instance.log_file})")
        
        pid = self.process_service.launch_instance(cmd, instance.log_file, env)
        instance.pid = pid
        
        self.logger.info(f"Instance {instance.instance_num} started with PID: {pid}")
    
    def _prepare_environment(self, instance: GameInstance, steam_root: Path) -> dict:
        """Prepare environment variables for instance"""
        env = os.environ.copy()
        env.update({
            'STEAM_COMPAT_CLIENT_INSTALL_PATH': str(steam_root),
            'STEAM_COMPAT_DATA_PATH': str(instance.prefix_dir),
            'WINEPREFIX': str(instance.prefix_dir / 'pfx'),
            'DXVK_ASYNC': '1',
            'PROTON_LOG': '1',
            'PROTON_LOG_DIR': str(Config.LOG_DIR)
        })
        return env
    
    def _build_command(self, profile: GameProfile, proton_path: Path) -> List[str]:
        """Build gamescope + proton command"""
        return [
            'gamescope',
            '-W', str(profile.instance_width),
            '-H', str(profile.instance_height),
            '-f',
            '--',
            str(proton_path),
            'run',
            str(profile.exe_path)
        ]
    
    def monitor_and_wait(self):
        """Monitor instances until all terminate"""
        while self.process_service.monitor_processes():
            time.sleep(5)
        
        self.logger.info("All instances have terminated")
    
    def terminate_all(self):
        """Terminate all instances"""
        self.process_service.terminate_all()