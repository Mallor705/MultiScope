"""
Steam verifier module for the Twinverse application.

This module provides functionality to verify Steam installations.
"""

from pathlib import Path


class SteamVerifier:
    """Verifies Steam installations for Twinverse instances."""

    def __init__(self, logger):
        """Initialize the Steam verifier with a logger."""
        self.logger = logger

    def verify(self, instance_path: Path) -> bool:
        """Verify if Steam is properly installed at the given instance path."""
        steam_sh_path = instance_path / ".local/share/Steam/steam.sh"
        self.logger.info(f"Verifying Steam installation at: {steam_sh_path}")
        is_verified = steam_sh_path.exists()
        self.logger.info(f"Verification result: {'Passed' if is_verified else 'Failed'}")
        return is_verified
