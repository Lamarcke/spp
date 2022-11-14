class ScraperError(Exception):
    pass


class UploaderError(Exception):
    pass


class UploaderFileError(Exception):
    pass


class UploaderDuplicateError(Exception):
    pass


class UploaderHumanConfirmationError(Exception):
    pass


class HistoryError(Exception):
    pass


class HistoryFileError(Exception):
    pass
