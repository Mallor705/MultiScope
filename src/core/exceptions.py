class LinuxCoopError(Exception):
    """
    Base exception for all custom errors raised by the Proton-Coop application.

    Catching this exception allows for handling of all application-specific
    errors.
    """
    pass

class ProfileNotFoundError(LinuxCoopError):
    """
    Raised when a specified game profile `.json` file cannot be found.
    """
    pass

class ProtonNotFoundError(LinuxCoopError):
    """
    Raised when a specified Proton version cannot be located in the standard
    Steam library paths.
    """
    pass

class DependencyError(LinuxCoopError):
    """
    Raised when a required external dependency (e.g., `bwrap`, `gamescope`)
    is not found on the system's PATH.
    """
    pass

class ExecutableNotFoundError(LinuxCoopError):
    """
    Raised when the game executable specified in a profile does not exist at
    the configured path.
    """
    pass
