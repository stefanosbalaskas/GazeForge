"""Package-specific exception types."""


class GazeForgeError(Exception):
    """Base exception for GazeForge."""


class SchemaError(GazeForgeError, ValueError):
    """Raised when gaze data do not satisfy the canonical schema."""


class ModelCompatibilityError(GazeForgeError, ValueError):
    """Raised when a model is incompatible with the data being analysed."""


class OptionalDependencyError(GazeForgeError, ImportError):
    """Raised when an optional feature is requested without its dependency."""
