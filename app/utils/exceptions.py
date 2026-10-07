class ApplicationError(Exception):
    """Base exception with a client-safe message."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidGeospatialFileError(ApplicationError):
    pass


class UnsupportedFileTypeError(ApplicationError):
    status_code = 415


class UploadTooLargeError(ApplicationError):
    status_code = 413


class UnsafeArchiveError(ApplicationError):
    pass


class CRSProcessingError(ApplicationError):
    pass


class MeasurementError(ApplicationError):
    pass
