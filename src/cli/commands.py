import click
import signal
import subprocess
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
            
            # Lógica para determinar o caminho do perfil (JSON ou .profile)
            profile_path_json = Config.PROFILE_DIR / f"{profile_name}.json"
            profile_path_profile = Config.get_profile_path(profile_name) # Este já retorna com .profile

            profile_to_load = None
            if profile_path_json.exists():
                profile_to_load = profile_path_json
                self.logger.info(f"Loading JSON profile: {profile_to_load}")
            elif profile_path_profile.exists():
                profile_to_load = profile_path_profile
                self.logger.info(f"Loading .profile: {profile_to_load}")
            else:
                self.logger.error(f"Profile not found for '{profile_name}'. Looked for {profile_path_json} and {profile_path_profile}")
                raise ProfileNotFoundError(f"Profile '{profile_name}' not found as .json or .profile")

            print(f"[DEBUG] profile_path (selected): {profile_to_load}")
            print("[DEBUG] Chamando GameProfile.load_from_file()")
            profile = GameProfile.load_from_file(profile_to_load)
            
            # Usa effective_num_players para determinar o número de instâncias
            # Se profile.player_configs foi carregado, ele será a fonte da verdade para o número de jogadores.
            # Se não, profile.num_players (do arquivo de perfil) será usado.
            # Esta lógica assume que se player_configs está presente, seu tamanho define num_players.
            # A validação de num_players >= 2 ainda ocorre no Pydantic.
            # Se num_players for definido no JSON e player_configs também, precisamos decidir qual tem precedência
            # ou garantir que sejam consistentes. O Pydantic validará num_players como um campo obrigatório
            # se não for inferido de player_configs no load_from_file.
            # A lógica atual em load_from_file infere num_players de len(players) se num_players não estiver no JSON.
            # Se ambos estiverem, o num_players do JSON será usado, mas effective_num_players ainda pode ser usado aqui.

            self.logger.info(f"Loading profile: {profile.game_name} for {profile.effective_num_players} players")
            # Passa profile.effective_num_players se a lógica de lançamento depender disso explicitamente,
            # ou garante que profile.num_players foi corretamente ajustado/validado no load.
            # Por enquanto, launch_instances usa profile.num_players diretamente.
            # Se effective_num_players for diferente de profile.num_players, isso pode ser um problema.
            # O ideal é que profile.num_players seja a única fonte de verdade após o carregamento.
            # O validador de num_players já garante que seja >=2.
            # Se player_configs estiver presente, o load_from_file já ajusta num_players se não estiver no json.
            # Se num_players ESTIVER no json e for diferente de len(player_configs), Pydantic não vai reclamar por padrão.
            # Poderíamos adicionar um root_validator em GameProfile para garantir consistência se ambos forem fornecidos.

            # Para simplificar, vamos confiar que profile.num_players é a fonte correta após o carregamento.
            # O load_from_file tenta preencher num_players se ausente e players está presente.

            print("[DEBUG] Chamando launch_instances()")
            # A assinatura de launch_instances espera profile.num_players.
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
            # Tenta validar as credenciais sudo usando uma caixa de diálogo gráfica
            self.logger.info("Attempting to get sudo credentials via graphical prompt (pkexec)...")
            subprocess.run(['pkexec', 'whoami'], check=True, capture_output=True)
            self.logger.info("Sudo credentials obtained successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to validate sudo credentials using pkexec. Error: {e}")
            # Adiciona uma mensagem mais amigável para o usuário
            print("Falha ao obter permissões de superusuário. Verifique se você digitou a senha corretamente ou se o Polkit está configurado.")
            raise TerminateCLI()
        except FileNotFoundError:
            # Fallback para o método original se pkexec não for encontrado
            self.logger.warning("pkexec not found. Falling back to 'sudo -v'.")
            try:
                subprocess.run(['sudo', '-v'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                self.logger.error("Failed to validate sudo credentials using 'sudo -v'")
                print("Falha ao obter permissões de superusuário com 'sudo -v'.")
                raise TerminateCLI()
            except FileNotFoundError:
                self.logger.error("'sudo' command not found. Cannot acquire root privileges.")
                print("Comando 'sudo' não encontrado. Não é possível obter privilégios de root.")
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