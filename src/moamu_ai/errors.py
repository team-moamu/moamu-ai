class PhotoVerificationError(Exception):
    """Base class for errors safe to map to internal API responses."""


class ImageRootUnavailableError(PhotoVerificationError):
    pass


class ImageNotFoundError(PhotoVerificationError):
    pass


class ImagePathNotAllowedError(PhotoVerificationError):
    pass


class ImageUnreadableError(PhotoVerificationError):
    pass


class ProviderConfigurationError(PhotoVerificationError):
    pass


class ModelProviderError(PhotoVerificationError):
    pass


class InvalidModelOutputError(PhotoVerificationError):
    pass
