import os

from selenium.webdriver.chrome.webdriver import WebDriver

from scrapers_preservation.exceptions.exceptions import UploaderError
from scrapers_preservation.models.uploader_models import LibgenMetadata
from scrapers_preservation.upload.libgen_uploader import LibgenUpload


class UploadHelper:
    """
    This class implements static helpers that are to be used by UploadQueue and LibgenUpload.
    """

    def __init__(self, download_folder_path: str, driver: WebDriver):
        self.d_path = download_folder_path
        self.driver = driver
        self.uploaded_files = []