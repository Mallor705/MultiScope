from pathlib import Path


class SteamVerifier:
    def __init__(self, logger):
        self.logger = logger

    def verify(self, instance_path: Path) -> bool:
        steam_sh_path = instance_path / ".local/share/Steam/steam.sh"
        self.logger.info(f"Verifying Steam installation at: {steam_sh_path}")
        is_verified = steam_sh_path.exists()
        self.logger.info(f"Verification result: {'Passed' if is_verified else 'Failed'}")
        return is_verified
