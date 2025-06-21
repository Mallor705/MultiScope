from pathlib import Path
from typing import Tuple, Optional, Dict, List
from functools import lru_cache
from ..core.config import Config
from ..core.exceptions import ProtonNotFoundError
from ..core.logger import Logger

class ProtonService:
    """Serviço responsável por localizar e validar o Proton e diretórios do Steam."""
    def __init__(self, logger: Logger):
        """Inicializa o serviço de Proton com logger."""
        self.logger = logger
        self._steam_path_cache: Dict[str, Optional[Path]] = {}
        self._proton_cache: Dict[str, Tuple[Optional[Path], Optional[Path]]] = {}
    
    def find_proton_path(self, version: str) -> Tuple[Path, Path]:
        """Procura o executável do Proton e o diretório raiz do Steam para a versão informada."""
        # Check cache first
        if version in self._proton_cache:
            cached_result = self._proton_cache[version]
            if cached_result[0] is not None and cached_result[1] is not None:
                self.logger.info(f"Proton found in cache: {cached_result[0]}")
                return cached_result[0], cached_result[1]
        
        self.logger.info(f"Searching for Proton: {version}")
        
        # Get valid Steam paths (cached)
        valid_steam_paths = self._get_valid_steam_paths()
        
        for steam_path in valid_steam_paths:
            proton_path = self._search_proton_in_steam(steam_path, version)
            
            if proton_path and proton_path.exists():
                self.logger.info(f"Proton found: {proton_path}")
                # Cache the result
                self._proton_cache[version] = (proton_path, steam_path)
                return proton_path, steam_path
        
        # Cache negative result
        self._proton_cache[version] = (None, None)
        raise ProtonNotFoundError(f"Proton '{version}' not found")
    
    @lru_cache(maxsize=32)
    def _get_valid_steam_paths(self) -> Tuple[Path, ...]:
        """Cache Steam paths que existem no sistema."""
        valid_paths = []
        for steam_path in Config.STEAM_PATHS:
            cache_key = str(steam_path)
            if cache_key not in self._steam_path_cache:
                self._steam_path_cache[cache_key] = steam_path if steam_path.exists() else None
            
            if self._steam_path_cache[cache_key]:
                valid_paths.append(self._steam_path_cache[cache_key])
        
        return tuple(valid_paths)

    @lru_cache(maxsize=64)
    def _search_proton_in_steam(self, steam_path: Path, version: str) -> Optional[Path]:
        """Procura o Proton nos diretórios do Steam com cache."""
        search_dirs = [
            steam_path / "steamapps/common",
            steam_path / "compatibilitytools.d"
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            # Try different naming conventions
            proton_candidates = []
            if version == "Experimental":
                proton_candidates = [search_dir / "Proton - Experimental"]
            else:
                proton_candidates = [
                    search_dir / f"Proton {version}",
                    search_dir / version
                ]
            
            for proton_dir in proton_candidates:
                proton_script = proton_dir / "proton"
                if proton_script.exists():
                    return proton_script
        
        return None

    def list_installed_proton_versions(self) -> List[str]:
        """Lista todas as versões do Proton instaladas encontradas nos diretórios do Steam."""
        self.logger.info("Listing installed Proton versions.")
        installed_versions = set()
        
        valid_steam_paths = self._get_valid_steam_paths()
        
        for steam_path in valid_steam_paths:
            search_dirs = [
                steam_path / "steamapps/common",
                steam_path / "compatibilitytools.d"
            ]
            
            for search_dir in search_dirs:
                if search_dir.exists():
                    for item in search_dir.iterdir():
                        if item.is_dir() and ("Proton" in item.name or "GE-Proton" in item.name or "Wine" in item.name):
                            # Basic check for a 'proton' executable within the directory
                            if (item / "proton").exists():
                                installed_versions.add(item.name)
        
        sorted_versions = sorted(list(installed_versions))
        self.logger.info(f"Found Proton versions: {sorted_versions}")
        return sorted_versions