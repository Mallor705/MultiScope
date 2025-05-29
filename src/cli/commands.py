import click
import signal
import subprocess
from ..core.config import Config
from ..core.logger import Logger
from ..core.exceptions import LinuxCoopError
from ..models.profile import GameProfile
from ..services.instance import InstanceService

class TerminateCLI(Exception):
    """Exceção para finalizar a CLI de forma controlada."""
    pass

class LinuxCoopCLI:
    """Interface de linha de comando para o Linux-Coop."""
    def __init__(self):
        """Inicializa a CLI com logger e serviços necessários."""
        self.logger = Logger("linux-coop", Config.LOG_DIR)
        self.instance_service = InstanceService(self.logger)
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configura os handlers de sinal para garantir limpeza ao encerrar."""
        def signal_handler(signum, frame):
            self.logger.info("Received interrupt signal. Terminating instances...")
            self.instance_service.terminate_all()
            raise TerminateCLI()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, profile_name: str):
        """Fluxo principal de execução da CLI."""
        print(f"[DEBUG] Entrou em LinuxCoopCLI.run() com profile_name: {profile_name}")
        if not profile_name or not profile_name.strip():
            self.logger.error("O nome do perfil não pode ser vazio.")
            print("[DEBUG] Nome do perfil vazio, raising TerminateCLI")
            raise TerminateCLI()
        try:
            print("[DEBUG] Chamando _prompt_sudo()")
            self._prompt_sudo()
            print("[DEBUG] Chamando validate_dependencies()")
            self.instance_service.validate_dependencies()
            print("[DEBUG] Chamando get_profile_path()")
            profile_path = Config.get_profile_path(profile_name)
            print(f"[DEBUG] profile_path: {profile_path}")
            print("[DEBUG] Chamando GameProfile.load_from_file()")
            profile = GameProfile.load_from_file(profile_path)
            print("[DEBUG] Chamando launch_instances()")
            self.logger.info(f"Loading profile: {profile_name}")
            self.instance_service.launch_instances(profile, profile_name)
            print("[DEBUG] Chamando monitor_and_wait()")
            self.instance_service.monitor_and_wait()
            self.logger.info("Script completed")
            print("[DEBUG] Script completed")
        except LinuxCoopError as e:
            self.logger.error(str(e))
            print(f"[DEBUG] LinuxCoopError capturada: {e}")
            raise TerminateCLI()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            print(f"[DEBUG] Exception inesperada: {e}")
            raise TerminateCLI()
    
    def _prompt_sudo(self):
        """Solicita senha sudo se necessário para operações privilegiadas."""
        try:
            subprocess.run(['sudo', '-v'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.logger.error("Failed to validate sudo credentials")
            raise TerminateCLI()

@click.command()
@click.argument('profile_name')
def main(profile_name):
    """Lança instâncias do jogo usando o perfil especificado."""
    print("[DEBUG] Entrou no main() com profile_name:", profile_name)
    cli = LinuxCoopCLI()
    try:
        print("[DEBUG] Chamando cli.run()")
        cli.run(profile_name)
        print("[DEBUG] cli.run() finalizou normalmente")
    except TerminateCLI:
        print("[DEBUG] TerminateCLI capturada no main()")
        pass