import os


class UploadHelper:
    """
    This class implements static helpers that are to be used by HistoryHandler and LibgenUpload.
    """

    def __init__(self):
        self.valid_extensions = ("epub", "pdf", "mobi")
        pass

    @staticmethod
    def _is_path_valid(file_path: str):
        file_path.encode("UTF-8")
        return os.path.isfile(file_path)


    def _is_extension_valid(self, file_path: str):
        if file_path.endswith(self.valid_extensions):
            return True

        return False

    def check_filepaths(self, file_paths: list[str]):
        valid_filepaths = []
        for filepath in file_paths:
            if self._is_path_valid(filepath) and self._is_extension_valid(filepath):
                valid_filepaths.append(filepath)

        return valid_filepaths
