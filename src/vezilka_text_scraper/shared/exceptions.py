"""Project-specific exceptions."""


class VezilkaTextScraperError(Exception):
    """Base exception for expected project failures."""


class ConfigurationError(VezilkaTextScraperError):
    """Raised when application configuration is invalid."""


class AdapterError(VezilkaTextScraperError):
    """Raised when an external system or infrastructure boundary fails."""


class ServiceError(VezilkaTextScraperError):
    """Raised when a domain workflow cannot complete."""


class JobError(VezilkaTextScraperError):
    """Raised when an executable corpus job fails."""
