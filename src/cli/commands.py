import click
import shutil
import signal
import subprocess
from functools import lru_cache
from typing import Optional
from ..core.config import Config
from ..core.logger import Logger
from ..core.exceptions import LinuxCoopError, ProfileNotFoundError
from ..models.profile import GameProfile
from ..services.instance import InstanceService

class TerminateCLI(Exception):
    """Exceção para finalizar a CLI de forma controlada."""
    pass

class LinuxCoopCLI:
    """Interface de linha de comando para o Linux-Coop."""
    def __init__(self):
        """Inicializa a CLI com logger e configuração de sinais."""
        self.logger = Logger("linux-coop", Config.LOG_DIR)
        self._instance_service: Optional[InstanceService] = None
        self._sudo_validated = False
        self.setup_signal_handlers()
    
    @property
    def instance_service(self) -> InstanceService:
        """Lazy loading do InstanceService."""
        if self._instance_service is None:
            self._instance_service = InstanceService(self.logger)
        return self._instance_service
    
    def setup_signal_handlers(self):
        """Configura os handlers de sinal para garantir limpeza ao encerrar."""
        def signal_handler(signum, frame):
            self.logger.info("Received interrupt signal. Terminating instances...")
            if self._instance_service is not None:
                self._instance_service.terminate_all()
            raise TerminateCLI()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, profile_name: str):
        """Fluxo principal de execução da CLI."""
        if not profile_name or not profile_name.strip():
            self.logger.error("O nome do perfil não pode ser vazio.")
            raise TerminateCLI()
        try:
            # Validações em lote
            self._batch_validate(profile_name)
            
            # Carrega perfil (com cache)
            profile = self._load_profile(profile_name)
            
            self.logger.info(f"Loading profile: {profile.game_name} for {profile.effective_num_players} players")

            self.instance_service.launch_instances(profile, profile_name)
            self.instance_service.monitor_and_wait()
            self.logger.info("Script completed")
        except LinuxCoopError as e:
            self.logger.error(str(e))
            raise TerminateCLI()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise TerminateCLI()
    
    def _batch_validate(self, profile_name: str):
        """Executa todas as validações necessárias em lote."""
        # Validate sudo (cached)
        self._prompt_sudo()
        
        # Validate dependencies (cached in InstanceService)
        self.instance_service.validate_dependencies()
        
        # Validate profile exists
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        if not profile_path.exists():
            self.logger.error(f"Profile not found: {profile_path}")
            raise ProfileNotFoundError(f"Profile '{profile_name}' not found")
    
    @lru_cache(maxsize=16)
    def _load_profile(self, profile_name: str) -> GameProfile:
        """Carrega perfil com cache."""
        profile_path = Config.PROFILE_DIR / f"{profile_name}.json"
        return GameProfile.load_from_file(profile_path)
    
    def _prompt_sudo(self):
        """Solicita senha sudo usando interface gráfica (zenity) ou terminal."""
        # Cache sudo validation
        if self._sudo_validated:
            return
            
        # Primeiro verifica se já tem privilégios sudo válidos
        if self._check_sudo_valid():
            self.logger.info("Sudo credentials already valid.")
            self._sudo_validated = True
            return
        
        # Tenta usar zenity para interface gráfica se disponível
        if self._try_zenity_sudo():
            self._sudo_validated = True
            return
        
        # Fallback para prompt de terminal
        if self._try_terminal_sudo():
            self._sudo_validated = True
            return
            
        self.logger.error("Failed to obtain sudo credentials")
        raise TerminateCLI()
    
    @lru_cache(maxsize=1)
    def _check_sudo_valid(self) -> bool:
        """Verifica se sudo já está válido (cached)."""
        try:
            subprocess.run(['sudo', '-n', 'true'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _try_zenity_sudo(self) -> bool:
        """Tenta obter sudo via zenity."""
        if not shutil.which('zenity'):
            return False
            
        try:
            self.logger.info("Requesting sudo password via graphical interface...")
            result = subprocess.run([
                'zenity', '--password', 
                '--title=Linux-Coop', 
                '--text=Digite sua senha para continuar:'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error("Password dialog cancelled by user")
                raise TerminateCLI()
            
            password = result.stdout.strip()
            # Testa a senha com sudo
            sudo_process = subprocess.Popen(
                ['sudo', '-S', 'true'], 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = sudo_process.communicate(input=password + '\n')
            
            if sudo_process.returncode == 0:
                self.logger.info("Sudo credentials obtained successfully.")
                return True
            else:
                self.logger.error("Invalid sudo password provided")
                raise TerminateCLI()
                
        except FileNotFoundError:
            self.logger.warning("zenity not found, falling back to terminal prompt")
            return False
        except Exception as e:
            self.logger.warning(f"zenity failed: {e}, falling back to terminal prompt")
            return False
    
    def _try_terminal_sudo(self) -> bool:
        """Tenta obter sudo via terminal."""
        try:
            self.logger.info("Requesting sudo password via terminal...")
            subprocess.run(['sudo', '-v'], check=True)
            self.logger.info("Sudo credentials obtained successfully.")
            return True
        except subprocess.CalledProcessError:
            self.logger.error("Failed to validate sudo credentials")
            return False
        except FileNotFoundError:
            self.logger.error("'sudo' command not found. Cannot acquire root privileges.")
            return False

@click.command()
@click.argument('profile_name')
def main(profile_name):
    """Lança instâncias do jogo usando o perfil especificado."""
    cli = LinuxCoopCLI()
    try:
        cli.run(profile_name)
    except TerminateCLI:
        pass