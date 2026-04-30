class OutputDirNotAllowedError(Exception):
    """Raised when the output directory is not allowed."""
    pass

class LMStudioUnavailableError(Exception):
    """Raised when LM Studio is not available."""
    pass

class UnknownRunError(Exception):
    """Raised when a requested run ID is not found."""
    pass