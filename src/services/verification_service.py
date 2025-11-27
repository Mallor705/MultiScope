import json
from pathlib import Path
from ..core.config import Config

class VerificationService:
    def __init__(self, logger):
        self.logger = logger
        self.cache_dir = Path.home() / f".cache/{Config.APP_NAME}/tmp"
        self.cache_file = self.cache_dir / "verification_cache.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_verification_path(self, instance_num: int) -> Path:
        return Config.get_steam_home_path(instance_num) / ".local/share"

    def verify_instance(self, instance_num: int) -> str:
        verification_path = self._get_verification_path(instance_num)

        # Adjusting the path to include the "Steam" folder
        steam_dir = verification_path / "Steam"
        steamclient_dll = steam_dir / "steamclient.dll"
        steamclient64_dll = steam_dir / "steamclient64.dll"

        status = "Failed"
        if steamclient_dll.exists() and steamclient64_dll.exists():
            status = "Passed"

        self.logger.info(f"Verification for instance {instance_num}: Status - {status} at path {steam_dir}")
        self.update_cache(instance_num, status)
        return status

    def update_cache(self, instance_num: int, status: str):
        cache_data = self.read_cache()
        cache_data[f"instance_{instance_num}"] = status
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=4)
        except IOError as e:
            self.logger.error(f"Failed to write to cache file: {e}")

    def read_cache(self) -> dict:
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to read cache file: {e}")
            return {}

    def get_instance_status(self, instance_num: int) -> str:
        return self.read_cache().get(f"instance_{instance_num}", "Failed")
