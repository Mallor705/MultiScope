"""
Module defining the Steam instance model for the Twinverse application.

This module contains the data model for representing a single, running
instance of Steam.
"""

from typing import Optional

from pydantic import BaseModel


class SteamInstance(BaseModel):
    """
    Represents a single, running instance of Steam.

    Attributes:
        instance_num (int): A unique identifier for this instance (e.g., 1, 2).
        pid (Optional[int]): The process ID of the Gamescope/Steam process.
    """

    instance_num: int
    pid: Optional[int] = None
