class LinuxCoopError(Exception):
    """Base exception for Linux-Coop"""
    pass

class ProfileNotFoundError(LinuxCoopError):
    """Profile file not found"""
    pass

class ProtonNotFoundError(LinuxCoopError):
    """Proton version not found"""
    pass

class DependencyError(LinuxCoopError):
    """Required dependency not found"""
    pass

class ExecutableNotFoundError(LinuxCoopError):
    """Game executable not found"""
    pass