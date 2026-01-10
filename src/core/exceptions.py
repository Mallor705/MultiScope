"""
Module defining custom exceptions for the Twinverse application.

This module contains all custom exception classes used throughout the
Twinverse application to handle specific error conditions.
"""


class TwinverseError(Exception):
    """Base exception for all custom errors raised by the Twinverse application.

    Catching this exception allows for handling of all application-specific
    errors.
    """

    pass


class ProfileNotFoundError(TwinverseError):
    """Raised when a specified game profile `.json` file cannot be found."""

    pass


class DependencyError(TwinverseError):
    """Raised when a required external dependency (e.g., `bwrap`, `gamescope`) is not found on the system's PATH."""

    pass


class VirtualDeviceError(TwinverseError):
    """Raised when there is an error creating or managing a virtual device."""

    pass
