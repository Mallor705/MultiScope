import click
import signal
import subprocess
from ..core.config import Config
from ..core.logger import Logger
from ..core.exceptions import LinuxCoopError
from ..models.profile import GameProfile
from ..services.instance_service import InstanceService

class LinuxCoopCLI:
    def __init__(self):
        self.logger = Logger("linux-coop", Config.LOG_DIR)
        self.instance_service = InstanceService(self.logger)
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for cleanup"""
        def signal_handler(signum, frame):
            self.logger.info("Received interrupt signal. Terminating instances...")
            self.instance_service.terminate_all()
            exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, profile_name: str):
        """Main execution flow"""
        try:
            self._prompt_sudo()
            self.instance_service.validate_dependencies()
            
            profile_path = Config.get_profile_path(profile_name)
            profile = GameProfile.load_from_file(profile_path)
            
            self.logger.info(f"Loading profile: {profile_name}")
            
            self.instance_service.launch_instances(profile, profile_name)
            self.instance_service.monitor_and_wait()
            
            self.logger.info("Script completed")
            
        except LinuxCoopError as e:
            self.logger.error(str(e))
            exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            exit(1)
    
    def _prompt_sudo(self):
        """Prompt for sudo password if needed"""
        try:
            subprocess.run(['sudo', '-v'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.logger.error("Failed to validate sudo credentials")
            exit(1)

@click.command()
@click.argument('profile_name')
def main(profile_name):
    """Launch game instances using specified profile"""
    cli = LinuxCoopCLI()
    cli.run(profile_name)