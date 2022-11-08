import os

from selenium.webdriver.chrome.webdriver import WebDriver

from biblioterra_scraper.exceptions.exceptions import UploaderError
from biblioterra_scraper.models.uploader_models import LibgenMetadata
from biblioterra_scraper.upload.libgen_uploader import LibgenUpload


class UploadHelper:
    """
    This helper class has methods for batch uploading.
    Using this class is optional.
    """

    def __init__(self, download_folder_path: str, driver: WebDriver):
        self.d_path = download_folder_path
        self.driver = driver
        self.uploaded_files = []